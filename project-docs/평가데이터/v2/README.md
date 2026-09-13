# ASTRA 평가 데이터 v2 — 질문·기대답·근거 300건

작성일 2026-09-13. 질문 300건(회사별 60건), 공고 51건. 기존 25건을 포함하며 중복 합산하지 않는다.
실제 답변 생성·환각 span 라벨링·RAG 성능 평가·사람 승인은 아직 하지 않았다.

## 구성과 사용 범위

공고 고유 조건 질문 255건 + 기존 공고/회사 대조 25건 + 새 합성 시나리오 20건이다.
공고 255건은 회사별 세션으로 배정한 공개 문서 이해 문제이며 255건 전체가 회사 적격 비교는 아니다.
이는 내부 평가용 초안으로, 자동 검증 통과를 독립된 골든셋의 사람 승인으로 해석하면 안 된다.
기대답 요지와 answer_evidence_excerpt의 원문 수치·단위·예외를 함께 검토한다. 문장을 그대로 복사하는 채점만 사용하지 않는다.

| 유형 | 건수 |
|---|---:|
| access_control | 5 |
| access_policy | 14 |
| boundary | 40 |
| certification | 30 |
| conflict | 26 |
| contract | 33 |
| cost | 35 |
| eligibility | 25 |
| fact | 19 |
| multi_document | 13 |
| performance | 16 |
| personnel | 44 |

## 새 합성 자료

L2 상태/배치, L3 비용: 회사별 3개, 총 15개 문서·106개 청크.
C01 0036 가정, C02 인증 갱신 가정, C03/C05 missing 실적 증빙 가정,
C04 서비스 주체의 CSAP·공급계약 가정을 기존 v1과 별도로 둔다.
실제 기관의 증명서·견적서가 아니며 실제 증빙/공급사 견적 확보는 missing이다.
가격은 시장가격 추정이 아닌 내부 계산 연습용 설정이다. C02 공개 협약 총액만 실제 추출값이며 합성 단가와 구분한다.
회사의 기존 실적·금액·인력·만료·미보유 상태는 바꾸지 않았다. 실제 투찰가와 전체 적격은 null이다.

## 파일

- evaluation/questions_300.jsonl: 정본 평가 자료. CSV는 동일 필드를 표로 내보낸 검토용 파일이다. 배열·객체와 answer_evidence_excerpt 셀은 원문 공백을 보존한 JSON 표현이다.
- evaluation/composition_plan.json / distribution.json: 사전 구성과 실제 집계.
- scenarios/scenario_extensions.json: 날짜·근거 성격·계산식과 별도 상태 가정. 통째로 검색에 넣지 않는다.
- retrieval_manifest.json: 새 문서 및 기존 문서의 명시적 허용 목록. 아직 색인하지 않았다.
- evaluation/gap_resolution.json: 51건 기존 쟁점과 국소 원문 확인 결과. 모든 조건 해결을 뜻하지 않는다.
- validation/report.json / test_results.json: 자동 검사와 오류 주입 결과. source_audit.json은 로컬 원천 정본·파일을 실제 대조한 별도 실행 결과다.
- evaluation/content_review.md: 에이전트 검토 범위와 사람 검수 우선순위.

## 재현

저장소 루트에서 Python으로 실행한다. 유료 LLM·DB·모델 실행은 필요 없다.

```text
python procurement-pipeline/build_qa300.py
python procurement-pipeline/build_qa300.py --check
python -m unittest discover -s procurement-pipeline -p "test_*documents.py"
python -m unittest discover -s procurement-pipeline -p "test_company_master.py"
python -m unittest discover -s procurement-pipeline -p "test_qa300.py"
python procurement-pipeline/run_qa300_checks.py
```

로컬 원천 재확인은 `--source-cache <source-texts.json> --source-root <원천 폴더>`를 추가한다.
재배포에는 원천 파일·전체 추출 캐시를 포함하지 않는다. evaluation/authoring에는 평가에 필요한 짧은 연속 인용과 작성 명세만 저장한다.
offset은 Unicode code point의 [text_start, text_end)이며 UTF-8 바이트·UTF-16 인덱스가 아니다.
HWP/PDF 인쇄 쪽수가 미확인인 곳은 쪽수를 꾸미지 않고 추출 정본 해시와 offset을 쓴다.

## 다음 단계 / 검수

사람은 특히 원문충돌·규격 수량·평가표의 합쳐진 셀·공동수급·합성 조건·원가·권한 차단을 검수한다.
접근 거절 문항의 private_audit_evidence는 관리자 전용이다. 모델 입력이나 사용자 출력에 포함하지 않는다.
평가 JSONL을 그대로 프롬프트에 넣지 말고 질문·세션·선택한 시나리오만 전달한다.
context_qa300.py의 evaluation_request()로 입력 허용 필드만 추출하고, select()로 자료를 제한한다.
그 후 RAG 답변을 별도 저장하고, 그때 실제 답변의 환각 span을 라벨링한다.
질문/답안/구성표/검증 결과는 검색 입력에 넣지 않는다. 근거 파일 연결 검사는 검색 정확도 측정이 아니다.
공고 및 시나리오는 같은 split에 묶였다. 공통 회사 지식과 유사 조건은 공유되므로 완전한 독립성 주장은 하지 않는다.
