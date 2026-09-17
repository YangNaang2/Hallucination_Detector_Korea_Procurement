# ASTRA L1/L2/L3 청킹·하이브리드 검색·답변 생성 SVG

비개발자도 권한형 RAG 흐름을 이해할 수 있도록 만든 16:9 SVG 4장이다.

1. L1·L2·L3 문서 등급과 검색 전 권한 검사
2. parent chunk와 embedding window의 차이
3. lexical·dense·RRF 하이브리드 검색
4. 근거 선택·Qwen3-4B 로컬 생성·인용 및 결과 보존

4장은 실제 RAG observatory 화면을 SVG 안에 포함해 단독으로 이동해도 이미지가 깨지지 않는다.

근거: `project-docs/RAG파일럿/workstation-275/index_manifest.json`, `embedding_config.json`, `procurement-pipeline/rag_pilot.py`, `security_schema.py`, workstation 환경·실행 기록.
