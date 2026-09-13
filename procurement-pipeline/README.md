# 나라장터 집계 및 보안 등급별 가상 기업 자료 생성

L1 = 공개 입찰공고와 첨부 문서. L2 = 입찰 참여 기업의 내부 실적·인력·인증. L3 = 해당 기업의 원가·투찰전략·협력사 견적.

**L2/L3는 자료 접근 등급이다. 3D 건물·내부 설비 단계와 무관하다.** 이번 코드에서는 3D 장면을 생성하지 않는다.

회사 문서 후속 생성: `generate_c01_documents.py`의 회사별 공통 원장 투영 함수를 일반화하고, `generate_remaining_companies.py`로 C02~C05의 공통·공고별 문서 36개와 청크 140개를 생성했다. [산출물·원문 대조·합성 가정·재현 지침](../project-docs/가상기업/v1/generated/C02-C05/r1/README.md)을 참고한다. `--check`는 저장된 파일을 결정적 재생성 결과와 비교하며 C01 기존 출력도 byte 단위로 검사한다. 실제 DB 적재는 수행하지 않는다.

2026-09-13 평가 데이터 v2: `build_qa300.py`로 회사별 60건, 공고 51건을 포함한 질문·기대답·근거 300건을 생성한다. 기존 25건 + 공개 공고 조건 255건 + 새 합성 시나리오 20건이며, 전부 회사 적격 비교 문항은 아니다. 별도 상태·배치·원가 문서 15개와 청크 106개를 추가하고 v1/r1은 보존했다. [데이터셋·검수·실행 지침](../project-docs/평가데이터/v2/README.md)을 참고한다. `run_qa300_checks.py`는 기존 회귀와 새 오류 주입 검사를 실행해 결과를 기록한다. 사람 승인·실제 RAG 답변·환각 span 라벨링·DB 적재는 미완료다.

Python 3.10 이상, 외부 패키지 설치 불필요. SQLite 기반 로컬 집계다. 실제 수집 파일 구조는 아직 제공되지 않아 아래 manifest 입력 계약을 사용한다.

## 1. 입력 계약

JSONL 한 줄은 공고 한 버전이다. UTF-8 CSV도 지원하지만 attachments 열은 JSON 배열 문자열이어야 한다.
정정공고의 이전/최신 버전을 임의로 합치지 않는다. **집계 단위는 공고 ID + 버전**이므로 고유 공고 수와 다를 수 있다.
최신 버전만 분석하려면 팀 수집 단계에서 최신 유효 버전으로 필터링한다.

```json
{"notice_id":"202605-00001","version":"01","sector":"AI·빅데이터","month":"2026-05","title":"데이터센터 증설","agency":"발주기관","budget_krw":1450000000,"deadline":"2026-07-30","location":null,"attachments":[{"document_id":"doc-001","name":"제안요청서.pdf","kind":"rfp","path":"files/rfp.pdf","sha256":"파일의 실제 SHA256","download_status":"ok","parse_status":"ok","integrity_ok":true,"text_path":"parsed/rfp.jsonl"}]}
```

- `sector`: 팀에서 사용하는 산업 분류. 값이 없으면 미분류이며 추천 제외. 공사/물품/용역처럼 대분류만 있으면 그 수준에서 집계된다. 상세 산업 분류를 임의로 추정하지 않는다.
- `integrity_ok`: 수집/파싱 담당자가 실제 파일 검사 후 설정. 단순히 파일이 있다는 이유로 true를 넣으면 안 된다. 이 코드가 PDF 구조를 자체 검사하는 것은 아니다.
- `path`, `text_path`: `--root` 아래 상대경로. 외부 경로는 사용하지 않는다.
- 같은 공고 안에서는 SHA256 우선, 없으면 파일 경로/문서ID 기준으로 중복을 제거한다. HWP/PDF 내용이 동일한지는 상위 전처리에서 판정해야 한다. 원본은 삭제하지 않는다.
- 같은 공고 ID+버전의 완전 중복 행은 1회 집계. 내용이 다른 행은 오류로 중단하므로 분할 수집 manifest를 먼저 병합한다.
- 첨부 누락 공고도 manifest에 남겨야 전체 분모와 누락률을 알 수 있다.

