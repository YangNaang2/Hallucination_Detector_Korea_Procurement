"""MSDS 평가 세트 채점 — 사람이 만든 정답지와 모델 예측을 대조한다.

`examples_msds_*.jsonl` (박승형 작성) 을 그대로 읽는다. 각 줄은 문서(`context`)·질문
(`question`)·답변(`answer`)과, 답변 안에서 환각인 구간(`hall_spans`)을 가지고 있다.
**사람이 이미 정답을 표시해 두었으므로 라벨링을 기다리지 않고 바로 채점할 수 있다.**

네 가지로 잰다.

- **토큰 단위 AUROC** — **대표 지표다.** 환각 토큰 비율이 RAGTruth(약 4%)와 이 세트
  (사람이 일부러 심었으므로 훨씬 높다)에서 크게 다른데, **macro F1 은 그 비율에
  흔들리고 AUROC 은 흔들리지 않는다.** 도메인 격차는 반드시 AUROC 으로 말한다.
- **토큰 단위 macro F1** — 벤치마크 표에 실린 것과 같은 형식이지만, 위 이유로
  **비율이 다른 두 세트를 직접 빼면 안 된다.** 참고로만 싣는다.
- **문항 단위 탐지율·오탐률** — 실무 감각에 가깝다. "환각이 든 답변 중 몇 개에
  형광펜이 갔나", "멀쩡한 답변 중 몇 개를 잘못 칠했나".
- **스팬 겹침** — 세트 README 7절이 정한 기준. 경계가 정확히 맞지 않아도 겹치기만
  하면 탐지로 센다. 실사용에서는 "확인할 자리를 가리켰는가"가 중요하지 경계의
  정확도는 부차적이기 때문이다.

**임계값을 이 세트에서 고르면 안 된다.** 같은 데이터에서 기준을 정하고 그 데이터로
채점하면 숫자가 부풀려진다. `--threshold` 에는 학습 쪽에서 정한 값을 넣는다.
`--sweep` 은 민감도를 보기 위한 참고용이며 대표 숫자로 쓰지 않는다.

모델은 문항마다 **한 번만** 돌린다. 토큰 확률을 받아 두고 임계값은 파이썬에서
적용하므로 `--sweep` 을 붙여도 추가 비용이 거의 없다.

사용 예
    python demo/score_msds.py --run runs/bgem3 --files "demo/msds/examples_msds_*.jsonl" \
        --threshold 0.5 --max-length 2048 --baseline-auroc 0.8834 --baseline 0.7385 \
        --sweep --out demo/msds_report.md
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
    """`hall_spans` 를 답변 안의 문자 구간으로 바꾼다.

    `answer_tagged` 가 있으면 `<HAL>` 위치에서 그대로 복원한다. 같은 문자열이
    여러 번 나와도 순서가 어긋나지 않는다.
    """
    ans = row.get("answer", "")
    tagged = row.get("answer_tagged")
    if tagged:
        spans, i = [], 0
        while True:
            o = tagged.find("<HAL>", i)
            if o < 0:
                break
            c = tagged.find("</HAL>", o)
            if c < 0:
                break
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


def spans_from_probs(probs, offsets, thr: float, min_chars: int = 2):
    """`detector.spans` 와 같은 규칙으로 확률을 문자 구간으로 묶는다.

    모델을 다시 돌리지 않고 임계값만 바꿔 볼 수 있게 하려고 떼어 놓았다.
    규칙이 어긋나면 데모의 형광펜과 채점 결과가 달라지므로 함께 고칠 것.
    """
    out, cur_s, cur_e = [], None, None
    for p, (s, e) in zip(probs, offsets):
        if s == e:
            continue
        if p >= thr:
            if cur_s is None:
                cur_s, cur_e = s, e
            elif s - cur_e <= 1:
                cur_e = e
            else:
                out.append((cur_s, cur_e))
                cur_s, cur_e = s, e
        elif cur_s is not None:
            out.append((cur_s, cur_e))
            cur_s = None
    if cur_s is not None:
        out.append((cur_s, cur_e))
    return [(s, e) for s, e in out if e - s >= min_chars]


# --------------------------------------------------------------------- 지표
def f1_from_counts(tp: int, fp: int, fn: int) -> float:
    if tp == 0:
        return 0.0
    p = tp / (tp + fp)
    r = tp / (tp + fn)
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def macro_f1(tp: int, fp: int, fn: int, tn: int) -> tuple[float, float, float]:
    f_pos = f1_from_counts(tp, fp, fn)
    f_neg = f1_from_counts(tn, fn, fp)
    return f_pos, f_neg, (f_pos + f_neg) / 2


def auroc(y: np.ndarray, p: np.ndarray) -> float:
    """순위 기반 AUROC. 동점은 평균 순위로 처리한다."""
    y = np.asarray(y, dtype=bool)
    n_pos, n_neg = int(y.sum()), int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty(len(p), dtype=float)
    sp = p[order]
    i = 0
    while i < len(sp):
        j = i
        while j + 1 < len(sp) and sp[j + 1] == sp[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return (ranks[y].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def auprc(y: np.ndarray, p: np.ndarray) -> float:
    """평균 정밀도(average precision). 무작위 기준선은 양성 비율과 같다."""
    y = np.asarray(y, dtype=bool)
    if y.sum() == 0:
        return float("nan")
    order = np.argsort(-p, kind="mergesort")
    ys = y[order]
    tp = np.cumsum(ys)
    prec = tp / np.arange(1, len(ys) + 1)
    return float(prec[ys].sum() / ys.sum())


class Acc:
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


# --------------------------------------------------------------------- 예측
def predict(rows, det, window):
    """문항마다 모델을 한 번만 돌려 토큰 확률과 정답 라벨을 받아 둔다."""
    cache = []
    for k, r in enumerate(rows, 1):
        ans = r.get("answer", "")
        probs, offsets = det.token_probs(r.get("context", ""), r.get("question", ""),
                                         ans, window=window)
        gold = gold_char_spans(r)
        keep = [(i, (s, e)) for i, (s, e) in enumerate(offsets) if s != e]
        idx = [i for i, _ in keep]
        offs = [o for _, o in keep]
        g = np.array([any(overlaps(o, gs) for gs in gold) for o in offs], dtype=bool)
        cache.append({
            "row": r, "answer": ans, "gold": gold,
            "probs": np.asarray(probs)[idx] if len(probs) else np.zeros(0),
            "offsets": offs, "gold_tok": g,
        })
        if k % 10 == 0:
            print(f"  {k}/{len(rows)}")
    return cache


def score_at(cache, thr):
    """받아 둔 확률에 임계값만 적용해 집계한다. 모델을 다시 돌리지 않는다."""
    per_row = []
    tok_all = Acc()
    tok_by_type = defaultdict(Acc)
    tok_by_mat = defaultdict(Acc)
    span_hit = span_gold = pred_hit = pred_all = 0

    for c in cache:
        r, gold = c["row"], c["gold"]
        pred = spans_from_probs(c["probs"], c["offsets"], thr)

        if len(c["offsets"]):
            g = c["gold_tok"]
            p = np.array([any(overlaps(o, ps) for ps in pred) for o in c["offsets"]],
                         dtype=bool)
            tok_all.add(g, p)
            tok_by_type[r.get("hall_type", "?")].add(g, p)
            tok_by_mat[r.get("_material", "?")].add(g, p)

        span_gold += len(gold)
        span_hit += sum(1 for gs in gold if any(overlaps(gs, ps) for ps in pred))
        pred_all += len(pred)
        pred_hit += sum(1 for ps in pred if any(overlaps(gs, ps) for gs in gold))

        per_row.append({
            "id": r.get("id"), "material": r.get("_material"),
            "hall_type": r.get("hall_type"), "q_type": r.get("q_type"),
            "n_gold": len(gold), "n_pred": len(pred),
            "hit": sum(1 for gs in gold if any(overlaps(gs, ps) for ps in pred)),
            "answer": c["answer"], "gold": gold, "pred": pred,
        })

    return per_row, tok_all, tok_by_type, tok_by_mat, (span_hit, span_gold, pred_hit, pred_all)


def rank_metrics(cache, key=None):
    """임계값과 무관한 지표. key 로 부분집합을 골라 낼 수 있다."""
    ys, ps = [], []
    for c in cache:
        if key is not None and not key(c["row"]):
            continue
        if len(c["offsets"]):
            ys.append(c["gold_tok"])
            ps.append(c["probs"])
    if not ys:
        return float("nan"), float("nan"), 0.0, 0
    y = np.concatenate(ys)
    p = np.concatenate(ps)
    return auroc(y, p), auprc(y, p), float(y.mean()), len(y)


def item_rates(per_row):
    hal = [x for x in per_row if x["n_gold"] > 0]
    ok = [x for x in per_row if x["n_gold"] == 0]
    detected = sum(1 for x in hal if x["hit"] > 0)
    flagged = sum(1 for x in ok if x["n_pred"] > 0)
    return hal, ok, detected, flagged


# --------------------------------------------------------------------- 보고서
def build_report(args, rows, cache, per_row, tok_all, tok_by_type, tok_by_mat,
                 span_stats, sweep):
    hal, ok, detected, flagged = item_rates(per_row)
    span_hit, span_gold, pred_hit, pred_all = span_stats
    f_pos, f_neg, f_macro = tok_all.macro()
    roc, prc, rate, ntok = rank_metrics(cache)
    L = []
    A = L.append

    A("# MSDS 평가 세트 채점 결과")
    A("")
    A(f"- 모델 `{args.run}` · 임계값 **{args.threshold}** · max_length {args.max_length} "
      f"· 집계 `{args.agg}` · 창 {'미사용' if args.no_window else '사용'}")
    A(f"- 문항 {len(rows)}건 (환각 {len(hal)} / 정답 {len(ok)}) · 정답 스팬 {span_gold}개 "
      f"· 평가 토큰 {ntok:,}개")
    A("")
    A("> 임계값은 학습 쪽에서 정한 값을 가져와 고정한 것이다. 이 세트에서 고른 값이 아니다.")
    A("")

    A("## 1. 판별력 — 도메인 격차는 이 숫자로 말한다")
    A("")
    A("| 지표 | 값 |")
    A("|---|---|")
    A(f"| **AUROC** | **{roc:.4f}** |")
    A(f"| AUPRC | {prc:.4f} (무작위 기준선 {rate:.4f}) |")
    A(f"| 환각 토큰 비율 | {100 * rate:.2f}% |")
    A("")
    if args.baseline_auroc:
        A(f"**도메인 격차 — 벤치마크 AUROC {args.baseline_auroc:.4f} → MSDS {roc:.4f} "
          f"= {roc - args.baseline_auroc:+.4f}**")
        A("")
        A("AUROC 은 환각 비율에 흔들리지 않으므로 비율이 다른 두 세트를 비교할 수 있다. "
          "**이 값이 이 프로젝트가 내놓기로 한 숫자다.**")
        A("")

    A("## 2. 임계값 0.5에서의 F1 (참고 — 벤치마크와 직접 빼지 말 것)")
    A("")
    A("| 지표 | 값 |")
    A("|---|---|")
    A(f"| macro F1 | {f_macro:.4f} |")
    A(f"| 환각 클래스 F1 | {f_pos:.4f} |")
    A(f"| 정상 클래스 F1 | {f_neg:.4f} |")
    A("")
    if args.baseline:
        A(f"벤치마크 macro F1 {args.baseline:.4f} 와의 산술 차이는 "
          f"{f_macro - args.baseline:+.4f} 이지만, **환각 토큰 비율이 "
          f"{100 * rate:.1f}% 대 약 4% 로 크게 다르므로 이 뺄셈은 의미가 없다.** "
          "격차는 위의 AUROC 으로 읽는다.")
        A("")

    A("## 3. 문항 단위 — 실무 감각")
    A("")
    A("| 항목 | 값 |")
    A("|---|---|")
    A(f"| 환각 문항 탐지율 | **{detected}/{len(hal)} = {100.0 * detected / max(1, len(hal)):.1f}%** |")
    A(f"| 정답 문항 오탐률 | **{flagged}/{len(ok)} = {100.0 * flagged / max(1, len(ok)):.1f}%** |")
    A("")
    A("오탐률이 함께 있어야 의미가 있다. 모든 문장에 형광펜을 칠하면 탐지율은 100%가 "
      "되지만 오탐률도 100%가 되어 아무 쓸모가 없다.")
    A("")

    A("## 4. 스팬 겹침")
    A("")
    A("| 항목 | 값 |")
    A("|---|---|")
    A(f"| 정답 스팬 중 잡힌 것 (재현) | {span_hit}/{span_gold} = {100.0 * span_hit / max(1, span_gold):.1f}% |")
    A(f"| 예측 스팬 중 맞은 것 (정밀) | {pred_hit}/{pred_all} = {100.0 * pred_hit / max(1, pred_all):.1f}% |")
    A("")

    A("## 5. 환각 유형별 — 무엇을 못 잡는가")
    A("")
    A("| 유형 | 문항 | 문항 탐지율 | AUROC | 토큰 macro F1 |")
    A("|---|---:|---:|---:|---:|")
    for t in sorted(tok_by_type, key=lambda k: -tok_by_type[k].n):
        sub = [x for x in per_row if x["hall_type"] == t]
        subhal = [x for x in sub if x["n_gold"] > 0]
        if subhal:
            rt = f"{100.0 * sum(1 for x in subhal if x['hit'] > 0) / len(subhal):.0f}%"
        else:
            rt = f"(오탐 {sum(1 for x in sub if x['n_pred'] > 0)}/{len(sub)})"
        r_roc, _, _, _ = rank_metrics(cache, key=lambda r, t=t: r.get("hall_type") == t)
        rs = "—" if np.isnan(r_roc) else f"{r_roc:.4f}"
        A(f"| {t} | {len(sub)} | {rt} | {rs} | {tok_by_type[t].macro()[2]:.4f} |")
    A("")
    A("유형 하나에 문항이 8개 미만이면 두세 개 차이로 비율이 크게 흔들린다. "
      "그런 줄은 참고로만 읽는다. 정답 줄의 AUROC 은 환각 토큰이 없어 계산되지 않는다.")
    A("")

    if len(tok_by_mat) > 1:
        A("## 6. 물질별 — 문서 하나에서만 되는 것인가")
        A("")
        A("| 물질 | 문항 | AUROC | 토큰 macro F1 |")
        A("|---|---:|---:|---:|")
        for m in sorted(tok_by_mat):
            n = sum(1 for x in per_row if x["material"] == m)
            m_roc, _, _, _ = rank_metrics(cache, key=lambda r, m=m: r.get("_material") == m)
            ms = "—" if np.isnan(m_roc) else f"{m_roc:.4f}"
            A(f"| {m} | {n} | {ms} | {tok_by_mat[m].macro()[2]:.4f} |")
        A("")
        A("물질 사이의 차이가 크면 성능이 특정 문서의 성격에 기대고 있다는 뜻이다.")
        A("")

    if sweep:
        A("## 7. 임계값 민감도 (참고용 — 대표 숫자로 쓰지 않는다)")
        A("")
        A("| 임계값 | 토큰 macro F1 | 문항 탐지율 | 문항 오탐률 |")
        A("|---:|---:|---:|---:|")
        for t, mf, dr, fr in sweep:
            A(f"| {t:.2f} | {mf:.4f} | {dr:.0f}% | {fr:.0f}% |")
        A("")
        A("AUROC 은 임계값과 무관하므로 이 표에 없다. 이 표를 보고 임계값을 고르면 "
          "그 숫자는 부풀려진 것이다.")
        A("")

    A("## 8. 놓친 문항 — 발표에 쓸 사례를 여기서 고른다")
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

    A("## 9. 잘못 칠한 문항 — 오탐")
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
    ap.add_argument("--run", required=True, help="학습된 모델 폴더 (예: runs/bgem3)")
    ap.add_argument("--files", nargs="+", required=True, help="평가 jsonl 경로 또는 glob")
    ap.add_argument("--threshold", type=float, required=True,
                    help="학습 쪽에서 정한 값을 넣는다. 이 세트에서 고르지 말 것")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--agg", default="min2", choices=["min", "min2", "mean"])
    ap.add_argument("--no-window", action="store_true")
    ap.add_argument("--baseline-auroc", type=float, default=None,
                    help="비교할 벤치마크 AUROC (bge-m3 0.8834)")
    ap.add_argument("--baseline", type=float, default=None,
                    help="비교할 벤치마크 macro F1 (bge-m3 0.7385). 참고용으로만 쓰인다")
    ap.add_argument("--sweep", action="store_true")
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

    cache = predict(rows, det, not args.no_window)
    per_row, tok_all, tok_by_type, tok_by_mat, span_stats = score_at(cache, args.threshold)

    sweep = []
    if args.sweep:
        for t in [0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7]:
            pr, ta, _, _, _ = score_at(cache, t)
            h, o, dd, ff = item_rates(pr)
            sweep.append((t, ta.macro()[2], 100.0 * dd / max(1, len(h)),
                          100.0 * ff / max(1, len(o))))

    report = build_report(args, rows, cache, per_row, tok_all, tok_by_type,
                          tok_by_mat, span_stats, sweep)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    io.open(args.out, "w", encoding="utf-8").write(report)

    roc, prc, rate, ntok = rank_metrics(cache)
    hal, ok, detected, flagged = item_rates(per_row)
    print()
    print(f"AUROC        : {roc:.4f}   (벤치마크 {args.baseline_auroc or '-'})")
    print(f"AUPRC        : {prc:.4f}   (무작위 {rate:.4f})")
    print(f"토큰 macro F1: {tok_all.macro()[2]:.4f}  ※ 비율이 달라 직접 비교 금지")
    print(f"문항 탐지율  : {detected}/{len(hal)} = {100.0 * detected / max(1, len(hal)):.1f}%")
    print(f"문항 오탐률  : {flagged}/{len(ok)} = {100.0 * flagged / max(1, len(ok)):.1f}%")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
