# 가상 인우블록 합성 시나리오 COST

합성 내부 검토 자료. 실제 기관 발급 증명서·견적서가 아니다. SC-QA300-C03-A / 2.0.0

## prices-1

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| prices / item_id | C03-SYN-PRICE-01 |
| prices / 인증명 | 개발·시험 라이선스 |
| prices / quantity | 1 units · 합성 설정값 |
| prices / unit_net | 1,800,000 KRW/unit · 합성 설정값 |
| prices / 공급가액 | 1,800,000 KRW · 계산값 · 산식: quantity * unit_net |
| prices / 통화 | KRW |
| prices / VAT 기준 | exclusive — VAT 제외 |
| prices / price_origin | synthetic_setting |
| prices / actual_supplier_quote_state | missing — 증빙 미확보 |
| prices / assumption_reason | 가용 인력의 내부 연습 원가에 외부비용을 더하기 위한 설계값. 시장 조사 가격·실제 견적이 아니며 규격 검증 미완료. |
| prices / application_period / 시작일 | 2026-06-01 |
| prices / application_period / 종료일 | 2026-12-10 |
| prices / application_period / 값의 성격 | synthetic_setting |
| prices / application_period / 지역 | 대한민국 내부 연습용 |
| prices / application_period / condition | 이 시나리오 과업 범위에만 적용. 실제 구매/공급 가능 여부는 미확정. |

## prices-2

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| prices / item_id | C03-SYN-PRICE-02 |
| prices / 인증명 | 추가 보안 점검 도구 |
| prices / quantity | 1 units · 합성 설정값 |
| prices / unit_net | 2,400,000 KRW/unit · 합성 설정값 |
| prices / 공급가액 | 2,400,000 KRW · 계산값 · 산식: quantity * unit_net |
| prices / 통화 | KRW |
| prices / VAT 기준 | exclusive — VAT 제외 |
| prices / price_origin | synthetic_setting |
| prices / actual_supplier_quote_state | missing — 증빙 미확보 |
| prices / assumption_reason | 가용 인력의 내부 연습 원가에 외부비용을 더하기 위한 설계값. 시장 조사 가격·실제 견적이 아니며 규격 검증 미완료. |
| prices / application_period / 시작일 | 2026-06-01 |
| prices / application_period / 종료일 | 2026-12-10 |
| prices / application_period / 값의 성격 | synthetic_setting |
| prices / application_period / 지역 | 대한민국 내부 연습용 |
| prices / application_period / condition | 이 시나리오 과업 범위에만 적용. 실제 구매/공급 가능 여부는 미확정. |

## labor_lines-1

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| labor_lines / 인력 ID | C03-P-02 |
| labor_lines / master_role | SW개발자 |
| labor_lines / 시작일 | 2026-06-01 |
| labor_lines / 종료일 | 2026-12-10 |
| labor_lines / 투입 FTE | 0.4 FTE · 합성 설정값 |
| labor_lines / month_prorata [1] / month | 2026-06 |
| labor_lines / month_prorata [1] / days | 30 |
| labor_lines / month_prorata [1] / denominator | 30 |
| labor_lines / month_prorata [1] / 값의 성격 | calculated |
| labor_lines / month_prorata [2] / month | 2026-07 |
| labor_lines / month_prorata [2] / days | 31 |
| labor_lines / month_prorata [2] / denominator | 31 |
| labor_lines / month_prorata [2] / 값의 성격 | calculated |
| labor_lines / month_prorata [3] / month | 2026-08 |
| labor_lines / month_prorata [3] / days | 31 |
| labor_lines / month_prorata [3] / denominator | 31 |
| labor_lines / month_prorata [3] / 값의 성격 | calculated |
| labor_lines / month_prorata [4] / month | 2026-09 |
| labor_lines / month_prorata [4] / days | 30 |
| labor_lines / month_prorata [4] / denominator | 30 |
| labor_lines / month_prorata [4] / 값의 성격 | calculated |
| labor_lines / month_prorata [5] / month | 2026-10 |
| labor_lines / month_prorata [5] / days | 31 |
| labor_lines / month_prorata [5] / denominator | 31 |
| labor_lines / month_prorata [5] / 값의 성격 | calculated |
| labor_lines / month_prorata [6] / month | 2026-11 |
| labor_lines / month_prorata [6] / days | 30 |
| labor_lines / month_prorata [6] / denominator | 30 |
| labor_lines / month_prorata [6] / 값의 성격 | calculated |
| labor_lines / month_prorata [7] / month | 2026-12 |
| labor_lines / month_prorata [7] / days | 10 |
| labor_lines / month_prorata [7] / denominator | 31 |
| labor_lines / month_prorata [7] / 값의 성격 | calculated |
| labor_lines / person_months_exact_decimal | 2.529032258064516129032258064 |
| labor_lines / 1인·1개월 기준급 | 4,490,000 KRW/person_month · 합성 설정값 |
| labor_lines / 사업주 부담 가정 | 20 percent · 합성 설정값 |
| labor_lines / labor_net | 13,626,426 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |

