# ASTRA 최종발표 사실 검증표

기준 커밋: `cb45470` (`origin/feature/sample-expansion-demo`)

| 슬라이드 | 핵심 주장 | 근거 파일 | 판정·표현 제한 |
|---:|---|---|---|
| 1 | 권한형 검색, 로컬 RAG, 구절 단위 검증을 통합한 프로젝트 | `project-docs/PPT_최종발표_제작_인수인계_프롬프트.md` | 제품 목표로 표현. 운영 완성 또는 성능 우수로 확대하지 않음 |
| 2 | 정정공고, 문서 충돌, 평가 기준 불명확성이 검토 부담을 만든다 | `project-docs/나라장터_문제정의_1차리서치_팀원용.md`, 표본 검수 문서 | 정정공고 번호는 저장소 사례 범위 |
| 3 | 검색·생성·권한을 한 요청 흐름으로 연결 | `procurement-pipeline/rag_pilot.py`, `procurement-pipeline/security_schema.py` | 경쟁 제품 성능 비교가 아님 |
| 4 | 권한 확인 → 검색 → 로컬 생성 → 답변 검증 | `procurement-pipeline/rag_pilot.py`, `demo-ui/spatial-poc/live-design/Live_RAG_전환설계.md` | 전체 입찰 적격 판정으로 확대하지 않음 |
| 5 | 검색 자산 223문서·3,275청크, 평가 300건 | `project-docs/RAG파일럿/v1/index_manifest.json`, `project-docs/평가데이터/v2/validation/report.json` | 300건은 검색 코퍼스가 아닌 평가 데이터 |
| 6 | 서버 세션이 검색 범위를 결정 | `procurement-pipeline/rag_pilot.py` | 운영 인증·인가 완성으로 표현하지 않음 |
| 7 | 공고 행 137,745; 첨부 285,252; 사용 가능 246,797; 완전 공고 28,852/14,145/8,082; 표본 51 | `project-docs/데이터현황/3개월_통합현황.md`, `project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md` | 공고 행은 차수 포함. 사용 가능은 파이프라인 판정 기준 |
| 8 | L1 공개, L2·L3 합성, 가상 기업 5곳 | `project-docs/가상기업/v1/README.md`, `project-docs/RAG파일럿/v1/index_manifest.json` | L2·L3는 실제 기업 기밀이 아님 |
| 9 | 300 Q-A-R; 회사별 60; 생성 295; 정상 차단 5; 25문항 검수 접수 | `project-docs/평가데이터/v2/validation/report.json`, `project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json`, `project-docs/환각라벨링/pilot-25-human-review-v1/README.md` | 최종 사람 승인과 training export는 pending |
| 10 | viewer L1, bid analyst L1/L2, cost analyst·bid approver L1/L2/L3 | `procurement-pipeline/rag_pilot.py`의 `ROLE_LEVELS` | 파일럿 정책 구현. 운영 인증·인가는 추가 필요 |
| 11 | BM25 형태 키워드 + multilingual-e5-small + RRF(k=60), top 6, 생성 최대 4 | `procurement-pipeline/rag_pilot.py`, `project-docs/평가데이터/v2/retrieval_manifest.json` | GraphRAG로 부르지 않음 |
| 12 | Qwen3-4B Q4_K_M, 로컬 GPU, 외부 API 미사용; 잘림 4, 인용 오류 1 | `project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json`, 생성 manifest | 생성 품질 이슈를 누락하지 않음 |
| 13 | 실제 생성 근거와 답변을 window·토큰 수준에서 비교하고 문자 오프셋으로 표시 | `procurement-pipeline/detector300*.py`, `procurement-pipeline/prepare_detector300_handoff.py` | 모델 경고와 사람 확정 라벨을 구분 |
| 14 | KLUE·XLM-R·BGE-M3 전체 비교 평가 미완료 | `project-docs/환각라벨링/detector-300-workstation-v1/README.md`, handoff prompt | 모든 성능 칸을 `평가 진행 중`으로 유지 |
| 15 | 모순, 근거 없음, 인용번호 오류 대표 사례 | `results-v4/annotation` 계열 검수·수정 이력 | 에이전트 조정안이며 사람 최종 승인 pending |
| 16 | 세 모델 × 295답변 = 885 실행 슬롯 | detector-300 인수인계 문서와 실행 산출물 | 완료 성능이 아니라 평가 범위로 표현 |
| 17 | 저장 예제, L1 테스트, L2·L3 자유 질문 모드가 다름 | `demo-ui/spatial-poc/live-design/Live_RAG_전환설계.md` | 저장 결과 재생을 실시간 생성으로 표현하지 않음 |
| 18 | 구현 자산과 남은 검증 과제를 함께 공개 | PPT 인수인계 문서와 각 최신 manifest | 탐지/RAG 성능 수치를 새로 만들지 않음 |

## 수치 교차검증

| 항목 | 발표값 | 검증 상태 |
|---|---:|---|
| 4~6월 공고 행 | 137,745 | 확인, 차수 포함 |
| 최신 차수 공고 | 124,522 | 확인, 슬라이드 본문에는 미표기 |
| 전체 첨부 | 285,252 | 확인 |
| 사용 가능 첨부 | 246,797 | 확인, 87% |
| 완전 공고 용역/물품/공사 | 28,852 / 14,145 / 8,082 | 확인 |
| 표본 | 51 | 확인, 월별 17건 |
| RAG 문서/청크 | 223 / 3,275 | 확인 |
| L1 문서/청크 | 167 / 3,002 | 확인, 대본에서는 생략 |
| L2 문서/청크 | 34 / 159 | 확인, 대본에서는 생략 |
| L3 문서/청크 | 22 / 114 | 확인, 대본에서는 생략 |
| 평가 질문 | 300 | 확인 |
| 생성 답변/정상 차단 | 295 / 5 | 확인 |
| 탐지 비교 슬롯 | 885 | 산술 확인, 평가 완료를 뜻하지 않음 |
