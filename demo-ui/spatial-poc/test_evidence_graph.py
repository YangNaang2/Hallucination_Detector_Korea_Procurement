import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = load_module("build_evidence_graph", HERE / "build_evidence_graph.py")
server = load_module("evidence_graph_server", HERE / "evidence_graph_server.py")


class EvidenceGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = builder.build()

    def test_integrity_and_offsets(self):
        report = builder.validate(self.graph)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertTrue(all(report["checks"].values()))

    def test_stable_ids(self):
        again = builder.build()
        self.assertEqual([n["id"] for n in self.graph["nodes"]], [n["id"] for n in again["nodes"]])
        self.assertEqual([e["id"] for e in self.graph["edges"]], [e["id"] for e in again["edges"]])

    def test_public_projection_is_l1_only(self):
        public = builder.public_projection(self.graph)
        self.assertTrue(public["nodes"])
        self.assertEqual({n["access"]["level"] for n in public["nodes"]}, {"L1"})
        ids = {n["id"] for n in public["nodes"]}
        self.assertTrue(all(e["source"] in ids and e["target"] in ids for e in public["edges"]))

    def test_viewer_receives_no_tenant_nodes(self):
        result = server.project("viewer", "C01")
        self.assertEqual({n["access"]["level"] for n in result["nodes"]}, {"L1"})

    def test_tenant_isolation(self):
        result = server.project("bid_analyst", "C01")
        private = [n for n in result["nodes"] if n["access"]["level"] != "L1"]
        self.assertTrue(private)
        self.assertEqual({n["access"]["tenant_id"] for n in private}, {"astra-c01"})
        self.assertNotIn("company:C02", {n["id"] for n in result["nodes"]})

    def test_question_to_evidence_and_answer_paths_exist(self):
        ids = {n["id"] for n in self.graph["nodes"]}
        adjacency = {node_id: set() for node_id in ids}
        for edge in self.graph["edges"]:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])
        for question in [n for n in self.graph["nodes"] if n["type"] == "Question"]:
            expected_answer = question["id"].replace("question:", "answer:")
            seen = {question["id"]}
            frontier = [question["id"]]
            for _ in range(4):
                frontier = [x for current in frontier for x in adjacency[current] if x not in seen]
                seen.update(frontier)
            self.assertIn(expected_answer, seen)
            self.assertTrue(any(x.startswith("window:") for x in seen))


if __name__ == "__main__":
    unittest.main()
