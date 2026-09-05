"""한국어 환각 탐지기 — 팀원 노트북용 (GPU 불필요).

탐지기는 110M 짜리라 노트북 CPU 에서도 몇 초면 돈다. 답변을 만드는 생성 모델(12B)은
빼고 **검사만** 하는 화면이다. 예시를 불러오거나 문서와 답변을 직접 붙여 넣으면 된다.

이 파일은 혼자서 돌아간다. 프로젝트 저장소가 없어도 된다.

실행
  python app_cpu.py
"""
from __future__ import annotations

import json
from pathlib import Path

import gradio as gr
import numpy as np
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE / "model"
EXAMPLES = HERE / "examples.jsonl"

MAX_LENGTH = 512
DEFAULT_THRESHOLD = 0.35
HALLUCINATED = 1
torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))


# --------------------------------------------------------------------------
# 탐지기 — 워크스테이션 학습 때와 같은 방식으로 입력을 만든다
# --------------------------------------------------------------------------
class Detector:
    def __init__(self, model_dir: Path):
        self.tok = AutoTokenizer.from_pretrained(str(model_dir))
        self.model = AutoModelForTokenClassification.from_pretrained(str(model_dir)).eval()
        self.cls_id = self.tok.cls_token_id if self.tok.cls_token_id is not None else self.tok.bos_token_id
        self.sep_id = self.tok.sep_token_id if self.tok.sep_token_id is not None else self.tok.eos_token_id
        self.n_special = (1 if self.cls_id is not None else 0) + (2 if self.sep_id is not None else 0)

    @torch.no_grad()
    def _forward(self, prompt_ids, ans_ids):
        ids = ([self.cls_id] if self.cls_id is not None else []) + prompt_ids
        if self.sep_id is not None:
            ids.append(self.sep_id)
        start = len(ids)
        ids += ans_ids
        if self.sep_id is not None:
            ids.append(self.sep_id)
        t = torch.tensor([ids])
        logits = self.model(input_ids=t, attention_mask=torch.ones_like(t)).logits
        prob = torch.softmax(logits[0].float(), dim=-1)[:, HALLUCINATED].numpy()
        return prob[start:start + len(ans_ids)]

    def token_probs(self, context: str, question: str, answer: str):
        enc = self.tok(answer, add_special_tokens=False, return_offsets_mapping=True)
        ans_ids, offsets = enc["input_ids"], enc["offset_mapping"]
        if not ans_ids:
            return np.zeros(0), []

        question, context = (question or "").strip(), (context or "").strip()
        prompt = f"질문: {question}\n\n문서:\n{context}" if question else f"문서:\n{context}"
        prompt_ids = self.tok(prompt, add_special_tokens=False)["input_ids"]

        budget = MAX_LENGTH - len(ans_ids) - self.n_special
        if budget <= 0:
            keep = MAX_LENGTH - self.n_special
            return self._forward([], ans_ids[:keep]), offsets[:keep]
        if len(prompt_ids) <= budget:
            return self._forward(prompt_ids, ans_ids), offsets

        # 문서가 길면 겹치는 창으로 나눠 훑고, 창별 확률 중 **두 번째로 작은 값**을 쓴다.
        # 최솟값을 쓰면 창이 많아질수록 확률이 0 으로 눌려 아무것도 못 잡는다.
        stride = max(1, budget // 2)
        mat = []
        for s in range(0, len(prompt_ids), stride):
            chunk = prompt_ids[s:s + budget]
            if not chunk:
                break
            mat.append(self._forward(chunk, ans_ids))
            if s + budget >= len(prompt_ids):
                break
        m = np.stack(mat)
        return (m.min(axis=0) if len(m) == 1 else np.sort(m, axis=0)[1]), offsets

    def highlighted(self, context, question, answer, threshold):
        probs, offsets = self.token_probs(context, question, answer)
        if not len(probs):
            return [(answer, None)], 0, 0.0

        spans, cur = [], None
        for p, (s, e) in zip(probs, offsets):
            if s == e:
                continue
            if p >= threshold:
                if cur is None:
                    cur = [s, e]
                elif s - cur[1] <= 1:
                    cur[1] = e
                else:
                    spans.append(tuple(cur)); cur = [s, e]
            elif cur is not None:
                spans.append(tuple(cur)); cur = None
        if cur is not None:
            spans.append(tuple(cur))
        spans = [(s, e) for s, e in spans if e - s >= 2]

        out, pos = [], 0
        for s, e in spans:
            if s > pos:
                out.append((answer[pos:s], None))
            out.append((answer[s:e], "환각 의심"))
            pos = e
        if pos < len(answer):
            out.append((answer[pos:], None))
        marked = sum(e - s for s, e in spans)
        return (out or [(answer, None)]), len(spans), marked / max(len(answer), 1)


GUIDE = """
### 이게 뭐예요?

AI 챗봇이 **문서를 보고 답하면서 지어낸 부분**을 찾아내는 모델입니다.
문서와 답변을 넣으면, 답변에서 **문서로 뒷받침되지 않는 구간에 형광펜**을 칠합니다.

### 어떻게 쓰나요?

1. 왼쪽에서 **예시를 하나 고르거나**, 문서와 답변을 직접 붙여 넣습니다
2. **검사하기**를 누릅니다
3. 빨간 형광펜이 칠해진 곳이 "문서에 근거가 없다"고 판단한 부분입니다

### 형광펜이 안 뜨면요?

두 가지 경우입니다. **답변이 정말 정확하거나**, 아니면 **모델이 놓쳤거나.**
지금 성능이 환각 3건 중 1건을 잡는 수준이라 놓치는 게 정상입니다.
민감도를 낮추면 더 많이 잡지만 맞는 문장에도 칠하기 시작합니다.

### 맞는 문장에 칠해지면요?

그것도 있습니다. 특히 **"문서에 나와있지 않습니다"** 같은 답변이 잘 칠해지는데,
그 문장 자체가 문서에 없는 말이라 그렇습니다. 모델이 배운 기준으로는 틀린 게 아닙니다.

### 민감도는 뭔가요?

낮추면 의심스러운 걸 더 많이 칠하고, 올리면 확실한 것만 칠합니다.
**0.35가 기본값**이고, 이 값에서 정답 15건 중 14건은 형광펜이 뜨지 않았습니다.
"""


def load_examples():
    if not EXAMPLES.exists():
        return []
    out = []
    for line in EXAMPLES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out.append(r)
    return out


def main():
    if not (MODEL_DIR / "config.json").exists():
        raise SystemExit(f"[!] 모델이 없습니다: {MODEL_DIR}\n"
                         "    압축을 풀 때 model 폴더가 같이 나왔는지 확인하세요.")
    print("모델을 불러오는 중입니다. 처음 한 번만 10초쯤 걸립니다...")
    det = Detector(MODEL_DIR)
    examples = load_examples()
    labels = [f"{i + 1}. {r['question']}" for i, r in enumerate(examples)]
    print(f"준비 완료. 예시 {len(examples)}개")

    def pick(label):
        if not label:
            return "", "", ""
        i = labels.index(label)
        r = examples[i]
        return r["question"], r["context"], r["answer"]

    def check(question, context, answer, threshold):
        if not (answer or "").strip():
            return [("답변을 넣어 주세요.", None)], "—"
        if not (context or "").strip():
            return [("문서를 넣어 주세요. 무엇과 대조할지 알아야 검사할 수 있습니다.", None)], "—"
        chunks, n, ratio = det.highlighted(context, question, answer, float(threshold))
        verdict = (f"### 환각 의심 **{n}곳** · 답변의 **{ratio:.1%}**" if n
                   else "### 근거 없는 부분이 발견되지 않았습니다")
        return chunks, verdict

    with gr.Blocks(title="한국어 환각 탐지기") as ui:
        gr.Markdown("# 한국어 환각 탐지기\n"
                    "챗봇 답변에서 **문서로 뒷받침되지 않는 부분**을 찾아 형광펜을 칠합니다. "
                    "B1조 · 검증 모델 파트")

        with gr.Row():
            with gr.Column(scale=1):
                ex = gr.Dropdown(labels, label="예시 불러오기", value=None)
                q = gr.Textbox(label="질문", lines=2)
                ctx = gr.Textbox(label="문서 (이것과 대조합니다)", lines=12)
                ans = gr.Textbox(label="검사할 답변", lines=6)
                thr = gr.Slider(0.02, 0.9, value=DEFAULT_THRESHOLD, step=0.01,
                                label="민감도 — 낮출수록 많이 칠합니다")
                btn = gr.Button("검사하기", variant="primary")
            with gr.Column(scale=1):
                verdict = gr.Markdown("—")
                out = gr.HighlightedText(label="검사 결과", color_map={"환각 의심": "red"},
                                         show_legend=True)
                with gr.Accordion("처음 오셨나요? 읽어보세요", open=True):
                    gr.Markdown(GUIDE)

        ex.change(pick, [ex], [q, ctx, ans])
        btn.click(check, [q, ctx, ans, thr], [out, verdict])

    ui.launch(inbrowser=True)


if __name__ == "__main__":
    main()
