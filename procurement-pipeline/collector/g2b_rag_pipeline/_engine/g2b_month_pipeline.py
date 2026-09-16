#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나라장터 완전 독립형 월 단위 수집/파싱 엔진 v4.

이 파일은 기존 narajangteo_rag_ingest 프로젝트를 import하지 않는다.
동일 ZIP에 포함된 g2b_core.py만 사용한다.

권장 처리 순서
1) fetch    : 월 전체 입찰공고 API 수집
2) download : 수집 완료된 공고의 첨부 raw 병렬 다운로드
3) parse    : raw를 CPU ProcessPool 병렬 파싱
4) 별도 g2b_gpu_ocr.py : CPU 파싱 후 남은 PDF만 GPU OCR

`all`은 위 1~3을 순서대로 실행한다. OCR은 절대 섞지 않는다.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

from dotenv import load_dotenv

import g2b_core as core


PIPELINE_VERSION = "g2b-oneclick-v4"
DEFAULT_PRIORITY = ["hwpx", "docx", "hwp", "pdf", "txt", "xls", "xlsx", "zip"]

DEFAULTS: dict[str, Any] = {
    "business_types": ["service", "goods", "construction", "foreign", "etc"],
    "keyword": None,
    "demand_org": None,
    "min_budget": None,
    "max_budget": None,
    "contract_method": None,
    "bid_name_contains": None,
    "notice_org_contains": None,
    "demand_org_contains": None,
    "unknown_budget": "keep",
    "doc_mode": "all",
    "eorder_fallback": False,
    "duplicate_format_priority": list(DEFAULT_PRIORITY),
    "page_size": 999,
    "api_concurrency": 4,
    "download_concurrency": 12,
    "workers": 8,
    "chunk_days": 15,
    "max_file_mb": 100,
    "min_quality": 0.55,
}

_WORKER_PARSER = None
_WORKER_MIN_QUALITY = 0.55


# ---------------------------------------------------------------------------
# Generic file helpers
# ---------------------------------------------------------------------------

def json_line(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)


def read_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                yield obj


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json_line(row) + "\n")
    temp.replace(path)


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json_line(obj) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    temp.replace(path)


def month_base(out: str | Path, year: int, month: int) -> Path:
    return Path(out).expanduser().resolve() / f"{year:04d}-{month:02d}"


def _show(value: Any, none: str = "(필터 없음)") -> str:
    if value is None or value == "" or value == [] or value == {}:
        return none
    if isinstance(value, list):
        return ", ".join(map(str, value))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


# ---------------------------------------------------------------------------
# Config / filter UX
# ---------------------------------------------------------------------------

