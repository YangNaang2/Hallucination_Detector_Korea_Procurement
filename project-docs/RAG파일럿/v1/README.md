# ASTRA 로컬 RAG 파일럿

51건 공개 공고와 가상 기업 5곳의 자료를 실제 검색·생성 경로에서 점검하는 개발용 실험이다. 회사 문서는 합성 자료이며 사람 검수 승인은 여전히 pending이다. 운영 서비스·UI 인증 연동·환각 탐지 모델 실행과는 별개다.

## 구성과 입력 경계

- 원천 검토 캐시의 공고별 전체 파싱 텍스트를 사용한다. 평가용 정답 인용을 검색 입력으로 사용하지 않는다.
- L1 167개 문서 / 3,002개 청크, L2 34개 / 159개, L3 22개 / 114개: 합계 223개 / 3,275개. 모든 51개 공고에 읽을 수 있는 자료가 존재한다. 읽을 수 없는 첨부 16개는 `index_manifest.json`에 별도로 남겼다. 첨부 전체 파싱 완료라는 뜻이 아니다.
- 회사 문서는 v2 retrieval_manifest의 기존 41개와 후속 15개 허용 목록만 사용한다. 원장 전체, 평가 JSONL, 검수 결과, 평가용 source bank를 색인하지 않는다.
- 실제 SQLite·벡터·모델·원문 프롬프트는 비커밋 `work/rag-pilot`에 둔다. 이 문서 폴더는 검색 입력이 아니다. 운영 색인은 수행하지 않는다.
- 원천 바이너리 SHA-256과 캐시 연결을 확인했다. HWP 표 병합·스캔 PDF의 내용 완전성까지 보장하는 검사는 아니다.

## 25문항 구성

각 회사에서 공개 공고 조건 1개, 기존 공고–회사 비교 1개, 합성 상태 해석 1개, 원가 계산 1개, 권한 차단 1개를 선택했다. 선택은 검색 결과를 보기 전에 고정했다. 총 7개 공고에 걸쳐 있다.

`evaluation/selection.json`에 ID·선정 이유·유형·역할·시나리오·분할을 기록했다. dev 9개, train 8개, test 8개이며 test 8개는 이번 개발에 노출된 것으로 표시했다. 이후 독립적인 최종 테스트 결과로 재사용하면 안 된다. 기존 300문항과 split은 수정하지 않는다.

`runtime/requests.json`은 `evaluation_request()`의 허용 필드만 담은 로컬 실행 요청이다. 기대답·정답 인용·관리자 비공개 근거는 포함하지 않는다. 이 요청 파일도 검색 자료가 아니다.

## 권한·시나리오

이 CLI의 세션은 검수자가 제공한 오프라인 테스트 픽스처다. 실제 로그인 서버를 구현한 것은 아니다. 질문에 쓰인 역할 변경 문구는 세션에 반영하지 않는다.

인증·활성 소속·tenant·역할별 등급 상한·시나리오 버전·공고를 확인하고 **후보 벡터를 선택한 다음** 유사도를 계산한다. L1은 선택 공고/차수, L2/L3는 허용 회사/역할/버전으로 제한한다. 프롬프트 직전에 허용 청크의 ID·본문·offset·메타데이터를 다시 대조한다. 서버 API를 추가할 때에는 신뢰할 수 있는 로그인 세션을 이 입력으로 연결해야 한다.

기존 context_qa300.select의 전체 문서 제외 정책을 출발점으로 사용하되, 합성 변경 주체를 원장의 정확한 entity Pointer로 찾아 영향받지 않은 인증·실적 청크는 복원한다. 예를 들어 C02 개발 인증의 갱신 가정이 C02 유지관리 인증까지 검색에서 지우지 않는다. 변경 대상의 기존 상태와 새 상태를 무조건 합치지 않는다. 적용일 이전과 만료 이후에는 STATE 가정 문서를 제외한다.

변경된 실적의 과거 금액 등 추가 사실이 필요한 질문은 기존 레코드를 역사적 근거로 구분해 제시하는 확장이 필요할 수 있다. 현재는 변경된 entity 전체를 제외하는 보수적 정책이며 이 한계를 숨기지 않는다.

