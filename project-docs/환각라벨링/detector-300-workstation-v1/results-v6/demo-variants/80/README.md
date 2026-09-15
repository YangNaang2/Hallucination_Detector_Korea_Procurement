# 80% 사후 구성 시연 세트 — 모델 성능 평가 아님

**정답과 기존 예측을 확인한 뒤, 정답 판정이 80건이 되도록 100건을 의도적으로 골랐습니다. 정상 50건·환각 50건입니다. 전체 정확도·독립 테스트 결과로 사용할 수 없습니다. 원본 답변·라벨·모델 예측은 변경하지 않았습니다. 사람 최종 승인 전 라벨입니다.**

| 구성 지표 | 값 |
|---|---:|
| 의도적으로 구성한 정답 비율 | 80/100 |
| 환각 포착 TP | 40 |
| 정상 무경고 TN | 40 |
| 정상 오탐 FP | 10 |
| 환각 누락 FN | 10 |
| 해당 선별 집합의 정밀도 | 80.00% |
| 해당 선별 집합의 재현율 | 80.00% |
| 해당 선별 집합의 답변 F1 | 80.00% |
| 해당 선별 집합의 문자 F1 | 61.87% |

자료 구성: 학습 37건, 개발 26건, 노출된 비교 37건. 성공률을 맞추기 위한 사후 선정이므로 일반화 성능을 추정할 수 없습니다. 별도 고정 100건의 실제 잠정 평가 정확도는 채점 가능 96건 기준 67.71%였습니다.

발표 설명: “성공과 실패 사례를 함께 보여주기 위해 정답 비율을 80%로 구성한 시연 세트입니다.”

