"""RAGTruth 원본 → `<HAL>` 태그가 삽입된 번역 입력 JSONL.

하는 일
  1) source_info.jsonl / response.jsonl 적재
  2) 겹치는 라벨 구간 병합 (원본에 약 1.5% 존재 — 병합하지 않으면 태그가 중첩된다)
  3) 응답 텍스트에 `<HAL>…</HAL>` 삽입
  4) context/prompt 는 source_id 단위로 중복 제거해 따로 뺀다
     (하나의 source 에 6개 모델 응답이 달려 있어, 안 하면 같은 지문을 6번 번역하게 된다)

사용
  python -m src.prepare_ragtruth --inspect          # 스키마만 확인
  python -m src.prepare_ragtruth --limit 200        # 파일럿
  python -m src.prepare_ragtruth                    # 전체
"""
from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from typing import Any, Iterable

import config as C


# --------------------------------------------------------------------------- io
def load_jsonl(path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"[!] 파일이 없습니다: {path}\n"
            f"    git clone https://github.com/ParticleMedia/RAGTruth.git data/RAGTruth"
        )
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


# ----------------------------------------------------------------------- spans
def merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """겹치거나 맞닿은 구간을 하나로 합친다."""
    if not spans:
        return []
    spans = sorted(spans)
    merged = [list(spans[0])]
    for s, e in spans[1:]:
        if s <= merged[-1][1]:          # 겹침 또는 인접
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def extract_spans(labels: Any, text_len: int) -> tuple[list[tuple[int, int]], int]:
    """labels 리스트에서 (start, end) 를 뽑아 정리. (구간들, 버린 개수) 를 돌려준다."""
    raw, dropped = [], 0
    if not isinstance(labels, list):
        return [], 0
    for lab in labels:
        if not isinstance(lab, dict):
            dropped += 1
            continue
        s, e = lab.get(C.FIELD_SPAN_START), lab.get(C.FIELD_SPAN_END)
        if not isinstance(s, int) or not isinstance(e, int):
            dropped += 1
            continue
        s, e = max(0, s), min(text_len, e)
        if s >= e:
            dropped += 1
            continue
        raw.append((s, e))
    return merge_spans(raw), dropped


def insert_tags(text: str, spans: list[tuple[int, int]]) -> str:
    """뒤에서부터 삽입해야 앞쪽 오프셋이 밀리지 않는다."""
    out = text
    for s, e in sorted(spans, reverse=True):
        out = out[:s] + C.HAL_OPEN + out[s:e] + C.HAL_CLOSE + out[e:]
    return out


# ----------------------------------------------------------------- source_info
def flatten_source_info(task_type: str, source_info: Any) -> str:
    """과제별로 모양이 다른 source_info 를 하나의 텍스트로 편다.

    QA        : {"question": ..., "passages": ...}
    Data2txt  : Yelp 업소 정보 dict
    Summary   : 기사 원문 문자열
    """
    if isinstance(source_info, str):
        return source_info
    if isinstance(source_info, dict):
        # QA 는 question 이 따로 있으므로 지문만 뽑는다
        for key in ("passages", "passage", "context", "document", "article"):
            if key in source_info:
                val = source_info[key]
                if isinstance(val, list):
                    return "\n\n".join(str(v) for v in val)
                return str(val)
        return json.dumps(source_info, ensure_ascii=False, indent=2)
    if isinstance(source_info, list):
        return "\n\n".join(str(v) for v in source_info)
    return str(source_info)


def extract_question(source_info: Any) -> str:
    if isinstance(source_info, dict):
        for key in ("question", "query"):
            if key in source_info:
                return str(source_info[key])
    return ""


