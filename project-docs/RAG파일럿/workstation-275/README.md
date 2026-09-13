# 워크스테이션 RAG 후속 실행·검수 완료 — 사람 승인 대기

2026-09-14, `rag/workstation-275`. e8d745f 및 origin/main 7902090 이력을 포함한다. 기존 v1 결과·300문항·회사 마스터는 그대로 보존했다. GitHub Release로 원천을 확보했으며 USB 전송을 기다리지 않았다.

## 최종 고유 문항 현황

| 구분 | 기존 v1 보존 | 신규 | 통합 |
|---|---:|---:|---:|
| 고유 문항 |25|275|300|
| 실제 LLM 답변 |20|275|295|
| LLM 없는 정상 권한 차단 |5|0|5|
| 최종 실행 실패·미실행 |0|0|0|

신규 최초 실행은 274개 생성·HTTP500 1개 실패였고, 같은 설정의 명시적 재시도로 실패 문항도 생성됐다. 실패 파일은 남아 있다. 최초 run 총276시도, 검색 수정 후6시도는 동일 질문의 재실행이며 새 질문으로 세지 않는다. GPU 개발 시험4생성과 최종 기존25개 회귀(20개 생성 + 5개 차단)도 통합300에 추가하지 않는다.

신규275개의 모든 최초 최신 답변과 수정후6개를 직접 읽어 에이전트 내용 검토를 완료했다. 최종 선택 결과는 **정상73, 부분충족·추가검토133, 실질오류69**다. 정상은 이 검토에서 핵심 판단·필수조건의 중대한 오류를 발견하지 않았다는 뜻이다. 부분 판정에는 누락, 과도한 보충 설명, 추가 원문 확인이 필요한 주장이 포함된다. 이는 독립적인 단일 조건 정답률이나 환각 탐지 지표가 아니다. **사람 승인 전300개 pending, 환각 span 라벨링 미실시(null)**.

## 실제 환경 및 실행

- Ubuntu22.04.5, Xeon Silver4210R 10코어/20스레드, RAM약62GiB, RTX A5000 24GB.
- 호스트 재부팅 후 드라이버580.178.04 정상. 기존 NVML mismatch는 해소됐다.
- 공식 llama.cpp b10938/f1e44dcc1 Vulkan 실행 파일. 모델37/37레이어 GPU offload 로그와 GPU 이용률100% 표본을 확인했다. 관측 전체 GPU 사용 메모리 최대5588MiB(데스크톱 사용 포함).
- 생성 Qwen/Qwen3-4B-GGUF Q4_K_M, revision bc640142c66e1fdd12af0bd68f40445458f3869b, 가중치SHA 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5.
- E5 multilingual-e5-small revision614241f622f53c4eeff9890bdc4f31cfecc418b3. CPU로 임베딩을 완료했고 생성은 GPU를 사용했다. 임베딩 모델·벡터 재학습/교체 없음.
- GPU 프로필: 단일 모델 4슬롯, 슬롯당 4096 문맥, 최대 생성 768, batch/ubatch 512, f16 KV. 기존 샘플링 유지. 프로필·revision·코드·색인·벡터 해시는 각 state에 저장.
- 최초275개 고정 round-robin 4분할(69/69/69/68). 생성시간 중앙값 약8.5초. 병렬 문항 시간의 합은 벽시계 실행시간이 아니다. 수정6개와 회귀25개는 두 실행기가 같은 서버를 공유했으므로 속도 수치를 단순 비교하지 않는다.
- 외부 추론·유료API·학습·배포는 사용하지 않았다. 인증된127.0.0.1:18769만 사용했다.

## 검증 결과

전체 자동검사 **190개 통과**. 신규275개·수정6개·회귀25개 감사에서 요청ID, tenant/회사/역할/보안등급, 공고차수·시나리오·버전, 원문hash·offset, 실제 프롬프트 연결의 무결성 오류0개. 빈답변0개, 최종실패0개. 차단5개는 LLM 미호출·제한정보 비노출 확인.

신규 최종 답변에는 **출력잘림4개**, **잘못된 인용번호1개**가 남는다. 이들은 실행실패로 바꾸거나 답변을 대신 고쳐 채우지 않았다. 유효한 인용번호도 주장 지지를 보장하지 않는다. 각 문항의 실제 원문 연결은 `evaluation/labeling_handoff.json`에 있다.

