"""MSDS 평가 세트 채점 — 이 컴퓨터에서 숫자를 직접 뽑는다.

`msds/` 폴더의 `examples_msds_*.jsonl` 을 모두 읽어 채점하고 `채점결과.md` 를 만든다.
파일을 새로 넣으면(자일렌·메탄올 등) 자동으로 함께 채점된다.

    python 채점.py                 # 기본 임계값 0.5
    python 채점.py --threshold 0.35

**임계값을 결과를 보고 고르면 안 된다.** 같은 데이터로 기준을 정하고 채점하면
숫자가 부풀려진다. 기본값 0.5 를 그대로 쓰고, 바꿔야 한다면 담당자와 상의할 것.

무엇을 보는가
- **AUROC** — 대표 지표. 환각 비율이 달라도 비교할 수 있다. 워크스테이션에서 잰
  klue 의 값은 톨루엔 52문항에서 **0.7941** 이었다. 크게 다르면 알려 줄 것.
- **문항 탐지율 / 오탐률** — 오탐이 함께 있어야 의미가 있다. 전부 칠하면
  탐지율은 100% 가 되지만 오탐률도 100% 가 된다.
- **유형별** — 어떤 종류를 못 잡는지. 지금까지는 숫자변조가 가장 약했다.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from app_cpu import Detector, MODEL_DIR

HERE = Path(__file__).resolve().parent
MSDS_DIR = HERE / "msds"


# --------------------------------------------------------------------- 자료
def load_rows():
    rows = []
    for path in sorted(MSDS_DIR.glob("examples_msds_*.jsonl")):
        mat = path.stem.replace("examples_msds_", "")
        for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception as e:
                print(f"[건너뜀] {path.name}:{ln} — {e}")
                continue
            r["_material"] = mat
            rows.append(r)
    return rows


def gold_spans(row):
    """`answer_tagged` 의 <HAL> 위치에서 정답 구간을 복원한다."""
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
            before = tagged[:o].replace("<HAL>", "").replace("</HAL>", "")
            inner = tagged[o + 5:c]
            spans.append((len(before), len(before) + len(inner)))
            i = c + 6
        if spans:
            return spans
    spans, cur = [], 0
    for s in row.get("hall_spans", []) or []:
        k = ans.find(s, cur)
        if k < 0:
            k = ans.find(s)
        if k < 0:
            continue
        spans.append((k, k + len(s)))
        cur = k + len(s)
    return spans


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def auroc(y, p):
    y = np.asarray(y, dtype=bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0:
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
    return (ranks[y].sum() - npos * (npos + 1) / 2.0) / (npos * nneg)


def spans_from_probs(probs, offsets, thr, min_chars=2):
    out, cur = [], None
    for p, (s, e) in zip(probs, offsets):
        if s == e:
            continue
        if p >= thr:
            if cur is None:
                cur = [s, e]
            elif s - cur[1] <= 1:
                cur[1] = e
            else:
                out.append(tuple(cur))
                cur = [s, e]
        elif cur is not None:
            out.append(tuple(cur))
            cur = None
    if cur is not None:
        out.append(tuple(cur))
    return [(s, e) for s, e in out if e - s >= min_chars]


# --------------------------------------------------------------------- 본체
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="결과를 보고 고치지 말 것. 기본 0.5")
    ap.add_argument("--out", default="채점결과.md")
    args = ap.parse_args()

    if not (MODEL_DIR / "config.json").exists():
        raise SystemExit(f"[!] 모델이 없습니다: {MODEL_DIR}")
    rows = load_rows()
    if not rows:
        raise SystemExit(f"[!] {MSDS_DIR} 에 examples_msds_*.jsonl 이 없습니다.")
    print(f"[읽음] {len(rows)}문항")

    det = Detector(MODEL_DIR)
    print("모델을 불러왔습니다. 채점을 시작합니다 (CPU 라 몇 분 걸립니다)...")

    ys, ps = [], []
    per_row = []
    by_type = defaultdict(lambda: {"n": 0, "hal": 0, "hit": 0, "fp": 0})

    for k, r in enumerate(rows, 1):
        ans = r.get("answer", "")
        probs, offsets = det.token_probs(r.get("context", ""), r.get("question", ""), ans)
        keep = [(i, o) for i, o in enumerate(offsets) if o[0] != o[1]]
        idx = [i for i, _ in keep]
        offs = [o for _, o in keep]
        gold = gold_spans(r)
        pred = spans_from_probs(np.asarray(probs)[idx] if len(probs) else [], offs,
                                args.threshold)
        if offs:
            ys.append(np.array([any(overlaps(o, g) for g in gold) for o in offs], dtype=bool))
            ps.append(np.asarray(probs)[idx])

        hit = sum(1 for g in gold if any(overlaps(g, p) for p in pred))
        t = r.get("hall_type", "?")
        by_type[t]["n"] += 1
        if gold:
            by_type[t]["hal"] += 1
            by_type[t]["hit"] += 1 if hit else 0
        elif pred:
            by_type[t]["fp"] += 1
        per_row.append({"id": r.get("id"), "material": r.get("_material"),
                        "type": t, "n_gold": len(gold), "n_pred": len(pred),
                        "hit": hit, "answer": ans, "gold": gold, "pred": pred})
        if k % 10 == 0:
            print(f"  {k}/{len(rows)}")

    y = np.concatenate(ys) if ys else np.zeros(0, bool)
    p = np.concatenate(ps) if ps else np.zeros(0)
    roc = auroc(y, p)

    hal = [x for x in per_row if x["n_gold"] > 0]
    ok = [x for x in per_row if x["n_gold"] == 0]
    det_n = sum(1 for x in hal if x["hit"] > 0)
    fp_n = sum(1 for x in ok if x["n_pred"] > 0)

    L = [f"# MSDS 채점 결과", "",
         f"- 임계값 **{args.threshold}** · 문항 {len(rows)}건 "
         f"(환각 {len(hal)} / 정답 {len(ok)}) · 평가 토큰 {len(y):,}개", "",
         "| 지표 | 값 |", "|---|---|",
         f"| **AUROC** | **{roc:.4f}** |",
         f"| 환각 문항 탐지율 | {det_n}/{len(hal)} = {100.0 * det_n / max(1, len(hal)):.1f}% |",
         f"| 정답 문항 오탐률 | {fp_n}/{len(ok)} = {100.0 * fp_n / max(1, len(ok)):.1f}% |",
         f"| 환각 토큰 비율 | {100.0 * y.mean() if len(y) else 0:.2f}% |", "",
         "> 워크스테이션에서 잰 klue 의 톨루엔 52문항 AUROC 은 **0.7941** 이었다. "
         "크게 다르면 담당자에게 알릴 것.", "",
         "## 환각 유형별", "",
         "| 유형 | 문항 | 탐지율 |", "|---|---:|---:|"]
    for t, d in sorted(by_type.items(), key=lambda kv: -kv[1]["n"]):
        rate = (f"{100.0 * d['hit'] / d['hal']:.0f}%" if d["hal"]
                else f"(오탐 {d['fp']}/{d['n']})")
        L.append(f"| {t} | {d['n']} | {rate} |")
    L += ["", "문항이 8개 미만인 유형은 두세 개 차이로 크게 흔들린다. 참고로만 읽을 것.", ""]

    L += ["## 놓친 문항", ""]
    for x in [x for x in per_row if x["n_gold"] > 0 and x["hit"] == 0][:20]:
        L += [f"**{x['id']}** · {x['type']}", "", f"> {x['answer']}", "",
              f"정답 구간: {[x['answer'][s:e] for s, e in x['gold']]}", ""]

    L += ["## 잘못 칠한 문항", ""]
    for x in [x for x in per_row if x["n_gold"] == 0 and x["n_pred"] > 0][:20]:
        L += [f"**{x['id']}**", "", f"> {x['answer']}", "",
              f"칠한 구간: {[x['answer'][s:e] for s, e in x['pred']]}", ""]

    Path(args.out).write_text("\n".join(L), encoding="utf-8")
    print()
    print(f"AUROC       : {roc:.4f}")
    print(f"문항 탐지율 : {det_n}/{len(hal)} = {100.0 * det_n / max(1, len(hal)):.1f}%")
    print(f"문항 오탐률 : {fp_n}/{len(ok)} = {100.0 * fp_n / max(1, len(ok)):.1f}%")
    print(f"→ {args.out}  (이 파일을 담당자에게 보내 주세요)")


if __name__ == "__main__":
    main()
