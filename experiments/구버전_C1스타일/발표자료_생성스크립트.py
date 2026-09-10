# -*- coding: utf-8 -*-
"""C1 1주차 발표자료 템플릿을 따라 'AI 프로젝트 아이디어' 덱 생성"""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ---------- 팔레트 ----------
BG        = RGBColor(0xE9, 0xEF, 0xF7)
PILL_L    = RGBColor(0xC2, 0xD8, 0xEF)
PILL_R    = RGBColor(0xEE, 0xF4, 0xFB)
COVER_PIL = RGBColor(0xBF, 0xD6, 0xEE)
COVER_BRD = RGBColor(0xA9, 0xC4, 0xDF)
COLHEAD   = RGBColor(0xB9, 0xD1, 0xE9)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
INK       = RGBColor(0x22, 0x2B, 0x35)
BODY      = RGBColor(0x3A, 0x42, 0x4C)
GREY      = RGBColor(0x6B, 0x76, 0x84)
ACCENT    = RGBColor(0x2F, 0x6F, 0xB5)
BADGE_BRD = RGBColor(0xC8, 0xD6, 0xE6)
CARD_BRD  = RGBColor(0xE2, 0xE9, 0xF2)

FONT = "맑은 고딕"

# ---------- 지오메트리 (inch, 13.333 x 7.5) ----------
SW, SH   = 13.333, 7.5
PILL     = (0.245, 0.225, 8.16, 0.73)
BADGE_C  = (7.97, 0.59, 0.50)          # cx, cy, diameter
CARD     = (0.245, 1.155, 12.87, 6.21)
COL_W, COL_GAP = 3.74, 0.34
COL_X    = [0.73, 0.73 + COL_W + COL_GAP, 0.73 + 2 * (COL_W + COL_GAP)]
COL_TOP  = 1.86
COL_BOT  = 6.85
HEAD_H   = 0.55
PAGENO_Y = 7.10


def _round(shape, adj=0.16):
    try:
        shape.adjustments[0] = adj
    except Exception:
        pass


def add_shape(slide, kind, x, y, w, h, fill=None, line=None, adj=0.16):
    s = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        _round(s, adj)
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def add_grad_pill(slide, x, y, w, h):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                               Inches(x), Inches(y), Inches(w), Inches(h))
    _round(s, 0.42)
    s.fill.gradient()
    s.fill.gradient_angle = 0.0
    stops = s.fill.gradient_stops
    stops[0].color.rgb = PILL_L
    stops[0].position = 0.0
    stops[1].color.rgb = PILL_R
    stops[1].position = 1.0
    s.line.fill.background()
    s.shadow.inherit = False
    return s


