"""문서 기반 질의응답 + 환각 탐지 통합 API (로컬 CPU 전용).

업로드한 PDF/TXT 에서 본문을 뽑아 그것을 근거로 로컬 Ollama 가 답을 만들고,
그 답을 app_cpu.py 의 Detector 로 검사해 환각 의심 구간까지 한 번에 돌려준다.

실행
  uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import io
import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app_cpu import HERE, MODEL_DIR, DEFAULT_THRESHOLD, Detector

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
OLLAMA_TIMEOUT = 300

STATIC_DIR = HERE / "frontend" / "dist"
REPORT_LOG = HERE / "false_positive_reports.jsonl"

# 탐지기는 512 토큰까지만 본다. 이 한계를 넘기면 문서를 창 여러 개로 쪼개 훑는데,
# 그러면 창별 확률이 서로를 눌러 환각을 하나도 못 잡는다(창이 많을수록 심해진다).
# 그래서 문서 + 답변이 창 하나에 들어가도록 예산을 잡는다. 프롬프트가 짧아지는 덕에
# CPU 에서 LLM 생성도 빨라진다.
ANSWER_TOKEN_CAP = 160          # 생성 답변 길이 상한
CONTEXT_TOKEN_BUDGET = 512 - ANSWER_TOKEN_CAP - 40   # 질문·특수토큰 몫으로 40 을 뺀다
CONTEXT_CHAR_BUDGET = 620       # 한글 기준 대략 위 토큰 예산에 해당
CHUNK_CHAR_SIZE = 200

PROMPT = """다음 문서만 근거로 질문에 한국어로 답하세요.
문서에 없는 내용은 지어내지 말고, 모르면 모른다고 답하세요.

문서:
{context}

질문: {question}

답변:"""

# 시연용. 위 프롬프트를 쓰면 모델이 "문서에 없습니다"로만 답해 환각이 나오지 않는다.
# 탐지기가 실제로 무엇을 잡는지 보여주려면 일부러 지어내게 만들어야 한다.
LOOSE_PROMPT = """다음 문서를 참고해 질문에 한국어로 자신 있게 답하세요.
문서에 정보가 부족하더라도 아는 대로 구체적인 수치와 연도를 넣어 상세히 답하세요.

문서:
{context}

질문: {question}

