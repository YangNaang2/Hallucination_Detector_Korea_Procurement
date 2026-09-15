# GPU 탐지 실행 완료 · 전수 라벨은 진행 중

기준 커밋 `6bfbc94`, 작업 브랜치 `eval/detector-300-v1`. 정본 답변·기존25 검수·기존 RAG 작업을 보존했다. **전체 평가 완료가 아닌 재개 가능한 중간 체크포인트**다.

## 실제 완료 범위

- 당시 생성입력 복원 **295/295**: 답변·전체 프롬프트·청크·원문 slice 해시, ACL 대조. 신규275는 기존 private prompt, 기존20는 `9678497`의 prompt 함수와 SYSTEM으로 복원 후 전체 해시 일치.
- 선택된 프롬프트의 별도 산식 검산 보충문은 **0개**였다. 존재 여부를 검사했으며 새 계산문이나 기대답을 추가하지 않았다. 실제 시나리오·판단기준일 header는 유지하고 system과 출력 형식 지시는 제외했다.
- RTX A5000에서 모델별295건, **885/885 성공, 실패0**. 별도 소수검사15회는 이 분모에 포함하지 않는다.
- 정상 차단 **5/5**: 기록상 LLM 미호출, 고정 차단문만 출력, 현재 권한 정책 재검증. 새로운 LLM 호출 없음.
- 구절 검토 **40/295**: 기존25 재사용 + 새15 전체 답변·입력 직접 대조. **255건 미검토**, `spans=null`, `reviewed_ranges=[]`.
- 사람 최종 승인 **0건**. 생성답변295건 전부 최종 승인 대기. 기존25 사람 제출과 에이전트 조정안은 별도 참조.

## 고정 추론 조건

공통512 / 답변192토큰 비중첩 분할 / 근거를 포함한 학습형식 prompt를 남은 예산의 절반 stride로 전부 순회 / 환각확률 min / threshold0.5 / float32 weights + CUDA bf16 autocast / microbatch1. 토큰 간 문자 중복은 max. 확률0.5 이상 문자의 연속구간을 예측 span으로 저장하며 공백을 임의로 메우지 않는다. 길이초과 시 답변만 추론하는 fallback은 없다.

각 모델은 한 번 로드해 전체 답변을 처리했다. 기존 llama-server는 종료하지 않았다. BGE-M3의 원래 긴 문맥 프로파일은 이번에 실행하지 않았다. 512/min/0.5는 조달 튜닝값이 아니다. min 집계에 따른 낮은 검출량은 후속 개발 가설이며 이번에 임계값을 최적화하지 않았다.

## 잠정 paired 문자 지표 — 검토40건만

기존25 조정안 + 새15 초안 기준. 동일 문항·동일 문자 영역에서 계산한다. 미승인 자료이고 의도적 개발표본이므로 일반 성능이나 전체295 오류율로 발표할 수 없다.

| 모델 | Precision | Recall | F1 | 순수 추론 합계(초) | 최대 allocated VRAM(GiB) |
|---|---:|---:|---:|---:|---:|
| klue | 0.3986 | 0.0461 | 0.0826 | 58.92 | 0.61 |
| xlmr | 0.0719 | 0.0050 | 0.0094 | 58.23 | 1.24 |
| bgem3 | 0.6534 | 0.0482 | 0.0897 | 107.59 | 2.71 |

**사람 승인 gold 지표: N/A.** 초기 agent_draft 기준은 `evaluation/summary.json`에 별도 수록한다. strict exact-span F1은 모두0이며, 85개 유효 gold span의 경계가 일치한 예측은 없었다. 모델별 token-F1은 비교하지 않았다.

전체 답변136,055문자 중 모델별105,364문자를 토큰 offset으로 검사했다(77.44%). 나머지30,691문자는 **모두 공백류**이며 문자 점수에서 제외했다. 비공백 미검사0. 검토40건은19,953문자, uncertain/citation/quality 마스킹 후 세 모델 공통 점수영역14,720문자(전체 답변의10.82%)다. 미검토255건을 정상으로 계산하지 않는다.

문자 지표는 micro positive class. 분모0이면 null. exact-span은 원래 경계가 일치해야 하고, 모든 비공백 문자가 검사되고 전체 span이 검토·비마스킹 영역일 때만 포함한다. 답변단위 지표는 **점수영역 내 환각 유무**로 정의하며 전체답변 진실성과 구분한다. 원문 사후 진실성은 별도 미평가다.

