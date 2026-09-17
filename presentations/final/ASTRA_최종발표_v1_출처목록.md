# ASTRA 최종발표 출처 목록

## 프로젝트 인수인계·구조

- `project-docs/PPT_최종발표_제작_인수인계_프롬프트.md`
- `output/visuals/ASTRA_Presentation_Storyboard_AwardStyle.svg`
- `output/visuals/ASTRA_User_Query_Pipeline.svg`
- `output/visuals/ASTRA_Input_Process_Output_Pipeline.svg`

## 수집·표본·합성 자료

- `project-docs/데이터현황/3개월_통합현황.md`
- `project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md`
- `project-docs/가상기업/v1/README.md`
- `procurement-pipeline/collector/g2b_rag_pipeline/README.md`

## RAG·보안·평가 데이터

- `project-docs/RAG파일럿/v1/index_manifest.json`
- `project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json`
- `project-docs/평가데이터/v2/validation/report.json`
- `project-docs/평가데이터/v2/retrieval_manifest.json`
- `procurement-pipeline/rag_pilot.py`
- `procurement-pipeline/security_schema.py`
- `demo-ui/spatial-poc/live-design/Live_RAG_전환설계.md`

## 환각 라벨·탐지 평가

- `project-docs/환각라벨링/pilot-25-human-review-v1/README.md`
- `project-docs/환각라벨링/detector-300-workstation-v1/README.md`
- `project-docs/환각라벨링/detector-300-workstation-v1/WORKSTATION_PROMPT.md`
- `project-docs/환각라벨링/detector-300-workstation-v1/selected_inputs.json`
- `procurement-pipeline/prepare_detector300_handoff.py`
- `procurement-pipeline/detector300*.py`

## 표현 제한

- 탐지기 성능은 전체 비교 평가와 사람 승인 라벨이 완료되지 않아 수치로 제시하지 않는다.
- RAG 검색 자산과 평가 데이터 300건을 같은 집합으로 표현하지 않는다.
- 합성 기업의 L2·L3를 실제 기업 내부 자료로 표현하지 않는다.
- 파일럿 역할 정책을 운영 인증·인가 완성으로 표현하지 않는다.
- 현재 구현을 별도 그래프 DB 기반 GraphRAG로 표현하지 않는다.