def tb(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = t.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def run(p, text, size, bold=False, color=BODY, font=FONT):
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = font
    return r


EMU_IN = 914400


def hang(p, marL=0.155):
    """불릿 걸어쓰기(hanging indent)"""
    pPr = p._pPr if p._pPr is not None else p._p.get_or_add_pPr()
    pPr.set("marL", str(int(marL * EMU_IN)))
    pPr.set("indent", str(int(-marL * EMU_IN)))


def para(tf, first, space_before=0, space_after=4, line=1.28, align=PP_ALIGN.LEFT,
         indent=0.0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = line
    p.alignment = align
    if indent:
        p.left_indent = Inches(indent)
    return p


def slide_base(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = add_shape(s, MSO_SHAPE.RECTANGLE, 0, 0, SW, SH, fill=BG)
    bg.line.fill.background()
    return s


# ---------- 본문 컬럼 렌더러 ----------
# item = (kind, text) ; kind: 'b'(불릿) 'h'(소제목) 'p'(설명) 'a'(기술스택 강조)
# 불릿 텍스트에 '||' 가 있으면 뒷부분을 강조색으로

def render_column(slide, idx, title, items, body_size=10.5, col_bot=COL_BOT):
    x = COL_X[idx]
    body_top = COL_TOP + 0.30
    add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, body_top, COL_W,
              col_bot - body_top, fill=WHITE, line=CARD_BRD, adj=0.055)
    add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, COL_TOP, COL_W, HEAD_H,
              fill=COLHEAD, adj=0.30)
    ht = tb(slide, x, COL_TOP + 0.10, COL_W, 0.36, MSO_ANCHOR.MIDDLE)
    hp = para(ht, True, align=PP_ALIGN.CENTER, space_after=0)
    run(hp, title, 14.5, True, INK)

    tf = tb(slide, x + 0.20, body_top + 0.30, COL_W - 0.40, col_bot - body_top - 0.42)
    first = True
    for kind, text in items:
        if kind == "b":
            p = para(tf, first, space_after=6)
            hang(p)
            head, _, tail = text.partition("||")
            run(p, "• ", body_size, False, BODY)
            run(p, head, body_size, False, BODY)
            if tail:
                run(p, tail, body_size, False, ACCENT)
        elif kind == "h":
            p = para(tf, first, space_before=4 if not first else 0, space_after=1)
            hang(p)
            run(p, "• ", body_size, True, BODY)
            run(p, text, body_size, True, INK)
        elif kind == "p":
            p = para(tf, first, space_after=1, indent=0.13)
            run(p, text, body_size, False, BODY)
        elif kind == "a":
            p = para(tf, first, space_after=6, indent=0.13)
            run(p, "→ " + text, body_size, False, ACCENT)
        first = False


def content_slide(prs, num, title, subtitle, cols):
    s = slide_base(prs)
    add_grad_pill(s, *PILL)
    tf = tb(s, PILL[0] + 0.35, PILL[1] + 0.09, PILL[2] - 1.4, 0.58)
    p = para(tf, True, space_after=1)
    run(p, title, 19, True, INK)
    p = para(tf, False, space_after=0)
    run(p, subtitle, 9.5, False, GREY)

    cx, cy, d = BADGE_C
    add_shape(s, MSO_SHAPE.OVAL, cx - d / 2, cy - d / 2, d, d,
              fill=WHITE, line=BADGE_BRD)
    btf = tb(s, cx - d / 2, cy - 0.14, d, 0.28, MSO_ANCHOR.MIDDLE)
    bp = para(btf, True, align=PP_ALIGN.CENTER, space_after=0)
    run(bp, str(num), 15, False, GREY)

    add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, *CARD, fill=WHITE, adj=0.035)
    for i, (ct, items, size) in enumerate(cols):
        render_column(s, i, ct, items, size)

    ptf = tb(s, 0, PAGENO_Y, SW, 0.3)
    pp = para(ptf, True, align=PP_ALIGN.CENTER, space_after=0)
    run(pp, str(num + 1), 10, False, GREY)
    return s


# =======================================================================
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)

# ---------- 표지 ----------
s = slide_base(prs)
tf = tb(s, 0.245, 0.26, 6.0, 0.35)
p = para(tf, True, space_after=0)
run(p, "청년 AI·Big Data 아카데미 34기", 14, True, INK)

add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 2.93, 3.02, 7.67, 1.15,
          fill=COVER_PIL, line=COVER_BRD, adj=0.48)
tf = tb(s, 2.93, 3.25, 7.67, 0.7, MSO_ANCHOR.MIDDLE)
p = para(tf, True, align=PP_ALIGN.CENTER, space_after=0)
run(p, "AI 프로젝트 아이디어", 38, True, GREY)

tf = tb(s, 0, 4.52, SW, 0.35)
p = para(tf, True, align=PP_ALIGN.CENTER, space_after=0)
run(p, "○조   양진우", 13, False, INK)

# ---------- 목차 ----------
s = slide_base(prs)
add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.245, 0.30, 1.58, 0.62,
          fill=COVER_PIL, adj=0.45)
tf = tb(s, 0.245, 0.30, 1.58, 0.62, MSO_ANCHOR.MIDDLE)
p = para(tf, True, align=PP_ALIGN.CENTER, space_after=0)
run(p, "목차", 22, True, INK)

TOC = [
    "1. 근거가 보이는 AI 상담 챗봇  —  LLM 환각 판별 (작은 모델이 큰 모델을 검증)",
    "2. 실시간 발표 코칭 AI  —  음성·영상 멀티모달 분석",
    "3. 베어링 진동 신호 기반 고장진단 및 잔여수명(RUL) 예측",
    "4. 시각·음향 융합 공간 쾌적도 분석 AI",
    "5. 고령층 다제복용 알약 식별 및 상호작용 위험 분석 AI",
]
tf = tb(s, 1.09, 2.05, 11.5, 4.3)
for i, t in enumerate(TOC):
    p = para(tf, i == 0, space_after=22, line=1.0)
    run(p, t, 15.5, False, RGBColor(0x1F, 0x3B, 0x5C))

