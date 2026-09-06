"""학습 데이터가 멀쩡한지 확인한다 — 학습이 무너졌을 때 가장 먼저 볼 것.

영어 대조 런이 AUROC 0.497(= 동전 던지기)로 무너졌다. 모델이 못 배운 것인지
**애초에 배울 것이 없었던 것**인지를 가르는 것이 먼저다. 라벨이 엉뚱한 곳을
가리키면 아무리 학습해도 신호가 없다.

세 가지를 본다.
  1) 구간이 실제 답변 텍스트의 어디를 가리키는가 (사람이 눈으로 확인)
  2) 토크나이즈 후 환각 라벨이 몇 %나 남는가 (한국어 4.16% 와 비슷해야 한다)
  3) 답변이 잘려 라벨이 통째로 사라진 건이 있는가

사용
  python -m src.check_data --data work/en_ragtruth_full.jsonl --model BAAI/bge-m3 --max-length 2048
  python -m src.check_data --data work/ko_ragtruth_full.jsonl --model BAAI/bge-m3 --max-length 2048
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter

import config as C


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default=None, help="주면 토크나이즈까지 확인한다")
    ap.add_argument("--max-length", type=int, default=2048)
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    rows = load(args.data)
    labeled = [r for r in rows if r.get("n_spans", 0) > 0]
    n_span = sum(r.get("n_spans", 0) for r in rows)

    print(f"== {args.data}")
    print(f"레코드 {len(rows):,} · 구간이 있는 레코드 {len(labeled):,} · 구간 합계 {n_span:,}")
    split = Counter(r.get("split") for r in rows)
    task = Counter(r.get("task_type") for r in rows)
    print("  split : " + " / ".join(f"{k} {v:,}" for k, v in sorted(split.items())))
    print("  task  : " + " / ".join(f"{k} {v:,}" for k, v in sorted(task.items())))

    # --- 1) 구간이 가리키는 글자를 눈으로 본다 ------------------------------
    print("\n== 구간이 실제로 가리키는 글자 (여기가 환각처럼 읽혀야 한다)")
    bad_range = 0
    for r in rows:
        a = r.get("answer") or ""
        for s, e in r.get("spans", []):
            if not (0 <= s < e <= len(a)):
                bad_range += 1
    if bad_range:
        print(f"  [!] 답변 길이를 벗어난 구간 {bad_range}개 — 라벨이 어긋나 있다")

    rng = random.Random(args.seed)
    for r in rng.sample(labeled, min(args.samples, len(labeled))):
        a = r["answer"]
        print(f"\n  [{r.get('task_type')} · {r.get('split')}] 답변 {len(a)}자, 구간 {r['n_spans']}개")
        for s, e in r["spans"][:3]:
            frag = a[s:e].replace("\n", " ")
            print(f"    {s:>5}~{e:<5} | {frag[:90]}")

    # --- 2) 빈 문맥·빈 질문 ------------------------------------------------
    empty_ctx = sum(1 for r in rows if not (r.get("context") or "").strip())
    empty_q = sum(1 for r in rows if not (r.get("question") or "").strip())
    print(f"\n== 빈 문맥 {empty_ctx:,}건 · 빈 질문 {empty_q:,}건")
    if empty_ctx > len(rows) * 0.1:
        print("  [!] 문맥이 비어 있으면 모델이 대조할 근거가 없다. 여기가 원인일 수 있다")

    # --- 3) 토크나이즈 후 라벨 비율 ----------------------------------------
    if not args.model:
        print("\n(--model 을 주면 토크나이즈 후 라벨 비율까지 확인합니다)")
        return

    from transformers import AutoTokenizer

    from src.dataset import encode_example

    tok = AutoTokenizer.from_pretrained(args.model)
    print(f"\n== 토크나이즈 후 ({args.model}, max_length {args.max_length})")

    n_tok = n_pos = n_lost = n_none = 0
    check = [r for r in rows if r.get("split") == "train"] or rows
    check = check[: min(2000, len(check))]
    for r in check:
        enc = encode_example(r, tok, args.max_length)
        if enc is None:
            n_none += 1
            continue
        labels = enc["labels"]
        keep = [x for x in labels if x != C.IGNORE_INDEX]
        n_tok += len(keep)
        pos = sum(1 for x in keep if x == C.LABEL_HALLUCINATED)
        n_pos += pos
        if r.get("n_spans", 0) > 0 and pos == 0:
            n_lost += 1

    print(f"  표본 {len(check):,}건 · 채점 대상 토큰 {n_tok:,}")
    print(f"  환각 토큰 {n_pos:,} ({n_pos / max(1, n_tok):.2%})   ← 4% 안팎이어야 정상")
    print(f"  구간이 있는데 환각 토큰이 하나도 안 남은 건 {n_lost:,}")
    if n_none:
        print(f"  인코딩에서 버려진 건 {n_none:,}")

    if n_pos == 0:
        print("\n  [!!] 환각 토큰이 하나도 없다. 모델이 배울 것이 없으므로 무너지는 것이 당연하다.")
        print("       라벨 좌표가 답변 텍스트와 어긋나 있다는 뜻이다.")
    elif n_pos / max(1, n_tok) < 0.005:
        print("\n  [!] 환각 토큰이 너무 적다. 라벨이 일부만 살아남았을 수 있다.")
    else:
        print("\n  라벨 자체는 정상이다. 무너진 원인은 데이터가 아니라 학습 쪽에서 찾아야 한다.")


if __name__ == "__main__":
    main()
