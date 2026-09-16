#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""사용자용 원클릭 실행기. 내부 엔진 파일을 직접 실행할 필요가 없다."""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.toml"
ENV_FILE = ROOT / ".env"
ENGINE = ROOT / "_engine"
PIPELINE = ENGINE / "g2b_month_pipeline.py"
OCR = ENGINE / "g2b_gpu_ocr.py"


def read_config():
    if not CONFIG.exists():
        raise SystemExit("config.toml이 없습니다.")
    with CONFIG.open("rb") as f:
        cfg = tomllib.load(f)
    run = cfg.get("run") or {}
    try:
        year = int(run["year"])
        month = int(run["month"])
    except Exception:
        raise SystemExit("config.toml의 [run] year/month를 확인하세요.")
    if month < 1 or month > 12:
        raise SystemExit("month는 1~12여야 합니다.")
    return cfg, run, year, month


def env_has_key() -> bool:
    if not ENV_FILE.exists():
        return False
    for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("NARA_API_KEY="):
            value = line.split("=", 1)[1].strip()
            return bool(value)
    return False


def ensure_api_key():
    if os.getenv("NARA_API_KEY") or env_has_key():
        return
    print("\n[첫 실행] 나라장터/공공데이터포털 서비스키를 입력하세요.")
    key = getpass.getpass("NARA_API_KEY: ").strip()
    if not key:
        raise SystemExit("API 키가 입력되지 않았습니다.")
    ENV_FILE.write_text(f"NARA_API_KEY={key}\n", encoding="utf-8")
    try:
        ENV_FILE.chmod(0o600)
    except Exception:
        pass
    print(".env에 저장했습니다.\n")


def run_cmd(args: list[str], check=True) -> int:
    shown = " ".join(args)
    print(f"\n$ {shown}\n")
    proc = subprocess.run(args, cwd=ROOT)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc.returncode


def pipeline_cmd(command: str, year: int, month: int, out_dir: str, extra=None):
    cmd = [
        sys.executable, str(PIPELINE), command,
        "--year", str(year), "--month", str(month),
        "--out", out_dir,
        "--filter-config", str(CONFIG),
    ]
    if extra:
        cmd += list(extra)
    return cmd


def gpu_ready() -> tuple[bool, str]:
    code = (
        "import torch, easyocr, pymupdf; "
        "print(torch.cuda.is_available()); "
        "print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NO_GPU')"
    )
    p = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if p.returncode != 0:
        return False, (p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "GPU OCR 패키지 없음")
    lines = [x.strip() for x in p.stdout.splitlines() if x.strip()]
    ok = bool(lines and lines[0] == "True")
    return ok, (lines[1] if len(lines) > 1 else "CUDA unavailable")


def main():
    ap = argparse.ArgumentParser(description="Standalone G2B one-click runner")
    ap.add_argument("--settings", action="store_true", help="설정만 확인")
    ap.add_argument("--cpu-only", action="store_true", help="GPU OCR 생략")
    ap.add_argument("--ocr-only", action="store_true", help="기존 CPU 결과에서 GPU OCR만 실행")
    ap.add_argument("--status", action="store_true", help="현재 월 상태만 확인")
    args = ap.parse_args()

    cfg, run, year, month = read_config()
    out_dir = str(run.get("out", "./data"))
    resume = bool(run.get("resume", True))
    auto_ocr = bool(run.get("run_gpu_ocr", True)) and not args.cpu_only
    dpi = int(run.get("gpu_ocr_dpi", 160))
    base = (ROOT / out_dir / f"{year:04d}-{month:02d}").resolve() if not Path(out_dir).is_absolute() else Path(out_dir) / f"{year:04d}-{month:02d}"

    print("=" * 68)
    print("G2B One-Click Pipeline")
    print("=" * 68)
    print(f"기간       : {year:04d}-{month:02d}")
    print(f"데이터     : {base}")
    print(f"재시작모드 : {resume}")
    print(f"GPU OCR    : {auto_ocr}")
    print("=" * 68)

    if args.settings:
        run_cmd(pipeline_cmd("show-settings", year, month, out_dir))
        return
    if args.status:
        run_cmd(pipeline_cmd("status", year, month, out_dir))
        return

    ensure_api_key()

    if args.ocr_only:
        auto_ocr = True
    else:
        bids = base / "bids.jsonl"
        download_manifest = base / "download_manifest.jsonl"

        if resume and bids.exists():
            print("[재시작] bids.jsonl 존재 → API fetch 생략")
        else:
            run_cmd(pipeline_cmd("fetch", year, month, out_dir))

        if resume and download_manifest.exists():
            print("[재시작] download_manifest.jsonl 존재 → 다운로드 단계 생략")
        else:
            run_cmd(pipeline_cmd("download", year, month, out_dir))

        # parse는 재실행해도 성공 parsed 캐시는 재사용하고 실패/저품질만 다시 시도한다.
        run_cmd(pipeline_cmd("parse", year, month, out_dir))

    if auto_ocr:
        ok, gpu = gpu_ready()
        if ok:
            print(f"\nGPU OCR 시작: {gpu}")
            run_cmd([
                sys.executable, str(OCR),
                "--year", str(year), "--month", str(month),
                "--out", out_dir,
                "--dpi", str(dpi),
                "--apply",
            ])
        else:
            print(f"\n[GPU OCR 생략] {gpu}")
            print("CPU 결과는 정상 보존됩니다. GPU 환경을 준비한 뒤 `python run.py --ocr-only`로 이어서 실행하세요.")

    print("\n최종 상태")
    run_cmd(pipeline_cmd("status", year, month, out_dir))
    print("\n완료. RAG 입력은 해당 월의 chunk_ready.jsonl을 사용하세요.")


if __name__ == "__main__":
    main()
