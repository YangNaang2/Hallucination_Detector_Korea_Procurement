"""Fixed chunk-size ablation with gold source offsets used only by the evaluator."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "procurement-pipeline"))
import context_qa300 as context  # noqa: E402
import rag_pilot as p  # noqa: E402

MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
STRATEGIES = [
    dict(id="flat-token-460", flat=True, parent_chars=None, overlap_chars=None,
         window_tokens=460, stride_tokens=420, first_only=False),
    dict(id="parent-900-w460", flat=False, parent_chars=900, overlap_chars=120,
         window_tokens=460, stride_tokens=420, first_only=False),
    dict(id="parent-1200-w460", flat=False, parent_chars=1200, overlap_chars=160,
         window_tokens=460, stride_tokens=420, first_only=False),
    dict(id="parent-1800-first460", flat=False, parent_chars=1800, overlap_chars=240,
         window_tokens=460, stride_tokens=420, first_only=True),
    dict(id="parent-1800-w256", flat=False, parent_chars=1800, overlap_chars=240,
         window_tokens=256, stride_tokens=216, first_only=False),
    dict(id="parent-1800-w384", flat=False, parent_chars=1800, overlap_chars=240,
         window_tokens=384, stride_tokens=344, first_only=False),
    dict(id="parent-1800-w460", flat=False, parent_chars=1800, overlap_chars=240,
         window_tokens=460, stride_tokens=420, first_only=False),
    dict(id="parent-2400-w460", flat=False, parent_chars=2400, overlap_chars=320,
         window_tokens=460, stride_tokens=420, first_only=False),
]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low, high = math.floor(pos), math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - pos) + ordered[high] * (pos - low)


def char_parents(text: str, size: int, overlap: int):
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            newline = text.rfind("\n", start + size // 2, end)
            if newline > start:
                end = newline + 1
        yield start, end
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


class Encoder:
    def __init__(self, model_dir: Path, device: str):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, use_fast=True)
        self.model = AutoModel.from_pretrained(model_dir, local_files_only=True).to(device).eval()
        self.prefix_ids = self.tokenizer("passage: ", add_special_tokens=False)["input_ids"]

    def text_offsets(self, text: str):
        encoded = self.tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        return encoded["input_ids"], encoded["offset_mapping"]

    def parent_windows(self, text: str, window: int, stride: int, first_only: bool):
        ids = self.tokenizer("passage: " + text, add_special_tokens=False)["input_ids"]
        windows = []
        for start in range(0, max(1, len(ids)), stride):
            chunk = ids[start : start + window]
            if start:
                chunk = self.prefix_ids + chunk
            windows.append(self.tokenizer.build_inputs_with_special_tokens(chunk))
            if first_only or start + window >= len(ids):
                break
        return windows

    def query(self, texts: list[str], batch_size: int = 64):
        batches = []
        for text in texts:
            ids = self.tokenizer("query: " + text, add_special_tokens=False)["input_ids"]
            batches.append(self.tokenizer.build_inputs_with_special_tokens(ids))
        return self.encode(batches, batch_size)

    def encode(self, sequences: list[list[int]], batch_size: int = 32):
        torch = self.torch
        output = []
        for start in range(0, len(sequences), batch_size):
            padded = self.tokenizer.pad(
                {"input_ids": sequences[start : start + batch_size]}, padding=True, return_tensors="pt"
            ).to(self.device)
            with torch.inference_mode():
                with torch.autocast(device_type="cuda", dtype=torch.float16,
                                    enabled=self.device == "cuda"):
                    hidden = self.model(**padded).last_hidden_state.float()
                mask = padded["attention_mask"].unsqueeze(-1).bool()
                mean = hidden.masked_fill(~mask, 0).sum(1) / mask.sum(1)
                vectors = torch.nn.functional.normalize(mean, p=2, dim=1)
            output.append(vectors.cpu().numpy().astype("float32"))
        return np.concatenate(output)


class Dense:
    def __init__(self, vectors: np.ndarray, parents: np.ndarray, chunks: list[dict], queries: dict[str, np.ndarray]):
        self.vectors = vectors
        self.parents = parents
        self.positions = {chunk["chunk_id"]: i for i, chunk in enumerate(chunks)}
        self.queries = queries

    def scores(self, question: str, permitted: list[dict]):
        allowed = {self.positions[chunk["chunk_id"]] for chunk in permitted}
        selected = np.array([i for i, parent in enumerate(self.parents) if int(parent) in allowed], dtype=np.int64)
        similarities = self.vectors[selected] @ self.queries[p.digest(question)]
        scores: dict[int, float] = {}
        for row, score in zip(selected, similarities):
            parent = int(self.parents[row])
            scores[parent] = max(scores.get(parent, -1.0), float(score))
        return [scores[self.positions[chunk["chunk_id"]]] for chunk in permitted]


def baseline_chunks(index: Path):
    connection = sqlite3.connect(f"file:{index.as_posix()}?mode=ro", uri=True)
    chunks = [json.loads(row[0]) for row in connection.execute("SELECT payload FROM corpus ORDER BY rowid")]
    connection.close()
    return chunks


def public_documents(manifest: dict, source_cache: list[dict]):
    lookup = {(item["bid"], item["sha256"]): item for item in source_cache}
    docs = []
    for document in manifest["documents"]:
        if document["security_level"] != "L1":
            continue
        item = lookup.get((document["bid_key"], document["sha256"]))
        if item is None:
            raise ValueError(f"Missing canonical source: {document['document_id']}")
        if hashlib.sha256(item["text"].encode("utf-8")).hexdigest() != document["text_sha256"]:
            raise ValueError(f"Canonical text hash mismatch: {document['document_id']}")
        docs.append((document, item["text"]))
    return docs


def make_chunks(strategy: dict, docs, private: list[dict], encoder: Encoder):
    chunks: list[dict] = []
    sequences: list[list[int]] = []
    window_parents: list[int] = []
    if strategy["flat"]:
        for document, text in docs:
            ids, offsets = encoder.text_offsets(text)
            for number, token_start in enumerate(range(0, max(1, len(ids)), strategy["stride_tokens"])):
                token_end = min(len(ids), token_start + strategy["window_tokens"])
                if not offsets:
                    continue
                start = offsets[token_start][0]
                end = offsets[token_end - 1][1]
                parent = document | {
                    "chunk_id": f"{document['document_id']}-FLAT-{number:05}",
                    "text": text[start:end], "text_start": start, "text_end": end,
                    "offset_unit": "Unicode code point, end exclusive",
                }
                chunks.append(parent)
                seq = encoder.parent_windows(parent["text"], strategy["window_tokens"],
                                             strategy["stride_tokens"], True)[0]
                sequences.append(seq); window_parents.append(len(chunks) - 1)
                if token_end >= len(ids):
                    break
    else:
        for document, text in docs:
            for number, (start, end) in enumerate(char_parents(
                text, strategy["parent_chars"], strategy["overlap_chars"]
            )):
                parent = document | {
                    "chunk_id": f"{document['document_id']}-AB-{number:05}",
                    "text": text[start:end], "text_start": start, "text_end": end,
                    "offset_unit": "Unicode code point, end exclusive",
                }
                chunks.append(parent)
                for seq in encoder.parent_windows(parent["text"], strategy["window_tokens"],
                                                  strategy["stride_tokens"], strategy["first_only"]):
                    sequences.append(seq); window_parents.append(len(chunks) - 1)
    # Private/company entities keep their audited parent boundary, but use the strategy's embedding windows.
    for original in private:
        chunks.append(original)
        for seq in encoder.parent_windows(original["text"], strategy["window_tokens"],
                                          strategy["stride_tokens"], strategy["first_only"]):
            sequences.append(seq); window_parents.append(len(chunks) - 1)
    return chunks, sequences, np.array(window_parents, dtype=np.int32)


def overlap_length(interval: tuple[int, int], spans: list[tuple[int, int]]) -> int:
    start, end = interval
    clipped = sorted((max(start, s), min(end, e)) for s, e in spans if min(end, e) > max(start, s))
    if not clipped:
        return 0
    total, left, right = 0, *clipped[0]
    for s, e in clipped[1:]:
        if s > right:
            total += right - left; left, right = s, e
        else:
            right = max(right, e)
    return total + right - left


def evaluate(strategy, chunks, dense, questions, registry):
    rows = []
    latencies = []
    for gold in questions:
        request = context.evaluation_request(gold)
        started = time.perf_counter()
        retrieved = p.retrieve(request, chunks, registry, dense=dense, top_k=6, purpose=True)
        latencies.append((time.perf_counter() - started) * 1000)
        evidence = gold["public_notice_evidence"]
        hits = []
        for ev in evidence:
            ranks = [rank for rank, chunk in enumerate(retrieved, 1)
                     if chunk.get("sha256") == ev["sha256"] and
                     min(chunk["text_end"], ev["text_end"]) > max(chunk["text_start"], ev["text_start"])]
            hits.append(min(ranks) if ranks else None)
        any_rank = min((rank for rank in hits if rank is not None), default=None)
        coverage_parts = []
        for ev in evidence:
            spans = [(chunk["text_start"], chunk["text_end"]) for chunk in retrieved
                     if chunk.get("sha256") == ev["sha256"]]
            covered = overlap_length((ev["text_start"], ev["text_end"]), spans)
            coverage_parts.append(covered / max(1, ev["text_end"] - ev["text_start"]))
        rows.append({
            "question_id": gold["question_id"], "split": gold["split"],
            "hit1": any_rank is not None and any_rank <= 1,
            "hit3": any_rank is not None and any_rank <= 3,
            "hit6": any_rank is not None and any_rank <= 6,
            "mrr6": 1 / any_rank if any_rank is not None and any_rank <= 6 else 0,
            "evidence_recall6": sum(rank is not None and rank <= 6 for rank in hits) / len(hits),
            "gold_char_coverage6": statistics.mean(coverage_parts),
            "top4_context_chars": sum(len(chunk["text"]) for chunk in retrieved[:4]),
            "retrieved_ids": [chunk["chunk_id"] for chunk in retrieved],
        })
    def summary(group):
        return {
            "questions": len(group),
            "hit_at_1": statistics.mean(row["hit1"] for row in group),
            "hit_at_3": statistics.mean(row["hit3"] for row in group),
            "hit_at_6": statistics.mean(row["hit6"] for row in group),
            "mrr_at_6": statistics.mean(row["mrr6"] for row in group),
            "evidence_recall_at_6": statistics.mean(row["evidence_recall6"] for row in group),
            "gold_char_coverage_at_6": statistics.mean(row["gold_char_coverage6"] for row in group),
            "top4_context_chars_mean": statistics.mean(row["top4_context_chars"] for row in group),
        }
    by_split = {split: summary([row for row in rows if row["split"] == split])
                for split in ["train", "dev", "test"]}
    return rows, summary(rows) | {
        "retrieval_latency_ms_median": statistics.median(latencies),
        "retrieval_latency_ms_p95": percentile(latencies, .95),
        "by_split": by_split,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--output", type=Path, default=ROOT / "project-docs/RAG파일럿/chunk-ablation-v1/results.json")
    args = parser.parse_args()
    local = ROOT / "work/rag-workstation-275"
    model_dir = local / "e5"
    manifest_path = ROOT / "project-docs/RAG파일럿/workstation-275/index_manifest.json"
    dataset_path = ROOT / "project-docs/평가데이터/v2/evaluation/questions_300.jsonl"
    source_path = ROOT / "work/source-transfer/source-texts.posix.json"
    manifest = read(manifest_path)
    originals = baseline_chunks(local / "index.sqlite")
    private = [chunk for chunk in originals if chunk["security_level"] != "L1"]
    docs = public_documents(manifest, read(source_path))
    questions = [q for q in jsonl(dataset_path) if q.get("public_notice_evidence") and q["expected_status"] != "access_denied"]
    if len(questions) != 295:
        raise ValueError(f"Expected 295 evaluable questions, found {len(questions)}")
    encoder = Encoder(model_dir, args.device)
    query_texts = sorted({q["question"] for q in questions})
    query_started = time.perf_counter()
    query_matrix = encoder.query(query_texts)
    queries = {p.digest(text): vector for text, vector in zip(query_texts, query_matrix)}
    query_seconds = time.perf_counter() - query_started
    registry = p.registry()
    results = []
    for strategy in STRATEGIES:
        started = time.perf_counter()
        chunks, sequences, parents = make_chunks(strategy, docs, private, encoder)
        token_count = sum(len(sequence) for sequence in sequences)
        vectors = encoder.encode(sequences)
        build_seconds = time.perf_counter() - started
        dense = Dense(vectors, parents, chunks, queries)
        rows, metrics = evaluate(strategy, chunks, dense, questions, registry)
        public_count = sum(chunk["security_level"] == "L1" for chunk in chunks)
        result = strategy | {
            "parent_chunks": len(chunks), "public_parent_chunks": public_count,
            "private_parent_chunks": len(chunks) - public_count,
            "embedding_windows": len(sequences), "embedding_input_tokens": token_count,
            "vector_bytes": int(vectors.nbytes), "build_seconds": build_seconds,
            "metrics": metrics, "rows": rows,
        }
        results.append(result)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"status": "running", "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(strategy["id"], "parents", len(chunks), "windows", len(sequences),
              "hit6", round(metrics["hit_at_6"], 4), "seconds", round(build_seconds, 2), flush=True)
    payload = {
        "status": "completed", "purpose": "retrospective development chunk ablation; not independent test",
        "created_at": "2026-09-22", "device": args.device,
        "model": "intfloat/multilingual-e5-small", "model_revision": MODEL_REVISION,
        "model_sha256": sha256(model_dir / "model.safetensors"),
        "dataset_sha256": sha256(dataset_path), "source_cache_sha256": sha256(source_path),
        "code_sha256": sha256(Path(__file__)), "questions": len(questions),
        "query_embeddings": len(query_texts), "query_embedding_seconds": query_seconds,
        "original_documents": len(docs), "baseline_private_chunks": len(private),
        "rrf_k": 60, "retrieval_top_k": 6, "generation_context_top_k": 4,
        "results": results,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("completed", args.output, flush=True)


if __name__ == "__main__":
    main()
