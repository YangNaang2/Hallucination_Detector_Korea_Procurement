"""평가② 채점 — **이 프로젝트의 핵심 숫자를 만드는 파일이다.**

번역 테스트셋에서의 성능(①)과 진짜 한국어 문서에서의 성능(②)을 나란히 놓고
**격차 = ① − ②** 를 낸다. 이 격차가 "번역해서 만든 모델이 진짜 한국어 문서에서
통하는가"에 대한 답이고, 아무도 아직 답하지 않은 질문이다.

문장 단위로 채점한다. 모델은 토큰 단위로 예측하므로, **한 문장 안에 환각 토큰이
하나라도 있으면 그 문장을 환각으로 본다**(구간 탐지기를 문장 판정기로 올리는 표준
방식). 라벨러도 문장 단위로 판단했으므로 양쪽이 같은 단위에서 만난다.

사용
  python demo/score_eval2.py --run ../runs/klue --threshold 0.5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from detector import HalluDetector  # noqa: E402

LABEL_DIR = HERE / "labels"


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="../runs/klue")
    ap.add_argument("--sheet", default=str(LABEL_DIR / "label_sheet.jsonl"))
    ap.add_argument("--labels", default=str(LABEL_DIR / "labels_done.json"))
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--no-window", action="store_true",
                    help="슬라이딩 윈도우를 끄고 학습 때처럼 뒤를 자른다 (대조용)")
    args = ap.parse_args()

    sheet_path, label_path = Path(args.sheet), Path(args.labels)
    for p in (sheet_path, label_path):
        if not p.exists():
            raise SystemExit(f"[!] 없습니다: {p}")

    sheet = [json.loads(l) for l in sheet_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    gold = json.loads(label_path.read_text(encoding="utf-8"))

    det = HalluDetector(args.run, max_length=args.max_length, threshold=args.threshold)

    tp = fp = fn = tn = 0
    per_item = []
    for item in sheet:
        key = str(item["idx"])
        if key not in gold:
            continue
        g = {int(d["sent"]): bool(d["hallucinated"]) for d in gold[key]}
        spans = det.spans(item["context"], item["question"], item["answer"],
                          threshold=args.threshold, window=not args.no_window)

        item_tp = item_fp = item_fn = 0
        for s in item["sentences"]:
            truth = g.get(s["sent"], False)
            pred = any(sp["start"] < s["end"] and sp["end"] > s["start"] for sp in spans)
            if pred and truth:
                tp += 1; item_tp += 1
            elif pred and not truth:
                fp += 1; item_fp += 1
            elif truth:
                fn += 1; item_fn += 1
            else:
                tn += 1
        per_item.append({"idx": item["idx"], "question": item["question"],
                         "tp": item_tp, "fp": item_fp, "fn": item_fn})

    total = tp + fp + fn + tn
    if not total:
        raise SystemExit("[!] 겹치는 라벨이 없습니다. idx 가 맞는지 확인하세요.")

    p1, r1, f1 = prf(tp, fp, fn)
    p0, r0, f0 = prf(tn, fn, fp)
    macro = (f0 + f1) / 2
    ratio = (tp + fn) / total

    # ① 번역 테스트셋 성능 — 같은 run 의 eval.json 에서 읽어 온다
    ev = Path(args.run) / "eval.json"
    translated = json.loads(ev.read_text(encoding="utf-8"))["whole"] if ev.exists() else None

    result = {
        "문장수": total, "환각문장비율": ratio,
        "환각_precision": p1, "환각_recall": r1, "환각_f1": f1,
        "macro_f1": macro, "threshold": args.threshold,
        "sliding_window": not args.no_window,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }
    if translated:
        result["번역테스트셋_macro_f1"] = translated["f1"]
        result["격차"] = translated["f1"] - macro

    out = LABEL_DIR / "eval2_result.json"
    out.write_text(json.dumps({"요약": result, "건별": per_item}, indent=2,
                              ensure_ascii=False), encoding="utf-8")

    print(f"\n{'='*58}")
    print(f"평가② — 진짜 한국어 문서 (문장 {total}개, 환각 {ratio:.1%})")
    print(f"  환각 문장  P {p1:.4f} / R {r1:.4f} / F1 {f1:.4f}")
    print(f"  macro F1   {macro:.4f}")
    if translated:
        print(f"\n① 번역 테스트셋 macro F1 : {translated['f1']:.4f}")
        print(f"② 진짜 문서   macro F1 : {macro:.4f}")
        print(f"\n★ 격차 = ① − ② = {translated['f1'] - macro:+.4f}")
        print("  ← 이 숫자가 발표의 핵심입니다. 작을수록 번역 학습이 실제로 통한다는 뜻입니다.")
    print(f"{'='*58}\n→ {out}")


if __name__ == "__main__":
    main()
