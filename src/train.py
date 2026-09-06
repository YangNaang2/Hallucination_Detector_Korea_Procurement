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
                          Trainer, TrainerCallback, TrainingArguments)

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


class CollapseGuard(TrainerCallback):
    """학습이 무너졌으면 일찍 멈춘다.

    bge-m3 는 XLM-RoBERTa-large 기반이라 파인튜닝이 불안정하다. 실제로 영어 대조
    런이 6 에폭 내내 AUROC 0.50 언저리에 머물다 상수로 굳었다(모든 토큰에 같은 값을
    뱉는 상태). **다섯 시간을 태우고 나서야 그것을 알았다.**

    AUROC 은 임계값과 무관하게 "순위를 매기는 능력" 을 보므로, 학습이 되고 있으면
    첫 에폭부터 0.5 를 뚜렷하게 넘는다. 두 에폭 연속 문턱을 못 넘으면 되살아날
    가능성이 낮으므로 멈추고, 무엇을 바꿔야 하는지 함께 찍는다.
    """

    def __init__(self, floor: float = 0.55, patience: int = 2):
        self.floor = floor
        self.patience = patience
        self.bad = 0

    def on_evaluate(self, args, state, control, metrics=None, **kw):
        auroc = (metrics or {}).get("eval_auroc")
        if auroc is None:
            return
        if auroc < self.floor:
            self.bad += 1
            print(f"[학습] ! AUROC {auroc:.4f} — 아직 배우지 못했습니다 "
                  f"({self.bad}/{self.patience})")
            if self.bad >= self.patience:
                print("[학습] !! 두 에폭 연속으로 신호가 없어 멈춥니다. "
                      "AUROC 0.5 는 동전 던지기와 같습니다.")
                print("       다음을 순서대로 시도하세요 — "
                      "① --seed 를 바꿔 다시 (large 계열은 초기값을 탄다) "
                      "② --lr 5e-6 로 낮추기 "
                      "③ --grad-accum 8 로 배치 키우기 "
                      "④ 더 작고 안정적인 인코더(xlm-roberta-base)로 대조하기")
                control.should_training_stop = True
        else:
            self.bad = 0


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
    ap.add_argument("--seed", type=int, default=42,
                    help="난수 씨앗. large 계열이 무너지면 이것부터 바꿔 본다")
    ap.add_argument("--no-guard", action="store_true",
                    help="학습이 안 되어도 끝까지 돌린다")
    ap.add_argument("--save-total-limit", type=int, default=2,
                    help="남겨 둘 체크포인트 수. bge-m3 는 하나에 7GB 쯤이라 "
                         "디스크가 빠듯하면 1 로 줄인다")
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

    # 체크포인트 하나가 모델 크기의 3배쯤 된다(가중치 + 옵티마이저 상태).
    # 두 시간 학습한 뒤 저장 단계에서 디스크가 터진 적이 있어 미리 경고한다.
    try:
        import shutil
        n_param = sum(p.numel() for p in model.parameters())
        need_gb = n_param * 4 * 3 * max(1, args.save_total_limit) / 1e9
        free_gb = shutil.disk_usage(".").free / 1e9
        print(f"[학습] 파라미터 {n_param/1e6:.0f}M · 체크포인트 {args.save_total_limit}개에 "
              f"약 {need_gb:.1f}GB 필요 · 남은 공간 {free_gb:.1f}GB")
        if free_gb < need_gb * 1.3:
            print(f"[학습] ! 공간이 빠듯합니다. --save-total-limit 1 로 줄이거나 "
                  f"runs/*/checkpoint-* 를 지우세요.")
    except Exception:
        pass

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
        save_total_limit=args.save_total_limit,
        load_best_model_at_end=bool(len(eval_ds)),
        metric_for_best_model="hallu_f1",
        greater_is_better=True,
        report_to=[],
        seed=args.seed,
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
    if not args.no_guard and len(eval_ds):
        trainer.add_callback(CollapseGuard())
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
