# Turk-LettuceDetect — 한국어 재현용 구현 레시피

> 원논문: Taş et al., "Turk-LettuceDetect: A Hallucination Detection Models for Turkish RAG Applications", Newmind AI, arXiv:2509.17671v1 (2025.09.22).
> PDF: `논문자료/turk_lettuce.pdf`. 이 문서는 우리가 한국어로 그대로 재현할 때 필요한 부분만 발췌한 것.

---

## 1. 한 줄 요약

RAGTruth(영어)를 `<HAL>` 태그째 gemma-3-27b-it로 기계번역 → 번역본으로 인코더 3종을 **이진 토큰 분류**로 파인튜닝 → 터키어 RAG 환각 탐지. 전체 테스트셋 토큰 F1 최고 **0.7266**(ModernBERT-base-tr). 우리는 이걸 한국어로 한 뒤, 진짜 한국어 문서로 격차를 측정하는 게 추가 기여.

---

## 2. 번역 파이프라인 (논문 III-B)

| 항목 | 값 |
|---|---|
| 번역 모델 | `google/gemma-3-27b-it` |
| 실행 | vLLM, NVIDIA A100 1대 |
| 병렬 | 약 30건 동시 |
| 소요 | 한 타겟 언어 풀 패스 ≈ **12시간** |
| 프로토콜 | 2종 — ① Answer 번역(`<HAL>` 태그 보존) ② Prompt 번역(JSON 키·값까지 전부, 기능 등가 우선) |

### 2.1 Core Translation Prompt (논문 p.3 박스 — 그대로 인용)

```
Translate the following text from {source_lang} to {target_lang}. If the
original text contains <HAL> tags, translate the content inside <HAL> tags
and ensure the number of the <HAL> tags remain exactly the same in the
output. If the original text does not contain <HAL> tags, just translate the
text. Do NOT add any <HAL> tags if they were not in the original text. Do
NOT remove any <HAL> tags that were in the original text. Do not include
any additional sentences summarizing or explaining the translation. Your
output should be just the translated text, nothing else.
```

### 2.2 Answer 번역 프로토콜 (논문 III-B-2-a)
- **태그 보존**: `<HAL>` 태그의 개수·위치를 원문 그대로, 태그 안 내용만 번역
- **태그 밖**: 일반 번역(의미·문맥 뉘앙스 유지)
- **구조 무결성**: 태그 신규 추가 금지, 기존 태그 삭제 금지
- **출력**: 번역문만. 메타 설명·주석 금지

### 2.3 Prompt 번역 프로토콜 (논문 III-B-2-b)
- 자연어 지시문 + JSON 등 구조 요소의 **키와 값 모두** 번역
- 축자역이 아니라 **기능 등가**(같은 응답을 끌어내는지) 우선
- 출력은 타겟 언어 프롬프트만

### 2.4 라벨 좌표 처리 (논문 Table I에서 관찰)
- 원본 어노테이션: `{start, end, text, type}` (문자 오프셋 + 환각 유형)
- 번역 시 `<HAL>` 태그가 텍스트와 함께 이동 → **번역 후 태그 위치에서 start/end를 다시 계산**
- 번역본 어노테이션은 `{start, end, label}` 형태로 단순화됨 (Table I 터키어 예시: 영어 start 636 → 터키어 start 545 로 좌표가 바뀜)
- **유형 4종(Evident/Subtle Conflict, Evident/Subtle Baseless Info)은 버리고 이진으로 축소**

---

## 3. 데이터셋 (논문 III-A)

| 항목 | 값 |
|---|---|
| 규모 | train 17,790 / test 2,700 |
| 과제 3종 | QA(MS MARCO 지문) · data-to-text(Yelp Open Dataset) · 요약(CNN/Daily Mail) |
| 응답 생성 LLM | GPT-4-0613, Mistral-7B-Instruct, LLaMA2-7B/13B-Chat 등 6종 (데이터포인트마다 6개 모델 응답) |
| 토큰 길이 | 평균 801 / 중앙값 741 / 범위 194–2,632 → **4096 초과 컨텍스트 필요** |
| 라벨 | 사람이 환각 구간 + 근거(rationale) 라벨링. 우리 학습에선 유형 무시하고 이진 |

---

