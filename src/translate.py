"""vLLM + gemma-3-27b-it 로 RAGTruth 를 한국어 번역한다.

논문(arXiv:2509.17671) III-B 의 두 프로토콜을 그대로 따른다.
  · Answer  : `<HAL>` 태그 개수·위치 보존, 태그 안만 번역
  · Context/Question : 일반 번역 (태그 없음 — 같은 프롬프트가 태그 없을 때도 동작한다)

실행 환경: **A5000 1장(24GB)**. 27B bf16(약 54GB)은 들어가지 않으므로 기본값은 12B다.

사용
  python -m src.translate                                   # 12B, A5000 1장
  python -m src.translate --quantization bitsandbytes       # 메모리가 빠듯할 때
  python -m src.translate --model google/gemma-3-27b-it \
                          --quantization bitsandbytes       # 27B 를 int4 로 (느림)
  python -m src.translate --tag pilot12b                    # 산출물 이름 구분 (모델 비교용)
"""
from __future__ import annotations

import argparse
import json

import config as C
from src.prepare_ragtruth import load_jsonl, write_jsonl


def build_prompt(text: str) -> str:
    return C.CORE_TRANSLATION_PROMPT.format(
        source_lang=C.SOURCE_LANG, target_lang=C.TARGET_LANG, text=text
    )


def estimate_max_tokens(text: str) -> int:
    """한국어는 영어보다 토큰이 늘어난다. 넉넉히 잡되 상한을 둔다."""
    return min(8192, max(256, int(len(text) / 2.0) + 512))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tp", type=int, default=1,
                    help="tensor_parallel_size (A5000 1장이므로 기본 1)")
    ap.add_argument("--model", default=C.TRANSLATE_MODEL)
    ap.add_argument("--quantization", default=None,
                    help="예: bitsandbytes / awq / gptq. 24GB에 안 들어갈 때 사용")
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--max-num-seqs", type=int, default=16,
                    help="동시 처리 시퀀스 수. VRAM이 모자라면 낮춘다")
    ap.add_argument("--gpu-mem", type=float, default=0.90)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--tag", default=None,
                    help="산출물 파일명 접미사 (모델 비교 시 결과를 덮어쓰지 않게)")
    args = ap.parse_args()

    suffix = f"_{args.tag}" if args.tag else ""

    from vllm import LLM, SamplingParams
    from transformers import AutoTokenizer

    answers = load_jsonl(C.WORK_DIR / "to_translate.jsonl")
    sources = load_jsonl(C.WORK_DIR / "source_to_translate.jsonl")
    if args.limit:
        answers = answers[: args.limit]
        keep = {a["source_id"] for a in answers}
        sources = [s for s in sources if s["source_id"] in keep]

    # 번역할 항목을 (종류, 인덱스, 필드) 로 평탄화
    jobs: list[tuple[str, int, str, str]] = []
    for i, a in enumerate(answers):
        jobs.append(("answer", i, "answer_en_tagged", a["answer_en_tagged"]))
    for i, s in enumerate(sources):
        if s["context_en"].strip():
            jobs.append(("source", i, "context_en", s["context_en"]))
        if s["question_en"].strip():
            jobs.append(("source", i, "question_en", s["question_en"]))

    print(f"번역 대상 {len(jobs):,} 건 "
          f"(응답 {len(answers):,} / 지문·질문 {len(jobs) - len(answers):,})")

    tok = AutoTokenizer.from_pretrained(args.model)
    prompts = [
        tok.apply_chat_template(
            [{"role": "user", "content": build_prompt(text)}],
            tokenize=False, add_generation_prompt=True,
        )
        for *_, text in jobs
    ]
    params = [
        SamplingParams(temperature=0.0, top_p=1.0, max_tokens=estimate_max_tokens(text))
        for *_, text in jobs
    ]

    llm_kwargs = dict(
        model=args.model,
        tensor_parallel_size=args.tp,
        max_model_len=args.max_model_len,
        max_num_seqs=args.max_num_seqs,
        dtype="bfloat16",
        gpu_memory_utilization=args.gpu_mem,
        trust_remote_code=True,
    )
    if args.quantization:
        llm_kwargs["quantization"] = args.quantization
        if args.quantization == "bitsandbytes":
            llm_kwargs["load_format"] = "bitsandbytes"

    print(f"모델 로드: {args.model} "
          f"(tp={args.tp}, quantization={args.quantization or 'none'})")
    llm = LLM(**llm_kwargs)
    outputs = llm.generate(prompts, params)

    for (kind, idx, field, _), out in zip(jobs, outputs):
        ko = out.outputs[0].text.strip()
        target = answers[idx] if kind == "answer" else sources[idx]
        target[field.replace("_en", "_ko")] = ko

    # 지문·질문 번역을 응답 레코드에 합쳐 준다
    by_sid = {s["source_id"]: s for s in sources}
    for a in answers:
        s = by_sid.get(a["source_id"], {})
        a["context_ko"] = s.get("context_ko", "")
        a["question_ko"] = s.get("question_ko", "")
        a["context_en"] = s.get("context_en", "")

    out_path = C.WORK_DIR / f"translated{suffix}.jsonl"
    n = write_jsonl(out_path, answers)
    write_jsonl(C.WORK_DIR / f"sources_translated{suffix}.jsonl", sources)
    print(f"\n번역 완료 {n:,} 건 → {out_path}")
    print(f"다음: python -m src.postprocess --in {out_path}")


if __name__ == "__main__":
    main()
