"""학사요람 RAG 챗봇 + 환각 형광펜. — 심사 1차 관문(데모)이 이 화면에 달려 있다.

흐름
  질문 → 학사요람에서 관련 청크 검색 → gemma-3-12b-it 가 답변 생성
       → **우리 탐지기가 답변을 토큰 단위로 검사** → 근거 없는 부분에 형광펜

24GB 한 장에 생성 모델(12B int4 ≈ 7GB)과 탐지기(0.5GB)가 함께 올라간다.

"이 답변 저장" 을 누르면 `demo/logs/eval2.jsonl` 에 쌓인다. 그게 평가② 손라벨링
대상이 된다(`export_for_labeling.py`).

사용
  python demo/app.py --run ../runs/klue --threshold 0.5
  python demo/app.py --run ../runs/klue --no-generator     # 답변을 직접 붙여 넣어 시험
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import gradio as gr
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from detector import HalluDetector  # noqa: E402

INDEX_DIR = HERE / "index"
LOG_PATH = HERE / "logs" / "eval2.jsonl"

# 처음에는 "문서에 없으면 확인되지 않는다고 답하라"를 넣었는데, gemma 가 그 지시를
# 너무 잘 따라서 24문항 중 13개를 거부해 버렸다. 환각이 발생하지 않으면 탐지기가
# 보여줄 것이 없어 데모가 성립하지 않는다.
#
# 실제 서비스의 RAG 챗봇은 대개 이 정도의 평범한 지시만 주고, RAGTruth 의 응답도
# 그렇게 생성됐다. 즉 아래 프롬프트가 오히려 현실에 가깝고, 환각도 자연스럽게 나온다.
SYSTEM = (
    "당신은 대학 학사 안내 도우미입니다. 아래 [문서]를 참고해 학생의 질문에 한국어로 "
    "친절하고 구체적으로 답하세요. 답변은 3~5문장으로 쓰세요.\n\n[문서]\n{context}\n\n"
    "[질문] {question}"
)


class Retriever:
    def __init__(self):
        if not (INDEX_DIR / "vectors.npy").exists():
            raise SystemExit("[!] 인덱스가 없습니다. 먼저 build_index.py 를 돌리세요.")
        from transformers import AutoModel, AutoTokenizer
        meta = json.loads((INDEX_DIR / "meta.json").read_text(encoding="utf-8"))
        self.vecs = np.load(INDEX_DIR / "vectors.npy")
        self.chunks = [json.loads(l) for l in
                       (INDEX_DIR / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tok = AutoTokenizer.from_pretrained(meta["embedder"])
        self.model = AutoModel.from_pretrained(meta["embedder"]).to(self.device).eval()
        print(f"[검색] {len(self.chunks):,} 청크")

    @torch.no_grad()
    def __call__(self, query: str, k: int = 4) -> list[dict]:
        enc = self.tok([query], padding=True, truncation=True,
                       max_length=512, return_tensors="pt").to(self.device)
        q = self.model(**enc).last_hidden_state[:, 0]
        q = torch.nn.functional.normalize(q, dim=-1).cpu().numpy()[0]
        idx = np.argsort(-(self.vecs @ q))[:k]
        return [self.chunks[i] for i in idx]


class Generator:
    def __init__(self, model_name: str = "google/gemma-3-12b-it"):
        from transformers import AutoTokenizer, BitsAndBytesConfig
        try:
            from transformers import Gemma3ForConditionalGeneration as Loader
        except ImportError:
            from transformers import AutoModelForCausalLM as Loader
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                               bnb_4bit_quant_type="nf4")
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = Loader.from_pretrained(model_name, quantization_config=q,
                                            device_map="auto").eval()
        print(f"[생성] {model_name} (4bit)")

    @torch.no_grad()
    def __call__(self, context: str, question: str, max_new_tokens: int = 320) -> str:
        msgs = [{"role": "user", "content": SYSTEM.format(context=context, question=question)}]

        # transformers 버전에 따라 apply_chat_template 이 텐서 또는 BatchEncoding 을 준다.
        # 최신 버전은 딕셔너리라 .shape 가 없다 — 양쪽을 모두 받아 넘긴다.
        try:
            enc = self.tok.apply_chat_template(
                msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        except TypeError:
            enc = self.tok.apply_chat_template(
                msgs, add_generation_prompt=True, return_tensors="pt")

        if hasattr(enc, "keys"):
            # token_type_ids 등은 모델에 따라 받지 않으므로 두 개만 넘긴다
            inputs = {k: v.to(self.model.device) for k, v in enc.items()
                      if k in ("input_ids", "attention_mask")}
        else:
            inputs = {"input_ids": enc.to(self.model.device)}

        n = inputs["input_ids"].shape[-1]
        out = self.model.generate(**inputs, max_new_tokens=max_new_tokens,
                                  do_sample=False,
                                  pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
        return self.tok.decode(out[0][n:], skip_special_tokens=True).strip()


def build_ui(det: HalluDetector, ret: Retriever, gen: Generator | None, thr0: float):
    state = gr.State({})

    def ask(question, manual_answer, threshold, top_k):
        if not question.strip():
            return [("질문을 입력하세요.", None)], "", {}, "—"
        hits = ret(question, k=int(top_k))
        context = "\n\n".join(f"[{h['id']}] {h['text']}" for h in hits)

        if manual_answer.strip():
            answer = manual_answer.strip()
        elif gen is not None:
            answer = gen(context, question)
        else:
            return ([("생성 모델이 꺼져 있습니다. 답변을 직접 붙여 넣으세요.", None)],
                    context, {}, "—")

        chunks = det.highlighted(context, question, answer, threshold=float(threshold))
        spans = det.spans(context, question, answer, threshold=float(threshold))
        n_hl = sum(len(t) for t, lab in chunks if lab)
        ratio = n_hl / max(len(answer), 1)
        verdict = (f"환각 의심 구간 **{len(spans)}개** · 답변의 **{ratio:.1%}**"
                   if spans else "**근거 없는 부분이 발견되지 않았습니다.**")

        rec = {"time": datetime.now().isoformat(timespec="seconds"),
               "question": question, "context": context, "answer": answer,
               "retrieved": [h["id"] for h in hits],
               "pred_spans": spans, "threshold": float(threshold)}
        return chunks, context, rec, verdict

    def save(rec):
        if not rec:
            return "저장할 것이 없습니다."
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n = sum(1 for _ in open(LOG_PATH, encoding="utf-8"))
        return f"저장했습니다. 누적 {n}건 → `{LOG_PATH.name}`"

    with gr.Blocks(title="한국어 환각 탐지 — 학사요람 도우미") as ui:
        gr.Markdown("# 학사요람 도우미\n"
                    "답변에서 **문서로 뒷받침되지 않는 부분**을 형광펜으로 칠합니다.")
        with gr.Row():
            with gr.Column(scale=3):
                q = gr.Textbox(label="질문", placeholder="복수전공은 몇 학점을 들어야 하나요?", lines=2)
                manual = gr.Textbox(label="답변 직접 입력 (비워 두면 모델이 생성)", lines=3)
                btn = gr.Button("물어보기", variant="primary")
            with gr.Column(scale=1):
                thr = gr.Slider(0.005, 0.95, value=thr0, step=0.005, label="탐지 민감도(임계값)")
                topk = gr.Slider(1, 8, value=3, step=1, label="검색할 문단 수")

        verdict = gr.Markdown("—")
        out = gr.HighlightedText(label="답변 (형광펜 = 환각 의심)",
                                 color_map={"환각 의심": "red"}, show_legend=True)
        with gr.Row():
            save_btn = gr.Button("이 답변 저장 (평가② 라벨링용)")
            save_msg = gr.Markdown("")
        ctx = gr.Textbox(label="검색된 학사요람 문단", lines=10)

        btn.click(ask, [q, manual, thr, topk], [out, ctx, state, verdict])
        save_btn.click(save, [state], [save_msg])
    return ui


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="../runs/klue", help="학습된 탐지기 경로")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="dry_run.py 가 찾아준 최적 임계값을 넣을 것")
    ap.add_argument("--agg", default="min2", choices=["min", "min2", "mean"],
                    help="창 집계 방식. 긴 실제 문서에는 min2 를 권한다")
    ap.add_argument("--generator", default="google/gemma-3-12b-it")
    ap.add_argument("--no-generator", action="store_true")
    ap.add_argument("--share", action="store_true")
    args = ap.parse_args()

    det = HalluDetector(args.run, max_length=args.max_length, threshold=args.threshold,
                        agg=args.agg)
    ret = Retriever()
    gen = None if args.no_generator else Generator(args.generator)
    build_ui(det, ret, gen, args.threshold).launch(share=args.share)


if __name__ == "__main__":
    main()
