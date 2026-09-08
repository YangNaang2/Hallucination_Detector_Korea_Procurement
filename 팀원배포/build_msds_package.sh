#!/usr/bin/env bash
# MSDS 작업용 zip 을 만든다. **워크스테이션에서** 실행할 것.
#
#   bash 팀원배포/build_msds_package.sh
#
# 만드는 것: MSDS_환각탐지.zip
#   모델(klue) + 형광펜 앱 + 답변 모으기 + 채점 스크립트 + 톨루엔 52문항 + 설명
#
# 기존 build_package.sh 와 다른 점 — 예시가 학사요람 로그가 아니라 **MSDS 평가 세트**이고,
# 답변을 모으는 화면과 채점 스크립트가 함께 들어간다. GPU 없이 돌아간다.
set -eu

cd "$(dirname "$0")/.."
SRC="팀원배포"
RUN="${RUN:-runs/klue}"
OUT="MSDS_환각탐지"
WORK=".pkg_msds"

if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "[!] 파이썬을 찾을 수 없습니다. .venv-train 을 활성화하고 다시 실행하세요."; exit 1
fi
echo "파이썬: $($PY --version 2>&1)"

echo "=== 1/4  작업 폴더 준비 ==="
rm -rf "$WORK"
mkdir -p "$WORK/$OUT/model" "$WORK/$OUT/msds" "$WORK/$OUT/수집"

echo "=== 2/4  모델 복사 ($RUN) ==="
# 학습 체크포인트는 추론에 필요 없으므로 담지 않는다
for f in config.json model.safetensors pytorch_model.bin tokenizer.json tokenizer_config.json \
         special_tokens_map.json vocab.txt sentencepiece.bpe.model spiece.model added_tokens.json; do
  if [ -f "$RUN/$f" ]; then
    cp "$RUN/$f" "$WORK/$OUT/model/"
    echo "    $f"
  fi
done
if [ ! -f "$WORK/$OUT/model/config.json" ]; then
  echo "[!] $RUN 에 config.json 이 없습니다. RUN=경로 로 지정하세요."
  exit 1
fi

echo "=== 3/4  평가 세트 복사 ==="
N=0
for f in demo/msds/examples_msds_*.jsonl; do
  [ -f "$f" ] || continue
  cp "$f" "$WORK/$OUT/msds/"
  N=$((N + 1))
  echo "    $(basename "$f")"
done
if [ "$N" -eq 0 ]; then
  echo "[!] demo/msds/ 에 examples_msds_*.jsonl 이 없습니다."
  exit 1
fi
for f in demo/msds/chunks_*.json demo/msds/README_박승형.md; do
  [ -f "$f" ] && cp "$f" "$WORK/$OUT/msds/" && echo "    $(basename "$f")"
done

echo "=== 4/4  스크립트와 설명 복사 ==="
cp "$SRC/app_cpu.py"            "$WORK/$OUT/"     # app_msds 가 탐지기를 여기서 가져온다
cp "$SRC/app_msds.py"           "$WORK/$OUT/"
cp "$SRC/채점.py"                "$WORK/$OUT/"
cp "$SRC/requirements.txt"      "$WORK/$OUT/"
cp "$SRC/MSDS_읽어보세요.md"     "$WORK/$OUT/읽어보세요.md"
cp "$SRC/윈도우_MSDS실행.bat"    "$WORK/$OUT/윈도우_실행.bat"
cp "$SRC/맥_MSDS실행.command"    "$WORK/$OUT/맥_실행.command"
chmod +x "$WORK/$OUT/맥_실행.command"
printf '여기에 모은 답변이 쌓입니다. 다 하시면 이 폴더째로 보내 주세요.\n' \
  > "$WORK/$OUT/수집/읽어보세요.txt"

DEST="$(pwd)/$OUT.zip"
rm -f "$DEST"
$PY - "$DEST" "$WORK/$OUT" "$OUT" << 'ZIPEOF'
import sys, zipfile
from pathlib import Path
dest, src, top = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(src.rglob("*")):
        if f.is_file():
            z.write(f, f"{top}/{f.relative_to(src)}")
ZIPEOF
rm -rf "$WORK"

SIZE=$(du -h "$DEST" | cut -f1)
echo
echo "==================================================================="
echo " 팀원에게 보낼 파일:"
echo "   $DEST"
echo "   크기: $SIZE"
echo "==================================================================="
echo " 압축을 풀고"
echo "   윈도우 → 윈도우_실행.bat 더블클릭"
echo "   맥     → 맥_실행.command 더블클릭"
echo
echo " 돌려받을 것: 수집/모은답변.jsonl · 채점결과.md"
