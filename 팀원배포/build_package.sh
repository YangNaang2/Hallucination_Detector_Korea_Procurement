#!/usr/bin/env bash
# 팀원에게 보낼 zip 을 만든다. **워크스테이션에서** 실행할 것.
#
#   bash 팀원배포/build_package.sh
#
# 만드는 것: 한국어환각탐지기.zip  (모델 + 실행 스크립트 + 예시 + 설명)
#
# pipefail 을 쓰지 않는다 — sh/dash 로 실행돼도 그대로 돌아가게 하기 위해서다.
set -eu

cd "$(dirname "$0")/.."
SRC="팀원배포"
RUN="${RUN:-runs/klue}"
OUT="한국어환각탐지기"
WORK=".pkg_build"

# python3 만 있는 환경도 있으므로 찾아서 쓴다
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo "[!] 파이썬을 찾을 수 없습니다. .venv-train 을 활성화하고 다시 실행하세요."; exit 1
fi
echo "파이썬: $($PY --version 2>&1)"

echo "=== 1/4  작업 폴더 준비 ==="
rm -rf "$WORK"
mkdir -p "$WORK/$OUT/model"

echo "=== 2/4  모델 복사 ($RUN) ==="
# 학습 체크포인트(checkpoint-*, optimizer.pt 등)는 추론에 불필요하므로 담지 않는다
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

echo "=== 3/4  예시 만들기 ==="
$PY - "$WORK/$OUT/examples.jsonl" << 'PYEOF'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
log = Path("demo/logs/eval2.jsonl")
labels_p = Path("demo/dryrun_labels.json")
labels = {}
if labels_p.exists():
    labels = {k: v for k, v in json.loads(labels_p.read_text(encoding="utf-8")).items()
              if not k.startswith("_")}
seen = {}
if log.exists():
    for line in log.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            seen[r["question"]] = r          # 같은 질문은 마지막 것(최신 답변)만
# 환각이 있는 것을 앞에 — 팀원이 첫 예시부터 형광펜을 보게 한다
order = sorted(seen.values(),
               key=lambda r: (not labels.get(r["question"], {}).get("hallucinated", False),
                              r["question"]))
with open(out, "w", encoding="utf-8") as f:
    for r in order:
        f.write(json.dumps({"question": r["question"], "context": r["context"],
                            "answer": r["answer"]}, ensure_ascii=False) + "\n")
print(f"    예시 {len(order)}개")
PYEOF

echo "=== 4/4  스크립트와 설명 복사 ==="
for f in app_cpu.py 읽어보세요.md requirements.txt 윈도우_실행.bat 맥_실행.command; do
  cp "$SRC/$f" "$WORK/$OUT/"
done
chmod +x "$WORK/$OUT/맥_실행.command"

DEST="$(pwd)/$OUT.zip"
rm -f "$DEST"
# zip 명령이 없는 서버가 흔하므로 파이썬으로 묶는다 (팀원이 윈도우라 zip 형식이어야 한다)
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
echo " 이 파일 하나만 보내면 됩니다. 팀원은 압축을 풀고"
echo "   윈도우 → 윈도우_실행.bat 더블클릭"
echo "   맥     → 맥_실행.command 더블클릭"