## labor_lines-2

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| labor_lines / 인력 ID | C03-P-03 |
| labor_lines / master_role | SW개발자 |
| labor_lines / 시작일 | 2026-06-01 |
| labor_lines / 종료일 | 2026-12-10 |
| labor_lines / 투입 FTE | 0.8 FTE · 합성 설정값 |
| labor_lines / month_prorata [1] / month | 2026-06 |
| labor_lines / month_prorata [1] / days | 30 |
| labor_lines / month_prorata [1] / denominator | 30 |
| labor_lines / month_prorata [1] / 값의 성격 | calculated |
| labor_lines / month_prorata [2] / month | 2026-07 |
| labor_lines / month_prorata [2] / days | 31 |
| labor_lines / month_prorata [2] / denominator | 31 |
| labor_lines / month_prorata [2] / 값의 성격 | calculated |
| labor_lines / month_prorata [3] / month | 2026-08 |
| labor_lines / month_prorata [3] / days | 31 |
| labor_lines / month_prorata [3] / denominator | 31 |
| labor_lines / month_prorata [3] / 값의 성격 | calculated |
| labor_lines / month_prorata [4] / month | 2026-09 |
| labor_lines / month_prorata [4] / days | 30 |
| labor_lines / month_prorata [4] / denominator | 30 |
| labor_lines / month_prorata [4] / 값의 성격 | calculated |
| labor_lines / month_prorata [5] / month | 2026-10 |
| labor_lines / month_prorata [5] / days | 31 |
| labor_lines / month_prorata [5] / denominator | 31 |
| labor_lines / month_prorata [5] / 값의 성격 | calculated |
| labor_lines / month_prorata [6] / month | 2026-11 |
| labor_lines / month_prorata [6] / days | 30 |
| labor_lines / month_prorata [6] / denominator | 30 |
| labor_lines / month_prorata [6] / 값의 성격 | calculated |
| labor_lines / month_prorata [7] / month | 2026-12 |
| labor_lines / month_prorata [7] / days | 10 |
| labor_lines / month_prorata [7] / denominator | 31 |
| labor_lines / month_prorata [7] / 값의 성격 | calculated |
| labor_lines / person_months_exact_decimal | 5.058064516129032258064516129 |
| labor_lines / 1인·1개월 기준급 | 4,490,000 KRW/person_month · 합성 설정값 |
| labor_lines / 사업주 부담 가정 | 20 percent · 합성 설정값 |
| labor_lines / labor_net | 27,252,852 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |

## labor_lines-3

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| labor_lines / 인력 ID | C03-P-04 |
| labor_lines / master_role | SW개발자 |
| labor_lines / 시작일 | 2026-06-01 |
| labor_lines / 종료일 | 2026-12-10 |
| labor_lines / 투입 FTE | 0.5 FTE · 합성 설정값 |
| labor_lines / month_prorata [1] / month | 2026-06 |
| labor_lines / month_prorata [1] / days | 30 |
| labor_lines / month_prorata [1] / denominator | 30 |
| labor_lines / month_prorata [1] / 값의 성격 | calculated |
| labor_lines / month_prorata [2] / month | 2026-07 |
| labor_lines / month_prorata [2] / days | 31 |
| labor_lines / month_prorata [2] / denominator | 31 |
| labor_lines / month_prorata [2] / 값의 성격 | calculated |
| labor_lines / month_prorata [3] / month | 2026-08 |
| labor_lines / month_prorata [3] / days | 31 |
| labor_lines / month_prorata [3] / denominator | 31 |
| labor_lines / month_prorata [3] / 값의 성격 | calculated |
| labor_lines / month_prorata [4] / month | 2026-09 |
| labor_lines / month_prorata [4] / days | 30 |
| labor_lines / month_prorata [4] / denominator | 30 |
| labor_lines / month_prorata [4] / 값의 성격 | calculated |
| labor_lines / month_prorata [5] / month | 2026-10 |
| labor_lines / month_prorata [5] / days | 31 |
| labor_lines / month_prorata [5] / denominator | 31 |
| labor_lines / month_prorata [5] / 값의 성격 | calculated |
| labor_lines / month_prorata [6] / month | 2026-11 |
| labor_lines / month_prorata [6] / days | 30 |
| labor_lines / month_prorata [6] / denominator | 30 |
| labor_lines / month_prorata [6] / 값의 성격 | calculated |
| labor_lines / month_prorata [7] / month | 2026-12 |
| labor_lines / month_prorata [7] / days | 10 |
| labor_lines / month_prorata [7] / denominator | 31 |
| labor_lines / month_prorata [7] / 값의 성격 | calculated |
| labor_lines / person_months_exact_decimal | 3.161290322580645161290322580 |
| labor_lines / 1인·1개월 기준급 | 4,490,000 KRW/person_month · 합성 설정값 |
| labor_lines / 사업주 부담 가정 | 20 percent · 합성 설정값 |
| labor_lines / labor_net | 17,033,032 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |

## labor_lines-4

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| labor_lines / 인력 ID | C03-P-05 |
| labor_lines / master_role | QA |
| labor_lines / 시작일 | 2026-06-01 |
| labor_lines / 종료일 | 2026-12-10 |
| labor_lines / 투입 FTE | 0.2 FTE · 합성 설정값 |
| labor_lines / month_prorata [1] / month | 2026-06 |
| labor_lines / month_prorata [1] / days | 30 |
| labor_lines / month_prorata [1] / denominator | 30 |
| labor_lines / month_prorata [1] / 값의 성격 | calculated |
| labor_lines / month_prorata [2] / month | 2026-07 |
| labor_lines / month_prorata [2] / days | 31 |
| labor_lines / month_prorata [2] / denominator | 31 |
| labor_lines / month_prorata [2] / 값의 성격 | calculated |
| labor_lines / month_prorata [3] / month | 2026-08 |
| labor_lines / month_prorata [3] / days | 31 |
| labor_lines / month_prorata [3] / denominator | 31 |
| labor_lines / month_prorata [3] / 값의 성격 | calculated |
| labor_lines / month_prorata [4] / month | 2026-09 |
| labor_lines / month_prorata [4] / days | 30 |
| labor_lines / month_prorata [4] / denominator | 30 |
| labor_lines / month_prorata [4] / 값의 성격 | calculated |
| labor_lines / month_prorata [5] / month | 2026-10 |
| labor_lines / month_prorata [5] / days | 31 |
| labor_lines / month_prorata [5] / denominator | 31 |
| labor_lines / month_prorata [5] / 값의 성격 | calculated |
| labor_lines / month_prorata [6] / month | 2026-11 |
| labor_lines / month_prorata [6] / days | 30 |
| labor_lines / month_prorata [6] / denominator | 30 |
| labor_lines / month_prorata [6] / 값의 성격 | calculated |
| labor_lines / month_prorata [7] / month | 2026-12 |
| labor_lines / month_prorata [7] / days | 10 |
| labor_lines / month_prorata [7] / denominator | 31 |
| labor_lines / month_prorata [7] / 값의 성격 | calculated |
| labor_lines / person_months_exact_decimal | 1.264516129032258064516129032 |
| labor_lines / 1인·1개월 기준급 | 4,720,000 KRW/person_month · 합성 설정값 |
| labor_lines / 사업주 부담 가정 | 20 percent · 합성 설정값 |
| labor_lines / labor_net | 7,162,219 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |

## labor_lines-5

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| labor_lines / 인력 ID | C03-P-06 |
| labor_lines / master_role | 운영엔지니어 |
| labor_lines / 시작일 | 2026-06-01 |
| labor_lines / 종료일 | 2026-12-10 |
| labor_lines / 투입 FTE | 0.2 FTE · 합성 설정값 |
| labor_lines / month_prorata [1] / month | 2026-06 |
| labor_lines / month_prorata [1] / days | 30 |
| labor_lines / month_prorata [1] / denominator | 30 |
| labor_lines / month_prorata [1] / 값의 성격 | calculated |
| labor_lines / month_prorata [2] / month | 2026-07 |
| labor_lines / month_prorata [2] / days | 31 |
| labor_lines / month_prorata [2] / denominator | 31 |
| labor_lines / month_prorata [2] / 값의 성격 | calculated |
| labor_lines / month_prorata [3] / month | 2026-08 |
| labor_lines / month_prorata [3] / days | 31 |
| labor_lines / month_prorata [3] / denominator | 31 |
| labor_lines / month_prorata [3] / 값의 성격 | calculated |
| labor_lines / month_prorata [4] / month | 2026-09 |
| labor_lines / month_prorata [4] / days | 30 |
| labor_lines / month_prorata [4] / denominator | 30 |
| labor_lines / month_prorata [4] / 값의 성격 | calculated |
| labor_lines / month_prorata [5] / month | 2026-10 |
| labor_lines / month_prorata [5] / days | 31 |
| labor_lines / month_prorata [5] / denominator | 31 |
| labor_lines / month_prorata [5] / 값의 성격 | calculated |
| labor_lines / month_prorata [6] / month | 2026-11 |
| labor_lines / month_prorata [6] / days | 30 |
| labor_lines / month_prorata [6] / denominator | 30 |
| labor_lines / month_prorata [6] / 값의 성격 | calculated |
| labor_lines / month_prorata [7] / month | 2026-12 |
| labor_lines / month_prorata [7] / days | 10 |
| labor_lines / month_prorata [7] / denominator | 31 |
| labor_lines / month_prorata [7] / 값의 성격 | calculated |
| labor_lines / person_months_exact_decimal | 1.264516129032258064516129032 |
| labor_lines / 1인·1개월 기준급 | 4,950,000 KRW/person_month · 합성 설정값 |
| labor_lines / 사업주 부담 가정 | 20 percent · 합성 설정값 |
| labor_lines / labor_net | 7,511,226 KRW · 계산값 · 산식: round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100)) |

## other_direct_net

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| other_direct_net | 1,200,000 KRW · 계산값 · 산식: assumed visits * assumed unit cost |

## calculation

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| calculation / 값의 성격 | calculated |
| calculation / 통화 | KRW |
| calculation / VAT 기준 | exclusive — VAT 제외 |
| calculation / VAT 가정 요율 | 10 percent · 합성 설정값 |
| calculation / scoped_direct_net | 73785755 |
| calculation / synthetic_external_net | 4200000 |
| calculation / original_agreement_gross | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| calculation / public_agreement_origin | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| calculation / original_agreement_inputs | 등록 항목 없음 (임의 보완하지 않음) |
| calculation / overhead_percent | 14 |
| calculation / contingency_percent | 5 |
| calculation / margin_percent | 17 |
| calculation / assumed_cost_net | 92803048 |
| calculation / target_net | 111810902 |
| calculation / target_gross | 122991992 |
| calculation / 산식 | direct = prior rounded scoped direct + synthetic external + (public agreement gross / 1.1 if supplied); cost = direct*(1+overhead/100+contingency/100); target_net = cost/(1-margin/100); target_gross = unrounded target_net*1.1; final KRW HALF_UP |

## actual_supplier_quote_state

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| actual_supplier_quote_state | missing — 증빙 미확보 |

## actual_bid_price

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| actual_bid_price | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |

## limitation

가상 인우블록 · C03 · astra-c03 · L3 · 상태 기준일 2026-06-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| limitation | 전체 과업과 제품의 적합성 검증 전 내부 연습 계산. 실제 제출 가능·시장 적정성·낙찰 가능성은 미확정. |
