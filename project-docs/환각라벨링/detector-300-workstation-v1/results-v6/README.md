# v6 — KLUE numeric contrast training and separate answer regeneration

Status: **in progress; operational success criterion not met**. Human-final-approved gold: 0.

Original answers, evidence, v1–v5 results and original weights are preserved. Branch `feature/klue-regeneration-v6`; no main merge. See `protocol.json`, `selection_policy.json`, `selection.json` and `strict_selection.json` for frozen provenance and development-only selection. Historical comparison questions are exposed development material, **not an independent test**.

## Detector result on the existing 63-answer comparison

| Configuration | TP | FP / 28 normal | FN | TN | Answer recall | Character F1 |
|---|---:|---:|---:|---:|---:|---:|
| v3 mil3 min2 .5 | 32 | 21 | 3 | 7 | 91.43% | 31.13% |
| v5 fp1 min .8 | 24 | 10 | 11 | 18 | 68.57% | 15.28% |
| v5 fp1 min .9 | 15 | 8 | 20 | 20 | 42.86% | 7.81% |
| v6 contrast3 min .3 | 27 | 14 | 8 | 14 | 77.14% | 24.89% |

New training uses 248 train-only numeric contrast cases and stronger normal-token loss. At the **same min/.3 operating point**, v5 has TP31/FP21 versus v6 TP27/FP14: fewer false positives but four additional missed hallucinated answers. This does not establish a superior operating configuration. Against the prior v5 .8 operating point, v6 adds three detections and four false warnings. The strict development-selected configuration remains v5 fp1/.9. No candidate is deployed.

## New-answer experiment

Separate run `v6-grounded-generation-1` reuses original retrieved evidence and the existing local Qwen3-4B server. Original answers and evaluation labels are absent from generation requests. Private full answers: `work/quality-v6/generated`; Git contains hashes and per-record metadata in `generation_records`. Two workers share one loaded server/model. Original server and other work were preserved.

Existing v3 and candidate KLUE predictions are written separately under `new_predictions`. These are predictions, not labels. `new_agent_labels` contains fresh, explicit evidence-based agent reviews and question-fulfillment/omission assessments. These are **not human approvals**. Unreviewed answers must not be scored as normal.

Qwen self-review and initial Gemma review pilots made semantic mistakes, including labelling correct rejection of a false question premise as contradiction. Their drafts/holds are preserved but are **not accepted ground truth**. A further prompt-format pilot is exploratory. The model judge is never the only approved truth source.

Generation and dual-detector inference are still running. `validation-progress.json` records a point-in-time snapshot; its counts may lag the running jobs. A/B results above are available; C/D conclusions require new-answer evidence labels and matched coverage. No claim of improved generation quality is made yet.

## Reproduce / resume

Use the existing `.venv-train/bin/python` documented in the protocol, from repository root:

```sh
python procurement-pipeline/prepare_detector300_handoff.py --check
python procurement-pipeline/detector_v6_generate_parallel.py
python procurement-pipeline/detector_v6_infer_new.py --watch
python procurement-pipeline/detector_v6_validate.py
python -m unittest discover -s procurement-pipeline -p 'test_detector_v6.py'
```

Private weights/probability matrices/full prompts must not be committed. Generation and inference validate immutable input/configuration identity before reusing per-record outputs.

## Additional completed experiments (checkpoint update)

