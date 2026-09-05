#!/usr/bin/env bash
# 200건 파일럿 — 목적은 두 가지다.
#   1) `<HAL>` 태그가 한국어 번역에서 살아남는지 (보존율 측정)
#   2) 12B 로도 27B 만큼 보존되는지 (되면 전체 번역이 A5000 1장으로 현실화된다)
#
# 사용: bash scripts/run_pilot.sh [건수]
set -euo pipefail

N="${1:-200}"
ENCODER="${ENCODER:-Alibaba-NLP/gte-multilingual-base}"

cd "$(dirname "$0")/.."

echo "=== 1/4 데이터 준비 (${N}건) ==="
source .venv-train/bin/activate
python -m src.prepare_ragtruth --limit "$N"
deactivate

echo
echo "=== 2/4 번역 — 모델 2종 비교 (A5000 1장) ==="
source .venv-vllm/bin/activate

echo "--- 12B ---"
python -m src.translate --model google/gemma-3-12b-it \
                        --quantization bitsandbytes --tag 12b

echo "--- 27B (int4, 느림. 건너뛰려면 SKIP_27B=1) ---"
if [[ "${SKIP_27B:-0}" != "1" ]]; then
  python -m src.translate --model google/gemma-3-27b-it \
                          --quantization bitsandbytes --max-num-seqs 8 --tag 27b || {
    echo "[!] 27B 실패 (VRAM 부족 가능). 12B 결과만으로 진행합니다."
  }
fi
deactivate

echo
echo "=== 3/4 검증 + 오프셋 재계산 ==="
source .venv-train/bin/activate
for T in 12b 27b; do
  F="work/translated_${T}.jsonl"
  [[ -f "$F" ]] || continue
  echo "--- ${T} ---"
  python -m src.postprocess --in "$F"
done

echo
echo "=========== 태그 보존율 비교 ==========="
for T in 12b 27b; do
  R="work/qc_report_${T}.md"
  [[ -f "$R" ]] || continue
  echo "[$T] $(grep -o '태그 보존율' -B1 "$R" | head -1)"
  grep '태그 보존율' "$R" || true
done
echo "======================================="
echo "상세: work/qc_report_*.md"
echo

read -r -p "어느 번역본으로 학습할까요? (12b / 27b): " PICK
DATA="work/ko_ragtruth_${PICK}.jsonl"
[[ -f "$DATA" ]] || { echo "[!] $DATA 없음"; exit 1; }

echo "=== 4/4 학습 + 평가 (${ENCODER}) ==="
RUN="runs/$(basename "$ENCODER")-${PICK}"
python -m src.train    --model "$ENCODER" --data "$DATA" --out "$RUN" --trust-remote-code
python -m src.evaluate --run "$RUN" --data "$DATA" --trust-remote-code

echo "완료. → $RUN"
