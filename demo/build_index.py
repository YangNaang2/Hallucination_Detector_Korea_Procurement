"""학사요람(또는 아무 한국어 문서)을 청크로 쪼개 검색 인덱스를 만든다. — A 파트

PDF·TXT·MD 를 넣으면 `demo/index/` 에 청크와 임베딩이 저장된다.
FAISS 같은 것을 쓰지 않고 numpy 내적으로 끝낸다. 학사요람 규모(수천 청크)에서는
그게 더 빠르고 설치할 것도 없다.

사용
  python demo/build_index.py --src ../학사요람.pdf
  python demo/build_index.py --src 문서폴더/ --chunk-size 700
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

HERE = Path(__file__).resolve().parent
INDEX_DIR = HERE / "index"
DEFAULT_EMBEDDER = "BAAI/bge-m3"


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import pypdf
        except ImportError:
            raise SystemExit("[!] pip install pypdf")
        r = pypdf.PdfReader(str(path))
        return "\n\n".join((p.extract_text() or "") for p in r.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def chunk(text: str, size: int, overlap: int) -> list[str]:
    """문단 경계를 지키면서 자른다. 문단 하나가 너무 길면 문장 단위로 더 쪼갠다."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    units: list[str] = []
    for p in paras:
        if len(p) <= size:
            units.append(p)
            continue
        # 각 lookbehind 는 폭이 고정돼야 한다 (파이썬 re 제약) — 분기별로 따로 쓴다
        for sent in re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+", p):
            if sent is None:
                continue
            sent = sent.strip()
            while len(sent) > size:
                units.append(sent[:size])
                sent = sent[size - overlap:]
            if sent:
                units.append(sent)

    out, buf = [], ""
    for u in units:
        if len(buf) + len(u) + 2 <= size:
            buf = f"{buf}\n\n{u}" if buf else u
        else:
            if buf:
                out.append(buf)
            buf = (out[-1][-overlap:] + "\n\n" + u) if (out and overlap) else u
    if buf:
        out.append(buf)
    return [c for c in out if len(c.strip()) >= 30]


@torch.no_grad()
def embed(texts: list[str], model_name: str, batch: int = 8) -> np.ndarray:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device).eval()
    vecs = []
    for i in range(0, len(texts), batch):
        enc = tok(texts[i:i + batch], padding=True, truncation=True,
                  max_length=1024, return_tensors="pt").to(device)
        out = model(**enc).last_hidden_state[:, 0]        # bge 계열은 CLS 풀링
        vecs.append(torch.nn.functional.normalize(out, dim=-1).cpu().numpy())
        if i % (batch * 20) == 0:
            print(f"  임베딩 {i:,}/{len(texts):,}", flush=True)
    return np.concatenate(vecs).astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="파일 또는 폴더")
    ap.add_argument("--embedder", default=DEFAULT_EMBEDDER)
    ap.add_argument("--chunk-size", type=int, default=700)
    ap.add_argument("--overlap", type=int, default=100)
    args = ap.parse_args()

    src = Path(args.src)
    files = sorted([p for p in src.rglob("*") if p.suffix.lower() in {".pdf", ".txt", ".md"}]) \
        if src.is_dir() else [src]
    if not files:
        raise SystemExit(f"[!] 읽을 문서가 없습니다: {src}")

    chunks: list[dict] = []
    for f in files:
        text = read_text(f)
        for j, c in enumerate(chunk(text, args.chunk_size, args.overlap)):
            chunks.append({"id": f"{f.stem}-{j:04d}", "source": f.name, "text": c})
        print(f"{f.name}: 누적 {len(chunks):,} 청크")

    if not chunks:
        raise SystemExit("[!] 청크가 하나도 안 나왔습니다. PDF 텍스트 추출을 확인하세요.")

    vecs = embed([c["text"] for c in chunks], args.embedder)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(INDEX_DIR / "vectors.npy", vecs)
    with open(INDEX_DIR / "chunks.jsonl", "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (INDEX_DIR / "meta.json").write_text(
        json.dumps({"embedder": args.embedder, "n_chunks": len(chunks),
                    "chunk_size": args.chunk_size, "overlap": args.overlap},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n→ {INDEX_DIR}  ({len(chunks):,} 청크 · {vecs.shape[1]} 차원)")


if __name__ == "__main__":
    main()