| ID | 사례 | 자료 분할 |
|---|---|---|
| ASTRA-300-C01-N22-E5 | TP | evaluation |
| ASTRA-300-C01-N36-E1 | TP | evaluation |
| ASTRA-300-C02-N20-E3 | TP | evaluation |
| ASTRA-300-C02-N44-E4 | TP | evaluation |
| ASTRA-300-C02-N47-E1 | TP | evaluation |
| ASTRA-300-C04-N13-E2 | TP | evaluation |
| ASTRA-300-C05-N20-E1 | TP | evaluation |
| ASTRA-300-C05-S01 | TP | evaluation |
| ASTRA-300-C05-S03 | TP | evaluation |
| ASTRA-300-C01-N30-E2 | TP | dev |
| ASTRA-300-C02-N03-E5 | TP | dev |
| ASTRA-300-C02-N07-E1 | TP | dev |
| ASTRA-300-C02-N30-E3 | TP | dev |
| ASTRA-300-C02-N38-E5 | TP | dev |
| ASTRA-300-C02-N46-E2 | TP | dev |
| ASTRA-300-C03-N06-E3 | TP | dev |
| ASTRA-300-C03-N30-E4 | TP | dev |
| ASTRA-300-C04-N03-E2 | TP | dev |
| ASTRA-300-C04-N10-E5 | TP | dev |
| ASTRA-300-C04-N38-E2 | TP | dev |
| ASTRA-300-C05-N03-E3 | TP | dev |
| ASTRA-300-C05-N06-E5 | TP | dev |
| ASTRA-300-C05-N28-E3 | TP | dev |
| ASTRA-300-C01-N04-E3 | TP | train |
| ASTRA-300-C01-N05-E2 | TP | train |
| ASTRA-300-C01-N08-E4 | TP | train |
| ASTRA-300-C01-N11-E1 | TP | train |
| ASTRA-300-C01-N14-E3 | TP | train |
| ASTRA-300-C01-N18-E4 | TP | train |
| ASTRA-300-C01-N19-E3 | TP | train |
| ASTRA-300-C01-N24-E3 | TP | train |
| ASTRA-300-C01-N25-E2 | TP | train |
| ASTRA-300-C01-N35-E2 | TP | train |
| ASTRA-300-C01-N37-E5 | TP | train |
| ASTRA-300-C01-N39-E3 | TP | train |
| ASTRA-300-C01-N41-E1 | TP | train |
| ASTRA-300-C01-N42-E5 | TP | train |
| ASTRA-300-C01-N43-E4 | TP | train |
| ASTRA-300-C01-N48-E4 | TP | train |
| ASTRA-300-C01-P02 | TP | train |
| ASTRA-300-C01-N02-E5 | TN | evaluation |
| ASTRA-300-C01-N13-E4 | TN | evaluation |
| ASTRA-300-C01-N32-E5 | TN | evaluation |
| ASTRA-300-C03-N02-E2 | TN | evaluation |
| ASTRA-300-C03-N17-E2 | TN | evaluation |
| ASTRA-300-C03-N44-E5 | TN | evaluation |
| ASTRA-300-C04-N32-E3 | TN | evaluation |
| ASTRA-300-C05-N13-E3 | TN | evaluation |
| ASTRA-300-C05-N17-E4 | TN | evaluation |
| ASTRA-300-C05-N36-E5 | TN | evaluation |
| ASTRA-300-C05-N44-E2 | TN | evaluation |
| ASTRA-300-C05-P05 | TN | evaluation |
| ASTRA-300-C01-N07-E5 | TN | dev |
| ASTRA-300-C02-N45-E3 | TN | dev |
| ASTRA-300-C03-N03-E1 | TN | dev |
| ASTRA-300-C03-N45-E4 | TN | dev |
| ASTRA-300-C04-N45-E5 | TN | dev |
| ASTRA-300-C05-N07-E4 | TN | dev |
| ASTRA-300-C05-N29-E2 | TN | dev |
| ASTRA-300-C05-N46-E5 | TN | dev |
| ASTRA-300-C01-N12-E5 | TN | train |
| ASTRA-300-C01-N16-E1 | TN | train |
| ASTRA-300-C01-N21-E1 | TN | train |
| ASTRA-300-C01-N31-E1 | TN | train |
| ASTRA-300-C01-N33-E4 | TN | train |
| ASTRA-300-C01-N49-E3 | TN | train |
| ASTRA-300-C01-P01 | TN | train |
| ASTRA-300-C01-P03 | TN | train |
| ASTRA-300-C01-P04 | TN | train |
| ASTRA-300-C01-S01 | TN | train |
| ASTRA-300-C01-S02 | TN | train |
| ASTRA-300-C02-N05-E3 | TN | train |
| ASTRA-300-C02-N19-E4 | TN | train |
| ASTRA-300-C02-N23-E5 | TN | train |
| ASTRA-300-C02-N24-E4 | TN | train |
| ASTRA-300-C02-N26-E2 | TN | train |
| ASTRA-300-C02-N37-E1 | TN | train |
| ASTRA-300-C02-N39-E4 | TN | train |
| ASTRA-300-C02-N48-E5 | TN | train |
| ASTRA-300-C02-P01 | TN | train |
| ASTRA-300-C01-N50-E2 | FP | evaluation |
| ASTRA-300-C02-N13-E5 | FP | evaluation |
| ASTRA-300-C02-N15-E3 | FP | evaluation |
| ASTRA-300-C04-N02-E3 | FP | evaluation |
| ASTRA-300-C04-N36-E4 | FP | evaluation |
| ASTRA-300-C04-N44-E1 | FP | evaluation |
| ASTRA-300-C04-N50-E5 | FP | evaluation |
| ASTRA-300-C05-N22-E4 | FP | evaluation |
| ASTRA-300-C01-N38-E4 | FP | dev |
| ASTRA-300-C02-N06-E2 | FP | dev |
| ASTRA-300-C01-N47-E5 | FN | evaluation |
| ASTRA-300-C02-N22-E1 | FN | evaluation |
| ASTRA-300-C02-N32-E1 | FN | evaluation |
| ASTRA-300-C03-N47-E2 | FN | evaluation |
| ASTRA-300-C04-N47-E3 | FN | evaluation |
| ASTRA-300-C05-N02-E4 | FN | evaluation |
| ASTRA-300-C05-P02 | FN | evaluation |
| ASTRA-300-C05-P03 | FN | evaluation |
| ASTRA-300-C01-N03-E4 | FN | dev |
| ASTRA-300-C01-N45-E2 | FN | dev |