# =======================================================================
# 1. 환각 판별 AI
content_slide(
    prs, 1,
    "근거가 보이는 AI 상담 챗봇  —  LLM 환각 판별",
    "답변에 형광펜, 틀린 구간을 지목 · 소형 검증 모델 직접 학습 · 지원사업/법률 문서 대상",
    [
        ("추진배경", [
            ("b", "LLM은 그럴듯하지만 틀린 답을 만든다. 법률·의료처럼 오답이 실제 피해로 이어지는 분야에서 치명적"),
            ("b", "기본 RAG로는 부족 — 근거를 찾아줘도 LLM이 이를 무시하거나 왜곡해 요약한다"),
            ("b", "검증을 거대 LLM에 맡기면 답변 1건당 수십 회 호출 → ||비용·지연으로 실시간 불가"),
            ("b", "\"사실인가\"를 검증하면 세상의 진실을 알아야 해 무한 후퇴 → ||\"근거와 일치하는가\"로 정의를 좁혀야 성립"),
        ], 10.5),
        ("주요기능", [
            ("h", "문장·구간 단위 환각 판별"),
            ("p", "답변을 주장 단위로 분해해 지지 / 반박 / 정보부족 3분류, 틀린 부분은 구간(span)으로 지목"),
            ("a", "DeBERTa 계열 NLI 파인튜닝"),
            ("h", "검증자의 환각까지 차단"),
            ("p", "검증 모델이 인용한 근거 구간이 원문에 실제 존재하는지 문자열 매칭으로 기계 확인"),
            ("a", "Citation Grounding"),
            ("h", "신뢰도 시각화 UI"),
            ("p", "답변 문장마다 초록·노랑·빨강 표시, 클릭 시 근거 문서의 해당 구간 하이라이트"),
            ("a", "RAG + FastAPI + React"),
        ], 10.0),
        ("기대효과", [
            ("b", "||3분 시연에서 결과가 눈에 보인다 — 답변에 형광펜이 그어지고 클릭하면 근거가 열린다"),
            ("b", "파라미터가 100배 작은 모델이 거대 LLM의 환각을 잡아낸다 → ||\"우리가 모델을 만들었다\"가 성립"),
            ("b", "동일 GPU에서 측정한 ||비용·지연 우위를 실측 그래프로 제시"),
            ("b", "검증: RAGTruth·FEVER 공개 데이터셋, 베이스라인은 ||LLM에게 그냥 물어보기(self-check)"),
            ("b", "지표: 문장 F1, 구간 IoU, 3분류 정확도, 신뢰도 보정(ECE)"),
            ("b", "실습실 A5000 6대로 ||모델 크기별 성능-비용 곡선까지 제시 가능"),
        ], 10.5),
    ])

# 1-보충 : 팀원 기획안과의 결합
s = slide_base(prs)
add_grad_pill(s, *PILL)
tf = tb(s, PILL[0] + 0.35, PILL[1] + 0.09, PILL[2] - 1.4, 0.58)
p = para(tf, True, space_after=1)
run(p, "[보충] 1번 아이디어 — 팀원 기획안과 합치면", 19, True, INK)
p = para(tf, False, space_after=0)
run(p, "환각 방지 RAG 챗봇 + 소형 검증 모델 · 서로의 빈칸을 정확히 메운다", 9.5, False, GREY)
cx, cy, d = BADGE_C
add_shape(s, MSO_SHAPE.OVAL, cx - d / 2, cy - d / 2, d, d, fill=WHITE, line=BADGE_BRD)
btf = tb(s, cx - d / 2, cy - 0.14, d, 0.28, MSO_ANCHOR.MIDDLE)
bp = para(btf, True, align=PP_ALIGN.CENTER, space_after=0)
run(bp, "1+", 13, False, GREY)
add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, *CARD, fill=WHITE, adj=0.035)

