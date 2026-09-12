import io, html
W, H = 1700, 940
NW, NH = 200, 64
COL = [40 + 240 * i for i in range(7)]
ROW = {1: 66, 2: 206, 3: 346, 4: 486, 5: 660, 6: 800}
BANDS = [
    (36, 140, "① 수집  ·  팀원 워크스테이션 3대 (4·5·6월)", "#eef3f8"),
    (176, 140, "② 변환·집계·표본  ·  procurement-pipeline", "#eef6f0"),
    (316, 140, "③ 사람 작업  ·  팀원 5명", "#f8f3e8"),
    (456, 140, "④ 문서 등급  ·  L1 공개 / L2 내부 / L3 민감  (가상 기업 5곳, 멀티 테넌트)", "#f3eef8"),
    (610, 290, "⑤ 서비스  ·  질문 → 권한 필터 → 검색 → 답변 → 환각 탐지 → 화면   /   평가", "#fdf0ee"),
]
# id: (col, row, title, sub, style)
N = {
    "api":    (0, 1, "나라장터 OpenAPI", "조달청 입찰공고정보서비스", "ext"),
    "ing":    (1, 1, "수집기", "목록 · 첨부 다운로드 · 파싱", "svc"),
    "store":  (2, 1, "raw/ · parsed/ · jsonl", "해시 저장소, 공고 137,745행", "db"),
    "rep":    (3, 1, "재파싱 도구", "파서 미설치 캐시 복구 92~95%", "ext"),
    "adapt":  (2, 2, "adapt_g2b.py", "파이프라인 입력으로 변환", "svc"),
    "prep":   (3, 2, "prepare.py", "완전 공고 집계 · 표본 추출", "svc"),
    "sector": (4, 2, "3개월 분야 표", "용역 완전 공고 28,852건", "db"),
    "sample": (6, 2, "표본 51건", "원본 151개 · 텍스트 430만 자", "db"),
    "team":   (5, 3, "팀원 5명 요건 추출", "공고문 + 제안요청서, 9/13", "actor"),
    "sheet":  (4, 3, "요건 시트", "자격·실적·인력·인증·금액·일정", "db"),
    "q":      (3, 3, "검수 질문 300개", "유형 20 × 공고 × 기업", "db"),
    "l2":     (3, 4, "L2 기업 내부 자료", "실적 · 인력 · 인증", "l2"),
    "synth":  (4, 4, "가상 기업 5곳 합성", "LLM 생성 + 검증 규칙 + 사람 검수", "svc"),
    "l3":     (5, 4, "L3 기업 민감 자료", "단가 · 협력사 견적 · 투찰 전략", "l3"),
    "l1":     (6, 4, "L1 공개 공고", "표본 51건 그대로", "l1"),
    "user":   (0, 5, "입찰 기업 직원", "회사 · 역할로 로그인", "actor"),
    "ui":     (1, 5, "ASTRA UI", "질문 · 근거 하이라이트 · 환각 표시", "svc"),
    "auth":   (2, 5, "권한 필터", "회사(tenant) + 등급 검사", "gate"),
    "rag":    (3, 5, "RAG 검색", "BGE-M3 임베딩 색인", "svc"),
    "gem":    (4, 5, "답변 생성 LLM", "Gemma (소형 오픈 모델)", "svc"),
    "det":    (5, 5, "환각 탐지 모델", "직접 학습 · BGE-M3 토큰 분류 · F1 0.74", "core"),
    "rule":   (6, 5, "규칙 검증", "답변 숫자 ↔ 문서 숫자 대조", "svc"),
    "label":  (4, 6, "환각 구간 라벨링", "5명 × 60건 + 교차 검수", "actor"),
    "eval":   (5, 6, "평가", "유형별 탐지율 · 권한 차단 20케이스", "db"),
}
FILL = {"svc": "#ffffff", "db": "#ffffff", "ext": "#ffffff", "actor": "#fffbe6", "gate": "#fff4e5",
        "core": "#ffe9d6", "l1": "#e6f4ea", "l2": "#e3eefb", "l3": "#fbe4e4"}
STROKE = {"core": "#d9480f", "l1": "#2b8a3e", "l2": "#1c6fbf", "l3": "#c92a2a", "gate": "#e67700"}

