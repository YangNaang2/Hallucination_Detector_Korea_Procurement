# -*- coding: utf-8 -*-
"""번역 결과에서 <HAL> 태그가 살아남았는지, 한국어 경계 문제가 없는지 검사한다."""
import json, re, io, sys

items = json.load(open("추출_10건.json", encoding="utf-8"))
raw = open("번역_출력.txt", encoding="utf-8").read()

blocks = {}
for m in re.finditer(r"^===== #(\d+) =====\n(.*?)(?=^===== #|\Z)", raw, re.S | re.M):
    blocks[int(m.group(1))] = m.group(2).strip()

# 뒤에 붙으면 구간 경계가 어긋나는 조사·어미 (긴 것부터)
JOSA = ["으로부터","에서부터","까지도","에서는","으로는","이라는","라는","에게서","으로써","으로서",
        "까지","부터","에서","에게","한테","으로","라고","이라","와의","과의","의","와","과","을","를",
        "은","는","이","가","도","로","만","에","보다","처럼","마다","조차","밖에"]
OUT = io.StringIO()
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s); OUT.write(s + "\n")

TAG = re.compile(r"</?HAL>")
rows = []
P("# <HAL> 태그 번역 생존 시험 — 검사 결과\n")

for it in items:
    n = it["no"]; ko = blocks.get(n, "")
    tags = TAG.findall(ko)
    n_open, n_close = tags.count("<HAL>"), tags.count("</HAL>")

    # 1) 짝·중첩 검사
    depth = 0; wellformed = True; nested = False
    for t in tags:
        depth += 1 if t == "<HAL>" else -1
        if depth > 1: nested = True
        if depth < 0: wellformed = False
    if depth != 0: wellformed = False

    ko_spans = re.findall(r"<HAL>(.*?)</HAL>", ko, re.S)
    plain = TAG.sub("", ko)

    # 2) 개수 일치
    count_ok = (n_open == n_close == it["n_spans"])
    # 3) 빈 구간
    empty = [s for s in ko_spans if not s.strip()]
    # 4) 조사 경계 — </HAL> 바로 뒤에 조사가 붙어 있는가
    josa_hits = []
    for m in re.finditer(r"</HAL>", ko):
        after = ko[m.end():m.end()+6]
        for j in JOSA:
            if after.startswith(j):
                josa_hits.append(j); break
    # 5) 구간 위치 이동량 (문서 내 상대 위치 비교)
    shifts = []
    en_plain = it["response_raw"]
    for k, sp in enumerate(ko_spans):
        pk = plain.find(sp) / max(len(plain), 1)
        pe = en_plain.find(it["spans_en"][k]) / max(len(en_plain), 1) if k < len(it["spans_en"]) else -1
        if pe >= 0: shifts.append(round(abs(pk - pe), 3))

    ok = count_ok and wellformed and not nested and not empty
    rows.append({"no": n, "task": it["task_type"], "expect": it["n_spans"], "got": n_open,
                 "wellformed": wellformed, "nested": nested, "empty": len(empty),
                 "josa": josa_hits, "max_shift": max(shifts) if shifts else None, "ok": ok,
                 "ko_spans": ko_spans, "en_spans": it["spans_en"]})

    P(f"## #{n} [{it['task_type']}]  {'PASS' if ok else 'FAIL'}")
    P(f"- 태그 개수: 기대 {it['n_spans']} / 실제 여는태그 {n_open}, 닫는태그 {n_close} → {'일치' if count_ok else '불일치'}")
    P(f"- 짝 맞음: {wellformed} / 중첩: {nested} / 빈 구간: {len(empty)}")
    P(f"- 구간 위치 이동(상대, 0~1): {shifts}")
    if josa_hits: P(f"- !! 조사 경계 문제: </HAL> 뒤에 '{', '.join(josa_hits)}' 가 붙음")
    for k, sp in enumerate(ko_spans):
        en = it["spans_en"][k] if k < len(it["spans_en"]) else "(대응 없음)"
        P(f"  · EN: {en[:90]}")
        P(f"    KO: {sp[:90]}")
    P("")

P("\n# 요약\n")
P("| # | 유형 | 기대 | 실제 | 짝 | 중첩 | 조사문제 | 최대이동 | 판정 |")
P("|---|------|------|------|----|------|---------|---------|------|")
for r in rows:
    P(f"| {r['no']} | {r['task']} | {r['expect']} | {r['got']} | {'O' if r['wellformed'] else 'X'} | "
      f"{'있음' if r['nested'] else '-'} | {', '.join(r['josa']) if r['josa'] else '-'} | "
      f"{r['max_shift']} | {'통과' if r['ok'] else '실패'} |")

npass = sum(r["ok"] for r in rows)
njosa = sum(1 for r in rows if r["josa"])
P(f"\n- **태그 보존율: {npass}/{len(rows)} ({npass/len(rows)*100:.0f}%)**")
P(f"- **조사 경계 문제 발생: {njosa}/{len(rows)}건**")
P(f"- 총 구간 수: 기대 {sum(r['expect'] for r in rows)} / 보존 {sum(r['got'] for r in rows)}")

open("검사_결과.md", "w", encoding="utf-8").write(OUT.getvalue())
json.dump(rows, open("검사_결과.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
