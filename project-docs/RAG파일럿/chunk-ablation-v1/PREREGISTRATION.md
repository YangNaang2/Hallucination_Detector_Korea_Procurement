# 청크 크기 비교 실험 사전 명세

기준일: 2026-09-22. 이 파일의 설정과 지표를 결과 확인 전에 고정한다.

## 목적과 범위

기존 300문항 중 정상 접근 차단 5건을 제외한 295건에는 문항별 공개 원문 근거의 파일 SHA-256과 문자 offset이 있다. 동일한 원천, 권한 필터, `multilingual-e5-small`, lexical+dense RRF를 유지하고 청크 설정만 바꿔 공개 근거 검색을 비교한다. 답변 생성은 실행하지 않는다.

이 자료는 이미 개발·검토에 노출됐으므로 독립 테스트가 아니라 **회고적 개발 비교**다. 결과를 보고 설정이나 지표를 바꾸지 않는다.

## 고정 비교군

| ID | 생성에 전달할 Parent | 임베딩 Window | 목적 |
|---|---:|---:|---|
| flat-token-460 | 460토큰 Window 자체 | 460 / stride 420 | 작은 청크만 쓰는 방식 |
| parent-900-w460 | 900자 / overlap 120자 | 460 / stride 420 | 작은 Parent |
| parent-1200-w460 | 1,200자 / overlap 160자 | 460 / stride 420 | 중간 Parent |
| parent-1800-first460 | 1,800자 / overlap 240자 | 첫 460토큰만 | 긴 Parent를 잘라 임베딩하는 대조군 |
| parent-1800-w256 | 1,800자 / overlap 240자 | 256 / stride 216 | 작은 검색 Window |
| parent-1800-w384 | 1,800자 / overlap 240자 | 384 / stride 344 | 중간 검색 Window |
| parent-1800-w460 | 1,800자 / overlap 240자 | 460 / stride 420 | 현재 구성 |
| parent-2400-w460 | 2,400자 / overlap 320자 | 460 / stride 420 | 큰 Parent |

`first460` 외에는 모든 토큰을 Window로 덮는다. 공개 공고 Parent만 크기를 바꾸고 가상기업·시나리오 엔터티 청크는 원래 경계를 보존한다.

## 고정 지표

- Gold evidence Hit@1, Hit@3, Hit@6: 상위 k Parent 중 하나라도 정답 파일·offset과 겹치는 문항 비율
- Evidence Recall@6: 문항별 여러 정답 근거 중 상위 6개가 찾은 비율의 평균
- MRR@6: 첫 정답 Parent 순위의 역수
- Gold character coverage@6: 정답 offset 중 상위 6개 Parent가 덮은 문자 비율
- top4 context characters: 실제 생성 제한과 같은 상위 4개 Parent 본문 문자량
- Parent 수, Window 수, 실제 임베딩 입력 토큰 수, 벡터 메모리
- 색인 구축 시간과 문항당 검색 지연 중앙값·p95

동률 순서는 `chunk_id`로 고정한다. 현재 운영 채택 판단의 우선순위는 Hit@6, MRR@6, top4 문맥량, 구축·검색 비용 순으로 기술하되 단일 종합점수를 사후 제작하지 않는다.

## 해석 제한

- 정답 offset은 사람 최종 승인 전 평가 자료를 포함한다.
- 검색 지표이며 최종 답변 정확도나 환각률이 아니다.
- 한 대의 RTX A5000에서 실행한 시간은 해당 환경의 비교값이다.
- `test` split도 이전 작업에 노출됐으므로 독립 일반화 결과라고 부르지 않는다.
