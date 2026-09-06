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


def kappa(a: list[bool], b: list[bool]) -> float:
    """코헨 카파 — 우연히 일치할 확률을 빼고 남는 일치도.

    단순 일치율은 환각 문장이 드물수록 부풀려진다(둘 다 "아니오"만 찍어도 90%가
    나온다). 카파는 그 우연분을 빼므로 라벨 신뢰도의 근거로 쓸 수 있다.
    통상 0.6 이상이면 쓸 만하고, 0.4 아래면 기준을 다시 맞춰야 한다.
    """
    n = len(a)
    if not n:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def merge_labels(paths, on_disagree: str):
    """여러 라벨러의 파일을 하나로 합치고, 겹친 부분의 일치도를 잰다.

    두 사람이 같은 문장을 다르게 봤다면 그 문장은 기본적으로 **채점에서 뺀다**.
    한쪽 손을 들어 주면 그 사람의 기준이 정답이 되어 버리고, 합집합을 쓰면
    환각 문장을 인위적으로 늘려 모델에 불리해진다. 뺀 개수를 함께 보고한다.
    """
    per_file = []
    for p in paths:
        per_file.append(json.loads(Path(p).read_text(encoding="utf-8")))

    votes = {}   # (idx, sent) -> [bool, ...]
    for d in per_file:
        for k, sents in d.items():
            for s in sents:
                votes.setdefault((str(k), int(s["sent"])), []).append(
                    bool(s["hallucinated"]))

    overlap = {k: v for k, v in votes.items() if len(v) > 1}
    agree = sum(1 for v in overlap.values() if len(set(v)) == 1)
    kap = float("nan")
    if len(per_file) == 2 and overlap:
        a = [v[0] for v in overlap.values()]
        b = [v[1] for v in overlap.values()]
        kap = kappa(a, b)

    gold, n_dropped = {}, 0
    for (k, sent), v in votes.items():
        if len(set(v)) > 1:
            if on_disagree == "exclude":
                n_dropped += 1
                continue
            val = any(v) if on_disagree == "union" else v[0]
        else:
            val = v[0]
        gold.setdefault(k, {})[sent] = val

    info = {"라벨러수": len(per_file), "겹친문장": len(overlap),
            "겹친문장_일치": agree, "카파": kap, "불일치제외": n_dropped}
    return gold, info


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="../runs/klue")
    ap.add_argument("--sheet", default=str(LABEL_DIR / "label_sheet.jsonl"))
    ap.add_argument("--labels", nargs="+",
                    default=[str(LABEL_DIR / "labels_done_1.json")],
                    help="라벨러별 파일. 여러 개 주면 합치고 일치도를 잰다")
    ap.add_argument("--on-disagree", default="exclude",
                    choices=["exclude", "union", "first"],
                    help="두 라벨러가 갈린 문장을 어떻게 할지 (기본: 채점에서 제외)")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--translated-f1", type=float, default=None,
                    help="① 번역 테스트셋 macro F1. --run 과 같은 모델의 값을 넣을 것")
    ap.add_argument("--no-window", action="store_true",
                    help="슬라이딩 윈도우를 끄고 학습 때처럼 뒤를 자른다 (대조용)")
    args = ap.parse_args()

    sheet_path = Path(args.sheet)
    label_paths = [Path(p) for p in args.labels]
    for p in [sheet_path] + label_paths:
        if not p.exists():
            raise SystemExit(f"[!] 없습니다: {p}")

    sheet = [json.loads(l) for l in sheet_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    gold_raw, agree_info = merge_labels(label_paths, args.on_disagree)
    print(f"라벨러 {agree_info['라벨러수']}명 · 겹친 문장 {agree_info['겹친문장']}개 중 "
          f"{agree_info['겹친문장_일치']}개 일치", end="")
    if agree_info["겹친문장"]:
        print(f" (일치율 {agree_info['겹친문장_일치'] / agree_info['겹친문장']:.1%}, "
              f"카파 {agree_info['카파']:.3f})")
    else:
        print()
    if agree_info["불일치제외"]:
        print(f"  판단이 갈려 채점에서 뺀 문장 {agree_info['불일치제외']}개")
    gold = {k: [{"sent": s, "hallucinated": v} for s, v in d.items()]
            for k, d in gold_raw.items()}

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
            if s["sent"] not in g:
                continue   # 라벨이 없거나 판단이 갈려 뺀 문장
            truth = g[s["sent"]]
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

    # ① 번역 테스트셋 성능. --translated-f1 로 직접 넣는 쪽이 정확하다 —
    # eval.json 은 임계값 0.5 고정 · 창 없음 기준이라, 창과 튜닝을 적용한
    # 최종 숫자(klue 0.6980 / bge-m3 0.7385)와 다르다. ①과 ②는 반드시
    # **같은 모델 · 같은 추론 설정**에서 나온 값이어야 격차가 의미를 가진다.
    if args.translated_f1 is not None:
        translated = {"f1": args.translated_f1}
    else:
        ev = Path(args.run) / "eval.json"
        translated = json.loads(ev.read_text(encoding="utf-8"))["whole"] if ev.exists() else None

    result = {
        "문장수": total, "환각문장비율": ratio,
        "환각_precision": p1, "환각_recall": r1, "환각_f1": f1,
        "macro_f1": macro, "threshold": args.threshold,
        "sliding_window": not args.no_window,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "라벨일치도": agree_info,
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
