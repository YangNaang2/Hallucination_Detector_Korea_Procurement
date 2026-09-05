"""토크나이즈 + 라벨 정렬.

논문 III-D 와 동일한 구성:
  · answer 토큰만 0(지지)/1(환각) 라벨을 받는다
  · context·question 토큰은 label = -100 으로 마스킹되어 loss 에 들어가지 않는다

핵심 주의점 — **답변 토큰은 절대 자르지 않는다.** 길이가 넘치면 context 뒤쪽을 자른다.
답변을 자르면 그 구간의 정답 라벨이 통째로 사라져 평가가 왜곡되기 때문이다.
"""
from __future__ import annotations

import json
from pathlib import Path

import torch
from torch.utils.data import Dataset

import config as C


def align_labels(answer: str, spans: list[tuple[int, int]], offsets) -> list[int]:
    """토큰 오프셋과 문자 구간을 겹침 기준으로 맞춘다."""
    labels = []
    for (s, e) in offsets:
        if s == e:                                   # 특수·빈 토큰
            labels.append(C.LABEL_SUPPORTED)
            continue
        hit = any(s < he and e > hs for hs, he in spans)
        labels.append(C.LABEL_HALLUCINATED if hit else C.LABEL_SUPPORTED)
    return labels


def encode_example(rec: dict, tokenizer, max_length: int) -> dict | None:
    answer = rec.get("answer") or ""
    if not answer.strip():
        return None

    spans = [(int(s), int(e)) for s, e in rec.get("spans", [])]

    enc_ans = tokenizer(answer, add_special_tokens=False,
                        return_offsets_mapping=True)
    ans_ids = enc_ans["input_ids"]
    if not ans_ids:
        return None
    ans_labels = align_labels(answer, spans, enc_ans["offset_mapping"])

    question = (rec.get("question") or "").strip()
    context = (rec.get("context") or "").strip()
    prompt = f"질문: {question}\n\n문서:\n{context}" if question else f"문서:\n{context}"
    prompt_ids_full = tokenizer(prompt, add_special_tokens=False)["input_ids"]

    cls_id = tokenizer.cls_token_id if tokenizer.cls_token_id is not None else tokenizer.bos_token_id
    sep_id = tokenizer.sep_token_id if tokenizer.sep_token_id is not None else tokenizer.eos_token_id
    n_special = (1 if cls_id is not None else 0) + (2 if sep_id is not None else 0)

    # 절삭 진단용 — 자르기 전에 필요한 길이를 먼저 기록해 둔다 (src/diagnose.py 가 쓴다)
    n_prompt_full = len(prompt_ids_full)
    n_ans_full = len(ans_ids)
    n_needed = n_prompt_full + n_ans_full + n_special
    answer_truncated = False

    budget = max_length - len(ans_ids) - n_special
    if budget < 0:
        # 답변만으로 이미 최대 길이를 넘는 극단적 경우 — 이때만 답변 뒤를 자른다
        keep = max_length - n_special
        ans_ids, ans_labels = ans_ids[:keep], ans_labels[:keep]
        prompt_ids = []
        answer_truncated = True
    else:
        prompt_ids = prompt_ids_full[:budget]        # 앞쪽(대개 더 관련 있는 부분)을 남긴다

    input_ids, labels = [], []
    if cls_id is not None:
        input_ids.append(cls_id); labels.append(C.IGNORE_INDEX)
    input_ids += prompt_ids;      labels += [C.IGNORE_INDEX] * len(prompt_ids)
    if sep_id is not None:
        input_ids.append(sep_id); labels.append(C.IGNORE_INDEX)
    input_ids += ans_ids;         labels += ans_labels
    if sep_id is not None:
        input_ids.append(sep_id); labels.append(C.IGNORE_INDEX)

    n_dropped = n_prompt_full - len(prompt_ids)

    return {
        "input_ids": input_ids,
        "attention_mask": [1] * len(input_ids),
        "labels": labels,
        "task_type": rec.get("task_type") or "unknown",
        # --- 절삭 진단 메타 (Collator 는 무시하므로 학습에 영향 없다) ---
        "example_id": rec.get("id") or rec.get("response_id") or "",
        "n_needed": n_needed,                 # 자르지 않았다면 필요했을 총 토큰 수
        "n_dropped": n_dropped,               # 문서 뒤쪽에서 버린 토큰 수
        "truncated": bool(n_dropped > 0 or answer_truncated),
        "answer_truncated": answer_truncated,  # 답변까지 잘린 최악의 경우
    }


class HalluDataset(Dataset):
    def __init__(self, path: Path, tokenizer, max_length: int = C.MAX_LENGTH,
                 split: str | None = None):
        self.examples: list[dict] = []
        skipped = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if split and rec.get("split") != split:
                    continue
                ex = encode_example(rec, tokenizer, max_length)
                if ex is None:
                    skipped += 1
                    continue
                self.examples.append(ex)
        if skipped:
            print(f"[dataset] 인코딩 실패로 건너뜀: {skipped} 건")

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, i: int) -> dict:
        return self.examples[i]


class Collator:
    """동적 패딩. 라벨 패딩은 -100."""

    def __init__(self, tokenizer):
        self.pad_id = tokenizer.pad_token_id or 0

    def __call__(self, batch: list[dict]) -> dict:
        maxlen = max(len(b["input_ids"]) for b in batch)
        out = {"input_ids": [], "attention_mask": [], "labels": []}
        for b in batch:
            pad = maxlen - len(b["input_ids"])
            out["input_ids"].append(b["input_ids"] + [self.pad_id] * pad)
            out["attention_mask"].append(b["attention_mask"] + [0] * pad)
            out["labels"].append(b["labels"] + [C.IGNORE_INDEX] * pad)
        return {k: torch.tensor(v, dtype=torch.long) for k, v in out.items()}
