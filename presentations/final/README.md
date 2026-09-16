# ASTRA 최종발표 자료

기준: `origin/feature/sample-expansion-demo`의 `cb45470`

## 산출물

- `ASTRA_최종발표_v1.pptx`: 편집 가능한 16:9 발표 자료, 발표자 노트 포함
- `ASTRA_최종발표_v1.pdf`: 공유·검토용 PDF
- `ASTRA_최종발표_v1_발표자대본.md`: 15분 발표용 대본
- `ASTRA_최종발표_v1_사실검증표.md`: 슬라이드별 주장·근거·표현 제한
- `ASTRA_최종발표_v1_출처목록.md`: 사용한 저장소 출처와 정확성 제한
- `ASTRA_최종발표_v1_contact_sheet.png`: 전체 18장 미리보기
- `rendered/`: 슬라이드별 PNG 렌더링
- `source/build_final_deck.mjs`: artifact-tool 기반 재생성 스크립트

## 디자인과 편집성

- 기본 흐름과 색상 방향은 `output/visuals/ASTRA_Presentation_Storyboard_AwardStyle.svg`를 따른다.
- 사용자 질의와 전체 파이프라인은 제공 SVG의 구조를 참고해 PowerPoint 기본 도형으로 재구성했다. 모든 텍스트와 도형을 편집할 수 있고 한글 SVG 렌더링 차이를 피한다.
- 정량 그래프는 PowerPoint 네이티브 차트이며, 권한·모델·통합 평가 표는 네이티브 표다.

## 재생성

번들 런타임 환경 변수 `SKILL_DIR`, `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON`을 설정한 뒤 다음을 실행한다.

```bash
node presentations/final/source/build_final_deck.mjs
```

스크립트는 18장, 발표자 노트, 네이티브 표·차트, 승인 글꼴, 패키지 무결성과 레이아웃을 검사한 뒤 최종 PPTX를 저장한다.

## 정확성 제한

- KLUE·XLM-R·BGE-M3의 295답변 전체 비교 성능은 평가 진행 중이다.
- 25문항 검수는 접수됐지만 최종 사람 승인은 pending이다.
- 운영용 인증·인가와 L2·L3 자유 질문 Live DB 연결은 완료되지 않았다.
- 발표 자료에는 검증되지 않은 환각 탐지 또는 RAG 성능 수치를 넣지 않았다.
