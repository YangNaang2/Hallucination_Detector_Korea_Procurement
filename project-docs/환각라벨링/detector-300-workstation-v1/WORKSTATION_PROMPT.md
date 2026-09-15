너는 ko-LettuceDetect / ASTRA의 환각 탐지 모델 평가 엔지니어이자 데이터 검수 담당자다.
이 워크스테이션에서 기존 300문항의 실제 실행 결과를 기반으로 KLUE·XLM-R·BGE-M3 환각 탐지기 비교와 구절 라벨 초안 구축을 수행해라. 계획만 쓰지 말고 코드·실행·검증·보고서·커밋까지 진행한다.

1. 저장소와 인계 확인
대상 GitHub: YangNaang2/ko-lettucedetect, 인계 브랜치 origin/feature/sample-expansion-demo.
현재 경로·git status·branch·remote를 먼저 확인하고 기존 변경/커밋을 보존한 채 fetch한다. main에 자동 병합하거나 reset --hard로 작업을 지우지 마라. 기존 실행 중 프로세스를 확인하고 다른 작업을 중단시키지 마라.
인계 파일이 없는 브랜치이면 원격 인계 커밋에서 별도 checkout/worktree와 작업 브랜치 eval/detector-300-v1을 만들어 진행한다. 기존 브랜치가 있으면 상태를 확인하고 재사용한다.
AGENTS.md가 있으면 읽고 다음 실제 파일을 읽어라.
- project-docs/프로젝트_진행현황_팀공유_2026-09-11.md 특히7절
- project-docs/환각라벨링/detector-300-workstation-v1/README.md 및 selected_inputs.json
- project-docs/RAG파일럿/workstation-275/README.md와 evaluation/effective_results.json, final_summary.json
- project-docs/환각라벨링/pilot-25-v1 및 pilot-25-human-review-v1의 README·조정안·제출 의견
- project-docs/평가데이터/v2/evaluation/questions_300.jsonl
- demo/detector.py, src/dataset.py, src/evaluate.py, src/eval_window.py, config.py
- demo-ui/spatial-poc/detector_bridge.py, smoke_detector.py
- procurement-pipeline/rag_pilot.py와 기존 근거 복원·권한·라벨링 코드
- 팀원배포/dashboard-integration-v1/checkpoints.json, detector-smoke.json
저장소 루트에서 python procurement-pipeline/prepare_detector300_handoff.py --check를 실행한다. 이 검사는 동결입력 무결성 검사이며 실제 탐지 평가가 아니다.

2. 이번 평가 범위
300레코드 중 실제 답변295건에 대해 탐지기3종을 실행한다(기본885추론 슬롯). 정상 접근차단5건은 탐지 대상에서 제외하고 LLM 미호출·민감정보 노출 여부를 별도 검사한다.
생성 모델 Qwen/Llama/EXAONE 비교는 다른 담당자의 작업이다. 여기서 새 답변을 생성하거나 300문항 RAG를 재실행하지 않는다. 기존 질문·기대답·실제 답변·회사 사실·검수 원본을 수정하지 않는다.
과거 결과는 검색 수리와 재시도가 혼합된 개발 자료다. 탐지기끼리는 동일한 선택 답변/근거를 비교하되 독립 벤치마크 성능이라고 일반화하지 않는다.

3. 실제 모델·환경 확인
OS, GPU모델/VRAM, RAM, 디스크, Python/torch/transformers/CUDA, 기존 학습 환경을 확인한다. 설치된 정상 환경을 우선 사용한다.
학습 체크포인트 klue/xlmr/bgem3 폴더를 로컬 runs·모델 디렉터리와 기존 기록에서 찾는다. 원래 노트북에서는 D드라이브에 있었지만 워크스테이션에 같은 경로가 있다고 가정하지 않는다.
각 config/tokenizer/safetensors 및 학습·평가 기록을 확인한다. 0=SUPPORTED, 1=HALLUCINATED, TokenClassification head와 실제 가중치 로드를 확인한다. e5 검색 임베딩을 탐지기로 쓰지 않는다.
checkpoints.json과 해시를 대조하고 다른 체크포인트면 원인·출처·버전을 별도로 기록한다. 승인 없이 원본 가중치를 변환/덮어쓰거나 임의 원격 코드를 실행하지 않는다.
기반모델·입력 포맷·최대길이·aggregation·임계값·dtype를 실제 코드와 기록에서 확인한다. 기존 데모의 512/min/0.5는 조달 보정값이 아니다. 성능 수치만 보고 서로 다른 실험 설정을 같은 결과로 비교하지 않는다.
없어진 자료는 기존 이전 안내부터 확인하고 끝내 못 찾는 실제 경로/필요 파일만 질문한다. 나머지 입력 준비·평가 코드·테스트는 계속한다. 유료 API·모델 학습·새 대형 모델 다운로드는 이번에 하지 않는다.

