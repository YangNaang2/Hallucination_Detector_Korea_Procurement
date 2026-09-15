# GPU 탐지·295답변 라벨 초안·잠정 평가 완료

인계 커밋 `6bfbc94`, 작업 브랜치 `eval/detector-300-v1`. 295개 정본 답변에 대한 에이전트 전수 검토와 비교 평가를 완료했다. **최종 사람 승인 0건, 확정 gold 지표 N/A**다. 기존25 검수 원본·300개 실행 기록·원래 작업 트리와 실행 중 llama-server를 보존했다.

## 완료 범위

- 당시 생성입력 복원 **295/295**. 신규275는 기존 private prompt, 기존20는 `9678497`의 prompt 함수와 SYSTEM으로 복원하여 전체 프롬프트 SHA256까지 일치했다.
- 선택된 입력의 별도 산식 검산 보충문은 **0개**. 실제 업무·회사·시나리오·기준일 문맥을 유지하고 system 지시와 기대답은 탐지 근거에 넣지 않았다.
- RTX A5000 GPU에서 KLUE·XLM-R·BGE-M3 각각295건, **885/885 성공, 실패·보류0**. 소수검사15회는 별도다.
- 정상 차단 **5/5**: 원기록상 LLM 미호출, 고정 차단문만 출력, 권한 정책 재검증. 민감정보 노출 없음.
- 라벨 초안 **295/295**: 기존25 답변 해시가 같은 검수 재사용 + 신규270 답변·실제 입력 근거 전체 직접 대조. 미검토0.
- 기존25 사람 제출, 기존25 에이전트 조정안, 신규270 에이전트 초안, 최종 사람 승인을 분리했다. 신규270의 통합 상태는 독립 조정 미실시이며 **295건 전부 최종 사람 승인 대기**다.

## 고정 추론 조건

공통512 / 답변192토큰 비중첩 분할 / 학습형식 prompt에 근거를 포함하여 남은 예산의 절반 stride로 전체 근거 순회 / 환각확률 min / threshold0.5 / float32 weights + CUDA bf16 autocast / microbatch1. 토큰 간 문자 중복은 max. 확률0.5 이상 문자의 연속구간을 예측 span으로 저장하고 공백을 임의로 메우지 않는다. 길이초과 시 답변만 추론하는 fallback은 없다.

모델은 각각 한 번 로드하여 여러 문항을 처리했다. 로컬 safetensors·tokenizer·config를 사용했고 배포 checkpoints.json과 가중치 해시가 일치한다. BGE-M3 원래 긴 문맥 프로파일은 실행하지 않았다. 512/min/0.5는 조달 보정값이 아니며 이번 자료에 임계값을 튜닝하지 않았다. 로드·워밍업 시간은 모델별 summary에, 아래 시간은 순수 추론 합계다.

## 잠정 paired 문자 지표 — 전체295건

기존25 조정안 + 신규270 에이전트 초안 기준이다. 초기 agent_draft와 통합 조정안 기준은 evaluation/summary.json에서 별도 제공한다. **미승인 개발자료 기준 점수이며 독립 벤치마크 성능이 아니다.**

| 모델 | Precision | Recall | F1 | 추론 합계(초) | 최대 allocated VRAM(GiB) |
|---|---:|---:|---:|---:|---:|
| klue | 0.4688 | 0.0236 | 0.0449 | 58.92 | 0.61 |
| xlmr | 0.1793 | 0.0088 | 0.0167 | 58.23 | 1.24 |
| bgem3 | 0.4826 | 0.0128 | 0.0250 | 107.59 | 2.71 |

**사람 승인 gold 지표: N/A.** strict exact-span F1은 세 모델 모두0이며, 유효466개 양성 라벨 구간과 정확한 경계가 일치하는 예측은 없었다. 답변 단위는 점수 영역 내 환각 존재 여부로 계산한다.

| 모델 | 답변 TP / FP / FN / TN | 답변 F1 |
|---|---|---:|
| klue | 24 / 5 / 162 / 104 | 0.2233 |
| xlmr | 19 / 7 / 167 / 102 | 0.1792 |
| bgem3 | 10 / 3 / 176 / 106 | 0.1005 |

전체 답변 **136,055문자** 중 모델별 **105,364문자(77.44%)**를 검사했다. 미검사30,691문자는 모두 공백류이며 비공백 미검사0이다. 전체 검토 후 uncertain/citation_error/quality_only 마스킹은3,071문자, 공백과 마스킹의 합집합을 제외한 세 모델 공통 점수 영역은 **102,856문자(75.60%)**다. 양성14,027문자, 답변단위 양성186건은 이 잠정 점수 영역 기준이다.

문자 지표는 Unicode code point micro positive class P/R/F1. 분모0은 null. exact-span은 일대일 동일 경계, 전체 span이 검토·비마스킹 상태이고 모든 비공백 문자가 검사되어야 포함한다. 원래 경계를 잘라 맞추지 않는다. uncertain·인용오류·품질문제를 내용 환각과 합산하지 않는다. 미검토 구간을 정상으로 채우지 않으며 이번에는 미검토0이다. tokenizer별 token-F1은 비교하지 않았다.

## 오류 분석

세 모델 모두 낮은 재현율을 보였다. 현재 min 집계가 검출량을 줄일 가능성은 후속 실험 가설이며, 이번 결과만으로 원인을 확정하지 않는다.

