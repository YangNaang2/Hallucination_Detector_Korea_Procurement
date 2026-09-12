// Slide content for the focused week-three progress report.
// Native shapes and tables remain editable in PowerPoint.
export function compose({p,C,text,change,title,table,bullets,node}){
const rect=(s,x,y,w,h,fill=C.paper,line=C.line)=>s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:1}});
const arrow=(s,a,b)=>s.shapes.connect(a,b,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:C.blue,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});
const head=(i,t,sub)=>{const s=p.slides.items[i];title(s,t,i+1);change(s,'3',sub,{x:41,y:132,w:1197,h:64,size:25,color:C.muted});return s;};
const foot=(s,t)=>text(s,t,41,674,1160,26,15,C.muted);

// 1. Start with the domain decision, without a separate cover.
{
const s=head(0,'환각 탐지의 적용 무대를 나라장터로 넓혔다','B1조 3주차 진행 보고 · 한국어 환각 탐지와 권한 기반 입찰 검토');
text(s,'출발점',41,231,520,40,25,C.muted);
text(s,'문서를 보고도 틀리는 답변',41,291,535,56,33,C.blue,true);
text(s,'한국어 답변에서 근거가 부족한\\n구절을 찾아 표시하는 모델 개발'.replace('\\n','\n'),41,374,535,100,27);
text(s,'확장한 업무',674,231,564,40,25,C.muted);
text(s,'공고 조건과 회사 증빙의 대조',674,291,564,56,32,C.blue,true);
bullets(s,['공개 공고를 확보하고 조건을 비교할 수 있음','실적·인력·인증을 회사 자료와 함께 검토','비공개 자료의 접근 권한까지 다룰 수 있음'],674,370,559,198,25);
const divider=rect(s,620,242,2,317,C.line,C.line);
rect(s,41,584,1197,61,'#E8EDF9','#E8EDF9');
text(s,'목표  허용된 자료로 입찰 조건을 검토하고, 의심 구간을 원문에서 확인',59,600,1160,37,27,C.blue,true);
foot(s,'현재 주제: 정보시스템 구축·운영 입찰 · 2026.09.13 기준');
}
// 2. Six brief problem boxes, as requested.
{
const s=head(1,'새로운 문제: 조건·버전·기밀을 함께 다뤄야 한다','실제 조달 사례와 AI 보안·답변 문제에서 필요한 기능을 도출');
const cards=[
['입찰 취소 분쟁','제출 조건과 제출 사실의 관계\n권익위는 입찰 절차 진행 시정권고','권익위 · 2019.10.07','조건 대조'],
['모호한 평가 기준','적격심사 방법을 더 구체적으로\n알리라는 권익위 의견표명','권익위 · 의안번호 2023','근거 확인'],
['같은 공고도 바뀐다','참가 업종 1468 → 1469 정정\n입찰 일정도 변경 안내','나라장터 · R26BK01336025-001','버전 관리'],
['외부 전송의 위험','내부 코드 입력 사고 이후\n삼성전자 생성형 AI 사용 제한 보도','머니투데이 · 2023.05.02','처리 경계'],
['민감정보 보호','AI 도입과 함께 기밀 유출 등\n보안 위협에 대한 대응 필요','국정원 AI보안 가이드북 발간 안내','권한 통제'],
['근거가 있어도 오답','다른 물질 질문에 제공된 자료를\n적용한 MSDS 답변 사례','B1조 2주차 문서 주입 실험','답변 검증']
];
cards.forEach(([h,b,source,tag],i)=>{
const x=41+(i%3)*406,y=215+Math.floor(i/3)*205;
rect(s,x,y,385,188,'#F3F6FB',C.line);
text(s,tag,x+17,y+14,345,24,17,i<3?C.blue:C.rose,true);
text(s,h,x+17,y+48,345,36,27,C.ink,true);
text(s,b,x+17,y+95,345,58,21);
text(s,source,x+17,y+162,350,21,13,C.muted);
});
foot(s,'설계 방향: 조건·원문·버전을 함께 제시하고 허용된 자료만 사용 · 분쟁 자동 해결을 주장하지 않음');
}
// 3. Simplify the supplied five-band architecture into editable data + service flows.
{
const s=head(2,'데이터 준비와 실제 서비스 연결을 하나의 흐름으로 설계','준비한 자료와 앞으로 연결할 검색·생성·검증을 구분');
text(s,'데이터 준비',41,205,1160,36,24,C.blue,true);
const top=[['공고 수집·파싱','원본 · 텍스트 · 버전'],['표본·요건 CSV','51건 · 조건 · 근거 위치'],['검수 질문·가상 기업','질문 300건 · 회사별 자료']];
const tn=top.map(([h,b],i)=>{const x=41+i*411;const n=rect(s,x,255,375,121,'#E8EDF9',C.line);text(s,h,x+17,277,342,37,27,C.blue,true);text(s,b,x+17,328,342,30,21);return n;});
arrow(s,tn[0],tn[1]);arrow(s,tn[1],tn[2]);
text(s,'실제 서비스 연결 예정',41,410,1160,36,24,C.blue,true);
const bottom=[['권한 검색','회사·프로젝트·승인'],['로컬 답변 생성','허용된 문맥으로 생성'],['환각·규칙 검증','문서 지지 · 숫자 대조'],['ASTRA 원문 검토','근거 · 의심 구간 표시']];
const bn=bottom.map(([h,b],i)=>{const x=41+i*305;const n=rect(s,x,461,281,114,C.paper,C.line);text(s,h,x+15,482,251,38,25,C.blue,true);text(s,b,x+15,531,251,30,20);return n;});
for(let i=0;i<3;i++)arrow(s,bn[i],bn[i+1]);
text(s,'검색 자료: 공고 원문 + 합성 기업 L2/L3    /    질문·정답표: 검색 DB와 분리',41,612,1190,40,24);
foot(s,'L1 공개 · L2 내부 · L3 민감은 사내 문서 분류 예시 · 국가 비밀취급인가와 구분');
}
// 4. Verified collection statistics, no claim of 100% parsing quality.
{
const s=head(3,'4~6월 공고 수집·파싱·변환 단계를 마쳤다','원본과 파싱 텍스트를 보관하고, 어댑터 입력과 월별 집계까지 연결');
text(s,'137,745',41,213,620,102,76,C.blue,true);
text(s,'수집 공고 행 · 차수 포함',41,323,640,40,26);
table(s,[['수집 월','공고 행','최신 차수'],['4월','53,153','48,033'],['5월','40,241','36,419'],['6월','44,351','40,070'],['합계','137,745','124,522']],41,400,673,228,[193,240,240],23);
text(s,'124,522건',794,235,444,58,39,C.blue,true);
text(s,'최신 차수 기준 공고',794,302,444,37,25);
text(s,'246,797개',794,383,444,58,39,C.blue,true);
text(s,'사용 가능한 첨부\n전체 집계 285,252개 중',794,452,444,83,25);
text(s,'파싱 처리 완료와 별개로\n실패·품질 미달 자료는 구분 관리',794,564,444,75,22,C.muted);
foot(s,'근거: 4·5·6월 워크스테이션 adapt_report.json · 모든 첨부가 정상 파싱됐다는 의미는 아님');
}
// 5. Topic selection.
{
const s=head(4,'주요 분야는 정보시스템 구축·운영으로 선정','분야별 문서 가용성을 집계한 뒤, 입찰 조건 대조에 적합한 업무를 선택');
text(s,'정보시스템 구축·운영',41,236,1190,55,39,C.blue,true);
table(s,[['타깃 분야','공고','완전 공고'],['SW·시스템 개발','2,163','984'],['운영·유지관리','1,313','681'],['합계','3,476','1,665']],41,337,692,241,[332,180,180],24);
text(s,'이 분야를 고른 이유',798,337,440,42,27,C.blue,true);
bullets(s,['실적·인력·인증 조건을 비교하기 좋음','가상 기업의 충족·미충족 사례를 구성할 수 있음','팀의 IT·SW 이해를 활용해 검수 가능'],798,404,440,216,23);
text(s,'완전 공고 = 공고문 + (RFP 또는 과업·규격서)',41,615,713,44,22,C.muted);
foot(s,'근거: 3개월 워크스테이션 통합 sector_report.csv · 완비율이 가장 높은 분야라는 뜻은 아님');
}
// 6. Sample and CSV, distinct from RAG chunks.
{
const s=head(5,'51건을 데모 표본으로 추출하고 요건 CSV를 제작','원문은 검색 자료로, 사람이 확인한 요건은 질문·기업 자료 설계의 기준으로');
text(s,'51건',41,220,525,96,72,C.blue,true);
text(s,'4월 17건 · 5월 17건 · 6월 17건',41,331,525,41,26);
text(s,'SW·시스템 개발 32건\n운영·유지관리 19건',41,404,525,89,26);
text(s,'원문과 파싱 텍스트를 함께 확인\n조건·숫자·예외·근거 위치를 기록',41,559,537,78,24);
text(s,'요건추출시트.csv',653,226,585,46,30,C.blue,true);
table(s,[['기록하는 내용','후속 용도'],['자격 · 실적 · 인력 · 인증','기업 조건 설계'],['금액 · 일정 · 배점 · 특이조건','질문 · 기대 정답'],['근거 문서 · 쪽수 · 검토 메모','원문 대조 · 불일치 확인']],653,310,585,267,[334,251],22);
text(s,'청크 = 원문 조각\nCSV = 사람이 정리한 요건 기준',653,606,585,60,22,C.muted);
foot(s,'표본 수·월·분야: 표본_목록.csv 재집계 · 요건 시트 제작 완료는 9/13 진행 현황 반영');
}
// 7. User-confirmed completion, not span labels or all confidential documents.
{
const s=head(6,'질문·정답·근거 300건과 입찰용 가상 기업을 준비','공고의 조건을 질문과 회사 상황으로 연결할 준비를 마침');
text(s,'300건',41,229,580,96,73,C.blue,true);
text(s,'질문 + 기대 정답 + 근거',41,341,580,45,30,C.blue,true);
bullets(s,['무엇을 질문할지 고정','어떤 답을 기대하는지 기록','답을 확인할 원문 근거 연결'],41,429,550,162,25);
text(s,'가상 기업 구성',676,241,562,54,36,C.blue,true);
text(s,'입찰 조건을 대조할 회사 상황 마련',676,327,562,43,26);
bullets(s,['실적·인력·인증 등 기업 조건','충족·미충족·자료 부족 상황 구분','L2/L3 상세 자료와 권한 연결의 기반'],676,429,554,177,25);
rect(s,41,621,1197,42,'#E8EDF9','#E8EDF9');
text(s,'다음: 실제 답변 생성 → 환각 구간 라벨링 → 교차 검수',56,629,1165,33,23,C.blue,true);
foot(s,'질문·기업 준비는 팀의 최신 완료 확인 반영 · 기업은 합성 자료 · 생성 답변의 span 라벨링은 후속 단계');
}
// 8. Next steps only, no evaluation metric table or private spatial demo.
{
const s=head(7,'다음 단계는 준비한 자료로 실제 답변을 끝까지 연결하는 것','작은 시나리오부터 실행한 뒤 300건 검수로 확장');
const steps=[['01','자료·버전 연결','공고·기업·질문의 ID 고정\nL2/L3 상세 증빙과 권한 연결\n개발용·최종 평가용 자료 분리'],['02','답변 생성·검수','허용 근거로 로컬 답변 생성\n환각 구간 라벨링·교차 검수\n숫자·기간 규칙 대조'],['03','ASTRA 실연결','검색·생성·탐지 API 연결\n원문·의심 구간 표시\n승인 전후·타 회사 접근 차단']];
steps.forEach(([n,h,b],i)=>{const x=41+i*411;text(s,n,x,230,375,65,46,C.blue,true);text(s,h,x,326,375,47,30,C.blue,true);text(s,b,x,410,375,137,25);});
rect(s,41,594,1197,66,'#E8EDF9','#E8EDF9');
text(s,'첫 연결 기준  실제 공고 1건 + 가상 기업 1곳 + 질문 5개를 사람이 확인',57,612,1165,42,26,C.blue,true);
foot(s,'현재: 데이터·검수 자산 준비    /    다음: 권한 적용 서비스 통합과 재현 가능한 시연');
}
}
