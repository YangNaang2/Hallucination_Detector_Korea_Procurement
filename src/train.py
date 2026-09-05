"""이진 토큰 분류 파인튜닝 (논문 III-D 설정 그대로).

  6 epoch / lr 1e-5 / 유효 배치 4 / bf16

A5000 24GB 1장 기준이라 per-device 배치 1 + grad_accum 4 + gradient checkpointing 이
기본값이다. 논문의 A100 40GB · 배치 4 와 유효 배치가 같다.

사용
  python -m src.train --model Alibaba-NLP/gte-multilingual-base --trust-remote-code
  python -m src.train --model klue/roberta-base --max-length 512
"""
from __future__ import annotations

import argparse
import inspect
import json
import math

import numpy as np
import torch
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                          Trainer, TrainingArguments)

import config as C
from src.dataset import Collator, HalluDataset


class WeightedTrainer(Trainer):
    """환각 클래스에 가중치를 준 CE loss.

    환각 토큰이 4% 뿐이라 기본 CE 는 '전부 지지' 쪽으로 쏠린다. 실제로 xlmr 은
    환각 재현율이 0.269 까지 떨어졌다. 가중치를 주면 재현율이 오르고 정밀도가
    내려가므로, 가중치 값은 1.5 ~ 5 사이를 몇 개 시도해 보고 고른다.
    """

    def __init__(self, *a, class_weight: float = 1.0, **kw):
        super().__init__(*a, **kw)
        self.class_weight = class_weight

    def compute_loss(self, model, inputs, return_outputs=False, **kw):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        w = torch.tensor([1.0, self.class_weight],
                         device=outputs.logits.device, dtype=outputs.logits.dtype)
        loss = torch.nn.functional.cross_entropy(
            outputs.logits.view(-1, outputs.logits.size(-1)), labels.view(-1),
            weight=w, ignore_index=C.IGNORE_INDEX)
        return (loss, outputs) if return_outputs else loss


