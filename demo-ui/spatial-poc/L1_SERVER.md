# 공개 L1 로컬 질문 서버

## 이번 완료 범위
기존 51건의 공개 색인 → 공고별 키워드 검색 → 테스트/향후 모델 어댑터 → NDJSON → 질문 화면.
실제 모델 다운로드·시작·추론·E5 임베딩 실행·학습·외부 API 호출은 하지 않았다.
모델 SSE 어댑터는 모의 전송으로만 검사했다. 실제 Qwen 연결 성공 또는 RAG 정확도 측정이 아니다.

## 실행
저장소 루트에서 Python 3.11 이상을 사용한다. 기존 procurement-pipeline 의존성이 설치된 Python 환경을 사용한다.
기존 rag_pilot의 lexical_scores/no_gold/SYSTEM/digest를 재사용한다. import로 기존 실행·평가 함수는 실행하지 않는다.
별도 서버 프레임워크나 모델 라이브러리를 추가 설치하지 않았다.

~~~powershell
# 기본: 공개 L1 서버는 작동하지만 생성은 미연결
python demo-ui/spatial-poc/l1_server.py --port 8768

# 명시적 테스트 생성기. 공고 판단 답변을 생성하지 않음
python demo-ui/spatial-poc/l1_server.py --port 8768 --generator test
~~~

http://127.0.0.1:8768/rag-observatory.html 에서 실행 모드 → L1 테스트 서버 선택 → 질문 → 전송.
테스트 생성 동작에서 정상/지연/오류/빈 응답/시간 초과를 선택한다. 지연 중 취소 버튼을 누를 수 있다.
저장 결과 모드는 별도로 유지한다. 기존 8767 정적 서버도 중단하지 않았다.
터미널 실행은 Ctrl+C로 종료한다. 백그라운드로 실행한 경우 시작 시 받은 PID가 이 서버인지 확인한 후 해당 프로세스만 종료한다.

색인 경로는 --index, manifest는 --manifest로 변경할 수 있다. 기본 경로는 저장소 상대 work/rag-pilot/index.sqlite와 project-docs/RAG파일럿/v1/index_manifest.json이다.
없으면 index missing 상태를 반환하며 질문을 거절한다. 부정합·변조된 색인은 서버 시작을 실패시킨다.
CLI에서 공개 공고 목록과 색인의 51개 ID 집합을 대조한다.

## 처리와 근거 보존
1. 기존 SQLite를 mode=ro, query_only로 읽는다. SQL에서 L1/public/비합성/회사·tenant·시나리오 없음/공고번호·차수 조건을 제한한다.
2. manifest의 문서·버전·메타데이터와 대조한다. 문서별 겹치는 청크를 재조립해 정본 SHA, 문자 위치, 중첩·누락을 검사한다. 연결은 명시적으로 닫는다.
3. 검증된 L1만 메모리의 고정 snapshot으로 보관한다. DB의 L2/L3 payload는 로드하지 않는다.
4. 선택 공고 후보만 기존 한국어 lexical_scores로 점수화한다. 양수 점수에서 최대 3개·총 6,000문자 이하의 완전한 청크를 사용한다.
5. 반환 직전 및 프롬프트 구성 직전에 원래 snapshot의 내용·권한·버전·offset과 다시 대조한다.
6. 실제 생성 프롬프트에 파일명·인용번호·본문을 제공한다. 평가 정답은 입력하지 않는다.

이번 검색은 키워드 방식이며 기존 E5 dense 검색과 동일하지 않다. 토큰이 일부 겹치는 것만으로도 결과가 있을 수 있고 검색 정확도는 별도로 평가해야 한다.
6,000문자 제한은 모델 토큰 문맥 적합성을 보장하지 않는다. 워크스테이션 연결 시 tokenizer 기반 문맥 검사가 필요하다.
정본 해시 일치는 파싱 정확성·문서 간 충돌 해소를 뜻하지 않는다.

## 실제 구현 계약
live-design/l1-contract.ts 및 dist/rag-http.mjs 참조. 이전 /api/v1 설계는 변경 없이 보존했다.
이 버전은 GraphRAG/회사 workspace 없이 공개 L1 요청에 필요한 /api/l1만 구현한다.

|경로|동작|
|---|---|
|GET /api/l1/status|계약 버전, snapshot, 실행 모드, 검색 가능 여부, 로컬 요청 토큰|
|POST /api/l1/answers/stream|JSON 요청, NDJSON retrieval → delta → done 또는 error|
|POST /api/l1/cancel|request_id 취소, 토큰 필요|

