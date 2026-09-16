#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나라장터 독립형 GPU OCR 단계.

CPU 일반 파싱이 모두 끝난 뒤 실행하는 별도 프로그램.
현재 quarantine에 남은 PDF 후보만 기존 raw에서 읽어 EasyOCR CUDA로 처리.

- 나라장터 API 호출 없음
- 첨부 재다운로드 없음
- CPU 일반 파싱과 동시 실행하지 않는 것을 권장
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import easyocr
import numpy as np
import pymupdf
import torch

import g2b_core as core
import g2b_month_pipeline as pipeline


OCR_VERSION = "easyocr-cuda-v3"


def render_page(page, dpi: int):
    scale = dpi / 72.0
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(scale, scale),
        colorspace=pymupdf.csRGB,
        alpha=False,
    )
    arr = np.frombuffer(pix.samples, dtype=np.uint8)
    arr = arr.reshape(pix.height, pix.width, pix.n)
    if pix.n > 3:
        arr = arr[:, :, :3]
    return arr


def ocr_pdf(reader, data: bytes, dpi: int, max_pages: int | None):
    doc = pymupdf.open(stream=data, filetype="pdf")
    blocks = []
    texts = []

    try:
        page_count = len(doc)
        if max_pages is not None:
            page_count = min(page_count, max_pages)

        for page_no in range(page_count):
            image = render_page(doc[page_no], dpi)
            lines = reader.readtext(
                image,
                detail=0,
                paragraph=False,
                workers=0,
            )
            lines = [str(x).strip() for x in lines if str(x).strip()]
            text = "\n".join(lines)

            texts.append(f"[페이지 {page_no + 1}]\n{text}")
            blocks.append({
                "type": "page",
                "order": page_no,
                "page": page_no + 1,
                "source": "easyocr-cuda",
                "text": text,
            })
            del image

        return "\n\n".join(texts).strip(), blocks
    finally:
        doc.close()


def load_download_index(base: Path):
    out = {}
    for row in pipeline.read_jsonl(base / "download_manifest.jsonl"):
        if row.get("download_status") != "downloaded":
            continue
        docid = str(row.get("document_id") or "")
        if docid:
            out.setdefault(docid, row)
    return out


def find_targets(base: Path):
    by_docid = load_download_index(base)
    targets = {}
    non_pdf = set()
    raw_missing = set()

    for qrow in pipeline.read_jsonl(base / "quarantine.jsonl"):
        for attempt in qrow.get("candidate_attempts") or []:
            docid = str(attempt.get("document_id") or "")
            if not docid or docid not in by_docid:
                continue

            drow = by_docid[docid]
            raw_path = Path(str(drow.get("raw_path") or ""))
            if not raw_path.exists():
                raw_missing.add(docid)
                continue

            try:
                with raw_path.open("rb") as f:
                    head = f.read(5)
            except Exception:
                raw_missing.add(docid)
                continue

            if raw_path.suffix.lower() == ".pdf" or head.startswith(b"%PDF"):
                targets.setdefault(docid, drow)
            else:
                non_pdf.add(docid)

    return targets, non_pdf, raw_missing


