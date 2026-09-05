"""절삭 진단 + 임계값 스윕 + AUPRC. **1순위 실험.**

세 가지를 한 번에 답한다.

  1) 512 절삭이 성능을 얼마나 깎았나
     테스트셋을 '잘린 샘플 / 안 잘린 샘플' 로 나눠 따로 채점한다.
     차이가 크면 긴 컨텍스트 인코더(bge-m3)로 가는 근거가 되고,
     차이가 없으면 512 는 무죄이고 원인은 번역 품질 쪽이다.

  2) 임계값 0.5 가 최선이었나
     test 를 샘플 단위로 반씩 나눠, 한쪽에서 임계값을 고르고 다른 쪽에서 채점한다
     (교차 적용 후 평균). 같은 데이터에서 고르고 채점하면 부풀려진 숫자가 나오므로
     반드시 이렇게 해야 한다.

  3) 환각 F1 0.365 가 정말 낮은 것인가
     AUPRC 와, '모든 토큰을 환각이라고 찍는' 자명한 모델의 F1 을 같이 낸다.

GPU 는 최초 1회만 쓴다. 예측값을 `preds.npz` 로 저장하므로 이후 분석은 `--reuse` 로
GPU 없이 몇 초 만에 다시 돌릴 수 있다.

사용
  python -m src.diagnose --run runs/klue --max-length 512
  python -m src.diagnose --run runs/klue --reuse          # 재분석 (GPU 불필요)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

import config as C

BASELINE_TR = {"whole": 0.7266, "QA": 0.7588, "Data2txt": 0.7391, "Summary": 0.6007}


# --------------------------------------------------------------------------
# 지표
# --------------------------------------------------------------------------
def sweep(y_true: np.ndarray, y_prob: np.ndarray):
    """모든 가능한 임계값에서 macro F1 과 환각 F1 을 한 번에 계산한다.

    확률로 내림차순 정렬한 뒤 상위 k 개를 양성으로 잡는 방식이라 O(n log n) 이다.
    임계값을 0.01 씩 훑는 것보다 정확하고 빠르다.
    """
    order = np.argsort(-y_prob, kind="mergesort")
    p_sorted = y_prob[order]
    t_sorted = y_true[order].astype(np.int64)

    P = int(t_sorted.sum())
    N = len(t_sorted) - P
    if P == 0 or N == 0:
        return None

    tp = np.cumsum(t_sorted)                 # 상위 k 개 중 진짜 환각
    k = np.arange(1, len(t_sorted) + 1)
    fp = k - tp
    fn = P - tp
    tn = N - fp

    f1_pos = 2 * tp / np.maximum(2 * tp + fp + fn, 1)
    f1_neg = 2 * tn / np.maximum(2 * tn + fn + fp, 1)
    macro = (f1_pos + f1_neg) / 2

    # k 개를 양성으로 만드는 임계값 = k 번째 확률 (동점은 함께 넘어간다)
    thr = p_sorted
    return {"thr": thr, "macro_f1": macro, "hallu_f1": f1_pos}


def score_at(y_true: np.ndarray, y_prob: np.ndarray, thr: float) -> dict:
    y_pred = (y_prob >= thr).astype(int)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())

    def prf(tp, fp, fn):
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        return p, r, f

    p1, r1, f1 = prf(tp, fp, fn)
    p0, r0, f0 = prf(tn, fn, fp)
    out = {
        "n_tokens": int(len(y_true)),
        "hallu_ratio": float(y_true.mean()),
        "threshold": float(thr),
        "precision": (p0 + p1) / 2, "recall": (r0 + r1) / 2, "f1": (f0 + f1) / 2,
        "hallu_precision": p1, "hallu_recall": r1, "hallu_f1": f1,
    }
    if len(np.unique(y_true)) == 2:
        out["auroc"] = float(roc_auc_score(y_true, y_prob))
        out["auprc"] = float(average_precision_score(y_true, y_prob))
        # 모든 토큰을 환각으로 찍는 자명한 모델의 F1 — 0.365 가 낮은지 판단하는 기준선
        base = float(y_true.mean())
        out["trivial_hallu_f1"] = 2 * base / (1 + base)
        out["lift_over_trivial"] = f1 / out["trivial_hallu_f1"] if out["trivial_hallu_f1"] else 0.0
    return out


# --------------------------------------------------------------------------
# 예측값 생성 (GPU 1회)
# --------------------------------------------------------------------------
def run_inference(args) -> dict:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    from src.dataset import Collator, HalluDataset

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.run, trust_remote_code=args.trust_remote_code)
    model = AutoModelForTokenClassification.from_pretrained(
        args.run, trust_remote_code=args.trust_remote_code).to(device).eval()

    ds = HalluDataset(args.data, tok, args.max_length, split=args.split)
    print(f"{args.split} {len(ds):,} 건 · max_length={args.max_length}")
    if not len(ds):
        raise SystemExit("[!] 평가 데이터가 비었습니다.")

    collate = Collator(tok)
    probs, trues, tasks, truncs, exidx, needed = [], [], [], [], [], []

    with torch.no_grad():
        for i in range(0, len(ds), args.batch):
            chunk = [ds[j] for j in range(i, min(i + args.batch, len(ds)))]
            batch = collate(chunk)
            labels = batch.pop("labels")
            batch = {k: v.to(device) for k, v in batch.items()}
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16,
                                enabled=(device == "cuda")):
                logits = model(**batch).logits.float().cpu()
            prob = torch.softmax(logits, dim=-1)[..., C.LABEL_HALLUCINATED]

            for row, (lab, pr) in enumerate(zip(labels, prob)):
                m = lab != C.IGNORE_INDEX
                n = int(m.sum())
                if not n:
                    continue
                ex = chunk[row]
                probs.append(pr[m].numpy().astype(np.float32))
                trues.append(lab[m].numpy().astype(np.int8))
                tasks += [ex["task_type"]] * n
                truncs += [ex["truncated"]] * n
                needed += [ex["n_needed"]] * n
                exidx += [i + row] * n
            if (i // args.batch) % 100 == 0:
                print(f"  {i:,}/{len(ds):,}", flush=True)

    data = {
        "prob": np.concatenate(probs),
        "true": np.concatenate(trues),
        "task": np.array(tasks),
        "trunc": np.array(truncs, dtype=bool),
        "needed": np.array(needed, dtype=np.int32),
        "exidx": np.array(exidx, dtype=np.int32),
    }
    np.savez_compressed(Path(args.run) / "preds.npz", **data)
    print(f"→ {args.run}/preds.npz  ({len(data['prob']):,} 토큰)")
    return data


# --------------------------------------------------------------------------
# 분석
# --------------------------------------------------------------------------
def truncation_report(d: dict, thr: float) -> dict:
    """잘린 샘플 / 안 잘린 샘플을 따로 채점한다. 이 문서의 핵심 질문."""
    out = {}
    for name, mask in [("절삭됨", d["trunc"]), ("절삭안됨", ~d["trunc"])]:
        if mask.sum() == 0:
            continue
        out[name] = score_at(d["true"][mask], d["prob"][mask], thr)

    # 얼마나 넘쳤는지에 따라 구간을 나눠 본다 — 단조 감소하면 절삭이 원인이라는 강한 증거
    edges = [(0, 512), (512, 768), (768, 1024), (1024, 2048), (2048, 10 ** 9)]
    buckets = {}
    for lo, hi in edges:
        m = (d["needed"] >= lo) & (d["needed"] < hi)
        if m.sum() < 500 or len(np.unique(d["true"][m])) < 2:
            continue
        buckets[f"{lo}~{hi if hi < 10**9 else '∞'} 토큰"] = score_at(
            d["true"][m], d["prob"][m], thr)
    out["필요_길이별"] = buckets

    ex_total = len(np.unique(d["exidx"]))
    ex_trunc = len(np.unique(d["exidx"][d["trunc"]]))
    out["요약"] = {
        "샘플_전체": ex_total,
        "샘플_절삭됨": ex_trunc,
        "절삭_비율": ex_trunc / ex_total if ex_total else 0.0,
        "토큰_절삭됨_비율": float(d["trunc"].mean()),
    }
    return out


def truncation_within_task(d: dict, thr: float) -> dict:
    """**과제를 고정한 채** 절삭/비절삭을 비교한다.

    `truncation_report` 의 '절삭안됨' 집단에는 문맥이 짧은 Data2txt 가 몰려 있고
    '절삭됨' 에는 QA·Summary 가 몰려 있다. 그래서 둘의 차이에는 '절삭 피해' 와
    '과제 구성 차이' 가 섞여 있다. 같은 과제 안에서만 비교하면 구성 요인이 사라지고
    절삭의 순수한 효과만 남는다.

    macro F1 과 함께 **AUROC 차이**를 반드시 본다. macro F1 은 임계값 0.5 고정이라
    보정 차이에 흔들리지만 AUROC 은 그렇지 않으므로, 판별력이 실제로 깎였는지는
    AUROC 이 답한다.
    """
    out = {}
    for t in sorted(set(d["task"].tolist())):
        tm = d["task"] == t
        row = {}
        for name, mask in [("절삭안됨", tm & ~d["trunc"]), ("절삭됨", tm & d["trunc"])]:
            if mask.sum() < 500 or len(np.unique(d["true"][mask])) < 2:
                continue
            row[name] = score_at(d["true"][mask], d["prob"][mask], thr)
        if len(row) == 2:
            row["차이_macro_f1"] = row["절삭안됨"]["f1"] - row["절삭됨"]["f1"]
            row["차이_auroc"] = row["절삭안됨"]["auroc"] - row["절삭됨"]["auroc"]
            out[t] = row
    return out


def threshold_report(d: dict, seed: int = 0) -> dict:
    """test 를 샘플 단위로 반씩 나눠 교차 적용한다 (한쪽에서 고르고 다른 쪽에서 채점)."""
    rng = np.random.default_rng(seed)
    ex_ids = np.unique(d["exidx"])
    rng.shuffle(ex_ids)
    half = len(ex_ids) // 2
    fold = {0: set(ex_ids[:half].tolist()), 1: set(ex_ids[half:].tolist())}
    in_fold = {f: np.isin(d["exidx"], list(fold[f])) for f in (0, 1)}

    res = {"folds": [], "objective": {}}
    for objective in ("macro_f1", "hallu_f1"):
        held = []
        for tune, test in ((0, 1), (1, 0)):
            sw = sweep(d["true"][in_fold[tune]], d["prob"][in_fold[tune]])
            if sw is None:
                continue
            best = sw["thr"][int(np.argmax(sw[objective]))]
            s = score_at(d["true"][in_fold[test]], d["prob"][in_fold[test]], float(best))
            held.append(s)
        if held:
            res["objective"][objective] = {
                "threshold_평균": float(np.mean([h["threshold"] for h in held])),
                "macro_f1": float(np.mean([h["f1"] for h in held])),
                "hallu_f1": float(np.mean([h["hallu_f1"] for h in held])),
                "hallu_precision": float(np.mean([h["hallu_precision"] for h in held])),
                "hallu_recall": float(np.mean([h["hallu_recall"] for h in held])),
            }
    res["기준_0.5"] = score_at(d["true"], d["prob"], 0.5)
    return res


def task_report(d: dict, thr: float) -> dict:
    out = {}
    for t in sorted(set(d["task"].tolist())):
        m = d["task"] == t
        if len(np.unique(d["true"][m])) < 2:
            continue
        s = score_at(d["true"][m], d["prob"][m], thr)
        if t in BASELINE_TR:
            s["터키어_기준선"] = BASELINE_TR[t]
            s["격차"] = s["f1"] - BASELINE_TR[t]
        out[t] = s
    return out


def fmt(v: float) -> str:
    return f"{v:.4f}"


def write_markdown(path: Path, run: str, whole: dict, trunc: dict,
                   thr: dict, tasks: dict, within: dict | None = None) -> None:
    L = [f"# 진단 리포트 — `{run}`", ""]

    L += ["## 1. 절삭 진단 (핵심 질문)", ""]
    s = trunc["요약"]
    L += [f"- 샘플 {s['샘플_전체']:,}건 중 **{s['샘플_절삭됨']:,}건({s['절삭_비율']:.1%})이 잘렸다.**",
          f"- 평가 토큰 기준으로는 {s['토큰_절삭됨_비율']:.1%}.", "",
          "| 구분 | 토큰 | 환각비율 | macro F1 | 환각 F1 | AUROC |",
          "|---|---|---|---|---|---|"]
    for k in ("절삭안됨", "절삭됨"):
        if k in trunc:
            v = trunc[k]
            L.append(f"| **{k}** | {v['n_tokens']:,} | {v['hallu_ratio']:.2%} | "
                     f"{fmt(v['f1'])} | {fmt(v['hallu_f1'])} | {fmt(v.get('auroc', 0))} |")
    if "절삭됨" in trunc and "절삭안됨" in trunc:
        gap = trunc["절삭안됨"]["f1"] - trunc["절삭됨"]["f1"]
        L += ["", f"**차이: {gap:+.4f}**", ""]
        if gap >= 0.03:
            L += ["> 잘린 쪽이 뚜렷하게 낮다. **512 절삭이 격차의 주요 원인이라는 근거가 된다.**",
                  "> → `BAAI/bge-m3`(8,192 토큰)로 재학습하면 회복이 기대된다."]
        elif gap <= 0.01:
            L += ["> 차이가 거의 없다. **512 는 무죄다.**",
                  "> → 긴 컨텍스트 모델에 시간을 쓰지 말고, 영어 대조 런으로 번역 손실을 확인할 것."]
        else:
            L += ["> 차이가 애매하다. 필요 길이별 표를 보고 단조 감소하는지 확인할 것."]
    if trunc["필요_길이별"]:
        L += ["", "### 필요했던 길이별 (단조 감소하면 절삭이 원인)", "",
              "| 필요 길이 | 토큰 | macro F1 | AUROC |", "|---|---|---|---|"]
        for k, v in trunc["필요_길이별"].items():
            L.append(f"| {k} | {v['n_tokens']:,} | {fmt(v['f1'])} | {fmt(v.get('auroc', 0))} |")

    if within:
        L += ["", "### 과제를 고정하고 다시 본 절삭 효과 (구성 차이 제거)", "",
              "위 표의 '절삭안됨' 에는 문맥이 짧은 Data2txt 가 몰려 있어 절삭 피해와 "
              "과제 구성이 섞인다. 같은 과제 안에서만 비교하면 절삭의 순수 효과가 남는다.", "",
              "| 과제 | macro F1 (안잘림→잘림) | 차이 | AUROC (안잘림→잘림) | **AUROC 차이** |",
              "|---|---|---|---|---|"]
        for t, r in within.items():
            a, b = r["절삭안됨"], r["절삭됨"]
            L.append(f"| {t} | {fmt(a['f1'])} → {fmt(b['f1'])} | {r['차이_macro_f1']:+.4f} | "
                     f"{fmt(a['auroc'])} → {fmt(b['auroc'])} | **{r['차이_auroc']:+.4f}** |")
        mean_auroc = float(np.mean([r["차이_auroc"] for r in within.values()]))
        mean_f1 = float(np.mean([r["차이_macro_f1"] for r in within.values()]))
        L += ["", f"**과제 평균 — macro F1 차이 {mean_f1:+.4f} / AUROC 차이 {mean_auroc:+.4f}**", ""]
        if mean_auroc >= 0.02:
            L += ["> 과제를 고정해도 AUROC 이 뚜렷하게 떨어진다. **절삭이 진짜 원인이다.** "
                  "→ 긴 컨텍스트 인코더로 갈 근거가 된다."]
        elif mean_auroc <= 0.008:
            L += ["> 과제를 고정하니 AUROC 차이가 사라진다. **앞 표의 격차는 대부분 "
                  "과제 구성 차이였다.** → 긴 컨텍스트 인코더에 시간을 쓰지 말 것."]
        else:
            L += ["> 애매하다. 얻을 수 있는 상한이 작으므로 다른 실험을 먼저 할 것."]

    L += ["", "## 2. 임계값", "",
          "한쪽 절반에서 임계값을 고르고 나머지 절반에서 채점했다(교차 후 평균). "
          "같은 데이터에서 고르고 채점하면 부풀려지므로 이렇게 해야 한다.", "",
          "| 기준 | 임계값 | macro F1 | 환각 F1 | 환각 P | 환각 R |", "|---|---|---|---|---|---|"]
    b = thr["기준_0.5"]
    L.append(f"| 현재 (0.5 고정) | 0.500 | {fmt(b['f1'])} | {fmt(b['hallu_f1'])} | "
             f"{fmt(b['hallu_precision'])} | {fmt(b['hallu_recall'])} |")
    for name, v in thr["objective"].items():
        L.append(f"| {name} 최대화 | {v['threshold_평균']:.3f} | {fmt(v['macro_f1'])} | "
                 f"{fmt(v['hallu_f1'])} | {fmt(v['hallu_precision'])} | {fmt(v['hallu_recall'])} |")

    L += ["", "## 3. 환각 F1 이 낮아 보이는 이유", "",
          f"- 환각 토큰 비율 **{whole['hallu_ratio']:.2%}**",
          f"- AUROC **{fmt(whole.get('auroc', 0))}** / AUPRC **{fmt(whole.get('auprc', 0))}** "
          f"(AUPRC 의 무작위 기준선 = {whole['hallu_ratio']:.4f})",
          f"- 모든 토큰을 환각으로 찍는 모델의 F1 = **{fmt(whole['trivial_hallu_f1'])}**",
          f"- 실제 환각 F1 {fmt(whole['hallu_f1'])} = 그 **{whole['lift_over_trivial']:.1f}배**"]

    L += ["", "## 4. 과제별 (임계값 0.5)", "",
          "| 과제 | macro F1 | 터키어 | 격차 | AUROC | 환각비율 |", "|---|---|---|---|---|---|"]
    for t, v in tasks.items():
        g = v.get("격차")
        L.append(f"| {t} | {fmt(v['f1'])} | {v.get('터키어_기준선', '-')} | "
                 f"{g:+.4f} | {fmt(v.get('auroc', 0))} | {v['hallu_ratio']:.2%} |"
                 if g is not None else
                 f"| {t} | {fmt(v['f1'])} | - | - | {fmt(v.get('auroc', 0))} | {v['hallu_ratio']:.2%} |")

    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--data", default=str(C.WORK_DIR / "ko_ragtruth_full.jsonl"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--trust-remote-code", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="preds.npz 재사용 (GPU 불필요)")
    args = ap.parse_args()

    cache = Path(args.run) / "preds.npz"
    if args.reuse and cache.exists():
        z = np.load(cache, allow_pickle=False)
        d = {k: z[k] for k in z.files}
        print(f"[캐시] {cache} · {len(d['prob']):,} 토큰")
    else:
        d = run_inference(args)

    whole = score_at(d["true"], d["prob"], 0.5)
    trunc = truncation_report(d, 0.5)
    within = truncation_within_task(d, 0.5)
    thr = threshold_report(d)
    tasks = task_report(d, 0.5)

    result = {"whole": whole, "절삭진단": trunc, "과제내_절삭": within,
              "임계값": thr, "과제별": tasks}
    out_json = Path(args.run) / "diagnosis.json"
    out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(Path(args.run) / "diagnosis.md", args.run, whole, trunc, thr, tasks, within)

    s = trunc["요약"]
    print(f"\n{'='*60}\n절삭된 샘플: {s['샘플_절삭됨']:,}/{s['샘플_전체']:,} ({s['절삭_비율']:.1%})")
    if "절삭됨" in trunc and "절삭안됨" in trunc:
        a, b = trunc["절삭안됨"]["f1"], trunc["절삭됨"]["f1"]
        print(f"macro F1 — 안잘림 {a:.4f} vs 잘림 {b:.4f}  (차이 {a-b:+.4f})")
    if within:
        ma = float(np.mean([r["차이_auroc"] for r in within.values()]))
        mf = float(np.mean([r["차이_macro_f1"] for r in within.values()]))
        print(f"과제 고정 후 — macro F1 차이 {mf:+.4f} / AUROC 차이 {ma:+.4f}"
              f"  ({'절삭이 원인' if ma >= 0.02 else '구성 차이였음' if ma <= 0.008 else '애매'})")
    print(f"AUPRC {whole.get('auprc', 0):.4f} (무작위 기준선 {whole['hallu_ratio']:.4f})")
    for name, v in thr["objective"].items():
        print(f"임계값 {v['threshold_평균']:.3f} ({name} 최대화) → "
              f"macro {v['macro_f1']:.4f} / 환각 {v['hallu_f1']:.4f}")
    print(f"{'='*60}\n→ {out_json}\n→ {Path(args.run) / 'diagnosis.md'}")


if __name__ == "__main__":
    main()
