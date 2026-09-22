from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/pdf/ASTRA_RAG_전체구조_설명서.pdf"

NAVY = colors.HexColor("#10243E")
BLUE = colors.HexColor("#224A73")
TEAL = colors.HexColor("#21A89A")
MINT = colors.HexColor("#EAF7F3")
PALE_BLUE = colors.HexColor("#EDF3FA")
PALE_RED = colors.HexColor("#FFF0EE")
PALE_GOLD = colors.HexColor("#FFF7DF")
INK = colors.HexColor("#172536")
MUTED = colors.HexColor("#5E6D7D")
LINE = colors.HexColor("#CED8E3")


pdfmetrics.registerFont(TTFont("Malgun", "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont("Malgun-Bold", "C:/Windows/Fonts/malgunbd.ttf"))


styles = getSampleStyleSheet()
TITLE = ParagraphStyle(
    "TitleKR", fontName="Malgun-Bold", fontSize=25, leading=34,
    textColor=colors.white, alignment=TA_LEFT, spaceAfter=10,
)
SUBTITLE = ParagraphStyle(
    "SubtitleKR", fontName="Malgun", fontSize=10.5, leading=17,
    textColor=colors.HexColor("#CFE2F3"),
)
H1 = ParagraphStyle(
    "H1KR", fontName="Malgun-Bold", fontSize=18, leading=25,
    textColor=NAVY, spaceBefore=2, spaceAfter=10,
)
H2 = ParagraphStyle(
    "H2KR", fontName="Malgun-Bold", fontSize=12, leading=18,
    textColor=BLUE, spaceBefore=8, spaceAfter=5,
)
BODY = ParagraphStyle(
    "BodyKR", fontName="Malgun", fontSize=9.2, leading=15,
    textColor=INK, spaceAfter=5,
)
SMALL = ParagraphStyle(
    "SmallKR", fontName="Malgun", fontSize=7.7, leading=12,
    textColor=MUTED,
)
CELL = ParagraphStyle(
    "CellKR", fontName="Malgun", fontSize=8.1, leading=12,
    textColor=INK,
)
CELL_BOLD = ParagraphStyle(
    "CellBoldKR", fontName="Malgun-Bold", fontSize=8.2, leading=12,
    textColor=NAVY,
)
WHITE_CELL = ParagraphStyle(
    "WhiteCellKR", fontName="Malgun-Bold", fontSize=8.4, leading=12,
    textColor=colors.white, alignment=TA_CENTER,
)
CALLOUT = ParagraphStyle(
    "CalloutKR", fontName="Malgun-Bold", fontSize=10.2, leading=16,
    textColor=NAVY,
)
CODE = ParagraphStyle(
    "CodeKR", fontName="Malgun", fontSize=7.6, leading=11,
    textColor=colors.HexColor("#DDEAF4"), leftIndent=5, rightIndent=5,
)


def P(text, style=BODY):
    return Paragraph(text, style)


def bullet(text):
    return Paragraph("&#8226; " + text, BODY)


def section_title(no, title, kicker):
    return [
        P(f"{no:02d} / {kicker}", ParagraphStyle(
            "Kicker", parent=SMALL, textColor=TEAL, fontName="Malgun-Bold",
            spaceAfter=3,
        )),
        P(title, H1),
    ]


def callout(text, background=MINT):
    t = Table([[P(text, CALLOUT)]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.7, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def styled_table(data, widths, header=True, row_colors=None, font_size=8.1):
    converted = []
    for r, row in enumerate(data):
        converted.append([
            P(str(value), WHITE_CELL if header and r == 0 else ParagraphStyle(
                f"cell-{r}-{c}", parent=CELL, fontSize=font_size,
                fontName="Malgun-Bold" if c == 0 else "Malgun",
            ))
            for c, value in enumerate(row)
        ])
    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    for r in range(1 if header else 0, len(data)):
        bg = row_colors[r - (1 if header else 0)] if row_colors else (
            colors.white if r % 2 else colors.HexColor("#F6F8FB")
        )
        commands.append(("BACKGROUND", (0, r), (-1, r), bg))
    table.setStyle(TableStyle(commands))
    return table


def flow_box(title, detail, color):
    t = Table([
        [P(title, ParagraphStyle("fbh", parent=CELL_BOLD, alignment=TA_CENTER))],
        [P(detail, ParagraphStyle("fbb", parent=SMALL, alignment=TA_CENTER, textColor=INK))],
    ], colWidths=[24.5 * mm], rowHeights=[10 * mm, 18 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color),
        ("BOX", (0, 0), (-1, -1), 0.8, color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


class DocTemplate(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(
            filename, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=19 * mm, bottomMargin=17 * mm,
            title="ASTRA RAG 전체 구조 설명서",
            author="ko-LettuceDetect / ASTRA",
            subject="나라장터 공고 및 합성 기업 자료 기반 권한형 하이브리드 RAG 구조",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        if doc.page == 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            canvas.setFillColor(TEAL)
            canvas.rect(0, 0, 9 * mm, A4[1], fill=1, stroke=0)
        else:
            canvas.setStrokeColor(LINE)
            canvas.line(20 * mm, 14 * mm, 190 * mm, 14 * mm)
            canvas.setFont("Malgun", 7.2)
            canvas.setFillColor(MUTED)
            canvas.drawString(20 * mm, 9 * mm, "ko-LettuceDetect / ASTRA  |  RAG 구조 설명서")
            canvas.drawRightString(190 * mm, 9 * mm, f"{doc.page}")
        canvas.restoreState()


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    story = []

    story += [Spacer(1, 55 * mm), P("ASTRA RAG<br/>전체 구조 설명서", TITLE)]
    story += [P("나라장터 공개 공고와 합성 기업 내부 자료를 보안등급별로 검색하고,<br/>근거 기반 답변과 환각 의심 구절 검증까지 연결하는 파일럿 구조", SUBTITLE)]
    story += [Spacer(1, 18 * mm)]
    story += [callout(
        "핵심 정의  |  300개 Q-A-R은 RAG 자체가 아니라, RAG와 환각 탐지기를 시험하는 비공개 평가셋입니다.",
        colors.HexColor("#D9F2EC"),
    )]
    story += [Spacer(1, 47 * mm), P("기준일 2026-09-16", SUBTITLE)]
    story += [P("파일럿 manifest와 저장소 구현을 기준으로 작성", SUBTITLE), PageBreak()]

    story += section_title(1, "한눈에 보는 전체 구조", "END-TO-END PIPELINE")
    boxes = [
        flow_box("원천", "나라장터 L1<br/>합성 기업 L2/L3", PALE_BLUE),
        P("&#8594;", ParagraphStyle("arrow", parent=H1, alignment=TA_CENTER)),
        flow_box("구조화", "문서 JSON<br/>청크 JSONL", MINT),
        P("&#8594;", ParagraphStyle("arrow2", parent=H1, alignment=TA_CENTER)),
        flow_box("검색", "권한 필터<br/>키워드 + 벡터", PALE_GOLD),
        P("&#8594;", ParagraphStyle("arrow3", parent=H1, alignment=TA_CENTER)),
        flow_box("생성", "로컬 LLM<br/>근거 번호 답변", PALE_BLUE),
        P("&#8594;", ParagraphStyle("arrow4", parent=H1, alignment=TA_CENTER)),
        flow_box("검증", "규칙 검사<br/>환각 탐지", PALE_RED),
    ]
    t = Table(
        [boxes],
        colWidths=[25 * mm, 8 * mm, 25 * mm, 8 * mm, 25 * mm, 8 * mm, 25 * mm, 8 * mm, 25 * mm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [t, Spacer(1, 8 * mm)]
    story += [callout(
        "사용자의 질문을 받으면 전체 자료를 한꺼번에 검색하지 않습니다. 먼저 선택 공고, 회사, tenant, 역할, 보안등급과 시나리오 버전으로 검색 후보를 제한합니다."
    )]
    story += [Spacer(1, 6 * mm)]
    story += [P("RAG를 구성하는 세 축", H2)]
    story += [styled_table([
        ["축", "구성", "역할"],
        ["지식 자료", "L1 공개 공고 + L2 내부 자료 + L3 민감 자료", "검색 가능한 업무 근거"],
        ["검색·생성", "메타데이터 필터 + 키워드/벡터 검색 + 로컬 LLM", "질문에 맞는 근거와 답변 생성"],
        ["검증·평가", "규칙 검사 + 환각 탐지 + 300개 Q-A-R", "답변 품질과 근거 불일치 측정"],
    ], [28 * mm, 72 * mm, 70 * mm])]
    story += [Spacer(1, 5 * mm), P(
        "현재 파일럿은 ID와 메타데이터 관계를 활용한 권한형 하이브리드 RAG입니다. UI는 관계를 그래프로 표현하지만, 검색 핵심은 SQLite, 키워드 검색, 벡터 검색과 메타데이터 필터입니다. 별도 그래프 DB에서 경로 추론을 수행하는 완성형 GraphRAG라고 설명하지 않습니다.",
        SMALL,
    ), PageBreak()]

    story += section_title(2, "L1, L2, L3는 무엇인가", "DOCUMENT SECURITY LEVELS")
    story += [styled_table([
        ["등급", "정보 주체", "대표 내용", "생성 근거"],
        ["L1 공개", "발주기관", "공고문, 제안요청서, 과업내용서, 참가조건, 공개 예산·일정", "실제 나라장터 공고·첨부문서"],
        ["L2 내부", "가상 입찰 기업", "업종·등록, 실적, 인력, 인증, 증빙, 배치 가능량", "51건 조건 분석 후 설계한 합성 회사 원장"],
        ["L3 민감", "가상 입찰 기업", "인건비, 원가, 비용 가정, 마진, 투찰 검토", "회사 정책과 공고별 합성 계획·계산"],
    ], [25 * mm, 32 * mm, 62 * mm, 51 * mm], row_colors=[PALE_BLUE, MINT, PALE_RED])]
    story += [Spacer(1, 7 * mm), P("같은 '가격'도 정보 성격에 따라 등급이 달라집니다", H2)]
    story += [styled_table([
        ["예시", "등급", "이유"],
        ["발주기관이 공개한 사업예산", "L1", "공개 공고 정보"],
        ["회사가 과거에 수행한 계약금액", "L2", "회사 내부 실적 정보"],
        ["이번 사업의 내부 원가와 목표 마진", "L3", "투찰 판단에 영향을 주는 민감 정보"],
    ], [66 * mm, 20 * mm, 84 * mm])]
    story += [Spacer(1, 7 * mm), callout(
        "L1/L2/L3는 문서 접근등급입니다. 지도나 3D 화면의 확대 단계가 아닙니다.", PALE_GOLD
    )]
    story += [Spacer(1, 7 * mm), P("L2·L3의 파생 관계", H2)]
    story += [bullet("L1에서 참가자격·실적·인력·인증·지역·기간·공동수급·예산 조건을 읽습니다.")]
    story += [bullet("조건과 비교할 수 있도록 서로 다른 강점과 제약을 가진 가상 기업 5곳의 공통 사실을 설계합니다.")]
    story += [bullet("공통 회사 사실을 L2 문서로, 공고별 원가·가격·투찰 판단을 L3 시나리오로 분리합니다.")]
    story += [bullet("인증 갱신이나 증빙 확보 같은 추가 가정은 기존 사실을 덮어쓰지 않고 별도 시나리오와 버전으로 관리합니다.")]
    story += [Spacer(1, 4 * mm), P(
        "가상 회사의 실적·인력·인증·금액은 평가용 합성 설정입니다. L1 공고 인용은 회사의 합성 사실이 실제라는 증거가 아닙니다.", SMALL
    ), PageBreak()]

    story += section_title(3, "데이터는 어떤 형식으로 저장되는가", "DATA FORMATS")
    story += [styled_table([
        ["형식", "내용", "주요 사용자"],
        ["raw", "다운로드한 HWP·HWPX·PDF 원본", "원문 재확인"],
        ["parsed", "원본에서 추출한 정본 텍스트", "청킹·인용 위치 확인"],
        ["JSONL", "공고·청크·질문 등을 한 줄에 한 레코드씩 기록", "배치 처리·재개"],
        ["JSON", "문서 전체, 회사 마스터, manifest와 설정", "프로그램·검증기"],
        ["Markdown", "사람이 읽는 회사 대장과 설명", "검수자"],
        ["CSV/TSV", "51건 요건시트와 평가 검토표", "사람 검수·비교"],
        ["SQLite", "검색기가 읽는 로컬 청크 저장소", "RAG 검색"],
    ], [25 * mm, 92 * mm, 53 * mm])]
    story += [Spacer(1, 7 * mm), P("문서와 청크의 핵심 필드", H2)]
    code_text = (
        "{<br/>"
        "&nbsp;&nbsp;\"chunk_id\": \"C01-PERF-...-CH-...\",<br/>"
        "&nbsp;&nbsp;\"document_id\": \"C01-PERF-1.0.0-r1\",<br/>"
        "&nbsp;&nbsp;\"company_id\": \"C01\",<br/>"
        "&nbsp;&nbsp;\"tenant_id\": \"astra-c01\",<br/>"
        "&nbsp;&nbsp;\"security_level\": \"L2\",<br/>"
        "&nbsp;&nbsp;\"allowed_roles\": [\"bid_analyst\", \"cost_analyst\"],<br/>"
        "&nbsp;&nbsp;\"text_start\": 74, \"text_end\": 1180,<br/>"
        "&nbsp;&nbsp;\"text\": \"실적 금액·VAT·기간·증빙 상태...\"<br/>"
        "}"
    )
    code_table = Table([[P(code_text, CODE)]], colWidths=[170 * mm])
    code_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("BOX", (0, 0), (-1, -1), 0.8, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story += [code_table, Spacer(1, 6 * mm)]
    story += [callout(
        "문자 위치는 Unicode code point 기준의 [text_start, text_end) 형식입니다. end 위치의 문자는 포함하지 않습니다."
    )]
    story += [Spacer(1, 6 * mm), P(
        "Manifest는 문서 ID, 버전, 파일 해시, 정본 텍스트 해시, 파싱 방식, 승인 상태를 연결합니다. 원천 파일과 전체 비공개 프롬프트·색인·모델 가중치는 GitHub에 저장하지 않습니다.",
        BODY,
    ), PageBreak()]

    story += section_title(4, "청킹과 현재 코퍼스 규모", "CORPUS AND CHUNKING")
    story += [styled_table([
        ["보안등급", "문서 수", "청크 수", "청킹 원칙"],
        ["L1", "167", "3,002", "부모 청크 최대 약 1,800자, 약 240자 중첩, 문단 경계 우선"],
        ["L2", "34", "159", "실적 1건·인력 1명·인증 1건 등 의미 단위 유지"],
        ["L3", "22", "114", "원가 정책·공고별 비용·투찰 검토 단위 유지"],
        ["합계", "223", "3,275", "파일럿 index_manifest 기준"],
    ], [28 * mm, 24 * mm, 24 * mm, 94 * mm], row_colors=[PALE_BLUE, MINT, PALE_RED, PALE_GOLD])]
    story += [Spacer(1, 7 * mm), P("L1 청킹", H2)]
    story += [bullet("공고문과 제안요청서의 전체 파싱 텍스트를 부모 청크로 나눕니다.")]
    story += [bullet("각 청크에 공고번호·차수·문서 ID·파일명·정본 문자 위치와 해시를 유지합니다.")]
    story += [bullet("긴 표나 예외 조항은 경계를 넘을 수 있어 인접 청크 확인이 필요할 수 있습니다.")]
    story += [P("L2·L3 청킹", H2)]
    story += [bullet("금액과 VAT 기준, 기간과 완료 상태, 인증명과 보유 주체·유효기간이 분리되지 않게 합니다.")]
    story += [bullet("다른 회사나 다른 보안등급의 자료가 하나의 청크에 섞이지 않게 합니다.")]
    story += [bullet("회사 전체 마스터를 통째로 검색시키지 않고 업무에 필요한 문서 단위로 제공합니다.")]
    story += [Spacer(1, 6 * mm), callout(
        "51개 공고에 읽을 수 있는 자료가 존재하지만, 읽을 수 없었던 첨부 16개는 manifest에 별도로 기록했습니다. 모든 첨부의 완전 파싱을 의미하지 않습니다.",
        PALE_GOLD,
    ), PageBreak()]

    story += section_title(5, "권한 필터가 검색보다 먼저 작동한다", "ACCESS BOUNDARY")
    story += [P(
        "질문 문장에 '관리자' 또는 'L3'라고 적는 것으로 권한이 바뀌지 않습니다. 신뢰된 세션의 회사·tenant·역할·허용등급·시나리오를 사용해 후보 문서를 제한합니다.",
        BODY,
    )]
    story += [styled_table([
        ["역할", "허용 보안등급", "대표 사용"],
        ["viewer", "L1", "공개 공고 조회"],
        ["bid_analyst", "L1, L2", "공고와 회사 실적·인력 비교"],
        ["cost_analyst", "L1, L2, L3", "공고·회사·원가 검토"],
        ["bid_approver", "L1, L2, L3", "내부 검토 결과 승인 역할"],
    ], [40 * mm, 45 * mm, 85 * mm])]
    story += [Spacer(1, 7 * mm)]
    access_flow = styled_table([
        ["1. 요청 문맥", "2. 후보 제한", "3. 검색", "4. 반환 전 재검증"],
        ["공고·회사·tenant<br/>역할·시나리오", "선택 공고 L1<br/>허용 회사 L2/L3", "허용 후보 안에서만<br/>키워드·벡터 계산", "ID·본문·offset<br/>메타데이터 재대조"],
    ], [42.5 * mm] * 4)
    story += [access_flow, Spacer(1, 7 * mm)]
    story += [P("예시", H2)]
    story += [callout(
        "C01의 bid_analyst가 질문하면 선택 공고의 L1과 C01 tenant의 L2만 후보가 됩니다. 다른 회사 문서와 L3 원가 자료는 검색 후보에서 제외됩니다."
    )]
    story += [Spacer(1, 7 * mm), P(
        "현재 배치 평가의 사용자 세션은 오프라인 테스트용 픽스처입니다. 실제 운영 인증 서버를 의미하지 않습니다. 실시간 UI의 자유 질문 서비스는 현재 공개 L1과 선택 공고 범위가 중심입니다.",
        SMALL,
    ), PageBreak()]

    story += section_title(6, "하이브리드 검색과 답변 생성", "RETRIEVAL AND GENERATION")
    story += [styled_table([
        ["단계", "현재 파일럿 방식", "강점과 한계"],
        ["키워드 검색", "한국어 2글자 부분어와 영문·숫자 단어 기반 BM25 계열 점수", "코드·금액·고유 용어에 유리, 완전한 형태소 분석은 아님"],
        ["벡터 검색", "multilingual-e5-small, cosine 유사도", "의미 유사성 검색, 질문·문서 접두사와 정규화 사용"],
        ["순위 결합", "키워드와 벡터 순위를 RRF(k=60)로 결합", "서로 다른 검색 신호를 하나의 순위로 통합"],
        ["선택", "검색 top_k=6, 생성에는 상위 부모 청크 최대 4개", "입력 한도 초과 시 낮은 순위 부모 전체 제외"],
    ], [31 * mm, 74 * mm, 65 * mm])]
    story += [Spacer(1, 7 * mm), P("LLM에 전달되는 개념적 입력", H2)]
    code = (
        "[시스템 지시] 근거에서 확인되는 내용만 답하고 수치·VAT·기간을 보존<br/><br/>"
        "[근거 1] 과업내용서.hwpx - AI-OCR 솔루션 영구라이선스 각 1식 구매...<br/>"
        "[근거 2] 제안요청서.hwp - 라이선스 비용 등 일체의 비용을 포함...<br/><br/>"
        "[질문] OCR 사용권을 구독료만으로 계획해도 되는가?"
    )
    t = Table([[P(code, CODE)]], colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story += [t, Spacer(1, 7 * mm)]
    story += [P(
        "생성은 Qwen 계열 GGUF와 llama.cpp 기반 로컬 서버를 사용한 기록이 있습니다. 결과 비교 시 모델명·revision·양자화·컨텍스트·출력 설정을 함께 봐야 합니다. UI에서 확인한 Qwen2.5 1.5B 연결과 기존 배치 파일럿 결과를 같은 실험으로 합치지 않습니다.",
        BODY,
    ), PageBreak()]

    story += section_title(7, "답변 이후의 규칙 검증과 환각 탐지", "POST-GENERATION CHECKS")
    story += [styled_table([
        ["검증", "입력", "출력", "주의"],
        ["규칙 검증", "금액·VAT·기간·인증일·지분·FTE", "계산 가능한 조건의 충족·미충족", "학습된 탐지 모델과 다른 기능"],
        ["환각 탐지", "질문 + 실제 입력 근거 + 생성 답변", "답변 토큰별 SUPPORTED/HALLUCINATED 확률과 의심 구절", "세상의 사실이 아니라 입력 근거의 지지 여부를 검사"],
    ], [28 * mm, 52 * mm, 55 * mm, 35 * mm], row_colors=[PALE_GOLD, PALE_RED])]
    story += [Spacer(1, 7 * mm)]
    detection_flow = styled_table([
        ["생성 답변", "실제 입력 근거와 결합", "토큰 분류", "문자 위치 변환", "UI 형광펜"],
        ["정본 문자열 보존", "사후 추가 근거와 구분", "SUPPORTED /<br/>HALLUCINATED", "Unicode<br/>[start,end)", "의심 구절 표시"],
    ], [34 * mm] * 5)
    story += [detection_flow, Spacer(1, 7 * mm)]
    story += [P("현재 연결 후보", H2)]
    story += [bullet("KLUE 기반 토큰 분류 모델")]
    story += [bullet("XLM-R 기반 토큰 분류 모델")]
    story += [bullet("BGE-M3 기반 토큰 분류 모델 - 검색 임베딩 모델과 별개의 학습된 분류 체크포인트")]
    story += [Spacer(1, 6 * mm), callout(
        "탐지 결과가 0건이어도 답변이 정확하다는 보장은 아닙니다. 실제 성능은 사람 구절 라벨과 비교해 정탐·오탐·미탐을 계산해야 합니다.",
        PALE_RED,
    ), PageBreak()]

    story += section_title(8, "300개 Q-A-R은 어디에 쓰이는가", "EVALUATION SET")
    story += [P(
        "Q-A-R은 사용자에게 300개 질문을 고르라고 보여주는 메뉴가 아니라, 실제 입찰 담당자가 물을 법한 질문을 미리 구성한 내부 평가셋입니다.",
        BODY,
    )]
    story += [styled_table([
        ["항목", "의미", "모델 입력 여부"],
        ["Q - Question", "사용자가 물을 법한 예상 질문", "질문으로 입력"],
        ["A - Expected Answer", "근거를 정확히 읽었을 때의 기대 결론", "생성 모델에는 숨김"],
        ["R - Reference", "기대 결론을 판단하는 공고·회사 근거 위치", "채점 기준. 검색기는 업무 문서에서 근거를 찾아야 함"],
    ], [35 * mm, 81 * mm, 54 * mm], row_colors=[PALE_BLUE, PALE_GOLD, MINT])]
    story += [Spacer(1, 7 * mm)]
    story += [callout(
        "현재 구성: 회사별 60문항, 총 300문항, 51개 공고 포함. 실제 실행 결과는 생성 답변 295건과 정상 접근 차단 5건입니다.",
        PALE_BLUE,
    )]
    story += [Spacer(1, 7 * mm), P("두 가지 평가", H2)]
    story += [styled_table([
        ["평가 대상", "핵심 질문", "필요한 기준"],
        ["RAG·생성 모델", "올바른 근거를 찾고 기대 결론에 맞게 답했는가?", "기대답·근거·필수 사실·금지 주장"],
        ["환각 탐지 모델", "생성 답변의 근거 불일치 구절을 찾아냈는가?", "동일 정본 답변에 대한 사람 구절 라벨"],
    ], [42 * mm, 75 * mm, 53 * mm])]
    story += [Spacer(1, 7 * mm), P(
        "현재 기존 25문항에는 팀원 검수 의견과 통합 조정안이 있으나 최종 사람 승인은 pending입니다. 300개 전체 탐지 평가는 생성된 295개 답변의 정본과 실제 생성 입력 근거를 고정해 진행합니다.",
        BODY,
    ), PageBreak()]

    story += section_title(9, "현재 구현 상태와 정확한 설명", "WHAT IS WORKING NOW")
    story += [styled_table([
        ["구성", "현재 상태"],
        ["L1/L2/L3 파일럿 코퍼스", "223개 문서·3,275개 청크가 manifest에 기록됨"],
        ["배치 평가", "300문항 중 답변 295건·접근 차단 5건 결과 보존"],
        ["실시간 UI", "공개 L1·선택 공고 범위의 질문과 Qwen 생성 연결 확인"],
        ["환각 탐지 UI", "답변 완료 후 로컬 탐지기 결과와 Unicode 구절 표시 연결"],
        ["L2/L3 자유 질문", "완전한 운영 인증 서버와 연결된 상태는 아님"],
        ["사람 구절 정답지", "기존 25문항 검수 통합, 최종 승인 pending; 전체 295답변은 평가 진행 대상"],
        ["GraphRAG", "ID·Pointer·manifest 관계와 UI 그래프는 존재. 별도 그래프 DB 경로 추론은 미완성"],
    ], [47 * mm, 123 * mm])]
    story += [Spacer(1, 9 * mm), callout(
        "ASTRA는 권한에 맞는 L1·L2·L3 문서를 먼저 제한하고, 키워드와 임베딩 검색으로 근거를 찾은 뒤 로컬 LLM이 출처 기반 답변을 생성하는 시스템입니다. 생성 결과는 규칙 검사와 토큰 단위 환각 탐지로 다시 확인하며, 300개 Q-A-R 평가셋으로 품질을 측정합니다."
    )]
    story += [Spacer(1, 9 * mm), P("해석할 때 지켜야 할 점", H2)]
    story += [bullet("자동 검증 통과를 모델 정확도나 사람 승인으로 표현하지 않습니다.")]
    story += [bullet("합성 회사 자료를 실제 기업의 실적·인증·견적으로 소개하지 않습니다.")]
    story += [bullet("검색 근거 연결 여부, 답변 정확도, 환각 탐지 성능은 서로 다른 지표입니다.")]
    story += [bullet("미확인 수치·페이지·원문 우선순위를 임의로 확정하지 않습니다.")]
    story += [Spacer(1, 8 * mm), P(
        "근거 문서: project-docs/RAG파일럿/v1/README.md, index_manifest.json, project-docs/가상기업/v1/README.md, project-docs/평가데이터/v2/README.md, procurement-pipeline/rag_pilot.py. 수치는 2026-09-16 현재 저장소 파일럿 기록 기준입니다.",
        SMALL,
    )]

    doc = DocTemplate(str(OUT))
    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
