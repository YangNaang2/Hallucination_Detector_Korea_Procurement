# -*- coding: utf-8 -*-
"""B1조 'AI 프로젝트 아이디어' 덱 생성 (C4 1주차 발표자료 템플릿 스타일 참고)"""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)

BLACK = RGBColor(0x11, 0x11, 0x11)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GREY  = RGBColor(0xDD, 0xDD, 0xDD)
SHDW  = RGBColor(0xC9, 0xC9, 0xC9)
INK    = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0xB2, 0x3A, 0x32)   # 형광펜 빨강 — img_gap/img_pipeline과 동일 계열
FONT  = "맑은 고딕"

SW, SH   = 13.333, 7.5
BAR_W    = 0.37
TITLE_Y, TITLE_H = 0.66, 0.78
CARD_L   = (0.75, 1.68, 3.64, 5.52)              # 아이디어 카드
RC_X, RC_W = 4.55, 8.04                          # 우측 카드
RC_GAP   = 0.19
RC_H     = (CARD_L[3] - 2 * RC_GAP) / 3
RC_TOPS  = [CARD_L[1] + i * (RC_H + RC_GAP) for i in range(3)]
EMU_IN   = 914400


# ───────────────────────── 유틸 ─────────────────────────
def txt_w(s, size):
    """대략적인 텍스트 폭(inch)"""
    w = 0.0
    for ch in s:
        if ch == " ":
            w += size * 0.32
        elif ord(ch) > 0x2000:                    # 한글·전각
            w += size * 1.02
        else:
            w += size * 0.58
    return w / 72.0


def shape(sl, kind, x, y, w, h, fill=None, line=None, lw=2.4, adj=None):
    s = sl.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if adj is not None:
        try:
            s.adjustments[0] = adj
        except Exception:
            pass
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(lw)
    s.shadow.inherit = False
    return s


def card(sl, x, y, w, h, radius=0.055):
    """그림자 있는 흰 라운드 카드"""
    shape(sl, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.055, y + 0.065, w, h,
          fill=SHDW, adj=radius)
    return shape(sl, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h,
                 fill=WHITE, line=BLACK, lw=2.2, adj=radius)


