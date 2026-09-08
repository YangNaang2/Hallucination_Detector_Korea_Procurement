"""MSDS 환각 탐지 — 팀원 노트북용 (GPU 불필요)

`app_cpu.py` 의 탐지기를 그대로 쓰면서 두 가지를 더한다.

1. **MSDS 52문항 예시** — 사람이 정답을 표시해 둔 세트라 모델이 무엇을 놓치는지
   눈으로 바로 확인할 수 있다.
2. **답변 모으기** — 실제 LLM 이 문서를 보고 만든 답변을 쌓는다. 지금 가진
   52문항은 사람이 환각을 일부러 심은 것이라 **모델이 실제로 내는 실수와는 다르다.**
   진짜 성능을 재려면 LLM 이 스스로 만든 답변이 필요하다.

**생성은 껐다 켤 수 있다.** 기본은 꺼짐이며, 이때는 답변을 직접 붙여 넣는다.
켜면 두 가지 방법이 나온다.

- **웹 LLM 복붙 (권장)** — 프롬프트를 만들어 주면 ChatGPT·Gemini 에 붙여넣고
  나온 답을 다시 가져온다. **GPU 가 필요 없고, 상용 모델의 답을 쓰므로
  "최신 모델도 지어낸다"는 것을 보이기에 오히려 낫다.**
- **로컬 생성** — 작은 모델을 내려받아 이 컴퓨터에서 돌린다. GPU 가 없으면
  답변 하나에 수십 초에서 수 분이 걸린다. 급하지 않을 때만 쓴다.

모은 답변은 `수집/모은답변.jsonl` 에 쌓이고, 그 파일을 프로젝트 담당자에게 보내면
채점과 라벨링에 쓴다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import gradio as gr

from app_cpu import Detector, DEFAULT_THRESHOLD, MODEL_DIR

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE / "msds" / "examples_msds_toluene.jsonl"
EXAMPLE_GLOB = "examples_msds_*.jsonl"
CHUNKS = HERE / "msds" / "chunks_toluene.json"
COLLECT_DIR = HERE / "수집"
COLLECT_FILE = COLLECT_DIR / "모은답변.jsonl"

# 문서를 주고 답하게 하는 지시문. 일부러 "모르면 모른다고 하라"를 넣지 않았다 —
# 그 문장을 넣으면 모델이 지나치게 정직해져 환각이 발생하지 않고, 그러면 평가할
# 것이 사라진다. 학사요람 실험에서 24문항 중 13문항이 거부로 돌아온 적이 있다.
GEN_PROMPT = """아래 문서를 참고해서 질문에 답해 주세요.
답변은 3문장 이내로, 구체적인 수치와 항목명을 포함해서 작성해 주세요.

[문서]
{context}

[질문]
{question}

[답변]"""


# --------------------------------------------------------------------- 자료
def load_examples() -> list[dict]:
    """평가 세트를 읽는다. 물질이 늘어나도 파일만 넣으면 자동으로 잡힌다."""
    out = []
    folder = HERE / "msds"
    if not folder.exists():
        return out
    for path in sorted(folder.glob(EXAMPLE_GLOB)):
        mat = path.stem.replace("examples_msds_", "")
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                r["_material"] = mat
                out.append(r)
    return out


def load_chunks() -> dict:
    """문서 조각. 답변을 새로 모을 때 문서를 골라 넣는 데 쓴다."""
    if not CHUNKS.exists():
        return {}
    data = json.loads(CHUNKS.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # {조각이름: 본문} 또는 {조각이름: {"text": 본문}}
        return {k: (v if isinstance(v, str) else v.get("text", "")) for k, v in data.items()}
    if isinstance(data, list):
        return {str(d.get("id", i)): d.get("text", "") for i, d in enumerate(data)}
    return {}


def collected_count() -> int:
    if not COLLECT_FILE.exists():
        return 0
    return sum(1 for line in COLLECT_FILE.read_text(encoding="utf-8").splitlines()
               if line.strip())


# --------------------------------------------------------------------- 로컬 생성
class LocalGenerator:
    """작은 지시 모델 하나. 켤 때 처음으로 불러온다(내려받기 포함)."""

    def __init__(self, model_name: str):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, dtype=torch.float32).eval()

    def __call__(self, prompt: str, max_new_tokens: int = 200) -> str:
        msgs = [{"role": "user", "content": prompt}]
        try:
            text = self.tok.apply_chat_template(msgs, tokenize=False,
                                                add_generation_prompt=True)
        except Exception:
            text = prompt
        enc = self.tok(text, return_tensors="pt")
        with self.torch.no_grad():
            out = self.model.generate(**enc, max_new_tokens=max_new_tokens,
                                      do_sample=True, temperature=0.7, top_p=0.9)
        return self.tok.decode(out[0][enc["input_ids"].shape[1]:],
                               skip_special_tokens=True).strip()


GUIDE = """
### 무엇을 하는 화면인가요

