"""한국어 환각 탐지기 — 팀원 노트북용 (GPU 불필요).

탐지기는 110M 짜리라 노트북 CPU 에서도 몇 초면 돈다. 답변을 만드는 생성 모델(12B)은
빼고 **검사만** 하는 화면이다. 예시를 불러오거나 문서와 답변을 직접 붙여 넣으면 된다.

이 파일은 혼자서 돌아간다. 프로젝트 저장소가 없어도 된다.

실행
  python app_cpu.py
"""
from __future__ import annotations

import html as html_lib
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


FEATURE_INTRO_MD = """
### 이게 뭐예요?

AI 챗봇이 **문서를 보고 답하면서 지어낸 부분**을 찾아내는 모델입니다.
문서와 답변을 넣으면, 답변에서 **문서로 뒷받침되지 않는 구간에 형광펜**을 칠합니다.

### 어떻게 쓰나요?

1. 왼쪽에서 **예시를 하나 고르거나**, 문서와 답변을 직접 붙여 넣습니다
2. **검사 시작**을 누릅니다
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

TECH_STACK_MD = """
> ✏️ 아래 내용은 임시 텍스트입니다. 발표 전 실제 정보로 교체해 주세요.

### 🧠 탐지 모델
- **모델 구조**: (예) 토큰 분류(Token Classification) 기반 경량 모델, 약 110M 파라미터
- **판정 방식**: 질문 + 참고 문서 + 검사할 답변을 하나의 시퀀스로 토큰화한 뒤, 답변 구간의 토큰별 환각 확률을 계산

### ⚙️ 실행 환경
- **추론 방식**: GPU 없이 CPU 단독 추론 (노트북 환경에서도 수 초 내 처리)
- **주요 라이브러리**: PyTorch, Hugging Face Transformers

### 🖥️ 프론트엔드 / 서빙
- **UI 프레임워크**: Gradio (`gr.Blocks`)
- **배포 형태**: (예) 로컬 실행 / 사내 데모 서버 — 발표 상황에 맞게 기입

### 📊 데이터 & 평가
- **학습 데이터**: (예) OOO 데이터셋 OOO건
- **평가 지표**: (예) Precision / Recall / F1 — 실제 수치로 교체
"""

CUSTOM_CSS = """
.app-header { display: flex; align-items: flex-start; justify-content: space-between;
              gap: 16px; flex-wrap: wrap; }
.app-header h1 { margin: 0 0 4px 0; font-size: 1.5rem; }
.app-header .subtitle { margin: 0; color: var(--body-text-color-subdued); font-size: 0.92rem; }
.header-actions { display: flex; gap: 8px; justify-content: flex-end; }

.modal-overlay { position: fixed !important; inset: 0; z-index: 1000;
                 display: flex; align-items: center; justify-content: center;
                 background: rgba(0, 0, 0, 0.45); }
.modal-card { background: var(--background-fill-primary); border-radius: var(--radius-lg, 12px);
              max-width: 640px; width: 92%; max-height: 82vh; overflow-y: auto;
              padding: 20px 24px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
              border: 1px solid var(--border-color-primary); }
.modal-card__header { display: flex; align-items: center; justify-content: space-between; }
.modal-card__header h3 { margin: 0; }

.report-card { display: flex; align-items: center; gap: 12px; padding: 14px 16px;
               border-radius: var(--radius-lg, 10px); border: 1px solid var(--border-color-primary);
               margin-bottom: 12px; }
.report-card__icon { font-size: 1.6rem; line-height: 1; }
.report-card__title { font-weight: 600; font-size: 1.02rem; }
.report-card__sub { color: var(--body-text-color-subdued); font-size: 0.88rem; margin-top: 2px; }
.report-card--empty { background: var(--background-fill-secondary); }
.report-card--ok { background: rgba(34, 197, 94, 0.12); border-color: rgba(34, 197, 94, 0.35); }
.report-card--warn { background: rgba(239, 68, 68, 0.10); border-color: rgba(239, 68, 68, 0.35); }
.report-card--invalid { background: rgba(234, 179, 8, 0.12); border-color: rgba(234, 179, 8, 0.4); }

.result-box { min-height: 160px; padding: 16px 18px; border-radius: var(--radius-lg, 10px);
              border: 1px solid var(--border-color-primary); background: var(--background-fill-primary);
              line-height: 1.7; white-space: pre-wrap; }
.result-box--empty { border-style: dashed; color: var(--body-text-color-subdued);
                      display: flex; align-items: center; justify-content: center; text-align: center; }
.hl-mark { background: rgba(239, 68, 68, 0.25); border-bottom: 2px solid #ef4444;
           padding: 0 2px; border-radius: 3px; }