회사별·장문(600문자 기준)·정답 오류유형별 Recall과 FN/FP 위치는 evaluation 아래에 있다. 예: 진행중 실적을 완료로 인정한 C01-N05-E2, 업종코드를 세부품명으로 바꾼 C03-N07-E2의 오류를 놓쳤다. BGE FP에는 C03-S03의 `판斷`/`기준일` 일부, C05-S02의 일부 금액 표현이 있다. 모두 잠정 라벨 기준 사례다.

## 파일

- `inputs/`: 동결 선택·복원 결과·차단 검증.
- `predictions/<model>/common512-v2/`: 본 실행295건씩. `common512-v1`은 복원 코드 수정 전 소수검사5건씩이며 본점수에 사용하지 않는다.
- `annotation/agent_draft/labels.json`: 295개 상태, 검토40건 구절·이유·근거.
- `annotation/adjudicated/proposals.json`: 기존25 조정안과 신규 초안. 새15건은 독립 조정 완료로 표시하지 않는다.
- `annotation/human_submitted/references.json`: 기존 제출 원본 참조와 해시.
- `annotation/resume.json`: 미검토255개 ID와 재개 규칙.
- `annotation/human_review_queue.json`: 전체 사람 검수대상과 회사별 예측 없음·공통 검출 문자·모델 불일치 표본.
- `evaluation/`: 모델별·paired 점수, 사례,885슬롯 상태. `validation.json`과 `environment.json`은 실행 검증·환경.

전체 근거/확률은 ignored `work/detector300/`에만 있다. 로컬 `work/detector300/review.html`에는 예측을 숨긴 295답변+복원근거 검수 화면이 있다. HTML의 실제 브라우저 렌더 검사는 미실시다.

## 재현·재개

저장소 루트에서 실행한다. 이 PC의 기존 경로 예시이며 다른 PC에서는 경로만 바꾼다.

```bash
PYTHON=/home/piai/바탕화면/ko_lettucedetect/.venv-train/bin/python
python procurement-pipeline/prepare_detector300_handoff.py --check
$PYTHON procurement-pipeline/detector300.py run --model-root /home/piai/바탕화면/ko_lettucedetect/runs --run-id common512-v2
python procurement-pipeline/detector300_labels.py
python procurement-pipeline/detector300_score.py --run-id common512-v2
python procurement-pipeline/detector300_package.py
$PYTHON -m unittest discover -s procurement-pipeline -p "test_detector300*.py"
```

동일 run 재개는 완료된885건을 모두 건너뛴다. 입력/코드/설정 해시가 다르면 거부하며, 새 설정은 새 run-id가 필요하다. 실패를 재시도할 때만 `--retry`를 사용하고 이전 시도는 attempts에 보존한다. source/weights나 원답변은 변경하지 않는다.

복원 재현은 `detector300.py recover --index <기존 index.sqlite> --source-cache <source-texts.posix.json> --cache-root <기존 work>`를 사용한다. 이 PC 캐시는 `/home/piai/Documents/Codex/2026-09-13/files-pasted-by-the-user-ko/ko-lettucedetect/work` 아래에 있다.

## 다음 작업: 나머지255개 전수 라벨

이번 턴은 입력·추론·부분 라벨·평가 코드의 체크포인트로 남긴다. 원천 부족은 없다. 255개 전체 답변과 전체 입력을 직접 읽는 검토는 아직 수행하지 않았다. `annotation/resume.json`의 ID를 순서대로 처리하고, 모델 예측을 먼저 보지 않은 채 `detector300_review_specs.py`에 정확한 구절·분류·이유·입력 앵커를 추가한다. 기존 원본을 편집하지 않는다. 라벨 생성·점수·검수 패키지를 위 명령으로 갱신한다. 자동 규칙이나 모델 예측 복사로 전수 라벨 완료를 대체하지 않는다.

기존 split을 보존했다. 모든300개가 이전 RAG 개발에 노출됐으므로 새 독립 holdout을 주장하지 않는다. 이번에 학습/튜닝은 없으며 후속 튜닝용 dev와 평가용 holdout은 공고 단위로 따로 고정해야 한다. 최종 사람 승인 이름·시각·대상은 별도 승인본에 기록해야 한다.

검증: 신규 단위/오류주입22개 통과, 실제885건 해시·offset·범위·확률 검사 통과, 원입력 무결성 재검사 통과. 동일 설정 resume skip 및 변경된 runner identity의 resume 거부를 확인했다.
