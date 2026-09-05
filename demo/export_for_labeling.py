"""데모 로그 → 손라벨링 시트. — D 파트

**문장 단위로 라벨링한다.** 구간(문자 단위)으로 라벨링하면 사람마다 경계가 달라
일치도가 떨어지고 시간도 몇 배 든다. 문장 단위면 "이 문장이 문서로 뒷받침되는가"
라는 예/아니오 판단만 하면 되고, 채점할 때 모델 예측을 문장 단위로 올려서 비교하면
공정하다(`score_eval2.py`).

만드는 것 두 개
  labels/label_sheet.jsonl   채점 스크립트가 읽는 원본
  labels/label_sheet.html    라벨러가 클릭만 하면 되는 화면 (JSON 내려받기 버튼 포함)

사용
  python demo/export_for_labeling.py
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "logs" / "eval2.jsonl"
OUT_DIR = HERE / "labels"

SENT_RE = re.compile(r"(?<=[.!?])\s+|(?<=다\.)\s+|\n+")


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


HTML_HEAD = """<!doctype html><meta charset="utf-8"><title>환각 라벨링</title>
<style>
body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.7}
.item{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1.5rem 0}
.q{font-weight:600;color:#1a4d8f}
.ctx{background:#f6f7f9;padding:.8rem;border-radius:6px;font-size:.88rem;
     max-height:16rem;overflow:auto;white-space:pre-wrap;margin:.6rem 0}
.sent{display:block;padding:.35rem .5rem;border-radius:4px;cursor:pointer}
.sent:hover{background:#f0f4ff}
input:checked + span{background:#ffe1e1;text-decoration:underline wavy #c00}
button{position:sticky;bottom:1rem;padding:.7rem 1.4rem;font-size:1rem;
       background:#1a4d8f;color:#fff;border:0;border-radius:6px;cursor:pointer}
h1{font-size:1.4rem} .hint{color:#555;font-size:.9rem}
</style>
<h1>환각 라벨링</h1>
<p class="hint"><b>[문서]에 근거가 없는 문장</b>에만 체크하세요. 문서에 있는 내용이면
표현이 달라도 체크하지 않습니다. 판단이 어려우면 넘어가고 회의에서 함께 봅니다.<br>
다 하면 맨 아래 <b>내려받기</b> 를 눌러 나온 파일을 프로젝트 담당에게 보내세요.</p>
"""

HTML_TAIL = """
<button onclick="save()">라벨 내려받기 (labels_done.json)</button>
<script>
function save(){
  const out={};
  document.querySelectorAll('input[type=checkbox]').forEach(c=>{
    const [i,j]=c.dataset.k.split('|');
    (out[i]=out[i]||[]).push({sent:+j, hallucinated:c.checked});
  });
  const b=new Blob([JSON.stringify(out,null,1)],{type:'application/json'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(b); a.download='labels_done.json'; a.click();
}
</script>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=str(LOG_PATH))
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    log = Path(args.log)
    if not log.exists():
        raise SystemExit(f"[!] 로그가 없습니다: {log}\n    데모에서 '이 답변 저장'을 먼저 누르세요.")

    records = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet, body = [], []
    for i, r in enumerate(records):
        sents = split_sentences(r["answer"])
        sheet.append({"idx": i, "question": r["question"], "context": r["context"],
                      "answer": r["answer"],
                      "sentences": [{"sent": j, "start": s, "end": e,
                                     "text": r["answer"][s:e]}
                                    for j, (s, e) in enumerate(sents)]})
        rows = "".join(
            f'<label class="sent"><input type="checkbox" data-k="{i}|{j}">'
            f'<span>{html.escape(r["answer"][s:e])}</span></label>'
            for j, (s, e) in enumerate(sents))
        body.append(
            f'<div class="item"><div class="q">Q{i + 1}. {html.escape(r["question"])}</div>'
            f'<div class="ctx">{html.escape(r["context"])}</div>{rows}</div>')

    with open(out_dir / "label_sheet.jsonl", "w", encoding="utf-8") as f:
        for s in sheet:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    (out_dir / "label_sheet.html").write_text(
        HTML_HEAD + "\n".join(body) + HTML_TAIL, encoding="utf-8")

    n_sent = sum(len(s["sentences"]) for s in sheet)
    print(f"{len(sheet)}건 · 문장 {n_sent}개")
    print(f"→ {out_dir / 'label_sheet.html'}  (브라우저로 열어 라벨링)")
    print(f"→ {out_dir / 'label_sheet.jsonl'}")
    print("\n라벨링이 끝나면 labels_done.json 을 labels/ 에 두고 score_eval2.py 를 돌리세요.")


if __name__ == "__main__":
    main()
