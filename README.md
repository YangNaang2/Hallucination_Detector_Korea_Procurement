# ko-lettucedetect — 한국어 RAG 환각 탐지 파일럿

RAGTruth(영어)를 `<HAL>` 태그째 한국어로 기계번역하고, 한국어 인코더를 **이진 토큰 분류**로 파인튜닝한다.
Turk-LettuceDetect(arXiv:2509.17671)의 방법을 한국어로 재현하는 것이 목표이며, 상세 근거는 `../논문자료/turk_lettuce_구현레시피.md` 참고.

**실행 환경: A5000 1장(24GB) 워크스테이션, Linux.** 노트북에서는 돌리지 않는다.

> **논문과의 차이 — GPU.** 논문은 A100 1장(80GB)에서 `gemma-3-27b-it` 를 bf16 으로 돌려
> 풀 패스 12시간이 걸렸다. 우리는 24GB 1장이라 **27B bf16(약 54GB)이 들어가지 않는다.**
> 그래서 번역 모델을 12B 로 낮추고, 파일럿에서 27B(int4)와 태그 보존율을 비교해 결정한다.
> **학습 쪽은 24GB 1장으로 충분하다.**

---

## 0. 중요 — 가상환경을 두 개로 나눌 것

vLLM은 torch 버전을 강하게 고정하므로 학습 환경과 섞으면 깨진다.

```bash
# 번역용
python -m venv .venv-vllm  && source .venv-vllm/bin/activate
pip install -r requirements-translate.txt
deactivate

# 학습용
python -m venv .venv-train && source .venv-train/bin/activate
pip install -r requirements-train.txt
```

---

## 1. 데이터 받기

```bash
git clone https://github.com/ParticleMedia/RAGTruth.git data/RAGTruth
```

`data/RAGTruth/dataset/` 안에 `source_info.jsonl`, `response.jsonl`이 있어야 한다.

---

## 2. 스키마 확인 (반드시 먼저)

RAGTruth 필드명이 릴리스마다 다를 수 있으므로 **가장 먼저 스키마를 눈으로 확인**한다.

```bash
source .venv-train/bin/activate
python -m src.prepare_ragtruth --inspect
```

출력된 키 이름이 `config.py`의 `FIELD_*` 상수와 다르면 그 상수만 고치면 된다.

---

## 3. 파이프라인 (파일럿 200건)

```bash
bash scripts/run_pilot.sh
```

내부적으로 순서대로 실행된다.

| 단계 | 스크립트 | 하는 일 | 산출물 |
|---|---|---|---|
| 1 | `prepare_ragtruth.py` | 겹침 라벨 병합 → 응답에 `<HAL>…</HAL>` 삽입 → 번역 입력 생성 (context는 source_id 단위로 중복 제거) | `work/to_translate.jsonl`, `work/source_to_translate.jsonl` |
| 2 | `translate.py` | vLLM, 논문의 Core Translation Prompt 그대로. **12B·27B 두 번 돌려 비교** | `work/translated_12b.jsonl`, `work/translated_27b.jsonl` |
| 3 | `postprocess.py` | 태그 개수·균형 검증 → 문자 오프셋 **재계산** → QC 리포트 | `work/ko_ragtruth_*.jsonl`, `work/qc_report_*.md` |
| 4 | `train.py` | 이진 토큰 분류 파인튜닝 (6 epoch, lr 1e-5) | `runs/<encoder>-<번역모델>/` |
| 5 | `evaluate.py` | 토큰 단위 P/R/F1/AUROC, 과제별 분해 | `runs/…/eval.json` |

**3단계의 QC 리포트가 곧 "200건 배치 태그 보존율 재측정" 결과물이다.** 이 숫자가 나와야 전체 번역 일정을 확정할 수 있다. 스크립트가 두 모델의 보존율을 나란히 보여주고 어느 쪽으로 학습할지 물어본다.

27B 가 VRAM 때문에 실패하면 `SKIP_27B=1 bash scripts/run_pilot.sh 200` 으로 12B 만 돌린다.

---

## 4. 전체 데이터로 확대

파일럿에서 고른 번역 모델로 진행한다 (아래는 12B 를 골랐다고 가정).