def tb(sl, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    t = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = t.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def para(tf, first, before=0, after=5, line=1.22, align=PP_ALIGN.LEFT, hang=0.0):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.space_before = Pt(before); p.space_after = Pt(after)
    p.line_spacing = line; p.alignment = align
    if hang:
        pPr = p._pPr if p._pPr is not None else p._p.get_or_add_pPr()
        pPr.set("marL", str(int(hang * EMU_IN)))
        pPr.set("indent", str(int(-hang * EMU_IN)))
    return p


def run(p, s, size, bold=False, color=INK):
    r = p.add_run(); r.text = s
    r.font.size = Pt(size); r.font.bold = bold
    r.font.color.rgb = color; r.font.name = FONT
    return r


def pic_fit(sl, path, bx, by, bw, bh):
    """박스 안에 비율 유지하며 중앙 배치"""
    iw, ih = Image.open(P(path)).size
    sc = min(bw / iw, bh / ih)
    w, h = iw * sc, ih * sc
    return sl.shapes.add_picture(P(path), Inches(bx + (bw - w) / 2),
                                 Inches(by + (bh - h) / 2), Inches(w), Inches(h))


def base(prs):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    bg = shape(sl, MSO_SHAPE.RECTANGLE, 0, 0, SW, SH, fill=WHITE)
    shape(sl, MSO_SHAPE.RECTANGLE, 0, 0, BAR_W, SH, fill=BLACK)
    return sl


def title_block(sl, text, size=32):
    w = txt_w(text, size) + 0.72
    w = min(w, 12.0)
    x = BAR_W + (SW - BAR_W - w) / 2
    shape(sl, MSO_SHAPE.RECTANGLE, x, TITLE_Y, w, TITLE_H, fill=BLACK)
    tf = tb(sl, x, TITLE_Y, w, TITLE_H, MSO_ANCHOR.MIDDLE)
    p = para(tf, True, after=0, align=PP_ALIGN.CENTER)
    run(p, text, size, True, WHITE)


def badge(sl, cx, cy, icon, label, d=0.60, pill_w=1.34, pill_h=0.40, fs=15.5):
    """원형 아이콘 + 검은 라벨 알약 (세로 배치)"""
    shape(sl, MSO_SHAPE.OVAL, cx + 0.04 - d / 2, cy + 0.05 - d / 2, d, d, fill=SHDW)
    shape(sl, MSO_SHAPE.OVAL, cx - d / 2, cy - d / 2, d, d, fill=WHITE,
          line=BLACK, lw=2.0)
    pic_fit(sl, icon, cx - d * 0.30, cy - d * 0.30, d * 0.60, d * 0.60)
    py = cy + d / 2 + 0.10
    shape(sl, MSO_SHAPE.ROUNDED_RECTANGLE, cx - pill_w / 2 + 0.035, py + 0.05,
          pill_w, pill_h, fill=SHDW, adj=0.45)
    shape(sl, MSO_SHAPE.ROUNDED_RECTANGLE, cx - pill_w / 2, py, pill_w, pill_h,
          fill=BLACK, adj=0.45)
    tf = tb(sl, cx - pill_w / 2, py, pill_w, pill_h, MSO_ANCHOR.MIDDLE)
    p = para(tf, True, after=0, align=PP_ALIGN.CENTER)
    run(p, label, fs, True, WHITE)


def idea_slide(prs, title, image, quote, bg, func, eff,
               labels=("추진배경", "주요기능", "기대효과")):
    sl = base(prs)
    title_block(sl, title)

    # 왼쪽 아이디어 카드
    x, y, w, h = CARD_L
    card(sl, x, y, w, h)
    badge_cx, badge_cy = x + 0.62, y + 0.50
    d = 0.56
    shape(sl, MSO_SHAPE.OVAL, badge_cx + 0.04 - d / 2, badge_cy + 0.05 - d / 2,
          d, d, fill=SHDW)
    shape(sl, MSO_SHAPE.OVAL, badge_cx - d / 2, badge_cy - d / 2, d, d,
          fill=WHITE, line=BLACK, lw=2.0)
    pic_fit(sl, "ic_idea.png", badge_cx - d * 0.29, badge_cy - d * 0.29,
            d * 0.58, d * 0.58)
    pw, ph = 1.52, 0.46
    px = badge_cx + 0.42
    shape(sl, MSO_SHAPE.ROUNDED_RECTANGLE, px + 0.035, badge_cy - ph / 2 + 0.05,
          pw, ph, fill=SHDW, adj=0.45)
    shape(sl, MSO_SHAPE.ROUNDED_RECTANGLE, px, badge_cy - ph / 2, pw, ph,
          fill=BLACK, adj=0.45)
    tf = tb(sl, px, badge_cy - ph / 2, pw, ph, MSO_ANCHOR.MIDDLE)
    p = para(tf, True, after=0, align=PP_ALIGN.CENTER)
    run(p, "아이디어", 18, True, WHITE)

    pic_fit(sl, image, x + 0.17, y + 0.95, w - 0.34, 3.08)

    tf = tb(sl, x + 0.16, y + 4.24, w - 0.32, 1.20, MSO_ANCHOR.TOP)
    p = para(tf, True, after=0, line=1.30, align=PP_ALIGN.CENTER)
    run(p, "“", 15, True)
    run(p, quote, 12.5, False)
    run(p, "”", 15, True)

    # 오른쪽 3단 카드
    for i, (icon, label, items) in enumerate([
            ("ic_bg.png", labels[0], bg),
            ("ic_func.png", labels[1], func),
            ("ic_effect.png", labels[2], eff)]):
        top = RC_TOPS[i]
        card(sl, RC_X, top, RC_W, RC_H)
        badge(sl, RC_X + 0.96, top + 0.56, icon, label)
        n = len(items)
        fs = 13.6 if n <= 3 else 12.6
        bx, bw = RC_X + 1.82, RC_W - 2.12
        lines = 0
        for it in items:
            plain = it.replace("||", "")
            lines += max(1, int(txt_w(plain, fs) / (bw - 0.20)) + 1)
        lh = fs / 72.0 * 1.22
        th = lines * lh + (n - 1) * (6 / 72.0)
        tf = tb(sl, bx, top + (RC_H - th) / 2 - 0.03, bw, th + 0.4, MSO_ANCHOR.TOP)
        for j, it in enumerate(items):
            p = para(tf, j == 0, after=6, line=1.20, hang=0.17)
            run(p, "• ", fs)
            if "||" in it:
                head, tail = it.split("||", 1)
                run(p, head, fs, True, ACCENT)
                run(p, tail, fs)
            else:
                run(p, it, fs)
    return sl


# ═══════════════════════════ 덱 ═══════════════════════════
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)