AI 챗봇이 **문서를 보고 답하면서 지어낸 부분**을 찾아 형광펜을 칠합니다.
기준은 "이 말이 사실인가"가 아니라 **"이 문서에 있는가"** 입니다.

### 하실 일은 둘 중 하나입니다

**1) 예시로 확인하기** — 왼쪽에서 MSDS 예시를 고르고 검사해 보세요.
사람이 미리 정답을 표시해 둔 문항이라, 모델이 무엇을 잡고 무엇을 놓치는지 보입니다.

**2) 답변 모으기** — 「답변 생성 모드」를 켜고, 실제 LLM 이 만든 답변을 모아 주세요.
지금 예시들은 사람이 환각을 **일부러 심은 것**이라 실제 모델의 실수와는 다릅니다.
진짜 성능을 재려면 LLM 이 스스로 만든 답변이 필요합니다.

### 이미 알고 있는 약점

- **숫자를 잘 못 잡습니다.** 문서에 6개월인데 답변이 12개월이라고 해도 자주 놓칩니다.
  크기가 5배 다른 두 모델이 똑같이 실패했으니 모델 탓이 아니라 학습 자료의 한계입니다.
- **"문서에 없습니다" 류 답변**에 형광펜이 잘 칠해집니다. 그 문장 자체가
  문서에 없는 말이라 그렇습니다.

이런 걸 발견하시면 그대로 알려 주세요. **한계를 아는 것이 결과입니다.**

### 민감도

