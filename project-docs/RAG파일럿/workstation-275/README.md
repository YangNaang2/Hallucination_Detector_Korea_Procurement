# 워크스테이션 후속 RAG — 원천 확보 완료, GPU 재부팅 대기

기준 e8d745f와 최신 origin/main 7902090을 전용 브랜치 `rag/workstation-275`에 보존 병합했다. v1 원본 결과·300문항·회사 마스터는 변경하지 않았다. 이전 원천 입력 대기는 GitHub Release 수신으로 해소됐다. 현재 GPU 드라이버 업데이트를 적용할 호스트 재부팅이 필요하며 신규 275개 LLM 실행은 아직 시작하지 않았다.

## 실제 진행 상태

|구분|기존 v1 유효 결과|신규 275|
|---|---:|---:|
|LLM 답변|20|0|
|정상 권한 차단|5|0|
|실행 실패|0|0|
|미실행|0|275|

기존 두 후속 재실행을 별도 질문으로 중복 집계하지 않았다. 기존 유효 원시 결과의 고유 ID 25개를 전체 300개에서 뺀 대상이 정확히 275개임을 검증했다. 기존 v1 선택표는 그대로이며 이번 개발용 regression 결과를 독립 평가 지표에 합치지 않는다.

CPU 개발 시험은 기존 문항에서 생성 4회(고유 질문 3개), 정상 차단 1회, 의도적 중단 1회를 별도 보존했다. 검색 전용 25개 점검(20 retrieval_only + 5 차단)도 별도다. 신규 275개 실적으로 집계하지 않는다. 생성된 네 답변과 차단 응답을 모두 내용 검토했다. 신규 실제 답변 전체 검수와 환각 span 라벨링은 미실시, 사람 승인은 pending이다.

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

## 환경과 GPU 진단

Ubuntu 22.04.5, Xeon Silver 4210R 10코어/20스레드, RAM 약62GiB. RTX A5000은 커널 정보에서 확인했지만 GPU 실행은 아직 하지 않았다. 별도 `.venv-rag-workstation`에 CPU torch 2.14.0과 지정 의존성을 설치했다. Qwen3-4B Q4_K_M 및 E5는 원래 revision/가중치 해시를 보존했다.

