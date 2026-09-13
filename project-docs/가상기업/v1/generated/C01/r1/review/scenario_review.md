# 한빛IT 대표 공고 검토 초안

L3 · astra-c01 · cost_analyst/bid_approver · 검색 적재 금지.

## 실행 차단 및 제한된 원가 예시

가상 한빛IT · C01 · astra-c01 · L3 · 상태 기준일 2026-04-01

합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.
문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.

| 항목 | 값 |
|---|---|
| schema_version | 1.0.0 |
| 회사 ID | C01 |
| tenant_id | astra-c01 |
| 보안등급 | L3 |
| allowed_roles [1] | cost_analyst |
| allowed_roles [2] | bid_approver |
| rag_ingest | 아니오 |
| purpose | offline_planning_review_only |
| source_scenario / scenario_id | SC-WB-C01 |
| source_scenario / bid_key | R26BK01487327-000 |
| source_scenario / 회사 ID | C01 |
| source_scenario / mode | solo |
| source_scenario / decision_as_of | 2026-04-01 |
| source_scenario / 상태 | draft_not_submitted |
| source_scenario / mutually_exclusive_group | C01-2026-OPTIONS |
| source_scenario / allocation_policy | draft alternatives do not consume capacity until committed |
| source_scenario / staffing [1] / 인력 ID | C01-P-03 |
| source_scenario / staffing [1] / 시작일 | 2026-06-01 |
| source_scenario / staffing [1] / 종료일 | 2026-12-17 |
| source_scenario / staffing [1] / 투입 FTE | 0.5 FTE · 합성 설정값 |
| source_scenario / joint_members | 등록 항목 없음 (임의 보완하지 않음) |
| source_scenario / supplier_quotes | 등록 항목 없음 (임의 보완하지 않음) |
| source_scenario / cost_sheet | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| source_scenario / bid_price | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| execution_gate | blocked_not_a_submission_plan |
| blockers [1] / 업종·인증 코드 | SOLO_0036_NOT_HELD |
| blockers [1] / source_ids [1] | S-WB-0036 |
| blockers [1] / master_pointer | /companies/0/known_absences/0 |
| blockers [1] / note | 현재 단독 모드의 0036 조건 미충족. 업체 사실 변경 또는 임의 공동수급 승인 금지. |
| blockers [2] / 업종·인증 코드 | NOTICE_YEAR_UNRESOLVED |
| blockers [2] / source_ids [1] | S-WB-YEAR |
| blockers [2] / source_ids [2] | S-WB-DEADLINE |
| blockers [2] / source_ids [3] | S-WB-AMOUNT |
| blockers [2] / master_pointer | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| blockers [2] / note | 2025-04-24 말미 날짜와 2026-05-15 제출 일정의 연도 불일치. 최근 3년 실적 계산 보류. |
| staffing_check | existing_plus_this_independent_draft_within_capacity |
| staffing_basis | 기존 시나리오의 날짜·0.5 FTE를 그대로 재사용한 합성 대안; 발주기관 필수 투입량·실제 착수일이 아님 |
| cost_example / value | 2436700 |
| cost_example / unit | KRW/full_month |
| cost_example / 값의 성격 | calculated |
| cost_example / VAT 기준 | exclusive — VAT 제외 |
| cost_example / scope | C01-P-03 한 명의 온전한 1개월 0.5 FTE 직접 인건비 예시만. 전체 견적·투찰가 아님 |
| cost_example / 산식 | round_half_up(monthly_base * 0.5 * (1 + employer_burden / 100)) |
| cost_example / master_pointers [1] | /companies/0/personnel/2 |
| cost_example / master_pointers [2] | /companies/0/l3_policy/labor_rates/1 |
| period_person_months | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| supplier_quote_amount | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| total_direct_cost | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| total_cost | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| bid_price | null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음 |
| missing_inputs [1] | 실제 착수일·과업별 필요 인원·투입률 |
| missing_inputs [2] | 월 중 종료의 공수/일할계산 정책 |
| missing_inputs [3] | 외부 견적·기타 직접비 |
| missing_inputs [4] | 참여 방식 해소 및 공식 공고 기준일 |
| approval_status | not_approved |
| index_status | not_indexed |