파서 결과 `parsed/rfp.jsonl`의 각 줄:

```json
{"page":4,"section":"제4조 납품규격","text":"서버 랙 50식을 설치하여야 한다."}
```

HWP/PDF 파싱·OCR은 **이전 단계**다. 파싱 산출물에 페이지와 조항을 유지한다.
좌표가 확인된 경우에만 다음 입력을 허용한다. 발주기관 주소를 사업장 주소로 대신 사용하지 않는다.

```json
{"lat":37.208,"lng":127.067,"alt":null,"kind":"execution_site","verified":true}
```

위 숫자는 형식 예시다. 실제 위치는 별도 지오코딩·검증이 필요하다. 미확인 좌표는 출력 null, needs_geocoding=true.

## 2. 로컬 집계와 대표 표본

```bash
python prepare.py --input /data/manifest.jsonl --root /data --out out --n 40 --min-sector 30
```

출력:

- `sector_report.csv/json`: 분야별 공고 수, 첨부 수, 사용 가능 문서 수, 핵심 3종 확보 수/비율, 추천 점수.
- `audit.sqlite`: 원천 메타데이터와 검사 결과의 디스크 인덱스. 재실행하면 이 도구의 notices 테이블을 재구축한다.
- `sampling.json`: 선택된 공고 ID, 표본 선정 방식, 전달할 글자 수.
- `packets.jsonl`: 모델에 전달할 근거 묶음.

핵심 그룹: **입찰공고 / 제안요청(RFP) / 과업·규격 문서**.
통합 문서가 여러 그룹에 해당할 수 있다. 세 개의 별도 파일을 반드시 요구하는 기준이 아니다.
**완전 공고 = 공고문 1건 + 요건 문서(제안요청서 또는 과업·규격서) 1건 이상.**
2026-05 실데이터 표본에서 세 종류가 모두 있는 공고는 드물었고(5건 중 0건), 공고문+제안요청서 또는 공고문+과업지시서 구성이 일반적이라 이렇게 정했다.
12대 문서 이름은 서로 겹치는 분류이며 모두 별도 파일로 존재해야 하는 조건이 아니다.

파일 존재·크기, download_status=ok, parse_status=ok, integrity_ok=true, 파서 결과 존재를 모두 요구한다.
이는 **구조적 가용성**이다. 본문 내용이 완전한지, 스캔 표가 빠졌는지는 추가 품질검사가 필요하다.

추천 조건: 미분류 제외, 분야 모수 30 이상, 완전 공고 N개 이상. `--business 용역` 을 주면 그 업무구분 안에서만 추천한다.
점수 = 완전 공고 비율의 Wilson 95% 하한 × 0.8 + 사용 가능 첨부 비율 × 0.2. **점수는 자격 판단용이고, 적격 분야끼리는 완전 공고 수가 많은 순으로 추천한다.**
(2026-05 실데이터에서 비율만 쓰면 135건짜리 물품 소분야가 1,096건·3,063건 용역 분야를 제치고 1위가 됐다.)
분야를 사람이 정했으면 `--sector "용역·SW 및 시스템 개발"` 처럼 지정한다. 적격 미달이어도 경고만 내고 그대로 뽑는다.
몇 개만 수집된 분야의 100% 비율에 과도한 점수를 주지 않는다. 조건 미달이면 추천을 보류한다.
분야별 필수 문서 관행이 다르므로 최종 타깃은 사람이 확인한다. 3D 시각화 적합성을 직접 측정한 점수는 아니다.

선택은 월·기관·예산 자릿수 구간별 순환 추출(고정 seed 해시 정렬)이다.
**시연 다양성을 위한 표본이지 모집단 비례 평가 표본은 아니다.** 평가셋은 따로 추출한다.
공고당 850자 구간, 150자 중첩. 규격·수량·자격 등 키워드 구간을 우선하며 문서별 순환 선택한다.
최대 본문 10,000자/공고. 전체 요건의 완전한 추출을 보장하지 않으며 표·예외 조항은 사람 검토 대상이다.

## 3. LLM 요청 준비 및 실행

먼저 **네트워크 호출 없이** 요청 파일과 plan.json을 생성한다.

