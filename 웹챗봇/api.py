"""문서 기반 질의응답 + 환각 탐지 통합 API (로컬 CPU 전용).

업로드한 PDF/TXT 에서 본문을 뽑아 그것을 근거로 로컬 Ollama 가 답을 만들고,
그 답을 app_cpu.py 의 Detector 로 검사해 환각 의심 구간까지 한 번에 돌려준다.

실행
  uvicorn api:app --reload --port 8000
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app_cpu import HERE, MODEL_DIR, DEFAULT_THRESHOLD, Detector

# 윈도우 콘솔은 cp949 라, 로그에 한글 밖의 기호가 하나 섞이면 print 가 예외를 던지고
# 그 예외가 요청 처리를 통째로 죽인다. 로그 때문에 서비스가 멈추는 일은 없어야 한다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

# 답변 생성은 성능 좋은 클라우드 모델에 맡기고, 환각 검증만 노트북 CPU 에서 돌린다.
# 키가 없거나 네트워크가 끊기면 로컬 Ollama → 목업 순으로 내려간다. 발표 중에
# 화면이 죽는 것보다 품질이 떨어지는 편이 낫다.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# latest 별칭은 몰리는 탓에 503/429 가 잦다(실측 4번 중 1번 성공). 버전을 박는 편이
# 훨씬 안정적이다. 더 빠른 쪽이 필요하면 GEMINI_MODEL=gemini-3.1-flash-lite (평균 4초).
# 이 모델이 언젠가 내려가면 404 가 나므로, 그때 목록을 다시 받아 갱신해야 한다.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_TIMEOUT = 60

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:1b")
OLLAMA_TIMEOUT = 300

STATIC_DIR = HERE / "frontend" / "dist"
REPORT_LOG = HERE / "false_positive_reports.jsonl"

# 탐지기는 512 토큰까지만 본다. 이 한계를 넘기면 문서를 창 여러 개로 쪼개 훑는데,
# 그러면 창별 확률이 서로를 눌러 환각을 하나도 못 잡는다(창이 많을수록 심해진다).
# 그래서 문서는 창 하나에 들어갈 만큼만 넣고, 답변이 길면 문장 단위로 나눠 여러 번 검사한다.
# 답변 쪽을 나누는 방식이라 답변 길이에 상한을 둘 필요가 없다.
ANSWER_TOKEN_CAP = 512          # 생성 답변 길이 상한 (잘림 방지용으로 넉넉히)
ANSWER_SEGMENT_TOKENS = 180     # 검사 한 번에 볼 답변 분량. 문서 몫을 남기려고 잡아 둔다
CONTEXT_CHAR_BUDGET = 620       # 문서에서 추려 넣을 분량
CHUNK_CHAR_SIZE = 200
DETECTOR_MAX_TOKENS = 512

# 기본 경로. 생성 모델에게는 문서를 주지 않는다. 자기가 아는 대로 답하게 두고,
# 그 답변을 업로드한 문서와 대조하는 일은 탐지 모델에게 맡긴다.
# 생성과 검증을 분리해야 탐지 모델이 무엇을 하는지가 드러난다.
STANDALONE_PROMPT = """다음 질문에 한국어로 답하세요.

질문: {question}

답변:"""

# 비교용. 문서를 함께 주면 생성 모델이 문서 안에서만 답하려 하므로 환각이 크게 줄어든다.
GROUNDED_PROMPT = """다음 문서만 근거로 질문에 한국어로 답하세요.
문서에 없는 내용은 지어내지 말고, 모르면 모른다고 답하세요.

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
# 질문에서 걷어낼 말. 의문사와 빈 명사는 문서에 드물게 나오는 탓에 IDF 가 오히려
# 높은 점수를 준다. "어느 정도의" 의 "정도" 가 "중등정도의" 에 걸려 엉뚱한 조각이
# 1위로 올라오는 식이라, 아예 질문에서 지우고 시작한다.
QUESTION_NOISE = re.compile(
    r"어느|어떤|어떻게|얼마나|얼마|무엇|무슨|언제|어디|왜|정도|가해|대해|대한|관해|관한|"
    r"알려|설명|해줘|주세요|인가요|입니까|있나요|하나요|합니까|될까요|뭐야|뭔지|건가요|"
    r"이야기|말해|궁금"
)