def main() -> None:
    ap = argparse.ArgumentParser(
        description="미해결 PDF만 NVIDIA CUDA GPU OCR"
    )
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--month", type=int, required=True, choices=range(1, 13))
    ap.add_argument("--out", default="./data")
    ap.add_argument("--dpi", type=int, default=160)
    ap.add_argument("--min-quality", type=float, default=0.55)
    ap.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="0이면 전체 페이지",
    )
    ap.add_argument(
        "--duplicate-format-priority",
        default="hwpx,docx,hwp,pdf,txt,xls,xlsx,zip",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.dry_run == args.apply:
        ap.error("--dry-run 또는 --apply 중 하나만 선택하세요.")

    base = pipeline.month_base(args.out, args.year, args.month)
    if not (base / "quarantine.jsonl").exists():
        raise SystemExit(
            "quarantine.jsonl 없음. 먼저 CPU parse를 완료하세요."
        )

    targets, non_pdf, raw_missing = find_targets(base)

    print("=" * 80)
    print("GPU OCR 대상 점검")
    print("=" * 80)
    print(f"데이터 폴더             : {base}")
    print(f"미해결 PDF              : {len(targets):>10,}")
    print(f"비-PDF                  : {len(non_pdf):>10,}")
    print(f"raw 없음                : {len(raw_missing):>10,}")
    print(f"CUDA 사용 가능          : {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU                     : {torch.cuda.get_device_name(0)}")
    print("나라장터 API 호출       : OFF")
    print("첨부 재다운로드         : OFF")
    print("CPU 일반 파싱           : OFF")
    print("=" * 80)

    if args.dry_run:
        print("[DRY-RUN] 파일 변경 없음")
        return

    if not torch.cuda.is_available():
        raise SystemExit("PyTorch에서 CUDA GPU가 활성화되어 있지 않습니다.")

    reader = easyocr.Reader(["ko", "en"], gpu=True, verbose=False)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    result_log = base / f"gpu_ocr_results.{stamp}.jsonl"
    result_log.write_text("", encoding="utf-8")

    started = time.time()
    recovered = low_quality = failed = 0
    max_pages = None if args.max_pages <= 0 else args.max_pages

    for idx, (docid, row) in enumerate(targets.items(), 1):
        raw_path = Path(str(row.get("raw_path") or ""))
        attachment = row.get("attachment") or {}
        bid = row.get("bid") or {}

        if idx == 1 or idx % 10 == 0 or idx == len(targets):
            elapsed = max(time.time() - started, 0.001)
            rate = (idx - 1) / elapsed if idx > 1 else 0.0
            remain = (
                (len(targets) - idx + 1) / rate / 60
                if rate else 0.0
            )
            print(
                f"[ocr] {idx:>5,}/{len(targets):,} "
                f"복구 {recovered:,} / low {low_quality:,} / "
                f"failed {failed:,} / 잔여 {remain:.1f}분",
                flush=True,
            )

        try:
            data = raw_path.read_bytes()
            if hashlib.sha256(data).hexdigest() != docid:
                raise RuntimeError("SHA-256 mismatch")

            text, blocks = ocr_pdf(
                reader, data, args.dpi, max_pages
            )
            quality = float(core.extraction_quality(text))
            status = (
                "parsed"
                if text.strip() and quality >= args.min_quality
                else "low_quality"
            )

            parsed_path = base / "parsed" / f"{docid}.json"
            document = {
                "document_id": docid,
                "sha256": docid,
                "source": {
                    "url": attachment.get("url"),
                    "filename": (
                        attachment.get("filename") or raw_path.name
                    ),
                    "attachment_source": attachment.get("source"),
                    "raw_path": str(raw_path),
                },
                "bid": bid,
                "parse": {
                    "status": status,
                    "detected_format": "pdf",
                    "parser": "easyocr-gpu(ko+en)+pymupdf",
                    "quality": round(quality, 4),
                    "warnings": [
                        f"GPU OCR fallback dpi={args.dpi}",
                        "기존 raw 사용 / API 호출 없음 / 재다운로드 없음",
                    ],
                    "pipeline_version": pipeline.PIPELINE_VERSION,
                    "ocr_used": True,
                    "ocr_version": OCR_VERSION,
                    "gpu": torch.cuda.get_device_name(0),
                },
                "text": text,
                "blocks": blocks,
            }
            core.write_json(parsed_path, document)

            if status == "parsed":
                recovered += 1
            else:
                low_quality += 1

            pipeline.append_jsonl(result_log, {
                "document_id": docid,
                "status": status,
                "quality": round(quality, 4),
                "raw_path": str(raw_path),
                "parsed_path": str(parsed_path),
            })

        except Exception as e:
            failed += 1
            pipeline.append_jsonl(result_log, {
                "document_id": docid,
                "status": "failed",
                "raw_path": str(raw_path),
                "error": f"{type(e).__name__}: {e}",
            })

    priority = [
        x.strip().lower().lstrip(".")
        for x in args.duplicate_format_priority.split(",")
        if x.strip()
    ]
    for fmt in pipeline.DEFAULT_PRIORITY:
        if fmt not in priority:
            priority.append(fmt)

    stats = pipeline.rebuild_indexes(
        base,
        min_quality=args.min_quality,
        priority=priority,
    )
    stats.update({
        "gpu_ocr_version": OCR_VERSION,
        "gpu_ocr_targets": len(targets),
        "gpu_ocr_recovered": recovered,
        "gpu_ocr_low_quality": low_quality,
        "gpu_ocr_failed": failed,
        "gpu_ocr_elapsed_seconds": round(time.time() - started, 2),
        "gpu_ocr_result_log": str(result_log),
        "gpu": torch.cuda.get_device_name(0),
    })
    pipeline.write_json(base / "summary.json", stats)

    print("\nGPU OCR 완료")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