- Control training without the 248 synthetic pairs completed three GPU epochs. Fixed epoch3/min/.3 comparison: TP27, FP13, FN8, TN15, character F1 24.14%. The augmented variant has TP27/FP14 and character F1 24.89%. No clear benefit of numeric augmentation; sample count and optimizer steps also differ. See `control/fixed_ablation.json` and `control/fixed-evaluation.json`.
- Warning continuity filtering tried minimum nonspace lengths 1/4/8/12 on development data. Selection retained minimum1, so suppressing short warnings was not adopted. Whitespace-only joining changes span presentation, not answer warnings or character decisions.
- New answers: 293/295 successfully saved. Two repeatable local server parser failures (C05-N18-E3, C05-N34-E2): `expected peg-native format`; no source evidence was shortened to conceal the failure.
- All 63 historical comparison questions now have fresh agent review drafts. Confirmed new hallucination34/63, unresolved4/63; occurrence interval53.97–60.32%, versus old35/63. Question fulfillment: complete31, partial32. This does not establish generation improvement.
- Operational whole-answer scoring excludes uncertain-only truth from normal counts. Historical A: TP32/FP19/FN3/TN7 (2 unknown); B:27/12/8/14 (2 unknown); C:30/18/4/7 (4 unknown); D:23/11/11/14 (4 unknown). These differ from legacy masked counts above by design; unknown truth is never counted as normal. See `abcd_comparison.json`.
- `group_bootstrap.json` reports bid-group intervals on exposed data; `label_revision_effect.json` rescores unchanged predictions before/after a documented new-label correction. Original labels remain unchanged.

Remaining work: review the rest of the new answers, resolve/document generation parser failures, complete resource and final validation report. No autonomous operational configuration has met the target.


## 사용자 범위 조정: 선별 시연 50건 (2026-09-16)

추가 대규모 실험은 늘리지 않고 현재 결과에서 성공 사례를 선별했다. `showcase/manifest.json`은 **정답 확인 후 선정한 데모**이며 전체 성능 추정에 사용할 수 없다. 정상 무경고 25건, 실제 오류 구절 포착 25건이다. 비교 21건·개발 22건·학습 7건이며 모두 과거 노출 자료다. 학습 자료를 포함하고, 문자 경계가 완벽한 사례만 모은 것도 아니다. 재현 코드는 `procurement-pipeline/detector_v6_showcase.py`다.

전체 기존 비교 결과는 정상 오탐 21→14, 환각 포착 32→27, 문자 F1 31.13→24.89%다. 목표 미달이며 운영 설정 변경을 채택하지 않았다. 추가 숫자 학습은 통제 실험 대비 명확한 개선을 보이지 않았다.

새 답변 293건과 각각의 두 모델 예측을 보존했다. 새 답변 직접 에이전트 검토 154건, 나머지 성공 생성 139건 미검토, 생성 실패 2건이다. 사람 최종 승인 라벨이 아니다. 갱신된 `abcd_comparison.json`, `group_bootstrap.json`, `validation-progress.json`이 현재 집계의 기준이다. 앞선 중간 집계보다 이 파일들을 우선한다. 생성 서버의 두 질문 형식 파싱 오류는 별도 복구 설정에서도 재현돼 미해결로 남겼다. 복구 실험용 서버만 종료했으며 기존 PID4922 서버는 유지했다.

새 학습 공고 답변을 추가하는 학습은 제안 단계에서 사용자 범위 조정으로 실행하지 않았다. 전체 새 답변 검토·모든 개선 실험을 완료했다는 의미가 아니다. 데모의 성공 사례를 전체 성능 개선으로 해석하지 않는다.

## 추가 요청: 고정 100건 평가

`sample100/`은 현재 학습 분할을 제외한 113건 중 예측·라벨과 무관한 고정 해시 순서로 한 번만 추출한 100건이다. 4건의 불확실한 정답은 정상으로 넣지 않았다. 채점 가능 96건에서 v3 정확도 65.62%, v6 정확도 67.71%, v6 정밀도 77.78%, 재현율 68.85%다. **정확도 80% 목표 미달**. v3 대비 오탐 25→12, 누락 8→19이며 정밀도 상승과 재현율 하락을 함께 보고한다. 과거 노출 개발·비교 자료의 탐색 결과이며 독립 테스트가 아니다. 새 사람 라벨 100건을 작성한 것이 아니라 기존 잠정 에이전트 라벨을 재사용했다.

최종 점검: 입력 무결성 300건 PASS, 원본 보존 및 295건 예측 검증 PASS, 회귀 유닛 테스트 4건 PASS (`python procurement-pipeline/test_detector_v6.py`; 환경에 pytest 모듈은 없어 unittest 실행). 가중치와 전체 private 프롬프트는 커밋에서 제외했다.