답변:"""


# --------------------------------------------------------------------------
# 파일 → 텍스트
# --------------------------------------------------------------------------
def extract_text(data: bytes, filename: str) -> str:
    """업로드된 PDF/TXT 바이트에서 본문 텍스트를 뽑는다."""
    name = (filename or "").lower()

    if name.endswith(".pdf"):
        return _extract_pdf(data)

    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        pass
    else:
        with fitz.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc).strip()

    try:
        import pdfplumber
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF 처리 라이브러리가 없습니다. pip install pymupdf 또는 pdfplumber 를 실행하세요.",
        )
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages).strip()


# --------------------------------------------------------------------------
# 질문과 관련된 구간 고르기
# --------------------------------------------------------------------------
def _tokens(text: str) -> set[str]:
    """조사에 덜 휘둘리도록 2글자 이상 낱말과 그 앞 2글자를 같이 담는다."""
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", text.lower())
    return set(words) | {w[:2] for w in words if len(w) > 2}


def select_context(context: str, question: str) -> str:
    """문서를 조각내고 질문과 겹치는 조각을 예산만큼 고른다.

    문서가 애초에 짧으면 그대로 쓴다. 고를 게 마땅치 않으면 앞부분을 쓴다.
    """
    if len(context) <= CONTEXT_CHAR_BUDGET:
        return context

    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", context) if p.strip()]
    chunks: list[str] = []
    for p in paras:
        if len(p) <= CHUNK_CHAR_SIZE:
            chunks.append(p)
        else:
            for i in range(0, len(p), CHUNK_CHAR_SIZE):
                chunks.append(p[i:i + CHUNK_CHAR_SIZE])

    q = _tokens(question)
    scored = []
    for i, c in enumerate(chunks):
        overlap = len(q & _tokens(c))
        scored.append((overlap, -i, i, c))
    scored.sort(reverse=True)

    # 겹치는 조각을 먼저 담되, 예산이 남으면 나머지로도 채운다.
    # 근거가 될 문장이 주변 조각에 걸쳐 있는 경우가 많아 빈 자리를 남기면 손해다.
    picked: list[tuple[int, str]] = []
    used = 0
    for overlap, _, i, c in scored:
        if used + len(c) > CONTEXT_CHAR_BUDGET:
            continue
        picked.append((i, c))
        used += len(c)

    if not picked:
        return context[:CONTEXT_CHAR_BUDGET]

    picked.sort()  # 문서에 나온 순서대로 되돌린다
    return "\n".join(c for _, c in picked)


def fit_for_detector(context: str, question: str, answer: str) -> str:
    """문서 + 질문 + 답변이 탐지기의 창 하나(512 토큰)에 들어가도록 문서를 줄인다.

    글자 수로 어림잡은 예산이 빗나갈 수 있어, 실제 토크나이저로 한 번 더 확인한다.
    창이 둘로 갈리는 순간 탐지가 무력해지므로 이 방어가 필요하다.
    """
    tok = detector.tok
    ans_n = len(tok(answer, add_special_tokens=False)["input_ids"])
    head_n = len(tok(f"질문: {question}\n\n문서:\n", add_special_tokens=False)["input_ids"])
    budget = 512 - ans_n - head_n - detector.n_special - 4
    if budget <= 0:
        return ""

    ids = tok(context, add_special_tokens=False)["input_ids"]
    if len(ids) <= budget:
        return context
    return tok.decode(ids[:budget])


# --------------------------------------------------------------------------
# 답변 생성 — 로컬 Ollama
# --------------------------------------------------------------------------
def generate_answer(context: str, question: str, loose: bool = False) -> tuple[str, str]:
    """(답변, 생성 방식) 을 돌려준다. Ollama 가 없으면 목업으로 넘어간다."""
    template = LOOSE_PROMPT if loose else PROMPT
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": template.format(context=context, question=question),
        "stream": False,
        # 답변이 길어지면 CPU 생성이 느려지고, 탐지기의 512 토큰 창도 넘긴다.
        "options": {
            "num_predict": ANSWER_TOKEN_CAP,
            "temperature": 0.9 if loose else 0.3,
        },
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        answer = (r.json().get("response") or "").strip()
        if answer:
            return answer, OLLAMA_MODEL
        print("[!] Ollama 가 빈 답변을 반환했습니다. 목업으로 대체합니다.")
    except requests.RequestException as e:
        print(f"[!] Ollama 를 쓸 수 없어 목업으로 대체합니다: {e}")

    return mock_answer(context, question), "mock"


def mock_answer(context: str, question: str) -> str:
    """Ollama 없이도 화면을 시연할 수 있게 만드는 가짜 답변.

    문서에서 실제로 가져온 문장(근거 있음) 뒤에 문서에 없는 문장(환각)을 붙여,
    탐지기가 형광펜을 칠할 거리를 일부러 만들어 준다.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+|\n+", context) if len(s.strip()) > 10]
    grounded = " ".join(sentences[:2]) if sentences else context[:200].strip()
    return (
        f"{grounded} "
        "또한 해당 문서는 2019년 국제 표준 인증을 취득하였으며, "
        "전체 조항의 87%가 이미 사내 시스템에 반영 완료된 상태입니다."
    )


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
detector: Detector | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global detector
    if not (MODEL_DIR / "config.json").exists():
        raise RuntimeError(f"탐지 모델이 없습니다: {MODEL_DIR}")
    print("탐지 모델을 불러오는 중입니다...")
    detector = Detector(MODEL_DIR)
    yield


app = FastAPI(title="한국어 환각 탐지 API", lifespan=lifespan)


@app.post("/api/v1/chat-and-detect")
async def chat_and_detect(
    file: UploadFile = File(...),
    question: str = Form(...),
    threshold: float = Form(DEFAULT_THRESHOLD),
    loose: bool = Form(False),
):
    full_context = extract_text(await file.read(), file.filename)
    if not full_context.strip():
        raise HTTPException(status_code=400, detail="파일에서 텍스트를 추출하지 못했습니다.")

    # 답변 생성과 환각 검사 모두 같은 구간을 근거로 삼아야 결과가 일관된다.
    context = select_context(full_context, question)

    answer, generated_by = generate_answer(context, question, loose=loose)

    # 답변 길이까지 알고 난 뒤 창 하나에 확실히 들어가도록 한 번 더 줄인다.
    context = fit_for_detector(context, question, answer)
    chunks, suspicious_count, suspicious_ratio = detector.highlighted(
        context, question, answer, float(threshold)
    )

    return {
        "answer": answer,
        "chunks": [{"text": t, "label": label} for t, label in chunks],
        "suspicious_count": suspicious_count,
        "suspicious_ratio": suspicious_ratio,
        "generated_by": generated_by,
        "context_chars": len(context),
        "document_chars": len(full_context),
    }


class FalsePositiveReport(BaseModel):
    answer: str
    question: str | None = None
    flagged: list[str] = []


@app.post("/api/v1/report-false-positive")
def report_false_positive(report: FalsePositiveReport):
    """오탐지 신고를 파일에 한 줄씩 쌓아 둔다."""
    record = {"at": datetime.now().isoformat(timespec="seconds"), **report.model_dump()}
    with REPORT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


@app.get("/api/v1/health")
def health():
    """Ollama 가 살아 있는지, 지금 답변을 무엇으로 만드는지 알려준다."""
    try:
        requests.get(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=2).raise_for_status()
        return {"detector": detector is not None, "generator": OLLAMA_MODEL, "ollama": True}
    except requests.RequestException:
        return {"detector": detector is not None, "generator": "mock", "ollama": False}


# 빌드된 React 앱 서빙 — 개발 서버 없이 이 서버 하나로 화면까지 띄운다.
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