# ---------------------------------------------------------------------- 스키마
def inspect() -> None:
    src = load_jsonl(C.SOURCE_INFO_FILE)
    res = load_jsonl(C.RESPONSE_FILE)
    print(f"source_info.jsonl : {len(src):,} rows")
    print(f"response.jsonl    : {len(res):,} rows\n")

    print("── source_info 키 ──")
    print(sorted(src[0].keys()))
    print("\n샘플 1건 (값은 200자까지):")
    print(json.dumps({k: str(v)[:200] for k, v in src[0].items()},
                     ensure_ascii=False, indent=2))

    print("\n── response 키 ──")
    print(sorted(res[0].keys()))
    labeled = next((r for r in res if r.get(C.FIELD_LABELS)), res[0])
    print("\n라벨이 있는 샘플 1건:")
    print(json.dumps({k: str(v)[:300] for k, v in labeled.items()},
                     ensure_ascii=False, indent=2))

    splits, tasks = {}, {}
    for r in res:
        splits[r.get(C.FIELD_SPLIT)] = splits.get(r.get(C.FIELD_SPLIT), 0) + 1
    for s in src:
        tasks[s.get(C.FIELD_TASK_TYPE)] = tasks.get(s.get(C.FIELD_TASK_TYPE), 0) + 1
    print(f"\nsplit 분포 : {splits}")
    print(f"task 분포  : {tasks}")
    print("\n위 키 이름이 config.py 의 FIELD_* 와 다르면 config.py 를 고치세요.")


# ------------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inspect", action="store_true", help="스키마만 출력하고 종료")
    ap.add_argument("--limit", type=int, default=None, help="응답 N건만 (파일럿용)")
    ap.add_argument("--split", default=None, choices=["train", "test"],
                    help="특정 split 만")
    args = ap.parse_args()

    if args.inspect:
        inspect()
        return

    sources = {s[C.FIELD_SOURCE_ID]: s for s in load_jsonl(C.SOURCE_INFO_FILE)}
    responses = load_jsonl(C.RESPONSE_FILE)

    if args.split:
        responses = [r for r in responses if r.get(C.FIELD_SPLIT) == args.split]
    if args.limit:
        # 환각이 있는 응답과 없는 응답을 섞어서 뽑는다 (전부 무라벨이면 검증이 안 된다)
        with_lab = [r for r in responses if r.get(C.FIELD_LABELS)]
        without = [r for r in responses if not r.get(C.FIELD_LABELS)]
        half = args.limit // 2
        responses = with_lab[:half] + without[: args.limit - half]

    answer_rows, dropped_total, tagged_total = [], 0, 0
    needed_sources: "OrderedDict[str, dict]" = OrderedDict()

    for r in responses:
        sid = r.get(C.FIELD_SOURCE_ID)
        src = sources.get(sid)
        if src is None:
            continue
        text = r.get(C.FIELD_RESPONSE) or ""
        if not text.strip():
            continue

        spans, dropped = extract_spans(r.get(C.FIELD_LABELS), len(text))
        dropped_total += dropped
        if spans:
            tagged_total += 1

        answer_rows.append({
            "response_id": r.get(C.FIELD_RESPONSE_ID),
            "source_id": sid,
            "model": r.get(C.FIELD_MODEL),
            "split": r.get(C.FIELD_SPLIT),
            "task_type": src.get(C.FIELD_TASK_TYPE),
            "answer_en": text,
            "answer_en_tagged": insert_tags(text, spans),
            "spans_en": [list(s) for s in spans],
            "n_spans": len(spans),
        })
        needed_sources.setdefault(sid, src)

    source_rows = []
    for sid, src in needed_sources.items():
        info = src.get(C.FIELD_SOURCE_INFO)
        source_rows.append({
            "source_id": sid,
            "task_type": src.get(C.FIELD_TASK_TYPE),
            "context_en": flatten_source_info(src.get(C.FIELD_TASK_TYPE), info),
            "question_en": extract_question(info),
        })

    n_a = write_jsonl(C.WORK_DIR / "to_translate.jsonl", answer_rows)
    n_s = write_jsonl(C.WORK_DIR / "source_to_translate.jsonl", source_rows)

    print(f"응답        : {n_a:,} 건  (환각 라벨 있는 응답 {tagged_total:,} 건)")
    print(f"고유 source : {n_s:,} 건  ← 중복 제거로 번역량 {n_a - n_s:,} 건 절약")
    if dropped_total:
        print(f"[경고] 형식이 이상해 버린 라벨 {dropped_total} 개")
    print(f"\n→ {C.WORK_DIR / 'to_translate.jsonl'}")
    print(f"→ {C.WORK_DIR / 'source_to_translate.jsonl'}")


if __name__ == "__main__":
    main()