```bash
python -m src.prepare_ragtruth                       # --limit 없이
python -m src.translate --model google/gemma-3-12b-it \
                        --quantization bitsandbytes --tag full   # 수일 소요 — nohup 권장
python -m src.postprocess --in work/translated_full.jsonl
python -m src.train    --model Alibaba-NLP/gte-multilingual-base \
                       --data work/ko_ragtruth_full.jsonl --trust-remote-code
python -m src.evaluate --run runs/gte-multilingual-base \
                       --data work/ko_ragtruth_full.jsonl --trust-remote-code
```

번역은 길게 도니 세션이 끊겨도 살아남게 실행한다.

```bash
nohup python -m src.translate ... > work/translate.log 2>&1 &
tail -f work/translate.log
```

---

## 5. GPU 메모 (A5000 24GB 1장 기준)

| 작업 | VRAM | 가능 여부 |
|---|---|---|
| 번역 27B bf16 (논문 그대로) | 약 54GB | **✗ 불가** |
| 번역 27B int4 (`--quantization bitsandbytes`) | 약 14GB + KV캐시 | △ 되지만 느림 |
| 번역 12B int4 | 약 7GB | **○ 여유 — 기본값** |
| 학습 305M 인코더, 4096 토큰 | 약 15~20GB | ○ 가능 |

- 학습 기본값은 `batch 1 + grad_accum 4 + gradient_checkpointing` 으로 **논문의 유효 배치 4와 동일**하다. OOM 이 나면 `--max-length 2048` 로 먼저 낮춘다.
- `--max-num-seqs` 가 번역 시 동시 처리량이다. VRAM 이 모자라면 낮춘다(기본 16).

### 전체 번역 시간 — 결정이 필요한 지점

논문은 A100 1장 + 30건 병렬로 **풀 패스 12시간**이었다. A5000 1장 int4 면 **전체 데이터(약 1.8만 응답 + 지문)는 2~4일 연속 가동** 수준이다. 200건 파일럿은 1시간 안쪽이라 문제없다.

**그래서 순서를 지킬 것 — 파일럿으로 태그 보존율을 먼저 확인하고, 전체 번역 인프라는 그 결과를 보고 정한다.** 선택지:

| 안 | 내용 | 비고 |
|---|---|---|
| A | 12B 로 로컬 풀 패스 | 파일럿에서 12B 보존율이 27B와 비슷하면 이게 가장 싸다 |
| B | A5000 1장으로 27B int4, 며칠 방치 | 품질 최우선, 일정 압박 |
| C | 클라우드 GPU(A100) 1회 대여 | 12시간 규모, 비용 소액. 일정이 급하면 유력 |
| D | 번역 API 사용 | GPU 불필요, 품질 좋음. 비용은 분량에 비례 |

---

## 6. 인코더 후보

| 모델 | 컨텍스트 | 비고 |
|---|---|---|
| `Alibaba-NLP/gte-multilingual-base` | 8192 | **1순위.** 터키팀 2번 모델(TurkEmbed4STS)의 베이스와 동일. `trust_remote_code=True` 필요 |
| `jhgan/ko-sroberta-multitask` 등 KorNLI/STS 튜닝 인코더 | 512 | 터키팀 최고 모델이 NLI/STS 튜닝 백본이었음 → 성능상 유리할 수 있으나 컨텍스트가 짧다 |
| `xlm-roberta-base` | 512 | 안전한 대조군 |
| `klue/roberta-base` | 512 | 한국어 대조군. 단독으로는 긴 문맥 부적합 |

`--model`만 바꾸면 3종 비교가 된다. `trust_remote_code`가 필요한 모델은 `--trust-remote-code`를 붙인다.

---

## 7. 알려진 제약

- 이 파이프라인은 논문과 동일하게 **이진 분류**다(지지/환각). 3분류(NEI)는 포함하지 않는다.
- 컨텍스트가 최대 길이를 넘으면 **앞에서부터 남기고 뒤를 자른다.** 답변 토큰은 절대 자르지 않는다(라벨이 사라지므로).
- 조사가 `<HAL>` 구간 밖으로 밀리는 현상은 `postprocess.py`가 경고만 남기고 그대로 둔다. 한국어 고유 연구 소재이므로 임의 보정하지 않는다.