낮추면 더 많이 칠하고 올리면 확실한 것만 칠합니다. 기본 0.35 로 두시면 됩니다.
"""


def main():
    if not (MODEL_DIR / "config.json").exists():
        raise SystemExit(f"[!] 모델이 없습니다: {MODEL_DIR}\n"
                         "    압축을 풀 때 model 폴더가 같이 나왔는지 확인하세요.")

    print("모델을 불러오는 중입니다. 처음 한 번만 10초쯤 걸립니다...")
    det = Detector(MODEL_DIR)
    examples = load_examples()
    chunks = load_chunks()
    ex_labels = [f"{i + 1}. [{r.get('_material', '')}] {r['question']}"
                 for i, r in enumerate(examples)]
    chunk_labels = list(chunks.keys())
    print(f"준비 완료. 예시 {len(examples)}개 · 문서 조각 {len(chunk_labels)}개")

    gen_box = {"model": None, "name": ""}

    # ------------------------------------------------------------- 동작
    def pick_example(label):
        if not label:
            return "", "", ""
        r = examples[ex_labels.index(label)]
        return r["question"], r["context"], r["answer"]

    def pick_chunk(label):
        return chunks.get(label, "")

    def check(question, context, answer, threshold):
        if not (answer or "").strip():
            return [("답변을 넣어 주세요.", None)], "—"
        if not (context or "").strip():
            return [("문서를 넣어 주세요. 무엇과 대조할지 알아야 검사할 수 있습니다.",
                     None)], "—"
        chunks_out, n, ratio = det.highlighted(context, question, answer, float(threshold))
        verdict = (f"### 환각 의심 **{n}곳** · 답변의 **{ratio:.1%}**" if n
                   else "### 근거 없는 부분이 발견되지 않았습니다")
        return chunks_out, verdict

    def toggle_gen(on):
        return gr.update(visible=bool(on))

    def make_prompt(question, context):
        if not (context or "").strip() or not (question or "").strip():
            return "문서와 질문을 먼저 채워 주세요."
        return GEN_PROMPT.format(context=context.strip(), question=question.strip())

    def gen_local(question, context, model_name):
        if not (context or "").strip() or not (question or "").strip():
            return "", "문서와 질문을 먼저 채워 주세요."
        name = (model_name or "").strip()
        if not name:
            return "", "모델 이름을 넣어 주세요."
        try:
            if gen_box["name"] != name:
                gen_box["model"] = None
                yield "", f"**{name}** 을 불러오는 중입니다. 처음에는 내려받기까지 몇 분 걸립니다..."
                gen_box["model"] = LocalGenerator(name)
                gen_box["name"] = name
            yield "", "답변을 만드는 중입니다. GPU 가 없으면 1~3분 걸릴 수 있습니다..."
            text = gen_box["model"](make_prompt(question, context))
            yield text, "생성이 끝났습니다. 아래 **검사하기** 를 눌러 보세요."
        except Exception as e:
            yield "", (f"생성에 실패했습니다 — {type(e).__name__}: {e}\n\n"
                       "**웹 LLM 복붙 방식을 쓰시면 됩니다.** 위의 프롬프트를 복사해 "
                       "ChatGPT 나 Gemini 에 붙여넣고, 나온 답변을 답변칸에 옮겨 주세요.")

    def save_answer(question, context, answer, source, note):
        if not (answer or "").strip() or not (context or "").strip():
            return f"저장할 수 없습니다 — 문서와 답변이 모두 있어야 합니다. (현재 {collected_count()}건)"
        COLLECT_DIR.mkdir(exist_ok=True)
        rec = {
            "id": f"COL-{datetime.now().strftime('%y%m%d-%H%M%S')}",
            "question": (question or "").strip(),
            "context": context.strip(),
            "answer": answer.strip(),
            "source": (source or "").strip() or "미기재",
            "note": (note or "").strip(),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
        }
        with COLLECT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return (f"저장했습니다. 지금까지 **{collected_count()}건**\n\n"
                f"`{COLLECT_FILE}`")

    # ------------------------------------------------------------- 화면
    with gr.Blocks(title="MSDS 환각 탐지") as ui:
        gr.Markdown("# MSDS 환각 탐지\n"
                    "답변에서 **문서로 뒷받침되지 않는 부분**에 형광펜을 칠합니다. "
                    "B1조 · 검증 모델 파트")

        with gr.Row():
            with gr.Column(scale=1):
                ex = gr.Dropdown(ex_labels, label="예시 불러오기 (사람이 정답을 표시해 둔 문항)",
                                 value=None)
                ch = gr.Dropdown(chunk_labels, label="문서 조각 골라 넣기 (새 답변을 모을 때)",
                                 value=None)
                q = gr.Textbox(label="질문", lines=2)
                ctx = gr.Textbox(label="문서 (이것과 대조합니다)", lines=12)
                ans = gr.Textbox(label="검사할 답변", lines=6)
                thr = gr.Slider(0.02, 0.9, value=DEFAULT_THRESHOLD, step=0.01,
                                label="민감도 — 낮출수록 많이 칠합니다")
                btn = gr.Button("검사하기", variant="primary")

                gen_on = gr.Checkbox(False, label="답변 생성 모드 켜기")
                with gr.Group(visible=False) as gen_panel:
                    gr.Markdown(
                        "**방법 1 — 웹 LLM 복붙 (권장, GPU 불필요)**\n\n"
                        "아래 프롬프트를 복사해 ChatGPT·Gemini 에 붙여넣고, "
                        "나온 답변을 위 **검사할 답변** 칸에 옮겨 주세요.")
                    mk = gr.Button("프롬프트 만들기")
                    prompt_out = gr.Textbox(label="복사해서 쓰세요", lines=8,
                                            show_copy_button=True)
                    gr.Markdown("---\n**방법 2 — 이 컴퓨터에서 생성 (느립니다)**\n\n"
                                "GPU 가 없으면 답변 하나에 1~3분 걸립니다. "
                                "처음 한 번은 모델을 내려받느라 더 오래 걸립니다.")
                    gen_model = gr.Textbox("Qwen/Qwen2.5-1.5B-Instruct",
                                           label="쓸 모델 (바꾸지 않아도 됩니다)")
                    gen_btn = gr.Button("이 컴퓨터에서 생성하기")
                    gen_msg = gr.Markdown("—")

            with gr.Column(scale=1):
                verdict = gr.Markdown("—")
                out = gr.HighlightedText(label="검사 결과",
                                         color_map={"환각 의심": "red"}, show_legend=True)
                gr.Markdown("---\n### 이 답변 모아 두기\n"
                            "LLM 이 실제로 만든 답변이면 저장해 주세요. "
                            "나중에 사람이 정답을 표시해 진짜 성능을 잽니다.")
                src = gr.Textbox(label="어디서 만든 답변인가요 (예: ChatGPT, Gemini, 로컬)",
                                 lines=1)
                note = gr.Textbox(label="메모 (선택) — 이상한 점이 있으면 적어 주세요", lines=2)
                save = gr.Button("이 답변 저장")
                saved = gr.Markdown(f"지금까지 **{collected_count()}건**")
                with gr.Accordion("처음 오셨나요? 읽어보세요", open=True):
                    gr.Markdown(GUIDE)

        ex.change(pick_example, [ex], [q, ctx, ans])
        ch.change(pick_chunk, [ch], [ctx])
        btn.click(check, [q, ctx, ans, thr], [out, verdict])
        gen_on.change(toggle_gen, [gen_on], [gen_panel])
        mk.click(make_prompt, [q, ctx], [prompt_out])
        gen_btn.click(gen_local, [q, ctx, gen_model], [ans, gen_msg])
        save.click(save_answer, [q, ctx, ans, src, note], [saved])

    ui.launch(inbrowser=True)


if __name__ == "__main__":
    main()
