# ASTRA Evidence Graph 설계

기준일: 2026-09-17
GitHub: <https://github.com/YangNaang2/ko-lettucedetect>
상태: 실제 저장 산출물의 읽기 전용 관계 시각화 v1

## 한 문장 설명

사용자 질문이 어떤 공고·문서·근거를 거쳐 답변으로 이어졌는지, 그리고 어느 답변 구간이 검수 대상으로 지정됐는지를 한 화면에서 추적한다.

## 현재 구현의 경계

이 기능은 **GraphRAG가 아니다.** 기존 lexical 검색, dense 검색, RRF 결합, 권한 필터와 로컬 답변 생성을 변경하지 않는다. 저장된 JSON 산출물을 노드와 관계로 투영해 설명 가능성과 검수 편의성을 높인다. 검색 순위별 점수는 현재 공개 재생 파일에 없으므로 화면에 만들지 않았다.

## 데이터 출처

| 출처 | 사용 내용 | 표시 범위 |
| --- | --- | --- |
| `demo-ui/spatial-poc/dist/rag-observatory.json` | 공개 문서 메타데이터, 저장 질문·답변 4건, 실제 생성 근거, 구절 검수 초안 | L1 |
| `demo-ui/spatial-poc/dist/public-notices.json` | 51개 표본 공고의 제목·기관·예산·일정 | L1 |
| `project-docs/가상기업/v1/company_master.json` | 5개 합성기업의 인력·실적·인증 | 합성 L2 |
| `project-docs/가상기업/v1/condition_mappings.json` | 합성기업과 개별 공고 조건의 충족·미충족·자료부족 매핑 | 합성 L2 |
| `project-docs/가상기업/v1/scenario_plans.json` | 합성 입찰 검토 시나리오 | 합성 L2 |

원본 공고 본문, 전체 색인 DB, 가중치와 private prompt는 그래프 산출물에 포함하지 않는다. 공개 문서 노드는 파일명·문서 ID·청크 수만 가진다. 답변 생성에 실제 사용된 9개 근거 구간은 기존 공개 L1 재생 파일에 포함된 텍스트만 사용한다.

현재 공개 재생 파일은 `ParentChunk`와 embedding window를 별도 객체로 구분해 제공하지 않는다. 따라서 v1은 이를 임의로 둘로 나누지 않고 표시 가능한 구간을 `EvidenceWindow` 하나로 보존한다.

## 사용자 경험

1. **근거 경로**: 질문 → 공고 → 문서 → 근거 구간 → 인용 → 답변을 탐색한다.
2. **환각 검수**: 답변 → 의심 구절 → 에이전트 검수 초안으로 이동한다. 구절별 특정 근거 ID가 원본에 없는 경우 연결을 만들지 않고 `기록되지 않음`으로 표시한다.
3. **공고·기업 조건**: 공고 조건과 합성기업의 충족·미충족·자료부족 판단, 인력·실적·인증을 살펴본다.
4. **전체 구조**: 현재 권한으로 반환된 노드 유형의 전체 관계를 본다.

노드를 선택하면 연결된 항목만 강조되고 오른쪽에 원본 파일, SHA-256, JSON 위치, stable ID가 표시된다. 그래프는 확대·축소, 이동, 노드 드래그, 유형 필터와 통합 검색을 지원한다.

## 권한 처리

`evidence_graph_server.py`가 노드를 반환하기 전에 다음을 검사한다.

- `viewer`: L1만 반환
- `bid_analyst`: L1과 선택 회사 tenant의 L2 반환
- `cost_analyst`, `bid_approver`: L1과 선택 회사 tenant의 L2/L3 반환
- 비공개 관계는 출발점과 도착점이 모두 허용된 경우에만 반환

권한이 없는 노드의 이름, 내용과 연결 수는 API 응답에 포함하지 않는다. 이 서버의 역할·회사 선택은 **데모 세션 선택기**이며 운영 인증 기능은 아니다. 서버 없이 HTML을 열면 `evidence-graph-public.json`의 L1 노드만 표시한다.

## 성능 전략

- 최초 화면에서 탐색 모드와 직접 연결된 노드만 표시한다.
- 전체 구조도는 우선순위에 따라 최대 150개, 다른 모드는 최대 180개로 제한한다.
- 문서 167개를 항상 동시에 그리지 않는다.
- SVG를 사용했으며 현재 공개/합성 데모 규모에 맞춘 선택이다. 수천 개 노드를 한 번에 표시해야 할 때는 Canvas/WebGL과 API 기반 부분 그래프 로딩을 검토한다.

## 검증

`python demo-ui/spatial-poc/build_evidence_graph.py --check`는 중복 ID, dangling edge, 원본 해시, Unicode 구절 offset을 검사한다. `python -m unittest demo-ui/spatial-poc/test_evidence_graph.py`는 stable ID, L1 projection, tenant 격리, 질문에서 답변·근거까지의 경로를 추가로 검사한다.

## 향후 GraphRAG 판단 기준

현재 그래프만으로 검색 정확도가 높아졌다고 말할 수 없다. 그래프 기반 검색은 아래가 별도 실험으로 확인될 때 검토한다.

1. 다중 홉 질문에서 기존 hybrid 검색보다 재현율이 높다.
2. 권한 필터 후에도 관계 탐색이 정확하다.
3. 그래프 구축·갱신 비용이 응답 품질 향상보다 작다.
4. 공고 단위 분할로 평가해 데이터 누출이 없다.

그 전까지 Evidence Graph는 근거 추적과 검수 화면으로 사용한다.
