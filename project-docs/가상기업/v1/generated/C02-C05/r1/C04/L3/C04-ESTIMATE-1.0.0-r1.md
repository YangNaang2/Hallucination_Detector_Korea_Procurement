# 가상 누리클라우드 공고별 원가 산출표

R26BK01574547-000 / SC-C04-REVIEW-r1 / 1.0.0-r1

합성 검토 초안. 제출 승인·증빙 확보·색인 적재 모두 미완료.

## 계산 범위 및 미확정 총액

가상 누리클라우드 · C04 · astra-c04 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| 통화 | KRW |
| VAT 기준 | exclusive — VAT 제외 |
| 값의 성격 | calculated |
| labor_net | 19,972,260 KRW · 계산값 · 산식: round_half_up(sum(unrounded labor lines)) |
| row_rounding_difference | 0 KRW · 계산값 · 산식: rounded total - sum(rounded rows) |
| other_direct_net | 600,000 KRW · 계산값 · 산식: assumed visits * assumed unit cost |
| scoped_direct_net | 20,572,260 KRW · 계산값 · 산식: unrounded labor + assumed visits |
| scoped_cost_net | 24,686,712 KRW · 계산값 · 산식: scoped direct * (1+overhead/100+contingency/100) |
| scope | 자체 인력과 합성 방문 경비만. 장비·클라우드·외부SW 및 전체 사업 원가는 아님. |
| supplier_quote_state | missing — 증빙 미확보 |
| supplier_quote_net | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| total_project_cost | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| bid_price | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |

## C04-P-07 인건비

가상 누리클라우드 · C04 · astra-c04 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| 인력 ID | C04-P-07 |
| master_role | 클라우드PM |
| 시작일 | 2026-06-01 |
| 종료일 | 2026-12-31 |
| 투입 FTE | 0.15 FTE · 합성 설정값 |
| month_prorata [1] / month | 2026-06 |
| month_prorata [1] / days | 30 |
| month_prorata [1] / denominator | 30 |
| month_prorata [1] / 값의 성격 | calculated |
| month_prorata [2] / month | 2026-07 |
| month_prorata [2] / days | 31 |
| month_prorata [2] / denominator | 31 |
| month_prorata [2] / 값의 성격 | calculated |
| month_prorata [3] / month | 2026-08 |
| month_prorata [3] / days | 31 |
| month_prorata [3] / denominator | 31 |
| month_prorata [3] / 값의 성격 | calculated |
| month_prorata [4] / month | 2026-09 |
| month_prorata [4] / days | 30 |
| month_prorata [4] / denominator | 30 |
| month_prorata [4] / 값의 성격 | calculated |
| month_prorata [5] / month | 2026-10 |
| month_prorata [5] / days | 31 |
| month_prorata [5] / denominator | 31 |
| month_prorata [5] / 값의 성격 | calculated |
| month_prorata [6] / month | 2026-11 |
| month_prorata [6] / days | 30 |
| month_prorata [6] / denominator | 30 |
| month_prorata [6] / 값의 성격 | calculated |
| month_prorata [7] / month | 2026-12 |
| month_prorata [7] / days | 31 |
| month_prorata [7] / denominator | 31 |
| month_prorata [7] / 값의 성격 | calculated |
| person_months_exact_decimal | 1.05 |
| 1인·1개월 기준급 | 4,440,000 KRW/person_month · 합성 설정값 |
| 사업주 부담 가정 | 21 percent · 합성 설정값 |
| labor_net | 5,641,020 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |

## C04-P-03 인건비

가상 누리클라우드 · C04 · astra-c04 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| 인력 ID | C04-P-03 |
| master_role | 운영엔지니어 |
| 시작일 | 2026-06-01 |
| 종료일 | 2026-12-31 |
| 투입 FTE | 0.25 FTE · 합성 설정값 |
| month_prorata [1] / month | 2026-06 |
| month_prorata [1] / days | 30 |
| month_prorata [1] / denominator | 30 |
| month_prorata [1] / 값의 성격 | calculated |
| month_prorata [2] / month | 2026-07 |
| month_prorata [2] / days | 31 |
| month_prorata [2] / denominator | 31 |
| month_prorata [2] / 값의 성격 | calculated |
| month_prorata [3] / month | 2026-08 |
| month_prorata [3] / days | 31 |
| month_prorata [3] / denominator | 31 |
| month_prorata [3] / 값의 성격 | calculated |
| month_prorata [4] / month | 2026-09 |
| month_prorata [4] / days | 30 |
| month_prorata [4] / denominator | 30 |
| month_prorata [4] / 값의 성격 | calculated |
| month_prorata [5] / month | 2026-10 |
| month_prorata [5] / days | 31 |
| month_prorata [5] / denominator | 31 |
| month_prorata [5] / 값의 성격 | calculated |
| month_prorata [6] / month | 2026-11 |
| month_prorata [6] / days | 30 |
| month_prorata [6] / denominator | 30 |
| month_prorata [6] / 값의 성격 | calculated |
| month_prorata [7] / month | 2026-12 |
| month_prorata [7] / days | 31 |
| month_prorata [7] / denominator | 31 |
| month_prorata [7] / 값의 성격 | calculated |
| person_months_exact_decimal | 1.75 |
| 1인·1개월 기준급 | 4,900,000 KRW/person_month · 합성 설정값 |
| 사업주 부담 가정 | 21 percent · 합성 설정값 |
| labor_net | 10,375,750 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |

## C04-P-08 인건비

가상 누리클라우드 · C04 · astra-c04 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| 인력 ID | C04-P-08 |
| master_role | 보안엔지니어 |
| 시작일 | 2026-06-01 |
| 종료일 | 2026-12-31 |
| 투입 FTE | 0.1 FTE · 합성 설정값 |
| month_prorata [1] / month | 2026-06 |
| month_prorata [1] / days | 30 |
| month_prorata [1] / denominator | 30 |
| month_prorata [1] / 값의 성격 | calculated |
| month_prorata [2] / month | 2026-07 |
| month_prorata [2] / days | 31 |
| month_prorata [2] / denominator | 31 |
| month_prorata [2] / 값의 성격 | calculated |
| month_prorata [3] / month | 2026-08 |
| month_prorata [3] / days | 31 |
| month_prorata [3] / denominator | 31 |
| month_prorata [3] / 값의 성격 | calculated |
| month_prorata [4] / month | 2026-09 |
| month_prorata [4] / days | 30 |
| month_prorata [4] / denominator | 30 |
| month_prorata [4] / 값의 성격 | calculated |
| month_prorata [5] / month | 2026-10 |
| month_prorata [5] / days | 31 |
| month_prorata [5] / denominator | 31 |
| month_prorata [5] / 값의 성격 | calculated |
| month_prorata [6] / month | 2026-11 |
| month_prorata [6] / days | 30 |
| month_prorata [6] / denominator | 30 |
| month_prorata [6] / 값의 성격 | calculated |
| month_prorata [7] / month | 2026-12 |
| month_prorata [7] / days | 31 |
| month_prorata [7] / denominator | 31 |
| month_prorata [7] / 값의 성격 | calculated |
| person_months_exact_decimal | 0.7 |
| 1인·1개월 기준급 | 4,670,000 KRW/person_month · 합성 설정값 |
| 사업주 부담 가정 | 21 percent · 합성 설정값 |
| labor_net | 3,955,490 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |
