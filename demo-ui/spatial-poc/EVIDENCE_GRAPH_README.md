# ASTRA Evidence Graph 실행

저장된 공고·문서·질문·답변·근거·검수 구간과 합성기업 자료의 관계를 탐색하는 읽기 전용 화면이다. 현재 하이브리드 RAG를 변경하지 않으며 GraphRAG가 아니다.

```bash
python build_evidence_graph.py
python evidence_graph_server.py
```

브라우저에서 <http://127.0.0.1:18772/evidence-graph.html>을 연다. 서버 없이 기존 정적 서버로 열면 공개 L1 projection만 제공된다.

검증:

```bash
python build_evidence_graph.py --check
python -m unittest test_evidence_graph.py
node --check dist/evidence-graph.js
```

세부 설계와 정확성 제한은 `project-docs/ASTRA_EVIDENCE_GRAPH_DESIGN.md`를 참고한다.
