# -*- coding: utf-8 -*-
"""RAGTruth에서 10건을 뽑아 <HAL> 태그를 삽입한 번역 입력을 만든다."""
import json, random, collections

D = "data/"
resp = [json.loads(l) for l in open(D+"response.jsonl", encoding="utf-8")]
srcs = {s["source_id"]: s for s in (json.loads(l) for l in open(D+"source_info.jsonl", encoding="utf-8"))}

def merge(spans):
    """겹치는 구간을 병합한다. 겹침이 있었는지도 함께 돌려준다."""
    spans = sorted(spans, key=lambda x: (x["start"], x["end"]))
    out, overlapped = [], False
    for s in spans:
        if out and s["start"] <= out[-1]["end"]:
            if s["start"] < out[-1]["end"]:
                overlapped = True
            out[-1] = {"start": out[-1]["start"], "end": max(out[-1]["end"], s["end"])}
        else:
            out.append({"start": s["start"], "end": s["end"]})
    return out, overlapped

def tag(text, spans):
    """뒤에서부터 삽입해야 앞쪽 오프셋이 밀리지 않는다."""
    for s in sorted(spans, key=lambda x: -x["start"]):
        text = text[:s["start"]] + "<HAL>" + text[s["start"]:s["end"]] + "</HAL>" + text[s["end"]:]
    return text

# 후보: 라벨 1~3개, 응답 300~1400자 (번역 한 번에 들어가는 크기)
cands = collections.defaultdict(list)
for r in resp:
    if not r.get("labels"): continue
    if not (300 <= len(r["response"]) <= 1400): continue
    m, _ = merge(r["labels"])
    if not (1 <= len(m) <= 3): continue
    tt = srcs[r["source_id"]]["task_type"]
    cands[tt].append(r)

print("task_type별 후보 수:", {k: len(v) for k, v in cands.items()})

random.seed(20260901)
picked = []
for tt, n in [("QA", 4), ("Data2txt", 3), ("Summary", 3)]:
    picked += random.sample(cands[tt], n)

items = []
for i, r in enumerate(picked, 1):
    m, ov = merge(r["labels"])
    src = srcs[r["source_id"]]
    items.append({
        "no": i, "id": r["id"], "task_type": src["task_type"], "model": r["model"],
        "overlap_merged": ov, "n_spans": len(m),
        "spans_en": [r["response"][s["start"]:s["end"]] for s in m],
        "label_types": sorted({l["label_type"] for l in r["labels"]}),
        "response_raw": r["response"],
        "response_tagged": tag(r["response"], m),
        "n_chars": len(r["response"]),
    })

json.dump(items, open("추출_10건.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

with open("번역_입력.txt", "w", encoding="utf-8") as f:
    for it in items:
        f.write(f"===== #{it['no']} | {it['task_type']} | id={it['id']} | 태그 {it['n_spans']}개 | {it['n_chars']}자 =====\n")
        f.write(it["response_tagged"] + "\n\n")

print(f"\n총 {len(items)}건 추출")
for it in items:
    print(f"  #{it['no']:>2} {it['task_type']:<9} 태그{it['n_spans']}개 {it['n_chars']:>5}자  겹침병합={it['overlap_merged']}  {it['label_types']}")