원가 의도에 대한 간단한 선차단 규칙은 보조 수단이다. 다른 표현을 쓰더라도 문서 ACL이 L3 입력을 막는다. 자연어 의도 검출의 완전성을 주장하지 않는다. 대화 이력·답변·검색 문맥 캐시는 사용하지 않는다. 질의 임베딩 캐시는 질의 텍스트 벡터만 저장하며 세션과 검색 자료를 포함하지 않는다.

## 모델과 검색

현재 PC는 Intel Core Ultra 5 225U, RAM 약 16GB, Intel 내장 그래픽이고 설치된 PyTorch는 CPU 버전이다. BGE-M3/Gemma의 준비된 로컬 가중치는 찾지 못했다. CPU 파일럿용으로 다음을 사용한다.

- 임베딩: [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small/tree/614241f622f53c4eeff9890bdc4f31cfecc418b3), 고정 revision, float32, mask mean pooling 및 L2 정규화. query/passage 접두사 적용.
- 생성: [Qwen3-4B-GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF/tree/bc640142c66e1fdd12af0bd68f40445458f3869b), Q4_K_M, 비사고 모드, [llama.cpp b10938](https://github.com/ggml-org/llama.cpp/releases/tag/b10938). 초기 Qwen2.5-1.5B 시행도 삭제하지 않고 보존했다.
- 현재 재개용 실행 설정: context 4,096, 출력 최대 768토큰, CPU 8스레드, KV cache q8_0. 샘플링과 가중치 SHA는 runtime/generation_profiles.json에 고정한다. CPU 소형 모델이므로 답변 품질과 지연을 별도로 검토한다.
- 원래 계획의 BGE-M3/Gemma 조합에 대한 성능 검증은 아니다. 모델·다운로드 해시·라이선스는 environment.json과 download_manifest.json에 기록한다.

공고 부모 청크는 최대 1,800자, 240자 중첩으로 문서 전체를 포함한다. 문단 끝을 우선하지만 길게 펼쳐진 표와 예외 조항은 인접 구간 확인이 필요하다. 회사 대장은 기존 의미 단위 청크를 온전히 유지한다.

임베딩은 부모 청크 안에서 460토큰 창·420토큰 간격으로 모든 토큰을 읽는다. 최대 512토큰 안에서 처리하고 중간 생략하지 않는다. 작은 창의 최대 유사도를 부모 점수로 사용하며 생성 모델에는 부모 원문과 실제 offset을 제공한다. 토큰 수를 문자 수로 대신하지 않는다.

기준 검색은 한국어 2글자 부분어와 영문/숫자 단어를 사용하는 BM25 형태 점수다. 후속 검색은 E5 cosine과 이 점수의 순위를 RRF(k=60)로 합친다. 검색 top_k=6. 완전한 형태소 분석기는 아니다.

`--purpose`는 질문에 명시된 실적·인력·인증 ID, 드문 업무 용어, 문서의 상태 변경·계산 구획을 이용한다. 정답이나 문항 유형은 참조하지 않는다. 드문 문자 일치 조항을 먼저 보존하고 공고–회사 비교에는 두 출처를 함께 확보한다. 이 규칙도 개발 파일럿에 맞춰 조정했으므로 독립 성능 평가가 아니다.

생성에는 우선 상위 부모 청크 최대 4개를 사용한다. 기술적 해시 ID는 감사 매핑에 보관하고 모델에는 번호를 붙인 원문과 파일명을 전달한다. 실제 문서 ID·버전·위치는 각 번호의 prompt_evidence와 retrieved 기록으로 복원한다.

모델 chat template로 입력 토큰 수를 직접 확인하고 출력 여유를 뺀 context limit을 지킨다. 넘으면 낮은 순위의 부모 청크 전체를 제외하며 회사 entity를 중간에서 자르지 않는다. 실제 전달한 근거와 제외 전 검색 결과를 각각 기록한다.

## 실행 순서

저장소 루트에서 실행한다. 경로는 환경에 맞게 지정한다.

```powershell
python -m venv --system-site-packages .venv-rag-pilot
.venv-rag-pilot/Scripts/python.exe -m pip install -r procurement-pipeline/requirements-rag-pilot.txt
python procurement-pipeline/setup_rag_pilot.py
python procurement-pipeline/rag_pilot.py prepare --source-cache <source-texts.json> --source-root <원천_폴더>
.venv-rag-pilot/Scripts/python.exe procurement-pipeline/rag_pilot_embedding.py
python -m unittest discover -s procurement-pipeline -p test_rag_pilot.py
./procurement-pipeline/start_rag_pilot_server.ps1
python procurement-pipeline/rag_pilot.py run --run-id <새_ID> --dense --purpose --execute
python procurement-pipeline/evaluate_rag_pilot.py <새_ID>
```

PyTorch가 없는 다른 PC에는 해당 하드웨어용 PyTorch도 별도로 설치한다. 모델 다운로드에는 인터넷이 필요하지만 색인·질의 임베딩·답변 생성에는 외부 API를 쓰지 않는다. 서버는 loopback과 로컬 API 키로 제한하고 Web UI 및 prompt cache를 끈다. 키는 work/rag-pilot/server.token에만 두며 출력·커밋하지 않는다.

RAM 부담 때문에 **문서 임베딩 → 25개 질의 임베딩 → 프로세스 종료 → 생성 서버 시작** 순으로 실행한다. 처음에는 두 모델을 동시에 실행했으나 가용 RAM이 약 1.1GiB로 줄어 첫 답변 완료 전에 중단했다. `validation/execution_events.json`에 이 시행과 초기 서버 경로 오류를 기록했다. 실패를 성공한 답변으로 집계하지 않는다.

새 run ID는 기존 결과를 덮어쓰지 않는다. 실행 결과에는 모델 설정·요청·검색 근거 ID와 offset·실제 전달 근거·답변·지연·실패를 남긴다. 긴 원문 프롬프트는 로컬 work에만 둔다. 검토자는 manifest와 원문을 통해 인용을 복원할 수 있다.

## 결과를 읽는 법과 다음 단계

evaluation의 실행별 assessment는 골든 근거와 검색 구간의 교집합·회사 청크 ID를 검사한다. 골든 근거에는 질문에 직접 필요하지 않은 주변 구간과 문서 전체 링크도 있어, 이를 Recall@K나 답변 정확도로 해석하지 않는다. 인용 번호가 존재한다는 검사는 해당 주장을 지지한다는 검사가 아니다.

실제 답변의 수치·증빙·조건 해석·출처 구분은 별도 에이전트 내용 검토 및 사람 검수가 필요하다. 환각 span은 이번에 라벨링하지 않으면 null이다. 25개 테스트로 무환각·무유출을 보장하지 않는다.

300문항 실행 전에는 파싱 불가 첨부, 복합 조건의 근거 검색, 계산 근거 전달, 모델의 한국어 답변 품질을 확인한다. 같은 데이터로 튜닝한 결과와 독립 평가를 구분한다. 300개 실제 답변을 얻은 뒤 그 답변에 대한 환각 구간을 라벨링하고 탐지 모델을 평가한다.


## 사용자 요청으로 일시 중지

현재 상태는 `validation/pause_state.json`에 기록했다. 최종 25문항 시행은 아직 완료된 문항이 없으며, 앞선 소규모 시행의 실제 답변과 시간 초과 결과는 별도 run에 보존했다. 모델 서버와 실행기는 중지했다. 자동 재개는 예약하지 않았다. 사용자의 재개 요청 후 로컬 서버를 시작하고 pause_state의 미완료 ID만 새 run ID에서 실행한다. 전체 실행·답변 내용 검토·최종 집계는 남아 있다.

사용자는 연결 중단이 있었다고 알렸다. 실행 로그만으로 긴 지연을 CPU 연산 시간이나 와이파이 문제 하나로 확정하지 않는다. 재개 후 관측한 지연을 별도로 보고한다. 현재 커밋은 중간 저장이며 파일럿 완료 보고가 아니다.


## 재개 후 문맥 선택 보완

첫 회사 5개 결과를 보존한 뒤 질문 텍스트 기반 문맥 선택을 보완했다. `rag_pilot_routing.py`는 ID만 있는 메타데이터 조각을 문맥에서 제외하고, 회사 상태 질문에는 불필요한 공고 조항을 넣지 않는다. 실적 금액 경계를 묻는 경우 총사업비·빈 서식보다 실적 금액과 이상/이하 등의 조건이 함께 있는 공고 구간을 우선한다. 회사의 명시된 실적과 비교 조항을 입력 앞쪽에 배치한다. 기대답·정답 근거·문항 ID를 이 규칙에서 읽지 않는다. 자연어 규칙이므로 일반 검색의 완전성을 보장하지 않으며 25개 개발 문항에 노출된 보완이다.