# ── 표지 ──
sl = base(prs)
shape(sl, MSO_SHAPE.ROUNDED_RECTANGLE, 0.52, 0.44, 3.98, 0.46, fill=GREY, adj=0.24)
tf = tb(sl, 0.52, 0.44, 3.98, 0.46, MSO_ANCHOR.MIDDLE)
p = para(tf, True, after=0, align=PP_ALIGN.CENTER)
run(p, "포스코 AI·Big Data 아카데미", 17, True, INK)
shape(sl, MSO_SHAPE.RECTANGLE, 4.62, 0.655, 8.05, 0.035, fill=BLACK)

tw = txt_w("AI 프로젝트 아이디어", 46) + 0.9
shape(sl, MSO_SHAPE.RECTANGLE, (SW - tw) / 2 + BAR_W / 2, 3.08, tw, 1.25, fill=BLACK)
tf = tb(sl, (SW - tw) / 2 + BAR_W / 2, 3.08, tw, 1.25, MSO_ANCHOR.MIDDLE)
p = para(tf, True, after=0, align=PP_ALIGN.CENTER)
run(p, "AI 프로젝트 아이디어", 46, True, WHITE)

tf = tb(sl, BAR_W, 6.42, SW - BAR_W, 0.4)
p = para(tf, True, after=0, align=PP_ALIGN.CENTER)
run(p, "B1조   양진우", 17, True, INK)
pic_fit(sl, "logo_posco.png", 0.62, 6.86, 1.30, 0.36)

# ── 목차 ──
sl = base(prs)
shape(sl, MSO_SHAPE.RECTANGLE, 0.79, 0.62, 1.26, 0.88, fill=BLACK)
tf = tb(sl, 0.79, 0.62, 1.26, 0.88, MSO_ANCHOR.MIDDLE)
p = para(tf, True, after=0, align=PP_ALIGN.CENTER)
run(p, "목차", 34, True, WHITE)
shape(sl, MSO_SHAPE.RECTANGLE, 0.79, 1.76, 11.88, 0.028, fill=BLACK)

TOC = [
    "한국어 환각 탐지 — 근거가 보이는 AI 상담 챗봇",
    "진동 신호 기반 베어링 정비 정책 최적화",
    "시각·음향 융합 공간 쾌적도 분석 AI",
    "고령층 다제복용 알약 식별 및 병용금기 분석 AI",
]
tf = tb(sl, 0.85, 2.18, 11.9, 4.4)
for i, t in enumerate(TOC):
    p = para(tf, i == 0, after=26, line=1.0)
    run(p, "%02d " % (i + 1), 23, True, ACCENT)
    run(p, t, 23, False, INK)

# ── 01 환각 판별 ──
idea_slide(
    prs,
    "한국어 환각 탐지 — 근거가 보이는 AI 상담 챗봇",
    "img_halluc.png",
    "영어에는 있고 한국어에는 없는 AI 환각 탐지기를, 한국어로 만든다",
    ["LLM은 그럴듯하지만 틀린 답을 만들어 피해로 이어진다",
     "탐지기는 영어 등 7개 언어에만 있고 한국어에는 없다",
     "거대 LLM으로 검증하면 비용·지연 탓에 실시간이 불가능"],
    ["Translate : ||RAGTruth를 <HAL> 태그째 한국어로 번역",
     "Detection : ||소형 인코더가 토큰 단위로 환각 구간을 지목",
     "Grounding : ||지목된 구간을 근거 문서와 문자열 대조",
     "Interface : ||답변 위에 형광펜 — 클릭하면 근거 문단으로"],
    ["한국어 구간 단위 환각 탐지기 — 국내 최초 시도",
     "번역 학습본과 실제 한국어 문서의 성능 격차를 최초로 측정",
     "형광펜이 그어지는 화면으로 3분 안에 결과가 보인다"])

