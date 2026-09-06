"""데모 로그 → 손라벨링 시트. — 평가② 준비

**문장 단위로 라벨링한다.** 구간(문자 단위)으로 라벨링하면 사람마다 경계가 달라
일치도가 떨어지고 시간도 몇 배 든다. 문장 단위면 "이 문장이 문서로 뒷받침되는가"
라는 예/아니오 판단만 하면 되고, 채점할 때 모델 예측을 문장 단위로 올려서 비교하면
공정하다(score_eval2.py).

**로그를 그대로 쓰면 안 된다.** demo/logs/eval2.jsonl 에는 시스템 프롬프트를 고치기
전의 1차 실행(답변 대부분이 "문서에 없습니다" 라는 거부였다)과 그 뒤의 2차 실행,
그리고 dry_run.py 기록이 뒤섞여 있다. 거부 답변은 문장이 한두 개뿐이라 라벨링
분량만 잡아먹고, 같은 질문이 여러 번 들어 있으면 같은 문장을 두 번 라벨링하게 된다.
그래서 기본으로 **시간 필터 · 중복 제거 · 거부 답변 제외**를 건다.

**두 사람이 나눠 하고 일부는 겹치게 한다.** 겹치는 부분에서 두 사람의 판단이 얼마나
일치하는지(일치도)를 잴 수 있어야 한다. 일치도가 낮으면 라벨 자체가 못 믿을 것이 되고,
그러면 평가② 숫자도 의미가 없다. 발표에서 "라벨러 2인, 일치도 0.8" 이라고 말할 수
있는 것과 없는 것의 차이가 크다.

만드는 것
  labels/label_sheet.jsonl      채점 스크립트가 읽는 원본 (전체, 정본 idx)
  labels/label_sheet_1.html     라벨러 1이 여는 화면
  labels/label_sheet_2.html     라벨러 2가 여는 화면 (일부 문항이 1과 겹친다)

사용
  python demo/export_for_labeling.py                      # 2인 · 겹침 10문항
  python demo/export_for_labeling.py --labelers 1         # 혼자 다 할 때
  python demo/export_for_labeling.py --since 2026-09-05   # 그 날짜 이후 기록만
"""
from __future__ import annotations

import argparse
import html
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "logs" / "eval2.jsonl"
OUT_DIR = HERE / "labels"

SENT_RE = re.compile(r"(?<=[.!?])\s+|(?<=다\.)\s+|\n+")

# 1차 실행에서 쏟아진 거부 답변. 이런 답변은 문장이 한두 개뿐이라 라벨링 가치가 낮고,
# 학습 데이터에 이런 표현이 없어 모델이 늘 환각으로 찍는다(라벨 규약 불일치).
# 빼는 편이 평가② 숫자를 정직하게 만든다.
REFUSAL_KEYS = ("확인되지 않", "찾을 수 없", "나와 있지 않", "언급되지 않",
                "알 수 없", "제공된 문서에는", "정보가 없")


def split_sentences(text: str) -> list[tuple[int, int]]:
    """문장 경계를 (시작, 끝) 문자 위치로 돌려준다."""
    spans, pos = [], 0
    for m in SENT_RE.finditer(text):
        if m.start() > pos:
            spans.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        spans.append((pos, len(text)))
    return [(s, e) for s, e in spans if text[s:e].strip()]


def is_refusal(answer: str) -> bool:
    return any(k in answer for k in REFUSAL_KEYS)


