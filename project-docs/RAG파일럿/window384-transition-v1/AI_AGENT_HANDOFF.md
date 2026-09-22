# ASTRA RAG Window 384 전환 · AI 에이전트 인계

> 이 문서는 자동 작성된 후속 작업 안내다. 최신 코드, `git log`, 실행 산출물과 검증 기록을 우선한다.

- GitHub: https://github.com/YangNaang2/ko-lettucedetect
- 구현 브랜치: `experiment/window384-transition-v1`
- 전환 구현 커밋: `18721d01acc897c382cb5bc018b21e75accd7469`
- 기준일: 2026-09-22

## 한 문장 요약

ASTRA RAG는 **Parent 1,800자·overlap 240자 구조를 유지**하면서, 각 Parent를 검색용으로 임베딩하는 Window를 **460토큰/stride 420에서 384토큰/stride 344로 변경**하고 RTX A5000에서 색인을 재구축·검증했다.

## 왜 바꿨는가

`project-docs/RAG파일럿/chunk-ablation-v1/`에서 8개 청크 구성을 292문항의 정답 근거 파일·문자 offset으로 비교했다. 자료는 이미 개발에 노출됐으므로 독립 테스트가 아니라 회고적 개발 비교다.

| 구성 | Hit@1 | Hit@4 보조지표 | Hit@6 | MRR@6 |
|---|---:|---:|---:|---:|
| Parent 1,800 / Window 460 | 49.66% | 73.29% | 78.42% | 60.37% |
| Parent 1,800 / Window 384 | **50.00%** | **74.66%** | **79.79%** | **60.96%** |
| Parent 1,800 / Window 256 | 47.95% | 73.97% | **80.14%** | 60.01% |

384는 256보다 Window 수가 적으면서 첫 근거 순위와 실제 생성 top4 도달률이 높아 균형 후보로 선택했다. 384와 460의 차이는 292건 중 Hit@6 순증 4건이며 신뢰구간이 겹친다. 확정적인 일반화 우위로 표현하면 안 된다.

## 변경 내용

`procurement-pipeline/rag_pilot_embedding.py`

- `token_window`: 460 → 384
- `stride`: 420 → 344
- CUDA가 없으면 CPU로 자동 전환하지 않고 오류 처리
- 모델과 입력 tensor를 CUDA에 적재
- `embedding_config.json`에 `device=cuda`, 실제 GPU 이름 기록

변경하지 않은 항목:

- Parent 최대 1,800자
- Parent overlap 240자
- lexical+dense RRF와 ACL 선필터
- 생성 모델의 `max_evidence_chunks=4`
- 기존 300개 답변과 환각 탐지 결과

## 실제 재구축 결과

- GPU: NVIDIA RTX A5000
- 전체 문서·질문 재구축: 43.60초
- 문서 Window 임베딩: 27.25초
- Parent: 3,275개
- Window: 8,901개
- 벡터 shape: `8901 × 384`
- 문항 벡터: 275개
- float32, attention-mask mean pooling, L2 normalization
- NaN/Inf: 0건
- norm 범위: 0.99999988–1.00000012

검증 기록은 `project-docs/RAG파일럿/workstation-275/validation/window384-transition.json`에 있다. Dense 로드 후 275문항 모두 검색을 완료했고 각 문항에서 상위 6개가 반환됐다. 전체 자동검사 190개가 통과했다.

## Git에 없는 로컬 산출물

대형·실행 전용 파일은 Git에 넣지 않는다.

- 새 벡터: `work/rag-workstation-275/vectors.npz`
- 새 질문 벡터: `work/rag-workstation-275/query_vectors.npz`
- W460 백업: 같은 폴더의 `*.bak-w460`
- W460 설정 백업: `project-docs/RAG파일럿/workstation-275/embedding_config.json.bak-w460` 로컬 파일

새 PC에서 Git만 받아서는 새 벡터가 생기지 않는다. 동일한 검증 원천, E5 revision과 GPU 환경에서 `workstation_rag.configure()` 후 `rag_pilot_embedding.build()`와 `query_vectors()`를 실행해야 한다.

## 해석 제한

이번 작업은 검색 색인 전환이다. 다음은 아직 검증하지 않았다.

- W384로 새 답변을 생성했을 때 답변 정확도가 향상되는지
- 환각 발생률이나 탐지 성능이 향상되는지
- 독립 신규 질문에서 개선이 재현되는지
- 운영 UI와 배포 서버가 새 로컬 벡터를 실제 사용하는지

따라서 발표에서는 “검색 근거 도달률 비교에 따라 384토큰 후보로 전환하고 색인 무결성과 275문항 검색 연결을 검증했다”고 말한다. “RAG 정확도 또는 환각 성능이 향상됐다”고 말하지 않는다.

## 후속 AI 에이전트 시작 프롬프트

다음을 복사해 사용한다.

> GitHub 저장소 `https://github.com/YangNaang2/ko-lettucedetect`와 `project-docs/RAG파일럿/window384-transition-v1/AI_AGENT_HANDOFF.md`를 먼저 읽어라. 현재 작업·미커밋 변경·실행 프로세스를 보존하고 최신 main을 확인해라. ASTRA RAG의 Parent 1,800자/overlap 240자는 유지하며 임베딩 Window 384/stride 344 설정과 `window384-transition.json` 검증을 기준으로 작업해라. 모델 작업은 CUDA GPU를 사용하고 CPU로 자동 대체하지 마라. 기존 W460 벡터·정본 답변·원천·평가 결과를 덮어쓰지 말고 새 실험은 별도 run ID와 경로를 사용해라. 검색 지표, 답변 품질, 환각 탐지 성능을 구분하고 검증되지 않은 향상을 주장하지 마라. 요청받은 후속 작업을 실제 실행·검증하고 명령·환경·코드·결과 해시를 남겨라.