4. 정확한 근거 복원
selected_inputs.json의 각 record_path와 answer_sha256를 사용해 정본 답변을 동결한다.
source run의 prompt_evidence, prompt_sha256, 원래 private prompt 캐시, 원래 색인/생성 코드와 비교해 당시 모델에 실제 전달한 업무 근거를 복원한다. retrieved 전체가 최종 prompt_evidence와 같다고 가정하지 않는다. 계산/시나리오 추가 문맥이 있었다면 이를 누락하지 말고 유형과 위치를 기록한다.
청크 ID·citation 순서·원문/문서 버전·정본 offset·text_sha256·company/tenant/보안·scenario를 대조한다. prompt의 system 지시문·정답·판정 rubric을 근거 문서에 넣지 않는다.
기대답 및 사후 발견 원문으로 생성 당시 근거를 바꿔 넣지 않는다. 당시 입력 근거에 대한 지지 여부와 사후 전체 원문 진실성은 별도 평가 축이다.
복원 불가능한 레코드는 coverage/status로 남기고 그 레코드의 정확한 당시근거 평가만 보류한다. 임의 인용으로 메워 전체 완료라고 하지 않는다.
전체 프롬프트·근거 텍스트 캐시는 ignored work에 보관한다. Git에는 짧은 필요한 인용과 해시·참조만 남긴다.

5. 모델 추론 구현
기존 HalluDetector와 학습 입력 형식을 재사용하고 워크스테이션 일괄 실행기를 만든다. 데모처럼 질문마다 모델을 새로 로드하지 말고 한 모델을 GPU에 올려 여러 답변을 처리한다. VRAM에 맞게 microbatch를 조절하고 모델별 순차 실행을 우선한다.
생성된 정본의 Unicode code point [start,end)로 예측을 연결한다. 질문/근거/특수토큰을 답변 환각 구절로 표시하지 않는다. 긴 답변은 답변 분할·근거 window·겹침/확률 집계 규칙을 사전에 버전으로 고정한다. 답변만 보는 추론으로 자동 전환하지 않는다. 미검사 구간을 표시한다.
같은 답변과 업무 근거를 모든 모델에 제공한다. 모델별 원래 지원길이를 사용하는 프로파일과 공통512 조건 비교는 별도 트랙으로 구분할 수 있다. 토크나이저가 다르므로 입력 토큰 수·window 수·실제 검사 커버리지도 남긴다. BGE-M3 긴 입력은 GPU메모리에 맞게 검증한 뒤 사용한다.
모델 예측은 확정정답이 아니다. 점수·구절·검사영역·시간·실패·설정해시·모델해시·run_id를 매 문항 저장하고 중단 후 재개한다. 다른 입력/설정의 결과를 이어붙이지 않는다. 실패 재시도는 attempt로 구분하며 가장 좋은 점수의 결과를 고르지 않는다.
회사별/고위험/장문을 포함한 소수 점검 후 승인 대기 없이 가능한 전체로 확대한다. OOM이면 배치/프로파일을 명시적으로 변경하고 재시도한다. 워밍업·로드·추론시간을 분리한다.