# ── [보충] 1번 : 선행연구와 우리 자리 ──
idea_slide(
    prs,
    "[보충] 선행연구와 우리 자리",
    "img_gap.png",
    "7개 언어에는 있고, 한국어에는 없다",
    ["LettuceDetect(2025) : ||영어·중국어 등 7개 언어 지원",
     "TinyLettuce : ||17M 모델이 235B LLM을 이미 이겼다",
     "K-FinHallu(2026) : ||한국어 유일 — 단, 턴 단위 판정 · 8B LLM"],
    ["Turk-LettuceDetect(2025.09)가 ||터키어로 같은 일을 해냈다",
     "핵심 : ||RAGTruth를 <HAL> 태그째 번역 → 구간 라벨이 보존된다",
     "검증 완료 : ||10건 시험에서 13/13 구간 100% 보존 확인",
     "비용 : ||A100 1대 12시간 — 실습실 A5000 6대면 넉넉하다"],
    ["K-FinHallu는 답변 전체를 판정 — ||어디가 환각인지는 못 짚는다",
     "터키어 팀은 ||번역본으로 학습하고 번역본으로만 평가했다",
     "우리 질문 : ||번역해 만든 모델이 진짜 한국어에서 통하는가"],
    labels=("이미 있는 것", "만드는 법", "우리 자리"))

# ── [보충] 2번 : 데이터와 파이프라인 ──
idea_slide(
    prs,
    "[보충] 무엇으로 배우고, 무엇을 검사하나",
    "img_pipeline.png",
    "정답지와 답안지를 나란히 놓고, 답안지에서 정답지에 없는 말에 밑줄을 긋는다",
    ["RAGTruth : ||AI가 실제로 저지른 환각 17,790건",
     "라벨 : ||환각 구간의 시작·끝이 글자 단위로 찍혀 있다",
     "표준 : ||영어·터키어 선행연구가 모두 이 데이터를 썼다",
     "번역 : ||영어이므로 <HAL> 태그째 한국어로 옮겨 쓴다"],
    ["대상 : ||대학 학사요람 — 팀 전원이 당사자라 검증이 된다",
     "제외 : ||법률·의료는 팀이 라벨의 정오를 판단할 수 없다",
     "핵심 : ||모델은 문서를 외우지 않고 답변과 대조할 뿐이다",
     "그래서 ||학습 도메인과 서비스 도메인이 달라도 성립한다"],
    ["확보 : ||RAGTruth 17,790건을 내려받아 직접 분석했다",
     "검증 : ||<HAL> 번역 생존 시험에서 13/13 구간 100% 보존",
     "다음 : ||실제 번역 모델로 200건 배치 재측정"],
    labels=("학습 데이터", "검사 대상", "확인된 것"))

# ── 02 베어링 정비 정책 ──
idea_slide(
    prs,
    "진동 신호 기반 베어링 정비 정책 최적화",
    "img_bearing.png",
    "실측 고장 이력 그대로에서, 언제 정비해야 손실이 최소인지 답하는 정책을 학습한다",
    ["정비는 여전히 정해진 주기·사람이 정한 임계값에 의존한다",
     "과잉정비 비용 낭비와 늑장정비 안전사고, 반대 리스크가 공존한다",
     "기존 CBM+RL은 가정된 이산 건강상태·전이확률 위에서 학습한다"],
    ["Replay : ||실측 run-to-failure 이력을 그대로 재현",
     "Policy : ||이익·고장위험·다운타임 보상으로 오프라인 RL 학습",
     "Compare : ||고정 임계값·이산 MDP RL과 총 비용 직접 비교"],
    ["이산 건강상태 가정 없이 실측 궤적에서 정책을 학습한다",
     "고정 임계값 대비 총 비용 절감분을 숫자로 제시한다",
     "\"언제 교체해야 손실 최소인가\"를 정비팀 관점에서 답한다"])

# ── [보충] 2번-A : 선행연구와 우리 자리 (베어링) ──
idea_slide(
    prs,
    "[보충] 기존 CBM+RL과 우리 자리",
    "img_bearing_gap.png",
    "가정된 시나리오가 아니라, 실제 고장 이력 그대로에서 배운다",
    ["CBM+RL : ||리뷰 논문이 나올 만큼 이미 활발한 분야다",
     "대부분 : ||이산 건강상태 · 가정된 전이확률 MDP 위에서 학습한다",
     "2026 : ||디지털 트윈 기반 sim-to-real RL 연구도 등장했다"],
    ["핵심 : ||IMS·FEMTO-ST 실측 이력을 그대로 오프라인 RL 환경으로 구성",
     "알고리즘 : ||온라인 상호작용 불가 → Conservative Q-Learning으로 안전하게 학습",
     "비용 : ||소규모 문제라 Colab 무료 GPU로 충분하다"],
    ["우리 : ||가정된 MDP가 아니라 실측 궤적 자체를 환경으로 사용한다",
     "검증 : ||고정 임계값·이산 MDP RL과 총 비용을 정량 비교하는 것이 핵심",
     "주의 : ||\"전혀 없다\"고 확언하긴 이르다 — 착수 전 문헌조사 한 번 더"],
    labels=("이미 있는 것", "만드는 법", "우리 자리"))

