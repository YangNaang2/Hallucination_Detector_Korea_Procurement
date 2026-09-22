"""Finalize the fixed 300-question W384 run without changing canonical answers.

This is a post-run tool.  Retrieval and generation never import this module and
never receive the gold dataset.  The latest attempt is selected even when it
failed; a later retry therefore remains visible in the attempt history.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "project-docs/RAG파일럿/window384-run-v1"
BASELINE = ROOT / "project-docs/RAG파일럿/workstation-275/evaluation/effective_results.json"
DATASET = ROOT / "project-docs/평가데이터/v2/evaluation/questions_300.jsonl"
RUN_ID = "window384-gpu-v1"
DENIAL = "현재 세션의 권한으로 요청한 내부 자료를 제공할 수 없습니다. 소속과 접근 권한을 확인해 주세요."


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str | None) -> str | None:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None


def jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def latest_records():
    rows = {}
    attempts_total = 0
    configs = []
    for shard in ("w1", "w2", "w3", "w4"):
        shard_root = OUT / "shards" / shard
        state = load(shard_root / "evaluation" / f"{RUN_ID}-state.json")
        configs.append(state["config"])
        for qid, attempts in state["attempts"].items():
            if qid in rows or not attempts:
                raise ValueError(f"duplicate or empty attempts: {qid}")
            attempts_total += len(attempts)
            selected = attempts[-1]
            record_path = shard_root / selected["record_path"]
            record = load(record_path)
            if record["request"]["question_id"] != qid or record["status"] != selected["status"]:
                raise ValueError(f"state/raw mismatch: {qid}")
            rows[qid] = {
                "record": record,
                "record_path": str(record_path.relative_to(ROOT)),
                "attempt_count": len(attempts),
                "attempts": attempts,
                "shard": shard,
            }
    return rows, attempts_total, configs


def main() -> None:
    selection = load(OUT / "evaluation/selection.json")
    requests = load(OUT / "runtime/requests.json")
    gold_rows = jsonl(DATASET)
    gold = {q["question_id"]: q for q in gold_rows}
    requested = [q["question_id"] for q in requests]
    failures = []

    if len(gold) != 300 or len(gold_rows) != 300:
        failures.append("gold dataset is not 300 unique questions")
    if requested != selection["question_ids"] or len(set(requested)) != 300:
        failures.append("runtime requests differ from preregistered 300 IDs")
    forbidden = {"expected_answer", "must_include", "must_not_claim", "reasoning", "hallucination_spans"}
    leaked = sorted((r["question_id"], sorted(forbidden & set(r))) for r in requests if forbidden & set(r))
    if leaked:
        failures.append(f"gold fields leaked into runtime requests: {leaked[:3]}")

    latest, attempts_total, configs = latest_records()
    if set(latest) != set(requested):
        failures.append("latest results do not cover exactly the preregistered IDs")
    # Each shard intentionally has a different request file.  All model,
    # index, vector, query-vector and code fingerprints must still match.
    comparable_configs = [{k: v for k, v in c.items() if k != "requests_sha256"} for c in configs]
    config_hashes = {hashlib.sha256(json.dumps(c, sort_keys=True).encode()).hexdigest() for c in comparable_configs}
    if len(config_hashes) != 1:
        failures.append("shard configs differ")

    baseline_data = load(BASELINE)
    baseline = {r["question_id"]: r for r in baseline_data["records"]}
    if set(baseline) != set(requested):
        failures.append("W460 baseline IDs differ from W384 IDs")

    exported = []
    links = []
    comparisons = []
    inspected_retrieved = 0
    generation_times = []
    invalid_citation_answers = 0
    answer_changed = 0
    top6_changed = 0
    top4_changed = 0
    initial_failure_ids = []

    for qid in requested:
        item = latest[qid]
        record = item["record"]
        request = record["request"]
        expected_request = next(r for r in requests if r["question_id"] == qid)
        if request != expected_request:
            failures.append(f"request mismatch: {qid}")
        statuses = [a["status"] for a in item["attempts"]]
        if "generation_failed" in statuses:
            initial_failure_ids.append(qid)
        if record.get("hallucination_spans") is not None:
            failures.append(f"unexpected prefilled hallucination labels: {qid}")
        retrieved = record.get("retrieved") or []
        evidence = record.get("prompt_evidence") or []
        inspected_retrieved += len(retrieved)
        retrieved_by_id = {r["chunk_id"]: r for r in retrieved}
        for e in evidence:
            source = retrieved_by_id.get(e["chunk_id"])
            if not source or e["text_sha256"] != source.get("text_sha256"):
                failures.append(f"prompt evidence is not linked to retrieved source: {qid}")
        answer = record.get("actual_answer")
        valid_citations = {e["citation"] for e in evidence}
        used_citations = {int(x) for x in re.findall(r"\[(\d+)\]", answer or "")}
        invalid = sorted(used_citations - valid_citations)
        invalid_citation_answers += bool(invalid)
        if record["status"] == "access_denied":
            if record.get("llm_called") or retrieved or evidence or answer != DENIAL:
                failures.append(f"invalid access-denied path: {qid}")
        elif record["status"] == "generated":
            if not answer or not answer.strip() or not record.get("llm_called"):
                failures.append(f"invalid generated answer: {qid}")
            generation_times.append(record.get("generation_seconds", 0.0))
        else:
            failures.append(f"unresolved latest status {record['status']}: {qid}")

        old = baseline[qid]
        old_record = load(ROOT / old["record_path"])
        old_top6 = [r["chunk_id"] for r in old_record.get("retrieved", [])]
        new_top6 = [r["chunk_id"] for r in retrieved]
        old_top4 = [r["chunk_id"] for r in old_record.get("retrieved", [])[:4]]
        new_top4 = [r["chunk_id"] for r in retrieved[:4]]
        changed_answer = old.get("actual_answer") != answer
        answer_changed += changed_answer
        top6_changed += old_top6 != new_top6
        top4_changed += old_top4 != new_top4
        comparisons.append({
            "question_id": qid,
            "status_w460": old["status"],
            "status_w384": record["status"],
            "top6_identical_order": old_top6 == new_top6,
            "top4_identical_order": old_top4 == new_top4,
            "top6_overlap": len(set(old_top6) & set(new_top6)),
            "answer_changed": changed_answer,
            "w460_answer_sha256": old.get("answer_sha256"),
            "w384_answer_sha256": sha256_text(answer),
            "w460_agent_review": old.get("agent_review"),
            "w384_agent_review": "pending",
            "caution": "Generation used temperature 0.7; answer differences combine retrieval and sampling effects.",
        })
        q = gold[qid]
        exported.append({
            "question_id": qid,
            "company_id": q["company_id"],
            "split": q["split"],
            "run_id": RUN_ID,
            "record_path": item["record_path"],
            "status": record["status"],
            "question": q["question"],
            "expected_answer": q["expected_answer"],
            "actual_answer": answer,
            "agent_review": "pending",
            "agent_notes": "W384 신규 답변 내용 검토 및 사람 최종 승인 대기",
            "invalid_citations": invalid,
            "answer_sha256": sha256_text(answer),
            "attempt_count": item["attempt_count"],
            "human_approval": "pending",
            "hallucination_spans": None,
        })
        record_path = ROOT / item["record_path"]
        links.append({
            "question_id": qid,
            "record_path": item["record_path"],
            "record_sha256": sha256_bytes(record_path),
            "answer_sha256": sha256_text(answer),
            "prompt_sha256": record.get("prompt_sha256"),
            "prompt_evidence": evidence,
            "human_approval": "pending",
            "hallucination_spans": None,
        })

    counts = dict(Counter(r["status"] for r in exported))
    summary = {
        "run_id": RUN_ID,
        "unique_questions": len(exported),
        "counts": counts,
        "attempt_count": attempts_total,
        "initial_generation_failure_ids_recovered_by_same_config_retry": initial_failure_ids,
        "invalid_citation_answers": invalid_citation_answers,
        "inspected_retrieved_chunks": inspected_retrieved,
        "generation_seconds": {
            "sum_successful_requests": sum(generation_times),
            "median": statistics.median(generation_times),
            "minimum": min(generation_times),
            "maximum": max(generation_times),
            "scope": "Successful local HTTP calls; model/index/query encoding and process startup excluded. Four calls ran concurrently.",
        },
        "w460_comparison": {
            "top6_order_changed": top6_changed,
            "top4_order_changed": top4_changed,
            "answer_changed": answer_changed,
            "same_question_count": 300,
            "limitation": "Temperature 0.7 means answer changes cannot be attributed only to W384 retrieval.",
        },
        "integrity_failures": failures,
        "runtime_gold_fields_present": bool(leaked),
        "content_review": "evaluation_in_progress",
        "human_approval": "pending",
        "hallucination_detection": "evaluation_in_progress",
        "interpretation": "Execution and provenance audit only. Counts are not answer accuracy, hallucination accuracy, or independent-test performance.",
    }
    dump(OUT / "evaluation/effective_results.json", summary | {"records": exported})
    dump(OUT / "evaluation/final_summary.json", summary)
    dump(OUT / "evaluation/w460-vs-w384.json", {"summary": summary["w460_comparison"], "records": comparisons})
    dump(OUT / "evaluation/labeling_handoff.json", {
        "run_id": RUN_ID,
        "answer_strings_immutable": True,
        "records": links,
        "note": "Label actual_answer from record_path. Detector output is a proposal, not ground truth; agent adjustment and human approval must remain separate.",
    })
    dump(OUT / "validation/execution-audit.json", summary)
    fields = ["question_id", "company_id", "split", "run_id", "status", "agent_review", "attempt_count", "record_path", "human_approval"]
    with (OUT / "evaluation/integrated_status.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(exported)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
