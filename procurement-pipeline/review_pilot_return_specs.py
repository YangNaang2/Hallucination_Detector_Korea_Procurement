"""Explicit agent adjudication proposals for the 2026-09-15 returned pilot sheets.
Never used as a human approval or a training export.
"""
RELABEL = {
 'C04-P04-S01': ('CONTRADICTION', 'actual_contract_start는 null이며 확정 사실로 간주하지 말라고 명시한다.'),
 'C04-P04-S02': ('CONTRADICTION', '미설정 계약 시작일을 확정 사실로 바꾼다.'),
 'C01-N43-E4-S01': ('CONTRADICTION', '재하도급 원칙적 불가와 반대로 제한 범위 내 허용을 주장한다. 전체 결론의 정오와 이 구절의 오류는 구분한다.'),
}
# qid, exact raw-answer quote, occurrence (1-based), reviewer label,
# agent disposition, proposed label, reason, source citations
ADDITIONS = [
 ('C04-N08-E2','공동이행 허용을 근거로 하도급을 허용하는 것은 법적 근거가 없다',1,'UNCERTAIN','hold','UNCERTAIN','해당 공고 조건 설명인지 법률 일반 주장인지 모호하다. 확정 환각으로 학습하지 않는다.',[1]),
 ('C05-S03','[1] 자료에서 제시된 C05-P-04, C05-P-07, C05-P-06 인력의',1,'CITATION_ERROR','accept_proposal','CITATION_ERROR','[1]은 P-04 한 명이다. P-07과 P-06은 실제 입력 [2], [3]에 있으므로 인용 연결 오류다.',[1,2,3]),
 ('C05-S03','[1] 자료에서 제시된 C05-P-04, C05-P-07, C05-P-06 인력의',2,'CITATION_ERROR','accept_proposal','CITATION_ERROR','동일 인용 연결 오류의 두 번째 실제 위치도 보존한다.',[1,2,3]),
 ('C01-S03','**능력이 있다.**',1,'CONTRADICTION','hold','UNCERTAIN','질문은 부분 월의 공수 계산인데 답변은 자원 능력으로 전환했다. 명백한 한 달 적용 주장은 기존 S01에 유지하고 짧은 능력 표현의 환각 여부는 보류한다.',[1]),
 ('C04-P01','두 인증은 서로 대체 관계가 아님을 명시한다',1,'UNSUPPORTED','accept_proposal','UNSUPPORTED','[1] 회사 ISO 레코드는 비대체 규정을 명시하지 않는다. 올바른 결론과 입력에 명시됐다는 주장은 별개다.',[1,2]),
 ('C01-N01-E1','**구체적인 금액 또는 단가**가 제공되지 않아, **확정 불가**함.',1,'CONTRADICTION','hold','UNCERTAIN','가능 여부와 비용 산정의 확정 여부를 혼동한다. 금액 부족 자체는 사실일 수 있어 구절 전체를 근거 모순으로 확정하지 않는다.',[1,2]),
 ('C02-P02','모두 만료된 것이 아닙니다',1,'UNCERTAIN','quality_only',None,'뒤에서 개발 만료·유지관리 미만료를 명확히 구분한다. 부분부정 해석이 문맥과 일치하므로 표현 개선 메모로 두며 확정 환각/O 라벨로도 내보내지 않는다.',[1,2]),
 ('C02-P02','유지관리 인증은 유효한 상태입니다',1,'CONTRADICTION / UNSUPPORTED','hold','UNCERTAIN','합성 레코드 날짜 범위 내 상태를 뜻할 수도 있고 실제 증빙 유효 단정으로 읽힐 수도 있다. synthetic_record 자체를 무효 인증으로 해석하지 않는다.',[2]),
 ('C02-S01','기존 유효 상태',1,'CONTRADICTION / UNCERTAIN','accept_proposal','CONTRADICTION','같은 대상의 기존 상태는 만료라고 근거에 명시한다. 유효성 상태라는 의역을 넣지 않고 실제 표기 기준으로 조정 제안한다.',[1]),
 ('C03-N48-E1','공고문에 명시된 공고기간은',1,'CITATION_ERROR / quality_only','hold','UNCERTAIN','공고문을 입찰공고서 파일명으로 쓴 것인지 공고 첨부 전체의 통칭인지 모호하다. RFP와 공고서의 시각 충돌·검색 누락은 별도 유지한다.',[1]),
 ('C03-P04','0.9 FTE를 초과하지 않으므로',1,'UNSUPPORTED / quality_only','quality_only',None,'0.5+0.4=0.9이며 0.9를 초과하지 않는다는 문장 자체는 참이다. 이를 명시되지 않은 상한 주장으로 확대해 환각 처리하지 않고 논거 부실로 기록한다.',[1,2]),
 ('C01-N43-E4','제2항 2가',1,'CITATION_ERROR','accept_proposal','CITATION_ERROR','재하도급 불가의 실제 위치는 2항 나)다.',[2]),
 ('C01-N43-E4','제2항 2나',1,'CITATION_ERROR','accept_proposal','CITATION_ERROR','하도급 초과 신청 반려는 5항 나)다.',[2]),
 ('C01-N43-E4','제2항 7가',1,'CITATION_ERROR','accept_proposal','CITATION_ERROR','제출 의무 일반문은 7항 본문이며 가)는 특정 확인서 제출이다.',[2]),
]
# Same systematically wrong hierarchy occurs six more times; these are agent additions,
# not extra human approvals. The trailing incomplete '- [2] 제2항' stays a quality issue.
AGENT_CITATIONS = [('제2항 6가','6항 가)'),('제2항 6라','6항 라)'),('제2항 7나','7항 나)'),('제2항 5가','5항 가)'),('제2항 5나','5항 나)'),('제2항 5라','5항 라)')]
ISSUES = [
 ('C01-N43-E4','review_note_conflict','T04 의견 앞부분은 결론을 지지한다고 쓰고 뒤에는 결론과 모순된다고 쓴다. 근거는 재하도급 원칙적 불가다. 결론보다 이후 유보의 과잉 허용·조항 오류를 구절별로 검토한다. 실제 답변 잘린 부분은 삭제하지 않는다.'),
 ('C02-N46-E2','question_premise_and_source_conflict','전국 제한이라는 질문 전제가 확인되지 않는다. 대구 본점 RFP는 입력 밖 참고다. 문서 우선순위·정정 이력을 확인하기 전 지역 자격 정답을 확정하지 않는다.'),
 ('C02-S03','question_ambiguity','0.51 FTE가 신규 배치 총량인지 기존 0.5의 변경값인지 질문만으로 혼동된다. 원 질문은 보존하고 다음 버전에서 신규 추가 배치 총량이라고 명시할 것을 제안한다.'),
 ('C02-N46-E2','repeated_comment_location','S04~S13에 두 번째 출현이라는 메모가 반복됐다. 실제 위치는 v1 정본 offset을 유지하며 의견의 출현 번호를 위치 데이터로 사용하지 않는다.'),
 ('C01-N43-E4','replacement_cell_blank','S01 수정의 J칸은 비어 있으나 K칸에 범위 유지·분류 변경이 명시됐다. K 근거로 분류 조정안을 기록하고 빈 J를 원본에서 고치지 않는다.'),
 ('C03-N48-E1','source_conflict','입력 RFP와 입력 밖 공고서 시각 불일치는 해결된 것으로 표시하지 않는다. 원문 전체 단어 횟수 등 팀원의 확인 주장은 이번 재집계 범위가 아니며 제출 의견으로만 보존한다.'),
 ('C02-S01','date_semantics','문서 상태 기준일과 질문 판단일·갱신 적용일은 서로 다른 축이다. 판단일 이전에 갱신을 소급 적용하지 않는다.'),
]
