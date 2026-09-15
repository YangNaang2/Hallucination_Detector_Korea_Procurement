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
