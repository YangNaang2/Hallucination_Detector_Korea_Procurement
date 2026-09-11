#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
과거 manifest.jsonl의 failed 캐시를 기존 raw/ 원본만 사용해 강제 재파싱한다.

중요:
- 나라장터 API를 호출하지 않는다.
- 첨부파일을 다시 다운로드하지 않는다.
- 현재 chunk_ready에 이미 들어간 document_id는 건너뛴다.
- parsed/<sha>.json의 과거 failed 캐시는 현재 파서로 덮어쓴다.
- 성공한 문서만 chunk_ready.jsonl에 추가한다.\n- OCR은 수행하지 않는다.
- 기존 quarantine.jsonl은 건드리지 않는다.
- 결과는 historical_failed_reparse.*.jsonl / historical_failed_unresolved.*.jsonl에 기록한다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import narajangteo_ingest as n
import quarantine_tool as q


def read_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                print(f"[WARN] {path.name}:{lineno} JSON 오류: {e}", file=sys.stderr)
                continue
            if isinstance(obj, dict):
                yield obj


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_raw(src: Path, row: dict[str, Any], document_id: str) -> Path | None:
    raw = str(row.get("raw_path") or "").strip()
    if raw:
        p = Path(raw)
        if p.exists() and p.is_file():
            return p

    # 절대경로가 달라졌거나 프로젝트를 이동한 경우 SHA 기반 raw cache에서 찾는다.
    raw_dir = src / "raw" / document_id[:2]
    if raw_dir.exists():
        matches = sorted(raw_dir.glob(f"{document_id}.*"))
        if matches:
            return matches[0]
    return None


def make_result_from_dict(d: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        status=d["status"],
        detected_format=d["detected_format"],
        parser=d["parser"],
        quality=float(d.get("quality") or 0.0),
        warnings=list(d.get("warnings") or []),
        text=d.get("text") or "",
        blocks=d.get("blocks") or [],
    )


def parse_local(parser: Any, data: bytes, filename: str, min_quality: float):
    # 1) .hwp로 잘못 명명된 실제 XLS를 먼저 감지
    xls = q._try_parse_ole_excel(data, filename, min_quality)
    if xls is not None:
        return make_result_from_dict(xls)

    # 2) 기존 현재 파서
    result = parser.parse(data, filename)

    # 3) OCR은 이번 패스에서는 사용하지 않는다.
    # 이미지 기반 PDF는 low_quality/failed로 남겨 두고,
    # 빠른 일반 파싱 복구가 끝난 뒤 별도 OCR 패스로 처리한다.
    return result


