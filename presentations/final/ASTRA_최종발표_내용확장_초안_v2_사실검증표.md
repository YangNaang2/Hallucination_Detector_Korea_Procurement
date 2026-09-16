# ASTRA 최종발표 내용 확장 초안 v2 · 사실 검증표

기준: origin/feature/sample-expansion-demo cb45470 + presentation/final-deck-v1 후속 개편

| 슬라이드 | 제목 | 근거 | 표현 제한 |
|---:|---|---|---|
| 1 | 표지 | project-docs/PPT_최종발표_제작_인수인계_프롬프트.md | 탐지 성능 우수 또는 운영 완성을 주장하지 않음 |
| 2 | 프로젝트 결과 요약 | project-docs/데이터현황/3개월_통합현황.md; project-docs/RAG파일럿/workstation-275/index_manifest.json; project-docs/평가데이터/v2/validation/report.json; project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json | 탐지 성능은 평가 진행 중 |
| 3 | 발표 흐름 | project-docs/PPT_최종발표_제작_인수인계_프롬프트.md | 구조 안내 |
| 4 | 조달 검토의 복잡성 | project-docs/나라장터_문제정의_1차리서치_팀원용.md; project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md | 자동 적격 판정이나 분쟁 해결을 주장하지 않음 |
| 5 | 공식 사례와 원문 충돌 | presentations/week3/source/acrc_order_excerpt.png; project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md | 12건 전체 셀·법령 검증이 아니라 쟁점 재대조 |
| 6 | 3개월 수집 결과 | project-docs/데이터현황/3개월_통합현황.md | 공고 행은 차수 포함, 사용 가능은 어댑터 판정 |
| 7 | 분야 선택 근거 | project-docs/데이터현황/3개월_통합현황.md | 완전 공고 정의와 확정 집계를 유지 |
| 8 | 51건 표본 구성 | project-docs/데모개선/2026-09-14/existing51-distribution.json; project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md | 확률표본 또는 전체 대표성 주장 금지 |
| 9 | 예산·조건 분포 | project-docs/데모개선/2026-09-14/existing51-distribution.json | 언급 집계와 의무·허용·금지 판정을 구분 |
| 10 | 원문 재대조 원칙 | project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md | 12개 쟁점 범위, 51건 전수 법률 검증 아님 |
| 11 | 가상 기업 원장 | project-docs/가상기업/v1/validation_report.json; project-docs/가상기업/v1/README.md | 모든 회사·인력·실적·인증·원가는 합성 설정 |
| 12 | 기업별 강점과 제약 | project-docs/가상기업/v1/company_master.json; project-docs/가상기업/v1/generated/C01/r1/README.md; project-docs/가상기업/v1/generated/C02-C05/r1/README.md | 합성 설정이며 실제 제출 자료 아님 |
| 13 | L1·L2·L3 색인 | project-docs/RAG파일럿/workstation-275/index_manifest.json | 로컬 실험 색인이며 production index가 아님 |
| 14 | 평가 데이터 300문항 | project-docs/평가데이터/v2/validation/report.json | 300개는 검색 코퍼스가 아님, 사람 승인 pending |
| 15 | ASTRA 전체 구조 | procurement-pipeline/rag_pilot.py; project-docs/RAG파일럿/workstation-275/index_manifest.json | 구축과 질의 실행을 구분 |
| 16 | 사용자 질의 흐름 | procurement-pipeline/rag_pilot.py; project-docs/데모개선/2026-09-15/local-integration/README.md | 파일럿 세션 정책과 운영 인증 체계를 구분 |
| 17 | 역할별 접근 정책 | procurement-pipeline/rag_pilot.py ROLE_LEVELS; project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json | 파일럿 정책, 운영 인증·인가 완성 아님 |
| 18 | 검색 전 ACL 강제 | project-docs/가상기업/v1/validation_report.json; project-docs/가상기업/v1/generated/C01/r1/README.md; project-docs/데모개선/2026-09-14/README.md | 오프라인·파일럿 검사와 운영 보안 검증을 구분 |
| 19 | 정본·청크·offset | project-docs/RAG파일럿/workstation-275/index_manifest.json; project-docs/환각라벨링/detector-300-workstation-v1/README.md | 로컬 실험 색인, production index 아님 |
| 20 | 임베딩 구축 | project-docs/RAG파일럿/workstation-275/embedding_config.json; project-docs/RAG파일럿/workstation-275/validation/vector_validation.json | 임베딩 구축 시간은 해당 워크스테이션 1회 기록 |
| 21 | 하이브리드 검색 | procurement-pipeline/rag_pilot.py; project-docs/평가데이터/v2/retrieval_manifest.json | 별도 그래프 DB 기반 GraphRAG 아님 |
| 22 | 로컬 GPU 생성 | project-docs/RAG파일럿/workstation-275/environment.json; project-docs/RAG파일럿/workstation-275/validation/runtime_tuning.json | GPU 수치는 해당 워크스테이션 실행 기록 |
| 23 | 정본 답변 295건 | project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json | 에이전트 검토를 정확도·독립 테스트 성능으로 표현 금지 |
| 24 | 환각 탐지 설계 | project-docs/환각라벨링/detector-300-workstation-v1/README.md; procurement-pipeline/detector300*.py | 모델 예측과 사람 승인 라벨을 구분 |
| 25 | 25문항 검수 현황 | project-docs/환각라벨링/pilot-25-human-review-v1/validation_report.json; project-docs/환각라벨링/pilot-25-human-review-v1/intake_manifest.json | 의도적으로 고른 개발 자료, 독립 테스트 아님 |
| 26 | 3모델 비교 평가 설계 | project-docs/환각라벨링/detector-300-workstation-v1/README.md; project-docs/환각라벨링/detector-300-workstation-v1/WORKSTATION_PROMPT.md | 성능 숫자·모델 우열 생성 금지 |
| 27 | 대표 오류 사례 | project-docs/환각라벨링/pilot-25-human-review-v1 조정사항 및 검수 산출물 | 대표 조정안이며 최종 사람 승인 pending |
| 28 | 통합 검증 상태 | project-docs/프로젝트_진행현황_팀공유_2026-09-11.md; 각 최신 README와 manifest | 완료·pending·평가 중을 혼합하지 않음 |
| 29 | 데모 화면 | project-docs/데모개선/2026-09-14/README.md; project-docs/데모개선/2026-09-15/local-integration/README.md | 저장 결과 재생을 실시간 생성으로 표현하지 않음 |
| 30 | 결론 | project-docs/PPT_최종발표_제작_인수인계_프롬프트.md; 각 최신 README와 manifest | 목표 미달 범위를 그대로 공개 |
| 31 | 부록 A · 재현성 검사 | project-docs/가상기업/v1/validation_report.json; project-docs/가상기업/v1/generated/C01/r1/README.md; project-docs/RAG파일럿/workstation-275/validation/tests.json; project-docs/데모개선 README | 자동 검사와 모델 성능·운영 보안을 구분 |
| 32 | 부록 B · 발표 수치 원장 | project-docs/데이터현황/3개월_통합현황.md; validation reports; index_manifest; final_summary | 상태 정의를 유지 |
| 33 | 부록 C · 주장 경계 | project-docs/PPT_최종발표_제작_인수인계_프롬프트.md | 검증되지 않은 성능·운영 완성 주장 금지 |
