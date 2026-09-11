# 3주차 중간 발표 초안

- [PPT 초안](output/3주차_중간발표_초안_v4.pptx): 표지 포함 7장. 편집 가능한 텍스트·비교표·아키텍처 구조도와 발표자 노트를 포함한다.
- [슬라이드 원고](3주차_중간발표_슬라이드원고.md): 장별 화면 본문, 발표 대본, 레이아웃 구성, 출처와 기술 보충 설명.
- [생성 코드](source/build_week3.mjs): 선택한 Business Review 템플릿을 불러와 내용을 반영하는 JavaScript.
- `source/astra_*.png`: 합성 자료 기반 로컬 데모의 실제 캡처. 화면 속 금액·시설·기관은 가상이다.

제목은 한국어 환각 탐지와 공간 시각화를 함께 드러내도록 수정했다. 최신 팀공유 문서 7절을 기준으로 구현 완료, 학습 완료 기록, 목업, 설계와 평가 계획을 구분한다. GraphRAG는 후속 관계 검색 확장으로 표시한다. 현재 현실 지도 엔진은 MapLibre다.

공고 건수는 월별 `adapt_report.json`, 분야 수치는 워크스테이션 통합 `sector_report.csv`, 표본 수는 `표본_목록.csv`를 사용한다. 모델 성능값은 원본 실험 기록이 이 저장소에 없어 본문에 넣지 않았다. 상세 출처는 원고와 각 슬라이드의 발표자 노트에 있다.

Business Review의 밝은 배경·파란 제목·구분선·설명 열·타임라인을 유지하고, 한국어 텍스트는 맑은 고딕으로 적용했다. 원본 템플릿 파일은 수정하지 않았다.

## 다시 생성하기

Codex의 bundled workspace dependencies와 presentation skill이 있는 환경에서 다음 환경변수를 설정한 뒤 해당 런타임의 Node로 `source/build_week3.mjs`를 실행한다.

| 변수 | 값 |
|---|---|
| `RUNTIME_NODE_MODULES` | bundled Node 패키지 디렉터리 |
| `RUNTIME_PYTHON` | bundled Python 실행 파일 |
| `PRESENTATION_SKILL` | presentations `SKILL.md`가 있는 디렉터리 |
| `BUSINESS_REVIEW_TEMPLATE` | 선택 템플릿의 `assets/reference.pptx` 절대 경로 |
| `DECK_REVISION` | 기존 최종본과 겹치지 않는 버전명 |

`.build/`는 렌더링·내부 검증용 임시 폴더로 Git에서 제외한다. 최종 PPTX, 원고와 필요한 생성 자료는 저장소에 커밋한다. 원천 공고 문서, 모델 가중치, 키는 포함하지 않는다.