HALF_W = 5.72
for i, (x, head, items) in enumerate([
    (0.73, "팀원 기획안이 이미 갖춘 것", [
        ("b", "도메인·데이터가 구체적 — 법률(국가법령정보센터 API), 조항 단위 청킹"),
        ("b", "3유형 평가셋 설계 — 사실확인 50% / 조건부 30% / ||범위밖 20%"),
        ("b", "근거 인용 강제·답변 거부 메커니즘 프롬프트 설계"),
        ("b", "RAGAS 기반 정량 평가 체계, 5주 WBS와 5인 역할 분담까지 완비"),
        ("b", "비어 있는 곳 → ||자기검증이 \"스트레치 목표\"로 밀려 있고, 직접 학습하는 모델이 없다"),
    ]),
    (6.88, "내 아이디어가 채우는 것", [
        ("b", "그 \"스트레치 목표\"를 ||프로젝트의 본체로 격상"),
        ("b", "검증기를 프롬프트가 아니라 ||소형 NLI 모델로 직접 학습 → API 래퍼 지적을 원천 차단"),
        ("b", "문장 단위를 넘어 ||구간(span) 단위로 틀린 곳을 지목"),
        ("b", "지지/반박/정보부족 3분류로 ||검색 실패와 실제 오답을 구분"),
        ("b", "필요한 것 → ||검증 대상이 될 RAG 챗봇과 도메인. 팀원 기획안이 그대로 무대가 된다"),
    ]),
]):
    add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, COL_TOP + 0.30, HALF_W, 2.50,
              fill=WHITE, line=CARD_BRD, adj=0.08)
    add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, COL_TOP, HALF_W, HEAD_H,
              fill=COLHEAD, adj=0.30)
    ht = tb(s, x, COL_TOP + 0.10, HALF_W, 0.36, MSO_ANCHOR.MIDDLE)
    hp = para(ht, True, align=PP_ALIGN.CENTER, space_after=0)
    run(hp, head, 14.5, True, INK)
    tf = tb(s, x + 0.22, COL_TOP + 0.64, HALF_W - 0.44, 2.1)
    for j, (k, t) in enumerate(items):
        p = para(tf, j == 0, space_after=6)
        hang(p)
        h_, _, tl = t.partition("||")
        run(p, "• ", 10.5, False, BODY)
        run(p, h_, 10.5, False, BODY)
        if tl:
            run(p, tl, 10.5, False, ACCENT)

BOT_T = 4.88
add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.73, BOT_T + 0.30, 11.87, 1.67,
          fill=WHITE, line=CARD_BRD, adj=0.10)
add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.73, BOT_T, 11.87, HEAD_H,
          fill=COLHEAD, adj=0.30)
ht = tb(s, 0.73, BOT_T + 0.10, 11.87, 0.36, MSO_ANCHOR.MIDDLE)
hp = para(ht, True, align=PP_ALIGN.CENTER, space_after=0)
run(hp, "합쳤을 때", 14.5, True, INK)
tf = tb(s, 0.95, BOT_T + 0.68, 11.43, 1.45)
p = para(tf, True, space_after=7)
run(p, "한 문장 : ", 11, True, INK)
run(p, "사람이 쓰는 상담 챗봇을 만들고, 그 답변의 환각을 100배 작은 모델이 구간 단위로 잡아낸다", 11, True, ACCENT)
for j, t in enumerate([
    "팀원 기획안의 1~2주차(데이터·지식베이스·baseline RAG)가 그대로 무대가 되고, 3~4주차의 신뢰성 장치가 우리 검증 모델로 대체된다",
    "RAGAS는 LLM 심판을 쓴다 → 우리 소형 모델과의 비용·지연·정확도 비교가 그 자체로 프로젝트의 성과 지표가 된다",
    "역할 분담이 자연스럽게 갈린다 :  데이터·RAG 구축  |  검증 모델 학습(본체)  |  평가셋·지표  |  프론트엔드·데모",
    "주의 — 앞에 세울 것은 \"검증 프레임워크\"가 아니라 사람이 쓰는 챗봇 화면이다. 검증은 그 제품의 기능으로 보여야 한다",
]):
    p = para(tf, False, space_after=5)
    hang(p)
    run(p, "• ", 10.5, False, BODY)
    run(p, t, 10.5, False, BODY)

ptf = tb(s, 0, PAGENO_Y, SW, 0.3)
pp = para(ptf, True, align=PP_ALIGN.CENTER, space_after=0)
run(pp, "3", 10, False, GREY)