| 모델 | contradiction Recall | unsupported Recall | 600자 미만 F1 | 600자 이상 F1 |
|---|---:|---:|---:|---:|
| klue | 0.0028 | 0.0318 | 0.0449 | 0.0451 |
| xlmr | 0.0170 | 0.0056 | 0.0198 | 0.0113 |
| bgem3 | 0.0210 | 0.0096 | 0.0228 | 0.0290 |

회사별 Recall은 KLUE 1.84~3.46%, XLM-R 0~2.53%, BGE-M3 0~3.28%다. XLM-R은 C05, BGE-M3는 C02·C03의 양성 문자를 모두 놓쳤다. 회사별 FN/FP·길이별 분모·오류유형별 수치는 summary.json에 제공한다. 오류유형별 Precision은 모델이 유형을 예측하지 않아 N/A다.

FN 사례: C05-N35-E1의 채용예정자를 현재 재직자로 기록해도 된다는 반복 주장, C05-N26-E5의 신규PM 발표 금지·대리공문 추가의무. 정확한 FN/FP 위치와 짧은 인용은 evaluation/adjudication_provisional/cases.json에 있다. 장문·반복은 문자 micro의 가중치가 커지므로 답변 지표와 함께 해석한다. 원문 전체를 사후 조회한 진실성 평가는 별도 미실시다.

## 파일·사람 검수

- `inputs/`: 동결 선택, 실제 생성입력 복원, 정상차단 검증.
- `predictions/<model>/common512-v2/`: 각295건. common512-v1은 소수검사5건씩으로 본점수에서 제외.
- `annotation/agent_draft/labels.json`: 전수295 답변 검토범위·구절·이유·근거.
- `annotation/adjudicated/proposals.json`: 기존25 조정안 + 신규270 초안. 독립 조정·사람 승인을 주장하지 않는다.
- `annotation/human_submitted/references.json`: 기존25 사람 제출 원본 참조·해시.
- `annotation/resume.json`: 검토295, 남은목록0, 사람승인대기295.
- `annotation/human_review_queue.json`: 전수295 목록 및 회사별 예측없음·공통검출·불일치 층화 제안 표본. 오류뿐 아니라 모델들이 동의한 구간과 무예측 답변도 검수한다.
- `evaluation/summary.json`: 초기초안/통합안·개별/paired·회사/길이/유형별 잠정 지표.
- `validation-final.json`: 최신 전체 검증. validation.json, validation-followup.json은 이전 단계 기록이다.

전체 근거·프롬프트·확률 배열은 ignored work/detector300에만 저장한다. `work/detector300/review.html`은 예측을 숨긴295답변+실제근거+라벨 로컬 검수 화면이다. HTML 브라우저 렌더 검사는 미실시이며 구조·레코드 수는 검증했다. 최종 승인자는 대상 답변 해시·이름·시각·결정 구절을 별도 승인본에 기록해야 한다. 현재 승인 gold 자동 추정은 없다.

## 재현·재개

저장소 루트에서 실행한다. 기존885건은 동일 run으로 재개하면 전부 건너뛴다. 다른 입력/설정/runner identity는 거부한다. 원래 가중치와 답변을 변경하지 않는다.

```bash
PYTHON=/home/piai/바탕화면/ko_lettucedetect/.venv-train/bin/python
python procurement-pipeline/prepare_detector300_handoff.py --check
$PYTHON procurement-pipeline/detector300.py run --model-root /home/piai/바탕화면/ko_lettucedetect/runs --run-id common512-v2
python procurement-pipeline/detector300_labels.py
python procurement-pipeline/detector300_score.py --run-id common512-v2
python procurement-pipeline/detector300_package.py
$PYTHON -m unittest discover -s procurement-pipeline -p "test_detector300*.py"
python procurement-pipeline/detector300_validate.py --index <기존-index.sqlite> --source-cache <source-texts.posix.json>
```

복원 재현: `detector300.py recover --index <기존 index.sqlite> --source-cache <source-texts.posix.json> --cache-root <기존 work>`. 기존 캐시는 `/home/piai/Documents/Codex/2026-09-13/files-pasted-by-the-user-ko/ko-lettucedetect/work` 아래 rag-workstation-275/index.sqlite, source-transfer/source-texts.posix.json이다. 실패 재시도만 --retry를 사용하며 이전 attempt를 보존한다.

## 검증·제한

- 단위/오류주입 **26개 통과**, 입력무결성300건 통과. 실제 **885예측·214,331확률 offset·645청크·743수동근거 앵커**와 정본 원문 위치를 검증했다.
- 합성표 내부의 `[2]`를 인용 경계로 오인하던 경우를 수정했다. 실제 행 시작의 인용 번호만 허용하고 회귀 테스트를 추가했다. 새 수동 라벨의 중첩 구간2개를 정리했다.
- 기존25 원본은 인계커밋과 byte diff가 없고 답변 해시를 대조해 재사용했다. 동일설정885 skip과 identity 변경 시 resume 거부는 이전 실행에서 검증했다.
- 기존 split을 보존했다. 모두 이전 RAG 개발에 노출된 자료다. 학습·튜닝은 하지 않았으며, 후속 임계값 개발용 dev와 보고용 holdout은 공고 단위로 별도 고정해야 한다.
- 이전 로컬 Qwen 보조초안4건은 품질검사에서 기각하여 점수·라벨에 제외했다. 원래295답변 생성·RAG 재실행은 하지 않았다.
- 자료 복원 보류·탐지 실패·에이전트 미검토는0. 남은 단계는 독립 조정 및 최종 사람 검수·승인295건이다.
