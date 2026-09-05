"""슬라이딩 윈도우 추론으로 재평가한다 — **bge-m3 를 돌리기 전에 이걸 먼저 한다.**

절삭 진단에서 "Summary 는 문맥이 잘려서 망가진다"가 나왔다. 그 가설을 **재학습 없이**
검증하는 방법이 이것이다. 문서를 겹치는 창으로 나눠 각각 돌리고 답변 토큰별 확률의
최솟값을 취하면(= 어느 창에서든 근거가 확인되면 지지), 512 모델이 문서 전체를 본다.

  · 창을 씌웠더니 Summary 가 올라간다  → 가설 확인. bge-m3 재학습이 값어치를 한다.
    (그리고 창만으로도 이득을 이미 얻은 것이므로, 학습 없이 이 성능을 써도 된다)
  · 올라가지 않는다 → 긴 문맥은 원인이 아니다. bge-m3 를 건너뛰고 영어 대조 런으로.

학습된 모델을 그대로 쓰므로 GPU 학습이 없다. 창이 여러 개라 추론은 몇 배 느리지만
그래도 30분~1시간이다.

사용
  python -m src.eval_window --run runs/klue --max-length 512
  python -m src.eval_window --run runs/klue --max-length 512 --tasks Summary   # 빠르게 확인만
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import config as C

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "demo"))
from detector import HalluDetector  # noqa: E402

from src.diagnose import score_at, sweep  # noqa: E402

BASELINE_TR = {"whole": 0.7266, "QA": 0.7588, "Data2txt": 0.7391, "Summary": 0.6007}


def load(path: str, split: str, tasks: set[str] | None) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("split") != split:
                continue
            if tasks and (r.get("task_type") or "unknown") not in tasks:
                continue
            if not (r.get("answer") or "").strip():
                continue
            out.append(r)
    return out


def collect(det: HalluDetector, recs: list[dict], window: bool):
    """레코드마다 답변 토큰 확률과 정답 라벨을 모은다."""
    from src.dataset import align_labels

    probs, trues, tasks, exidx = [], [], [], []
    for i, r in enumerate(recs):
        answer = r["answer"]
        spans = [(int(s), int(e)) for s, e in r.get("spans", [])]
        p, offsets = det.token_probs(r.get("context") or "", r.get("question") or "",
                                     answer, window=window)
        if not len(p):
            continue
        y = align_labels(answer, spans, offsets)
        n = min(len(p), len(y))
        probs.append(np.asarray(p[:n], dtype=np.float32))
        trues.append(np.asarray(y[:n], dtype=np.int8))
        tasks += [r.get("task_type") or "unknown"] * n
        exidx += [i] * n
        if i % 200 == 0:
            print(f"  {i:,}/{len(recs):,}", flush=True)
    return (np.concatenate(probs), np.concatenate(trues),
            np.array(tasks), np.array(exidx, dtype=np.int32))


def tuned(prob, true, task, exidx, seed: int = 0) -> dict:
    """**공정한 비교를 위해 임계값을 각자 최적화한 뒤 비교한다.**

    창을 씌우면 창별 확률의 최솟값을 취하므로 확률 분포가 통째로 아래로 내려간다.
    그래서 0.5 를 고정해 두고 비교하면 창 쪽이 부당하게 불리하다 — 정밀도만 오르고
    재현율이 깎여 F1 이 제자리로 보인다. 각자 최적 임계값에서 비교해야 실력 비교가 된다.

    임계값은 샘플을 반씩 나눠 한쪽에서 고르고 다른 쪽에서 채점한다(교차 후 평균).
    """
    rng = np.random.default_rng(seed)
    ids = np.unique(exidx)
    rng.shuffle(ids)
    half = len(ids) // 2
    inf = [np.isin(exidx, ids[:half]), np.isin(exidx, ids[half:])]

    out = {}
    for name, m in [("whole", np.ones(len(true), bool))] + \
                   [(t, task == t) for t in sorted(set(task.tolist()))]:
        held, thrs = [], []
        for a, b in ((0, 1), (1, 0)):
            mt, me = m & inf[a], m & inf[b]
            if len(np.unique(true[mt])) < 2 or len(np.unique(true[me])) < 2:
                continue
            sw = sweep(true[mt], prob[mt])
            if sw is None:
                continue
            t = float(sw["thr"][int(np.argmax(sw["macro_f1"]))])
            held.append(score_at(true[me], prob[me], t))
            thrs.append(t)
        if held:
            out[name] = {"threshold": float(np.mean(thrs)),
                         "f1": float(np.mean([h["f1"] for h in held])),
                         "hallu_f1": float(np.mean([h["hallu_f1"] for h in held]))}
    return out


def summarize(prob, true, task, thr) -> dict:
    res = {"whole": score_at(true, prob, thr)}
    for t in sorted(set(task.tolist())):
        m = task == t
        if len(np.unique(true[m])) < 2:
            continue
        res[t] = score_at(true[m], prob[m], thr)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--data", default=str(C.WORK_DIR / "ko_ragtruth_full.jsonl"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--tasks", nargs="*", default=None, help="예: --tasks Summary")
    ap.add_argument("--trust-remote-code", action="store_true")
    args = ap.parse_args()

    recs = load(args.data, args.split, set(args.tasks) if args.tasks else None)
    print(f"{args.split} {len(recs):,} 건")
    if not recs:
        raise SystemExit("[!] 평가 데이터가 비었습니다.")

    det = HalluDetector(args.run, max_length=args.max_length, threshold=args.threshold,
                        trust_remote_code=args.trust_remote_code)

    print("\n[1/2] 창 없이 (기존 방식 — 문서 뒤를 자름)")
    pb, tb, kb, eb = collect(det, recs, window=False)
    base = summarize(pb, tb, kb, args.threshold)
    print("\n[2/2] 슬라이딩 윈도우")
    pw, tw, kw, ew = collect(det, recs, window=True)
    win = summarize(pw, tw, kw, args.threshold)

    # 확률 분포가 달라졌으므로 0.5 고정 비교는 불공정하다 → 각자 최적 임계값에서 다시 비교
    base_t = tuned(pb, tb, kb, eb)
    win_t = tuned(pw, tw, kw, ew)
    np.savez_compressed(Path(args.run) / "window_preds.npz",
                        prob=pw, true=tw, task=kw, exidx=ew)

    rows = []
    for k in ["whole"] + [t for t in win if t != "whole"]:
        if k not in base or k not in win:
            continue
        rows.append({
            "과제": k,
            "창없음_f1": base[k]["f1"], "창있음_f1": win[k]["f1"],
            "차이_f1": win[k]["f1"] - base[k]["f1"],
            "창없음_auroc": base[k].get("auroc", 0), "창있음_auroc": win[k].get("auroc", 0),
            "차이_auroc": win[k].get("auroc", 0) - base[k].get("auroc", 0),
            "터키어": BASELINE_TR.get(k),
        })

    for r in rows:
        k = r["과제"]
        if k in base_t and k in win_t:
            r["창없음_튜닝f1"] = base_t[k]["f1"]
            r["창있음_튜닝f1"] = win_t[k]["f1"]
            r["차이_튜닝f1"] = win_t[k]["f1"] - base_t[k]["f1"]
            r["창있음_임계값"] = win_t[k]["threshold"]

    out = Path(args.run) / "window_eval.json"
    out.write_text(json.dumps({"창없음": base, "창있음": win,
                               "창없음_튜닝": base_t, "창있음_튜닝": win_t, "비교": rows},
                              indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== 임계값 0.5 고정 (창을 씌우면 확률이 내려가므로 불공정한 비교) ===")
    print(f"{'과제':<10}{'창없음':>9}{'창있음':>9}{'차이':>9}{'AUPRC차이':>11}")
    print("-" * 49)
    for r in rows:
        dp = win[r["과제"]].get("auprc", 0) - base[r["과제"]].get("auprc", 0)
        print(f"{r['과제']:<10}{r['창없음_f1']:>9.4f}{r['창있음_f1']:>9.4f}"
              f"{r['차이_f1']:>+9.4f}{dp:>+11.4f}")

    print(f"\n=== 각자 최적 임계값에서 비교 (이쪽이 진짜 실력 비교) ===")
    print(f"{'과제':<10}{'창없음':>9}{'창있음':>9}{'차이':>9}{'창임계값':>10}{'터키어':>9}")
    print("-" * 58)
    for r in rows:
        if "차이_튜닝f1" not in r:
            continue
        tr = f"{r['터키어']:.4f}" if r["터키어"] else "-"
        print(f"{r['과제']:<10}{r['창없음_튜닝f1']:>9.4f}{r['창있음_튜닝f1']:>9.4f}"
              f"{r['차이_튜닝f1']:>+9.4f}{r['창있음_임계값']:>10.3f}{tr:>9}")

    w = next((r for r in rows if r["과제"] == "whole" and "차이_튜닝f1" in r), None)
    if w:
        print()
        if w["차이_튜닝f1"] >= 0.015:
            print(f"→ 튜닝 후에도 창이 {w['차이_튜닝f1']:+.4f} 앞선다. **긴 문맥이 실제로 도움이 된다.**")
            print("   bge-m3 재학습이 값어치를 하고, 데모·평가②에도 창을 반드시 켠다.")
            print(f"   앞으로 창 추론에는 임계값 {w['창있음_임계값']:.3f} 를 쓴다.")
        else:
            print(f"→ 튜닝 후 차이 {w['차이_튜닝f1']:+.4f}. 창의 이득이 크지 않다.")
            print("   bge-m3 를 건너뛰고 영어 대조 런으로 갈 것.")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
