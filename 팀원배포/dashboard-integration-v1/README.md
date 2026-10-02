# ASTRA 대시보드 개발 패키지 · 2026-09-15

처음 받는 팀원은 [오늘 배포 시작 안내](https://github.com/YangNaang2/ko-lettucedetect/blob/ddcec71d2e2c75a18549943948f916283d92982b/%ED%8C%80%EC%9B%90%EB%B0%B0%ED%8F%AC/dashboard-integration-v1/%EC%98%A4%EB%8A%98_%EB%B0%B0%ED%8F%AC_%EC%8B%9C%EC%9E%91.md)를 먼저 읽습니다. 세 체크포인트 실제 CPU 스모크 결과는 detector-smoke.json, 파일 확인용 해시는 checkpoints.json입니다.

배포 브랜치: feature/sample-expansion-demo. 이 폴더와 해당 브랜치의 저장소가 개발 패키지다. 독립 실행 바이너리나 모델 포함 ZIP이 아니다. 팀원은 GitHub 저장소 접근 권한이 필요하다. main으로 자동 병합하지 않는다.

## 지금 되는 것

| 기능 | 상태 |
|---|---|
| 공고 지도·지역 묶음·금액 필터·저장 결과 | 기존 UI 유지 |
| 공개 L1 선택 공고 검색 | 기존 SQLite 색인 읽기 전용, 키워드 검색. 기존 배치 RAG의 dense 결합 순위와 동일하지 않음 |
| Qwen 실제 생성 | 이 PC의 Qwen2.5-1.5B Q4_K_M / llama.cpp로 HTTP 및 브라우저 실행 확인 |
| Qwen3-4B | 로컬 파일 존재. 이번 통합 실행에서는 사용하지 않음 |
| Llama·Gemma | OpenAI 호환 로컬 SSE 어댑터로 연결 가능. 이번에 설치·실행 검증하지 않음 |
| 환각 탐지 | KLUE·XLM-R·BGE-M3 실제 CPU 추론 및 반환 구절 offset 확인. 현재 서버는 KLUE 사용; 조달 정확도 검증은 별도 |
| 팀 검수 | 25문항·88구절 조정안 조회, 팀/분류/보류/문항 필터, 구절 선택→근거 열기 |
| 최종 사람 승인 | pending 유지. 승인 버튼·원본 수정 기능은 이번에 구현하지 않음 |
| L2/L3 자유 질문 | 미연결. 내부 검수 조회는 별도 키를 요구하는 로컬 개발 기능 |

## 처음 받기

기존 checkout이 있으면 작업을 보존하고 fetch한다. 아래 clone은 새 폴더에서만 실행한다. 실제 회사 키/모델/색인/원천 캐시는 Git에 올리지 않는다.

~~~text
git clone --branch feature/sample-expansion-demo https://github.com/YangNaang2/ko-lettucedetect.git
cd ko-lettucedetect
git switch -c ui/team1-notice
~~~

팀2~4는 아래 담당 지시서의 브랜치를 사용한다. Python 3.10 이상과 Git, JS 테스트용 Node 20 이상을 준비한다. 기본 서버·저장 재생은 Python 표준 라이브러리로 실행할 수 있다.

## 모델 없이 먼저 화면 실행

저장소 루트에서 실행하고 http://127.0.0.1:8769/rag-observatory.html을 연다.

~~~text
python demo-ui/spatial-poc/integrated_server.py --generator disconnected --port 8769
~~~

Windows 편의 실행: pwsh -File demo-ui/spatial-poc/start_integrated.ps1 -Mode disconnected

이 모드는 색인·모델 없이 저장 결과로 UI를 수정할 수 있다. 색인이 없으면 실제 검색과 테스트 생성 모드도 사용할 수 없다. 정상 종료는 서버 터미널에서 Ctrl+C다. 다른 서버 프로세스를 이름만 보고 일괄 종료하지 않는다.

## 실제 생성 연결

Windows 기존 모델 자료가 있을 때:

~~~text
pwsh -File procurement-pipeline/start_rag_pilot_server.ps1 -GenerationModel qwen2.5-1.5b
pwsh -File demo-ui/spatial-poc/start_integrated.ps1 -Mode model -Review
~~~

첫 명령은 기존 GGUF SHA-256을 검증하고 18767에 모델 서버를 실행한다. 두 번째는 실제 모델 설정/토큰을 읽어 8769에서 실행한다. 모델 서버 실행 파일과 GGUF가 Git에 없으므로 clone만으로 이 명령이 성공하지는 않는다. 다른 모델 프로세스가 실행 중이면 기존 스크립트가 교체를 거절한다.

실제 생성은 UI의 실행 모드를 선택하고 질문을 보낸다. 생성 완료 뒤 탐지 설정에 따라 검사한다. 저장 결과의 Qwen3-4B와 현재 Qwen2.5-1.5B의 이름을 섞지 않는다. CPU 지연과 출력 품질은 모델별로 다르다.

모델 종료는 work/rag-pilot/server.pid의 PID와 프로세스 실행 경로가 work/rag-pilot/llama-b10938/llama-server.exe인지 확인한 뒤 해당 PID만 종료한다. 자동으로 외부 접속을 허용하거나 방화벽을 변경하지 않는다.

## 내부 검수

Windows -Review 옵션이 work/internal-review.key를 생성한다. 이 파일을 로컬에서 읽어 http://127.0.0.1:8769/internal-review/의 입력란에 붙여 넣는다. 키를 URL·스크린샷·Git·단체 메시지에 넣지 않는다. 팀원은 자기 PC에서 각자 키를 만든다.

API는 Bearer 키 없이 자료를 제공하지 않는다. 전체 팀의 검수자가 접근하는 개발용 키이며 회사별 인증/RBAC를 구현한 것은 아니다. 자료는 공개 dist에 들어가지 않는다. 원본 검수 파일·정답은 수정하지 않는다.

## Linux / 워크스테이션

기존 워크스테이션 RAG 실행 환경과 원천 전달은 project-docs/RAG파일럿/workstation-275/README.md 및 v1/SOURCE_TRANSFER.md를 따른다. 기존 색인을 다시 만들거나 300문항을 재실행하지 않는다.

1. 현재 작업을 보존하고 이 브랜치를 fetch/checkout한다.
2. 기존 정상 모델 서버를 loopback의 OpenAI 호환 /v1/chat/completions SSE로 실행한다. 기존 start_workstation_rag_server.py의 --help와 실행 기록을 확인한다.
3. 이 폴더의 .env.example을 work/astra.env로 복사한다. 실제 모델 alias/토큰과 경로를 로컬에서 입력한다. 자동 셸 확장은 없으며 값에 따옴표를 붙이지 않는다.
4. 학습한 탐지기 폴더에는 config.json, tokenizer.json 및 *.safetensors가 필요하다. e5는 검색 임베딩이므로 대체할 수 없다. config.architectures가 TokenClassification인지 확인하고 학습 run의 버전·평가 설정도 함께 확인한다.
5. 기존 학습 가상환경에서 torch/transformers/numpy/safetensors를 확인한다. 새 환경이면 GPU에 맞는 torch를 설치하고 procurement-pipeline/requirements-rag-pilot.txt의 의존성을 검토한다. 무조건 현재 모델 환경의 패키지를 덮어쓰지 않는다.
6. ASTRA_DETECTOR_PATH에 확인한 체크포인트 디렉터리, ASTRA_DETECTOR_DEVICE에 cpu 또는 cuda를 지정한다. 학습 때 쓰던 max length와 집계·임계값을 확인한다. 기본 512/min/0.5는 연결용 임시 설정이며 조달 데이터 보정값이 아니다.
7. 실행:

~~~text
python demo-ui/spatial-poc/integrated_server.py --env-file work/astra.env --generator model --index /실제/기존/index.sqlite --port 8769
~~~

Linux 내부 검수 키는 python -c "import secrets; print(secrets.token_urlsafe(32))"로 로컬 생성해 env 파일에 넣는다. 원격 접속·방화벽 개방은 이 패키지 범위가 아니다. 워크스테이션의 로컬 브라우저로 확인한다.

## 대용량 자료와 해시

- GGUF: project-docs/RAG파일럿/v1/runtime/generation_profiles.json에 모델 revision·SHA-256·alias가 있다. Windows 실행기가 해시를 대조한다.
- 원천 전달: 비공개 release source-transfer-v1-20260913의 전달 지침을 사용한다. 저장소 문서의 체크섬 검증·압축 경계 검사를 유지한다.
- 색인: 기존 index.sqlite를 개인 로컬 work 아래에 보관한다. 이 서버는 공개 문서 manifest와 청크·정본 해시를 시작 시 검증한다. 전체 DB를 웹 정적 경로에 노출하지 않는다.
- 탐지 가중치: 사용자가 전달한 세 체크포인트를 확인했다. checkpoints.json의 SHA-256을 수신 파일과 대조한다. 가중치는 별도 전달하며 Git에는 포함하지 않는다. 연결 시 로컬 safetensors 해시가 상태 정보에 포함된다. 최초 학습 산출물의 출처/체크섬과 별도로 대조해야 한다.

## 테스트와 제출

~~~text
python demo-ui/spatial-poc/test_l1_server.py
python demo-ui/spatial-poc/test_integration.py
node demo-ui/spatial-poc/test-rag-http.mjs
node demo-ui/spatial-poc/test-rag-ux.mjs
node demo-ui/spatial-poc/test-detection-http.mjs
~~~

색인이 없는 환경의 실제 51건 검사는 skip일 수 있다. pytest 설치는 필요 없다. 테스트 성공을 모델 정확도라고 보고하지 않는다.

작업은 각자 브랜치에서 커밋/푸시하고 feature/sample-expansion-demo를 대상으로 PR을 만든다. PR에 전후 화면·실행법·테스트·남은 문제를 적는다. 공통 API·권한·모델 설정은 담당자가 단독 수정하지 않고 통합 담당자가 검토한다. 기대답·검수 데이터·원본 답변·회사 마스터는 작업 대상에서 제외한다.