def _tokens(text: str) -> set[str]:
    """한글은 글자 2-gram, 영문·숫자는 낱말 단위로 쪼갠다.

    낱말 단위로만 맞추면 조사와 합성어에 걸려 다 빗나간다. 질문의 "독성" 이
    문서의 "생태독성"·"독성을" 과 안 맞는 식이다. 형태소 분석기를 쓰면 깔끔하지만
    의존성이 늘어서, 한국어 검색에서 흔히 쓰는 2-gram 으로 대신한다.
    """
    low = text.lower()
    words = set(re.findall(r"[a-z0-9][a-z0-9.\-]*[a-z0-9]", low))
    grams = set()
    for run in re.findall(r"[가-힣]{2,}", low):
        grams.update(run[i:i + 2] for i in range(len(run) - 1))
    return words | grams


# 어떤 질문에도 근거가 될 수 없는 상용구. 표지·출처·법적 고지가 여기 걸린다.
# 이걸 안 걸러내면 문서 머리말이 예산을 다 먹어 정작 필요한 수치가 밀려난다.
BOILERPLATE = re.compile(
    r"https?\s*:|출처\s*:|저작권|산업안전보건법 제\d+조|책임을 물을 수 없|상업적 용도|"
    r"페이지 저장일|헤드리스|MSDS ?상세정보|경고표지|인쇄 또는 저장|편집 목록|참고용으로만|"
    r"제공 ?받으|위배 ?될"
)