6. 구절 라벨 초안 전수 작성
전체295답변의 근거 일치 여부를 읽고 환각 구절 초안을 만든다. 가능한 한 모델 예측을 보기 전에 별도 파일에 작성해 순환 채점과 편향을 줄인다. 탐지된 구절만 검토하지 말고 정상처럼 보이는 구간도 전체 읽어 놓친 오류를 찾는다.
기존25문항의 제출 의견과 조정안을 정본 해시가 같은 경우 재사용한다. 사람 제출·에이전트 조정·최종 사람 승인을 분리하고 pending을 자동 승인하지 않는다.
각 주장/구절에 supported, contradiction, unsupported, uncertain, citation_error, quality_only를 구분하고 정확한 인용·offset·판단 이유·관련 근거를 남긴다. 인용번호 오류와 내용 환각을 합산하지 않는다.
금액·VAT·경계값·지분·인력 FTE·인증주체·유효기간·합성 사실·자료부족·원문충돌을 특히 검토한다. 애매한 부분을 정상으로 억지 확정하지 않는다.
검수 상태와 답변 전체 검토범위도 기록한다. 미검토 구간을 negative/정상 라벨로 채우지 않는다. 에이전트의 전수 검토를 실제 사람 전수 검수로 표현하지 않는다.

7. 점수·분석
우선 agent_draft/adjudication 기준 잠정 점수와 최종 human-approved 기준 점수를 분리한다. 승인 gold가 없으면 후자는 N/A다.
공통 Unicode 문자 단위 Precision/Recall/F1과 micro 집계, span exact match F1(일대일 동일경계), 답변 단위 환각 포함 판단을 구분한다. 추가 overlap 지표는 일대일 매칭/IoU 임계값 등 정의를 먼저 고정하고 별도 보고한다. 모델별 tokenizer token-F1을 동일 단위처럼 비교하지 않는다.
지원되는 검토·검사영역의 교집합에서만 점수를 계산하고 전체답변 대비 커버리지를 함께 보고한다. uncertain/미검토 구간은 마스킹하고 분모·제외량을 공개한다. gold0/pred0의 분모0 정책을 명시하고 macro 점수를 임의로 높이지 않는다.
모델별 공통 평가 문항 교집합의 paired 점수와 전체 처리성공·실패·부분검사 현황을 함께 보고한다. 회사별/오류유형별/장문별 FN(놓침)·FP(과잉탐지), 시간·VRAM을 분석한다.
기존25는 개발·검수 절차 점검용이며 독립 test가 아니다. 기존 split을 보존하고 임계값 변경용 dev와 보고용 holdout을 공고 단위로 분리한다. 이미 노출된 자료의 한계를 명시하고 같은300에 튜닝한 결과를 독립 평가라고 하지 않는다.
사람이 최종 확인할 목록은 오류·경계 사례뿐 아니라 모델 간 동의 구간과 예측없는 답변의 층화 표본도 포함한다. 최종 전수 사람 검수 전에는 전수 gold 완성이라고 하지 않는다.

8. 테스트 및 산출물
잘못된 label mapping, 답변/근거 해시 변경, 잘못된 offset, Unicode/특수토큰, 겹침 중복, 근거 window 누락, 미검토 정상 처리, 인용오류 혼입, 다른회사 근거, 누락 레코드, 불일치 resume, 분모0에 대한 의미 있는 자동 테스트를 실행한다.
산출물은 project-docs/환각라벨링/detector-300-workstation-v1 아래의 후속 결과 버전으로 분리한다. 기존 인계·pilot25 원본·기존300 실행 기록을 덮어쓰지 않는다. 큰 예측 token probability 배열·private prompts는 ignored work에 둔다.
남길 것: 환경/모델/설정 manifest, 정확한 생성입력 복원 결과, 재현 가능한 batch·resume·scoring 코드, 모델별295건·총885슬롯 상태와 예측,295답변 라벨 초안·검수범위, 기존25 연결/보류 내역, 잠정 지표·FN/FP 사례·커버리지, 사람검수 패키지, README/실행법/남은문제.
실제 DB 재구축·모델학습·생성 재실행·UI 변경·유료API·다른 사람에게 메시지 발송은 하지 않는다.
작업 브랜치에 코드·적절한 소형 결과를 커밋하고 푸시한다. 원천·전체캐시·키·가중치는 제외하고 main 자동 병합 금지.
마지막에 실제 처리 답변/모델 수, 실패/보류, 잠정 및 확정지표 구분, 사람검수 필요량, 파일/브랜치/커밋을 보고한다. 자원이나 토큰 여유가 부족하면 문항별 체크포인트와 정확한 재개 명령을 남겨 재개 가능하게 종료해라.