사용자가 호스트 일반 터미널에서 확인한 오류는 `Failed to initialize NVML: Driver/library version mismatch`, NVML 580.178이다. 현재 로드 모듈은 580.173.02, 디스크에 설치된 `/lib/modules/6.8.0-138-generic/updates/dkms/nvidia.ko`는 580.178.04로 확인했다. 시스템 재시작 필요 플래그도 있다. 드라이버 재설치·모듈 강제 제거·재부팅은 수행하지 않았다. [NVIDIA 공식 업데이트 안내](https://docs.nvidia.com/dgx/dgx-os-6-user-guide/upgrading-the-os.html)는 이 오류에 재시작을 안내한다.

Codex 샌드박스에서도 /dev/nvidia*가 보이지 않았다. 장치 쓰기 권한 요청은 샌드박스가 특수 파일 아래 .git/.codex를 만들려다 실패했으며, 다음 turn에서 복구했다. 읽기 권한만 요청해도 장치는 노출되지 않았다. 이 권한 요청을 반복하지 않는다. 재부팅 후 호스트에서 GPU 서버를 실행하고 Codex는 인증된 loopback API로 연결하는 경로를 준비했다.

공식 llama.cpp b10938 Linux Vulkan 자산을 내려받아 Release SHA `cafef1d2cd2e39a94b5493ce0d5b756defce361a23f98c11eb2f9ac7a1b65ef3`를 검증했고 실행 파일 버전 f1e44dcc1/b10938을 확인했다. 이것은 GPU 로딩 완료라는 뜻이 아니다. GPU 런처는 실제 NVIDIA Vulkan 장치가 목록에 있어야 실행하며 그 장치를 명시적으로 선택한다. 로그의 실제 offload와 GPU 메모리·활용률을 확인하기 전에는 가속 성공으로 보고하지 않는다.

## CPU 시험과 수정

구형 노트북용 batch128/ubatch32/q8 KV 설정에서 첫 실제 질문이 280.92초 걸렸다. batch512/ubatch512/f16 KV로 바꾼 동일 질문은 171.36초였다. 두 시행 모두 E5 임베딩과 동시 실행했고 출력 토큰 수/내용도 달라 통제된 모델 성능 비교가 아니다. 모델 가중치·샘플링·질문·토큰 한도는 보존했고 런타임 프로필을 별도로 기록했다. GPU 프로필은 다시 별도 조건이다.

직접 수정한 사항:

- 원자적 문항 저장, 명시 대상 입력, 재개/실패 재시도·설정 해시 검사, 실패를 포함한 최신 시도 선택.
- LLM HTTP 요청 직전 `generation_running` 체크포인트 저장. 중단된 체크포인트를 완료로 오인하지 않도록 재개 시 interrupted로 기록.
- Windows 상대경로와 Linux 경로 호환, CSV CRLF 기록 해시의 정확 재구성 허용. 실제 내용 변경은 거부하며 원천·본문 해시에는 줄바꿈 예외를 적용하지 않음.
- 근거 없는 법적 위반·자동 시스템 동작·중복 결론을 덧붙이지 않도록 프롬프트 보완.
- 권한 확인된 합성 L3 calculation 표에 한해 명시 입력과 알려진 산식으로 Decimal 검산. 원본의 target 결과값은 계산 입력으로 읽지 않음. 매출대비 마진, VAT 변환, 최종 HALF_UP, 선택 협약 항목의 null과 실제0 구분. 알 수 없는 산식·중복 입력·필수값 누락은 검산을 만들지 않음.
- 실측 이후 확대할 수 있도록 단일 모델 서버의 최대4개 슬롯과 고정 round-robin 요청 분할을 준비. 별도 모델4개를 띄우는 방식이 아니다. shard ID 중복/누락·정답 필드 유입 검사를 추가. GPU 소규모 배치 후에만 확대한다.
- audit_workstation_rag.py로 요청·ACL·metadata/hash/offset·실제 비공개 prompt 연결·인용 번호·잘림을 post-run 검사. 인용 번호 유효성을 주장 지지 여부로 간주하지 않음.

최종 자동 검사 177개가 통과했다(`validation/pre-reboot-tests.json`). 전체 색인에서 평가 질문 정확문장 일치0을 확인했다. 실제 CPU 시험의 저장된 검색/프롬프트 감사에서 무결성 오류는 없었다. 이 검사는 답변 정확도를 보장하지 않는다.

## 남은 모델 오류

`regression/evaluation/cpu-smoke-content-review.json`에 전 생성 답변의 에이전트 판정을 기록했다.

- C01-N11-E1: 근거 없는 불법/법 위반 판단을 추가. 다른 CPU 설정에서는 마지막 결론에 원문과 다른 81111592 코드를 생성.
- C01-S01: 원문 note가 기존 마스터 변경이 아니라고 명시해도 기존 원장에 적용된다고 반대로 답함.
- C01-S02: 최종 금액/VAT 숫자는 맞지만, 매출대비15% 마진을 원가에15% 더하는 것처럼 설명. 개별 요건/전체 적격을 구분하지 않아도 된다는 근거 없는 주장도 추가. 정확한 계산 표와 Decimal 검산을 모두 전달한 상태에서 남은 모델 오류다.
- C01-S04: LLM 없는 고정 차단은 정상.

정답에 맞을 때까지 무한 재시도하지 않았다. CPU lexical 시험은 dense 검색의 최종 품질 평가도 아니다. 기존25개 dense 검색 회귀를 완료했고 v1의 검색 문서 ID/순서가 25개 모두 일치했다. 감사 오류도0이다. GPU에서는 영향 문항 생성 검토를 우선하며 새275개 결과를 보고 코드를 수정하면 노출 ID/split과 새 조건을 기록한다.

## 재부팅 후 사용자 단계

임베딩 저장과 현재 작업의 commit/push 완료를 확인한 뒤 다른 열린 작업을 저장하고 워크스테이션을 재부팅한다. 재부팅 후 일반 터미널에서 먼저 `nvidia-smi`가 정상인지 확인한다. 오류가 계속되면 결과를 공유하고 드라이버를 무작정 재설치하지 않는다.

정상이라면 일반 터미널에서 다음을 실행하고 터미널을 유지한다.

```bash
cd /home/piai/Documents/Codex/2026-09-13/files-pasted-by-the-user-ko/ko-lettucedetect
.venv-rag-workstation/bin/python procurement-pipeline/start_host_gpu_rag.py
```

`GPU server ready on 127.0.0.1:18769`가 출력되면 Codex에 알려 준다. 이 런처는 모델/장치를 확인하고 로컬 API 키를 출력하지 않으며, 원문 프롬프트·GPU 로그를 work/에 보관한다. 모델4개가 아니라 Qwen3 하나의4슬롯이다. 슬롯당4096 문맥, 생성768, 기존 샘플링을 유지한다. Ctrl-C는 자신의 서버 프로세스만 종료한다. 드라이버 변경·재부팅·패키지 설치는 하지 않는다.

## 다음 에이전트 실행 순서

1. git status, resume_state.json 및 work/rag-workstation-275/checkpoint.json을 확인한다. e8d745f/7902090 이력 포함과 v1 보존을 확인한다.
2. vector_validation.json, embedding_ready.json과 실제 npz를 대조한다. v1 prepare를 호출하지 않는다.
3. 호스트 GPU 장치 목록, gpu-server.log의 실제 offload, gpu-metrics.csv의 VRAM·사용률, active_generation.json의 모델 SHA/revision/backend를 확인한다. CPU 옵션만 보고 GPU라고 보고하지 않는다.
4. 별도 regression output/work의 dense-preflight-v1 및 dense-baseline-comparison.json(기존25개 검색 동일)을 확인하고, GPU 영향 문항 소규모 생성을 수행한다. 대상25 요청과 질의벡터·색인은 분리 준비되어 있다.
5. GPU 소규모 배치를 실행하고 audit_workstation_rag.py로 감사한 뒤 내용 검토한다. 샘플이 통과하면 limit를 늘린다. 아래 명령은 준비된4개 분할에서 각1개(총4개)부터 시작한다.

```bash
.venv-rag-workstation/bin/python procurement-pipeline/run_workstation_shards.py run --run-id workstation275-gpu-v1 --limit 1
# 다음 배치는 각 shard의 미시도 질문부터 재개한다.
.venv-rag-workstation/bin/python procurement-pipeline/run_workstation_shards.py run --run-id workstation275-gpu-v1 --limit 5
```

분할은 runtime/shard_plan.json의 정확한275개 ID를 네 집합(69/69/69/68)에 고정했다. 기대답·판정에 따라 분할하지 않는다. 각 shard/evaluation의 state와 원시 시도 파일을 보존한다. 실패 재시도는 --retry-failed로 명시하고 이전 실패도 남긴다. 모델/코드/색인/설정이 변하면 새 run ID를 사용한다.

6. 각 shard를 아래처럼 감사한다(w2~w4도 동일). 새275개의 전 질문·실제 답변을 내용 검토하고 날짜·수치·VAT/마진·증빙 상태·보유주체·문서충돌·차수/권한을 확인한다.

```bash
python3 procurement-pipeline/audit_workstation_rag.py --output project-docs/RAG파일럿/workstation-275/shards/w1 --work work/rag-workstation-275/shards/w1 --run-id workstation275-gpu-v1
```

7. 모든275개 최신 유효 시도와 기존25개를 고유ID로 통합한다. 서로 다른 CPU/GPU/코드 조건의 상태 집계와 독립적인 품질 지표를 구분한다. 자동감사·에이전트 내용검토·사람승인을 따로 기록한다. 실제 span 라벨링은 이번에는 수행하지 않고 null로 둔다. 환각 라벨링 후속 단계에는 actual_answer 불변 문자열과 prompt_evidence의 문서/offset 연결을 넘긴다.
8. 허용된 코드·문서·평가 결과만 전용 브랜치에 commit/push한다. 원천·모델·키·벡터·전체 프롬프트·GPU 원시 서버 로그를 Git에 넣지 않는다. main 강제 push/자동 병합은 하지 않는다.
