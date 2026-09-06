"""질문을 전부 돌려 보고 **시연에 쓸 질문 3개를 골라 준다.**

데모의 성패는 문서보다 질문에 달려 있다. 생성 모델이 지어내지 않으면 형광펜이
안 칠해지고, 그러면 보여줄 것이 없다. 그렇다고 전부 잡히는 것만 보여주면
"고른 것 아니냐"는 질문이 온다. 이 스크립트가 후보를 전부 돌려 보고 그 판단에
필요한 표를 만들어 준다.

임계값도 같이 정한다. RAGTruth 에서 찾은 0.065 를 실제 문서에 그대로 쓰면 안 된다 —
창을 합치는 방식과 문서 길이에 따라 확률 범위가 달라지기 때문이다. 여러 값에서
형광펜 비율이 어떻게 변하는지 보고 고른다.

사용
  python demo/dry_run.py --run ../runs/klue
  python demo/dry_run.py --run ../runs/klue --no-generator   # 생성 없이 검색만 점검
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from app import Generator, Retriever  # noqa: E402
from detector import HalluDetector  # noqa: E402

LOG_PATH = HERE / "logs" / "eval2.jsonl"
REPORT = HERE / "logs" / "dry_run.md"
SWEEP = [0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.35, 0.50]


def load_questions(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        kind, _, q = line.partition("|")
        if q.strip():
            out.append((kind.strip(), q.strip()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="../runs/klue")
    ap.add_argument("--questions", default=str(HERE / "questions.txt"))
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--threshold", type=float, default=0.065)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--agg", default="min2", choices=["min", "min2", "mean"])
    ap.add_argument("--generator", default="google/gemma-3-12b-it")
    ap.add_argument("--no-generator", action="store_true")
    ap.add_argument("--index", default=None,
                    help="쓸 색인 폴더. 생략하면 demo/index")
    args = ap.parse_args()

    qs = load_questions(Path(args.questions))
    print(f"질문 {len(qs)}개")

    det = HalluDetector(args.run, max_length=args.max_length,
                        threshold=args.threshold, agg=args.agg)
    ret = Retriever(args.index)
    gen = None if args.no_generator else Generator(args.generator)
    if gen is None:
        raise SystemExit("[!] --no-generator 로는 답변을 만들 수 없어 시연 판단을 못 합니다.")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with open(LOG_PATH, "a", encoding="utf-8") as logf:
        for i, (kind, q) in enumerate(qs, 1):
            hits = ret(q, k=args.top_k)
            context = "\n\n".join(f"[{h['id']}] {h['text']}" for h in hits)
            answer = gen(context, q)

            spans = det.spans(context, q, answer, threshold=args.threshold)
            ratio = sum(s["end"] - s["start"] for s in spans) / max(len(answer), 1)
            by_thr = {}
            for t in SWEEP:
                sp = det.spans(context, q, answer, threshold=t)
                by_thr[t] = sum(s["end"] - s["start"] for s in sp) / max(len(answer), 1)

            refuse = any(k in answer for k in
                         ("확인되지 않", "찾을 수 없", "나와 있지 않", "언급되지 않", "알 수 없"))
            rows.append({"유형": kind, "질문": q, "답변": answer,
                         "구간수": len(spans), "비율": ratio,
                         "거부": refuse, "임계값별": by_thr})

            logf.write(json.dumps(
                {"time": datetime.now().isoformat(timespec="seconds"), "question": q,
                 "context": context, "answer": answer,
                 "retrieved": [h["id"] for h in hits],
                 "pred_spans": spans, "threshold": args.threshold,
                 "kind": kind}, ensure_ascii=False) + "\n")
            print(f"  [{i:2d}/{len(qs)}] {kind} · 구간 {len(spans)} · {ratio:.1%} · {q[:28]}")

    # ---- 시연 추천 ------------------------------------------------------
    # 잘 잡는 것 = 환각 유발 유형인데 형광펜이 넉넉히 칠해진 것
    catch = sorted([r for r in rows if r["유형"] != "있음" and not r["거부"]],
                   key=lambda r: -r["비율"])
    # 조용한 것 = 문서에 답이 있고 형광펜이 거의 없는 것 (대조군으로 먼저 보여준다)
    quiet = sorted([r for r in rows if r["유형"] == "있음"], key=lambda r: r["비율"])
    miss = [r for r in rows if r["유형"] != "있음" and r["비율"] < 0.05 and not r["거부"]]

    L = ["# 데모 사전 점검", "",
         f"질문 {len(rows)}개 · 임계값 {args.threshold} · 집계 `{args.agg}` · 검색 {args.top_k}청크 · 모델 `{args.run}`", "",
         "## 시연 추천 (이 순서로 보여줄 것)", ""]
    if quiet:
        r = quiet[0]
        L += [f"**1) 먼저 정상 사례** — {r['질문']}", f"   → 형광펜 {r['비율']:.1%}. "
              "문서에 답이 있으면 조용하다는 것을 먼저 보여준다.", ""]
    for n, r in enumerate(catch[:2], 2):
        L += [f"**{n}) 환각을 잡는 사례** — {r['질문']}",
              f"   → 형광펜 {r['비율']:.1%}, 구간 {r['구간수']}개 ({r['유형']} 유형)", ""]
    if miss:
        r = miss[0]
        L += [f"**4) 놓치는 사례(선택)** — {r['질문']}",
              f"   → 형광펜 {r['비율']:.1%}. **한계를 먼저 말하면 방어가 된다.**", ""]

    L += ["## 임계값 고르기", "",
          "창을 합치는 방식(`--agg`)에 따라 확률 범위가 달라지므로 임계값도 함께 바뀐다. "
          "아래에서 **환각 유발 질문의 비율은 높고 '있음' 질문의 비율은 낮은**, "
          "즉 차이가 가장 큰 값을 고른다.", "",
          "| 임계값 | 있음 평균 | 환각유발 평균 | 차이 |", "|---|---|---|---|"]
    for t in SWEEP:
        a = [r["임계값별"][t] for r in rows if r["유형"] == "있음"]
        b = [r["임계값별"][t] for r in rows if r["유형"] != "있음"]
        am = sum(a) / len(a) if a else 0.0
        bm = sum(b) / len(b) if b else 0.0
        L.append(f"| {t} | {am:.1%} | {bm:.1%} | **{bm - am:+.1%}** |")

    L += ["", "## 전체 결과", "",
          "| 유형 | 질문 | 구간 | 형광펜 | 거부 |", "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['유형']} | {r['질문']} | {r['구간수']} | {r['비율']:.1%} | "
                 f"{'예' if r['거부'] else ''} |")

    L += ["", "## 답변 전문", ""]
    for r in rows:
        L += [f"### [{r['유형']}] {r['질문']}", "", f"> {r['답변']}", ""]

    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"\n{'='*58}")
    if quiet:
        print(f"정상 사례  : {quiet[0]['질문']}  ({quiet[0]['비율']:.1%})")
    for r in catch[:2]:
        print(f"환각 잡음  : {r['질문']}  ({r['비율']:.1%})")
    if miss:
        print(f"놓친 사례  : {miss[0]['질문']}  ({miss[0]['비율']:.1%})")
    print(f"{'='*58}")
    print(f"→ {REPORT}")
    print(f"→ {LOG_PATH}  (평가② 라벨링 대상으로 누적됨)")


if __name__ == "__main__":
    main()
