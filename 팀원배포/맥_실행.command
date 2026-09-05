#!/usr/bin/env bash
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
echo "==========================================="
echo " 한국어 환각 탐지기"
echo "==========================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "[오류] 파이썬이 없습니다."
  echo "  https://www.python.org/downloads/ 에서 설치한 뒤 다시 실행하세요."
  read -n 1 -s -r -p "아무 키나 누르면 닫힙니다"; exit 1
fi

if [ ! -f .setup_done ]; then
  echo "처음 실행이라 준비를 합니다. 5~10분 걸립니다."
  echo "이 창을 닫지 마세요."
  echo
  rm -rf .venv
  python3 -m venv .venv || { echo "[오류] 가상환경을 만들지 못했습니다."; read -n 1 -s -r; exit 1; }
  source .venv/bin/activate
  python -m pip install --upgrade pip
  if ! python -m pip install -r requirements.txt; then
    echo "[오류] 설치에 실패했습니다. 인터넷 연결을 확인하고 다시 실행하세요."
    read -n 1 -s -r; exit 1
  fi
  touch .setup_done
else
  source .venv/bin/activate
fi

echo
echo "브라우저가 열립니다. 이 창을 닫으면 종료됩니다."
echo
python app_cpu.py
echo
echo "종료되었습니다."
read -n 1 -s -r -p "아무 키나 누르면 닫힙니다"