# =======================================================================
# 2. 스피치 AI
content_slide(
    prs, 2,
    "실시간 발표 코칭 AI",
    "음성 + 영상 멀티모달 실시간 분석 · 말하는 도중 교정",
    [
        ("추진배경", [
            ("b", "발표 연습은 혼자 하면 무엇이 문제인지 알 수 없다. 피드백은 사후에, 그것도 주관적으로만 온다"),
            ("b", "스피치 학원·1:1 코칭은 비용이 크고 접근성이 낮다"),
            ("b", "기존 앱은 대부분 ||녹음 후 사후 분석에 그쳐 말하는 도중 교정이 불가능"),
            ("b", "취업 면접·발표 평가 비중은 커지는데 연습 수단은 거울과 녹화뿐"),
        ], 10.5),
        ("주요기능", [
            ("h", "실시간 음성 분석"),
            ("p", "말 속도(WPM), 필러워드(\"음·어\") 검출, 성량·떨림, 침묵 구간 자동 측정"),
            ("a", "Whisper + librosa / wav2vec"),
            ("h", "실시간 영상 분석"),
            ("p", "시선 방향, 자세 흔들림, 손동작 빈도를 프레임 단위로 추적"),
            ("a", "MediaPipe + CNN"),
            ("h", "멀티모달 종합 피드백"),
            ("p", "발표 중에는 화면에 실시간 게이지, 발표 후에는 구간별 개선 리포트 자동 생성"),
            ("a", "Multimodal Fusion + LLM 요약"),
        ], 10.0),
        ("기대효과", [
            ("b", "||발표장에서 즉석 시연이 가능 — 심사위원 앞에서 실시간 분석 화면을 띄우는 것 자체가 데모"),
            ("b", "면접·발표 준비의 비용 장벽 해소, 반복 연습의 정량적 근거 제공"),
            ("b", "검증: 연습 전후 지표 개선폭 + ||사람 평가자 점수와의 상관계수"),
            ("b", "음성·영상을 한 시점에 정렬해 융합하는 것이 기술적 난점이자 차별점"),
            ("b", "리스크: ||학습 데이터를 팀이 직접 녹화·라벨링해야 한다"),
        ], 10.5),
    ])

# 3. 베어링 RUL
content_slide(
    prs, 3,
    "베어링 진동 신호 기반 고장진단 및 잔여수명(RUL) 예측",
    "CNN + LSTM · 결함주파수 대조 검증 · 예지보전(PHM)",
    [
        ("추진배경", [
            ("b", "회전기계 고장은 ||설비 정지·안전사고·긴급 수리비로 직결된다"),
            ("b", "현장은 여전히 사람이 소리·진동으로 판단하거나 정기점검에 의존해 대응이 늦다"),
            ("b", "\"고장인가 아닌가\" 분류는 이미 흔하다 → ||\"앞으로 얼마나 더 쓸 수 있는가\"로 문제의 격을 올려야 한다"),
            ("b", "제조 현장 수요와 직결되어 포스코 맥락과 맞물린다"),
        ], 10.5),
        ("주요기능", [
            ("h", "진동 신호 고장 분류"),
            ("p", "원신호를 세그멘테이션·정규화 후 STFT 스펙트로그램으로 변환, 정상/내륜/외륜/볼 4분류"),
            ("a", "2D-CNN (ResNet18)"),
            ("h", "잔여수명(RUL) 회귀 예측"),
            ("p", "RMS·kurtosis 등 건강지표를 시간축으로 추출해 열화 추세를 학습, 남은 수명을 회귀 예측"),
            ("a", "CNN + LSTM"),
            ("h", "판단 근거 교차검증"),
            ("p", "베어링 스펙으로 결함주파수(BPFO/BPFI/BSF)를 직접 계산해 모델이 주목한 대역과 대조"),
            ("a", "Grad-CAM × 물리 계산"),
        ], 10.0),
        ("기대효과", [
            ("b", "||물리 계산과 AI 판단이 일치함을 보여 \"왜 그렇게 판단했나\"에 답할 수 있다"),
            ("b", "예지보전(PHM)의 실제 연구 주제와 일치 — 제조업 포트폴리오로서 설득력이 크다"),
            ("b", "검증: ||CWRU·IMS 공개 데이터셋, 부하조건(HP) 기준 분리로 일반화 성능 측정"),
            ("b", "||데이터 확보 리스크가 사실상 0 — 공개 데이터셋만으로 완주 가능"),
            ("b", "확장: 크로스 데이터셋 도메인 적응(CWRU→Paderborn), 경량화·스트리밍 추론"),
        ], 10.5),
    ])