원래 25개는 수정 전 dense 검색 문서와 순서가 v1과 전부 일치했다. 이번 수정에서 신규 275개 중 6개, 기존25중2개의 top6순서가 바뀌었다. 수정 후 기존 25개 실제 회귀는20개 생성 + 5개 차단으로 완료했고 별도로 전부 내용검토했다. 원본v1 선택표는 교체하지 않았다.

## 직접 수정 및 재실행

기존 준비 단계의 원자적 저장·체크포인트·명시ID·정답제거·실패재개·원천경로 이식·Decimal 검산을 유지하고 다음을 수정했다.

1. OCR과라이선스, 방문/도착과복구시간, 전자화와면단위가 함께 있는 허용된 원문 조항을 우선한다. 일반 사용권·복구 개요·ERP 단위가 핵심조항을 밀어내는 문제를 줄였다. 정답값이나문항ID를 검색에 넣지 않는다.
2. `P-09` 같은 짧은 인력ID도 이미 권한검사된 회사 청크의 정규ID와 연결한다. 다른 회사의 완전한ID는 치환하지 않는다.
3. 시나리오의 staffing과 state_change를 직원의 일반 가용기간이나 다른 인증보다 먼저 전달한다. 권한·회사·시나리오 필터는 유지한다.
4. 통합 선택·검토TSV·환각라벨링 연결을 생성하는 `finalize_workstation_rag.py` 추가. 최신실패도 선택하고 좋은답변만 남기는 선택을 금지하는 테스트 추가.

모든 300개 요청을 같은 검색기로 재검사해 **순서 있는 top6이 바뀐 전체집합**을 수정영향으로 정했다. 신규 275개 중 6개 전부를 별도 `routing-repair-v2`로 재실행했다. 이 중 방문 2시간/복구 4시간, 72,500면 단위, 서비스 종료일 2027-05-19 근거가 제대로 전달됐다. OCR 영구라이선스 근거도 전달됐으나 모델이 근거 없는 CPU/core 가격 산식을 덧붙였다. 부분월 공수는 정확한 staffing 날짜를 주어도 오답이 남았다. FTE 답변은 재실행에서 더 나쁜 설명을 추가했으며 **그 결과도 최신시도로 선택**했다.

`evaluation/repair_comparison.tsv`에 6문항 수정 전후 실제 문자열·판정·경로가 있다. 전체 275개의 train/validation/test 문항을 실행 후 검토한 다음 검색을 고쳤다. 노출 ID와 split은 `validation/development-exposure.json`에 기록했다. 정답은 실행 후 평가에서만 읽었으며 검색·프롬프트는 정답/금지 주장/평가 레이블을 사용하지 않는다.

## 남은 문제와 사람 검수

- 금지·만료·불포함 근거를 인용하고 첫 결론을 반대로 쓰는 자기모순.
- 판단기준일을 공고일·가격마감일로 치환, 합성 배치일과 근속일 혼동.
- 상한·하한·정확한경계,총예산/입찰금액/청구액/VAT,마진과원가가산 혼동.
- 공고/RFP/메타데이터 차이, 품명·자릿수·연도·지역 조건을 누락하거나 임의확정.
- 내부마스터와시나리오,회사ISO와서비스CSAP,합성 레코드와실제 증빙 혼동.
- 핵심조항 검색누락, 정확한근거를 전달해도 발생하는 모델 오류,무관한 법적효과·자동처리 설명,반복·다국어문자·잘림.

정답에 맞을 때까지 무한 재시도하지 않았다. 모든 사례가 해결됐다고 주장하지 않으며, 부분 판정 133개와 실질 오류 69개를 우선 검토하되 정상 73개도 사람 승인은 필요하다. 기존 25개와 회귀 25개의 남은 오류는 별도 검토표에 있다. 원본 파싱 캐시가 v1과 같다는 것은 원문 추출 정확성을 증명하지 않으며 숫자·표·문서충돌 항목은 원본을 대조해야 한다.

## 주요 산출물

