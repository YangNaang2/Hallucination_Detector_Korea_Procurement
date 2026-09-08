"""MSDS 평가 세트 채점 — 사람이 만든 정답지와 모델 예측을 대조한다.

`examples_msds_*.jsonl` (박승형 작성) 을 그대로 읽는다. 각 줄은 문서(`context`)·질문
(`question`)·답변(`answer`)과, 답변 안에서 환각인 구간(`hall_spans`)을 가지고 있다.
**사람이 이미 정답을 표시해 두었으므로 라벨링을 기다리지 않고 바로 채점할 수 있다.**

세 가지 단위로 잰다. 셋 다 필요하다.

- **토큰 단위 macro F1** — RAGTruth 벤치마크에서 쓴 것과 같은 지표다. 유일하게
  `bge-m3 0.7385` 같은 기존 숫자와 나란히 놓을 수 있다. 도메인 격차는 이걸로 말한다.
- **문항 단위 탐지율·오탐률** — 실무 감각에 가깝다. "환각이 든 답변 중 몇 개에
  형광펜이 갔나", "멀쩡한 답변 중 몇 개를 잘못 칠했나".
- **스팬 겹침** — 승형이 README 7절이 정한 기준. 경계가 정확히 맞지 않아도
  겹치기만 하면 탐지로 센다. 실사용에서는 "확인할 자리를 가리켰는가"가 중요하지
  경계의 정확도는 부차적이기 때문이다.

**임계값을 이 세트에서 고르면 안 된다.** 같은 데이터에서 기준을 정하고 그 데이터로
채점하면 숫자가 부풀려진다. `--threshold` 는 학습 쪽에서 정한 값을 그대로 넣는다
(klue 0.5 · xlmr 0.268 · bge-m3 는 별도 산출). `--sweep` 은 민감도를 보기 위한
참고용이며 대표 숫자로 쓰지 않는다.

사용 예
    python demo/score_msds.py --run runs/klue --files "demo/msds/examples_msds_*.jsonl" \
        --threshold 0.5 --max-length 512 --out demo/msds_report.md
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detector import HalluDetector  # noqa: E402


# --------------------------------------------------------------------- 데이터
def load_rows(patterns: list[str]) -> list[dict]:
    rows = []
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            mat = Path(path).stem.replace("examples_msds_", "") or Path(path).stem
            with io.open(path, encoding="utf-8") as f:
                for ln, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                    except Exception as e:
                        print(f"[건너뜀] {path}:{ln} JSON 오류 — {e}")
                        continue
                    r["_material"] = r.get("material") or mat
                    r["_src"] = path
                    rows.append(r)
    return rows


def gold_char_spans(row: dict) -> list[tuple[int, int]]:
    """`hall_spans` 문자열을 답변 안의 문자 구간으로 바꾼다.

    같은 문자열이 여러 번 나오면 앞에서부터 차례로 하나씩 잡는다. 태그가 붙은
    `answer_tagged` 가 있으면 그쪽에서 순서를 그대로 복원할 수 있으므로 우선 쓴다.
    """
    ans = row.get("answer", "")
    tagged = row.get("answer_tagged")
    if tagged:
        spans, pos, cur = [], 0, 0
        i = 0
        while True:
            o = tagged.find("<HAL>", i)
            if o < 0:
                break
            c = tagged.find("</HAL>", o)
            if c < 0:
                break
            # 태그 앞까지의 평문 길이 = 답변에서의 시작 위치
            plain_before = tagged[:o].replace("<HAL>", "").replace("</HAL>", "")
            inner = tagged[o + 5:c]
            spans.append((len(plain_before), len(plain_before) + len(inner)))
            i = c + 6
        if spans:
            return spans

    spans, cursor = [], 0
    for s in row.get("hall_spans", []) or []:
        idx = ans.find(s, cursor)
        if idx < 0:
            idx = ans.find(s)
        if idx < 0:
            continue
        spans.append((idx, idx + len(s)))
        cursor = idx + len(s)
    return spans


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


# --------------------------------------------------------------------- 지표
def f1_from_counts(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def macro_f1(tp: int, fp: int, fn: int, tn: int) -> tuple[float, float, float]:
    """환각 클래스 F1, 정상 클래스 F1, 그 평균."""
    f_pos = f1_from_counts(tp, fp, fn)
    f_neg = f1_from_counts(tn, fn, fp)
    return f_pos, f_neg, (f_pos + f_neg) / 2


class Acc:
    """토큰 단위 혼동행렬 하나를 누적한다."""

    def __init__(self):
        self.tp = self.fp = self.fn = self.tn = 0

    def add(self, gold: np.ndarray, pred: np.ndarray):
        self.tp += int(np.sum(gold & pred))
        self.fp += int(np.sum(~gold & pred))
        self.fn += int(np.sum(gold & ~pred))
        self.tn += int(np.sum(~gold & ~pred))

    @property
    def n(self):
        return self.tp + self.fp + self.fn + self.tn

    def macro(self):
        return macro_f1(self.tp, self.fp, self.fn, self.tn)


# --------------------------------------------------------------------- 채점
def score(rows, det, thr, window):
    """행마다 예측을 만들고 필요한 집계를 모두 채운다."""
    per_row = []
    tok_all = Acc()
    tok_by_type = defaultdict(Acc)
    tok_by_mat = defaultdict(Acc)

    span_hit = span_gold = 0          # 정답 스팬 중 겹친 것
    pred_hit = pred_all = 0           # 예측 스팬 중 정답과 겹친 것

    for r in rows:
        ans = r.get("answer", "")
        gold = gold_char_spans(r)
        pred = [(d["start"], d["end"]) for d in
                det.spans(r.get("context", ""), r.get("question", ""), ans,
                          threshold=thr, window=window)]

        # --- 토큰 단위 (학습 때와 같은 토크나이저로 자른다) ---
        enc = det.tok(ans, add_special_tokens=False, return_offsets_mapping=True)
        offs = [(s, e) for s, e in enc["offset_mapping"] if s != e]
        if offs:
            g = np.array([any(overlaps((s, e), gs) for gs in gold) for s, e in offs])
            p = np.array([any(overlaps((s, e), ps) for ps in pred) for s, e in offs])
            tok_all.add(g, p)
            tok_by_type[r.get("hall_type", "?")].add(g, p)
            tok_by_mat[r.get("_material", "?")].add(g, p)

        # --- 스팬 겹침 ---
        span_gold += len(gold)
        span_hit += sum(1 for gs in gold if any(overlaps(gs, ps) for ps in pred))
        pred_all += len(pred)
        pred_hit += sum(1 for ps in pred if any(overlaps(gs, ps) for gs in gold))

        per_row.append({
            "id": r.get("id"), "material": r.get("_material"),
            "hall_type": r.get("hall_type"), "q_type": r.get("q_type"),
            "n_gold": len(gold), "n_pred": len(pred),
            "hit": sum(1 for gs in gold if any(overlaps(gs, ps) for ps in pred)),
            "answer": ans, "gold": gold, "pred": pred,
        })

    return per_row, tok_all, tok_by_type, tok_by_mat, (span_hit, span_gold, pred_hit, pred_all)


def item_rates(per_row):
    """문항 단위 — 환각 문항 탐지율과 정답 문항 오탐률."""
    hal = [x for x in per_row if x["n_gold"] > 0]
    ok = [x for x in per_row if x["n_gold"] == 0]
    detected = sum(1 for x in hal if x["hit"] > 0)
    flagged = sum(1 for x in ok if x["n_pred"] > 0)
    return hal, ok, detected, flagged


# --------------------------------------------------------------------- 보고서
def build_report(args, rows, per_row, tok_all, tok_by_type, tok_by_mat, span_stats, sweep):
    hal, ok, detected, flagged = item_rates(per_row)
    span_hit, span_gold, pred_hit, pred_all = span_stats
    f_pos, f_neg, f_macro = tok_all.macro()
    L = []
    A = L.append

    A("# MSDS 평가 세트 채점 결과")
    A("")
    A(f"- 모델 `{args.run}` · 임계값 **{args.threshold}** · max_length {args.max_length} "
      f"· 집계 `{args.agg}` · 창 {'사용' if not args.no_window else '미사용'}")
    A(f"- 문항 {len(rows)}건 (환각 {len(hal)} / 정답 {len(ok)}) · 정답 스팬 {span_gold}개")
    A("")
    A("> 임계값은 학습 쪽에서 정한 값을 가져와 고정한 것이다. "
      "이 세트에서 고른 값이 아니다.")
    A("")

    A("## 1. 토큰 단위 — 벤치마크와 비교 가능한 숫자")
    A("")
    A("| 지표 | 값 |")
    A("|---|---|")
    A(f"| **macro F1** | **{f_macro:.4f}** |")
    A(f"| 환각 클래스 F1 | {f_pos:.4f} |")
    A(f"| 정상 클래스 F1 | {f_neg:.4f} |")
    A(f"| 환각 토큰 비율 | {100.0 * (tok_all.tp + tok_all.fn) / max(1, tok_all.n):.2f}% |")
    A(f"| 평가 토큰 수 | {tok_all.n:,} |")
    A("")
    if args.baseline:
        A(f"**도메인 격차 — 벤치마크 {args.baseline:.4f} → MSDS {f_macro:.4f} "
          f"= {f_macro - args.baseline:+.4f}**")
        A("")
        A("이 값이 이 프로젝트가 내놓기로 한 숫자다. 번역해서 만든 학습 자료가 "
          "실제 한국어 문서에서 얼마나 버티는지를 나타낸다.")
        A("")

    A("## 2. 문항 단위 — 실무 감각")
    A("")
    A("| 항목 | 값 |")
    A("|---|---|")
    A(f"| 환각 문항 탐지율 | **{detected}/{len(hal)} = {100.0 * detected / max(1, len(hal)):.1f}%** |")
    A(f"| 정답 문항 오탐률 | **{flagged}/{len(ok)} = {100.0 * flagged / max(1, len(ok)):.1f}%** |")
    A("")
    A("오탐률이 함께 있어야 의미가 있다. 모든 문장에 형광펜을 칠하면 탐지율은 "
      "100%가 되지만 오탐률도 100%가 되어 아무 쓸모가 없다.")
    A("")

    A("## 3. 스팬 겹침 — 경계가 정확하지 않아도 겹치면 성공")
    A("")
    A("| 항목 | 값 |")
    A("|---|---|")
    A(f"| 정답 스팬 중 잡힌 것 | {span_hit}/{span_gold} = {100.0 * span_hit / max(1, span_gold):.1f}% |")
    A(f"| 예측 스팬 중 맞은 것 | {pred_hit}/{pred_all} = {100.0 * pred_hit / max(1, pred_all):.1f}% |")
    A("")

    A("## 4. 환각 유형별 — 무엇을 못 잡는가")
    A("")
    A("| 유형 | 문항 | 문항 탐지율 | 토큰 macro F1 |")
    A("|---|---:|---:|---:|")
    for t in sorted(tok_by_type, key=lambda k: -tok_by_type[k].n):
        sub = [x for x in per_row if x["hall_type"] == t]
        subhal = [x for x in sub if x["n_gold"] > 0]
        if subhal:
            rate = f"{100.0 * sum(1 for x in subhal if x['hit'] > 0) / len(subhal):.0f}%"
        else:
            flag = sum(1 for x in sub if x["n_pred"] > 0)
            rate = f"(오탐 {flag}/{len(sub)})"
        A(f"| {t} | {len(sub)} | {rate} | {tok_by_type[t].macro()[2]:.4f} |")
    A("")
    A("유형 하나에 문항이 8개 미만이면 두세 개 차이로 비율이 크게 흔들린다. "
      "그런 줄은 참고로만 읽는다.")
    A("")

    if len(tok_by_mat) > 1:
        A("## 5. 물질별 — 문서 하나에서만 되는 것인가")
        A("")
        A("| 물질 | 문항 | 토큰 macro F1 |")
        A("|---|---:|---:|")
        for m in sorted(tok_by_mat):
            n = sum(1 for x in per_row if x["material"] == m)
            A(f"| {m} | {n} | {tok_by_mat[m].macro()[2]:.4f} |")
        A("")
        A("물질 사이의 차이가 크면 성능이 특정 문서의 성격에 기대고 있다는 뜻이다.")
        A("")

    if sweep:
        A("## 6. 임계값 민감도 (참고용 — 대표 숫자로 쓰지 않는다)")
        A("")
        A("| 임계값 | 토큰 macro F1 | 문항 탐지율 | 문항 오탐률 |")
        A("|---:|---:|---:|---:|")
        for t, mf, dr, fr in sweep:
            A(f"| {t:.2f} | {mf:.4f} | {dr:.0f}% | {fr:.0f}% |")
        A("")
        A("이 표를 보고 임계값을 고르면 그 숫자는 부풀려진 것이다. "
          "고르려면 별도의 조정용 데이터가 필요하다.")
        A("")

    A("## 7. 놓친 문항 — 발표에 쓸 사례를 여기서 고른다")
    A("")
    miss = [x for x in per_row if x["n_gold"] > 0 and x["hit"] == 0]
    if not miss:
        A("놓친 문항 없음.")
    for x in miss[:15]:
        A(f"**{x['id']}** · {x['hall_type']} · {x['q_type']}")
        A("")
        A(f"> {x['answer']}")
        A("")
        A(f"정답 구간: {[x['answer'][s:e] for s, e in x['gold']]}")
        A("")
    if len(miss) > 15:
        A(f"… 외 {len(miss) - 15}건")
    A("")

    A("## 8. 잘못 칠한 문항 — 오탐")
    A("")
    fp_rows = [x for x in per_row if x["n_gold"] == 0 and x["n_pred"] > 0]
    if not fp_rows:
        A("오탐 없음.")
    for x in fp_rows[:15]:
        A(f"**{x['id']}** · {x['q_type']}")
        A("")
        A(f"> {x['answer']}")
        A("")
        A(f"잘못 칠한 구간: {[x['answer'][s:e] for s, e in x['pred']]}")
        A("")
    if len(fp_rows) > 15:
        A(f"… 외 {len(fp_rows) - 15}건")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="학습된 모델 폴더 (예: runs/klue)")
    ap.add_argument("--files", nargs="+", required=True,
                    help="평가 jsonl 경로 또는 glob 패턴")
    ap.add_argument("--threshold", type=float, required=True,
                    help="학습 쪽에서 정한 값을 넣는다. 이 세트에서 고르지 말 것")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--agg", default="min2", choices=["min", "min2", "mean"],
                    help="슬라이딩 창 집계. 긴 실제 문서에는 min2 를 권한다")
    ap.add_argument("--no-window", action="store_true", help="슬라이딩 창을 쓰지 않는다")
    ap.add_argument("--baseline", type=float, default=None,
                    help="비교할 벤치마크 macro F1 (예: bge-m3 0.7385)")
    ap.add_argument("--sweep", action="store_true", help="임계값 민감도 표를 붙인다")
    ap.add_argument("--trust-remote-code", action="store_true")
    ap.add_argument("--out", default="demo/msds_report.md")
    args = ap.parse_args()

    rows = load_rows(args.files)
    if not rows:
        print("평가할 줄이 없다. --files 경로를 확인할 것.")
        return
    print(f"[읽음] {len(rows)}문항")

    det = HalluDetector(args.run, max_length=args.max_length,
                        threshold=args.threshold, agg=args.agg,
                        trust_remote_code=args.trust_remote_code)
    print(f"[모델] {args.run} · {det.device}")

    per_row, tok_all, tok_by_type, tok_by_mat, span_stats = score(
        rows, det, args.threshold, not args.no_window)

    sweep = []
    if args.sweep:
        for t in [0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7]:
            pr, ta, _, _, _ = score(rows, det, t, not args.no_window)
            hal, ok, dd, ff = item_rates(pr)
            sweep.append((t, ta.macro()[2],
                          100.0 * dd / max(1, len(hal)),
                          100.0 * ff / max(1, len(ok))))
            print(f"  임계값 {t:.2f} → macro F1 {ta.macro()[2]:.4f}")

    report = build_report(args, rows, per_row, tok_all, tok_by_type,
                          tok_by_mat, span_stats, sweep)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    io.open(args.out, "w", encoding="utf-8").write(report)

    hal, ok, detected, flagged = item_rates(per_row)
    print()
    print(f"토큰 macro F1 : {tok_all.macro()[2]:.4f}")
    print(f"문항 탐지율   : {detected}/{len(hal)} = {100.0 * detected / max(1, len(hal)):.1f}%")
    print(f"문항 오탐률   : {flagged}/{len(ok)} = {100.0 * flagged / max(1, len(ok)):.1f}%")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
