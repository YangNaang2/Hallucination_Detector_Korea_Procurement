#!/usr/bin/env python3
"""Local demo server with server-side ACL projection for ASTRA Evidence Graph."""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
GRAPH = json.loads((DIST / "evidence-graph.json").read_text(encoding="utf-8"))
ROLES = {
    "viewer": {"levels": {"L1"}},
    "bid_analyst": {"levels": {"L1", "L2"}},
    "cost_analyst": {"levels": {"L1", "L2", "L3"}},
    "bid_approver": {"levels": {"L1", "L2", "L3"}},
}


def allowed(node: dict, role: str, company_id: str | None) -> bool:
    policy = ROLES.get(role, ROLES["viewer"])
    acl = node["access"]
    if acl["level"] not in policy["levels"]:
        return False
    if acl["level"] == "L1":
        return True
    tenant = f"astra-{company_id.lower()}" if company_id else None
    return bool(tenant and acl["tenant_id"] == tenant and role in acl["allowed_roles"])


def project(role: str, company_id: str | None) -> dict:
    visible_nodes = [node for node in GRAPH["nodes"] if allowed(node, role, company_id)]
    visible_ids = {node["id"] for node in visible_nodes}
    visible_edges = [edge for edge in GRAPH["edges"] if edge["source"] in visible_ids and edge["target"] in visible_ids]
    return {
        **{key: value for key, value in GRAPH.items() if key not in {"nodes", "edges", "statistics"}},
        "scope": "server ACL projection; public L1 plus authorized synthetic tenant fixtures",
        "session": {"role": role, "company_id": company_id, "authentication": "demo selector; not production authentication"},
        "statistics": {"visible_nodes": len(visible_nodes), "visible_edges": len(visible_edges)},
        "nodes": visible_nodes,
        "edges": visible_edges,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/evidence-graph":
            query = parse_qs(parsed.query)
            role = query.get("role", ["viewer"])[0]
            company_id = query.get("company_id", [None])[0]
            if role not in ROLES:
                self.send_error(HTTPStatus.BAD_REQUEST, "unknown role")
                return
            if company_id and company_id not in {"C01", "C02", "C03", "C04", "C05"}:
                self.send_error(HTTPStatus.BAD_REQUEST, "unknown company")
                return
            body = json.dumps(project(role, company_id), ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/":
            self.path = "/evidence-graph.html"
        super().do_GET()


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 18772), Handler)
    print("ASTRA Evidence Graph: http://127.0.0.1:18772/evidence-graph.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
