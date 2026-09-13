# 가상 해온시스템 공고별 공급사 견적 대장

R26BK01474723-000 / SC-C02-REVIEW-r1 / 1.0.0-r1

합성 검토 초안. 제출 승인·증빙 확보·색인 적재 모두 미완료.

## 합성 직접 경비 가정

가상 해온시스템 · C02 · astra-c02 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| item | 내부 검토용 현장 방문 경비 |
| quantity | 8 visits · 합성 설정값 |
| unit_net | 150,000 KRW/visit · 합성 설정값 |
| reason | 교통·현장 소모품을 묶은 계획 가정. 실제 공공 운임표나 업체 견적이 아니며 숙박·장비 구매·상용 라이선스는 포함하지 않음 |

## 외부 견적 미확보

가상 해온시스템 · C02 · astra-c02 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| supplier_quote_state | missing — 증빙 미확보 |
| supplier_quote_amount | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| pending [1] | 기술지원 확약서 미확보(계약 전 제출 의무) |
| pending [2] | 중급 기술자 1명의 부분 투입만으로 장애 2시간 도착·4시간 복구 및 대체 인력 확보 여부 미검증 |
| pending [3] | 장비 교체·부품 비용 범위 및 공급사 최종 적용 조건 미확정 |
| source_ids [1] | A-BS-PERIOD |
| source_ids [2] | S-BS-STAFF |
| source_ids [3] | A-BS-SLA |
| source_ids [4] | A-BS-CONFIRM |
| source_ids [5] | A-BS-SUPPORT |
| source_ids [6] | A-BS-AGREEMENT-1 |
| source_ids [7] | A-BS-AGREEMENT-2 |
| external_reference_ids | 등록 항목 없음 (임의 보완하지 않음) |
| resolution | 확인된 인건비·방문 가정은 계산. 동일 규격 공급 조건과 실제 확보 상태는 별도로 남김. |

## 공개 협약 가격의 범위

가상 해온시스템 · C02 · astra-c02 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| source_ids [1] | A-BS-AGREEMENT-1 |
| source_ids [2] | A-BS-AGREEMENT-2 |
| source_ids [3] | A-BS-SUPPORT |
| amount | 56,320,240 KRW · 계산값 · 산식: 32628780 + 23691460 (A-BS-AGREEMENT-1/2) |
| VAT 기준 | inclusive — VAT 포함 |
| scope | 영상중계·통합플랫폼 SW 및 네트워크·보안 HW 두 협약 합계. 확인일 2026-09-13; 공고의 2026년 과업 참고. |
| company_quote | missing; C02 명의 확약서·견적서 아님 |