# 4. 공간 인식
content_slide(
    prs, 4,
    "시각·음향 융합 공간 쾌적도 분석 AI",
    "이미지 + 소음 멀티모달 · 공간 웰빙 지수 산출",
    [
        ("추진배경", [
            ("b", "층간소음·수면장애는 실생활 문제이나 ||조명과 소음은 늘 따로 진단된다"),
            ("b", "기존 인테리어 서비스는 미관 중심이라 실제 거주 쾌적도를 수치로 답하지 못한다"),
            ("b", "사용자는 \"이 방이 왜 불편한지\"를 언어화하지 못한다 → 진단 자체가 필요"),
            ("b", "빛과 소리는 수면·집중에 함께 작용하는데, 이를 통합해 보는 지표가 없다"),
        ], 10.5),
        ("주요기능", [
            ("h", "공간 시각 분석"),
            ("p", "사진에서 채광 방향, 색온도, 조도 분포와 영역별 마감재를 추정"),
            ("a", "CNN + Segmentation"),
            ("h", "실내 음향 분석"),
            ("p", "녹음된 소음을 스펙트로그램으로 변환해 소음원(도로·층간·기계음)을 분류하고 강도를 측정"),
            ("a", "MFCC + CNN"),
            ("h", "통합 쾌적도 지수와 처방"),
            ("p", "광 스펙트럼 + 사운드스케이프 조합을 추천하고 변화 후 모습을 시뮬레이션 렌더링"),
            ("a", "Multimodal Fusion"),
        ], 10.0),
        ("기대효과", [
            ("b", "||시각과 청각을 함께 다루는 것이 차별점 — 유사 서비스가 드물다"),
            ("b", "결과가 \"공간 웰빙 점수\" 한 장으로 요약되어 겉이 단순하고 속이 복잡한 구조"),
            ("b", "검증: ||사람 설문 쾌적도 점수와 모델 지수의 상관계수"),
            ("b", "층간소음·수면장애라는 사회적 문제와 바로 연결된다"),
            ("b", "리스크: ||정답(쾌적도) 라벨을 직접 만들어야 해 데이터 확보가 최대 난관"),
        ], 10.5),
    ])

# 5. 고령층 약
content_slide(
    prs, 5,
    "고령층 다제복용 알약 식별 및 상호작용 위험 분석 AI",
    "Object Detection + OCR · 병용금기(DUR) 위험도 산출",
    [
        ("추진배경", [
            ("b", "고령자·만성질환자는 여러 약을 동시에 복용해 ||알약 혼동·중복 복용·병용금기 오투약이 빈번하다"),
            ("b", "알약은 모양·색·각인이 비슷해 육안 구분이 어렵고, ||포장을 벗기면 정보가 사라진다"),
            ("b", "약사에게 매번 확인하기 어렵고, 여러 병원에서 받은 처방은 서로 대조되지 않는다"),
            ("b", "고령화로 다제복용 인구가 계속 증가한다"),
        ], 10.5),
        ("주요기능", [
            ("h", "다중 알약 동시 식별"),
            ("p", "손바닥·약통 위 여러 알약의 모양·색·각인을 한 번에 검출하고 품목을 식별"),
            ("a", "YOLO + OCR"),
            ("h", "알약 외관 품질 검사"),
            ("p", "깨짐, 습기로 인한 변색, 캡슐 훼손 등 물리적 결함을 감지"),
            ("a", "CNN 이상탐지"),
            ("h", "병용금기 위험 분석"),
            ("p", "식별된 조합의 동시복용금지·연령대금기·중복처방 위험을 점수로 산출하고 경고"),
            ("a", "식약처 DUR 공개 API + RAG"),
        ], 10.0),
        ("기대효과", [
            ("b", "||사회적 의의가 명확하고 고령화 맥락과 정확히 맞물린다"),
            ("b", "촬영 한 번에 경고가 뜨는 화면이라 ||데모가 직관적이고 즉시 이해된다"),
            ("b", "검증: ||식약처 의약품 낱알식별 공개 데이터 기준 식별 정확도, DUR 규칙 대조 정확도"),
            ("b", "CV와 규칙 기반 안전성 분석이 한 파이프라인에 결합된다"),
            ("b", "리스크: ||각인 OCR이 작고 흐려 난도가 높다 → 대상 약품 수를 좁혀 시작해야 한다"),
        ], 10.5),
    ])

# ---------- 마무리 ----------
s = slide_base(prs)
tf = tb(s, 0.245, 0.26, 6.0, 0.35)
p = para(tf, True, space_after=0)
run(p, "청년 AI·Big Data 아카데미 34기", 14, True, INK)
add_shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, 2.83, 3.05, 7.67, 1.35,
          fill=COVER_PIL, line=COVER_BRD, adj=0.48)
tf = tb(s, 2.83, 3.30, 7.67, 0.85, MSO_ANCHOR.MIDDLE)
p = para(tf, True, align=PP_ALIGN.CENTER, space_after=0)
run(p, "감사합니다", 40, True, GREY)

import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AI프로젝트_아이디어.pptx")
prs.save(out)
print("saved:", out, os.path.getsize(out), "bytes,", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
