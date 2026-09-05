#!/usr/bin/env bash
# 팀원에게 보낼 공유 링크를 띄운다. 워크스테이션에서 실행.
#
#   bash demo/share.sh
#
# 72시간짜리 공개 URL 이 나온다. 이 창을 닫으면 링크도 죽는다.
set -eu
cd "$(dirname "$0")/.."

RUN="${RUN:-runs/klue}"
AGG="${AGG:-min2}"
THR="${THR:-0.35}"

echo "설정: $RUN · 집계 $AGG · 임계값 $THR"
echo "잠시 뒤 'Running on public URL: https://....gradio.live' 줄이 뜹니다."
echo "그 주소를 팀원에게 보내세요. 이 창을 닫으면 링크가 끊깁니다."
echo
python demo/app.py --run "$RUN" --agg "$AGG" --threshold "$THR" --share
