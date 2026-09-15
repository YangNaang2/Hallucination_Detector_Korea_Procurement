# 정답 확인 후 선별한 성공 사례 100건

**성공 사례를 사후 선별한 시연용 집합입니다. 전체 성능이나 독립 테스트 결과가 아닙니다. 기존 사람 미승인 에이전트 라벨 기준입니다.**

- 원본 생성 답변 295건에서 정상 무경고 50건, 실제 환각 구절을 포착한 50건을 골랐습니다.
- 학습 57건, 개발 22건, 기존 노출 비교 21건입니다.
- 선별 집합의 답변 정확도·정밀도·재현율·F1: 모두 **100%** (TP 50, TN 50, FP 0, FN 0). 맞힌 답변만 골랐으므로 생기는 값이며 모델의 일반 성능을 입증하지 않습니다.
- 선별 집합의 문자 정밀도 **86.11%**, 재현율 **59.08%**, F1 **70.08%**. 정확한 구절 경계 exact-span F1 **0.00%**. 오류 구절 전체를 완벽하게 탐지했다는 뜻이 아닙니다.
- 별도로 고정 추출한 100건의 실제 잠정 평가에서는 채점 가능 96건의 정확도가 **67.71%**였습니다.

발표 문구: “정상 답변 무경고와 환각 포착이 성공한 사례 100건을 선별하여 시스템 동작을 시연했습니다.”