def load_toml(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise SystemExit(f"설정 파일 없음: {p}")
    with p.open("rb") as f:
        return tomllib.load(f)


def cfg_value(cfg: dict[str, Any], section: str, key: str):
    sec = cfg.get(section)
    if isinstance(sec, dict) and key in sec:
        return sec[key]
    return None


def parse_key_value(items: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in items or []:
        if "=" not in raw:
            raise SystemExit(f"--api-param은 KEY=VALUE 형식이어야 합니다: {raw}")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"--api-param 키가 비어 있습니다: {raw}")
        out[key] = value.strip()
    return out


def resolve_settings(args: argparse.Namespace) -> argparse.Namespace:
    cfg = load_toml(getattr(args, "filter_config", None))

    mapping = {
        "business_types": ("scope", "business_types"),
        "keyword": ("api_filters", "keyword"),
        "demand_org": ("api_filters", "demand_org"),
        "min_budget": ("local_filters", "min_budget"),
        "max_budget": ("local_filters", "max_budget"),
        "contract_method": ("local_filters", "contract_method"),
        "bid_name_contains": ("local_filters", "bid_name_contains"),
        "notice_org_contains": ("local_filters", "notice_org_contains"),
        "demand_org_contains": ("local_filters", "demand_org_contains"),
        "unknown_budget": ("local_filters", "unknown_budget"),
        "doc_mode": ("attachment_filters", "doc_mode"),
        "eorder_fallback": ("attachment_filters", "eorder_fallback"),
        "duplicate_format_priority": ("attachment_filters", "duplicate_format_priority"),
        "page_size": ("performance", "page_size"),
        "api_concurrency": ("performance", "api_concurrency"),
        "download_concurrency": ("performance", "download_concurrency"),
        "workers": ("performance", "workers"),
        "chunk_days": ("performance", "chunk_days"),
        "max_file_mb": ("performance", "max_file_mb"),
        "min_quality": ("performance", "min_quality"),
    }

    for attr, (section, key) in mapping.items():
        if getattr(args, attr, None) is not None:
            continue
        value = cfg_value(cfg, section, key)
        setattr(args, attr, DEFAULTS[attr] if value is None else value)

    if isinstance(args.business_types, str):
        raw = args.business_types.strip()
        args.business_types = (
            list(DEFAULTS["business_types"])
            if raw.casefold() == "all"
            else [x.strip().lower() for x in raw.split(",") if x.strip()]
        )

    if isinstance(args.duplicate_format_priority, str):
        args.duplicate_format_priority = [
            x.strip().lower().lstrip(".")
            for x in args.duplicate_format_priority.split(",")
            if x.strip()
        ]
    for fmt in DEFAULT_PRIORITY:
        if fmt not in args.duplicate_format_priority:
            args.duplicate_format_priority.append(fmt)

    for attr in (
        "keyword", "demand_org", "contract_method",
        "bid_name_contains", "notice_org_contains", "demand_org_contains",
    ):
        value = getattr(args, attr, None)
        if isinstance(value, str) and not value.strip():
            setattr(args, attr, None)

    api_extra: dict[str, Any] = {}
    cfg_extra = cfg.get("api_extra_params")
    if isinstance(cfg_extra, dict):
        api_extra.update(cfg_extra)
    api_extra.update(parse_key_value(getattr(args, "api_param", None)))
    args.api_extra_params = api_extra

    if args.unknown_budget not in {"keep", "drop"}:
        raise SystemExit("unknown_budget는 keep 또는 drop 이어야 합니다.")

    unknown_types = [x for x in args.business_types if x not in core.ENDPOINTS]
    if unknown_types:
        raise SystemExit(
            f"지원하지 않는 business_types: {unknown_types}; "
            f"가능: {list(core.ENDPOINTS)}"
        )

    args.page_size = int(args.page_size)
    args.api_concurrency = int(args.api_concurrency)
    args.download_concurrency = int(args.download_concurrency)
    args.workers = int(args.workers)
    args.chunk_days = int(args.chunk_days)
    args.max_file_mb = int(args.max_file_mb)
    args.min_quality = float(args.min_quality)
    return args


def print_effective_settings(args: argparse.Namespace) -> None:
    print()
    print("=" * 80)
    print("나라장터 독립형 파이프라인 — 실제 적용 설정")
    print("=" * 80)
    print(f"대상 기간             : {args.year:04d}-{args.month:02d}")
    print(f"저장 위치             : {Path(args.out).expanduser().resolve()}")
    print()
    print("[A. API 조회 범위 / API 요청 단계]")
    print(f"  업무 유형 API       : {_show(args.business_types)}")
    print(f"  공고명 검색어       : {_show(args.keyword)}")
    print(f"  수요기관 검색값     : {_show(args.demand_org)}")
    print(f"  추가 API 파라미터   : {_show(args.api_extra_params)}")
    print(f"  날짜 청크(day)      : {args.chunk_days}")
    print(f"  페이지 크기         : {args.page_size}")
    print(f"  API 동시 요청       : {args.api_concurrency}")
    print()
    print("[B. API 응답 수집 후 로컬 공고 필터]")
    print(f"  최소 예산           : {_show(args.min_budget)}")
    print(f"  최대 예산           : {_show(args.max_budget)}")
    print(f"  계약방법 포함       : {_show(args.contract_method)}")
    print(f"  공고명 포함         : {_show(args.bid_name_contains)}")
    print(f"  공고기관 포함       : {_show(args.notice_org_contains)}")
    print(f"  수요기관 포함       : {_show(args.demand_org_contains)}")
    print(f"  예산 미확인 공고    : {args.unknown_budget}")
    print()
    print("[C. 첨부파일]")
    print(f"  첨부 모드           : {args.doc_mode}")
    print(f"  e발주 fallback      : {args.eorder_fallback}")
    print(f"  다중포맷 우선순위   : {_show(args.duplicate_format_priority)}")
    print()
    print("[D. 성능 / 파싱]")
    print(f"  다운로드 동시수     : {args.download_concurrency}")
    print(f"  CPU worker          : {args.workers}")
    print(f"  최소 파싱 품질      : {args.min_quality}")
    print(f"  최대 파일(MB)       : {args.max_file_mb}")
    print("  일반 파싱 OCR       : OFF")
    print("  GPU OCR             : 별도 g2b_gpu_ocr.py")
    print("=" * 80)
    print()


def save_effective_settings(base: Path, args: argparse.Namespace) -> None:
    write_json(base / "effective_settings.json", {
        "pipeline_version": PIPELINE_VERSION,
        "year": args.year,
        "month": args.month,
        "api": {
            "business_types": args.business_types,
            "keyword": args.keyword,
            "demand_org": args.demand_org,
            "extra_params": args.api_extra_params,
            "page_size": args.page_size,
            "api_concurrency": args.api_concurrency,
            "chunk_days": args.chunk_days,
        },
        "local_filters": {
            "min_budget": args.min_budget,
            "max_budget": args.max_budget,
            "contract_method": args.contract_method,
            "bid_name_contains": args.bid_name_contains,
            "notice_org_contains": args.notice_org_contains,
            "demand_org_contains": args.demand_org_contains,
            "unknown_budget": args.unknown_budget,
        },
        "attachments": {
            "doc_mode": args.doc_mode,
            "eorder_fallback": args.eorder_fallback,
            "duplicate_format_priority": args.duplicate_format_priority,
        },
        "performance": {
            "download_concurrency": args.download_concurrency,
            "workers": args.workers,
            "min_quality": args.min_quality,
            "max_file_mb": args.max_file_mb,
        },
    })


def load_api_key(required: bool = True) -> str:
    load_dotenv()
    key = (os.getenv("NARA_API_KEY") or "").strip()
    if not key:
        if required:
            raise SystemExit(
                "NARA_API_KEY가 없습니다. 이 독립형 프로젝트의 .env에 "
                "NARA_API_KEY=... 를 입력하세요."
            )
        return ""

    # Encoding 키(%2B 등)가 들어오면 1회 decode 후 httpx가 정상 인코딩하게 함.
    if re_percent_encoded(key):
        key = unquote(key)
    return key


def re_percent_encoded(value: str) -> bool:
    import re
    return bool(re.search(r"%[0-9A-Fa-f]{2}", value))


def make_core_settings(
    args: argparse.Namespace,
    *,
    require_api_key: bool,
    disable_local_filters: bool = False,
) -> core.Settings:
    return core.Settings(
        year=args.year,
        month=args.month,
        api_key=load_api_key(required=require_api_key),
        out_dir=Path(args.out).expanduser().resolve(),
        business_types=list(args.business_types),
        page_size=args.page_size,
        api_concurrency=max(1, args.api_concurrency),
        download_concurrency=max(1, args.download_concurrency),
        parse_concurrency=1,
        chunk_days=max(1, args.chunk_days),
        min_quality=max(0.0, min(1.0, args.min_quality)),
        max_file_bytes=args.max_file_mb * 1024 * 1024,
        keyword=args.keyword,
        demand_org=args.demand_org,
        min_budget=None if disable_local_filters else args.min_budget,
        max_budget=None if disable_local_filters else args.max_budget,
        contract_method=None if disable_local_filters else args.contract_method,
        doc_mode=args.doc_mode,
        skip_attachments=False,
        eorder_fallback=args.eorder_fallback,
        duplicate_format_priority=list(args.duplicate_format_priority),
        api_extra_params=dict(args.api_extra_params),
    )


# ---------------------------------------------------------------------------
# Local bid filters
# ---------------------------------------------------------------------------

def contains(value: Any, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.casefold() in str(value or "").casefold()


def apply_local_bid_filters(
    bids: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], Counter]:
    out: list[dict[str, Any]] = []
    dropped: Counter = Counter()

    for item in bids:
        meta = core.selected_bid_metadata(item)
        budget = meta.get("budget")

        if args.min_budget is not None:
            if budget is None:
                if args.unknown_budget == "drop":
                    dropped["budget_unknown"] += 1
                    continue
            elif budget < args.min_budget:
                dropped["below_min_budget"] += 1
                continue

        if args.max_budget is not None:
            if budget is None:
                if args.unknown_budget == "drop":
                    dropped["budget_unknown"] += 1
                    continue
            elif budget > args.max_budget:
                dropped["above_max_budget"] += 1
                continue

        if not contains(meta.get("contract_method"), args.contract_method):
            dropped["contract_method"] += 1
            continue

        if not contains(meta.get("bid_name"), args.bid_name_contains):
            dropped["bid_name"] += 1
            continue

        if not contains(meta.get("notice_org"), args.notice_org_contains):
            dropped["notice_org"] += 1
            continue

        if not contains(meta.get("demand_org"), args.demand_org_contains):
            dropped["demand_org"] += 1
            continue

        out.append(item)

    return out, dropped


# ---------------------------------------------------------------------------
# Phase 1: fetch every notice first
# ---------------------------------------------------------------------------

async def phase_fetch(args: argparse.Namespace) -> dict[str, Any]:
    base = month_base(args.out, args.year, args.month)
    base.mkdir(parents=True, exist_ok=True)
    save_effective_settings(base, args)

    # API 단계에서는 로컬 예산/계약 필터를 끈다.
    # keyword/demand_org/api_extra_params만 API 요청에 사용된다.
    settings = make_core_settings(
        args,
        require_api_key=True,
        disable_local_filters=True,
    )
    client = core.G2BClient(settings)
    started = time.time()

    try:
        print("[1] 월 전체 입찰공고 API 수집 시작")
        api_bids = await client.collect_bids()
    finally:
        await client.close()

    # API 검색 결과 원문(업무유형 등의 내부 provenance 필드만 추가된 상태)
    write_jsonl(base / "bids_api.jsonl", api_bids)

    bids, dropped = apply_local_bid_filters(api_bids, args)
    write_jsonl(base / "bids.jsonl", bids)

    stats = {
        "pipeline_version": PIPELINE_VERSION,
        "year": args.year,
        "month": args.month,
        "api_bids": len(api_bids),
        "bids_after_local_filters": len(bids),
        "local_filter_dropped": dict(dropped),
        "api_business_types": args.business_types,
        "api_keyword": args.keyword,
        "api_demand_org": args.demand_org,
        "api_extra_params": args.api_extra_params,
        "elapsed_seconds": round(time.time() - started, 2),
        "attachments_downloaded": False,
        "parsed": False,
    }
    write_json(base / "fetch_summary.json", stats)

    print(
        f"API 공고 수집 완료: {len(api_bids):,}건 → "
        f"로컬 필터 후 {len(bids):,}건"
    )
    print("이 단계에서는 첨부 다운로드/파싱을 하지 않았습니다.")
    return stats


# ---------------------------------------------------------------------------
# Phase 2: make inventory then download every raw attachment
# ---------------------------------------------------------------------------

def format_rank(fmt: str, priority: list[str]) -> int:
    try:
        return priority.index(fmt)
    except ValueError:
        return len(priority) + 10


def make_inventory_rows(
    refs_with_items: list[tuple[core.AttachmentRef, dict[str, Any]]],
    priority: list[str],
) -> list[dict[str, Any]]:
    # 같은 공고 안의 같은 URL 중복 제거
    unique: dict[str, tuple[core.AttachmentRef, dict[str, Any]]] = {}
    order: list[str] = []

    for ref, item in refs_with_items:
        key = f"{ref.bid_key}|{ref.url}"
        if key not in unique:
            unique[key] = (ref, item)
            order.append(key)

    pairs = [unique[k] for k in order]

    # 같은 공고 + canonical stem으로 다중포맷 후보 그룹화
    buckets: dict[str, list[int]] = defaultdict(list)
    formats: dict[int, str] = {}
    stems: dict[int, str] = {}

    for idx, (ref, _) in enumerate(pairs):
        stem = core.canonical_attachment_stem(ref.filename)
        fmt = core.attachment_format(ref.filename, ref.url)
        stems[idx] = stem
        formats[idx] = fmt
        buckets[f"{ref.bid_key}|{stem}"].append(idx)

    group_by_idx: dict[int, str] = {}
    multi_format_groups = 0

    for bucket_key, indexes in buckets.items():
        fmts = {formats[i] for i in indexes}
        if len(indexes) > 1 and len(fmts) > 1:
            multi_format_groups += 1
            gid = f"multi|{bucket_key}"
            for i in indexes:
                group_by_idx[i] = gid
        else:
            # 같은 포맷/같은 stem은 다른 문서일 가능성이 있어 별도 처리
            for i in indexes:
                ref, _ = pairs[i]
                group_by_idx[i] = (
                    f"single|{ref.bid_key}|"
                    f"{hashlib.sha1(ref.url.encode('utf-8')).hexdigest()[:16]}"
                )

    rows = []
    for idx, (ref, item) in enumerate(pairs):
        fmt = formats[idx]
        rows.append({
            "inventory_index": idx,
            "selection_group": group_by_idx[idx],
            "group_name": stems[idx],
            "format": fmt,
            "format_rank": format_rank(fmt, priority),
            "bid": core.selected_bid_metadata(item),
            "attachment": asdict(ref),
        })

    print(
        f"첨부 inventory: {len(rows):,}개 / "
        f"다중 포맷 그룹: {multi_format_groups:,}개"
    )
    return rows


async def phase_download(args: argparse.Namespace) -> dict[str, Any]:
    base = month_base(args.out, args.year, args.month)
    bids_path = base / "bids.jsonl"
    if not bids_path.exists():
        raise SystemExit(
            f"{bids_path} 없음. 먼저 fetch를 실행하세요."
        )

    bids = list(read_jsonl(bids_path))
    raw_dir = base / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    settings = make_core_settings(
        args,
        require_api_key=bool(args.eorder_fallback),
        disable_local_filters=True,
    )
    client = core.G2BClient(settings)
    started = time.time()

    try:
        refs_with_items: list[tuple[core.AttachmentRef, dict[str, Any]]] = []
        eorder_candidates: list[dict[str, Any]] = []

        for item in bids:
            refs = client.attachments_from_notice(item, args.doc_mode)
            if refs:
                refs_with_items.extend((ref, item) for ref in refs)
            elif args.eorder_fallback:
                eorder_candidates.append(item)

        # e발주 API는 "모든 공고 API fetch가 끝난 뒤" 여기서만 선택적으로 호출.
        if eorder_candidates:
            print(f"e발주 fallback 조회: {len(eorder_candidates):,}개 공고")
            results = await asyncio.gather(
                *(client.eorder_attachments(item) for item in eorder_candidates),
                return_exceptions=True,
            )
            for item, result in zip(eorder_candidates, results):
                if isinstance(result, Exception):
                    append_jsonl(base / "download_errors.jsonl", {
                        "status": "eorder_lookup_failed",
                        "bid": core.selected_bid_metadata(item),
                        "error": f"{type(result).__name__}: {result}",
                    })
                    continue
                refs_with_items.extend((ref, item) for ref in result)

        inventory = make_inventory_rows(
            refs_with_items,
            list(args.duplicate_format_priority),
        )
        write_jsonl(base / "attachment_inventory.jsonl", inventory)

        # 이전 성공 다운로드를 current inventory 키 기준으로 재사용.
        prior: dict[str, dict[str, Any]] = {}
        for path in (
            base / "download_manifest.jsonl",
            base / "download_manifest.jsonl.part",
        ):
            for row in read_jsonl(path):
                att = row.get("attachment") or {}
                key = f"{att.get('bid_key','')}|{att.get('url','')}"
                raw_path = Path(str(row.get("raw_path") or ""))
                if (
                    row.get("download_status") == "downloaded"
                    and row.get("document_id")
                    and raw_path.exists()
                ):
                    prior[key] = row

        part = base / "download_manifest.jsonl.part"
        if part.exists():
            part.unlink()

        async def download_one(inv: dict[str, Any]) -> dict[str, Any]:
            att = inv.get("attachment") or {}
            key = f"{att.get('bid_key','')}|{att.get('url','')}"
            cached = prior.get(key)

            if cached:
                return {
                    **inv,
                    "download_status": "downloaded",
                    "document_id": cached.get("document_id"),
                    "raw_path": cached.get("raw_path"),
                    "bytes": cached.get("bytes"),
                    "detected_format": cached.get("detected_format"),
                    "download_cached": True,
                }

            ref = core.AttachmentRef(**att)
            try:
                data = await client.download(ref)
                digest = core.sha256_bytes(data)
                filename = core.safe_filename(ref.filename)
                detected = core.sniff_format(data, filename)

                suffix = Path(filename).suffix.lower()
                if suffix not in core.SUPPORTED_EXTENSIONS:
                    suffix = (
                        f".{detected}"
                        if detected in {
                            "hwp", "hwpx", "pdf", "docx",
                            "xls", "xlsx", "zip", "txt",
                        }
                        else ".bin"
                    )

                raw_path = raw_dir / digest[:2] / f"{digest}{suffix}"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                if not raw_path.exists():
                    raw_path.write_bytes(data)

                return {
                    **inv,
                    "download_status": "downloaded",
                    "document_id": digest,
                    "raw_path": str(raw_path),
                    "bytes": len(data),
                    "detected_format": detected,
                    "download_cached": False,
                }
            except Exception as e:
                return {
                    **inv,
                    "download_status": "failed",
                    "error": f"{type(e).__name__}: {e}",
                }

        total = len(inventory)
        done = success = failed = 0
        batch_size = max(100, args.download_concurrency * 20)

        print(
            f"첨부 raw 다운로드 시작: {total:,}개 "
            f"(동시수={args.download_concurrency})"
        )

        for start in range(0, total, batch_size):
            batch = inventory[start:start + batch_size]
            results = await asyncio.gather(*(download_one(x) for x in batch))
            for row in results:
                append_jsonl(part, row)
                done += 1
                if row.get("download_status") == "downloaded":
                    success += 1
                else:
                    failed += 1
            print(
                f"[download] {done:,}/{total:,} "
                f"성공 {success:,} / 실패 {failed:,}",
                flush=True,
            )

        final = base / "download_manifest.jsonl"
        if part.exists():
            part.replace(final)
        elif total == 0:
            final.write_text("", encoding="utf-8")

        stats = {
            "pipeline_version": PIPELINE_VERSION,
            "bids": len(bids),
            "attachments_discovered": total,
            "downloads_success": success,
            "downloads_failed": failed,
            "elapsed_seconds": round(time.time() - started, 2),
            "parsing_performed": False,
        }
        write_json(base / "download_summary.json", stats)
        print("raw 다운로드 완료. 아직 CPU 파싱은 하지 않았습니다.")
        return stats

    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Phase 3: CPU multiprocessing parse
# ---------------------------------------------------------------------------

def worker_init(min_quality: float) -> None:
    global _WORKER_PARSER, _WORKER_MIN_QUALITY
    _WORKER_MIN_QUALITY = min_quality
    _WORKER_PARSER = core.AttachmentParser(min_quality)


def parse_worker(task):
    docid, raw_path_s, filename, bid, attachment, parsed_dir_s = task
    raw_path = Path(raw_path_s)
    parsed_dir = Path(parsed_dir_s)

    try:
        data = raw_path.read_bytes()
    except Exception as e:
        return {
            "document_id": docid,
            "status": "failed",
            "error": f"raw_read: {type(e).__name__}: {e}",
        }

    if core.sha256_bytes(data) != docid:
        return {
            "document_id": docid,
            "status": "failed",
            "error": "SHA-256 mismatch",
        }

    try:
        result = _WORKER_PARSER.parse(data, filename)
    except Exception as e:
        result = core.ParseResult(
            "failed", core.sniff_format(data, filename),
            "worker_exception", 0.0, "",
            warnings=[f"{type(e).__name__}: {e}"],
        )

    parsed_path = parsed_dir / f"{docid}.json"
    document = {
        "document_id": docid,
        "sha256": docid,
        "source": {
            "url": attachment.get("url"),
            "filename": filename,
            "attachment_source": attachment.get("source"),
            "raw_path": str(raw_path),
        },
        "bid": bid,
        "parse": {
            "status": result.status,
            "detected_format": result.detected_format,
            "parser": result.parser,
            "quality": round(float(result.quality or 0.0), 4),
            "warnings": list(result.warnings or []),
            "pipeline_version": PIPELINE_VERSION,
            "ocr_used": False,
        },
        "text": result.text,
        "blocks": result.blocks,
    }
    core.write_json(parsed_path, document)

    return {
        "document_id": docid,
        "status": result.status,
        "quality": round(float(result.quality or 0.0), 4),
        "parser": result.parser,
        "detected_format": result.detected_format,
        "parsed_path": str(parsed_path),
        "warnings": list(result.warnings or []),
    }


def load_parse_info(parsed_path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(parsed_path.read_text(encoding="utf-8"))
        p = doc.get("parse") or {}
        return {
            "status": str(p.get("status") or "failed"),
            "quality": float(p.get("quality") or 0.0),
            "parser": p.get("parser"),
            "warnings": list(p.get("warnings") or []),
            "detected_format": p.get("detected_format"),
            "parsed_path": str(parsed_path),
            "text_length": len(doc.get("text") or ""),
            "ocr_used": bool(p.get("ocr_used")),
        }
    except Exception as e:
        return {
            "status": "failed",
            "quality": 0.0,
            "parser": None,
            "warnings": [f"parsed JSON read failed: {e}"],
            "detected_format": None,
            "parsed_path": str(parsed_path),
            "text_length": 0,
            "ocr_used": False,
        }


def rebuild_indexes(
    base: Path,
    min_quality: float,
    priority: list[str],
) -> dict[str, Any]:
    download_manifest = base / "download_manifest.jsonl"
    if not download_manifest.exists():
        raise SystemExit(f"없음: {download_manifest}")

    rows = list(read_jsonl(download_manifest))
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        gid = str(
            row.get("selection_group")
            or f"single-unknown|{row.get('inventory_index')}"
        )
        groups[gid].append(row)

    manifest_rows: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []
    chunk_rows: list[dict[str, Any]] = []
    counts: Counter = Counter()

    for gid, candidates in groups.items():
        candidates = sorted(
            candidates,
            key=lambda r: (
                int(r.get("format_rank", 9999)),
                str((r.get("attachment") or {}).get("filename") or "").casefold(),
            ),
        )

        attempts: list[dict[str, Any]] = []

        for row in candidates:
            if row.get("download_status") != "downloaded":
                info = {
                    "status": "download_failed",
                    "quality": 0.0,
                    "parser": None,
                    "warnings": [str(row.get("error") or "download failed")],
                    "detected_format": row.get("detected_format"),
                    "parsed_path": None,
                    "text_length": 0,
                    "ocr_used": False,
                }
            else:
                docid = str(row.get("document_id") or "")
                path = base / "parsed" / f"{docid}.json"
                info = (
                    load_parse_info(path)
                    if path.exists()
                    else {
                        "status": "failed",
                        "quality": 0.0,
                        "parser": None,
                        "warnings": ["parsed JSON 없음"],
                        "detected_format": row.get("detected_format"),
                        "parsed_path": str(path),
                        "text_length": 0,
                        "ocr_used": False,
                    }
                )

            attempts.append({
                "inventory_index": row.get("inventory_index"),
                "document_id": row.get("document_id"),
                "filename": (row.get("attachment") or {}).get("filename"),
                "declared_format": row.get("format"),
                "raw_path": row.get("raw_path"),
                **info,
            })

        selected_idx = None
        for idx, attempt in enumerate(attempts):
            if (
                attempt.get("status") == "parsed"
                and float(attempt.get("quality") or 0.0) >= min_quality
            ):
                selected_idx = idx
                break

        if selected_idx is not None:
            selected = candidates[selected_idx]
            selected_attempt = attempts[selected_idx]
            counts["parsed_groups"] += 1

            selection = {
                "reason": (
                    "same_name_multi_format_best_available"
                    if len(candidates) > 1
                    else "single_attachment"
                ),
                "group_name": selected.get("group_name"),
                "group_size": len(candidates),
                "priority": priority,
                "selected_declared_format": selected.get("format"),
                "selected_detected_format": selected_attempt.get("detected_format"),
                "selected_filename": (
                    selected.get("attachment") or {}
                ).get("filename"),
                "candidate_attempts": attempts,
            }

            chunk_rows.append({
                "document_id": selected.get("document_id"),
                "bid": selected.get("bid"),
                "attachment": selected.get("attachment"),
                "parsed_path": selected_attempt.get("parsed_path"),
                "selection": selection,
            })

            for idx, (row, attempt) in enumerate(zip(candidates, attempts)):
                manifest_rows.append({
                    "status": attempt.get("status"),
                    "quality": attempt.get("quality"),
                    "parser": attempt.get("parser"),
                    "warnings": attempt.get("warnings"),
                    "document_id": row.get("document_id"),
                    "bid": row.get("bid"),
                    "attachment": row.get("attachment"),
                    "raw_path": row.get("raw_path"),
                    "parsed_path": attempt.get("parsed_path"),
                    "download_status": row.get("download_status"),
                    "selection_group": gid,
                    "selection_role": (
                        "selected"
                        if idx == selected_idx
                        else "not_selected_duplicate"
                    ),
                })
        else:
            statuses = [str(a.get("status") or "failed") for a in attempts]
            if "low_quality" in statuses:
                final_status = "low_quality"
            elif "unsupported" in statuses:
                final_status = "unsupported"
            elif statuses and all(x == "download_failed" for x in statuses):
                final_status = "download_failed"
            else:
                final_status = "failed"

            counts[f"unresolved_{final_status}"] += 1

            quarantine_rows.append({
                "status": final_status,
                "selection_group": gid,
                "group_name": candidates[0].get("group_name") if candidates else None,
                "bid": candidates[0].get("bid") if candidates else None,
                "candidates": [
                    {
                        "document_id": row.get("document_id"),
                        "attachment": row.get("attachment"),
                        "raw_path": row.get("raw_path"),
                        "declared_format": row.get("format"),
                        "download_status": row.get("download_status"),
                    }
                    for row in candidates
                ],
                "candidate_attempts": attempts,
                "reason": (
                    "모든 후보가 실패/저품질/미지원/다운로드 실패. "
                    "PDF는 별도 GPU OCR 후보가 될 수 있음."
                ),
            })

            for row, attempt in zip(candidates, attempts):
                manifest_rows.append({
                    "status": attempt.get("status"),
                    "quality": attempt.get("quality"),
                    "parser": attempt.get("parser"),
                    "warnings": attempt.get("warnings"),
                    "document_id": row.get("document_id"),
                    "bid": row.get("bid"),
                    "attachment": row.get("attachment"),
                    "raw_path": row.get("raw_path"),
                    "parsed_path": attempt.get("parsed_path"),
                    "download_status": row.get("download_status"),
                    "selection_group": gid,
                    "selection_role": "unresolved",
                })

    write_jsonl(base / "manifest.jsonl", manifest_rows)
    write_jsonl(base / "quarantine.jsonl", quarantine_rows)
    write_jsonl(base / "chunk_ready.jsonl", chunk_rows)

    bids = sum(1 for _ in read_jsonl(base / "bids.jsonl"))
    success_downloads = sum(
        1 for row in rows
        if row.get("download_status") == "downloaded"
    )

    stats = {
        "pipeline_version": PIPELINE_VERSION,
        "bids": bids,
        "attachment_rows": len(rows),
        "download_success_rows": success_downloads,
        "download_failed_rows": len(rows) - success_downloads,
        "attachment_groups": len(groups),
        "chunk_ready_rows": len(chunk_rows),
        "quarantine_groups": len(quarantine_rows),
        "current_counts": dict(counts),
        "min_quality": min_quality,
        "source_of_truth": "current parsed cache + current download_manifest",
    }
    write_json(base / "summary.json", stats)
    return stats


def phase_parse(args: argparse.Namespace) -> dict[str, Any]:
    base = month_base(args.out, args.year, args.month)
    download_manifest = base / "download_manifest.jsonl"
    if not download_manifest.exists():
        raise SystemExit(
            f"{download_manifest} 없음. 먼저 download를 실행하세요."
        )

    parsed_dir = base / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    downloaded = [
        row for row in read_jsonl(download_manifest)
        if row.get("download_status") == "downloaded"
        and row.get("document_id")
    ]

    # 같은 SHA 원본은 1회만 실제 파싱.
    unique_docs: dict[str, dict[str, Any]] = {}
    for row in downloaded:
        unique_docs.setdefault(str(row["document_id"]), row)

    tasks = []
    success_cache = 0
    stale_non_success = 0
    raw_missing = 0

    for docid, row in unique_docs.items():
        parsed_path = parsed_dir / f"{docid}.json"

        if parsed_path.exists() and not args.force_all:
            info = load_parse_info(parsed_path)
            # 핵심 버그 방지: 정상 성공 결과만 캐시로 인정.
            if (
                info.get("status") == "parsed"
                and float(info.get("quality") or 0.0) >= args.min_quality
            ):
                success_cache += 1
                continue
            stale_non_success += 1

        raw_path = Path(str(row.get("raw_path") or ""))
        if not raw_path.exists():
            raw_missing += 1
            continue

        attachment = row.get("attachment") or {}
        tasks.append((
            docid,
            str(raw_path),
            str(attachment.get("filename") or raw_path.name),
            row.get("bid") or {},
            attachment,
            str(parsed_dir),
        ))

    print("=" * 80)
    print("CPU 병렬 파싱")
    print("=" * 80)
    print(f"다운로드된 첨부 행       : {len(downloaded):>10,}")
    print(f"고유 document_id         : {len(unique_docs):>10,}")
    print(f"성공 캐시 재사용         : {success_cache:>10,}")
    print(f"실패/저품질 캐시 재시도  : {stale_non_success:>10,}")
    print(f"raw 없음                 : {raw_missing:>10,}")
    print(f"이번 파싱 작업           : {len(tasks):>10,}")
    print(f"workers                   : {args.workers:>10,}")
    print("HWP                       : HWPLoader -> olefile -> hwp5txt(extra)")
    print("legacy XLS                : OLE Workbook/Book -> xlrd")
    print("OCR                       : OFF")
    print("API 호출                  : OFF")
    print("첨부 재다운로드           : OFF")
    print("=" * 80)

    started = time.time()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    result_log = base / f"parse_results.{stamp}.jsonl"
    result_log.write_text("", encoding="utf-8")

    done = 0
    statuses: Counter = Counter()

    if tasks:
        try:
            with ProcessPoolExecutor(
                max_workers=args.workers,
                initializer=worker_init,
                initargs=(args.min_quality,),
            ) as executor:
                futures = {
                    executor.submit(parse_worker, task): task[0]
                    for task in tasks
                }

                for future in as_completed(futures):
                    docid = futures[future]
                    done += 1
                    try:
                        result = future.result()
                    except Exception as e:
                        result = {
                            "document_id": docid,
                            "status": "failed",
                            "error": (
                                f"worker_crash: {type(e).__name__}: {e}"
                            ),
                        }

                    statuses[str(result.get("status") or "failed")] += 1
                    append_jsonl(result_log, result)

                    if done == 1 or done % 200 == 0 or done == len(tasks):
                        elapsed = max(time.time() - started, 0.001)
                        rate = done / elapsed
                        remain = (
                            (len(tasks) - done) / rate if rate else 0
                        )
                        print(
                            f"[parse] {done:>7,}/{len(tasks):,} "
                            f"parsed {statuses.get('parsed',0):,} / "
                            f"low {statuses.get('low_quality',0):,} / "
                            f"failed {statuses.get('failed',0):,} / "
                            f"{rate:.2f} docs/s / "
                            f"예상잔여 {remain/60:.1f}분",
                            flush=True,
                        )
        except KeyboardInterrupt:
            print("\n중단됨. 이미 저장된 parsed 성공 결과는 유지됩니다.")
            print("같은 명령 재실행 시 성공 캐시를 자동 skip합니다.")
            raise

    stats = rebuild_indexes(
        base,
        args.min_quality,
        list(args.duplicate_format_priority),
    )
    stats.update({
        "parse_workers": args.workers,
        "parse_tasks_this_run": len(tasks),
        "success_cache_reused": success_cache,
        "non_success_cache_retried": stale_non_success,
        "parse_statuses_this_run": dict(statuses),
        "parse_elapsed_seconds": round(time.time() - started, 2),
        "parse_result_log": str(result_log),
        "ocr_performed": False,
    })
    write_json(base / "summary.json", stats)

    print("\nCPU 파싱 완료")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

HELP = """
필터 구분
=========
[A] API 단계
  --business-types
  --keyword
  --demand-org
  --api-param KEY=VALUE   (공공데이터포털 PPSSrch 추가 파라미터)

[B] 로컬 단계
  --min-budget / --max-budget
  --contract-method
  --bid-name-contains
  --notice-org-contains
  --demand-org-contains

[C] 첨부 단계
  --doc-mode all|relevant
  --eorder-fallback
  --duplicate-format-priority

권장:
  filter_config.example.toml을 filter_config.toml로 복사해서 수정.
  실행 전 show-settings로 최종 적용값 확인.
"""


def add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--year", type=int, required=True, help="조회 연도")
    p.add_argument(
        "--month", type=int, required=True, choices=range(1, 13),
        help="조회 월 1~12"
    )
    p.add_argument("--out", default="./data", help="월 데이터 상위 폴더")
    p.add_argument(
        "--filter-config",
        default=None,
        help="예: filter_config.toml",
    )

    p.add_argument(
        "--business-types",
        default=None,
        help="service,goods,construction,foreign,etc 또는 all",
    )
    p.add_argument(
        "--keyword",
        default=None,
        help="[API] 공고명 검색어(bidNtceNm)",
    )
    p.add_argument(
        "--demand-org",
        default=None,
        help="[API] 수요기관명 검색값(dminsttNm)",
    )
    p.add_argument(
        "--api-param",
        action="append",
        default=None,
        help="[API] 추가 PPSSrch 파라미터 KEY=VALUE; 여러 번 사용 가능",
    )

    p.add_argument(
        "--min-budget", type=int, default=None,
        help="[로컬] 최소 예산/추정가격"
    )
    p.add_argument(
        "--max-budget", type=int, default=None,
        help="[로컬] 최대 예산/추정가격"
    )
    p.add_argument(
        "--contract-method", default=None,
        help="[로컬] 계약방법 문자열 포함"
    )
    p.add_argument(
        "--bid-name-contains", default=None,
        help="[로컬] 공고명 문자열 포함"
    )
    p.add_argument(
        "--notice-org-contains", default=None,
        help="[로컬] 공고기관 문자열 포함"
    )
    p.add_argument(
        "--demand-org-contains", default=None,
        help="[로컬] 수요기관 문자열 포함"
    )
    p.add_argument(
        "--unknown-budget",
        choices=("keep", "drop"),
        default=None,
        help="예산 필터 사용 시 예산 미확인 공고 유지/제외"
    )

    p.add_argument(
        "--doc-mode",
        choices=("all", "relevant"),
        default=None,
        help="첨부 전체 또는 관련 문서명만"
    )
    p.add_argument(
        "--eorder-fallback",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="직접 첨부가 없을 때 e발주 첨부 API 추가 조회"
    )
    p.add_argument(
        "--duplicate-format-priority",
        default=None,
        help="예: hwpx,docx,hwp,pdf,txt,xls,xlsx,zip"
    )

    p.add_argument("--page-size", type=int, default=None)
    p.add_argument("--api-concurrency", type=int, default=None)
    p.add_argument("--download-concurrency", type=int, default=None)
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--chunk-days", type=int, default=None)
    p.add_argument("--max-file-mb", type=int, default=None)
    p.add_argument("--min-quality", type=float, default=None)


def build_cli() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="나라장터 독립형 월 수집/CPU 파싱",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=HELP,
    )
    sub = ap.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("show-settings", "API 호출 없이 최종 설정 확인"),
        ("fetch", "월 전체 공고 API만 먼저 수집"),
        ("download", "bids.jsonl의 첨부 raw만 다운로드"),
        ("collect", "fetch 후 download까지 실행(파싱 안 함)"),
        ("parse", "기존 raw를 CPU 병렬 파싱"),
        ("all", "fetch -> download -> parse 순차 실행"),
        ("rebuild", "현재 parsed에서 인덱스만 재생성"),
        ("status", "현재 월 상태 확인"),
    ):
        sp = sub.add_parser(
            name,
            help=help_text,
            formatter_class=argparse.RawTextHelpFormatter,
        )
        add_common_args(sp)
        if name in {"parse", "all"}:
            sp.add_argument(
                "--force-all",
                action="store_true",
                help="성공 parsed 캐시까지 전부 재파싱",
            )

    return ap


