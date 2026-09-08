# 웹 챗봇 (문서 업로드 → 답변 생성 → 환각 탐지)

`팀원배포/` 의 검사 전용 Gradio 화면에 **답변 생성**을 붙이고, 화면을 React 로 다시 만든 것입니다.
PDF 를 올려 질문하면 답변을 만들고, 그 답변을 **기존 탐지 모델**로 검사해 형광펜을 칠합니다.

기존 파일은 건드리지 않았습니다. 이 폴더만 추가했습니다.

## 구성

| 파일 | 역할 |
|---|---|
| `api.py` | FastAPI 서버 — PDF 추출, 구간 추리기, Ollama 호출, 탐지, 정적 파일 서빙 |
| `frontend/` | React + Tailwind 챗봇 화면 |
| `app_cpu_ui개편.py` | `팀원배포/app_cpu.py` 의 Gradio UI 를 2열 + 모달로 재구성한 것 (참고용) |
| `evaluate.py` | MSDS 평가 세트로 AUROC · macro F1 측정 |
| `평가결과.md` | 위 측정 결과 |
| `실행방법.md` | 실행 절차 상세 |

## 준비

이 폴더는 **탐지 모델(`model/`)과 `app_cpu.py` 를 가져다 씁니다.** 둘 다 이 저장소에 없습니다
(`.gitignore` 가 `*.safetensors` 를 막고 있고, 모델은 워크스테이션 산출물입니다).

`팀원배포` 패키지를 푼 폴더를 `APP_DIR` 로 지정하거나, 이 폴더 옆에 두십시오.

```
어딘가/
├─ 팀원배포/        ← app_cpu.py, model/ 이 있는 곳
└─ 웹챗봇/          ← 이 폴더
```

```bash
pip install fastapi uvicorn python-multipart requests pymupdf
cd frontend && npm install && npm run build && cd ..
python -m uvicorn api:app --port 8000
```

http://localhost:8000 으로 접속합니다. 자세한 건 `실행방법.md` 를 보십시오.

## 답변 생성

로컬 Ollama(`gemma3:1b`)를 씁니다. 노트북 CPU 에서 답변 1건에 6~14초 걸립니다.
Ollama 가 없으면 목업 답변으로 자동 전환되고 화면에 배지가 뜹니다.
**환각 판정은 어느 경우든 기존 탐지 모델이 합니다.**

## 알아 둘 점 두 가지

**긴 문서는 그대로 넣으면 안 됩니다.** 탐지 모델은 512 토큰까지만 봅니다.
넘으면 창을 여러 개로 쪼개 훑는데, 창별 확률이 서로를 눌러 **환각을 하나도 못 잡습니다.**
실측으로 문서가 500 토큰을 넘어가는 순간 탐지가 0 이 됐습니다.
그래서 `api.py` 가 질문과 겹치는 구간만 추려(`select_context`) 창 하나에 들어가게 줄입니다(`fit_for_detector`).

**임계값 0.35 는 MSDS 도메인에 맞지 않습니다.** `평가결과.md` 참고.
분리 자체는 되지만(AUROC 0.814) 확률 절대값이 낮아 0.35 에서 자르면 대부분 놓칩니다.

## 평가 실행

평가 세트(`examples_msds_toluene.jsonl`)는 이 저장소에 없습니다. 만든 사람에게 받아 경로를 지정하십시오.

```bash
set EVAL_DATA=...\examples_msds_toluene.jsonl
set APP_DIR=...\팀원배포
python evaluate.py
```