| ID | 사례 | 자료 구분 |
|---|---|---|
| ASTRA-300-C01-N02-E5 | 정상 무경고 | evaluation |
| ASTRA-300-C01-N13-E4 | 정상 무경고 | evaluation |
| ASTRA-300-C01-N32-E5 | 정상 무경고 | evaluation |
| ASTRA-300-C03-N02-E2 | 정상 무경고 | evaluation |
| ASTRA-300-C03-N17-E2 | 정상 무경고 | evaluation |
| ASTRA-300-C03-N44-E5 | 정상 무경고 | evaluation |
| ASTRA-300-C04-N32-E3 | 정상 무경고 | evaluation |
| ASTRA-300-C05-N13-E3 | 정상 무경고 | evaluation |
| ASTRA-300-C05-N17-E4 | 정상 무경고 | evaluation |
| ASTRA-300-C05-N36-E5 | 정상 무경고 | evaluation |
| ASTRA-300-C05-N44-E2 | 정상 무경고 | evaluation |
| ASTRA-300-C05-P05 | 정상 무경고 | evaluation |
| ASTRA-300-C01-N07-E5 | 정상 무경고 | dev |
| ASTRA-300-C02-N45-E3 | 정상 무경고 | dev |
| ASTRA-300-C03-N03-E1 | 정상 무경고 | dev |
| ASTRA-300-C03-N45-E4 | 정상 무경고 | dev |
| ASTRA-300-C04-N45-E5 | 정상 무경고 | dev |
| ASTRA-300-C05-N07-E4 | 정상 무경고 | dev |
| ASTRA-300-C05-N29-E2 | 정상 무경고 | dev |
| ASTRA-300-C05-N46-E5 | 정상 무경고 | dev |
| ASTRA-300-C01-N12-E5 | 정상 무경고 | train |
| ASTRA-300-C01-N16-E1 | 정상 무경고 | train |
| ASTRA-300-C01-N21-E1 | 정상 무경고 | train |
| ASTRA-300-C01-N31-E1 | 정상 무경고 | train |
| ASTRA-300-C01-N33-E4 | 정상 무경고 | train |
| ASTRA-300-C01-N49-E3 | 정상 무경고 | train |
| ASTRA-300-C01-P01 | 정상 무경고 | train |
| ASTRA-300-C01-P03 | 정상 무경고 | train |
| ASTRA-300-C01-P04 | 정상 무경고 | train |
| ASTRA-300-C01-S01 | 정상 무경고 | train |
| ASTRA-300-C01-S02 | 정상 무경고 | train |
| ASTRA-300-C02-N05-E3 | 정상 무경고 | train |
| ASTRA-300-C02-N19-E4 | 정상 무경고 | train |
| ASTRA-300-C02-N23-E5 | 정상 무경고 | train |
| ASTRA-300-C02-N24-E4 | 정상 무경고 | train |
| ASTRA-300-C02-N26-E2 | 정상 무경고 | train |
| ASTRA-300-C02-N37-E1 | 정상 무경고 | train |
| ASTRA-300-C02-N39-E4 | 정상 무경고 | train |
| ASTRA-300-C02-N48-E5 | 정상 무경고 | train |
| ASTRA-300-C02-P01 | 정상 무경고 | train |
| ASTRA-300-C03-N01-E3 | 정상 무경고 | train |
| ASTRA-300-C03-N04-E5 | 정상 무경고 | train |
| ASTRA-300-C03-N12-E2 | 정상 무경고 | train |
| ASTRA-300-C03-N24-E5 | 정상 무경고 | train |
| ASTRA-300-C03-N26-E3 | 정상 무경고 | train |
| ASTRA-300-C03-N41-E3 | 정상 무경고 | train |
| ASTRA-300-C03-N42-E2 | 정상 무경고 | train |
| ASTRA-300-C03-N49-E5 | 정상 무경고 | train |
| ASTRA-300-C03-P01 | 정상 무경고 | train |
| ASTRA-300-C03-P03 | 정상 무경고 | train |
| ASTRA-300-C01-N22-E5 | 환각 구절 포착 | evaluation |
| ASTRA-300-C01-N36-E1 | 환각 구절 포착 | evaluation |
| ASTRA-300-C02-N20-E3 | 환각 구절 포착 | evaluation |
| ASTRA-300-C02-N44-E4 | 환각 구절 포착 | evaluation |
| ASTRA-300-C02-N47-E1 | 환각 구절 포착 | evaluation |
| ASTRA-300-C04-N13-E2 | 환각 구절 포착 | evaluation |
| ASTRA-300-C05-N20-E1 | 환각 구절 포착 | evaluation |
| ASTRA-300-C05-S01 | 환각 구절 포착 | evaluation |
| ASTRA-300-C05-S03 | 환각 구절 포착 | evaluation |
| ASTRA-300-C01-N30-E2 | 환각 구절 포착 | dev |
| ASTRA-300-C02-N03-E5 | 환각 구절 포착 | dev |
| ASTRA-300-C02-N07-E1 | 환각 구절 포착 | dev |
| ASTRA-300-C02-N30-E3 | 환각 구절 포착 | dev |
| ASTRA-300-C02-N38-E5 | 환각 구절 포착 | dev |
| ASTRA-300-C02-N46-E2 | 환각 구절 포착 | dev |
| ASTRA-300-C03-N06-E3 | 환각 구절 포착 | dev |
| ASTRA-300-C03-N30-E4 | 환각 구절 포착 | dev |
| ASTRA-300-C04-N03-E2 | 환각 구절 포착 | dev |
| ASTRA-300-C04-N10-E5 | 환각 구절 포착 | dev |
| ASTRA-300-C04-N38-E2 | 환각 구절 포착 | dev |
| ASTRA-300-C05-N03-E3 | 환각 구절 포착 | dev |
| ASTRA-300-C05-N06-E5 | 환각 구절 포착 | dev |
| ASTRA-300-C05-N28-E3 | 환각 구절 포착 | dev |
| ASTRA-300-C01-N04-E3 | 환각 구절 포착 | train |
| ASTRA-300-C01-N05-E2 | 환각 구절 포착 | train |
| ASTRA-300-C01-N08-E4 | 환각 구절 포착 | train |
| ASTRA-300-C01-N11-E1 | 환각 구절 포착 | train |
| ASTRA-300-C01-N14-E3 | 환각 구절 포착 | train |
| ASTRA-300-C01-N18-E4 | 환각 구절 포착 | train |
| ASTRA-300-C01-N19-E3 | 환각 구절 포착 | train |
| ASTRA-300-C01-N24-E3 | 환각 구절 포착 | train |
| ASTRA-300-C01-N25-E2 | 환각 구절 포착 | train |
| ASTRA-300-C01-N35-E2 | 환각 구절 포착 | train |
| ASTRA-300-C01-N37-E5 | 환각 구절 포착 | train |
| ASTRA-300-C01-N39-E3 | 환각 구절 포착 | train |
| ASTRA-300-C01-N41-E1 | 환각 구절 포착 | train |
| ASTRA-300-C01-N42-E5 | 환각 구절 포착 | train |
| ASTRA-300-C01-N43-E4 | 환각 구절 포착 | train |
| ASTRA-300-C01-N48-E4 | 환각 구절 포착 | train |
| ASTRA-300-C01-P02 | 환각 구절 포착 | train |
| ASTRA-300-C01-P05 | 환각 구절 포착 | train |
| ASTRA-300-C02-N01-E2 | 환각 구절 포착 | train |
| ASTRA-300-C02-N04-E4 | 환각 구절 포착 | train |
| ASTRA-300-C02-N08-E5 | 환각 구절 포착 | train |
| ASTRA-300-C02-N09-E4 | 환각 구절 포착 | train |
| ASTRA-300-C02-N16-E2 | 환각 구절 포착 | train |
| ASTRA-300-C02-N18-E5 | 환각 구절 포착 | train |
| ASTRA-300-C02-N21-E2 | 환각 구절 포착 | train |
| ASTRA-300-C02-N25-E3 | 환각 구절 포착 | train |
| ASTRA-300-C02-N27-E1 | 환각 구절 포착 | train |
