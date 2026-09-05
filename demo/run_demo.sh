#!/usr/bin/env bash
# 데모 준비를 한 번에. ko_lettucedetect/ 안에서 실행할 것.
#
#   bash demo/run_demo.sh
#
# 하는 일: 의존성 설치 → 문서 인덱싱 → 질문 사전 점검 → 화면 띄우기
set -eu

RUN="${RUN:-runs/klue}"
THR="${THR:-0.065}"

cd "$(dirname "$0")/.."

echo "=== 1/4  의존성 ==="
# gradio·pypdf 는 torch 에 의존하지 않는다.
# bitsandbytes 는 gemma 4bit 적재에 필요한데 .venv-train 에는 없다(번역은 .venv-vllm 에서 했다).
# --no-deps 로 torch 를 건드리지 않고 넣는다.
pip install -q gradio pypdf
pip install -q --no-deps "bitsandbytes>=0.46.1"

echo "=== 2/4  문서 인덱싱 ==="
python demo/build_index.py --src demo/corpus

echo "=== 3/4  질문 사전 점검 (답변 생성 포함, 10~20분) ==="
python demo/dry_run.py --run "$RUN" --threshold "$THR"

echo
echo "=== 4/4  demo/logs/dry_run.md 를 먼저 읽고 임계값을 정하세요 ==="
echo "    그 다음 아래 명령으로 화면을 띄웁니다:"
echo
echo "    python demo/app.py --run $RUN --threshold <정한 값>"
echo
