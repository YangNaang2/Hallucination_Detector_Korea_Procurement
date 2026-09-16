#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나라장터 독립형 공고 API/첨부/파서 코어

목적
- 지정 연/월의 나라장터 입찰공고를 업무구분별로 전체 페이지 수집
- 첨부파일 원본을 SHA-256 기반으로 보존
- HWP: HWPLoader -> hwp5txt(pyhwp) -> OLE recovery 순으로 폴백
- HWPX/PDF/DOCX/XLSX/ZIP 파싱
- 성공 결과는 청킹 직전 IR(JSON)로 저장, 실패는 quarantine에 기록

주의
- 공공데이터포털에서 "조달청_나라장터 입찰공고정보서비스" 활용신청 필요
- NARA_API_KEY는 Encoding/Decoding 서비스키 모두 지원 (Encoding 키는 시작 시 1회 자동 decode)
"""

from __future__ import annotations

import argparse
import asyncio
import calendar
import hashlib
import io
import json
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
import zipfile
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as StdET

import httpx
from dotenv import load_dotenv

try:
    import olefile
except ImportError:
    olefile = None

try:
    from langchain_teddynote.document_loaders import HWPLoader
except ImportError:
    HWPLoader = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document as DocxDocument
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph as DocxParagraph
except ImportError:
    DocxDocument = None
    DocxTable = None
    DocxParagraph = None

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None

try:
    import xlrd
except ImportError:
    xlrd = None

try:
    from lxml import etree
except ImportError:
    etree = None


# =============================================================================
# ★ 팀에서 가장 자주 바꿀 기본값
# CLI 인자가 있으면 CLI 값이 우선합니다.
# =============================================================================
DEFAULT_YEAR = 2026          # ← 다른 연도: --year 2025
DEFAULT_MONTH = 5            # ← 다른 월:   --month 6
DEFAULT_BUSINESS_TYPES = "service,goods,construction,foreign,etc"
DEFAULT_PAGE_SIZE = 999      # API 호출 수 최소화. 문제가 있으면 --page-size 500/100
DEFAULT_API_CONCURRENCY = 4  # 너무 높이면 공공데이터포털 제한에 걸릴 수 있음
DEFAULT_DOWNLOAD_CONCURRENCY = 8
DEFAULT_PARSE_CONCURRENCY = 4
DEFAULT_CHUNK_DAYS = 15      # 참고 저장소의 장기간 조회 우회 방식 준용
DEFAULT_MIN_QUALITY = 0.55
DEFAULT_MAX_FILE_MB = 100
# 같은 문서가 HWP/HWPX/PDF/DOCX 등 여러 포맷으로 함께 올라온 경우,
# 청킹용 구조 보존력을 우선하여 아래 순서로 한 개만 선택합니다.
# 선택 파일이 low_quality/failed이면 다음 포맷으로 자동 fallback 합니다.
DEFAULT_DUPLICATE_FORMAT_PRIORITY = "hwpx,docx,hwp,pdf,txt,xlsx,zip"
# =============================================================================

BASE_URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
EORDER_ENDPOINT = "getBidPblancListInfoEorderAtchFileInfo"

ENDPOINTS: dict[str, str] = {
    "service": "getBidPblancListInfoServcPPSSrch",
    "goods": "getBidPblancListInfoThngPPSSrch",
    "construction": "getBidPblancListInfoCnstwkPPSSrch",
    "foreign": "getBidPblancListInfoFrgcptPPSSrch",
    "etc": "getBidPblancListInfoEtcPPSSrch",
}

BUSINESS_LABELS = {
    "service": "용역",
    "goods": "물품",
    "construction": "공사",
    "foreign": "외자",
    "etc": "기타",
}

SUPPORTED_EXTENSIONS = {".hwp", ".hwpx", ".pdf", ".docx", ".xls", ".xlsx", ".zip", ".txt"}
RELEVANT_DOC_KEYWORDS = (
    "제안요청", "과업지시", "과업내용", "과업수행", "입찰공고", "규격서",
    "시방서", "제안서", "요구사항", "산출내역", "과업설명", "rfp",
)

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
PDF_MAGIC = b"%PDF"
ZIP_MAGIC = b"PK"

RETRYABLE_HTTP = {408, 425, 429, 500, 502, 503, 504}
RETRYABLE_API_CODES = {"22", "23"}  # 트래픽/요청 제한 계열

logger = logging.getLogger("g2b-standalone")


@dataclass
class ParseResult:
    status: str
    detected_format: str
    parser: str
    quality: float
    text: str
    blocks: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AttachmentRef:
    bid_key: str
    bid_no: str
    bid_ord: str
    business_type: str
    filename: str
    url: str
    source: str


@dataclass
class Settings:
    year: int
    month: int
    api_key: str
    out_dir: Path
    business_types: list[str]
    page_size: int
    api_concurrency: int
    download_concurrency: int
    parse_concurrency: int
    chunk_days: int
    min_quality: float
    max_file_bytes: int
    keyword: str | None
    demand_org: str | None
    min_budget: int | None
    max_budget: int | None
    contract_method: str | None
    doc_mode: str
    skip_attachments: bool
    eorder_fallback: bool
    duplicate_format_priority: list[str]
    api_extra_params: dict[str, Any] = field(default_factory=dict)


class RetryableError(RuntimeError):
    pass


class PermanentAPIError(RuntimeError):
    pass


# ------------------------------- utility -------------------------------------

def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json_dumps(obj) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def safe_filename(name: str, fallback: str = "attachment.bin") -> str:
    name = Path(name or fallback).name
    name = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "_", name).strip(" .")
    return name[:180] or fallback


def attachment_format(filename: str, url: str = "") -> str:
    """다운로드 전 중복 포맷 선택용 확장자 판별."""
    suffix = Path(filename or "").suffix.lower().lstrip(".")
    if suffix in {x.lstrip(".") for x in SUPPORTED_EXTENSIONS}:
        return suffix
    url_suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return url_suffix if url_suffix else "unknown"


def canonical_attachment_stem(filename: str) -> str:
    """확장자를 제외한 파일명을 중복 판별용으로 정규화한다.

    NFKC + casefold + 공백/일반 구분문자 제거를 적용하므로
    `제안요청서.hwp`, `제안 요청서.PDF`도 같은 문서명으로 묶인다.
    """
    name = Path(safe_filename(filename)).stem
    name = unicodedata.normalize("NFKC", name).casefold().strip()
    # 파일명 자체의 의미를 훼손하지 않는 범위에서 공백/구분문자만 정규화
    name = re.sub(r"[\s._\-]+", "", name)
    return name or "attachment"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def first_nonempty(d: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        val = d.get(key)
        if val not in (None, "", "0", 0):
            return val
    return None


def to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def bid_key(item: dict[str, Any]) -> str:
    no = str(item.get("bidNtceNo") or "UNKNOWN")
    order = str(item.get("bidNtceOrd") or item.get("bidNtceOrdNo") or "000")
    return f"{no}-{order}"


def make_date_chunks(year: int, month: int, chunk_days: int) -> list[tuple[str, str]]:
    """월 전체를 겹침/누락 없이 N일 단위 YYYYMMDDHHMM 구간으로 분할."""
    last_day = calendar.monthrange(year, month)[1]
    month_start = datetime(year, month, 1, 0, 0)
    month_end = datetime(year, month, last_day, 23, 59)

    chunks: list[tuple[str, str]] = []
    cursor = month_start
    while cursor <= month_end:
        end_date = min(cursor.date() + timedelta(days=chunk_days - 1), month_end.date())
        chunk_end = datetime(end_date.year, end_date.month, end_date.day, 23, 59)
        chunks.append((cursor.strftime("%Y%m%d%H%M"), chunk_end.strftime("%Y%m%d%H%M")))
        cursor = chunk_end + timedelta(minutes=1)
    return chunks


def unwrap_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    items = body.get("items")
    if not items or isinstance(items, str):
        return []
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    if isinstance(items, dict):
        inner = items.get("item", items)
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
        if isinstance(inner, dict):
            return [inner]
    return []


def ole_stream_names(data: bytes) -> set[str]:
    """OLE 컨테이너 stream 이름을 소문자로 반환. 진단/형식 오인식 복구용."""
    if olefile is None or not data.startswith(OLE_MAGIC):
        return set()
    try:
        ole = olefile.OleFileIO(io.BytesIO(data))
        try:
            return {"/".join(parts).lower() for parts in ole.listdir()}
        finally:
            ole.close()
    except Exception:
        return set()


def sniff_format(data: bytes, filename: str = "") -> str:
    if data.startswith(PDF_MAGIC):
        return "pdf"

    if data.startswith(OLE_MAGIC):
        # 4월 실데이터에서 ".hwp" 이름이지만 실제 BIFF XLS인 파일이 다수 발견됨.
        streams = ole_stream_names(data)
        if "workbook" in streams or "book" in streams:
            return "xls"
        if "fileheader" in streams or any(x.startswith("bodytext/section") for x in streams):
            return "hwp"

        # olefile이 없거나 특이 OLE이면 확장자를 보조 신호로 사용.
        suffix = Path(filename.lower()).suffix
        if suffix == ".xls":
            return "xls"
        return "hwp"

    if data.startswith(ZIP_MAGIC):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                names = set(zf.namelist())
                if any(n.startswith("Contents/section") and n.endswith(".xml") for n in names):
                    return "hwpx"
                if "word/document.xml" in names:
                    return "docx"
                if "xl/workbook.xml" in names:
                    return "xlsx"
                return "zip"
        except zipfile.BadZipFile:
            return "unknown"

    suffix = Path(filename.lower()).suffix
    if suffix == ".txt":
        return "txt"
    if suffix == ".xls":
        return "xls"
    return "unknown"


def extraction_quality(text: str) -> float:
    """파서가 '성공'했지만 깨진 문자열을 반환하는 경우를 거르는 휴리스틱."""
    if not text or not text.strip():
        return 0.0

    stripped = text.strip()
    n = max(len(stripped), 1)
    if stripped.startswith(("HWP extraction failed", "HWP Protected", "PDF extraction failed")):
        return 0.0

    printable = sum(ch.isprintable() or ch in "\n\t" for ch in stripped) / n
    useful = sum(ch.isalnum() or ("가" <= ch <= "힣") or ch.isspace() for ch in stripped) / n
    replacement = stripped.count("\ufffd") / n
    null_ratio = stripped.count("\x00") / n
    ctrl = sum(ord(ch) < 32 and ch not in "\n\r\t" for ch in stripped) / n
    length_score = min(len(stripped) / 1500.0, 1.0)

    score = (
        0.30 * printable
        + 0.30 * useful
        + 0.25 * length_score
        + 0.15 * (1.0 - min(ctrl * 20, 1.0))
        - min(replacement * 5, 0.5)
        - min(null_ratio * 5, 0.5)
    )
    return max(0.0, min(1.0, score))


def lines_to_blocks(text: str, source: str | None = None) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for i, raw in enumerate(text.splitlines()):
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if not line:
            continue
        blocks.append({"type": "paragraph", "order": i, "text": line, "source": source})
    return blocks


def selected_bid_metadata(item: dict[str, Any]) -> dict[str, Any]:
    budget = to_int(first_nonempty(item, ("bdgtAmt", "presmptPrce", "asignBdgtAmt")))
    return {
        "bid_key": bid_key(item),
        "bid_notice_no": item.get("bidNtceNo"),
        "bid_notice_order": item.get("bidNtceOrd") or item.get("bidNtceOrdNo"),
        "business_type": item.get("_business_type"),
        "business_type_name": item.get("_business_type_name"),
        "bid_name": item.get("bidNtceNm"),
        "notice_datetime": item.get("bidNtceDt"),
        "bid_close_datetime": item.get("bidClseDt"),
        "notice_org": item.get("ntceInsttNm"),
        "demand_org": item.get("dminsttNm"),
        "contract_method": first_nonempty(item, ("cntrctCnclsMthdNm", "cntrctMthdNm")),
        "budget": budget,
        "detail_url": item.get("bidNtceDtlUrl"),
    }


# ------------------------------ API client -----------------------------------

class G2BClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self.api_sem = asyncio.Semaphore(settings.api_concurrency)
        self.download_sem = asyncio.Semaphore(settings.download_concurrency)
        limits = httpx.Limits(
            max_connections=max(settings.api_concurrency + settings.download_concurrency + 4, 16),
            max_keepalive_connections=16,
        )
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=60.0, write=30.0, pool=30.0),
            follow_redirects=True,
            limits=limits,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; G2B-RAG-Ingest/1.0)",
                "Accept": "application/json,text/plain,*/*",
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _gateway_error_from_xml(content: bytes) -> tuple[str | None, str | None]:
        try:
            root = StdET.fromstring(content)
            code = root.findtext(".//resultCode") or root.findtext(".//returnReasonCode")
            msg = root.findtext(".//resultMsg") or root.findtext(".//errMsg") or root.findtext(".//returnAuthMsg")
            return code, msg
        except Exception:
            return None, None

    async def request_json(self, endpoint: str, params: dict[str, Any], retries: int = 6) -> dict[str, Any]:
        url = f"{BASE_URL}/{endpoint}"
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                async with self.api_sem:
                    response = await self.client.get(url, params=params)

                if response.status_code in RETRYABLE_HTTP:
                    raise RetryableError(f"HTTP {response.status_code}")
                response.raise_for_status()

                try:
                    data = response.json()
                except Exception as e:
                    code, msg = self._gateway_error_from_xml(response.content)
                    if code in RETRYABLE_API_CODES:
                        raise RetryableError(f"API {code}: {msg}")
                    detail = f" code={code} msg={msg}" if code or msg else response.text[:300]
                    raise PermanentAPIError(f"JSON 응답이 아님:{detail}") from e

                header = data.get("response", {}).get("header", {})
                code = str(header.get("resultCode", ""))
                msg = str(header.get("resultMsg", ""))
                if code and code != "00":
                    if code in RETRYABLE_API_CODES:
                        raise RetryableError(f"API {code}: {msg}")
                    raise PermanentAPIError(f"API {code}: {msg}")
                return data

            except PermanentAPIError:
                raise
            except (RetryableError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                if attempt == retries - 1:
                    break
                delay = min(2 ** attempt, 20) + (0.1 * attempt)
                logger.warning("재시도 %s/%s %s (%s)", attempt + 1, retries, endpoint, e)
                await asyncio.sleep(delay)
            except httpx.HTTPStatusError as e:
                # 4xx 인증/파라미터 오류는 반복해도 해결되지 않는 경우가 대부분
                raise PermanentAPIError(f"HTTP {e.response.status_code}: {e.response.text[:300]}") from e

        raise RuntimeError(f"API 재시도 소진: {endpoint}: {last_error}")

    def _base_search_params(self, start: str, end: str, page: int) -> dict[str, Any]:
        params: dict[str, Any] = {
            "serviceKey": self.s.api_key,
            "type": "json",
            "inqryDiv": "1",
            "inqryBgnDt": start,
            "inqryEndDt": end,
            "numOfRows": self.s.page_size,
            "pageNo": page,
        }
        # PPSSrch 공통 검색조건. 값이 없으면 파라미터 자체를 보내지 않는다.
        if self.s.keyword:
            params["bidNtceNm"] = self.s.keyword
        if self.s.demand_org:
            params["dminsttNm"] = self.s.demand_org

        # 사용자가 공공데이터포털 명세의 추가 PPSSrch 파라미터를
        # 코드 수정 없이 전달할 수 있게 한다. 핵심/페이지 파라미터는 덮어쓰기 금지.
        reserved = {
            "serviceKey", "type", "inqryDiv", "inqryBgnDt", "inqryEndDt",
            "numOfRows", "pageNo",
        }
        for key, value in (self.s.api_extra_params or {}).items():
            if key in reserved:
                raise ValueError(f"api_extra_params에서 예약 파라미터를 덮어쓸 수 없음: {key}")
            if value not in (None, ""):
                params[str(key)] = value
        return params

    async def fetch_page(self, operation: str, start: str, end: str, page: int) -> tuple[list[dict[str, Any]], int]:
        data = await self.request_json(operation, self._base_search_params(start, end, page))
        body = data.get("response", {}).get("body", {}) or {}
        return unwrap_items(body), int(body.get("totalCount") or 0)

    async def fetch_chunk(self, business_type: str, start: str, end: str) -> list[dict[str, Any]]:
        operation = ENDPOINTS[business_type]
        first_items, total = await self.fetch_page(operation, start, end, 1)
        total_pages = max(1, math.ceil(total / self.s.page_size)) if total else 1
        logger.info("[%s] %s~%s total=%s pages=%s", BUSINESS_LABELS[business_type], start[:8], end[:8], total, total_pages)

        all_items = list(first_items)
        if total_pages > 1:
            results = await asyncio.gather(
                *(self.fetch_page(operation, start, end, p) for p in range(2, total_pages + 1))
            )
            for page_items, _ in results:
                all_items.extend(page_items)

        for item in all_items:
            item["_business_type"] = business_type
            item["_business_type_name"] = BUSINESS_LABELS[business_type]
            item["_source_operation"] = operation
            item["_query_start"] = start
            item["_query_end"] = end
        return all_items

    async def collect_bids(self) -> list[dict[str, Any]]:
        chunks = make_date_chunks(self.s.year, self.s.month, self.s.chunk_days)
        logger.info("조회 기간 청크: %s", chunks)

        tasks = [
            self.fetch_chunk(bt, start, end)
            for bt in self.s.business_types
            for start, end in chunks
        ]
        results = await asyncio.gather(*tasks)

        # 공고번호 + 공고차수 기준 중복 제거. 같은 공고가 중복 응답되어도 1회만 처리한다.
        dedup: dict[str, dict[str, Any]] = {}
        for group in results:
            for item in group:
                key = bid_key(item)
                # 업무구분이 누락된 특이 케이스 방지
                if key == "UNKNOWN-000":
                    key = hashlib.sha1(json_dumps(item).encode("utf-8")).hexdigest()
                if key not in dedup:
                    dedup[key] = item

        bids = list(dedup.values())
        bids = [b for b in bids if self._passes_post_filters(b)]
        bids.sort(key=lambda x: (str(x.get("bidNtceDt") or ""), str(x.get("bidNtceNo") or "")))
        return bids

    def _passes_post_filters(self, item: dict[str, Any]) -> bool:
        budget = to_int(first_nonempty(item, ("bdgtAmt", "presmptPrce", "asignBdgtAmt")))
        if self.s.min_budget is not None and (budget is None or budget < self.s.min_budget):
            return False
        if self.s.max_budget is not None and (budget is None or budget > self.s.max_budget):
            return False
        if self.s.contract_method:
            method = str(first_nonempty(item, ("cntrctCnclsMthdNm", "cntrctMthdNm")) or "")
            if self.s.contract_method.lower() not in method.lower():
                return False
        return True

    @staticmethod
    def attachments_from_notice(item: dict[str, Any], doc_mode: str) -> list[AttachmentRef]:
        refs: list[AttachmentRef] = []
        key = bid_key(item)
        no = str(item.get("bidNtceNo") or "")
        order = str(item.get("bidNtceOrd") or item.get("bidNtceOrdNo") or "000")
        bt = str(item.get("_business_type") or "unknown")

        seen: set[str] = set()
        for i in range(1, 11):
            url = str(item.get(f"ntceSpecDocUrl{i}") or "").strip()
            filename = str(item.get(f"ntceSpecFileNm{i}") or "").strip()
            if not url:
                continue
            if not filename:
                filename = f"attachment_{i}{Path(urlparse(url).path).suffix or '.bin'}"
            if doc_mode == "relevant" and not any(k.lower() in filename.lower() for k in RELEVANT_DOC_KEYWORDS):
                continue
            if url in seen:
                continue
            seen.add(url)
            refs.append(AttachmentRef(key, no, order, bt, filename, url, "notice"))
        return refs

    async def eorder_attachments(self, item: dict[str, Any]) -> list[AttachmentRef]:
        no = str(item.get("bidNtceNo") or "")
        if not no:
            return []
        params = {
            "serviceKey": self.s.api_key,
            "type": "json",
            "inqryDiv": "2",
            "bidNtceNo": no,
            "numOfRows": min(self.s.page_size, 999),
            "pageNo": 1,
        }
        data = await self.request_json(EORDER_ENDPOINT, params)
        body = data.get("response", {}).get("body", {}) or {}
        raw_items = unwrap_items(body)
        refs: list[AttachmentRef] = []
        seen: set[str] = set()
        for idx, it in enumerate(raw_items, 1):
            filename = str(it.get("eorderAtchFileNm") or f"eorder_{idx}.bin")
            url = str(it.get("eorderAtchFileUrl") or "").strip()
            if not url or url in seen:
                continue
            if self.s.doc_mode == "relevant" and not any(k.lower() in filename.lower() for k in RELEVANT_DOC_KEYWORDS):
                continue
            seen.add(url)
            refs.append(AttachmentRef(
                bid_key(item), no,
                str(item.get("bidNtceOrd") or item.get("bidNtceOrdNo") or "000"),
                str(item.get("_business_type") or "unknown"),
                filename, url, "eorder",
            ))
        return refs

    async def download(self, ref: AttachmentRef, retries: int = 5) -> bytes:
        last_error: Exception | None = None
        headers = {
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Referer": "https://www.g2b.go.kr/",
        }
        for attempt in range(retries):
            try:
                async with self.download_sem:
                    async with self.client.stream("GET", ref.url, headers=headers) as resp:
                        if resp.status_code in RETRYABLE_HTTP:
                            raise RetryableError(f"HTTP {resp.status_code}")
                        resp.raise_for_status()
                        buf = bytearray()
                        async for chunk in resp.aiter_bytes(1024 * 1024):
                            buf.extend(chunk)
                            if len(buf) > self.s.max_file_bytes:
                                raise PermanentAPIError(
                                    f"파일 크기 제한 초과: {len(buf) / (1024*1024):.1f}MB"
                                )
                        data = bytes(buf)
                        if not data:
                            raise RetryableError("빈 파일")
                        return data
            except PermanentAPIError:
                raise
            except (RetryableError, httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
                last_error = e
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code not in RETRYABLE_HTTP:
                    break
                if attempt < retries - 1:
                    await asyncio.sleep(min(2 ** attempt, 15))
        raise RuntimeError(f"첨부파일 다운로드 실패: {last_error}")


# ------------------------------ parsers --------------------------------------

class AttachmentParser:
    def __init__(self, min_quality: float):
        self.min_quality = min_quality

    def parse(self, data: bytes, filename: str) -> ParseResult:
        fmt = sniff_format(data, filename)
        try:
            if fmt == "hwp":
                return self.parse_hwp(data)
            if fmt == "hwpx":
                return self.parse_hwpx(data)
            if fmt == "pdf":
                return self.parse_pdf(data)
            if fmt == "docx":
                return self.parse_docx(data)
            if fmt == "xls":
                return self.parse_xls(data)
            if fmt == "xlsx":
                return self.parse_xlsx(data)
            if fmt == "zip":
                return self.parse_zip(data)
            if fmt == "txt":
                text = data.decode("utf-8", errors="replace")
                q = extraction_quality(text)
                return ParseResult("parsed" if q >= self.min_quality else "low_quality", fmt, "utf8", q, text, lines_to_blocks(text))
            return ParseResult("unsupported", fmt, "none", 0.0, "", warnings=["지원하지 않거나 파일 형식과 확장자가 불일치"])
        except Exception as e:
            return ParseResult("failed", fmt, "exception", 0.0, "", warnings=[f"{type(e).__name__}: {e}"])

    def parse_hwp(self, data: bytes) -> ParseResult:
        """
        HWP Troubleshooting 반영:
        1) langchain-teddynote HWPLoader primary
        2) 실패/저품질이면 olefile fallback
        3) pyhwp(hwp5txt)가 있으면 추가 fallback
        DRM/암호화는 olefile 단계에서 명시적으로 감지한다.
        """
        warnings: list[str] = []
        candidates: list[ParseResult] = []

        # 1) primary: langchain-teddynote HWPLoader
        if HWPLoader is not None:
            try:
                with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
                    f.write(data)
                    temp_path = f.name
                try:
                    try:
                        loader = HWPLoader(file_path=temp_path)
                    except TypeError:
                        loader = HWPLoader(temp_path)
                    try:
                        docs = list(loader.lazy_load())
                    except Exception:
                        docs = list(loader.load())
                    text = "\n\n".join(
                        str(getattr(d, "page_content", "") or "")
                        for d in docs
                        if str(getattr(d, "page_content", "") or "").strip()
                    ).strip()
                    q = extraction_quality(text)
                    result = ParseResult(
                        "parsed" if q >= self.min_quality else "low_quality",
                        "hwp", "HWPLoader", q, text, lines_to_blocks(text), []
                    )
                    candidates.append(result)
                    if result.status == "parsed":
                        return result
                    warnings.append(f"HWPLoader low quality={q:.3f}")
                finally:
                    Path(temp_path).unlink(missing_ok=True)
            except Exception as e:
                warnings.append(f"HWPLoader 실패: {type(e).__name__}: {e}")
        else:
            warnings.append("HWPLoader 미설치")

        # 2) documented fallback: olefile
        try:
            text, ole_warnings = self._ole_recovery(data)
            warnings.extend(ole_warnings)
            q = extraction_quality(text)
            result = ParseResult(
                "parsed" if q >= self.min_quality else ("low_quality" if text.strip() else "failed"),
                "hwp", "olefile_hwp5_records", q, text, lines_to_blocks(text),
                list(dict.fromkeys(warnings)),
            )
            candidates.append(result)
            if result.status == "parsed":
                return result
        except Exception as e:
            warnings.append(f"olefile fallback 실패: {type(e).__name__}: {e}")

        # 3) optional extra fallback: pyhwp hwp5txt
        if shutil.which("hwp5txt"):
            try:
                with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
                    f.write(data)
                    temp_path = f.name
                try:
                    proc = subprocess.run(
                        ["hwp5txt", temp_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=90,
                        check=False,
                    )
                    text = proc.stdout.decode("utf-8", errors="replace").strip()
                    q = extraction_quality(text)
                    result = ParseResult(
                        "parsed" if proc.returncode == 0 and q >= self.min_quality
                        else ("low_quality" if text else "failed"),
                        "hwp", "hwp5txt", q, text, lines_to_blocks(text),
                        ([proc.stderr.decode("utf-8", errors="replace")[:500]]
                         if proc.stderr else []),
                    )
                    candidates.append(result)
                    if result.status == "parsed":
                        result.warnings = list(dict.fromkeys(warnings + result.warnings))
                        return result
                    warnings.append(
                        f"hwp5txt low/fail return={proc.returncode}, quality={q:.3f}"
                    )
                finally:
                    Path(temp_path).unlink(missing_ok=True)
            except Exception as e:
                warnings.append(f"hwp5txt 실패: {type(e).__name__}: {e}")
        else:
            warnings.append("hwp5txt 미설치(선택 fallback)")

        if candidates:
            best = max(candidates, key=lambda x: (x.status == "parsed", x.quality, len(x.text)))
            if best.status != "parsed":
                best.status = "low_quality" if best.text.strip() else "failed"
            best.warnings = list(dict.fromkeys(best.warnings + warnings))
            return best

        return ParseResult("failed", "hwp", "none", 0.0, "", warnings=warnings)

    @staticmethod
    def _clean_hwp_text(text: str) -> str:
        out = []
        for ch in text:
            if ch in "\n\r\t":
                out.append(ch)
            elif unicodedata.category(ch).startswith("C"):
                out.append(" ")
            else:
                out.append(ch)
        text = "".join(out)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def _parse_hwp_record_stream(cls, raw: bytes) -> str:
        """HWP5 record stream에서 HWPTAG_PARA_TEXT(tag id 67)를 추출."""
        import struct

        texts: list[str] = []
        i = 0
        n = len(raw)

        while i + 4 <= n:
            header = struct.unpack_from("<I", raw, i)[0]
            tag_id = header & 0x3FF
            rec_len = (header >> 20) & 0xFFF
            header_len = 4

            if rec_len == 0xFFF:
                if i + 8 > n:
                    break
                rec_len = struct.unpack_from("<I", raw, i + 4)[0]
                header_len = 8

            start = i + header_len
            end = start + rec_len
            if end > n:
                break

            if tag_id == 67 and rec_len > 0:
                payload = raw[start:end]
                if len(payload) % 2:
                    payload = payload[:-1]
                if payload:
                    text = payload.decode("utf-16-le", errors="ignore")
                    text = cls._clean_hwp_text(text)
                    if text:
                        texts.append(text)

            i = end

        return "\n".join(texts)

    @classmethod
    def _ole_recovery(cls, data: bytes) -> tuple[str, list[str]]:
        if olefile is None:
            raise RuntimeError("olefile 미설치")

        warnings: list[str] = []
        parts: list[str] = []
        ole = olefile.OleFileIO(io.BytesIO(data))

        try:
            if ole.exists("EncryptedPackage"):
                raise RuntimeError("DRM/암호화 가능성: EncryptedPackage 존재")

            compressed = False
            if not ole.exists("FileHeader"):
                raise RuntimeError("FileHeader stream 없음: HWP5 형식이 아닐 수 있음")

            header = ole.openstream("FileHeader").read()
            if len(header) >= 40:
                props = int.from_bytes(header[36:40], "little", signed=False)
                compressed = bool(props & 0x01)
                encrypted = bool(props & 0x02)
                if encrypted:
                    raise RuntimeError("HWP FileHeader 암호화 플래그 감지")

            # 미리보기 텍스트는 보조 신호로 보존.
            if ole.exists("PrvText"):
                try:
                    prv = ole.openstream("PrvText").read().decode(
                        "utf-16-le", errors="ignore"
                    )
                    prv = cls._clean_hwp_text(prv.replace("\x00", ""))
                    if prv:
                        parts.append(prv)
                except Exception as e:
                    warnings.append(f"PrvText 읽기 실패: {e}")

            section_found = False
            for i in range(500):
                name = f"BodyText/Section{i}"
                if not ole.exists(name):
                    if i > 0 and section_found:
                        break
                    continue

                section_found = True
                raw = ole.openstream(name).read()
                if compressed:
                    try:
                        raw = zlib.decompress(raw, -15)
                    except Exception as e:
                        warnings.append(f"{name} raw-deflate 해제 실패: {e}")
                        continue

                text = cls._parse_hwp_record_stream(raw)
                if text:
                    parts.append(text)

            if not section_found:
                warnings.append("BodyText/Section* stream 없음")

        finally:
            ole.close()

        return "\n\n".join(x for x in parts if x.strip()).strip(), warnings

    def parse_hwpx(self, data: bytes) -> ParseResult:
        if etree is None:
            raise RuntimeError("lxml 미설치")
        blocks: list[dict[str, Any]] = []
        warnings: list[str] = []
        order = 0

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            section_files = sorted(
                n for n in zf.namelist()
                if n.startswith("Contents/section") and n.endswith(".xml")
            )
            for section_index, section_name in enumerate(section_files):
                try:
                    root = etree.fromstring(zf.read(section_name))
                except Exception as e:
                    warnings.append(f"{section_name}: {e}")
                    continue

                def lname(elem: Any) -> str:
                    return etree.QName(elem).localname

                def inside_table(elem: Any) -> bool:
                    parent = elem.getparent()
                    while parent is not None:
                        if lname(parent).lower() in {"tbl", "table"}:
                            return True
                        parent = parent.getparent()
                    return False

                for elem in root.iter():
                    tag = lname(elem).lower()
                    if tag in {"tbl", "table"}:
                        rows: list[list[str]] = []
                        for row in elem.iter():
                            if lname(row).lower() not in {"tr", "row"}:
                                continue
                            cells: list[str] = []
                            for cell in row:
                                if lname(cell).lower() not in {"tc", "cell"}:
                                    continue
                                texts = [
                                    t.text.strip() for t in cell.iter()
                                    if lname(t).lower() in {"t", "text"} and t.text and t.text.strip()
                                ]
                                cells.append(" ".join(texts))
                            if cells:
                                rows.append(cells)
                        if rows:
                            table_text = "\n".join(" | ".join(row) for row in rows)
                            blocks.append({
                                "type": "table", "order": order, "section_index": section_index,
                                "rows": rows, "text": table_text,
                            })
                            order += 1
                    elif tag in {"p", "paragraph"} and not inside_table(elem):
                        texts = [
                            t.text.strip() for t in elem.iter()
                            if lname(t).lower() in {"t", "text"} and t.text and t.text.strip()
                        ]
                        text = " ".join(texts).strip()
                        if text:
                            blocks.append({
                                "type": "paragraph", "order": order,
                                "section_index": section_index, "text": text,
                            })
                            order += 1

        text = "\n\n".join(b["text"] for b in blocks if b.get("text"))
        q = extraction_quality(text)
        return ParseResult("parsed" if q >= self.min_quality else "low_quality", "hwpx", "hwpx_xml", q, text, blocks, warnings)

    def parse_pdf(self, data: bytes) -> ParseResult:
        if PdfReader is None:
            raise RuntimeError("pypdf 미설치")
        reader = PdfReader(io.BytesIO(data))
        blocks: list[dict[str, Any]] = []
        warnings: list[str] = []
        for page_no, page in enumerate(reader.pages, 1):
            try:
                text = (page.extract_text() or "").strip()
                if text:
                    blocks.append({"type": "page", "order": page_no - 1, "page": page_no, "text": text})
            except Exception as e:
                warnings.append(f"page {page_no}: {e}")
        text = "\n\n".join(b["text"] for b in blocks)
        q = extraction_quality(text)
        if not text:
            warnings.append("텍스트가 없는 이미지 기반 PDF일 수 있음: OCR 후보")
        return ParseResult("parsed" if q >= self.min_quality else "low_quality", "pdf", "pypdf", q, text, blocks, warnings)

    def parse_docx(self, data: bytes) -> ParseResult:
        if DocxDocument is None or DocxParagraph is None or DocxTable is None:
            raise RuntimeError("python-docx 미설치")
        doc = DocxDocument(io.BytesIO(data))
        blocks: list[dict[str, Any]] = []
        order = 0
        for child in doc.element.body.iterchildren():
            tag = child.tag.rsplit("}", 1)[-1]
            if tag == "p":
                para = DocxParagraph(child, doc)
                text = para.text.strip()
                if text:
                    blocks.append({"type": "paragraph", "order": order, "text": text})
                    order += 1
            elif tag == "tbl":
                table = DocxTable(child, doc)
                rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
                table_text = "\n".join(" | ".join(row) for row in rows)
                if table_text.strip():
                    blocks.append({"type": "table", "order": order, "rows": rows, "text": table_text})
                    order += 1
        text = "\n\n".join(b["text"] for b in blocks)
        q = extraction_quality(text)
        return ParseResult("parsed" if q >= self.min_quality else "low_quality", "docx", "python-docx", q, text, blocks)

    def parse_xls(self, data: bytes) -> ParseResult:
        if xlrd is None:
            raise RuntimeError("xlrd 미설치")

        wb = xlrd.open_workbook(file_contents=data)
        blocks: list[dict[str, Any]] = []
        text_parts: list[str] = []
        order = 0

        for ws in wb.sheets():
            rows: list[list[str]] = []
            for r in range(ws.nrows):
                vals: list[str] = []
                for c in range(ws.ncols):
                    value = ws.cell_value(r, c)
                    if isinstance(value, float) and value.is_integer():
                        value = int(value)
                    vals.append("" if value in (None, "") else str(value).strip())
                if any(vals):
                    rows.append(vals)

            if rows:
                table_text = "\n".join(" | ".join(row) for row in rows)
                text_parts.append(f"[시트] {ws.name}\n{table_text}")
                blocks.append({
                    "type": "table",
                    "order": order,
                    "sheet": ws.name,
                    "nrows": ws.nrows,
                    "ncols": ws.ncols,
                    "rows": rows,
                    "text": table_text,
                })
                order += 1

        text = "\n\n".join(text_parts)
        q = extraction_quality(text)
        return ParseResult(
            "parsed" if q >= self.min_quality else "low_quality",
            "xls", "xlrd", q, text, blocks,
            ["OLE Workbook/Book stream 감지: legacy XLS로 처리"],
        )

    def parse_xlsx(self, data: bytes) -> ParseResult:
        if load_workbook is None:
            raise RuntimeError("openpyxl 미설치")
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        blocks: list[dict[str, Any]] = []
        order = 0
        for ws in wb.worksheets:
            for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                vals = ["" if v is None else str(v).strip() for v in row]
                if not any(vals):
                    continue
                text = " | ".join(vals)
                blocks.append({
                    "type": "table_row", "order": order, "sheet": ws.title,
                    "row": row_idx, "values": vals, "text": text,
                })
                order += 1
        text = "\n".join(b["text"] for b in blocks)
        q = extraction_quality(text)
        return ParseResult("parsed" if q >= self.min_quality else "low_quality", "xlsx", "openpyxl", q, text, blocks)

    def parse_zip(self, data: bytes) -> ParseResult:
        blocks: list[dict[str, Any]] = []
        warnings: list[str] = []
        order = 0
        max_members = 50
        max_member_size = 50 * 1024 * 1024
        max_total_size = 200 * 1024 * 1024

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if len(infos) > max_members:
                warnings.append(f"ZIP 파일 수 {len(infos)} > {max_members}; 앞부분만 처리")
                infos = infos[:max_members]
            if sum(i.file_size for i in infos) > max_total_size:
                raise RuntimeError("ZIP 비압축 크기 제한 초과")

            for info in infos:
                if info.file_size > max_member_size:
                    warnings.append(f"ZIP member 너무 큼: {info.filename}")
                    continue
                name = info.filename
                suffix = Path(name.lower()).suffix
                if suffix not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    member = zf.read(info)
                    inner = self.parse(member, name)
                    if inner.text:
                        blocks.append({
                            "type": "embedded_document", "order": order,
                            "member": name, "parser": inner.parser,
                            "quality": inner.quality, "text": inner.text,
                            "blocks": inner.blocks,
                        })
                        order += 1
                    warnings.extend(f"{name}: {w}" for w in inner.warnings)
                except Exception as e:
                    warnings.append(f"{name}: {type(e).__name__}: {e}")

        text = "\n\n".join(f"[ZIP:{b['member']}]\n{b['text']}" for b in blocks)
        q = extraction_quality(text)
        return ParseResult("parsed" if q >= self.min_quality else "low_quality", "zip", "zip_recursive", q, text, blocks, warnings)


