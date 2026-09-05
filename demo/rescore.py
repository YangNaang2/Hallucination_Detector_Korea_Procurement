"""이미 만들어 둔 답변을 다시 채점해 **집계 방식과 임계값을 측정으로 고른다.**

생성을 다시 하지 않는다. `logs/eval2.jsonl` 에 저장된 답변을 그대로 읽어
`min` / `min2` / `mean` × 여러 임계값으로 탐지만 다시 돌린다. GPU 로 gemma 를
올리지 않으므로 2~3분이면 끝난다.

왜 필요한가 — `dry_run.md` 의 "있음 평균 vs 환각유발 평균" 표는 **질문의 유형**으로
묶은 것이라 채점 기준이 될 수 없다. gemma 가 정직하게 답한 경우가 많아서, 유형이
'환각 유발'이어도 답변에 환각이 없는 일이 흔하다. `dryrun_labels.json` 에 답변을
읽고 붙인 라벨이 있고, 이 스크립트는 그것으로 채점한다.

사용
  python demo/rescore.py --run ../runs/klue
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from detector import HalluDetector  # noqa: E402

LOG_PATH = HERE / "logs" / "eval2.jsonl"
LABELS = HERE / "dryrun_labels.json"
REPORT = HERE / "logs" / "rescore.md"

AGGS = ["min", "min2", "mean"]
THRS = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.65]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="../runs/klue")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--log", default=str(LOG_PATH))
    ap.add_argument("--labels", default=str(LABELS))
    ap.add_argument("--pick-agg", default=None, choices=["min", "min2", "mean"],
                    help="건별 표를 이 설정으로 뽑는다. 없으면 F1 최고 설정을 쓴다")
    ap.add_argument("--pick-thr", type=float, default=None)
    args = ap.parse_args()

    labels = {k: v for k, v in json.loads(
        Path(args.labels).read_text(encoding="utf-8")).items() if not k.startswith("_")}

    # 같은 질문이 여러 번 있으면 **마지막 것**을 쓴다 (프롬프트를 고친 뒤의 답변)
    recs: dict[str, dict] = {}
    for line in Path(args.log).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["question"] in labels:
                recs[r["question"]] = r
    print(f"채점 대상 {len(recs)}건 / 라벨 {len(labels)}건")
    missing = set(labels) - set(recs)
    if missing:
        print(f"[!] 로그에 없는 질문 {len(missing)}건은 건너뜁니다.")

    det = HalluDetector(args.run, max_length=args.max_length)

    # 집계 방식별로 토큰 확률을 한 번만 계산해 두고 임계값만 바꿔 가며 채점한다
    cache: dict[str, dict] = {}
    for agg in AGGS:
        det.agg = agg
        for q, r in recs.items():
            p, off = det.token_probs(r["context"], r["question"], r["answer"])
            cache[(agg, q)] = (p, off, r["answer"])
        print(f"  {agg} 계산 완료")

    def flagged(agg: str, q: str, thr: float) -> float:
        p, off, ans = cache[(agg, q)]
        n = sum(e - s for prob, (s, e) in zip(p, off) if prob >= thr and s != e)
        return n / max(len(ans), 1)

    rows = []
    for agg in AGGS:
        for thr in THRS:
            tp = fp = fn = tn = 0
            for q in recs:
                hit = flagged(agg, q, thr) >= 0.03      # 3% 이상 칠해지면 '탐지했다'로 본다
                truth = labels[q]["hallucinated"]
                if hit and truth:
                    tp += 1
                elif hit:
                    fp += 1
                elif truth:
                    fn += 1
                else:
                    tn += 1
            p = tp / (tp + fp) if tp + fp else 0.0
            r_ = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * p * r_ / (p + r_) if p + r_ else 0.0
            rows.append({"agg": agg, "thr": thr, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                         "precision": p, "recall": r_, "f1": f1})

    best = max(rows, key=lambda x: x["f1"])

    # 데모에서는 F1 이 아니라 **정밀도**가 중요하다. 맞는 문장이 빨개지면 화면이 무너진다.
    # 헛짚음 2건 이하인 설정 중 가장 많이 잡는 것을 따로 고른다.
    demo_rows = [x for x in rows if x["fp"] <= 2 and x["tp"] >= 2]
    demo = max(demo_rows, key=lambda x: (x["tp"], x["precision"])) if demo_rows else best

    if args.pick_agg or args.pick_thr is not None:
        pa = args.pick_agg or demo["agg"]
        pt = args.pick_thr if args.pick_thr is not None else demo["thr"]
        picked = next((x for x in rows if x["agg"] == pa and x["thr"] == pt), demo)
    else:
        picked = demo

    L = ["# 재채점 — 집계 방식과 임계값 고르기", "",
         f"답변 {len(recs)}건 · 환각 {sum(1 for q in recs if labels[q]['hallucinated'])}건 "
         f"· 모델 `{args.run}`", "",
         "채점 기준은 `dryrun_labels.json`(답변을 읽고 붙인 라벨)이다. "
         "답변의 3% 이상이 칠해지면 '탐지했다'로 센다.", "",
         f"## F1 최고 = `{best['agg']}` · {best['thr']}  "
         f"(P {best['precision']:.3f} / R {best['recall']:.3f} / F1 {best['f1']:.3f})",
         "",
         f"## ★ 데모 권장 = `{picked['agg']}` · {picked['thr']}  "
         f"(P {picked['precision']:.3f} / R {picked['recall']:.3f} · "
         f"잡음 {picked['tp']} · **헛짚음 {picked['fp']}**)",
         "",
         "> 데모에서는 F1 이 아니라 **정밀도**를 본다. 맞는 문장이 빨개지면 화면이 무너지기 "
         "때문이다. 놓치는 것은 '한계 사례'로 먼저 밝히면 오히려 방어가 된다.", "",
         "| 집계 | 임계값 | 잡음 | 헛짚음 | 놓침 | 정밀도 | 재현율 | F1 |",
         "|---|---|---|---|---|---|---|---|"]
    for x in rows:
        mark = " ←" if x is best else ""
        L.append(f"| {x['agg']} | {x['thr']} | {x['tp']} | {x['fp']} | {x['fn']} | "
                 f"{x['precision']:.3f} | {x['recall']:.3f} | **{x['f1']:.3f}**{mark} |")

    best = picked   # 이하 건별 표는 데모 권장 설정 기준
    L += ["", f"## 건별 ({best['agg']} · {best['thr']})", "",
          "| 실제 | 형광펜 | 질문 | 판단 근거 |", "|---|---|---|---|"]
    for q in sorted(recs, key=lambda q: -flagged(best["agg"], q, best["thr"])):
        ratio = flagged(best["agg"], q, best["thr"])
        truth = labels[q]["hallucinated"]
        mark = {(True, True): "정탐", (False, False): "정상",
                (False, True): "헛짚음", (True, False): "놓침"}[(truth, ratio >= 0.03)]
        L.append(f"| {'환각' if truth else '정상'} → **{mark}** | {ratio:.1%} | {q} | "
                 f"{labels[q]['note']} |")

    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"\n{'='*62}")
    print(f"최적: {best['agg']} · 임계값 {best['thr']}")
    print(f"  정밀도 {best['precision']:.3f} / 재현율 {best['recall']:.3f} / F1 {best['f1']:.3f}")
    print(f"  잡음 {best['tp']} · 헛짚음 {best['fp']} · 놓침 {best['fn']}")
    print(f"{'='*62}")
    print(f"→ {REPORT}")
    print(f"\n데모는 이 설정으로 띄우세요:")
    print(f"  python demo/app.py --run {args.run} --agg {best['agg']} --threshold {best['thr']}")


if __name__ == "__main__":
    main()
