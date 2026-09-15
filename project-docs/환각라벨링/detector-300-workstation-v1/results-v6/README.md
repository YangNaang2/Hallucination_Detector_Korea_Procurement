# v6 — KLUE numeric contrast training and separate answer regeneration

Status: **in progress; operational success criterion not met**. Human-final-approved gold: 0.

Original answers, evidence, v1–v5 results and original weights are preserved. Branch `feature/klue-regeneration-v6`; no main merge. See `protocol.json`, `selection_policy.json`, `selection.json` and `strict_selection.json` for frozen provenance and development-only selection. Historical comparison questions are exposed development material, **not an independent test**.

## Detector result on the existing 63-answer comparison

| Configuration | TP | FP / 28 normal | FN | TN | Answer recall | Character F1 |
|---|---:|---:|---:|---:|---:|---:|
| v3 mil3 min .5 | 32 | 21 | 3 | 7 | 91.43% | 31.13% |
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
