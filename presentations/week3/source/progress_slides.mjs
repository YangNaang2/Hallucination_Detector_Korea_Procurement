import fs from 'node:fs/promises';
// Slide content for the focused week-three progress report.
// Native shapes and tables remain editable in PowerPoint.
export async function compose({p,C,text,change,title,table,bullets,node}){
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
text(s,'입찰 담당자의 질문',41,497,535,30,21,C.blue,true);
text(s,'“우리 회사의 실적·인력으로 참여할 수 있나?”',41,535,550,38,23);
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
const x=41+(i%3)*406,y=200+Math.floor(i/3)*155;
rect(s,x,y,385,143,'#F3F6FB',C.line);
text(s,tag,x+17,y+9,345,22,15,i<3?C.blue:C.rose,true);
text(s,h,x+17,y+35,345,31,24,C.ink,true);
text(s,b,x+17,y+74,345,50,19);
text(s,source,x+17,y+124,350,19,12,C.muted);
});
s.images.add({blob:new Uint8Array(await fs.readFile(new URL('./acrc_order_excerpt.png',import.meta.url))),contentType:'image/png',alt:'권익위 공개 의결문 PDF 2쪽 주문 1·2: 취소 요청 심의안내, 평가 방법 명확화 의견표명',fit:'contain',position:{left:41,top:523,width:650,height:139}});
text(s,'공식 의결문에서 확인한 범위',725,529,513,33,24,C.blue,true);
text(s,'취소 요청은 심의안내\n평가 방법 명확화는 의견표명',725,577,513,62,23);
foot(s,'설계 방향: 조건·원문·버전을 함께 제시하고 허용된 자료만 사용 · 분쟁 자동 해결을 주장하지 않음');
}
// 3. Simplify the supplied five-band architecture into editable data + service flows.
{
const s=head(2,'데이터 준비와 실제 서비스 연결을 하나의 흐름으로 설계','준비한 자료와 앞으로 연결할 검색·생성·검증을 구분');
text(s,'데이터 준비',41,205,1160,36,24,C.blue,true);
const top=[['공고 수집·파싱','원본 · 텍스트 · 버전'],['표본·요건 CSV','51건 · 조건 · 근거 위치'],['검수 질문·가상 기업','질문 300건 · 회사별 자료']];
const tn=top.map(([h,b],i)=>{const x=41+i*411;const n=rect(s,x,255,375,121,'#E8EDF9',C.line);text(s,h,x+17,277,342,37,27,C.blue,true);text(s,b,x+17,328,342,30,21);return n;});
arrow(s,tn[0],tn[1]);arrow(s,tn[1],tn[2]);
text(s,'원문·기업 문서 → 청킹 → BGE-M3 임베딩 색인',41,386,1190,32,24,C.blue,true);
text(s,'실제 서비스 연결 예정',41,428,1160,27,19,C.muted);
const bottom=[['권한 검색','회사·프로젝트·승인'],['로컬 답변 생성','허용된 문맥으로 생성'],['환각·규칙 검증','문서 지지 · 숫자 대조'],['ASTRA 원문 검토','근거 · 의심 구간 표시']];
const bn=bottom.map(([h,b],i)=>{const x=41+i*305;const n=rect(s,x,461,281,114,C.paper,C.line);text(s,h,x+15,482,251,38,25,C.blue,true);text(s,b,x+15,531,251,30,20);return n;});
for(let i=0;i<3;i++)arrow(s,bn[i],bn[i+1]);
text(s,'검색 자료: 공고 원문 + 합성 기업 L2/L3    /    질문·정답표: 검색 DB와 분리',41,612,1190,40,24);
foot(s,'L1 공개 · L2 내부 · L3 민감은 사내 문서 분류 예시 · 국가 비밀취급인가와 구분');
}
// 4. Verified collection statistics, no claim of 100% parsing quality.
{
const s=head(3,'4~6월 공고 수집·파싱·변환 단계를 마쳤다','원본과 파싱 텍스트를 보관하고, 어댑터 입력과 월별 집계까지 연결');
text(s,'137,745',41,207,620,86,66,C.blue,true);
text(s,'수집 공고 행 · 차수 포함',41,294,640,36,25);
text(s,'원본·텍스트·공고 차수·해시를 보존',41,348,700,35,24,C.blue,true);
table(s,[['수집 월','공고 행','최신 차수'],['4월','53,153','48,033'],['5월','40,241','36,419'],['6월','44,351','40,070'],['합계','137,745','124,522']],41,400,673,228,[193,240,240],23);
text(s,'124,522건',794,235,444,58,39,C.blue,true);
text(s,'최신 차수 기준 공고',794,302,444,37,25);
text(s,'246,797개',794,383,444,58,39,C.blue,true);
text(s,'사용 가능한 첨부\n전체 집계 285,252개 중',794,452,444,83,25);
text(s,'처리 완료 ≠ 모든 첨부 정상 파싱\n실패·짧은 텍스트·품질 미달 분리',794,557,444,92,22,C.muted);
foot(s,'근거: 4·5·6월 워크스테이션 adapt_report.json · 모든 첨부가 정상 파싱됐다는 의미는 아님');
}
// 5. Topic selection.
{
const s=head(4,'주요 분야는 정보시스템 구축·운영으로 선정','분야별 문서 가용성을 집계한 뒤, 입찰 조건 대조에 적합한 업무를 선택');
text(s,'정보시스템 구축·운영',41,215,1190,51,35,C.blue,true);
table(s,[['타깃 분야','공고','완전 공고'],['SW·시스템 개발','2,163','984'],['운영·유지관리','1,313','681'],['합계','3,476','1,665']],41,294,692,231,[332,180,180],24);
text(s,'이 분야를 고른 이유',798,294,440,42,27,C.blue,true);
bullets(s,['실적·인력·인증 조건을 비교하기 좋음','가상 기업의 충족·미충족 사례를 구성할 수 있음','팀의 IT·SW 이해를 활용해 검수 가능'],798,353,440,190,22);
text(s,'완전 공고 = 공고문 + (RFP 또는 과업·규격서)',41,538,1190,32,21,C.muted);
const steps=[['문서·예산 확인','첨부 2개 이상 · 예산 존재'],['분산 추출·검토','기관·예산 규모 · 중복 확인'],['51건 데모 표본','4·5·6월 각 17건']];
const nn=steps.map(([h,b],i)=>{const x=41+i*411;const n=rect(s,x,581,375,81,'#E8EDF9');text(s,h,x+14,591,347,29,23,C.blue,true);text(s,b,x+14,631,347,24,19);return n;});arrow(s,nn[0],nn[1]);arrow(s,nn[1],nn[2]);
foot(s,'근거: 3개월 워크스테이션 통합 sector_report.csv · 완비율이 가장 높은 분야라는 뜻은 아님');
}
// 6. Documentary example from the team's instructions, not a fabricated completed CSV.
{
const s=head(5,'요건 CSV는 질문과 기업을 만드는 공통 기준이다','51건 원문에서 조건·예외·근거를 정리 · 원문 청크와 요건 시트의 역할 구분');
text(s,'팀원 지시서의 기입 예시',41,209,1190,29,20,C.muted);
text(s,'강릉시 아동 돌봄 통합정보제공 플랫폼 운영',41,253,1190,40,28,C.blue,true);
table(s,[['요건 항목','기입 예시'],['참가 자격','SW사업자 · 중소기업 확인 등'],['공동수급 / 하도급','불가 / 불가'],['사업 예산','공고 58,000,000원 = RFP 58,000천원'],['검토 메모','단위 환산 시 동일 금액 · 배점 추가 확인']],41,319,770,281,[190,580],22);
text(s,'후속 작업에 활용',861,319,377,35,27,C.blue,true);
text(s,'질문·기대 정답',861,383,377,33,24,C.blue,true);
text(s,'공동수급이 가능한가?\n기대 정답: 불가',861,430,377,66,23);
text(s,'기업 조건·검수',861,516,377,32,24,C.blue,true);
text(s,'증빙과 공고 요건을 대조\n불명확한 항목은 확인 대상으로',861,558,377,66,22);
rect(s,41,627,770,36,'#E8EDF9');text(s,'원문 청크 → 검색 DB    |    요건 CSV → 질문·기업 설계',53,633,746,27,21,C.blue,true);
foot(s,'출처: 팀원별_요건추출_지시서.md의 채운 예시 · 완성 CSV 전량 검수 결과가 아님 · 금액은 부가세 포함');
}
// 7. User-confirmed completion; scenario uses are explicitly design examples.
{
const s=head(6,'질문·정답·근거 300건과 입찰용 가상 기업을 준비','이번 주 산출물을 실제 답변 검수와 권한 시나리오로 연결');
rect(s,41,209,363,159,'#E8EDF9');text(s,'300건',58,221,329,74,61,C.blue,true);text(s,'질문 + 기대 정답 + 근거',58,319,329,34,24,C.blue,true);
text(s,'검수 레코드의 연결 구조',452,209,786,33,26,C.blue,true);
const rec=[['질문','어떤 조건을 묻는가'],['기대 정답','어떻게 답해야 하는가'],['문서 근거','어느 구간으로 확인하나']];
const nn=rec.map(([h,b],i)=>{const x=452+i*273;const n=rect(s,x,264,240,104,'#F3F6FB');text(s,h,x+13,279,214,33,25,C.blue,true);text(s,b,x+13,328,214,28,19);return n;});arrow(s,nn[0],nn[1]);arrow(s,nn[1],nn[2]);
text(s,'가상 기업을 활용할 세 가지 검토 상황',41,405,1190,35,27,C.blue,true);
const scenarios=[['충족','요구한 증빙이 존재\n허용된 자료에서 근거 제시'],['미충족','보유 조건이 요구에 못 미침\n부족한 조건을 설명'],['자료 부족','증빙이 없거나 확인할 수 없음\n충족 여부를 추정하지 않고 안내']];
scenarios.forEach(([h,b],i)=>{const x=41+i*411;rect(s,x,462,375,135,'#F3F6FB');text(s,h,x+16,479,343,34,26,C.blue,true);text(s,b,x+16,534,343,59,22);});
rect(s,41,623,1197,39,'#E8EDF9');text(s,'다음: 실제 답변 생성 → 환각 구간 라벨링 → 교차 검수',55,630,1169,31,23,C.blue,true);
foot(s,'질문·기업 준비는 9/13 팀 완료 확인 · 세 상황은 활용 설계 · 유형별 건수나 span 라벨링 완료를 뜻하지 않음');
}
// 8. Next steps only, no evaluation metric table or private spatial demo.
{
const s=head(7,'다음 단계는 준비한 자료로 실제 답변을 끝까지 연결하는 것','작은 시나리오부터 실행한 뒤 300건 검수로 확장');
const steps=[['01','자료·버전 연결','공고·기업·질문의 ID 고정\nL2/L3 상세 증빙과 권한 연결\n개발용·최종 평가용 자료 분리'],['02','답변 생성·검수','허용 근거로 로컬 답변 생성\n환각 구간 라벨링·교차 검수\n숫자·기간 규칙 대조'],['03','ASTRA 실연결','검색·생성·탐지 API 연결\n원문·의심 구간 표시\n승인 전후·타 회사 접근 차단']];
steps.forEach(([n,h,b],i)=>{const x=41+i*411;text(s,n,x,230,375,65,46,C.blue,true);text(s,h,x,326,375,47,30,C.blue,true);text(s,b,x,410,375,137,25);});
['산출물: 근거·권한이 연결된 입력 묶음','산출물: 생성 답변·문서 근거·검수 라벨','산출물: 실행 로그가 남는 통합 시연'].forEach((t,i)=>text(s,t,41+i*411,559,375,29,18,C.green,true));
rect(s,41,606,1197,54,'#E8EDF9','#E8EDF9');
text(s,'첫 연결 기준  실제 공고 1건 + 가상 기업 1곳 + 질문 5개를 사람이 확인',57,620,1165,36,25,C.blue,true);
foot(s,'현재: 데이터·검수 자산 준비    /    다음: 권한 적용 서비스 통합과 재현 가능한 시연');
}
}