def main() -> int:
    ap = argparse.ArgumentParser(
        description="과거 manifest failed 문서를 API 없이 raw 원본에서 강제 재파싱"
    )
    ap.add_argument("--src", default="data/2026-04", help="월 데이터 폴더")
    ap.add_argument("--min-quality", type=float, default=0.55)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.dry_run and args.apply:
        ap.error("--dry-run과 --apply는 동시에 사용할 수 없습니다.")
    if not args.dry_run and not args.apply:
        ap.error("--dry-run 또는 --apply 중 하나를 지정하세요.")

    src = Path(args.src).expanduser().resolve()
    manifest = src / "manifest.jsonl"
    chunk_ready = src / "chunk_ready.jsonl"
    parsed_dir = src / "parsed"

    if not manifest.exists():
        print(f"[ERROR] manifest.jsonl 없음: {manifest}")
        return 2
    if not chunk_ready.exists():
        print(f"[ERROR] chunk_ready.jsonl 없음: {chunk_ready}")
        return 2
    if not parsed_dir.exists():
        print(f"[ERROR] parsed/ 없음: {parsed_dir}")
        return 2

    # 현재 chunk_ready document_id
    chunk_ids: set[str] = set()
    chunk_keys: set[tuple[str, str]] = set()
    for row in read_jsonl(chunk_ready):
        docid = str(row.get("document_id") or "")
        if docid:
            chunk_ids.add(docid)
        bid = row.get("bid") or {}
        att = row.get("attachment") or {}
        bid_key = str(bid.get("bid_key") or att.get("bid_key") or "")
        url = str(att.get("url") or "")
        if bid_key and url:
            chunk_keys.add((bid_key, url))

    # historical failed 중 document_id 기준 중복 제거
    failed_unique: dict[str, dict[str, Any]] = {}
    failed_rows = 0
    for row in read_jsonl(manifest):
        if row.get("status") != "failed":
            continue
        failed_rows += 1
        docid = str(row.get("document_id") or "").strip()
        if not docid:
            continue
        failed_unique.setdefault(docid, row)

    already_recovered = sum(1 for d in failed_unique if d in chunk_ids)
    targets = [(d, r) for d, r in failed_unique.items() if d not in chunk_ids]

    raw_found = 0
    raw_missing = 0
    for docid, row in targets:
        if resolve_raw(src, row, docid) is None:
            raw_missing += 1
        else:
            raw_found += 1

    print("=" * 68)
    print("Historical failed cache 재파싱 점검")
    print("=" * 68)
    print(f"데이터 폴더                  : {src}")
    print(f"과거 manifest failed 행      : {failed_rows:>10,}")
    print(f"과거 failed 고유 document_id : {len(failed_unique):>10,}")
    print(f"이미 chunk_ready에 복구됨    : {already_recovered:>10,}")
    print(f"이번 재파싱 대상             : {len(targets):>10,}")
    print(f"로컬 raw 확인                : {raw_found:>10,}")
    print(f"로컬 raw 없음                : {raw_missing:>10,}")
    print(f"현재 chunk_ready             : {len(chunk_ids):>10,}")
    print("API 호출                     : 안 함")
    print("첨부 재다운로드              : 안 함")
    print("=" * 68)

    if args.dry_run:
        print("\n[DRY-RUN] 아무 파일도 변경하지 않았습니다.")
        print("대상 수와 raw 확인 수가 맞으면 --apply로 실행하세요.")
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = src / f"chunk_ready.before_historical_reparse.{stamp}.jsonl"
    shutil.copy2(chunk_ready, backup)

    result_log = src / f"historical_failed_reparse.{stamp}.jsonl"
    unresolved_log = src / f"historical_failed_unresolved.{stamp}.jsonl"
    result_log.write_text("", encoding="utf-8")
    unresolved_log.write_text("", encoding="utf-8")

    parser = n.AttachmentParser(args.min_quality)

    recovered = 0
    unresolved = 0
    missing = 0
    sha_mismatch = 0
    skipped_dup = 0

    for idx, (document_id, row) in enumerate(targets, 1):
        if idx == 1 or idx % 100 == 0 or idx == len(targets):
            print(
                f"[{idx:>6,}/{len(targets):,}] "
                f"복구 {recovered:,} / 미해결 {unresolved:,} / raw없음 {missing:,}",
                flush=True,
            )

        raw_path = resolve_raw(src, row, document_id)
        bid = row.get("bid") or {}
        att = row.get("attachment") or {}
        filename = str(att.get("filename") or raw_path.name if raw_path else att.get("filename") or "unknown.bin")
        bid_key = str(bid.get("bid_key") or att.get("bid_key") or "")
        url = str(att.get("url") or "")

        if raw_path is None:
            missing += 1
            unresolved += 1
            out = {
                **row,
                "reparse_status": "raw_missing",
                "reason": "기존 raw 원본을 찾지 못해 재파싱하지 않음",
            }
            append_jsonl(result_log, out)
            append_jsonl(unresolved_log, out)
            continue

        try:
            data = raw_path.read_bytes()
        except Exception as e:
            unresolved += 1
            out = {
                **row,
                "reparse_status": "raw_read_failed",
                "error": f"{type(e).__name__}: {e}",
            }
            append_jsonl(result_log, out)
            append_jsonl(unresolved_log, out)
            continue

        actual_digest = sha256_bytes(data)
        if actual_digest != document_id:
            sha_mismatch += 1
            unresolved += 1
            out = {
                **row,
                "reparse_status": "sha_mismatch",
                "actual_sha256": actual_digest,
                "reason": "manifest document_id와 raw 파일 SHA-256 불일치",
            }
            append_jsonl(result_log, out)
            append_jsonl(unresolved_log, out)
            continue

        try:
            result = parse_local(parser, data, filename, args.min_quality)
        except Exception as e:
            unresolved += 1
            out = {
                **row,
                "reparse_status": "exception",
                "error": f"{type(e).__name__}: {e}",
            }
            append_jsonl(result_log, out)
            append_jsonl(unresolved_log, out)
            continue

        parsed_path = parsed_dir / f"{document_id}.json"
        document = {
            "document_id": document_id,
            "sha256": document_id,
            "source": {
                "url": url,
                "filename": filename,
                "attachment_source": att.get("source"),
                "raw_path": str(raw_path),
            },
            "bid": bid,
            "parse": {
                "status": result.status,
                "detected_format": result.detected_format,
                "parser": result.parser,
                "quality": round(float(result.quality or 0.0), 4),
                "warnings": list(result.warnings or []),
            },
            "text": result.text,
            "blocks": result.blocks,
            "reprocessed_from_historical_failed": True,
        }
        n.write_json(parsed_path, document)

        log_row = {
            "document_id": document_id,
            "bid": bid,
            "attachment": att,
            "raw_path": str(raw_path),
            "parsed_path": str(parsed_path),
            "status": result.status,
            "parser": result.parser,
            "quality": round(float(result.quality or 0.0), 4),
            "warnings": list(result.warnings or []),
        }

        if result.status == "parsed" and float(result.quality or 0.0) >= args.min_quality:
            # document_id 또는 같은 공고+URL이 이미 있으면 중복 추가하지 않음
            if document_id in chunk_ids or (bid_key and url and (bid_key, url) in chunk_keys):
                skipped_dup += 1
                log_row["reparse_status"] = "parsed_but_chunk_duplicate"
            else:
                chunk_row = {
                    "document_id": document_id,
                    "bid": bid,
                    "attachment": att,
                    "parsed_path": str(parsed_path),
                    "selection": {
                        "reason": "historical_failed_local_reparse",
                    },
                }
                append_jsonl(chunk_ready, chunk_row)
                chunk_ids.add(document_id)
                if bid_key and url:
                    chunk_keys.add((bid_key, url))
                recovered += 1
                log_row["reparse_status"] = "recovered"
        else:
            unresolved += 1
            log_row["reparse_status"] = "still_unresolved"
            append_jsonl(unresolved_log, log_row)

        append_jsonl(result_log, log_row)

    print()
    print("=" * 68)
    print("재파싱 완료")
    print("=" * 68)
    print(f"재파싱 대상       : {len(targets):>10,}")
    print(f"복구 성공         : {recovered:>10,}")
    print(f"여전히 미해결     : {unresolved:>10,}")
    print(f"raw 없음          : {missing:>10,}")
    print(f"SHA 불일치        : {sha_mismatch:>10,}")
    print(f"chunk 중복 skip   : {skipped_dup:>10,}")
    print(f"현재 chunk_ready  : {len(chunk_ids):>10,}")
    print("-" * 68)
    print(f"chunk_ready 백업  : {backup}")
    print(f"전체 결과 로그    : {result_log}")
    print(f"미해결 결과 로그  : {unresolved_log}")
    print("=" * 68)
    print()
    print("주의: 기존 quarantine.jsonl은 변경하지 않았습니다.")
    print("다음 단계에서 unresolved 로그와 기존 quarantine을 합쳐 최종 상태를 정리하면 됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