def select(records, since, drop_refusal, keep_dups, min_sents):
    """라벨링할 기록만 골라낸다. 무엇을 왜 뺐는지 함께 돌려준다."""
    dropped = {"시간": 0, "거부": 0, "중복": 0, "너무짧음": 0, "빈답변": 0}
    kept = []
    for r in records:
        answer = (r.get("answer") or "").strip()
        if not answer:
            dropped["빈답변"] += 1
            continue
        if since and (r.get("time") or "") < since:
            dropped["시간"] += 1
            continue
        if drop_refusal and is_refusal(answer):
            dropped["거부"] += 1
            continue
        if len(split_sentences(answer)) < min_sents:
            dropped["너무짧음"] += 1
            continue
        kept.append(r)

    if not keep_dups:
        # 같은 질문이 여러 번 있으면 마지막 것만 남긴다 (뒤에 실행한 쪽이 최신 설정이다)
        by_q = {}
        for r in kept:
            by_q[(r.get("question") or "").strip()] = r
        dropped["중복"] = len(kept) - len(by_q)
        kept = list(by_q.values())

    return kept, dropped


HTML_HEAD = """<!doctype html><meta charset="utf-8"><title>환각 라벨링 — 라벨러 {who}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.7}}
.item{{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1.5rem 0}}
.q{{font-weight:600;color:#1a4d8f}}
.ctx{{background:#f6f7f9;padding:.8rem;border-radius:6px;font-size:.88rem;
     max-height:16rem;overflow:auto;white-space:pre-wrap;margin:.6rem 0}}
.sent{{display:block;padding:.35rem .5rem;border-radius:4px;cursor:pointer}}
.sent:hover{{background:#f0f4ff}}
input:checked + span{{background:#ffe1e1;text-decoration:underline wavy #c00}}
button{{position:sticky;bottom:1rem;padding:.7rem 1.4rem;font-size:1rem;
       background:#1a4d8f;color:#fff;border:0;border-radius:6px;cursor:pointer}}
h1{{font-size:1.4rem}} .hint{{color:#555;font-size:.9rem}}
.bar{{position:sticky;top:0;background:#fff;padding:.5rem 0;border-bottom:1px solid #eee;
     font-size:.9rem;color:#1a4d8f}}
</style>
<h1>환각 라벨링 — 라벨러 {who}</h1>
<p class="hint">
<b>[문서]에 근거가 없는 문장</b>에만 체크하세요. 문서에 있는 내용이면 표현이 달라도
체크하지 않습니다.<br>
문서의 단어를 그대로 쓰면서 <b>관계나 숫자를 잘못 엮은 문장</b>도 근거 없음입니다
(예: 문서에 130학점과 9학점이 따로 있는데 "합쳐서 139학점" 이라고 한 경우).<br>
판단이 어려우면 <b>체크하지 말고 넘어간 뒤</b> 회의에서 함께 봅니다.<br>
다 하면 맨 아래 <b>내려받기</b> 를 눌러 나온 파일을 검증 모델 담당에게 보내세요.
</p>
<div class="bar">문항 {n}개 · 문장 {n_sent}개 · 예상 소요 {mins}분</div>
"""

HTML_TAIL = """
<button onclick="save()">라벨 내려받기 (labels_done_{who}.json)</button>
<script>
function save(){{
  const out={{}};
  document.querySelectorAll('input[type=checkbox]').forEach(c=>{{
    const [i,j]=c.dataset.k.split('|');
    (out[i]=out[i]||[]).push({{sent:+j, hallucinated:c.checked}});
  }});
  const b=new Blob([JSON.stringify(out,null,1)],{{type:'application/json'}});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(b); a.download='labels_done_{who}.json'; a.click();
}}
</script>"""