## 4. 모델·학습 (논문 III-C, III-D)

- **태스크 정의**: answer의 각 토큰을 0(supported) / 1(hallucinated) 이진 분류
- **마스킹**: context·question 토큰은 `label = -100` → answer 토큰에만 loss
- **손실**: 토큰별 cross-entropy (special token·padding 마스킹)
- **NLI 사전학습 없음** — base transformer 표현 위에서 바로 분류 헤드
  - 단, 최고 성능 모델 `ModernBERT-base-tr`의 백본 자체는 **터키어 NLI·STS로 먼저 파인튜닝**된 것 (III 도입부). 즉 "HD 파인튜닝 전에 NLI/STS 튜닝된 백본"이 유리했다는 해석 가능
- **인코더 3종**: ModernBERT-base-tr / TurkEmbed4STS(= `gte-multilingual-base` 기반) / `lettucedect-210m-eurobert-tr`
- **하이퍼파라미터**: 6 epoch, lr 1e-5, batch size 4, A100 40GB, epoch당 ≈ 20분, 모델당 총 ≈ 2시간
- **라이브러리**: `lettucedetect`, `datasets` (pip)

### 결과 (Table II, 토큰 단위)

| 모델 | 전체 F1 | QA F1 | Data2txt F1 | 요약 F1 |
|---|---|---|---|---|
| ModernBERT-base-tr | **0.7266** | 0.7588 | 0.7391 | 0.6007 |
| TurkEmbed4STS | 0.7132 | 0.7380 | 0.7365 | 0.5862 |
| lettucedect-210m-eurobert-tr | 0.7163 | 0.7323 | 0.7496 | 0.5771 |

- **요약이 가장 어려움** (전 모델 F1 < 0.65)
- LLM(GPT-4.1, Mistral)은 recall 높고 precision 낮음 → 전용 탐지기 필요성의 근거

---

## 5. 한국어로 갈 때 정해야 할 것

### 5.1 인코더 선택 (가장 큰 결정)
한국어 전용 ModernBERT가 없음. 후보:
- **`gte-multilingual-base`** — 8,192 컨텍스트, 한국어 포함. 터키팀 2번 모델 베이스와 동일 → 가장 직접적인 대응. **1순위 후보.**
- **KorNLI/KLUE-NLI로 튜닝된 인코더** (ko-sroberta-multitask, KoSimCSE 등)를 백본으로 → 터키팀 최고 모델이 NLI/STS 튜닝 백본이었던 점과 부합. 단 대부분 512 토큰이라 긴 컨텍스트 처리 방안 필요
- **`xlm-roberta` + 롱컨텍스트 변형** 또는 커뮤니티 **KoModernBERT** 빌드 — 검증 필요
- `klue/roberta` 단독은 512 토큰이라 그대로는 부적합

### 5.2 이진 vs 3분류
이 논문 계보는 **순수 이진**(supported / hallucinated). 우리 로그 일부에 있는 "지지 / 반박 / 정보부족(NEI) 3분류"는 이 계보엔 없고 세션 9의 별도 설계 논의에서 온 것. **파일럿은 논문대로 이진으로**, 3분류 확장 여부는 팀 회의 안건.

### 5.3 예상 난점
- 요약 과제 성능 저하는 한국어에서도 재현될 것
- 조사가 `<HAL>` 구간 밖으로 밀리는 문제(우리 세션 26에서 관측) → 좌표 재계산 로직에서 처리 필요
- gemma-3-27b-it 로컬 구동: bf16 27B ≈ 54GB → A5000(24GB) 다중 텐서병렬 또는 int4 양자화 필요

---

## 6. 파일럿 최소 절차 (양진우)

1. RAGTruth 다운로드 (`github.com/ParticleMedia/RAGTruth`) + 라벨을 `<HAL>` 태그 삽입 형태로 변환
2. 소량(200건)만 위 Core Translation Prompt로 gemma-3-27b-it 번역 → 태그 보존율·좌표 재계산 검증 (세션 26 후속)
3. `gte-multilingual-base`로 이진 토큰 분류 파인튜닝 (6 epoch, lr 1e-5, bs 4)
4. 번역 test 2,700건에서 토큰 F1 측정 → 터키팀 0.7266과 비교