def status(args: argparse.Namespace) -> None:
    base = month_base(args.out, args.year, args.month)
    print(f"데이터 폴더: {base}")

    for name in (
        "bids_api.jsonl",
        "bids.jsonl",
        "attachment_inventory.jsonl",
        "download_manifest.jsonl",
        "manifest.jsonl",
        "chunk_ready.jsonl",
        "quarantine.jsonl",
    ):
        path = base / name
        count = sum(1 for _ in read_jsonl(path)) if path.exists() else 0
        print(f"{name:30s} {count:>12,}")

    summary = base / "summary.json"
    if summary.exists():
        print("\nsummary.json")
        print(summary.read_text(encoding="utf-8"))


def main() -> None:
    parser = build_cli()
    args = resolve_settings(parser.parse_args())
    print_effective_settings(args)

    if args.command == "show-settings":
        return

    if args.command == "fetch":
        asyncio.run(phase_fetch(args))
        return

    if args.command == "download":
        asyncio.run(phase_download(args))
        return

    if args.command == "collect":
        asyncio.run(phase_fetch(args))
        asyncio.run(phase_download(args))
        return

    if args.command == "parse":
        phase_parse(args)
        return

    if args.command == "all":
        asyncio.run(phase_fetch(args))
        asyncio.run(phase_download(args))
        phase_parse(args)
        return

    if args.command == "rebuild":
        base = month_base(args.out, args.year, args.month)
        stats = rebuild_indexes(
            base,
            args.min_quality,
            list(args.duplicate_format_priority),
        )
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return

    if args.command == "status":
        status(args)
        return


if __name__ == "__main__":
    main()