```bash
python generate.py --packets out/packets.jsonl --out generated --model YOUR_MODEL
```

검토 후 이미 실행 중인 로컬 추론 서버로 전송:

```bash
python generate.py --packets out/packets.jsonl --out generated --model YOUR_MODEL --base-url http://localhost:8000/v1 --execute --workers 1
```

서버 시작/모델 설치는 포함하지 않는다. `YOUR_MODEL`은 서버에서 실제 서비스하는 모델명으로 바꾼다.
클라우드/사내 HTTPS endpoint도 지정 가능. 인증키는 환경변수 `LLM_API_KEY`에서만 읽는다.
이 인터페이스는 [Hugging Face TGI Messages API의 Chat Completions 규격](https://huggingface.co/docs/text-generation-inference/messages_api)을 따른다.
모델은 순수 JSON 출력을 지원해야 한다. JSON 문법·원문 인용 검사 실패는 성공 처리하지 않는다.

여기서 Batch는 **작업 큐를 제한된 동시성으로 실행**한다는 뜻이다. 특정 클라우드 할인 Batch API는 아니다.
기본 40건, 동시 1개, 재시도 2회(최대 120 요청). 성공 결과는 요청/모델/endpoint 해시로 저장되어 재실행 때 건너뛴다.
실패는 errors/, 전체 상태는 run_report.json. 서버가 생성 후 응답을 잃으면 재시도 비용이 발생할 수 있다.

공고당 직렬화 입력 45,000바이트 제한, 출력 3,000토큰 제한.
**바이트 수는 토큰 수가 아니다.** 사용 모델 tokenizer로 입력 크기를 확인하고 문맥창에서 출력 여유를 확보한다.
짧은 컨텍스트 모델은 prepare --max-chars 값을 줄인다. 실제 usage는 성공 결과의 generation에 기록된다.
현재는 공급자별 토큰 단가를 추정하지 않는다. plan.json은 요청 수/상한을 검토하기 위한 것이다.

## 4. 생성 결과와 권한 적용

`generated/results/*.json`의 schema_version은 2다.

- `public_notice`: security_level=L1, 원래 공고 메타데이터.
- `company`: 공고별 가상 기업 ID 및 이름. synthetic=true.
- `records`: security_level=L2/L3, tenant_id, 자료 종류·제목·본문.
- `scenario_reference`: 합성의 배경으로 참고한 L1 원문 인용 및 위치.
- `review`: 사람 검토 필요. 입찰 자격 판정은 수행하지 않음.

**L1 인용은 가상 기업 실적·원가가 사실이라는 증거가 아니다.** 가상의 실적·인력·금액은 모두 합성 가정이며 실제 기업 자료와 혼합하지 않는다. 원문 인용 문자열 일치만 자동 검증하며, 금액 일관성·현실성·민감정보 포함 여부는 검토 후 확정한다.

기존 `generate.py` / `security_schema.py`는 공고별로 별도 가상 기업을 생성하는 초기 방식이다. **51건 기반 공통 기업은 [가상기업 v1 마스터](../project-docs/가상기업/v1/README.md)를 사용한다.** 회사 5곳의 사실은 이 원장에 고정하고 공고별 배치·원가·투찰안만 별도로 연결한다. 기존 생성기는 새 마스터를 자동으로 읽지 않으므로, 새 회사 자료 생성에 그대로 실행하면 안 된다. 후속 연결 시 `tenant_id`, 문서 생성 목록, `generated_document.schema.json`을 적용한다.

새 설계의 5개 질문·기대답은 `evaluation/`에 분리되어 있으며 RAG 입력이 아니다. 실제 생성 답변이나 환각 span 레이블은 아직 없다. 원장·문서 목록·조건 연결과 검증 예시는 작성되었지만 전체 L2/L3 문서, 질문 300건, 서비스 권한 연동 완료를 뜻하지 않는다.

C01 시범 문서는 `generate_c01_documents.py`가 원장 투영으로 생성한다. [시범 결과와 재현 절차](../project-docs/가상기업/v1/generated/C01/r1/README.md)에 공통 문서 5개·청크 27개·질문 근거 연결이 있다. `python generate_c01_documents.py --check`로 저장된 결과를 검증할 수 있다. L2/L3 청크에는 접근 메타데이터가 있으며 아직 검수 승인·실제 색인은 하지 않았다. 이 생성기는 외부 LLM을 호출하지 않고 기존 공고별 생성기와 독립적이다.

권한은 서버에서 **로그인 사용자 + 회사(tenant) 일치 + 해당 문서 접근 권한**을 확인해야 한다. 다른 회사의 L3 권한을 가진 사용자가 우리 회사 L2를 볼 수 있는 것이 아니다. 발주기관 역시 입찰 기업 내부 자료를 자동으로 보지 못한다.

이 스크립트는 분류 메타데이터만 생성한다. 실제 인증/인가를 구현하지 않는다. 검색 전에 권한을 제한하고 그래프·원문 뷰어·다운로드·캐시·로그에도 적용해야 한다. 프론트엔드 필터만으로 보안을 구현하면 안 된다. 생성 결과를 공개 dist 폴더에 복사하지 않는다.

3D 위치와 건물·설비 표현은 나중에 별도 scene 데이터로 연결한다. 기존 ASTRA UI/API에 자동 연결된 상태는 아니다.

## 5. 실제 수집기 출력 연결 (adapt_g2b.py)

팀 수집기(`narajangteo_ingest.py`)는 월 폴더에 `bids.jsonl`(API 원본), `manifest.jsonl`(첨부 처리 이력), `chunk_ready.jsonl`(선택 문서),
`raw/<sha2>/<sha256>.<ext>`(원본), `parsed/<sha256>.json`(text + blocks)을 만든다. 공고별 폴더가 아니라 해시 기반 평탄 구조다.
`adapt_g2b.py`가 이것을 위 입력 계약으로 바꾼다. 원본을 옮기거나 지우지 않고 `<월 폴더>/adapter/`에만 쓴다.

```bash
# 데이터가 있는 워크스테이션에서, procurement-pipeline 폴더에서 실행
python adapt_g2b.py --src /data/g2b/nara/2026-05
python prepare.py --input /data/g2b/nara/2026-05/adapter/manifest.jsonl --root /data/g2b/nara/2026-05 --out out/2026-05 --n 40 --min-sector 30
```

- 공고번호별 **최신 차수만** 남긴다(정정·재공고의 이전 차수 제외). 전부 남기려면 `--all-versions`.
- `sector` = 업무구분·세부분류. 용역은 공공조달 중분류(`pubPrcrmntMidClsfcNm`), 물품은 세부품명, 공사는 주공종명. 세부분류가 없으면 업무구분만.
- `kind` = 파일명 규칙 분류: notice / rfp / spec / eval / contract / estimate / form / other. 파일명이 애매하면 other가 되므로 표본 확정 전에 사람이 확인한다.
- `integrity_ok` = manifest status=parsed + raw·parsed 파일 실재 + 본문 100자 이상 + parse.quality ≥ 0.9(`--min-quality`). 내용의 완전성은 보장하지 않는다.
- `skipped_duplicate`(같은 이름의 다른 형식)는 첨부 목록에서 빼고 `adapt_report.json`에만 집계한다. `low_quality`/`failed`/`unsupported`는 첨부로 남기되 usable=false.
- 텍스트: PDF는 페이지 단위, HWP는 줄바꿈 없는 문단 하나라 `제N조`, `1.`, `Ⅰ.`, `□` 같은 제목 패턴으로 나누고 3,000자 초과분은 문장 끝에서 자른다. `section`은 구간 첫 30자.
- `adapt_report.json`: 상태별·종류별·분야별 집계, 파일 누락 수. 워크스테이션에서 이 파일과 `out/2026-05/sector_report.csv`만 공유하면 된다.

## 6. 실제 데이터 없이 먼저 테스트

```bash
python -m unittest -v test_pipeline.py
python make_example.py
python prepare.py --input example_input/manifest.jsonl --root example_input --out out --n 4 --min-sector 3
python generate.py --packets out/packets.jsonl --out generated
```

샘플은 모두 가상이며 집계/청킹/요청 준비를 검증하는 8건이다. 대규모 실제 처리 시간과 LLM 생성 품질은 실제 데이터·서버에서 별도 측정해야 한다.
