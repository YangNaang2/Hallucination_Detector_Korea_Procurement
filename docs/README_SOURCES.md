# README 출처와 편집 기준

작성일: 2026-09-29. 최종 발표 PPT를 우선 읽고 실제 저장소 문서·코드·결과를 대조했다. 이 작업은 README와 설명 이미지 변경이며 모델 재실행·재평가를 수행하지 않았다.

## 기준 자료

- 최종 PPT: `presentations/final/최종리허설_LastDanceV2!.pptx`, 37슬라이드, 46,970,283바이트.
- SHA-256: `aaf77bf90bce6952d248f5430ec34a80b5015eb7ba608bec103f07d9a0770455`.
- PPT 보관 커밋: `bb6b2ff2c158123eb5b997020f53bbc47801d4be`.
- 구현 점검 기준: `feature/sample-expansion-demo`의 위 커밋과 `origin/main`의 `590aadf`.
- PPT 외부 뉴스·정책 문구는 README의 성능·인증 근거로 사용하지 않았다.
- 종합 보고서는 이전 발표 버전을 바탕으로 만들어진 별도 산출물이다. 이번 37슬라이드 PPT와 동일한 버전으로 취급하지 않았다.

## 화면

PowerPoint에서 해당 슬라이드를 1,600×900 PNG로 내보냈다. 원본 PPT의 텍스트·이미지는 수정하지 않았다.

| 파일 | 원본 슬라이드 | 용도 |
|---|---:|---|
| assets/blue-jay-user-pipeline.png | 13 | 질문부터 근거·탐지 결과까지 사용자 흐름 |
| assets/blue-jay-dashboard.png | 33 | 최종 발표 UI 갤러리 |
| assets/blue-jay-evidence-detection.png | 34 | 문서 등급·출처·형광펜 시연 |

발표 화면을 현재 개발 서버에서 그대로 재현했다고 주장하지 않는다. 로그인 UI와 실제 서버 권한 검증도 분리한다.

## 주요 문구별 근거

| README 내용 | PPT | 저장소 확인 |
|---|---|---|
| Blue Jay 명칭·목표·팀 | 1, 10–13 | 기존 ASTRA 명칭을 유지하는 코드 경로와 구분 |
| 3개월 수집·분야 선정·51건 | 15 | `project-docs/데이터현황/3개월_통합현황.md`, `project-docs/표본_정보시스템/` |
| 가상 회사 5곳·자료 등급 | 11, 15 | `project-docs/가상기업/v1/company_master.json`, `procurement-pipeline/security_schema.py` |
| QAR 300건·회사별 60건 | 15 | `project-docs/평가데이터/v2/evaluation/questions_300.jsonl`, `distribution.json` |
| Parent 1800/240 · Window384/40 | 16–18 | `590aadf:project-docs/RAG파일럿/window384-transition-v1/`, `chunk-ablation-v1/` |
| lexical+dense · RRF · top6 | 19 | `procurement-pipeline/rag_pilot.py`의 후보 필터·순위 결합·겹침 억제 |
| Qwen3-8B 선택 | 20–21 | 발표 선정 결과로 표현. 과거 로컬 개발 서버의 모델과 구분 |
| 생성 근거 최대4 · 이진 탐지 | 22 | 후속 Window384 실행 기록, `src/dataset.py`, `demo/detector.py` |
| 17,537건 · 학습14863/평가2674 | 23–24 | `project-docs/학습과정_상세.md`, `결과분석_및_발표구성.md` |
| XLM-R/KLUE/BGE-M3 Macro F1 | 25 | `project-docs/Claude_인수인계_2026-09-11.md`, `결과분석_및_발표구성.md` |
| 검색 Hit@6 79.79% · MRR0.6096 | 16–18 | `590aadf:project-docs/RAG파일럿/chunk-ablation-v1/README.md`, `summary.csv`; 분모292 |
| 생성295 · 차단5 · 잘못된 인용2 | — | `590aadf:project-docs/RAG파일럿/window384-run-v1/evaluation/final_summary.json` |
| 저장 모드·실제 연결 경계 | 33–36과 별도 | `demo-ui/spatial-poc/integrated_server.py`, `l1_server.py`, `detector_bridge.py`, `팀원배포/dashboard-integration-v1/README.md` |

## 수치 해석

- 실험 모델 간 문맥 길이·윈도우·임계값 조건이 다르므로 공정한 동일 조건 순위로 표현하지 않는다.
- 구조 검사 통과율은 번역 의미 정확도가 아니다. 검색 근거 도달률은 답변 정확도나 환각 탐지 성능이 아니다.
- 100건·80%는 선별된 시연 자료이며 독립 성능 추정치가 아니다. 보관 패키지에는 KLUE 명칭이 있어 이를 BGE-M3의 독립 테스트 결과로 재명명하지 않았다.
- 11%에서2.2%는 가정 계산이다. 실측 서비스 환각 감소율로 인용하지 않았다.
- 질문의 기대답, 생성 답변, 사람 라벨, 최종 승인을 분리한다. 팀 검수25문항과 Window384 실행의 최종 승인 상태는 확인한 파일에서 pending이다.
- 입력 근거 범위 안의 지지 여부를 검증하며, 의심 표시는 확정 오류 판정이나 법적 입찰 적격 판정이 아니다.

## 변경 범위

README, 이 출처 문서, 발표에서 추출한 PNG 3개만 변경한다. 원천·가중치·색인·기존 평가 데이터는 변경하지 않는다. main용 PR은 해당 문서 변경만 담아 기능 브랜치의 다른 변경이 자동으로 합쳐지지 않게 한다.

## 이번 편집 검증

- README의 상대 경로 및 고정 커밋 링크 35개를 Git 객체와 대조: 누락 없음. main 기준으로도 상대 링크 대상 확인.
- 추출 PNG 3개를 직접 확인. PPT 원본 SHA-256 일치.
- 별도 임시 포트·없는 색인 경로·모델 환경변수 제거 상태에서 저장 모드 시작 확인. 질문 화면과 지도 HTTP 200, 상태 API 응답 확인. 모델은 실행하지 않았으며 새 기능 UI 검증이나 재평가를 수행한 것은 아님.
- 기존 서버는 중단하지 않았고, 검사용 프로세스만 종료.