필수 요청 필드는 schema_version/request_id/snapshot_id/bid/question이다. 추가 필드는 거절한다.
test_behavior는 test 서버에서만 허용한다. 사용자·회사·역할·보안등급은 받지 않는다. 현재 권한은 서버가 강제하는 공개 L1이다.
seq는 1부터 연속 증가하며 request_id/bid/snapshot/mode를 매 이벤트에 보존한다.
재시도는 새 UUID를 만들고 자동 재시도나 저장 답변 fallback은 없다. 사용한 UUID는 서버 생존 동안 재사용하지 않는다.
동시 질문은 4개, 요청당 처리 제한은 60초, 브라우저 총 대기는 70초다. 모델 소켓 대기는 5초다.
취소는 브라우저 Abort와 별도 취소 요청을 함께 사용한다. 모델 어댑터의 블로킹 읽기는 최대 소켓 대기 후 종료하므로 GPU 작업의 즉시 중단까지 보장하지 않는다.
재시도/오류/빈 응답/취소/시간 초과를 완료 답변으로 바꾸지 않는다. 부분 문자열은 미완료로 표시하고 복사를 비활성화한다.

근거 scope:
- test_input: 실제 검색 후 테스트 생성기에 전달한 근거. 모델 미실행.
- generation_input: 모델 요청용으로 구성한 근거. 요청 실패 시 실제 사용 여부 미확인.
- 실제 model done 성공 때 화면은 생성 입력 근거로 표시한다.
- 기존 저장 예시의 prompt_context와 reference_only_not_in_prompt는 그대로 유지한다.

페이지는 null이다. 현재 원문 다운로드 엔드포인트를 만들지 않았다.
탐지는 항상 not_run이고 새 답변의 spans는 빈 배열·형광펜 비활성이다. 이는 환각 없음 판정이 아니다.

## 로컬 경계
127.0.0.1만 바인딩한다. Host/Origin/Sec-Fetch-Site 검사와 시작마다 변경되는 X-Astra-Token을 사용한다.
CORS 허용 헤더는 없다. 토큰은 같은 출처 status를 읽은 화면 메모리에만 있고 URL/로그에 넣지 않는다.
인증된 사내 서비스나 인터넷 배포용 서버는 아니다. 서로 다른 로컬 OS 사용자 격리·TLS·실서비스 인증은 이번 범위 밖이다.
정적 파일은 DIST 전체가 아닌 STATIC의 파일명 allowlist만 제공한다. 디렉터리 목록·원천·회사 파일·색인 DB·모델·키 경로를 거절한다.
기존 가상 공간 index.html은 이 제한 서버에서 제공하지 않는다. 지도 화면은 유지하며 기존 가상 공간은 원래 정적 서버에서 사용한다.
접근 로그는 비활성화하고 HTTP 오류에 내부 경로·소켓 오류·토큰·질문 전문을 넣지 않는다. 요청/정답은 파일에 자동 저장하지 않는다.
구조 검사만으로 자유서술 원문에 비공개 내용이 전혀 없다는 보장을 하지는 않는다. 기존 L1 원문 분류를 전제로 한다.

## 워크스테이션 후속
1. 이 브랜치의 최신 코드와 원래 색인·manifest를 준비한다. 원천/DB/모델은 Git 커밋 대상이 아니다.
2. 승인된 별도 작업에서 기존 llama.cpp 서버를 루프백으로 실행한다.
3. 서버 프로세스 환경에 ASTRA_MODEL_URL, ASTRA_MODEL_ALIAS, 필요 시 ASTRA_MODEL_TOKEN을 설정한다.
   URL은 http://127.0.0.1:포트 형식만 허용하고 사용자 요청에서 URL/모델을 받지 않는다.
4. python demo-ui/spatial-poc/l1_server.py --generator model 실행.
5. 실제 모델 alias·문맥 크기·최초 토큰 지연·SSE 완료·취소·인용/출처를 소규모로 확인한다.
   이번 5초 소켓 대기/60초 제한이 적합한지 확인하고 변경 시 다시 테스트한다.
6. 실제 생성 결과의 정답성·탐지·L2/L3 인증은 별도 단계다. 이번 범위로 확대하지 않았다.

모델 어댑터는 기존 /v1/chat/completions 형식, 프록시 비사용, 한국어 시스템 지시를 재사용했다.
기존 local_post는 고정 실행 설정·비스트리밍 함수여서 직접 변경하지 않고 SSE 어댑터를 추가했다.
리다이렉트·임의 외부 주소는 금지한다. 실제 모델 probe도 이번에는 수행하지 않았다.

## 검사
~~~powershell
python -m unittest discover -s demo-ui/spatial-poc -p test_l1_server.py -v
node demo-ui/spatial-poc/test-rag-http.mjs
node demo-ui/spatial-poc/test-rag-ux.mjs
node demo-ui/spatial-poc/check-public-notices.cjs
python demo-ui/spatial-poc/check_rag_observatory.py
~~~
test_l1_server의 Fixture/HTTP는 전용 합성 테스트 원문을 사용한다.
LocalIndex만 실제 로컬 51건·167문서·3,002청크를 검사하며 DB 해시 불변을 대조한다.
실제 모델 전송은 unittest mock으로 대체하며 외부 추론은 실행하지 않는다.