def box(nid):
    c, r, *_ = N[nid]
    x, y = COL[c], ROW[r]
    return x, y, x + NW, y + NH, x + NW / 2, y + NH / 2

def node_svg(nid):
    c, r, title, sub, st = N[nid]
    x, y, x2, y2, cx, cy = box(nid)
    stroke = STROKE.get(st, "currentColor")
    sw = 2.2 if st == "core" else 1.3
    dash = ' stroke-dasharray="6 4"' if st == "ext" else ""
    rx = 32 if st == "actor" else 8
    shape = f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="{rx}" fill="{FILL[st]}" stroke="{stroke}" stroke-width="{sw}"{dash}/>'
    if st == "db":
        shape = (f'<rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="8" fill="{FILL[st]}" stroke="{stroke}" stroke-width="{sw}"/>'
                 f'<line x1="{x}" y1="{y+12}" x2="{x2}" y2="{y+12}" stroke="{stroke}" stroke-width="1" opacity="0.5"/>')
    t = html.escape(title); s = html.escape(sub)
    ty = cy - 4 if sub else cy + 5
    out = shape + f'<text x="{cx}" y="{ty}" text-anchor="middle" font-size="13" font-weight="700" fill="currentColor">{t}</text>'
    if sub:
        out += f'<text x="{cx}" y="{cy+15}" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.8">{s}</text>'
    return out

def label(x, y, text, anchor="middle", size=10.5, dy=0):
    return (f'<text x="{x}" y="{y+dy}" text-anchor="{anchor}" font-size="{size}" fill="currentColor" '
            f'paint-order="stroke" stroke="#ffffff" stroke-width="4" stroke-linejoin="round">{html.escape(text)}</text>')

