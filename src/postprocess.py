"""번역 결과 검증 + 문자 오프셋 재계산 + QC 리포트.

`<HAL>` 태그는 번역문 안에서 내용과 함께 이동하므로, 번역 후 **태그 위치에서
start/end 를 다시 계산**해야 한다 (논문 Table I: 영어 start 636 → 터키어 545).

여기서 만드는 `work/qc_report.md` 가 "200건 배치 태그 보존율 재측정" 결과물이다.

사용
  python -m src.postprocess
"""
from __future__ import annotations

import argparse
import re
import statistics
from collections import Counter
from pathlib import Path

import config as C
from src.prepare_ragtruth import load_jsonl, write_jsonl

TAG_RE = re.compile(re.escape(C.HAL_OPEN) + "|" + re.escape(C.HAL_CLOSE))
# 한국어 조사 — 구간 경계 바로 뒤에 붙어 나오면 경고만 남긴다 (임의 보정하지 않는다)
JOSA_RE = re.compile(r"^(은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만|까지|부터|보다|께|에게|한테)")


def parse_tagged(text: str) -> tuple[str, list[tuple[int, int]], str | None]:
    """`<HAL>…</HAL>` 이 박힌 텍스트를 (태그 제거 텍스트, 구간들, 오류) 로 분해."""
    clean_parts: list[str] = []
    spans: list[tuple[int, int]] = []
    pos = 0          # 원문(태그 포함) 커서
    out_len = 0      # 태그 제거 후 길이
    open_at: int | None = None

    for m in TAG_RE.finditer(text):
        chunk = text[pos:m.start()]
        clean_parts.append(chunk)
        out_len += len(chunk)
        pos = m.end()

        if m.group() == C.HAL_OPEN:
            if open_at is not None:
                return "", [], "중첩된 <HAL>"
            open_at = out_len
        else:
            if open_at is None:
                return "", [], "짝 없는 </HAL>"
            if out_len > open_at:
                spans.append((open_at, out_len))
            open_at = None

    if open_at is not None:
        return "", [], "닫히지 않은 <HAL>"

    clean_parts.append(text[pos:])
    return "".join(clean_parts), spans, None


def check_record(rec: dict) -> tuple[dict | None, str]:
    """한 건을 검증한다. (정상 레코드 또는 None, 사유) 를 돌려준다."""
    ko_tagged = (rec.get("answer_ko_tagged") or "").strip()
    if not ko_tagged:
        return None, "번역 결과 없음"

    n_open_src = rec["answer_en_tagged"].count(C.HAL_OPEN)
    n_close_src = rec["answer_en_tagged"].count(C.HAL_CLOSE)
    n_open_ko = ko_tagged.count(C.HAL_OPEN)
    n_close_ko = ko_tagged.count(C.HAL_CLOSE)

    if (n_open_ko, n_close_ko) != (n_open_src, n_close_src):
        return None, f"태그 개수 불일치 (원본 {n_open_src}/{n_close_src} → 번역 {n_open_ko}/{n_close_ko})"

    answer_ko, spans_ko, err = parse_tagged(ko_tagged)
    if err:
        return None, f"태그 구조 오류: {err}"
    if len(spans_ko) != rec["n_spans"]:
        return None, f"구간 수 불일치 ({rec['n_spans']} → {len(spans_ko)})"
    if not answer_ko.strip():
        return None, "태그 제거 후 본문이 빔"

    warnings = []
    for s, e in spans_ko:
        if JOSA_RE.match(answer_ko[e:e + 4]):
            warnings.append(f"조사 밀림 의심 @{e}")

    ratio = len(answer_ko) / max(1, len(rec["answer_en"]))
    if not (0.3 <= ratio <= 3.0):
        warnings.append(f"길이비 이상 {ratio:.2f}")

    return {
        "response_id": rec.get("response_id"),
        "source_id": rec.get("source_id"),
        "model": rec.get("model"),
        "split": rec.get("split"),
        "task_type": rec.get("task_type"),
        "question": rec.get("question_ko") or "",
        "context": rec.get("context_ko") or "",
        "answer": answer_ko,
        "spans": [list(s) for s in spans_ko],
        "n_spans": len(spans_ko),
        "len_ratio": round(ratio, 3),
        "warnings": warnings,
    }, "ok"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=None)
    ap.add_argument("--out", dest="out", default=None)
    args = ap.parse_args()

    inp = Path(args.inp) if args.inp else (C.WORK_DIR / "translated.jsonl")
    # translated_pilot12b.jsonl → ko_ragtruth_pilot12b.jsonl / qc_report_pilot12b.md
    suffix = inp.stem.replace("translated", "", 1)
    out = Path(args.out) if args.out else (C.WORK_DIR / f"ko_ragtruth{suffix}.jsonl")
    report = C.WORK_DIR / f"qc_report{suffix}.md"

    rows = load_jsonl(inp)
    good, reasons, ratios, warn_counter = [], Counter(), [], Counter()

    for rec in rows:
        ok, reason = check_record(rec)
        if ok is None:
            reasons[reason.split(" (")[0]] += 1
            continue
        good.append(ok)
        ratios.append(ok["len_ratio"])
        for w in ok["warnings"]:
            warn_counter[w.split(" @")[0]] += 1

    # 태그가 있던 레코드만 따로 — 보존율의 진짜 분모
    with_tags = [r for r in rows if r.get("n_spans", 0) > 0]
    good_with_tags = [g for g in good if g["n_spans"] > 0]

    n = write_jsonl(out, good)

    total = len(rows)
    rate = 100.0 * len(good) / max(1, total)
    tag_rate = 100.0 * len(good_with_tags) / max(1, len(with_tags))
    n_spans_src = sum(r.get("n_spans", 0) for r in with_tags)
    n_spans_ko = sum(g["n_spans"] for g in good_with_tags)

    lines = [
        "# 번역 QC 리포트",
        "",
        f"- 입력 파일: `{inp.name}`",
        f"- 입력 {total:,} 건 / 통과 **{len(good):,} 건 ({rate:.1f}%)**",
        f"- 환각 라벨이 있던 건: {len(with_tags):,} 건 중 **{len(good_with_tags):,} 건 통과 "
        f"({tag_rate:.1f}%) ← 태그 보존율**",
        f"- 구간 수: 원본 {n_spans_src:,} → 번역 {n_spans_ko:,}",
    ]
    if ratios:
        lines.append(
            f"- 길이비(한국어/영어 문자수): 중앙값 {statistics.median(ratios):.2f}, "
            f"최소 {min(ratios):.2f}, 최대 {max(ratios):.2f}"
        )
    lines += ["", "## 실패 사유", ""]
    if reasons:
        lines += ["| 사유 | 건수 |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in reasons.most_common()]
    else:
        lines.append("실패 없음.")

    lines += ["", "## 경고 (버리지 않고 표시만 함)", ""]
    if warn_counter:
        lines += ["| 종류 | 건수 |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in warn_counter.most_common()]
        lines += ["", "> 조사 밀림은 결함이 아니라 한국어 고유의 연구 소재다. 임의로 보정하지 않는다."]
    else:
        lines.append("경고 없음.")

    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:9]))
    print(f"\n→ {out}  ({n:,} 건)")
    print(f"→ {report}")


if __name__ == "__main__":
    main()
