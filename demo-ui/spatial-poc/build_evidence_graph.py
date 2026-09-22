#!/usr/bin/env python3
"""Build a deterministic, read-only ASTRA relationship projection.

The output is a visualization dataset, not a retrieval index or GraphRAG store.
Only committed public L1 records and explicitly synthetic company fixtures are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "demo-ui/spatial-poc/dist"

SOURCES = {
    "observatory": ROOT / "demo-ui/spatial-poc/dist/rag-observatory.json",
    "notices": ROOT / "demo-ui/spatial-poc/dist/public-notices.json",
    "companies": ROOT / "project-docs/가상기업/v1/company_master.json",
    "mappings": ROOT / "project-docs/가상기업/v1/condition_mappings.json",
    "scenarios": ROOT / "project-docs/가상기업/v1/scenario_plans.json",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def short(value: str, size: int = 14) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:size]


def access(level: str = "L1", tenant_id: str | None = None, roles: list[str] | None = None) -> dict:
    return {
        "level": level,
        "tenant_id": tenant_id,
        "company_id": tenant_id.removeprefix("astra-").upper() if tenant_id else None,
        "allowed_roles": roles or (["viewer", "bid_analyst", "cost_analyst", "bid_approver"] if level == "L1" else []),
    }


def provenance(source_key: str, pointer: str = "") -> dict:
    path = SOURCES[source_key]
    return {
        "source_path": path.relative_to(ROOT).as_posix(),
        "source_hash": sha256(path),
        "json_pointer": pointer,
    }


def build() -> dict:
    obs = read_json(SOURCES["observatory"])
    notices_doc = read_json(SOURCES["notices"])
    companies_doc = read_json(SOURCES["companies"])
    mappings_doc = read_json(SOURCES["mappings"])
    scenarios_doc = read_json(SOURCES["scenarios"])
    notice_by_id = {r["id"]: r for r in notices_doc["records"]}
    notice_index_by_id = {r["id"]: index for index, r in enumerate(notices_doc["records"])}

    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}

    def node(node_id: str, node_type: str, label: str, properties: dict, node_access: dict, prov: dict) -> None:
        item = {
            "id": node_id,
            "stable_id": node_id,
            "type": node_type,
            "label": label,
            "properties": properties,
            "access": node_access,
            "provenance": prov,
        }
        previous = nodes.get(node_id)
        if previous and previous != item:
            raise ValueError(f"conflicting node: {node_id}")
        nodes[node_id] = item

    def edge(source: str, target: str, edge_type: str, properties: dict | None = None) -> None:
        edge_id = f"edge:{short(source + '|' + edge_type + '|' + target)}"
        item = {
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
            "properties": properties or {},
        }
        previous = edges.get(edge_id)
        if previous and previous != item:
            raise ValueError(f"conflicting edge: {edge_id}")
        edges[edge_id] = item

    # Public notice and document projection.
    for index, doc in enumerate(obs["public_documents"]):
        bid = doc["bid_key"]
        notice_id = f"notice:{bid}"
        raw_notice = notice_by_id.get(bid, {})
        node(
            notice_id,
            "ProcurementNotice",
            raw_notice.get("title", bid),
            {
                "notice_id": bid,
                "agency": raw_notice.get("agency"),
                "budget": raw_notice.get("budget"),
                "deadline": raw_notice.get("deadline"),
                "sector": raw_notice.get("sector"),
                "url": raw_notice.get("url"),
                "evidence_scope": "public L1 metadata",
            },
            access("L1"),
            provenance("notices", f"/records/{notice_index_by_id.get(bid, 0)}"),
        )
        document_id = f"document:{doc['document_id']}"
        node(
            document_id,
            "Document",
            doc["filename"],
            {
                "document_id": doc["document_id"],
                "notice_id": bid,
                "chunks": doc["chunks"],
                "security_level": doc["security_level"],
                "body_in_demo": False,
            },
            access("L1"),
            provenance("observatory", f"/public_documents/{index}"),
        )
        edge(notice_id, document_id, "NOTICE_HAS_DOCUMENT")

    # Saved L1 question -> answer -> exact evidence and review projection.
    for case_index, case in enumerate(obs["cases"]):
        qid = f"question:{case['id']}"
        aid = f"answer:{case['id']}"
        notice_id = f"notice:{case['bid']}"
        node(
            qid,
            "Question",
            case["question"],
            {"question_id": case["id"], "notice_id": case["bid"], "mode": case["mode"]},
            access("L1"),
            provenance("observatory", f"/cases/{case_index}/question"),
        )
        node(
            aid,
            "Answer",
            case["answer"][:92] + ("…" if len(case["answer"]) > 92 else ""),
            {
                "question_id": case["id"],
                "notice_id": case["bid"],
                "answer": case["answer"],
                "answer_sha256": case["answer_sha256"],
                "human_approval": case["human_approval"],
                "quality_notes": case["quality_notes"],
                "model_prediction": "not included in this replay projection",
            },
            access("L1"),
            provenance("observatory", f"/cases/{case_index}/answer"),
        )
        edge(qid, notice_id, "QUESTION_ABOUT_NOTICE")
        edge(aid, qid, "ANSWER_RESPONDS_TO_QUESTION")

        for context_index, context in enumerate(case["contexts"]):
            window_id = f"window:{context['chunk_id']}:{context.get('text_start', 0)}:{context.get('text_end', 0)}"
            document_id = f"document:{context['document_id']}"
            node(
                window_id,
                "EvidenceWindow",
                context["text"][:80] + ("…" if len(context["text"]) > 80 else ""),
                {
                    "chunk_id": context["chunk_id"],
                    "document_id": context["document_id"],
                    "document_version": context["document_version"],
                    "filename": context["filename"],
                    "text": context["text"],
                    "character_start": context["text_start"],
                    "character_end": context["text_end"],
                    "citation": context["citation"],
                    "scope": context["scope"],
                    "ranking_scores": "기존 재생 파일에 기록되지 않음",
                },
                access("L1"),
                provenance("observatory", f"/cases/{case_index}/contexts/{context_index}"),
            )
            if document_id in nodes:
                edge(document_id, window_id, "DOCUMENT_HAS_EVIDENCE_WINDOW")
            edge(qid, window_id, "QUESTION_RETRIEVED_EVIDENCE", {"scope": context["scope"]})
            if context["citation"] is not None:
                citation_id = f"citation:{case['id']}:{context['citation']}"
                node(
                    citation_id,
                    "Citation",
                    f"인용 [{context['citation']}]",
                    {"citation_number": context["citation"], "question_id": case["id"]},
                    access("L1"),
                    provenance("observatory", f"/cases/{case_index}/contexts/{context_index}/citation"),
                )
                edge(aid, citation_id, "ANSWER_HAS_CITATION")
                edge(citation_id, window_id, "CITATION_POINTS_TO_EVIDENCE")

        for span_index, span in enumerate(case["spans"]):
            span_id = f"span:{case['id']}:{span['start']}:{span['end']}"
            review_id = f"review:{case['id']}:{span['start']}:{span['end']}"
            node(
                span_id,
                "HallucinationSpan",
                span["quote"],
                {
                    "question_id": case["id"],
                    "label": span["label"],
                    "reason": span["reason"],
                    "character_start": span["start"],
                    "character_end": span["end"],
                    "offset_unit": "Unicode code point; zero-based; end-exclusive",
                    "evidence_binding": "구간별 특정 근거 ID는 재생 파일에 기록되지 않음",
                },
                access("L1"),
                provenance("observatory", f"/cases/{case_index}/spans/{span_index}"),
            )
            node(
                review_id,
                "Review",
                f"검수 초안 · {span['label']}",
                {
                    "review_status": case["human_approval"],
                    "label": span["label"],
                    "actor": "agent draft/review candidate",
                    "human_final": False,
                },
                access("L1"),
                provenance("observatory", f"/cases/{case_index}/spans/{span_index}"),
            )
            edge(span_id, aid, "HALLUCINATION_SPAN_IN_ANSWER")
            edge(review_id, span_id, "REVIEW_REVIEWS_SPAN")

    # Sanitized synthetic-company fixture. It is not real company data and is ACL filtered by the demo server.
    for company_index, company in enumerate(companies_doc["companies"]):
        cid = company["company_id"]
        tenant = company["tenant_id"]
        company_access = access("L2", tenant, ["bid_analyst", "cost_analyst", "bid_approver"])
        company_id = f"company:{cid}"
        node(
            company_id,
            "Company",
            company["company_name"],
            {
                "company_id": cid,
                "tenant_id": tenant,
                "synthetic": True,
                "snapshot_as_of": company["snapshot_as_of"],
                "enterprise_size": company["enterprise_size"],
                "region": company["headquarters"]["region"],
                "specialties": company["specialties"],
                "design_summary": company["design_summary"],
            },
            company_access,
            provenance("companies", f"/companies/{company_index}"),
        )
        for person_index, person in enumerate(company.get("personnel", [])):
            pid = f"person:{person['person_id']}"
            node(
                pid,
                "Person",
                person.get("name", person["person_id"]),
                {
                    "person_id": person["person_id"],
                    "role": person.get("role") or person.get("job_title"),
                    "synthetic": True,
                    "details": "공개 데모에는 합성 식별자와 역할만 포함",
                },
                company_access,
                provenance("companies", f"/companies/{company_index}/personnel/{person_index}"),
            )
            edge(company_id, pid, "COMPANY_HAS_PERSON")
        for project_index, project in enumerate(company.get("projects", [])):
            pid = f"project:{project['project_id']}"
            node(
                pid,
                "Project",
                project["title"],
                {
                    "project_id": project["project_id"],
                    "domain": project.get("domain"),
                    "status": project.get("status"),
                    "completed_on": project.get("completed_on"),
                    "synthetic": True,
                },
                company_access,
                provenance("companies", f"/companies/{company_index}/projects/{project_index}"),
            )
            edge(company_id, pid, "COMPANY_HAS_PROJECT")
        for cert_index, cert in enumerate(company.get("certifications", [])):
            cert_id = f"certification:{cert['certification_id']}"
            node(
                cert_id,
                "Certification",
                cert["label"],
                {
                    "certification_id": cert["certification_id"],
                    "code": cert["code"],
                    "valid_from": cert.get("valid_from"),
                    "valid_until": cert.get("valid_until"),
                    "synthetic": True,
                },
                company_access,
                provenance("companies", f"/companies/{company_index}/certifications/{cert_index}"),
            )
            edge(company_id, cert_id, "COMPANY_HAS_CERTIFICATION")

    for mapping_index, mapping in enumerate(mappings_doc["mappings"]):
        tenant = f"astra-{mapping['company_id'].lower()}"
        mapping_access = access("L2", tenant, ["bid_analyst", "cost_analyst", "bid_approver"])
        req_id = f"requirement:{mapping['mapping_id']}"
        node(
            req_id,
            "Requirement",
            mapping["condition"],
            {
                "mapping_id": mapping["mapping_id"],
                "notice_id": mapping["bid_key"],
                "requirement_class": mapping["requirement_class"],
                "status": mapping["status"],
                "reason": mapping["reason"],
                "follow_up": mapping["follow_up"],
                "scope": mapping["scope"],
                "overall_eligibility": mapping["overall_eligibility"],
                "synthetic_company_assessment": True,
            },
            mapping_access,
            provenance("mappings", f"/mappings/{mapping_index}"),
        )
        relation = {
            "충족": "COMPANY_SATISFIES_REQUIREMENT",
            "미충족": "COMPANY_MISSING_REQUIREMENT",
            "자료부족": "COMPANY_REQUIREMENT_UNRESOLVED",
            "원문충돌": "COMPANY_REQUIREMENT_UNRESOLVED",
        }.get(mapping["status"], "COMPANY_REQUIREMENT_UNRESOLVED")
        edge(f"company:{mapping['company_id']}", req_id, relation, {"status": mapping["status"]})
        notice_id = f"notice:{mapping['bid_key']}"
        if notice_id in nodes:
            edge(notice_id, req_id, "NOTICE_REQUIRES_REQUIREMENT")

    for scenario_index, scenario in enumerate(scenarios_doc["scenarios"]):
        tenant = f"astra-{scenario['company_id'].lower()}"
        scenario_access = access("L2", tenant, ["bid_analyst", "cost_analyst", "bid_approver"])
        sid = f"scenario:{scenario['scenario_id']}"
        node(
            sid,
            "Scenario",
            scenario["scenario_id"],
            {
                "scenario_id": scenario["scenario_id"],
                "notice_id": scenario["bid_key"],
                "company_id": scenario["company_id"],
                "mode": scenario["mode"],
                "status": scenario["status"],
                "decision_as_of": scenario["decision_as_of"],
                "synthetic": True,
            },
            scenario_access,
            provenance("scenarios", f"/scenarios/{scenario_index}"),
        )
        edge(sid, f"company:{scenario['company_id']}", "SCENARIO_FOR_COMPANY")
        notice_id = f"notice:{scenario['bid_key']}"
        if notice_id in nodes:
            edge(sid, notice_id, "SCENARIO_FOR_NOTICE")

    for item in edges.values():
        if item["source"] not in nodes or item["target"] not in nodes:
            raise ValueError(f"dangling edge {item['id']}: {item['source']} -> {item['target']}")

    type_counts: dict[str, int] = {}
    edge_counts: dict[str, int] = {}
    for item in nodes.values():
        type_counts[item["type"]] = type_counts.get(item["type"], 0) + 1
    for item in edges.values():
        edge_counts[item["type"]] = edge_counts.get(item["type"], 0) + 1

    return {
        "schema_version": "1.0.0",
        "projection_kind": "read_only_relationship_visualization",
        "graph_rag": False,
        "run_id": "astra-evidence-graph-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "committed public L1 records plus clearly marked synthetic company fixtures",
        "limitations": [
            "This is a relationship visualization over saved artifacts, not a graph retrieval database.",
            "Lexical, dense and RRF ranking scores were not recorded in the saved replay artifact.",
            "Hallucination span labels are draft/review candidates and await final human approval.",
            "The static public projection contains L1 nodes only; synthetic L2/L3 projection requires the local ACL server.",
        ],
        "source_manifest": [
            {"key": key, "path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)}
            for key, path in SOURCES.items()
        ],
        "statistics": {
            "nodes": len(nodes),
            "edges": len(edges),
            "node_types": dict(sorted(type_counts.items())),
            "edge_types": dict(sorted(edge_counts.items())),
        },
        "nodes": sorted(nodes.values(), key=lambda item: item["id"]),
        "edges": sorted(edges.values(), key=lambda item: item["id"]),
    }


def public_projection(graph: dict) -> dict:
    allowed = {node["id"] for node in graph["nodes"] if node["access"]["level"] == "L1"}
    result = {key: value for key, value in graph.items() if key not in {"nodes", "edges", "statistics"}}
    result["nodes"] = [node for node in graph["nodes"] if node["id"] in allowed]
    result["edges"] = [edge for edge in graph["edges"] if edge["source"] in allowed and edge["target"] in allowed]
    result["scope"] = "public L1 projection only"
    result["statistics"] = {"nodes": len(result["nodes"]), "edges": len(result["edges"])}
    return result


def validate(graph: dict) -> dict:
    node_ids = [node["id"] for node in graph["nodes"]]
    edge_ids = [edge["id"] for edge in graph["edges"]]
    node_set = set(node_ids)
    errors = []
    if len(node_ids) != len(node_set):
        errors.append("duplicate node id")
    if len(edge_ids) != len(set(edge_ids)):
        errors.append("duplicate edge id")
    dangling = [edge["id"] for edge in graph["edges"] if edge["source"] not in node_set or edge["target"] not in node_set]
    if dangling:
        errors.append(f"dangling edges: {dangling[:5]}")
    for node in graph["nodes"]:
        source = ROOT / node["provenance"]["source_path"]
        if not source.exists() or sha256(source) != node["provenance"]["source_hash"]:
            errors.append(f"provenance mismatch: {node['id']}")
    for node in graph["nodes"]:
        if node["type"] == "HallucinationSpan":
            qid = node["properties"]["question_id"]
            answer = next((n for n in graph["nodes"] if n["id"] == f"answer:{qid}"), None)
            start = node["properties"]["character_start"]
            end = node["properties"]["character_end"]
            if not answer or answer["properties"]["answer"][start:end] != node["label"]:
                errors.append(f"Unicode offset mismatch: {node['id']}")
    return {
        "status": "pass" if not errors else "fail",
        "checks": {
            "unique_node_ids": len(node_ids) == len(node_set),
            "unique_edge_ids": len(edge_ids) == len(set(edge_ids)),
            "no_dangling_edges": not dangling,
            "source_hashes_match": not any(e.startswith("provenance") for e in errors),
            "unicode_offsets_match": not any(e.startswith("Unicode") for e in errors),
        },
        "node_count": len(node_ids),
        "edge_count": len(edge_ids),
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without rewriting outputs")
    args = parser.parse_args()
    graph = build()
    report = validate(graph)
    if args.check:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["status"] == "pass" else 1)
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "evidence-graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = public_projection(graph)
    (DIST / "evidence-graph-public.json").write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["full_sha256"] = sha256(DIST / "evidence-graph.json")
    report["public_sha256"] = sha256(DIST / "evidence-graph-public.json")
    (DIST / "evidence-graph-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"full": graph["statistics"], "public": public["statistics"], "validation": report["status"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
