"""MSDS 톨루엔 평가 세트로 환각 탐지 성능을 잰다.

두 단위로 잰다.
  문항 단위 — 이 답변에 환각이 있는가 없는가 (52문항, 환각 30 / 정답 22)
  토큰 단위 — 어느 구간이 환각인가 (hall_spans 를 토큰 라벨로 펼쳐서)

두 조건으로 잰다.
  원본 context — jsonl 에 들어 있는 항목별 조각을 그대로 (조원 설계 그대로)
  추린 context — api.py 의 select_context 를 거친 것 (챗봇이 실제로 쓰는 경로)

실행
  python evaluate.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score, roc_auc_score

HERE = Path(__file__).resolve().parent

# 평가 세트는 이 저장소에 없다. 만든 사람(평가·페르소나 파트)에게 받아
# 경로를 넘겨 주어야 한다.
#   set EVAL_DATA=...\examples_msds_toluene.jsonl
DATA = Path(os.environ.get("EVAL_DATA", HERE / "examples_msds_toluene.jsonl"))

# 탐지 모델(model/)과 app_cpu.py 가 있는 폴더. 팀원배포 패키지를 푼 자리를 가리킨다.
#   set APP_DIR=...\팀원배포
APP_DIR = Path(os.environ.get("APP_DIR", HERE.parent / "팀원배포"))
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(HERE))

from app_cpu import Detector, MODEL_DIR  # noqa: E402
import api  # noqa: E402

README_THRESHOLD = 0.35


def load_rows():
    if not DATA.exists():
        raise SystemExit(
            f"[!] 평가 세트가 없습니다: {DATA}\n"
            "    EVAL_DATA 환경변수로 examples_msds_toluene.jsonl 경로를 지정하세요."
        )
    return [json.loads(l) for l in DATA.read_text(encoding="utf-8").splitlines() if l.strip()]


def token_labels(answer: str, spans: list[str], offsets) -> np.ndarray:
    """hall_spans(문자열) 를 토큰 단위 0/1 라벨로 펼친다."""
    mask = np.zeros(len(answer), dtype=bool)
    for s in spans:
        start = answer.find(s)
        while start != -1:
            mask[start:start + len(s)] = True
            start = answer.find(s, start + 1)

    out = []
    for a, b in offsets:
        out.append(1 if (a != b and mask[a:b].any()) else 0)
    return np.array(out)


def macro_f1_at(y_true, scores, thr):
    return f1_score(y_true, (np.asarray(scores) >= thr).astype(int), average="macro", zero_division=0)


def best_threshold(y_true, scores):
    # 도메인이 달라 모델이 전반적으로 낮은 확률을 내므로 아래쪽을 촘촘히 훑는다.
    grid = np.concatenate([np.arange(0.001, 0.02, 0.001), np.arange(0.02, 0.95, 0.01)])
    vals = [macro_f1_at(y_true, scores, t) for t in grid]
    i = int(np.argmax(vals))
    return float(grid[i]), float(vals[i])


def run(det: Detector, rows, use_retrieval: bool):
    resp_scores, resp_true = [], []
    tok_scores, tok_true = [], []
    per_row = []

    for r in rows:
        ctx = r["context"]
        if use_retrieval:
            ctx = api.fit_for_detector(
                api.select_context(ctx, r["question"]), r["question"], r["answer"]
            )

        probs, offsets = det.token_probs(ctx, r["question"], r["answer"])
        if not len(probs):
            continue

        labels = token_labels(r["answer"], r["hall_spans"], offsets[:len(probs)])
        real = [i for i, (a, b) in enumerate(offsets[:len(probs)]) if a != b]
        p, y = probs[real], labels[real]

        tok_scores.extend(p.tolist())
        tok_true.extend(y.tolist())

        score = float(p.max())
        resp_scores.append(score)
        resp_true.append(0 if r["hall_type"] == "정답" else 1)
        per_row.append((r["id"], r["hall_type"], score))

    return {
        "resp_true": np.array(resp_true), "resp_scores": np.array(resp_scores),
        "tok_true": np.array(tok_true), "tok_scores": np.array(tok_scores),
        "per_row": per_row,
    }


def report(name, res, out):
    rt, rs = res["resp_true"], res["resp_scores"]
    tt, ts = res["tok_true"], res["tok_scores"]

    print(f"\n{'=' * 62}", file=out)
    print(f"{name}", file=out)
    print("=" * 62, file=out)

    print(f"\n[문항 단위]  {len(rt)}문항 (환각 {rt.sum()} / 정답 {(rt == 0).sum()})", file=out)
    print(f"  AUROC            {roc_auc_score(rt, rs):.3f}", file=out)
    print(f"  macro F1 @0.35   {macro_f1_at(rt, rs, README_THRESHOLD):.3f}", file=out)
    t, v = best_threshold(rt, rs)
    print(f"  macro F1 최적     {v:.3f}  (threshold {t:.2f})", file=out)

    print(f"\n[토큰 단위]  {len(tt)}토큰 (환각 {tt.sum()} / 정상 {(tt == 0).sum()})", file=out)
    print(f"  AUROC            {roc_auc_score(tt, ts):.3f}", file=out)
    print(f"  macro F1 @0.35   {macro_f1_at(tt, ts, README_THRESHOLD):.3f}", file=out)
    t, v = best_threshold(tt, ts)
    print(f"  macro F1 최적     {v:.3f}  (threshold {t:.2f})", file=out)

    print("\n[환각 유형별 탐지율 @0.35]", file=out)
    by = {}
    for rid, ht, sc in res["per_row"]:
        by.setdefault(ht, []).append(sc)
    for ht in ["지어내기", "숫자변조", "과일반화", "의무예외", "정답"]:
        if ht not in by:
            continue
        sc = np.array(by[ht])
        hit = (sc >= README_THRESHOLD).mean()
        tag = "오탐률" if ht == "정답" else "탐지율"
        print(f"  {ht:<6} {len(sc):>2}건  {tag} {hit:5.1%}", file=out)


def main():
    import io
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows = load_rows()
    det = Detector(MODEL_DIR)
    api.detector = det

    report("원본 context (항목별 조각 그대로 · app_cpu.py 경로)", run(det, rows, False), out)
    report("추린 context (select_context 적용 · 챗봇 api.py 경로)", run(det, rows, True), out)
    out.flush()


if __name__ == "__main__":
    main()