def render(sheet_items, who: str) -> str:
    body = []
    for item in sheet_items:
        i = item["idx"]
        rows = "".join(
            '<label class="sent"><input type="checkbox" data-k="%d|%d">'
            '<span>%s</span></label>' % (i, s["sent"], html.escape(s["text"]))
            for s in item["sentences"])
        body.append(
            '<div class="item"><div class="q">Q%d. %s</div>'
            '<div class="ctx">%s</div>%s</div>'
            % (i + 1, html.escape(item["question"]),
               html.escape(item["context"]), rows))
    n_sent = sum(len(it["sentences"]) for it in sheet_items)
    head = HTML_HEAD.format(who=who, n=len(sheet_items), n_sent=n_sent,
                            mins=max(5, round(n_sent * 0.4)))
    return head + "\n".join(body) + HTML_TAIL.format(who=who)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=str(LOG_PATH))
    ap.add_argument("--out", default=str(OUT_DIR))
    ap.add_argument("--since", default=None,
                    help="이 시각 이후 기록만 (예: 2026-09-05). 1차 실행분을 잘라낸다")
    ap.add_argument("--labelers", type=int, default=2, help="나눠 라벨링할 사람 수")
    ap.add_argument("--overlap", type=int, default=10,
                    help="일치도 측정용으로 모든 라벨러에게 공통으로 주는 문항 수")
    ap.add_argument("--min-sents", type=int, default=2,
                    help="문장이 이보다 적은 답변은 뺀다")
    ap.add_argument("--keep-refusal", action="store_true",
                    help="거부 답변('문서에 없습니다')도 라벨링 대상에 넣는다")
    ap.add_argument("--keep-dups", action="store_true",
                    help="같은 질문의 중복 기록을 모두 남긴다")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    log = Path(args.log)
    if not log.exists():
        raise SystemExit("[!] 로그가 없습니다: %s\n    데모에서 '이 답변 저장'을 먼저 누르세요." % log)

    records = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    kept, dropped = select(records, args.since, not args.keep_refusal,
                           args.keep_dups, args.min_sents)

    print("로그 %d건 → 라벨링 대상 %d건" % (len(records), len(kept)))
    for k, v in dropped.items():
        if v:
            print("  뺀 것 · %s %d건" % (k, v))
    if not kept:
        raise SystemExit("[!] 남은 기록이 없습니다. --since 를 풀거나 --keep-refusal 을 주세요.")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet = []
    for i, r in enumerate(kept):
        sents = split_sentences(r["answer"])
        sheet.append({"idx": i, "time": r.get("time"), "question": r["question"],
                      "context": r["context"], "answer": r["answer"],
                      "sentences": [{"sent": j, "start": s, "end": e,
                                     "text": r["answer"][s:e]}
                                    for j, (s, e) in enumerate(sents)]})

    with open(out_dir / "label_sheet.jsonl", "w", encoding="utf-8") as f:
        for s in sheet:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    n_sent = sum(len(s["sentences"]) for s in sheet)
    print("문항 %d개 · 문장 %d개" % (len(sheet), n_sent))

    n_lab = max(1, args.labelers)
    if n_lab == 1:
        (out_dir / "label_sheet_1.html").write_text(render(sheet, "1"), encoding="utf-8")
        print("→ %s" % (out_dir / "label_sheet_1.html"))
    else:
        rng = random.Random(args.seed)
        idxs = list(range(len(sheet)))
        rng.shuffle(idxs)
        n_ov = min(args.overlap, len(sheet) // 2)
        shared = sorted(idxs[:n_ov])
        rest = idxs[n_ov:]
        for k in range(n_lab):
            mine = sorted(shared + rest[k::n_lab])
            items = [sheet[i] for i in mine]
            who = str(k + 1)
            (out_dir / ("label_sheet_%s.html" % who)).write_text(
                render(items, who), encoding="utf-8")
            ns = sum(len(it["sentences"]) for it in items)
            print("→ %s  문항 %d개 (겹침 %d) · 문장 %d개"
                  % (out_dir / ("label_sheet_%s.html" % who), len(items), n_ov, ns))
        print("\n겹치는 %d문항으로 두 사람의 일치도를 잽니다. "
              "일치도가 낮으면 라벨을 다시 맞춘 뒤 채점하세요." % n_ov)

    print("\n라벨링이 끝나면 받은 파일들을 labels/ 에 두고:")
    print("  python demo/score_eval2.py --labels labels/labels_done_*.json")


if __name__ == "__main__":
    main()
