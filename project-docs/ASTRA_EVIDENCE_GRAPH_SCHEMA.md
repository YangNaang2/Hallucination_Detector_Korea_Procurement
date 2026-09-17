# ASTRA Evidence Graph 스키마

실행 스키마: `project-docs/ASTRA_EVIDENCE_GRAPH_SCHEMA.json`
생성기: `demo-ui/spatial-poc/build_evidence_graph.py`

## 노드

| 유형 | 의미 | v1 원본 |
| --- | --- | --- |
| `ProcurementNotice` | 나라장터 표본 공고 | public notices |
| `Document` | 공고 첨부 문서 메타데이터 | RAG manifest 공개 투영 |
| `Question` / `Answer` | 평가 질문과 저장 정본 답변 | RAG observatory |
| `EvidenceWindow` | 생성 당시 사용했거나 사후 검수에 추가한 근거 구간 | RAG observatory |
| `Citation` | 답변에 표시된 인용번호 | RAG observatory |
| `HallucinationSpan` | 구절 단위 검수 초안 | RAG observatory |
| `Review` | 에이전트 초안·사람 승인 상태 | RAG observatory |
| `Company` / `Person` / `Project` / `Certification` | 합성기업 증빙 구조 | company master |
| `Requirement` | 합성기업에 대조한 개별 공고 조건 | condition mappings |
| `Scenario` | 합성 입찰 검토 시나리오 | scenario plans |

각 노드는 `id`, `type`, `label`, 자유 형식 `properties`, `access`, `provenance`를 가진다. `provenance`에는 저장소 상대 경로, SHA-256과 JSON 위치가 들어간다.

## 관계

관계 방향은 원본의 의미를 설명하기 위한 방향이며 검색 알고리즘의 실행 순서를 뜻하지 않는다.

| 관계 | 의미 |
| --- | --- |
| `NOTICE_HAS_DOCUMENT` | 공고가 첨부 문서를 가짐 |
| `DOCUMENT_HAS_EVIDENCE_WINDOW` | 문서에 표시 근거가 속함 |
| `QUESTION_ABOUT_NOTICE` | 질문의 대상 공고 |
| `QUESTION_RETRIEVED_EVIDENCE` | 저장 생성/검수 자료에 연결된 근거 |
| `ANSWER_RESPONDS_TO_QUESTION` | 정본 답변의 질문 |
| `ANSWER_HAS_CITATION` / `CITATION_POINTS_TO_EVIDENCE` | 인용번호와 근거 연결 |
| `HALLUCINATION_SPAN_IN_ANSWER` | 검수 구절의 답변 위치 |
| `REVIEW_REVIEWS_SPAN` | 검수 초안과 구절 연결 |
| `NOTICE_REQUIRES_REQUIREMENT` | 공고의 개별 조건 |
| `COMPANY_SATISFIES_REQUIREMENT` | 기록상 개별 하위조건 충족 |
| `COMPANY_MISSING_REQUIREMENT` | 기록상 개별 하위조건 미충족 |
| `COMPANY_REQUIREMENT_UNRESOLVED` | 자료부족 또는 원문충돌 |
| `COMPANY_HAS_PERSON/PROJECT/CERTIFICATION` | 합성기업의 내부 증빙 연결 |
| `SCENARIO_FOR_COMPANY/NOTICE` | 시나리오의 회사·공고 문맥 |

`충족`은 회사의 전체 입찰자격 확정을 뜻하지 않는다. 원본 매핑의 `scope=individual_condition_only`, `overall_eligibility=null`을 보존한다.

## offset

환각 구절의 `character_start`, `character_end`는 Unicode 코드 포인트 기준, 0부터 시작하고 끝은 포함하지 않는다. 생성기는 `answer[start:end] == quote`를 검증한다.

## 의도적으로 만들지 않은 관계

현재 재생 파일은 환각 구절마다 특정 근거 ID를 기록하지 않는다. 그러므로 `SPAN_SUPPORTED_BY_EVIDENCE`, `SPAN_CONTRADICTED_BY_EVIDENCE`와 `SPAN_UNSUPPORTED` edge를 추정해 만들지 않았다. 화면은 라벨과 판단 이유를 보여주되 근거가 직접 연결된 것처럼 표현하지 않는다.