def arrow(points, text=None, dashed=False, tpos=None, anchor="middle", color="currentColor"):
    d = "M " + " L ".join(f"{x},{y}" for x, y in points)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    s = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4"{dash} marker-end="url(#arr)"/>'
    if text:
        if tpos is None:
            (x1, y1), (x2, y2) = points[0], points[-1]
            tpos = ((x1 + x2) / 2, (y1 + y2) / 2 - 5)
        s += label(tpos[0], tpos[1], text, anchor)
    return s

def right(a, b, text=None, **k):   # a → b (b is to the right)
    ax, ay, ax2, ay2, acx, acy = box(a); bx, by, bx2, by2, bcx, bcy = box(b)
    return arrow([(ax2, acy), (bx, bcy)], text, tpos=((ax2 + bx) / 2, ay2 + 14), **k)

def left(a, b, text=None, **k):    # a → b (b is to the left)
    ax, ay, ax2, ay2, acx, acy = box(a); bx, by, bx2, by2, bcx, bcy = box(b)
    return arrow([(ax, acy), (bx2, bcy)], text, tpos=((ax + bx2) / 2, ay2 + 14), **k)

def down(a, b, text=None, dx=0, **k):  # a → b (b is below)
    ax, ay, ax2, ay2, acx, acy = box(a); bx, by, bx2, by2, bcx, bcy = box(b)
    return arrow([(acx + dx, ay2), (bcx + dx, by)], text, tpos=(acx + dx + 6, (ay2 + by) / 2 + 4), anchor="start", **k)

E = []
E.append(right("api", "ing", "API 조회 · 첨부 다운로드"))
E.append(right("ing", "store", "저장 · 목록 기록"))
E.append(left("rep", "store", "실패 문서 재파싱", dashed=True))
E.append(down("store", "adapt", "jsonl 3종 + parsed/"))
E.append(right("adapt", "prep", "manifest + 구간 텍스트"))
E.append(right("prep", "sector", "집계"))
# sector → sample (skips a column)
sx, sy, sx2, sy2, scx, scy = box("sector"); px, py, px2, py2, pcx, pcy = box("sample")
E.append(arrow([(sx2, scy), (px, pcy)], "정보시스템 구축·운영 확정 → --ids 51건", tpos=((sx2 + px) / 2, scy - 6)))
# sample → team (down-left)
ax, ay, ax2, ay2, acx, acy = box("sample"); bx, by, bx2, by2, bcx, bcy = box("team")
E.append(arrow([(acx - 60, ay2), (bcx + 60, by)], "공고문 · 제안요청서 읽기", tpos=(acx - 30, (ay2 + by) / 2 + 4), anchor="end"))
E.append(left("team", "sheet", "시트 작성 (9/13)"))
E.append(left("sheet", "q", "정답 근거 · 기대 결론"))
E.append(down("sheet", "synth", "충족/미충족/자료부족 설계"))
E.append(left("synth", "l2", "생성"))
E.append(right("synth", "l3", "생성"))
E.append(down("sample", "l1", "그대로 (공개 자료)"))
# service row
E.append(right("user", "ui", "질문"))
E.append(right("ui", "auth", "회사 · 등급"))
E.append(right("auth", "rag", "허용 문서만"))
E.append(right("rag", "gem", "근거 구간"))
E.append(right("gem", "det", "답변 토큰 + 문맥"))
E.append(right("det", "rule", "탐지 결과"))
# L → RAG bundle
rx, ry, rx2, ry2, rcx, rcy = box("rag")
l2x, l2y, l2x2, l2y2, l2cx, l2cy = box("l2"); l3x, l3y, l3x2, l3y2, l3cx, l3cy = box("l3"); l1x, l1y, l1x2, l1y2, l1cx, l1cy = box("l1")
E.append(arrow([(l2cx - 20, l2y2), (rcx - 20, ry)], None, color=STROKE["l2"]))
E.append(label(l2cx - 14, 580, "L2 자기 회사만 색인", anchor="start", size=10))
E.append(arrow([(l3cx, l3y2), (l3cx, 590), (rcx + 20, 590), (rcx + 20, ry)], None, color=STROKE["l3"]))
E.append(label(l3cx + 6, 585, "L3 권한자만 색인", anchor="start", size=10))
E.append(arrow([(l1cx, l1y2), (l1cx, 600), (rcx + 60, 600), (rcx + 60, ry)], None, color=STROKE["l1"]))
E.append(label(l1cx + 6, 596, "L1 전체 색인", anchor="start", size=10))
# questions → gemma (batch, dashed) via gap x=740
qx, qy, qx2, qy2, qcx, qcy = box("q"); gx, gy, gx2, gy2, gcx, gcy = box("gem")
E.append(arrow([(qcx, qy2), (qcx, 440), (740, 440), (740, 612), (gcx - 40, 612), (gcx - 40, gy)], None, dashed=True))
E.append(label(732, 476, "질문 300개 배치 실행", anchor="end", size=10))
# return rail: rule → ui
ux, uy, ux2, uy2, ucx, ucy = box("ui"); rlx, rly, rlx2, rly2, rlcx, rlcy = box("rule")
E.append(arrow([(rlcx, rly), (rlcx, 636), (ucx, 636), (ucx, uy)], None, color=STROKE["core"]))
E.append(label((rlcx + ucx) / 2, 631, "환각 의심 구간 · 숫자 불일치 → 화면에 표시", size=11))
# eval row
E.append(down("gem", "label", "답변 300개", dx=0))
E.append(down("det", "eval", "예측", dx=0))
E.append(right("label", "eval", "정답 라벨"))

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
       f'aria-label="나라장터 공고 수집부터 변환·표본 추출, 팀원 요건 추출, 가상 기업 L1/L2/L3 자료 구축, 권한 필터를 거친 RAG 답변과 환각 탐지, 평가까지의 전체 흐름" '
       f'font-family="Pretendard, \'Noto Sans KR\', \'Malgun Gothic\', system-ui, sans-serif" color="#1f2430">',
       '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
       '<path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker></defs>',
       f'<rect x="0" y="0" width="{W}" height="{H}" fill="#f6f7f9"/>',
       f'<text x="24" y="24" font-size="17" font-weight="800" fill="currentColor">ko-LettuceDetect / ASTRA 전체 구조</text>',
       f'<text x="{W-24}" y="24" font-size="11" text-anchor="end" fill="currentColor" opacity="0.7">2026-09-12 기준 · 실선 = 데이터 흐름 · 점선 = 배치 작업/보조 · 색 테두리 = 문서 등급 · 주황 = 핵심 모델과 그 결과</text>']