def _split_units(context: str) -> list[str]:
    """문서를 조각낸다. MSDS 처럼 번호 항목이 있으면 그 경계를 살린다.

    번호 항목은 법으로 순서가 정해져 있어서(11. 독성, 12. 환경 영향 …) 질문과
    맞는 항목을 통째로 집는 편이 낫다. 줄 중간에서 자르면 수치가 반토막 난다.
    """
    marks = [m.start() for m in re.finditer(r"(?m)^\s*\d{1,2}\.\s*[가-힣]", context)]
    if len(marks) >= 3:
        bounds = marks + [len(context)]
        units = [context[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]
    else:
        units = re.split(r"\n\s*\n", context)

    out: list[str] = []
    for u in units:
        # 상용구는 줄 단위로 걷어낸다. 조각째 버리면 "※출처 : ECHA" 한 줄 때문에
        # 같은 조각에 있는 "어류 LC50 5.5 ㎎/ℓ" 같은 실제 데이터까지 날아간다.
        lines = [ln for ln in u.splitlines() if ln.strip() and not BOILERPLATE.search(ln)]
        if not lines:
            continue

        cur = ""
        for line in lines:                   # 줄 경계에서만 자른다
            if cur and len(cur) + len(line) > CHUNK_CHAR_SIZE:
                out.append(cur.strip())
                cur = line
            else:
                cur = f"{cur}\n{line}" if cur else line
        if cur.strip():
            out.append(cur.strip())
    return out


def select_context(context: str, question: str) -> str:
    """질문과 관련된 구간만 골라 낸다. 문서가 짧으면 그대로 쓴다."""
    if len(context) <= CONTEXT_CHAR_BUDGET:
        return context

    chunks = _split_units(context)
    q = _tokens(QUESTION_NOISE.sub(" ", question))

    # 문서 전체에 흔한 낱말은 변별력이 없다. 톨루엔 MSDS 에서 "톨루엔" 이 그렇다.
    # 어느 조각에나 있으니 이걸 세면 질문마다 같은 조각이 뽑힌다. 드문 낱말
    # (어류, 인화점, 누출)에 무게를 실어야 질문에 맞는 항목이 올라온다.
    chunk_tokens = [_tokens(c) for c in chunks]
    n = len(chunks)

    # 문서 주제어(제목에 나오는 말)는 변별력이 없다. 톨루엔 MSDS 는 전부가 톨루엔
    # 이야기라 어느 조각을 골라도 맞다. 그런데 "톨루엔" 이 2-gram 으로 쪼개지면
    # 톨루+루엔 두 몫을 챙겨, 정작 질문의 핵심어를 가진 조각을 눌러 버린다.
    subject = _tokens(context[:300])

    weight = {}
    for t in q:
        df = sum(1 for ct in chunk_tokens if t in ct)
        w = math.log((n + 1) / (df + 1)) if df else 0.0
        weight[t] = w * 0.15 if t in subject else w

    scored = []
    for i, c in enumerate(chunks):            # 상용구는 조각을 만들 때 이미 걸러 냈다
        score = sum(weight[t] for t in q & chunk_tokens[i])
        if score > 0:
            scored.append((score, -len(c), i))
    scored.sort(reverse=True)

    picked: set[int] = set()
    used = 0
    for _, _, i in scored:
        if used + len(chunks[i]) > CONTEXT_CHAR_BUDGET:
            continue
        picked.add(i)
        used += len(chunks[i])

    # 남은 자리는 고른 조각의 바로 앞뒤로만 넓힌다. 근거 수치가 옆 줄에 있는 일이
    # 많아서인데, 아무 데나 채우면 다시 머리말이 딸려 들어온다.
    for i in sorted(picked):
        for j in (i - 1, i + 1):
            if 0 <= j < len(chunks) and j not in picked:
                if used + len(chunks[j]) <= CONTEXT_CHAR_BUDGET:
                    picked.add(j)
                    used += len(chunks[j])

    if not picked:
        return context[:CONTEXT_CHAR_BUDGET]
    return "\n".join(chunks[i] for i in sorted(picked))


def fit_for_detector(context: str, question: str) -> str:
    """문서가 탐지기의 창 하나에 들어가도록 줄인다. 답변 몫은 따로 남겨 둔다.

    글자 수로 어림잡은 예산이 빗나갈 수 있어 실제 토크나이저로 한 번 더 확인한다.
    창이 둘로 갈리는 순간 탐지가 무력해지므로 이 방어가 필요하다.
    """
    tok = detector.tok
    head_n = len(tok(f"질문: {question}\n\n문서:\n", add_special_tokens=False)["input_ids"])
    budget = DETECTOR_MAX_TOKENS - ANSWER_SEGMENT_TOKENS - head_n - detector.n_special - 4
    if budget <= 0:
        return ""

    ids = tok(context, add_special_tokens=False)["input_ids"]
    if len(ids) <= budget:
        return context
    return tok.decode(ids[:budget])


def split_answer(context: str, question: str, answer: str) -> list[str]:
    """답변이 남은 창에 안 들어가면 문장 단위로 나눈다.

    답변 길이를 제한하는 대신 나눠서 여러 번 검사한다. 예전에는 생성 자체를
    160 토큰으로 잘랐는데, 그러면 안전 지침 같은 긴 답변이 문장 중간에서 끊겼다.
    """
    tok = detector.tok
    head_n = len(tok(f"질문: {question}\n\n문서:\n{context}", add_special_tokens=False)["input_ids"])
    budget = DETECTOR_MAX_TOKENS - head_n - detector.n_special - 4
    if budget < 32:
        budget = 32

    if len(tok(answer, add_special_tokens=False)["input_ids"]) <= budget:
        return [answer]

    # 자를 자리만 잡고 원문을 그대로 잘라 낸다. 이어 붙이면 원래 답변과 정확히 같아야
    # 화면에 줄바꿈과 번호 매김이 살아 있다.
    cuts = [m.end() for m in re.finditer(r"(?<=[.!?。])\s+|\n+", answer)]
    cuts.append(len(answer))

    parts: list[str] = []
    start = 0
    last = 0
    for c in cuts:
        if c <= start:
            continue
        if len(tok(answer[start:c], add_special_tokens=False)["input_ids"]) > budget and last > start:
            parts.append(answer[start:last])
            start = last
        last = c
    if start < len(answer):
        parts.append(answer[start:])
    return parts or [answer]


LABEL_CONFLICT = "오류"          # 문서가 다루는 내용인데 세부가 어긋남
LABEL_ABSENT = "문서에 없음"      # 문서가 아예 다루지 않는 내용
LABEL_SUPPORTED = "문서에서 확인"  # 문서에서 근거를 찾은 문장


def _sentences(text: str) -> list[str]:
    """문장 단위로 나눈다. 이어 붙이면 원문과 정확히 같아야 한다."""
    out, start = [], 0
    for m in re.finditer(r"(?<=[.!?。])\s+|\n+", text):
        out.append(text[start:m.end()])
        start = m.end()
    if start < len(text):
        out.append(text[start:])
    return out


def is_supported(sentence: str, context: str) -> bool:
    """이 문장이 문서에서 확인되는지 어휘로 따진다.

    탐지 모델은 환각만 표시하고 나머지는 그냥 표시하지 않는다. 표시가 없다는 건
    "근거가 있다" 가 아니라 "잡히지 않았다" 는 뜻이다. 그래서 초록은 모델의 침묵이
    아니라, 문서에서 실제로 어휘를 찾은 문장에만 칠한다.
    """
    words = _tokens(ENDING_NOISE.sub(" ", re.sub(r"[\d.,]+", " ", sentence)))
    if len(words) < 4:                       # 짧은 조각은 판단하지 않는다
        return False
    return len(words & _tokens(context)) / len(words) >= 0.6


# 어느 문장에나 붙는 어미. 주제어 비율을 재는 데 방해가 된다.
ENDING_NOISE = re.compile(
    r"입니다|습니다|합니다|됩니다|있습|없습|이며|하며|하고|이고|으로|하는|되는|"
    r"수 있|것으로|같습니다|바랍니다|하시오|하십시오|해야|한다|이다"
)


def _sentence_at(text: str, start: int, end: int) -> str:
    """구간이 속한 문장을 돌려준다. 구간만 보면 주제를 알 수 없기 때문이다.

    탐지기는 "40℃" 처럼 값만 잘라 내기도 한다. 그 조각만으로는 무엇에 대한
    값인지 알 수 없어, 같은 문장에 있는 항목명까지 함께 봐야 한다.
    """
    left = max(text.rfind(m, 0, start) for m in (". ", "\n", "! ", "? ")) if start else -1
    right = min((p for p in (text.find(m, end) for m in (". ", "\n", "! ", "? ")) if p != -1),
                default=-1)
    return text[(left + 1 if left != -1 else 0): (right if right != -1 else len(text))]


def classify_span(span: str, sentence: str, context: str) -> str:
    """형광펜 구간을 두 종류로 나눈다.

    탐지 모델은 SUPPORTED / HALLUCINATED 두 가지만 내놓는다. "값이 틀렸다" 와
    "문서에 없는 말이다" 를 구분하지 않는다. 그래서 여기서 어휘를 대조해 나눈다.
    모델의 판단이 아니라 그 위에 얹은 규칙이므로 틀릴 수 있다.

    문서가 이 주제를 다루고 있으면(어휘가 겹치면) 어긋난 쪽은 세부 값이라고 보고,
    주제 자체가 문서에 없으면 근거 부재로 본다.
    """
    topic = ENDING_NOISE.sub(" ", re.sub(r"[\d.,]+", " ", sentence or span))
    words = _tokens(topic)
    if not words:
        return LABEL_ABSENT

    ctx_words = _tokens(context)
    coverage = len(words & ctx_words) / len(words)

    span_nums = set(re.findall(r"\d+(?:\.\d+)?", span))
    ctx_nums = set(re.findall(r"\d+(?:\.\d+)?", context))
    # 문서에 없는 값을 말하는데 그 항목은 문서가 다루고 있으면, 값이 어긋난 것이다.
    if span_nums and not (span_nums & ctx_nums) and coverage >= 0.3:
        return LABEL_CONFLICT
    return LABEL_CONFLICT if coverage >= 0.5 else LABEL_ABSENT


def detect(context: str, question: str, answer: str, threshold: float):
    """긴 답변은 나눠서 검사하고 결과를 이어 붙인다."""
    segments = split_answer(context, question, answer)
    chunks: list[tuple[str, str | None]] = []
    n_spans = 0
    marked = 0
    for seg in segments:
        seg_chunks, seg_n, seg_ratio = detector.highlighted(context, question, seg, threshold)
        pos = 0
        for text, label in seg_chunks:
            if label:
                sentence = _sentence_at(seg, pos, pos + len(text))
                chunks.append((text, classify_span(text, sentence, context)))
            else:
                # 안 걸린 구간은 문장별로 따져 문서에서 확인되는 것만 초록으로 둔다.
                for sent in _sentences(text):
                    chunks.append((sent, LABEL_SUPPORTED if is_supported(sent, context) else None))
            pos += len(text)
        n_spans += seg_n
        marked += seg_ratio * len(seg)
    return chunks, n_spans, marked / max(len(answer), 1)


# --------------------------------------------------------------------------
# 답변 생성 — 로컬 Ollama
# --------------------------------------------------------------------------
def generate_answer(context: str, question: str, grounded: bool = False) -> tuple[str, str]:
    """(답변, 생성 방식) 을 돌려준다.

    grounded=False 가 기본이다. 생성 모델에게 문서를 주지 않고 자기가 아는 대로
    답하게 둔다. 문서와 대조하는 일은 탐지 모델이 맡는다.
    """
    prompt = (GROUNDED_PROMPT.format(context=context, question=question) if grounded
              else STANDALONE_PROMPT.format(question=question))

    if GEMINI_API_KEY:
        answer = _try_gemini(prompt)
        if answer:
            return answer, GEMINI_MODEL

    answer = _try_ollama(prompt)
    if answer:
        return answer, OLLAMA_MODEL

    return mock_answer(context, question), "mock"


def _try_gemini(prompt: str) -> str:
    base = {"maxOutputTokens": ANSWER_TOKEN_CAP, "temperature": 0.3}
    # 생각 단계를 끈다. 켜 두면 출력 토큰을 다 먹어 답변이 몇 글자에서 잘린다.
    # 이 옵션을 받지 않는 모델도 있어(400), 그때는 빼고 한 번 더 시도한다.
    for cfg in ({**base, "thinkingConfig": {"thinkingBudget": 0}}, base):
        # 503(과부하)·429(한도)는 잠시 뒤 풀리는 경우가 많다. 바로 로컬로 내려가면
        # 발표 도중 답변 품질이 널뛰므로 몇 번 더 두드려 본다.
        for attempt in range(3):
            try:
                r = requests.post(
                    GEMINI_URL.format(model=GEMINI_MODEL),
                    json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg},
                    headers={"x-goog-api-key": GEMINI_API_KEY},
                    timeout=GEMINI_TIMEOUT,
                )
                if r.status_code == 400 and "thinkingConfig" in cfg:
                    break  # 이 모델은 해당 옵션을 안 받는다 → 옵션 빼고 재시도
                if r.status_code in (429, 503) and attempt < 2:
                    print(f"[!] Gemini {r.status_code}, {2 ** attempt}초 뒤 재시도")
                    time.sleep(2 ** attempt)
                    continue
                r.raise_for_status()
                parts = r.json()["candidates"][0]["content"]["parts"]
                answer = "".join(p.get("text", "") for p in parts).strip()
                if answer:
                    return answer
                break
            except (requests.RequestException, KeyError, IndexError) as e:
                print(f"[!] Gemini 호출 실패: {e}")
                return ""
    return ""