def build_training_args(total_steps: int, **kw):
    """transformers 버전이 받지 않는 인자를 걸러 `TrainingArguments` 를 만든다.

    버전에 따라 인자 이름이 바뀌거나 사라진다. 실제로 `warmup_ratio` 를 받지 않아
    학습이 시작도 못 하고 죽은 적이 있다. 여기서 세 가지를 처리한다.

      1. `eval_strategy` ↔ `evaluation_strategy` — 버전마다 이름이 다르다
      2. `warmup_ratio` 가 없으면 `warmup_steps` 로 환산한다 — 워밍업을 그냥 버리면
         먼저 학습한 klue·xlmr 과 조건이 달라져 비교가 성립하지 않는다
      3. 그래도 남는 것은 버리고 **무엇을 버렸는지 화면에 찍는다** (조용히 넘어가면
         나중에 결과 차이의 원인을 못 찾는다)
    """
    import transformers
    sig = set(inspect.signature(TrainingArguments.__init__).parameters)
    print(f"[학습] transformers {transformers.__version__}")

    if "eval_strategy" in kw and "eval_strategy" not in sig:
        if "evaluation_strategy" in sig:
            kw["evaluation_strategy"] = kw.pop("eval_strategy")
        else:
            kw.pop("eval_strategy")

    if "warmup_ratio" in kw and "warmup_ratio" not in sig:
        ratio = kw.pop("warmup_ratio")
        if "warmup_steps" in sig:
            steps = max(1, int(total_steps * ratio))
            kw["warmup_steps"] = steps
            print(f"[학습] warmup_ratio 를 받지 않아 warmup_steps={steps} 로 바꿨습니다 "
                  f"(전체 {total_steps} 스텝의 {ratio:.0%})")
        else:
            print("[학습] ! 워밍업 설정을 넣지 못했습니다. 먼저 학습한 모델과 조건이 다릅니다.")

    dropped = sorted(k for k in kw if k not in sig)
    for k in dropped:
        kw.pop(k)
    if dropped:
        print(f"[학습] ! 이 버전이 받지 않아 뺀 인자: {', '.join(dropped)}")

    return TrainingArguments(**kw)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    mask = labels != C.IGNORE_INDEX
    y_true = labels[mask]
    y_pred = logits.argmax(-1)[mask]

    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0)
    p1, r1, f11, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=C.LABEL_HALLUCINATED,
        zero_division=0)

    out = {"macro_precision": p, "macro_recall": r, "macro_f1": f1,
           "hallu_precision": p1, "hallu_recall": r1, "hallu_f1": f11}

    if len(np.unique(y_true)) == 2:
        exp = np.exp(logits[mask] - logits[mask].max(-1, keepdims=True))
        prob = (exp / exp.sum(-1, keepdims=True))[:, C.LABEL_HALLUCINATED]
        out["auroc"] = roc_auc_score(y_true, prob)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=C.DEFAULT_ENCODER)
    ap.add_argument("--data", default=str(C.WORK_DIR / "ko_ragtruth.jsonl"))
    ap.add_argument("--max-length", type=int, default=C.MAX_LENGTH)
    ap.add_argument("--epochs", type=int, default=C.NUM_EPOCHS)
    ap.add_argument("--lr", type=float, default=C.LEARNING_RATE)
    ap.add_argument("--batch", type=int, default=C.PER_DEVICE_BATCH)
    ap.add_argument("--grad-accum", type=int, default=C.GRAD_ACCUM)
    ap.add_argument("--trust-remote-code", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--class-weight", type=float, default=1.0,
                    help="환각 클래스 가중치. 1.0 이면 논문 그대로. 2~3 부터 시도해 볼 것")
    args = ap.parse_args()

    out_dir = args.out or str(C.RUNS_DIR / args.model.split("/")[-1])

    tok = AutoTokenizer.from_pretrained(
        args.model, trust_remote_code=args.trust_remote_code)
    if not tok.is_fast:
        raise SystemExit(
            "[!] fast tokenizer 가 필요합니다 (offset_mapping 으로 라벨을 정렬하므로). "
            "다른 체크포인트를 쓰세요.")

    train_ds = HalluDataset(args.data, tok, args.max_length, split="train")
    eval_ds = HalluDataset(args.data, tok, args.max_length, split="test")
    print(f"train {len(train_ds):,} / test {len(eval_ds):,}")
    if len(train_ds) == 0:
        raise SystemExit("[!] 학습 데이터가 비었습니다. postprocess 결과와 split 값을 확인하세요.")

    model = AutoModelForTokenClassification.from_pretrained(
        args.model, num_labels=2,
        id2label={0: "SUPPORTED", 1: "HALLUCINATED"},
        label2id={"SUPPORTED": 0, "HALLUCINATED": 1},
        trust_remote_code=args.trust_remote_code,
    )

    total_steps = math.ceil(len(train_ds) / max(1, args.batch * args.grad_accum)) * args.epochs
    targs = build_training_args(
        total_steps=total_steps,
        output_dir=out_dir,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=max(1, args.batch),
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=True,
        bf16=True,
        warmup_ratio=0.06,
        weight_decay=0.01,
        logging_steps=50,
        eval_strategy="epoch" if len(eval_ds) else "no",
        save_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=bool(len(eval_ds)),
        metric_for_best_model="hallu_f1",
        greater_is_better=True,
        report_to=[],
    )

    kw = dict(
        model=model, args=targs,
        train_dataset=train_ds,
        eval_dataset=eval_ds if len(eval_ds) else None,
        data_collator=Collator(tok),
        compute_metrics=compute_metrics if len(eval_ds) else None,
    )
    if args.class_weight != 1.0:
        print(f"[학습] 환각 클래스 가중치 {args.class_weight}")
        trainer = WeightedTrainer(class_weight=args.class_weight, **kw)
    else:
        trainer = Trainer(**kw)
    trainer.train()
    trainer.save_model(out_dir)
    tok.save_pretrained(out_dir)

    if len(eval_ds):
        metrics = trainer.evaluate()
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
        with open(f"{out_dir}/train_eval.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print("\n비교 기준 — Turk-LettuceDetect 전체 테스트셋 토큰 F1 0.7266 (터키어)")

    print(f"\n→ {out_dir}")


if __name__ == "__main__":
    main()
