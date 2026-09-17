# ASTRA 내용 확장 발표 초안 v2 출처 목록

이 문서는 초안 슬라이드에 사용한 저장소 내부 근거의 빠른 탐색용 목록이다. 상세한 슬라이드별 수치와 표현 제한은 `ASTRA_최종발표_내용확장_초안_v2_사실검증표.md`를 우선한다.

## 발표 구조와 시각 자료

- `project-docs/PPT_최종발표_제작_인수인계_프롬프트.md`
- `output/visuals/ASTRA_Presentation_Storyboard_AwardStyle.svg`
- `output/visuals/ASTRA_User_Query_Pipeline.svg`
- `output/visuals/ASTRA_Input_Process_Output_Pipeline.svg`
- `project-docs/데모개선/2026-09-14/rag-observatory.png`
- `project-docs/데모개선/2026-09-14/ux-question-workspace/desktop.png`
- `presentations/week3/source/acrc_order_excerpt.png`

## 나라장터 수집·가공·표본

- `project-docs/데이터현황/3개월_통합현황.md`
- `project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md`
- `procurement-pipeline/collector/g2b_rag_pipeline/README.md`

발표의 137,745는 4~6월 공고 차수 포함 행 수이고, 124,522는 최신 차수 기준이다. 첨부 285,252개 중 246,797개를 어댑터 판정상 사용할 수 있었다. 51건은 전체 공고의 성능 표본이 아니라 구조를 점검한 층화 표본이다.

## 합성 기업·권한 정책

- `project-docs/가상기업/v1/README.md`
- `procurement-pipeline/security_schema.py`
- `demo-ui/spatial-poc/live-design/Live_RAG_전환설계.md`

5개 회사, 45명, 16개 프로젝트, 111개 증빙은 합성 데이터다. L2·L3는 실제 기업 내부 문서가 아니며, 발표 자료의 역할 매트릭스는 파일럿 정책이다.

## 색인·검색·생성

- `project-docs/RAG파일럿/v1/index_manifest.json`
- `procurement-pipeline/rag_pilot.py`
- `project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json`

223문서·3,275청크와 7,195 임베딩 window는 서로 다른 단위다. 생성 결과 295건과 정상 접근 차단 5건을 분리해 기록한다. 에이전트의 correct/partial/incorrect 분포는 탐색 결과이며 사람 gold 정확도가 아니다.

## 평가 데이터·사람 검수·탐지

- `project-docs/평가데이터/v2/validation/report.json`
- `project-docs/평가데이터/v2/retrieval_manifest.json`
- `project-docs/환각라벨링/pilot-25-human-review-v1/README.md`
- `project-docs/환각라벨링/detector-300-workstation-v1/README.md`
- `project-docs/환각라벨링/detector-300-workstation-v1/WORKSTATION_PROMPT.md`
- `project-docs/환각라벨링/detector-300-workstation-v1/selected_inputs.json`
- `procurement-pipeline/prepare_detector300_handoff.py`
- `procurement-pipeline/detector300*.py`

25문항 검수와 88개 조정 구절은 사람 최종 승인 전 자료다. KLUE·XLM-R·BGE-M3의 295답변 비교는 885개 실행 슬롯을 준비한 상태이며, 최종 성능 수치는 평가 진행 중으로 표현한다.

## 발표에서 넘지 않는 주장 경계

- 자동 검사 통과를 검색 Recall, 생성 정확도, 탐지 F1 또는 운영 보안 완성으로 바꾸어 말하지 않는다.
- 51건 표본을 전체 나라장터 대표 표본이라고 주장하지 않는다.
- 25문항 검수를 독립 gold test 또는 모델 정확도라고 부르지 않는다.
- 현재 구현을 별도 그래프 DB 기반 GraphRAG라고 표현하지 않는다.
- 미완료 성능은 수치 자리와 평가 방법만 보여주고 `평가 진행 중`으로 표시한다.