def _try_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": ANSWER_TOKEN_CAP, "temperature": 0.3},
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        r.raise_for_status()
        return (r.json().get("response") or "").strip()
    except requests.RequestException as e:
        print(f"[!] Ollama 도 쓸 수 없어 목업으로 대체합니다: {e}")
        return ""


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
    grounded: bool = Form(False),
):
    full_context = extract_text(await file.read(), file.filename)
    if not full_context.strip():
        raise HTTPException(status_code=400, detail="파일에서 텍스트를 추출하지 못했습니다.")

    # 답변 생성과 환각 검사 모두 같은 구간을 근거로 삼아야 결과가 일관된다.
    context = select_context(full_context, question)

    answer, generated_by = generate_answer(context, question, grounded=grounded)

    # 문서를 창 하나에 맞추고, 답변이 길면 나눠서 검사한다.
    context = fit_for_detector(context, question)
    chunks, suspicious_count, suspicious_ratio = detect(
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
    """지금 무엇이 답변을 만들고 무엇이 검증하는지 알려준다."""
    try:
        requests.get(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=2).raise_for_status()
        ollama_up = True
    except requests.RequestException:
        ollama_up = False

    if GEMINI_API_KEY:
        generator = GEMINI_MODEL
    elif ollama_up:
        generator = OLLAMA_MODEL
    else:
        generator = "mock"

    return {
        "detector": detector is not None,   # 항상 로컬 CPU
        "generator": generator,
        "gemini_key": bool(GEMINI_API_KEY),
        "ollama": ollama_up,
    }


# 빌드된 React 앱 서빙 — 개발 서버 없이 이 서버 하나로 화면까지 띄운다.
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