- `evaluation/final_summary.json`: 고유 300개·신규 275개 집계와 선택 규칙.
- `evaluation/effective_results.json`, `effective_review.tsv`: 최종 원시 결과 경로, 실제 답변, 기대답, 에이전트 검토, 사람 승인 상태.
- `evaluation/integrated_status.tsv`: 중복 없는 300문항 상태.
- `evaluation/repair_comparison.json`, `.tsv`: 수정 전후 6문항의 실제 답변 비교.
- `evaluation/labeling_handoff.json`: 답변·실행 파일 해시와 문서 ID·버전·offset·원문 해시 연결. 실제 span은 null.
- `shards/w*/evaluation/`: 최초 276시도와 감사. `repair-v2/evaluation/`: 후속 6시도. `regression/evaluation/`: 기존 25개 회귀 및 개발 시험.
- `validation/final-tests.json`, `routing-impact.json`, `development-exposure.json`, `gpu-ready.json`.
- `resume_state.json`: 실행 완료·사람 승인 대기. 호스트 모델 서버는 사용자가 연 터미널에 남아 있을 수 있다. 지금 Ctrl-C로 종료해도 저장된 결과에 영향이 없다.

## 다른 PC에서 검토·재현

기존 작업을 먼저 보존한 뒤 `git fetch origin`으로 받고 `rag/workstation-275` 브랜치를 검토한다. 이미 같은 브랜치이면 로컬 변경을 보존한 후 `git pull --ff-only origin rag/workstation-275`를 사용한다. 검토만 하려면 Git의 TSV와 원시 결과로 가능하다.

원문·모델·키·벡터 DB·전체 프롬프트는 Git에 없다. 원문 재검증이나 재실행에는 아래 Release와 v1/SOURCE_TRANSFER.md를 따르고, 같은 revision의 모델 및 E5 색인을 별도로 준비해야 한다. 이 PC의 절대 경로를 다른 PC에 그대로 사용하지 않는다.

```bash
gh release download source-transfer-v1-20260913 --repo YangNaang2/ko-lettucedetect --pattern 'astra-source-transfer.zip*' --dir work/source-transfer
```

이 PC에서 결과를 재집계하고 자동검사하기:

```bash
.venv-rag-workstation/bin/python procurement-pipeline/finalize_workstation_rag.py
.venv-rag-workstation/bin/python -m unittest discover -s procurement-pipeline -p 'test_*.py'
```

기존 run은 완료되어 재개할 필요가 없다. 이후 코드나 설정을 바꾸는 실험은 새 run ID와 출력 경로를 쓴다. 전체 프롬프트는 Git에 추가하지 않는다. 사람 승인과 환각 span 라벨링은 다음 단계다.

## 원천 검증·색인


`v1/SOURCE_TRANSFER.md` 지침에 따라 비공개 Release `source-transfer-v1-20260913`의 ZIP 및 체크섬을 수신했다. ZIP SHA-256은 `6d7ccf12f034887204436a19e15f441c3c119d46ac074f504b0cdef62ce0d918`로 지침과 일치한다. checksum 파일의 CRLF 때문에 sha256sum이 파일명 뒤 CR을 읽는 문제는 원본을 수정하지 않고 체크섬 토큰을 읽어 해결했다. ZIP 경로 이탈·심볼릭 링크·기존 파일 충돌과 CRC를 검사한 뒤 압축 해제했다.

실제 source-root는 `work/source-transfer`, 캐시는 그 아래 `source-texts.posix.json`이다. `raw/`나 `export/`를 source-root로 지정하면 안 된다.

- 원본 183개 파일의 크기·SHA, 두 캐시 SHA 검증 통과.
- 원래 캐시와 POSIX 캐시의 차이가 relative 구분자뿐임을 확인. 본문·해시·공고 ID 불변.
- 기준 L1 167개 문서의 정본 텍스트 SHA 전부 일치.
- 재구축 223문서, 3275부모 청크, 기존 제외16개. corpus hash가 기존 v1과 동일.
- record hash 차이도 L1 path의 `/`를 원래 역슬래시로 되돌리면 정확히 기존 해시가 되는 것으로 확인.
- 문서 임베딩은 같은 E5 revision, float32/mean pooling/L2 normalization으로 7195개 토큰 창을 처리한다. 완료·유한값·정규화 검사는 `validation/vector_validation.json`, `embedding_config.json`을 기준으로 한다.

`sources/required.json`, required.tsv, transfer_validation.json에 원본 목록·해시·검증 상태가 있다. 첨부 ID는 이전 manifest에 없어 만들어 넣지 않았다. 기존 제외16개를 정상 파싱한 것으로 바꾸지 않았다. 원천 전체·파싱 캐시·모델·벡터·키·전체 프롬프트는 무시되는 work/에만 있다.
