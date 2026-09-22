# ASTRA 질문 중심 데모
작업 저장소: C:/Projects/AI프로젝트/ko-lettucedetect. 기존 feature/sample-expansion-demo에서 작업.
## 사용자 흐름
공고 변경(51건 검색) 또는 지도 → 예시 선택 → 저장 답변 확인 → 인용/출처 드로어.
자유 질문은 입력 가능하나 즉시 생성 서버 미연결을 안내한다. 현재 공개 재생 예시는 4개이며 예시 없는 공고는 빈 상태를 제공한다. URL에는 공고번호만 넣는다. 공고 변경·뒤로가기 시 답변을 초기화한다.

## 구현 구분
|기능|상태|
|---|---|
|51건 탐색·지도 필터·질문 화면 이동|구현|
|4개 저장 답변·정본 복사·근거 드로어|구현|
|제한 Markdown·초안 형광펜|구현, 사람 승인 pending|
|문서 연결망·장식 광점·접기·확대·정지|구현|
|로딩·취소·오류·재시도·자료부족 화면|별도 UI 상태 시연에서만 제공|
|Qwen3-4B|기존 저장 결과의 생성 모델, 현재 실시간 미연결|
|Gemma|미연결, 선택 기능 없음|
|회사·역할 설정|읽기 전용 권한 시연 설정, 실제 인증 없음|
|실제 검색·생성·스트리밍·탐지|향후 서버 연결 필요|

## 코드와 연결 계약
- dist/rag-source.mjs: 저장 모드의 status/examples/ask. 정확한 공고+질문이 일치해야 반환한다. AbortSignal, 요청 epoch/공고 일치 검사를 제공한다.
- dist/rag-render.mjs: 원문 Unicode 코드 포인트를 기준으로 형광펜을 적용한다. 굵게·줄바꿈·목록 들여쓰기만 허용한다. HTML/이미지/링크 실행은 없고 인용은 실제 context 번호에만 연결한다. 주석 span이 Markdown 표기자와 겹치면 표기자를 숨기지 않는다.
- dist/rag-graph.js: 기존 실제 문서 관계와 빛 효과. 새 답변 처리 상태가 아니다.
- 기존 live-design/api.mjs / contracts.ts는 제안 계약이며 실행 중인 엔드포인트가 아니다. createDisconnectedSource는 미연결 상태에서 명시적으로 실패한다.
- validateEvent는 요청/snapshot/순서/기본 이벤트 형태에 대한 선행 가드다. 전체 서버 응답 스키마와 보안 검증이 완료됐다는 의미가 아니다.

실제 연결 시 서버가 세션에서 tenant/역할을 결정하고, 허용 문서만 검색해야 한다. 브라우저에서 임의 회사·역할을 전송해 접근 권한을 얻도록 하지 않는다.
서버에서 notice/version/snapshot을 받아 AskRequest를 만들고 기존 NDJSON ask 어댑터를 연결한다. retrieval→delta→citation→detection→done/error 이벤트를 소비하며 AbortController로 취소한다. request_id/seq/snapshot 가드 외에 전체 스키마·허용 문서·응답 해시·최종 정본과 탐지 span 범위 검증이 필요하다. 불완전/잘못된 스트림은 종료하고 재시도는 사용자 동작으로 처리한다. 현재는 이 연결 경로를 활성화하지 않는다.

## 실행
기존 dist 전용 정적 서버: http://127.0.0.1:8767/rag-observatory.html
새 실행: python demo-ui/spatial-poc/run_demo.py (기본 8765), 이후 /rag-observatory.html.
검사: node demo-ui/spatial-poc/test-rag-ux.mjs
기존 검사: node demo-ui/spatial-poc/check-public-notices.cjs / python demo-ui/spatial-poc/check_rag_observatory.py

## 보존
25문항 배포/라벨 원본, QA300, 회사 자료, 기존 RAG 실행 결과는 수정하지 않았다.
정적 JSON도 변경하지 않았다. L2/L3·전체 원문·모델·비밀키를 추가하지 않았다. 데모 형광펜 JSON은 검색 코퍼스로 사용하지 않는다. 추가49건 선정은 보류 유지.

## 검증
- 자동 검사: 저장 질문/공고 불일치 거절, 취소, 오래된 응답 차단, 이벤트 request/snapshot/seq/type 오류 주입, 위험 HTML/Markdown, 잘못된 인용, Unicode/형광펜, 기존 4개 정본 불변 통과.
- 기존 공개 데이터 9개 테스트와 지도 데이터/복합 필터 회귀 통과.
- 브라우저: 저장 답변, 자유 질문 미연결, 정본 복사, 인용 드로어, Escape 닫기와 인용 버튼 포커스 복귀, 형광펜, 동아보건대 잘림 및 사후 자료 표시 확인.
- 그래프 접기/확대/Escape/광점 OFF, 별도 상태 시연 로딩→취소 및 오류→재시도 확인.
- 모션 줄이기/비활성 탭 코드는 기존 동작을 보존했다. 실제 OS 모션 설정 변경 재현은 하지 않았다.
- 검사 범위는 UI·출처 보존이며 RAG 성능이나 답변 정답률 측정이 아니다. 사람 span 승인은 대기 상태다.

- 추가 브라우저 확인: 지도에서 서비스 인증 필터 5건, 실제 3D 지도 로딩, 선택 공고 질문하기 링크, 예시 없는 대전 K-Health 공고 빈 상태, 빈 입력 안내 확인.
- 노트북 1366×900 및 모바일 390×844에서 확인. 모바일 문서 폭/스크롤 폭 375/375로 가로 넘침 없음. 출처 드로어 내부 스크롤 확인.
- [데스크톱](desktop.png) / [모바일 출처](mobile-source.png). 스크린샷은 실제 로컬 정적 데모이며 실시간 모델 실행 화면이 아니다.
