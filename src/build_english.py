"""영어 대조 런용 데이터셋 — 번역 손실을 분리해 재기 위한 것.

**왜 필요한가.** 지금 우리에게는 한국어 성능 하나뿐이라, 그 숫자가 낮은(혹은 높은)
이유가 *한국어라서*인지 *번역을 거쳐서*인지 구분이 안 된다. 같은 모델·같은 설정으로
영어 원본을 학습시켜 보면 그 차이가 곧 **번역 비용**이다.

**핵심 설계 — 같은 예시만 쓴다.** `work/ko_ragtruth_full.jsonl` 에 살아남은
response_id 만 골라 영어판을 만든다. 번역 QC 에서 탈락한 4천여 건이 영어 쪽에만
들어가면, "번역 손실"과 "예시 구성 차이"가 섞여 버린다. 같은 예시를 언어만 바꿔
비교해야 개입(intervention)이 되고, 그래야 결론을 말할 수 있다.

한국어 라벨은 태그를 따라 재계산했지만 영어 라벨은 원본 좌표를 그대로 쓴다.
즉 영어 쪽 라벨은 사람이 단 원본이고, 이쪽이 라벨 품질의 상한선이 된다.

사용
  python -m src.build_english
  python -m src.train --model BAAI/bge-m3 --max-length 2048 \
      --data work/en_ragtruth_full.jsonl --out runs/bgem3_en
"""
from __future__ import annotations

import json
from collections import Counter

import config as C


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    ko_path = C.WORK_DIR / "ko_ragtruth_full.jsonl"
    ans_path = C.WORK_DIR / "to_translate.jsonl"
    src_path = C.WORK_DIR / "source_to_translate.jsonl"
    for p in (ko_path, ans_path, src_path):
        if not p.exists():
            raise SystemExit(f"[!] 파일이 없습니다: {p}")

    ko = load_jsonl(ko_path)
    keep = {}
    for r in ko:
        rid = r.get("response_id")
        if rid is not None:
            keep[rid] = r.get("split")
    print(f"한국어 데이터셋 {len(ko):,} 건 → 대조할 response_id {len(keep):,} 개")

    sources = {r["source_id"]: r for r in load_jsonl(src_path)}
    answers = load_jsonl(ans_path)

    out, missing_src, split_cnt = [], 0, Counter()
    for r in answers:
        rid = r.get("response_id")
        if rid not in keep:
            continue
        src = sources.get(r.get("source_id"))
        if src is None:
            missing_src += 1
            continue
        # split 은 한국어 쪽 값을 그대로 따른다. 학습/평가 분할이 어긋나면
        # 비교가 성립하지 않는다.
        split = keep[rid]
        split_cnt[split] += 1
        out.append({
            "response_id": rid,
            "source_id": r.get("source_id"),
            "model": r.get("model"),
            "split": split,
            "task_type": r.get("task_type"),
            "question": src.get("question_en") or "",
            "context": src.get("context_en") or "",
            "answer": r.get("answer_en") or "",
            "spans": [list(s) for s in r.get("spans_en", [])],
            "n_spans": r.get("n_spans", 0),
        })

    dst = C.WORK_DIR / "en_ragtruth_full.jsonl"
    with open(dst, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_span = sum(r["n_spans"] for r in out)
    print(f"영어 대조셋 {len(out):,} 건  (환각 구간 {n_span:,} 개)")
    print("  " + " / ".join(f"{k} {v:,}" for k, v in sorted(split_cnt.items())))
    if missing_src:
        print(f"[경고] source 를 못 찾아 뺀 응답 {missing_src} 건")
    if len(out) != len(keep):
        print(f"[경고] 한국어 {len(keep):,} 건 중 {len(out):,} 건만 짝이 맞았습니다. "
              f"차이가 크면 비교 전에 원인을 확인하세요.")
    print(f"\n→ {dst}")


if __name__ == "__main__":
    main()
