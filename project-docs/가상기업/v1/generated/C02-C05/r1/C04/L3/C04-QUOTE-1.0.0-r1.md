# 가상 누리클라우드 공고별 공급사 견적 대장

R26BK01574547-000 / SC-C04-REVIEW-r1 / 1.0.0-r1

합성 검토 초안. 제출 승인·증빙 확보·색인 적재 모두 미완료.

## 합성 직접 경비 가정

가상 누리클라우드 · C04 · astra-c04 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| item | 내부 검토용 현장 방문 경비 |
| quantity | 4 visits · 합성 설정값 |
| unit_net | 150,000 KRW/visit · 합성 설정값 |
| reason | 교통·현장 소모품을 묶은 계획 가정. 실제 공공 운임표나 업체 견적이 아니며 숙박·장비 구매·상용 라이선스는 포함하지 않음 |

## 외부 견적 미확보

가상 누리클라우드 · C04 · astra-c04 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| supplier_quote_state | missing — 증빙 미확보 |
| supplier_quote_amount | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| pending [1] | 공급 대상 서비스 CSAP 증빙 missing |
| pending [2] | 공급 계약·권한 missing |
| pending [3] | 서버·스토리지·트래픽·보안·솔루션을 포함하는 전체 동일 규격 공급가격 미확정 |
| source_ids [1] | A-CL-PERIOD |
| source_ids [2] | A-CL-SPEC |
| source_ids [3] | S-CL-CSAP |
| source_ids [4] | S-CL-ISMS |
| external_reference_ids [1] | W-NCLOUD |
| resolution | 확인된 인건비·방문 가정은 계산. 동일 규격 공급 조건과 실제 확보 상태는 별도로 남김. |
