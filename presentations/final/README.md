# ASTRA 발표 자료 초안

기준: `origin/feature/sample-expansion-demo`의 `cb45470`

## 산출물

### 내용 확장 초안 v2

- `ASTRA_최종발표_내용확장_초안_v2.pptx`: 팀 편집용 16:9 초안, 본편 30장과 부록 3장
- `ASTRA_최종발표_내용확장_초안_v2.pdf`: 33장 검토용 미리보기
- `ASTRA_최종발표_내용확장_초안_v2_발표메모.md`: 팀이 대본을 작성할 때 참고할 슬라이드별 핵심 메시지
- `ASTRA_최종발표_내용확장_초안_v2_사실검증표.md`: 주장·수치·근거·표현 제한
- `ASTRA_최종발표_내용확장_초안_v2_출처목록.md`: 저장소 내부 출처와 발표 시 주의할 해석
- `ASTRA_최종발표_내용확장_초안_v2_contact_sheet.png`: 전체 33장 미리보기
- `rendered-draft-v2/`: 슬라이드별 PNG 렌더링
- `source/build_final_deck_v2.mjs`: 확장 초안 재생성 스크립트

v2는 최종본이 아니다. 수집·가공·합성 데이터·권한형 RAG·생성·라벨링·탐지 평가를 팀이 선택해서 줄이거나 재배치할 수 있도록 근거와 세부 내용을 넉넉히 넣었다. 발표 대본은 팀이 별도로 작성하는 것을 전제로 참고 메모만 제공한다.

### 이전 압축안 v1

- `ASTRA_최종발표_v1.pptx`: 편집 가능한 16:9 발표 자료, 발표자 노트 포함
- `ASTRA_최종발표_v1.pdf`: 공유·검토용 PDF
- `ASTRA_최종발표_v1_발표자대본.md`: 15분 발표용 대본
- `ASTRA_최종발표_v1_사실검증표.md`: 슬라이드별 주장·근거·표현 제한
- `ASTRA_최종발표_v1_출처목록.md`: 사용한 저장소 출처와 정확성 제한
- `ASTRA_최종발표_v1_contact_sheet.png`: 전체 18장 미리보기
- `rendered/`: 슬라이드별 PNG 렌더링
- `source/build_final_deck.mjs`: artifact-tool 기반 재생성 스크립트

## 디자인과 편집성

- 기본 흐름은 `output/visuals/ASTRA_Presentation_Storyboard_AwardStyle.svg`를 따른다.
- v2는 밝은 배경의 기술 보고서형 초안이며, 사용자가 제공한 C4_AI PDF는 정보 밀도 참고에만 사용했다.
- 사용자 질의와 전체 파이프라인은 제공 SVG의 구조를 참고해 PowerPoint 기본 도형으로 재구성했다. 모든 텍스트와 도형을 편집할 수 있고 한글 SVG 렌더링 차이를 피한다.
- 정량 그래프는 PowerPoint 네이티브 차트이며, 권한·모델·통합 평가 표는 네이티브 표다.

## 재생성

번들 런타임 환경 변수 `SKILL_DIR`, `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON`을 설정한 뒤 다음을 실행한다.

```bash
node presentations/final/source/build_final_deck.mjs
```

v1 스크립트는 18장을, v2 스크립트는 33장을 생성한다. 두 스크립트 모두 발표자 노트, 네이티브 표·차트, 승인 글꼴, 패키지 무결성과 레이아웃을 검사한 뒤 PPTX를 저장한다.

## 정확성 제한

- KLUE·XLM-R·BGE-M3의 295답변 전체 비교 성능은 평가 진행 중이다.
- 25문항 검수는 접수됐지만 최종 사람 승인은 pending이다.
- 운영용 인증·인가와 L2·L3 자유 질문 Live DB 연결은 완료되지 않았다.
- 발표 자료에는 검증되지 않은 환각 탐지 또는 RAG 성능 수치를 넣지 않았다.
