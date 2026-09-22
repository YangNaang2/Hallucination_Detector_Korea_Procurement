#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# 활성화된 가상환경이 있으면 그대로 사용해 CUDA torch 환경을 보존한다.
if [ -n "${VIRTUAL_ENV:-}" ] && command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif [ -x .venv/bin/python ]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

# 필수 패키지가 없을 때만 설치한다. torch를 강제로 재설치하지 않는다.
if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import httpx, dotenv, olefile, pypdf, docx, openpyxl, xlrd, lxml
PY
then
  echo "[초기 설정] 필요한 Python 패키지를 설치합니다."
  "$PYTHON_BIN" -m pip install -r requirements.txt
fi

exec "$PYTHON_BIN" run.py "$@"