for y, h, title, fill in BANDS:
    svg.append(f'<rect x="20" y="{y}" width="{W-40}" height="{h}" rx="12" fill="{fill}" stroke="#d6dae2" stroke-width="1"/>')
    svg.append(f'<text x="34" y="{y+18}" font-size="12.5" font-weight="700" fill="currentColor" opacity="0.85">{html.escape(title)}</text>')
svg += E
for nid in N:
    svg.append(node_svg(nid))
svg.append('</svg>')
svg_text = "\n".join(svg)

# arrowheads: context-stroke has limited support; fall back to currentColor-colored marker copies
svg_text = svg_text.replace('fill="context-stroke"', 'fill="#1f2430"')
for cname, chex in (("l1", STROKE["l1"]), ("l2", STROKE["l2"]), ("l3", STROKE["l3"]), ("core", STROKE["core"])):
    svg_text = svg_text.replace(
        f'stroke="{chex}" stroke-width="1.4" marker-end="url(#arr)"', f'stroke="{chex}" stroke-width="1.4" marker-end="url(#arr-{cname})"')
extra = ''.join(f'<marker id="arr-{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{STROKE[c]}"/></marker>' for c in ("l1", "l2", "l3", "core"))
svg_text = svg_text.replace('</marker></defs>', '</marker>' + extra + '</defs>', 1)

page = f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ko-LettuceDetect 전체 구조</title>
<style>
  body {{ margin: 0; background: #f6f7f9; color: #1f2430; font-family: Pretendard, "Noto Sans KR", "Malgun Gothic", system-ui, sans-serif; }}
  main {{ max-width: 1760px; margin: 0 auto; padding: 20px 20px 40px; }}
  figure {{ margin: 0; }}
  svg {{ width: 100%; height: auto; display: block; border-radius: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  figcaption {{ font-size: 14px; line-height: 1.6; margin-top: 14px; color: #3a4150; }}
  figcaption b {{ color: #1f2430; }}
</style></head>
<body><main>
<figure>
{svg_text}
<figcaption>
<b>읽는 법.</b> 위에서 아래로 다섯 단계다. ① 세 워크스테이션이 나라장터 API로 4·5·6월 공고 137,745행과 첨부를 모아 해시 저장소에 둔다.
② 어댑터가 이를 파이프라인 입력으로 바꾸고, 세 달 분야 표에서 <b>정보시스템 구축·운영</b>을 골라 표본 51건을 뽑았다.
③ 팀원 5명이 공고문과 제안요청서에서 자격·실적·인력·인증·금액·일정을 시트로 옮기고, 그 시트가 질문 300개의 정답 근거가 된다.
④ 시트 조건에 맞춰 가상 기업 5곳의 L2(내부)·L3(민감) 자료를 합성하고, 표본은 그대로 L1(공개)이 된다. 어떤 기업이 어떤 조건을 충족·미충족하는지는 설계 단계에서 확정된다.
⑤ 직원이 회사·역할로 로그인해 질문하면 권한 필터가 검색 후보를 자기 회사 문서로 제한하고, RAG가 찾은 근거로 Gemma가 답을 쓴다.
<b>직접 학습한 환각 탐지 모델</b>이 답변 토큰마다 근거 유무를 판정하고, 모델이 약한 숫자 변조는 규칙 검증이 문서 숫자와 직접 대조해 보완한다. 결과는 화면에 근거 하이라이트와 환각 표시로 돌아온다.
질문 300개를 배치로 돌린 답변은 팀원이 라벨링해 탐지율을 재고, 권한 차단은 20케이스로 따로 검증한다.
</figcaption>
</figure>
</main></body></html>'''
OUT = r'C:\Users\aidan\Desktop\AI프로젝트\ko-lettucedetect\project-docs\도면'
io.open(OUT + r'\프로젝트_구조.html', 'w', encoding='utf-8').write(page)
io.open(OUT + r'\프로젝트_구조.svg', 'w', encoding='utf-8').write(svg_text)
import xml.dom.minidom
xml.dom.minidom.parseString(svg_text.encode('utf-8'))
print("HTML/SVG 생성 완료, SVG 문법 OK, 노드", len(N), "화살표", sum(1 for e in E if 'marker-end' in e))
