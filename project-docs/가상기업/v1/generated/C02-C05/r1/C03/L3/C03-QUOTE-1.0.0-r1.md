# 가상 인우블록 공고별 공급사 견적 대장

R26BK01518315-000 / SC-C03-REVIEW-r1 / 1.0.0-r1

합성 검토 초안. 제출 승인·증빙 확보·색인 적재 모두 미완료.

## 합성 직접 경비 가정

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| item | 내부 검토용 현장 방문 경비 |
| quantity | 8 visits · 합성 설정값 |
| unit_net | 150,000 KRW/visit · 합성 설정값 |
| reason | 교통·현장 소모품을 묶은 계획 가정. 실제 공공 운임표나 업체 견적이 아니며 숙박·장비 구매·상용 라이선스는 포함하지 않음 |

## 외부 견적 미확보

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| supplier_quote_state | missing — 증빙 미확보 |
| supplier_quote_amount | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| pending [1] | 총괄책임자와 세부 개발 범위에 대한 발주처 협의 미완료 |
| pending [2] | 기술등급 및 제출용 경력·가입자 증명 확인 필요 |
| pending [3] | 기존 인프라 활용 전제이며 추가 상용SW·보안 도구 비용 미확정 |
| source_ids [1] | A-IC-PERIOD |
| source_ids [2] | A-IC-INFRA |
| source_ids [3] | A-IC-STAFF |
| source_ids [4] | S-IC-REGION |
| external_reference_ids | 등록 항목 없음 (임의 보완하지 않음) |
| resolution | 확인된 인건비·방문 가정은 계산. 동일 규격 공급 조건과 실제 확보 상태는 별도로 남김. |
