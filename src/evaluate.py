"""학습된 모델을 토큰 단위로 평가하고 과제별로 분해한다 (논문 Table II 형식).

사용
  python -m src.evaluate --run runs/gte-multilingual-base
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict

import numpy as np
import torch
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score
from torch.utils.data import DataLoader
from transformers import AutoModelForTokenClassification, AutoTokenizer

import config as C
from src.dataset import Collator, HalluDataset


def scores(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    y_pred = (y_prob >= 0.5).astype(int)
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0)
    d = {"n_tokens": int(len(y_true)),
         "hallu_ratio": float(y_true.mean()),
         "precision": float(p), "recall": float(r), "f1": float(f1)}
    if len(np.unique(y_true)) == 2:
        d["auroc"] = float(roc_auc_score(y_true, y_prob))
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="학습 결과 디렉터리")
    ap.add_argument("--data", default=str(C.WORK_DIR / "ko_ragtruth.jsonl"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--max-length", type=int, default=C.MAX_LENGTH)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--trust-remote-code", action="store_true")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.run, trust_remote_code=args.trust_remote_code)
    model = AutoModelForTokenClassification.from_pretrained(
        args.run, trust_remote_code=args.trust_remote_code).to(device).eval()

    ds = HalluDataset(args.data, tok, args.max_length, split=args.split)
    print(f"{args.split} {len(ds):,} 건")
    if not len(ds):
        raise SystemExit("[!] 평가 데이터가 비었습니다.")

    # task_type 을 보존하려고 배치를 직접 돌린다
    collate = Collator(tok)
    order = list(range(len(ds)))
    all_true, all_prob, all_task = [], [], []

    with torch.no_grad():
        for i in range(0, len(order), args.batch):
            chunk = [ds[j] for j in order[i:i + args.batch]]
            batch = collate(chunk)
            labels = batch.pop("labels")
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16,
                                enabled=(device == "cuda")):
                logits = model(**batch).logits.float().cpu()
            prob = torch.softmax(logits, dim=-1)[..., C.LABEL_HALLUCINATED]
            for row, (lab, pr) in enumerate(zip(labels, prob)):
                m = lab != C.IGNORE_INDEX
                if not m.any():
                    continue
                all_true.append(lab[m].numpy())
                all_prob.append(pr[m].numpy())
                all_task.append(chunk[row]["task_type"])
            if (i // args.batch) % 50 == 0:
                print(f"  {i:,}/{len(order):,}", flush=True)

    results = {"whole": scores(np.concatenate(all_true), np.concatenate(all_prob))}

    by_task = defaultdict(lambda: ([], []))
    for t, p, task in zip(all_true, all_prob, all_task):
        by_task[task][0].append(t)
        by_task[task][1].append(p)
    for task, (ts, ps) in sorted(by_task.items()):
        results[task] = scores(np.concatenate(ts), np.concatenate(ps))

    out = f"{args.run}/eval.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'과제':<16}{'Precision':>11}{'Recall':>9}{'F1':>9}{'AUROC':>9}")
    print("-" * 54)
    for k, v in results.items():
        print(f"{k:<16}{v['precision']:>11.4f}{v['recall']:>9.4f}"
              f"{v['f1']:>9.4f}{v.get('auroc', float('nan')):>9.4f}")
    print("\n터키어 기준선 (Turk-LettuceDetect, ModernBERT-base-tr)")
    print("  Whole 0.7266 / QA 0.7588 / Data2txt 0.7391 / Summary 0.6007")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