"""

DEFAULT_RESULT_HTML = (
    '<div class="result-box result-box--empty">'
    '🔍 왼쪽에서 예시를 선택하거나 질문 · 참고 문서 · 검사할 AI 답변을 입력한 뒤 '
    '<b>검사 시작</b> 버튼을 눌러주세요.'
    '</div>'
)
DEFAULT_SUMMARY_HTML = (
    '<div class="report-card report-card--empty">'
    '<div class="report-card__icon">📝</div>'
    '<div><div class="report-card__title">검사 대기 중</div>'
    '<div class="report-card__sub">검사를 실행하면 이곳에 요약 리포트가 표시됩니다.</div></div>'
    '</div>'
)


def render_result_html(chunks: list[tuple[str, str | None]]) -> str:
    parts = []
    for text, label in chunks:
        escaped = html_lib.escape(text).replace("\n", "<br>")
        if label:
            parts.append(f'<mark class="hl-mark" title="{html_lib.escape(label)}">{escaped}</mark>')
        else:
            parts.append(escaped)
    body = "".join(parts) or "&nbsp;"
    return f'<div class="result-box">{body}</div>'


def render_summary_html(n: int, ratio: float) -> str:
    if n == 0:
        return ('<div class="report-card report-card--ok">'
                '<div class="report-card__icon">✅</div>'
                '<div><div class="report-card__title">근거 없는 부분이 발견되지 않았습니다</div>'
                '<div class="report-card__sub">검사한 답변이 참고 문서와 대체로 일치합니다.</div></div>'
                '</div>')
    return (f'<div class="report-card report-card--warn">'
            f'<div class="report-card__icon">⚠️</div>'
            f'<div><div class="report-card__title">환각 의심 {n}곳 발견</div>'
            f'<div class="report-card__sub">답변 글자 수 기준 약 {ratio:.1%}가 근거 부족 구간입니다.</div></div>'
            f'</div>')


def render_notice_html(message: str) -> str:
    return (f'<div class="report-card report-card--invalid">'
            f'<div class="report-card__icon">⚠️</div>'
            f'<div><div class="report-card__title">입력을 확인해 주세요</div>'
            f'<div class="report-card__sub">{html_lib.escape(message)}</div></div>'
            f'</div>')


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
        answer = (answer or "").strip()
        context = (context or "").strip()
        if not answer:
            return DEFAULT_RESULT_HTML, render_notice_html("검사할 AI 답변을 입력해 주세요.")
        if not context:
            return DEFAULT_RESULT_HTML, render_notice_html(
                "참고 문서를 입력해 주세요. 무엇과 대조할지 알아야 검사할 수 있습니다.")
        chunks, n, ratio = det.highlighted(context, question, answer, float(threshold))
        return render_result_html(chunks), render_summary_html(n, ratio)

    with gr.Blocks(title="한국어 환각 탐지기", css=CUSTOM_CSS) as ui:
        with gr.Row(elem_classes="app-header"):
            gr.Markdown(
                "<h1>한국어 환각 탐지기</h1>"
                "<p class='subtitle'>챗봇 답변에서 <b>문서로 뒷받침되지 않는 부분</b>을 찾아 "
                "형광펜을 칠합니다 · B1조 검증 모델 파트</p>"
            )
            with gr.Row(elem_classes="header-actions"):
                feature_btn = gr.Button("💡 챗봇 기능 설명", size="sm")
                tech_btn = gr.Button("⚙️ 사용 기술 (Tech Stack)", size="sm")

        with gr.Group(visible=False, elem_classes="modal-overlay") as feature_modal:
            with gr.Column(elem_classes="modal-card"):
                with gr.Row(elem_classes="modal-card__header"):
                    gr.Markdown("### 💡 챗봇 기능 설명")
                    feature_close = gr.Button("✕", size="sm")
                gr.Markdown(FEATURE_INTRO_MD)

        with gr.Group(visible=False, elem_classes="modal-overlay") as tech_modal:
            with gr.Column(elem_classes="modal-card"):
                with gr.Row(elem_classes="modal-card__header"):
                    gr.Markdown("### ⚙️ 사용 기술 (Tech Stack)")
                    tech_close = gr.Button("✕", size="sm")
                gr.Markdown(TECH_STACK_MD)

        with gr.Row():
            with gr.Column(scale=1):
                ex = gr.Dropdown(labels, label="예시 불러오기", value=None,
                                 info="미리 준비된 질문·문서·답변 예시를 선택하면 아래 입력칸에 자동으로 채워집니다.")
                q = gr.Textbox(label="질문", lines=2,
                               placeholder="사용자가 AI에게 물어본 질문을 입력하세요.")
                ctx = gr.Textbox(label="참고 문서", lines=10,
                                 placeholder="AI가 답변을 생성할 때 기준이 되는 원문/참고 문서를 입력하세요.")
                ans = gr.Textbox(label="검사할 AI 답변", lines=6,
                                 placeholder="환각을 탐지하고자 하는 문장/답변을 입력하세요!")
                thr = gr.Slider(0.02, 0.9, value=DEFAULT_THRESHOLD, step=0.01, label="민감도",
                                info="낮출수록 더 많은 구간을 의심스럽다고 표시합니다. (기본값 0.35 권장)")
                btn = gr.Button("🔍 검사 시작", variant="primary", size="lg")
            with gr.Column(scale=1):
                summary = gr.HTML(DEFAULT_SUMMARY_HTML, label="환각 의심 요약 리포트")
                out = gr.HTML(DEFAULT_RESULT_HTML, label="형광펜 하이라이팅 검사 결과")

        ex.change(pick, [ex], [q, ctx, ans])
        btn.click(check, [q, ctx, ans, thr], [out, summary])
        feature_btn.click(lambda: gr.update(visible=True), None, feature_modal)
        feature_close.click(lambda: gr.update(visible=False), None, feature_modal)
        tech_btn.click(lambda: gr.update(visible=True), None, tech_modal)
        tech_close.click(lambda: gr.update(visible=False), None, tech_modal)

    ui.launch(inbrowser=True)


if __name__ == "__main__":
    main()