# ── [보충] 2번-B : 데이터와 검증 (베어링) ──
idea_slide(
    prs,
    "[보충] 무엇으로 배우고, 무엇을 검사하나",
    "img_bearing_pipeline.png",
    "실측 궤적을 환경으로, 세 정책의 총 비용을 같은 베어링으로 나란히 잰다",
    ["IMS : ||정상~고장까지 실측 진동 전체 이력, 무료 공개",
     "FEMTO-ST(PHM2012) : ||여러 베어링의 run-to-failure 이력, 무료 공개",
     "라벨링 불필요 : ||\"마지막 시점=고장\"으로 두고 그대로 환경 궤적으로 쓴다"],
    ["대상 : ||학습에 안 쓴 베어링 개체에서 정책의 정비 시점을 확인한다",
     "측정 : ||정책의 정비 시점과 실제 고장 시점 사이의 간격을 비교한다",
     "비교 : ||고정 임계값 · 이산 MDP RL · 우리 정책을 같은 개체로 나란히 평가한다"],
    ["지형 : ||리뷰 논문으로 CBM+RL 분야 전반을 확인했다",
     "데이터 : ||IMS·FEMTO-ST 모두 무료 공개 — 확보 자체는 문제없다",
     "다음 : ||실제 코드 실행과 \"완전한 부재\" 여부는 아직 미확인"],
    labels=("학습 데이터", "검사 대상", "확인된 것"))

# ── 03 공간 쾌적도 ──
idea_slide(
    prs,
    "시각·음향 융합 공간 쾌적도 분석 AI",
    "img_space.png",
    "사진과 소음을 함께 분석해 '이 방이 왜 불편한지'를 점수와 처방으로 답하는 AI",
    ["층간소음 법정 기준(2024 개정, 39·34dB)은 있지만 시각과 묶이진 않는다",
     "빛과 소리가 각자 따로 측정돼 불편한 원인을 하나로 설명 못 한다",
     "WELL·LEED 국제 IEQ 기준은 있으나 전용 센서 없인 확인 못 한다"],
    ["Vision : ||사진 밝기 분포로 저채광 구역 등급 추정 (CNN)",
     "Audio : ||스펙트로그램 → NC 커브 + 국내 법정 dB 이중 판정",
     "Fusion : ||WELL 기준(300~500lux)과 대조해 웰빙 점수 산출",
     "Prescription : ||590nm 이상 조명 권장, 소음은 정보 제공 우선"],
    ["PROMET&O 등 기존 IEQ 모니터링과 달리 ||센서 설치 없이 사진·녹음만으로 진단",
     "판정 기준이 ||국내 법정 기준·WELL 국제 기준에 그대로 근거한다",
     "검증 : ||설문 쾌적도와 피어슨 상관계수 + 처방 전후 비교로 측정"])

# ── 04 고령층 알약 ──
idea_slide(
    prs,
    "고령층 다제복용 알약 식별 및 병용금기 분석 AI",
    "img_pill.png",
    "여러 알약을 한 번에 촬영하면 종류를 식별하고, 함께 먹으면 안 되는 조합을 경고하는 AI",
    ["다제복용으로 알약 혼동·중복 복용이 빈번하다",
     "포장을 벗기면 정보가 사라지고 각인은 구분이 어렵다",
     "여러 병원의 처방이 서로 대조되지 않는다"],
    ["Detection : ||모양·색·각인을 한 번에 검출 (YOLO)",
     "Recognition : ||각인 문자 인식으로 품목 특정 (OCR)",
     "Quality : ||깨짐·변색·훼손 감지 (CNN 이상탐지)",
     "DUR : ||식약처 병용금기 API 대조로 위험도 산출"],
    ["촬영 한 번에 경고가 뜨는 직관적인 데모",
     "식약처 낱알식별 공개 데이터로 정확도 정량 평가",
     "고령화 맥락과 맞물려 사회적 의의가 명확하다"])

# ── 마무리 ──
sl = base(prs)
tf = tb(sl, 1.10, 3.25, 9.0, 1.1, MSO_ANCHOR.MIDDLE)
p = para(tf, True, after=0)
run(p, "감사합니다.", 50, True, INK)

out = P("AI프로젝트_아이디어_B1.pptx")
prs.save(out)
print("saved:", out, os.path.getsize(out))
