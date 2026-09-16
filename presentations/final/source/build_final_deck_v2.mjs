import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const finalDir=path.resolve(here,'..');
const repo=path.resolve(finalDir,'../..');
const build=path.join(repo,'.presentation-build','final-deck-v2');
const skill=process.env.SKILL_DIR;
const modules=process.env.RUNTIME_NODE_MODULES;
const runtimePython=process.env.RUNTIME_PYTHON;
if(!skill||!modules||!runtimePython) throw new Error('Missing bundled runtime environment');

const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,makeNativeBulletParagraphs,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
await fs.mkdir(build,{recursive:true});

const p=Presentation.create({slideSize:{width:1280,height:720}});
const F='Noto Sans CJK KR';
const C={bg:'#F7F9FC',paper:'#FFFFFF',ink:'#132238',muted:'#52657A',navy:'#183B5B',blue:'#2F6BFF',teal:'#119C8B',green:'#2E7D62',orange:'#F29B38',red:'#D9564A',purple:'#7657C8',line:'#CFD9E6',panel:'#ECF2F7',paleBlue:'#E9F0FF',paleTeal:'#E7F6F3',paleOrange:'#FFF2DE',paleRed:'#FCEBE9',white:'#FFFFFF'};
const notes=[];
const facts=[];
const sections=['문제 정의','데이터 구축','평가 설계','권한형 RAG','생성·탐지','시연·결론','APPENDIX'];
const secBySlide=[0,0,0,0,0,1,1,1,1,1,1,1,1,2,2,3,3,3,3,3,3,4,4,4,4,4,4,5,5,5,6,6,6];
const slideTitles=['표지','프로젝트 결과 요약','발표 흐름','조달 검토의 복잡성','공식 사례와 원문 충돌','3개월 수집 결과','분야 선택 근거','51건 표본 구성','예산·조건 분포','원문 재대조 원칙','가상 기업 원장','기업별 강점과 제약','L1·L2·L3 색인','평가 데이터 300문항','ASTRA 전체 구조','사용자 질의 흐름','역할별 접근 정책','검색 전 ACL 강제','정본·청크·offset','임베딩 구축','하이브리드 검색','로컬 GPU 생성','정본 답변 295건','환각 탐지 설계','25문항 검수 현황','3모델 비교 평가 설계','대표 오류 사례','통합 검증 상태','데모 화면','결론','부록 A · 재현성 검사','부록 B · 발표 수치 원장','부록 C · 주장 경계'];

function addText(s,t,x,y,w,h,size=20,color=C.ink,bold=false,opts={}){
 const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=t;
 a.text.style={typeface:F,fontSize:size,color,bold,autoFit:'none',verticalAlignment:opts.v||'top',horizontalAlignment:opts.align||'left',insets:{left:opts.pad??0,right:opts.pad??0,top:opts.pad??0,bottom:opts.pad??0}};
 return a;
}
function box(s,x,y,w,h,fill=C.paper,stroke=C.line,r=8,width=1){return s.shapes.add({geometry:r?'roundRect':'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width}});}
function line(s,x1,y1,x2,y2,color=C.line,width=1.5){return s.shapes.add({geometry:'line',position:{left:x1,top:y1,width:x2-x1,height:y2-y1},fill:'none',line:{fill:color,width}});}
function circle(s,x,y,d,fill=C.blue){return s.shapes.add({geometry:'ellipse',position:{left:x,top:y,width:d,height:d},fill,line:{fill,width:1}});}
function header(s,i,title,sub=''){
 s.background.fill=C.bg; const sec=secBySlide[i];
 addText(s,sections[sec],54,22,260,22,13,sec===6?C.orange:C.teal,true);
 addText(s,title,54,48,1168,46,31,C.ink,true);
 if(sub)addText(s,sub,56,97,1150,26,16,C.muted,false);
 line(s,54,132,1226,132,C.line,1);
 addText(s,String(i+1).padStart(2,'0'),1176,22,50,24,13,C.muted,true,{align:'right'});
}
function foot(s,t){line(s,54,667,1226,667,C.line,1);addText(s,t,56,678,1120,20,11,C.muted);addText(s,'ASTRA · ko-LettuceDetect',1050,678,176,20,11,C.navy,true,{align:'right'});}
function tag(s,t,x,y,w,color=C.teal){box(s,x,y,w,27,color,color,7);addText(s,t,x,y+4,w,18,12,C.white,true,{align:'center'});}
function metric(s,num,label,x,y,w,color=C.blue,sub=''){box(s,x,y,w,112,C.paper,C.line,10);addText(s,num,x+16,y+14,w-32,44,32,color,true);addText(s,label,x+16,y+61,w-32,24,15,C.ink,true);if(sub)addText(s,sub,x+16,y+86,w-32,18,11,C.muted);}
function bullets(s,items,x,y,w,h,size=18,color=C.ink,space=7){const a=addText(s,'',x,y,w,h,size,color);a.text=makeNativeBulletParagraphs(items,{marginLeftPoints:14,hangingPoints:7,spaceAfterPoints:space});a.text.style={typeface:F,fontSize:size,color,autoFit:'none',verticalAlignment:'top',insets:{left:0,right:0,top:0,bottom:0}};return a;}
function table(s,vals,x,y,w,h,widths,opts={}){const t=s.tables.add({rows:vals.length,columns:vals[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values:vals});t.borders.assign({fill:opts.border||C.line,width:.8,style:'solid'});const all=t.cells.block({row:0,column:0,rowCount:vals.length,columnCount:vals[0].length});all.assign({fill:opts.fill||C.paper,textStyle:{typeface:F,fontSize:opts.size||15,color:opts.color||C.ink},margins:{left:8,right:8,top:6,bottom:6},anchor:'center'});for(let j=0;j<vals[0].length;j++){const c=t.getCell(0,j);c.fill=opts.headerFill||C.navy;c.text.style={typeface:F,fontSize:opts.size||15,bold:true,color:C.white};}return t;}
function chart(s,categories,series,x,y,w,h,opts={}){const ch=s.charts.add('bar',{position:{left:x,top:y,width:w,height:h},categories,series,barOptions:{direction:'column',grouping:opts.grouping||'clustered'},hasLegend:opts.legend!==false,dataLabels:{showValue:true,position:'outEnd'}});applyPresentationChartFont(ch,{fontFamily:F});return ch;}
function node(s,title,body,x,y,w,h,accent=C.blue){box(s,x,y,w,h,C.paper,C.line,8);box(s,x,y,6,h,accent,accent,0);addText(s,title,x+17,y+13,w-30,28,18,C.ink,true);addText(s,body,x+17,y+48,w-32,h-58,14,C.muted);return {x,y,w,h};}
function arrow(s,a,b,color=C.muted){const y=a.y+a.h/2;line(s,a.x+a.w,y,b.x,b.y+b.h/2,color,2);s.shapes.add({geometry:'triangle',position:{left:b.x-10,top:b.y+b.h/2-5,width:10,height:10},fill:color,line:{fill:color,width:1},rotation:90});}
function takeaway(s,t,color=C.navy){box(s,54,604,1172,47,color,color,8);addText(s,t,72,616,1136,24,18,C.white,true,{align:'center'});}
function addNote(text,source,limit=''){notes.push(text);facts.push({source,limit});}

// 1 Cover
{
 const s=p.slides.add();s.background.fill=C.bg;
 box(s,0,0,18,720,C.teal,C.teal,0);addText(s,'ASTRA',62,42,260,38,24,C.teal,true);addText(s,'PROCUREMENT INTELLIGENCE',64,82,300,20,11,C.muted,true);
 addText(s,'근거를 찾고, 권한을 지키고,\n답변의 의심 구절까지 확인하는 조달 검토 시스템',62,157,1010,144,43,C.ink,true);
 addText(s,'나라장터 공개 공고 · 합성 기업 자료 · 권한형 하이브리드 RAG · 구절 단위 환각 검증',64,327,1080,32,19,C.muted);
 const items=[['DATA','3개월 수집과 51건 원문 검수',C.blue],['RAG','223문서 · 3,275청크',C.teal],['EVAL','300문항 · 생성답변 295건',C.orange]];
 items.forEach(([a,b,c],i)=>{const x=64+i*386;box(s,x,411,350,116,C.paper,C.line,10);tag(s,a,x+18,428,74,c);addText(s,b,x+18,472,314,35,19,C.ink,true);});
 addText(s,'ko-LettuceDetect / ASTRA · B1조 최종발표',64,594,650,28,17,C.navy,true);addText(s,'2026.10.02',64,632,260,24,15,C.muted);
 addNote('ASTRA는 입찰 여부를 대신 확정하는 시스템이 아니라, 담당자가 권한에 맞는 자료에서 근거를 찾고 답변의 오류 가능성을 빠르게 확인하도록 돕는 시스템입니다. 데이터 수집부터 평가용 질문, 검색, 로컬 생성, 환각 검증까지 실제 구축한 범위와 아직 검증 중인 범위를 나눠 설명하겠습니다.','project-docs/PPT_최종발표_제작_인수인계_프롬프트.md','탐지 성능 우수 또는 운영 완성을 주장하지 않음');
}

// 2 Executive summary
{
 const s=p.slides.add();header(s,1,'프로젝트 결과를 먼저 숫자로 요약하면','수집·검수·색인·생성은 완료 범위가 있고, 탐지 성능은 평가 진행 중이다');
 const ms=[['137,745','공고 행','4~6월 · 차수 포함',C.blue],['246,797','사용 가능 첨부','전체 285,252개 중 87%',C.teal],['51','검수 표본','SW 개발 32 · 운영 19',C.orange],['223 / 3,275','문서 / 청크','L1·L2·L3 로컬 색인',C.purple],['300','평가 문항','합성 기업 5곳 × 60',C.blue],['295 + 5','생성 / 차단','실제 답변 295 · 정상 차단 5',C.teal]];
 ms.forEach(([n,l,sub,c],i)=>metric(s,n,l,54+(i%3)*390,164+Math.floor(i/3)*136,362,c,sub));
 box(s,54,451,1172,119,C.paleOrange,'#F6CF91',10);addText(s,'현재 발표 가능한 결론',74,469,240,30,18,C.orange,true);bullets(s,['데이터와 정본 답변, 근거 연결, 권한 차단은 재현 가능한 산출물로 보존','KLUE·XLM-R·BGE-M3의 295답변 전체 비교 수치는 아직 확정하지 않음','25문항 사람 검수는 접수 완료, 최종 승인과 학습 내보내기는 pending'],324,466,872,88,15,C.ink,4);
 foot(s,'근거: 3개월 통합현황 · index_manifest · QA validation · workstation final_summary');
 addNote('먼저 완료 범위를 숫자로 보겠습니다. 3개월 공고 137,745행과 첨부 285,252개를 처리했고, 51건 표본을 원문 대조했습니다. 검색용 자산은 223문서와 3,275청크, 평가용 자산은 300문항입니다. 실제 생성 답변은 295건이고 5건은 권한 정책에 따라 모델 호출 전에 차단했습니다. 탐지 성능은 아직 최종값으로 발표하지 않습니다.','project-docs/데이터현황/3개월_통합현황.md; project-docs/RAG파일럿/workstation-275/index_manifest.json; project-docs/평가데이터/v2/validation/report.json; project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json','탐지 성능은 평가 진행 중');
}

// 3 Agenda
{
 const s=p.slides.add();header(s,2,'발표 흐름','문제 → 데이터 → 평가 설계 → 권한형 RAG → 생성·탐지 → 시연 순으로 연결한다');
 const arr=[['01','왜 조달 검토가 어려운가','정정·충돌·누락·권한'],['02','어떤 데이터를 구축했는가','3개월 수집·51건 검수·합성기업'],['03','무엇으로 평가하는가','300 Q-A-R·정본·근거'],['04','어떻게 답하는가','ACL·하이브리드 검색·로컬 LLM'],['05','어떻게 오류를 찾는가','규칙·토큰 분류·사람 검수'],['06','현재 어디까지 왔는가','데모·검증·남은 과제']];
 arr.forEach(([n,h,b],i)=>{const x=54+(i%3)*390,y=166+Math.floor(i/3)*197;box(s,x,y,362,163,C.paper,C.line,10);addText(s,n,x+18,y+17,55,30,16,C.teal,true);addText(s,h,x+18,y+55,326,34,21,C.ink,true);addText(s,b,x+18,y+104,326,35,15,C.muted);});
 takeaway(s,'핵심 질문: “이 답은 누가 볼 수 있는 어떤 문서의 어느 구절에서 나왔는가?”',C.navy);foot(s,'부록에는 재현성 검사, 세부 수치 원장, 정확성 제한을 별도로 수록');
 addNote('발표는 여섯 부분입니다. 먼저 조달 문서가 왜 단순 검색으로 끝나지 않는지 설명합니다. 이어 데이터 수집과 원문 검수, 평가 데이터 설계를 보고, 권한 필터와 하이브리드 RAG, 로컬 생성과 탐지 흐름을 설명합니다. 마지막에는 실제 화면과 남은 검증 과제를 보여드리겠습니다.','project-docs/PPT_최종발표_제작_인수인계_프롬프트.md','구조 안내');
}

// 4 Problem
{
 const s=p.slides.add();header(s,3,'입찰 검토는 “문서 검색”보다 복잡하다','같은 사업 안에서도 문서 버전·조건 범위·기업 자료·권한을 함께 해석해야 한다');
 const items=[['버전','정정공고에서 업종 코드와 일정이 함께 변경',C.red],['범위','금액·실적·인력 조건이 문서마다 다른 범위를 가짐',C.orange],['충돌','공고문과 RFP의 공동수급·사업기간 표현이 병존',C.purple],['증빙','회사 실적 금액이 있어도 증빙이 missing이면 확정 불가',C.blue],['권한','공개 공고와 원가·마진 자료의 공개 범위가 다름',C.teal],['답변','근거가 있어도 모델이 숫자·주체·예외를 바꿀 수 있음',C.red]];
 items.forEach(([h,b,c],i)=>{const x=54+(i%2)*594,y=158+Math.floor(i/2)*137;box(s,x,y,570,113,C.paper,C.line,9);box(s,x,y,9,113,c,c,0);addText(s,h,x+26,y+17,90,28,18,c,true);addText(s,b,x+122,y+17,422,66,17,C.ink,true);});
 takeaway(s,'ASTRA는 검색 결과가 아니라 “권한이 적용된 근거 + 답변 + 검증 상태”를 하나의 단위로 다룬다',C.navy);foot(s,'공식 사례와 51건 원문대조에서 확인한 범위만 사용');
 addNote('조달 검토의 어려움은 문서 수만 많아서가 아닙니다. 정정공고로 조건이 바뀌고, 같은 사업에서도 공고문과 제안요청서의 범위가 다를 수 있습니다. 회사 실적과 인력 자료는 공개 공고와 접근 권한이 다르고, 모델은 근거를 받더라도 숫자나 예외를 잘못 바꿀 수 있습니다. ASTRA는 이 네 문제를 한 흐름에서 다룹니다.','project-docs/나라장터_문제정의_1차리서치_팀원용.md; project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md','자동 적격 판정이나 분쟁 해결을 주장하지 않음');
}

// 5 Evidence cases
{
 const s=p.slides.add();header(s,4,'실제 문서에서는 “정답 하나”가 바로 나오지 않는다','공식 의결문과 51건 원문대조에서 확인한 대표 사례');
 box(s,54,158,504,391,C.paper,C.line,8);s.images.add({blob:await fs.readFile(path.join(repo,'presentations/week3/source/acrc_order_excerpt.png')),contentType:'image/png',alt:'국민권익위원회 의결문 발췌',fit:'contain',position:{left:72,top:190,width:468,height:165}});addText(s,'평가 기준 명확화 요구',74,374,450,28,19,C.navy,true);addText(s,'향후 유사 공고에서 기술능력 평가 기준 등 적격심사 방법을 더 구체적으로 제공하라는 공식 의견.',74,414,450,82,15,C.muted);
 const vals=[['원문대조 사례','문서에 함께 존재한 값','처리'],['경민대 예산','165,000,000원 / 메타 181,500,000원','출처 분리'],['동아보건대 마감','11:00 / 10:00','단일값 보류'],['천안 사업기간','착수일부터 / 계약일부터 120일','기산점 보류'],['강릉 예산','58,000,000원 / 영향평가 80,000,000원','범위 구분']];
 table(s,vals,590,158,636,366,[210,244,182],{size:14});addText(s,'12개 쟁점 공고 재대조',590,544,260,26,16,C.teal,true);addText(s,'첨부 미확보 2 · 원문 문제 확인 6 · 일부 해소 4',850,544,376,26,15,C.ink,true,{align:'right'});
 foot(s,'원문 충돌은 다수결로 합치지 않고 출처·적용 범위를 남김');
 addNote('왼쪽은 평가 방법을 더 명확히 제공하라는 공식 의결문 발췌입니다. 오른쪽은 팀의 원문대조 사례입니다. 경민대는 공고와 RFP의 1억 6천5백만원과 수집 메타데이터의 1억 8천1백5십만원을 분리했습니다. 동아보건대 마감과 천안 사업기간도 두 값이 실제 원문에 병존했습니다. 이 경우 ASTRA의 정답은 임의의 단일값이 아니라 출처별 값과 보류 사유입니다.','presentations/week3/source/acrc_order_excerpt.png; project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md','12건 전체 셀·법령 검증이 아니라 쟁점 재대조');
}

// 6 Collection
{
 const s=p.slides.add();header(s,5,'3개월 동안 137,745개 공고 행을 수집·변환했다','월별 수집량과 최신 차수, 첨부 활용률을 분리해 기록');
 chart(s,['4월','5월','6월'],[{name:'공고 행',values:[53153,40241,44351],fill:C.blue},{name:'최신 차수',values:[48033,36419,40070],fill:C.teal}],54,175,714,330,{legend:true});
 metric(s,'285,252','전체 첨부',806,177,196,C.blue,'다운로드·파일 실재 기준');metric(s,'246,797','사용 가능',1020,177,206,C.teal,'어댑터 판정 87%');
 metric(s,'3,301','재파싱 후 실패',806,311,196,C.red,'4월 1,408 · 5월 144 · 6월 1,749');metric(s,'124,522','최신 차수 공고',1020,311,206,C.orange,'중복 차수 제거 관점');
 box(s,806,449,420,83,C.paleBlue,'#BDD0FF',8);addText(s,'저장 원칙',824,463,100,23,15,C.blue,true);addText(s,'raw / parsed / jsonl과 해시·실패 사유를 분리해 재개 가능하게 보존',924,461,280,50,14,C.ink,true);
 takeaway(s,'모든 첨부를 성공으로 세지 않고, 사용할 수 없는 문서와 실패 원인을 별도 기록',C.navy);foot(s,'근거: project-docs/데이터현황/3개월_통합현황.md · 2026.09.11 확정');
 addNote('4월 53,153행, 5월 40,241행, 6월 44,351행으로 총 137,745행을 수집했습니다. 최신 차수는 124,522건입니다. 첨부 285,252개 중 어댑터가 사용할 수 있다고 판정한 문서는 246,797개로 87%입니다. 재파싱 후 실패 3,301건도 숨기지 않고 남겼고, raw·parsed·jsonl과 해시를 분리해 재개 가능한 구조로 만들었습니다.','project-docs/데이터현황/3개월_통합현황.md','공고 행은 차수 포함, 사용 가능은 어댑터 판정');
}

// 7 sectors
{
 const s=p.slides.add();header(s,6,'완전 공고 비율과 요건 구조를 보고 “용역”을 선택했다','완전 공고 = 공고문 + 제안요청서 또는 과업·규격서');
 chart(s,['용역','물품','공사'],[{name:'완전 공고',values:[28852,14145,8082],fill:C.blue}],54,171,655,325,{legend:false});
 table(s,[['업무구분','공고','사용 가능 문서','완전 공고','비율'],['용역','50,717','102,702','28,852','57%'],['물품','32,673','66,298','14,145','43%'],['공사','38,839','73,038','8,082','21%']],743,172,483,264,[108,96,122,102,55],{size:14});
 box(s,743,456,483,110,C.paleTeal,'#AFDED5',8);addText(s,'메인 분야 선택',761,471,150,24,16,C.teal,true);addText(s,'SW 및 시스템 개발 984건 + 운영·유지관리 681건\n실적·인력·인증·단가 네 축을 비교하기에 적합',761,505,438,46,15,C.ink,true);
 takeaway(s,'분야는 가상 기업 서사가 아니라 데이터 규모·문서 완성도·요건 구조를 기준으로 결정',C.navy);foot(s,'근거: 2026-04to06 워크스테이션 통합 sector report');
 addNote('용역은 50,717개 공고 중 완전 공고가 28,852건으로 57%입니다. 물품은 43%, 공사는 21%였습니다. 용역 안에서도 SW 개발과 운영·유지관리는 실적, 인력, 인증, 단가가 문서에 비교적 명시돼 있어 회사 자료와 대조하기 좋았습니다. 분야 선택은 이야기보다 데이터 규모와 문서 구조를 기준으로 했습니다.','project-docs/데이터현황/3개월_통합현황.md','완전 공고 정의와 확정 집계를 유지');
}

// 8 sample
{
 const s=p.slides.add();header(s,7,'51건 표본은 월과 분야를 고정해 구성했다','4·5·6월 각 17건, SW 개발 32건과 운영·유지관리 19건');
 const a=node(s,'4월 17건','월별 편중을 막기 위해\n동일 수량 선정',54,185,254,132,C.blue);const b=node(s,'5월 17건','공고문·RFP·과업서\n확보 여부 확인',349,185,254,132,C.teal);const c=node(s,'6월 17건','요건 시트 15열로\n동일 구조 정리',644,185,254,132,C.orange);const d=node(s,'통합 51건','SW 개발 32\n운영·유지관리 19',939,185,287,132,C.purple);arrow(s,a,b);arrow(s,b,c);arrow(s,c,d);
 table(s,[['검수 대상','정리 항목','보존 방식'],['공고·첨부','공고번호·기관·예산·기한','원본 경로·해시'],['참가 조건','업종·지역·직접생산·공동수급','출처와 문구'],['평가 조건','실적·인력·인증·배점','없음/미확인 구분'],['쟁점','문서 충돌·추출 불완전','보류 사유']],54,363,754,213,[184,300,270],{size:15});
 box(s,840,363,386,213,C.paper,C.line,8);addText(s,'검수 결과',860,382,150,28,18,C.navy,true);bullets(s,['51건 · 15열 · 빈 요건 셀 없음','12개 쟁점 공고 원문 재대조','나머지 39개 공고 셀은 유지','원문·전체 추출 텍스트는 Git 제외'],860,425,340,128,15,C.ink,5);
 foot(s,'표본은 전체 나라장터를 대표하는 확률표본이 아니라 파일럿 구축용 검수 표본');
 addNote('표본은 월별 17건씩 균등하게 51건을 구성했습니다. 분야는 SW 개발 32건과 운영·유지관리 19건입니다. 공고번호, 기관, 예산, 기한과 참가·평가 조건을 15열 요건 시트로 정리했습니다. 12개 쟁점 공고는 원문을 다시 대조했고, 나머지 39개는 기존 셀을 유지했습니다.','project-docs/데모개선/2026-09-14/existing51-distribution.json; project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md','확률표본 또는 전체 대표성 주장 금지');
}

// 9 distribution
{
 const s=p.slides.add();header(s,8,'51건 안에서도 금액과 조건 조합이 다양하다','조건 수는 “언급 여부”이며 필수·허용·금지 판정 수가 아니다');
 chart(s,['5천만 미만','5천만~1억','1~3억','3억 이상'],[{name:'공고 수',values:[7,20,16,8],fill:C.blue}],54,175,555,311,{legend:false});
 chart(s,['직접생산','공동수급','하도급','지역','서비스 인증'],[{name:'언급 공고',values:[42,48,51,46,5],fill:C.teal}],645,175,581,311,{legend:false});
 box(s,54,512,1172,67,C.paleOrange,'#F3CD96',8);addText(s,'해석 주의',72,526,110,24,15,C.orange,true);addText(s,'“공동수급 48건”은 공동수급이라는 조건이 등장했다는 뜻이며, 48건 모두 허용한다는 뜻이 아니다.',182,524,1020,28,16,C.ink,true);
 takeaway(s,'단순 키워드 집계에서 멈추지 않고, 답변 단계에서는 허용·금지·예외와 근거 범위를 다시 확인',C.navy);foot(s,'분모 51 · 조건은 다중 언급');
 addNote('표본의 예산은 5천만원 미만 7건, 5천만원에서 1억원 20건, 1억원에서 3억원 16건, 3억원 이상 8건입니다. 조건 언급은 직접생산 42건, 공동수급 48건, 하도급 51건, 지역 46건, 서비스 인증 5건입니다. 다만 이 수치는 조건이 언급된 횟수이며, 허용이나 금지를 자동 판정한 결과가 아닙니다.','project-docs/데모개선/2026-09-14/existing51-distribution.json','언급 집계와 의무·허용·금지 판정을 구분');
}

// 10 reconciliation
{
 const s=p.slides.add();header(s,9,'원문 재대조는 “충돌을 없애는 작업”이 아니었다','문서 차이를 숨기지 않고 답변 가능한 범위와 판단 보류 범위를 분리');
 const vals=[['상태','건수','대표 사례','처리 원칙'],['첨부 미확보','2','법원센터·부산올랭','RFP 확보 전 없음으로 단정 금지'],['원문 문제 확인','6','천안·경기·첨단로봇·동아·강릉 등','양쪽 문서와 적용 범위 병기'],['일부 해소','4','충남 ESG·경민대·승차권·광양','확인된 항목만 수정, 잔여 쟁점 유지']];
 table(s,vals,54,164,1172,226,[180,90,330,572],{size:15});
 const rules=[['01','출처 고정','공고문·RFP·과업서·메타데이터를 구분'],['02','범위 고정','예산·실적·배점의 적용 대상을 분리'],['03','보류 유지','정정공고·발주기관 답변이 없으면 단일값 확정 금지'],['04','추출 한계','표·수식 경계가 깨지면 임의 복원하지 않음']];
 rules.forEach(([n,h,b],i)=>{const x=54+i*293;box(s,x,426,270,133,C.paper,C.line,8);tag(s,n,x+14,440,46,[C.blue,C.teal,C.orange,C.red][i]);addText(s,h,x+72,440,176,25,17,C.ink,true);addText(s,b,x+16,483,238,58,14,C.muted);});
 takeaway(s,'판단 보류는 실패가 아니라 원문이 허용하는 정확한 상태',C.navy);foot(s,'12개 쟁점 공고 재대조 · 파일 해시는 별도 식별 JSON에 보존');
 addNote('12개 쟁점 공고 중 첨부 미확보 2건, 원문 문제 확인 6건, 일부 해소 4건으로 정리했습니다. 검수의 목적은 충돌을 없애는 것이 아니라 출처와 범위를 고정하는 것입니다. 정정공고나 발주기관 답변이 없으면 판단 보류를 유지하고, 표나 수식이 깨진 경우 임의로 값을 복원하지 않았습니다.','project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md','12개 쟁점 범위, 51건 전수 법률 검증 아님');
}

// 11 synthetic master
{
 const s=p.slides.add();header(s,10,'가상 기업 5곳은 51건의 조건을 비교하기 위한 기준 회사다','실제 업체 정보가 아니라, 충족·미충족·자료부족 사례를 유지하는 합성 원장');
 const ms=[['5','가상 기업',C.blue],['45','인력 레코드',C.teal],['16','프로젝트',C.orange],['111','증빙 레코드',C.purple],['45','문서 템플릿',C.red]];ms.forEach(([n,l,c],i)=>metric(s,n,l,54+i*235,165,215,c));
 box(s,54,310,1172,238,C.paper,C.line,8);addText(s,'원장 설계 원칙',74,329,210,28,18,C.navy,true);
 const principles=[['고정 사실','공고마다 회사 주소·면허·실적을 바꾸지 않음'],['경계 사례','69,999,999원 vs 70,000,000원처럼 임계값을 보존'],['증빙 상태','금액이 있어도 missing 증빙은 인정으로 승격하지 않음'],['시간 상태','인증 유효기간·재직·기존 배치·잔여 FTE를 기준일로 계산'],['격리','평가 기대답과 라벨을 검색 문서에 복사하지 않음'],['보안','L2와 L3를 분리하고 tenant·역할을 문서 메타데이터로 고정']];
 principles.forEach(([h,b],i)=>{const x=76+(i%2)*565,y=376+Math.floor(i/2)*54;addText(s,'●',x,y,20,20,14,[C.blue,C.teal,C.orange][Math.floor(i/2)],true);addText(s,h,x+24,y,100,22,15,C.ink,true);addText(s,b,x+126,y,402,34,14,C.muted);});
 takeaway(s,'합성 데이터를 사용해 실제 기업 기밀 없이도 권한·경계값·자료부족 시나리오를 반복 검증',C.navy);foot(s,'자동검사 32개 통과 · 접근 규칙 20개 사례 통과 · 사람 승인 pending');
 addNote('가상 기업 원장에는 5개 회사, 45명 인력, 16개 프로젝트, 111개 증빙 레코드와 45개 문서 템플릿이 있습니다. 회사 사실은 공고마다 바뀌지 않고, 금액 경계와 증빙 부족, 인증 기간, 잔여 FTE를 의도적으로 유지했습니다. 실제 기업 기밀 없이도 권한과 판단 경계를 반복 검증하기 위한 설계입니다.','project-docs/가상기업/v1/validation_report.json; project-docs/가상기업/v1/README.md','모든 회사·인력·실적·인증·원가는 합성 설정');
}

// 12 company matrix
{
 const s=p.slides.add();header(s,11,'기업마다 강점과 제약을 다르게 설계했다','모든 회사를 쉽게 통과시키지 않고, 실제 검토처럼 자료부족과 조건 미충족을 남김');
 const vals=[['기업','규모·특성','주요 강점','의도적으로 유지한 제약'],['C01 한빛IT','소기업 · 웹/포털','개발 실적·개발 인력','0036 미보유 · 실적 증빙 missing'],['C02 해온시스템','소기업 · 유지관리','운영 경험·현장 대응','직접생산 만료 · 0.5 FTE 기존 배치 · 확약서 없음'],['C03 인우블록','소기업 · 소규모 개발','다역할 인력 구성','실적 증빙 missing · 공동수급 실패 사례'],['C04 누리클라우드','소기업 · 클라우드','클라우드 운영 인력','회사 ISO와 서비스 CSAP 분리 · 공급권한 없음'],['C05 새온에너지SW','중기업 · 산업 SW','장비 연계·제조 도메인','일부 실적 증빙·전체 장비 견적 없음']];
 table(s,vals,54,158,1172,350,[176,210,300,486],{size:13});
 box(s,54,529,1172,58,C.paleBlue,'#B9CDFF',8);addText(s,'생성 결과',72,544,120,23,15,C.blue,true);addText(s,'C01 5문서·27청크 + C02~C05 36문서·140청크 · 공통문서와 공고별 문서를 구분',194,542,1004,28,16,C.ink,true);
 takeaway(s,'제약을 없애지 않고 보존했기 때문에 “가능·불가·자료부족”을 모두 평가할 수 있다',C.navy);foot(s,'합성 회사 문서는 실제 제출 가능한 입찰안이나 기관 발급 증명서가 아님');
 addNote('다섯 회사는 모두 다른 제약을 갖습니다. 한빛IT는 정보통신공사업 0036을 보유하지 않고, 해온시스템은 직접생산 인증 만료와 기술지원 확약서 부족이 있습니다. 인우블록은 실적 증빙, 누리클라우드는 서비스 CSAP와 공급권한, 새온에너지SW는 장비 견적이 부족합니다. 이런 제약을 유지해야 정상 통과 사례뿐 아니라 미충족과 자료부족도 평가할 수 있습니다.','project-docs/가상기업/v1/company_master.json; project-docs/가상기업/v1/generated/C01/r1/README.md; project-docs/가상기업/v1/generated/C02-C05/r1/README.md','합성 설정이며 실제 제출 자료 아님');
}

// 13 L1/L2/L3
{
 const s=p.slides.add();header(s,12,'L1·L2·L3로 문서 성격과 검색 범위를 분리했다','검색 코퍼스 223문서·3,275청크의 실제 구성');
 chart(s,['L1 공개','L2 회사','L3 민감'],[{name:'문서',values:[167,34,22],fill:C.blue}],54,171,545,302,{legend:false});
 chart(s,['L1 공개','L2 회사','L3 민감'],[{name:'청크',values:[3002,159,114],fill:C.teal}],633,171,593,302,{legend:false});
 const bands=[['L1','나라장터 공고·RFP·과업지시서','모든 인증 사용자',C.blue],['L2','자기 회사 실적·인력·인증·배치안','bid analyst 이상',C.teal],['L3','원가·마진·견적·투찰 검토','cost analyst / approver',C.red]];
 bands.forEach(([l,d,r,c],i)=>{const x=54+i*390;box(s,x,505,362,76,C.paper,C.line,8);tag(s,l,x+14,519,46,c);addText(s,d,x+72,516,272,24,14,C.ink,true);addText(s,r,x+72,545,272,20,12,C.muted);});
 takeaway(s,'보안 등급은 문서의 성격, ACL은 로그인 사용자가 실제로 검색할 수 있는 범위를 결정',C.navy);foot(s,'L2·L3는 실제 기업 자료가 아닌 합성 내부 자료');
 addNote('실제 검색 코퍼스는 L1 167문서와 3,002청크, L2 34문서와 159청크, L3 22문서와 114청크입니다. L1은 공개 공고, L2는 자기 회사의 실적·인력·인증, L3는 원가와 투찰 검토입니다. 등급 분류와 사용자 권한 검사는 구분되며, L2와 L3는 모두 합성 자료입니다.','project-docs/RAG파일럿/workstation-275/index_manifest.json','로컬 실험 색인이며 production index가 아님');
}

// 14 evaluation data
{
 const s=p.slides.add();header(s,13,'300개 Q-A-R은 검색 DB가 아니라 평가 기준이다','질문·기대답·근거를 검색 문서와 분리해 생성 입력 누출을 막음');
 const a=node(s,'51건 요건','공고별 참가·실적·인력·인증·금액·일정',54,181,275,141,C.blue);const b=node(s,'가상 기업 5곳','회사별 강점·제약과 증빙 상태',375,181,275,141,C.teal);const c=node(s,'회사당 60문항','5 × 60 = 300 Q-A-R',696,181,275,141,C.orange);const d=node(s,'근거 연결','공고 발췌 299개\n회사 청크 연결 237개',1017,181,209,141,C.purple);arrow(s,a,b);arrow(s,b,c);arrow(s,c,d);
 table(s,[['검증 항목','결과','의미'],['질문 ID','300개 고유','회사별 60개'],['공고','51개','검수 표본 전체 연결'],['신규 평가 문서/청크','15 / 106','평가 전용 자산'],['기존 회귀','v1/r1 hash·C01 byte 재생성 통과','기존 자료 변경 방지'],['실제 답변/span','0 / 0','평가 데이터 생성 시점에는 미포함']],54,358,842,214,[250,220,372],{size:14});
 box(s,928,358,298,214,C.paleOrange,'#F1C783',8);addText(s,'누출 방지',948,377,120,26,17,C.orange,true);bullets(s,['기대답·라벨은 검색 문서에서 제외','평가 파일은 별도 경로에 격리','질문과 생성 답변을 같은 정본 ID로 연결','사람 승인 전 gold 성능으로 부르지 않음'],948,418,252,136,14,C.ink,5);
 foot(s,'문자열·참조 검사는 의미적 정답이나 검색 성능 보증이 아님');
 addNote('평가 데이터는 51건 요건과 가상 기업 5곳을 조합해 회사당 60문항, 총 300문항으로 만들었습니다. 고유 공고 발췌는 299개, 회사 청크 연결은 237개입니다. 기대답과 라벨은 검색 문서에 넣지 않았고, 평가 파일도 별도 경로로 격리했습니다. 이 단계의 검증은 구조와 참조 검증이지 의미적 정답 보증은 아닙니다.','project-docs/평가데이터/v2/validation/report.json','300개는 검색 코퍼스가 아님, 사람 승인 pending');
}

// 15 full architecture
{
 const s=p.slides.add();header(s,14,'ASTRA는 구축 파이프라인과 질의 파이프라인을 분리한다','정본을 한 번 구축하고, 질의마다 권한·검색·생성·검증을 순서대로 적용');
 const rows=[
  {y:167,label:'BUILD',color:C.blue,nodes:[['수집','OpenAPI·첨부'],['변환','파싱·해시·실패'],['정리','51건 요건'],['합성','기업 L2/L3'],['색인','223문서·3,275청크']]},
  {y:330,label:'RUN',color:C.teal,nodes:[['질문','공고·회사·역할'],['ACL','허용 문서 후보'],['검색','BM25 + E5 + RRF'],['생성','Qwen3-4B 로컬'],['검증','규칙 + 탐지기']]},
  {y:493,label:'OUTPUT',color:C.orange,nodes:[['답변','판단·설명'],['인용','[1] [2] 위치'],['근거','원문 구절'],['상태','충족·미충족·보류'],['경고','의심 구절·미검사']]}
 ];
 rows.forEach(row=>{tag(s,row.label,54,row.y+31,76,row.color);const ns=[];row.nodes.forEach(([h,b],i)=>ns.push(node(s,h,b,153+i*215,row.y,185,103,row.color)));for(let i=0;i<4;i++)arrow(s,ns[i],ns[i+1],row.color);});
 foot(s,'구축 시점과 질의 시점을 분리해 같은 정본·버전·권한 정책을 재사용');
 addNote('위쪽은 구축 파이프라인입니다. 공개 공고와 합성 기업 자료를 정본, 해시, 메타데이터와 함께 색인합니다. 가운데는 질의 파이프라인으로 질문, 권한 필터, 하이브리드 검색, 로컬 생성, 검증 순서입니다. 아래 출력은 답변만이 아니라 인용, 근거, 조건 상태와 의심 구절을 함께 반환합니다.','procurement-pipeline/rag_pilot.py; project-docs/RAG파일럿/workstation-275/index_manifest.json','구축과 질의 실행을 구분');
}

// 16 user workflow
{
 const s=p.slides.add();header(s,15,'사용자 질문은 여섯 단계를 거친다','권한 밖 문서는 검색 결과를 만든 뒤 숨기는 것이 아니라 검색 전에 제외');
 const steps=[['1','공고·회사 선택','질문과 기준일 입력',C.blue],['2','세션 검증','tenant·회사·역할·시나리오',C.teal],['3','ACL 필터','허용 문서 ID만 남김',C.red],['4','하이브리드 검색','키워드+벡터 순위 결합',C.purple],['5','로컬 답변 생성','선택 근거 최대 4개 사용',C.orange],['6','검증·표시','규칙·탐지·근거 UI',C.green]];
 steps.forEach(([n,h,b,c],i)=>{const x=54+(i%3)*390,y=172+Math.floor(i/3)*193;box(s,x,y,362,150,C.paper,C.line,9);circle(s,x+18,y+18,44,c);addText(s,n,x+18,y+26,44,24,16,C.white,true,{align:'center'});addText(s,h,x+78,y+20,250,29,20,C.ink,true);addText(s,b,x+78,y+62,250,50,15,C.muted);});
 line(s,416,247,444,247,C.muted,2);line(s,806,247,834,247,C.muted,2);line(s,416,440,444,440,C.muted,2);line(s,806,440,834,440,C.muted,2);
 takeaway(s,'클라이언트가 보낸 역할 문자열이 아니라 서버가 확인한 세션과 멤버십이 검색 범위를 결정',C.navy);foot(s,'실제 생성에 사용한 근거와 탐지 입력 근거를 동일하게 유지');
 addNote('사용자는 공고와 회사를 선택하고 질문합니다. 서버는 세션의 tenant, 회사, 역할과 시나리오를 확인하고, 허용 문서 ID만 남깁니다. 그 안에서 키워드와 벡터 검색을 결합하고 최대 4개 근거로 로컬 답변을 생성합니다. 마지막으로 규칙과 탐지를 수행해 답변과 근거, 의심 구절을 표시합니다.','procurement-pipeline/rag_pilot.py; project-docs/데모개선/2026-09-15/local-integration/README.md','파일럿 세션 정책과 운영 인증 체계를 구분');
}

// 17 ACL matrix
{
 const s=p.slides.add();header(s,16,'역할·회사·tenant·시나리오를 함께 검사한다','같은 역할이어도 다른 회사 문서나 승인되지 않은 시나리오는 검색하지 못함');
 table(s,[['역할','L1 공개','자기 회사 L2','자기 회사 L3','대표 업무'],['viewer','허용','차단','차단','공개 공고 확인'],['bid_analyst','허용','허용','차단','실적·인력·인증 검토'],['cost_analyst','허용','허용','허용','원가·견적 검토'],['bid_approver','허용','허용','허용','투찰 승인 검토']],54,166,740,306,[180,120,145,145,150],{size:15});
 box(s,830,166,396,306,C.paper,C.line,8);addText(s,'서버 검사 항목',850,185,200,29,19,C.navy,true);bullets(s,['authenticated = true','membership_active = true','tenant_id 일치','company_id 일치','role이 문서 allowed_roles에 포함','scenario_id와 기준일 유효'],850,235,334,192,16,C.ink,6);
 box(s,54,499,1172,82,C.paleRed,'#EFBBB5',8);addText(s,'차단은 정상 결과다',74,514,180,25,17,C.red,true);addText(s,'평가 300건 중 5건은 권한 정책에 따라 LLM을 호출하지 않고 access_denied로 기록했다.',256,512,938,31,17,C.ink,true);addText(s,'차단 답변을 빈 답변이나 모델 실패로 집계하지 않는다.',256,545,938,22,14,C.muted);
 foot(s,'파일럿 역할 정책 구현 · 운영용 인증·인가 및 감사로그는 후속 연결 범위');
 addNote('viewer는 공개 L1만, bid analyst는 자기 회사 L2까지, cost analyst와 bid approver는 허용된 L3까지 접근합니다. 역할만 확인하지 않고 로그인, 멤버십, tenant, 회사, 시나리오와 기준일을 함께 검사합니다. 평가 중 5건은 이 정책에 따라 모델 호출 전에 정상 차단했습니다.','procurement-pipeline/rag_pilot.py ROLE_LEVELS; project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json','파일럿 정책, 운영 인증·인가 완성 아님');
}

// 18 ACL invariants
{
 const s=p.slides.add();header(s,17,'권한 필터는 검색 순위 계산보다 먼저 실행된다','전역 검색 후 화면에서 숨기는 방식보다 데이터 경계를 앞단에서 강제');
 const ns=[node(s,'신뢰된 세션','사용자·멤버십·tenant\n회사·역할·시나리오',54,189,250,150,C.teal),node(s,'허용 문서 집합','security_level\ncompany_id · allowed_roles',363,189,250,150,C.red),node(s,'키워드·벡터 점수','허용 문서의 청크만\n점수 계산',672,189,250,150,C.blue),node(s,'근거·원문 열람','답변·인용·다운로드에\n동일 정책 적용',981,189,245,150,C.orange)];for(let i=0;i<3;i++)arrow(s,ns[i],ns[i+1]);
 const vals=[['검사한 실패 유형','기대 동작'],['타 tenant / 타 회사 문서 ID','요청 거부 또는 후보에서 제거'],['L2에 L3 내용 혼입','정본·스키마 검사 실패'],['기대답·라벨 필드 오염','생성·색인 검사 실패'],['잘못된 offset / 답변 hash','검수·데모 자료 검증 실패']];table(s,vals,54,380,763,203,[360,403],{size:14});
 box(s,850,380,376,203,C.paleTeal,'#A8D9CF',8);addText(s,'검증 자산',870,397,140,24,16,C.teal,true);bullets(s,['가상기업 접근 규칙 20건 통과','C01 7개 사용자 상황 × 27청크 = 189개 메타데이터 검사','데모 오류 주입 검사에서 L2 혼입·타회사 ID·기대답 유입 거부'],870,438,326,126,14,C.ink,5);
 foot(s,'오프라인 정책 검사와 실서비스 침투·보안 검증은 구분');
 addNote('ACL은 검색 결과를 만든 후 숨기는 것이 아니라, 허용 문서 집합을 먼저 만든 뒤 그 안에서 점수를 계산합니다. 답변 인용과 문서 열람에도 같은 정책을 사용합니다. 가상기업 접근 규칙 20건, C01 메타데이터 규칙 189건을 검사했고, 데모 오류 주입에서도 타회사 문서와 L2 혼입을 거부했습니다. 다만 이는 실서비스 침투 테스트가 아닙니다.','project-docs/가상기업/v1/validation_report.json; project-docs/가상기업/v1/generated/C01/r1/README.md; project-docs/데모개선/2026-09-14/README.md','오프라인·파일럿 검사와 운영 보안 검증을 구분');
}

// 19 chunking
{
 const s=p.slides.add();header(s,18,'색인은 정본·버전·문자 위치를 함께 보존한다','긴 문서는 의미 단위 parent chunk를 만들고 임베딩 window와 생성 근거를 분리');
 const cards=[['문서 정본','document_id · version · SHA-256\n원본 binary hash 대조',C.blue],['Parent chunk','최대 1,800자 · overlap 240자\n회사 entity는 온전하게 재사용',C.teal],['Offset','Unicode code point\n[start, end) · LF 기준',C.orange],['실패 분리','읽을 수 없는 문서 16개\n이번 색인에서 제외·사유 보존',C.red]];
 cards.forEach(([h,b,c],i)=>node(s,h,b,54+i*293,170,270,143,c));
 table(s,[['등급','문서','청크','문서당 평균 청크'],['L1','167','3,002','18.0'],['L2','34','159','4.7'],['L3','22','114','5.2'],['합계','223','3,275','14.7']],54,352,650,225,[140,120,130,260],{size:15});
 box(s,740,352,486,225,C.paper,C.line,8);addText(s,'생성 근거 보존 원칙',760,371,220,27,18,C.navy,true);bullets(s,['모델 입력에는 검색으로 선택된 parent 원문 사용','탐지기도 당시 생성에 사용한 동일 근거를 입력','사후 전체 원문은 별도 진실성 검토에만 사용','정본 답변과 근거 hash가 다르면 resume 중단'],760,414,430,142,15,C.ink,5);
 foot(s,'production index = not_indexed · local experiment index = SQLite/NumPy');
 addNote('색인은 문서 ID와 버전, SHA-256을 보존합니다. parent chunk는 최대 1,800자, overlap 240자이며, 문자 위치는 Unicode code point의 시작 포함·끝 제외 규칙입니다. 16개 문서는 사용할 수 있는 텍스트가 없어 제외 사유를 남겼습니다. 생성과 탐지에는 실제 생성 당시 선택된 동일 근거를 사용합니다.','project-docs/RAG파일럿/workstation-275/index_manifest.json; project-docs/환각라벨링/detector-300-workstation-v1/README.md','로컬 실험 색인, production index 아님');
}

// 20 embeddings
{
 const s=p.slides.add();header(s,19,'3,275개 parent 청크를 7,195개 임베딩 window로 확장했다','긴 문맥은 잘라 버리지 않고, window 최대 유사도를 parent 순위에 사용');
 const flow=[node(s,'Parent text','3,275개\n생성용 원문 유지',54,187,228,132,C.blue),node(s,'Token window','460 token\nstride 420',332,187,228,132,C.teal),node(s,'Embedding','multilingual-e5-small\n384차원 · L2 정규화',610,187,228,132,C.purple),node(s,'Parent score','window 최대 점수\nparent 최대 3 window',888,187,338,132,C.orange)];for(let i=0;i<3;i++)arrow(s,flow[i],flow[i+1]);
 const ms=[['7,195','embedding windows',C.blue],['512','token limit',C.teal],['8','batch size',C.orange],['4','CPU threads',C.purple],['1,379.6초','index build',C.red]];ms.forEach(([n,l,c],i)=>metric(s,n,l,54+i*235,363,215,c));
 box(s,54,509,1172,70,C.paleBlue,'#B9CCFB',8);addText(s,'모델 고정',72,524,120,24,15,C.blue,true);addText(s,'intfloat/multilingual-e5-small · revision 614241… · MIT · query:/passage: prefix · truncation=false',192,522,1008,29,15,C.ink,true);
 foot(s,'문서 임베딩은 CPU float32로 구축 · 생성 모델 GPU 실행과 별도');
 addNote('3,275개 parent 청크를 460토큰 window와 420토큰 stride로 나눠 7,195개 임베딩을 만들었습니다. multilingual-e5-small 384차원 벡터를 L2 정규화하고, 같은 parent의 window 중 최대 유사도를 parent 점수로 사용합니다. 구축은 CPU float32, 배치 8, 스레드 4로 1,379.6초가 걸렸습니다.','project-docs/RAG파일럿/workstation-275/embedding_config.json; project-docs/RAG파일럿/workstation-275/validation/vector_validation.json','임베딩 구축 시간은 해당 워크스테이션 1회 기록');
}

// 21 hybrid retrieval
{
 const s=p.slides.add();header(s,20,'키워드와 의미 검색을 RRF로 결합한다','코드·금액·날짜는 정확히, 표현이 다른 문장은 의미로 보완');
 const k=node(s,'Lexical','한국어 2글자 부분어\n영문·숫자 exact token\nBM25 형태 점수',54,178,320,180,C.blue);const v=node(s,'Dense','multilingual-e5-small\n질문과 문장 의미 유사도\nwindow 최대 parent 점수',480,178,320,180,C.teal);const r=node(s,'RRF 결합','rank 기반 결합 · k=60\n상위 parent 최대 6개\n생성에는 우선 최대 4개',906,178,320,180,C.orange);arrow(s,k,v);arrow(s,v,r);
 box(s,54,395,1172,86,C.paper,C.line,8);addText(s,'RRF(d) = Σ 1 / (60 + rankₘ(d))',86,416,520,38,24,C.navy,true);addText(s,'검색기의 점수 척도를 직접 섞지 않고 각 순위를 안정적으로 합산',640,420,548,30,17,C.muted,true,{align:'right'});
 const ex=[['“8111159901”','키워드가 코드 경계를 보존'],['“장애 방문과 복구시간 차이”','벡터가 유사 표현을 보완'],['“1억원 이상 실적”','숫자 exact + 의미 문맥을 함께 확인']];ex.forEach(([q,a],i)=>{const x=54+i*390;box(s,x,506,362,72,C.paleTeal,'#B2DED6',8);addText(s,q,x+14,519,334,21,14,C.teal,true);addText(s,a,x+14,544,334,20,12,C.ink);});
 foot(s,'현재 구현은 권한형 하이브리드 RAG · 별도 그래프 DB 기반 GraphRAG로 표현하지 않음');
 addNote('키워드 검색은 코드, 금액, 날짜처럼 정확한 표현에 강합니다. 벡터 검색은 같은 의미의 다른 표현을 보완합니다. 두 검색의 원점수를 직접 섞지 않고 RRF k 60으로 순위를 결합합니다. 상위 parent를 최대 6개 선정하고, 생성에는 우선 최대 4개를 전달합니다.','procurement-pipeline/rag_pilot.py; project-docs/평가데이터/v2/retrieval_manifest.json','별도 그래프 DB 기반 GraphRAG 아님');
}

// 22 generation GPU
{
 const s=p.slides.add();header(s,21,'답변은 외부 API 없이 로컬 GPU에서 생성했다','Qwen3-4B GGUF 모델을 한 번 로드하고 여러 문항을 배치·재개 방식으로 처리');
 const ms=[['Qwen3-4B','생성 모델',C.blue],['Q4_K_M','양자화',C.teal],['4,096','context',C.orange],['768','max tokens',C.purple],['37 / 37','GPU offload layers',C.red],['5,588 MiB','peak GPU memory',C.green]];ms.forEach(([n,l,c],i)=>metric(s,n,l,54+(i%3)*390,160+Math.floor(i/3)*132,362,c));
 table(s,[['설정','값','목적'],['temperature / top_p / top_k','0.7 / 0.8 / 20','일관성과 표현 다양성 균형'],['max evidence chunks','4','근거 범위 제한'],['batch / ubatch','512 / 512','워크스테이션 처리량 조정'],['backend / device','Vulkan / RTX A5000','37개 layer 전부 offload'],['외부 API','사용 안 함','회사 자료 전송 경계 통제']],54,438,1172,143,[280,310,582],{size:13});
 foot(s,'모델·revision·파일 SHA-256·프로필을 environment.json에 기록');
 addNote('생성 모델은 Qwen3-4B GGUF Q4_K_M입니다. context 4,096, 최대 출력 768토큰, 근거 최대 4개를 사용했습니다. 워크스테이션에서는 Vulkan으로 RTX A5000에 37개 레이어를 모두 offload했고, 기록된 peak GPU memory는 5,588 MiB입니다. 외부 API는 사용하지 않았으며 모델 파일 해시와 프로필을 기록했습니다.','project-docs/RAG파일럿/workstation-275/environment.json; project-docs/RAG파일럿/workstation-275/validation/runtime_tuning.json','GPU 수치는 해당 워크스테이션 실행 기록');
}

// 23 generation results
{
 const s=p.slides.add();header(s,22,'정본 답변 295건과 정상 차단 5건을 보존했다','에이전트 검토 분포는 탐색 결과이며 독립 정확도나 사람 gold 성능이 아니다');
 metric(s,'295','생성 답변',54,160,230,C.blue,'기존 25 + 신규 275');metric(s,'5','정상 접근 차단',304,160,230,C.teal,'LLM 호출 없음');metric(s,'4','잘림 답변',554,160,230,C.red,'신규 275 중');metric(s,'1','인용번호 오류 답변',804,160,230,C.orange,'신규 275 중');metric(s,'6','선택 재시도 ID',1054,160,172,C.purple,'repair attempt');
 chart(s,['correct','partial','incorrect'],[{name:'신규 275 에이전트 검토',values:[73,133,69],fill:C.blue}],54,306,654,267,{legend:false});
 box(s,742,306,484,267,C.paleOrange,'#F2CA8A',8);addText(s,'이 분포를 정확도로 부르지 않는 이유',762,325,438,28,18,C.orange,true);bullets(s,['질문마다 조건과 난도가 섞여 있음','실행 후 라우팅 repair에 노출된 개발 자료','에이전트 검토 rubric이며 사람 승인 아님','구절 단위 환각 라벨링은 당시 수행하지 않음'],762,371,434,155,15,C.ink,6);addText(s,'correct 73 · partial 133 · incorrect 69',762,539,430,22,14,C.navy,true);
 foot(s,'원본 25답변은 보존 · 답변·prompt·record hash로 선택 결과 고정');
 addNote('최종 선택 결과는 생성 답변 295건과 정상 차단 5건입니다. 신규 275건의 에이전트 검토는 correct 73, partial 133, incorrect 69였고, 잘림 4건과 인용번호 오류 1건이 있었습니다. 하지만 이 분포는 사람이 승인한 독립 정확도가 아닙니다. 개발 자료에 대한 탐색적 품질 검토로만 사용합니다.','project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json','에이전트 검토를 정확도·독립 테스트 성능으로 표현 금지');
}

// 24 detector design
{
 const s=p.slides.add();header(s,23,'환각 탐지는 답변을 실제 생성 근거와 직접 대조한다','답변 전체를 보되, 모델·규칙·인용 검사를 서로 다른 신호로 유지');
 const steps=[['입력 고정','질문·정본 답변\n당시 prompt 근거 hash',C.blue],['근거 window','긴 근거를 분할하되\nparent·offset 보존',C.teal],['토큰 분류','KLUE / XLM-R / BGE-M3\n0=정상 · 1=의심',C.purple],['규칙 검사','금액·VAT·날짜·자격\nFTE·주체·부정 표현',C.orange],['문자 구절','Unicode offset으로\n의심 구절·미검사 범위',C.red]];const ns=[];steps.forEach(([h,b,c],i)=>ns.push(node(s,h,b,54+i*235,177,214,166,c)));for(let i=0;i<4;i++)arrow(s,ns[i],ns[i+1]);
 const vals=[['판정 유형','의미','평가에서의 처리'],['CONTRADICTION','근거와 명시적으로 모순','환각 구절'],['UNSUPPORTED','근거가 답변 주장을 지지하지 않음','환각 구절'],['UNCERTAIN','근거 부족으로 확정 불가','보류 · 정상으로 계산 금지'],['CITATION_ERROR','인용번호·위치 오류','내용 환각과 별도'],['QUALITY_ONLY','잘림·형식·문장 품질','탐지 성능과 별도']];table(s,vals,54,378,1172,198,[220,470,482],{size:13});
 foot(s,'모델 예측은 라벨 초안이 아니며, 사람 승인과 분리');
 addNote('탐지 입력은 질문, 정본 답변, 실제 생성 당시 prompt 근거입니다. 긴 근거는 window로 나누되 parent와 offset을 보존합니다. 토큰 분류 모델과 금액·날짜·자격 같은 규칙 검사를 별도로 적용하고, 최종 화면에는 Unicode 문자 위치로 의심 구절과 미검사 범위를 표시합니다. 인용 오류와 문장 품질은 내용 환각과 따로 평가합니다.','project-docs/환각라벨링/detector-300-workstation-v1/README.md; procurement-pipeline/detector300*.py','모델 예측과 사람 승인 라벨을 구분');
}

// 25 review labels
{
 const s=p.slides.add();header(s,24,'25문항 사람 검수는 접수됐고, 88개 구절 조정안을 만들었다','최종 사람 승인 전이므로 학습용 gold나 독립 테스트로 사용하지 않음');
 metric(s,'25','검수 문항',54,160,220,C.blue,'팀원별 서로 다른 문항');metric(s,'68','기존 구절',294,160,220,C.teal,'동의 65 · 수정 3');metric(s,'88','조정안 구절',534,160,220,C.orange,'추가·수정 포함');metric(s,'79','근거 청크 참조',774,160,220,C.purple,'read-only index hash 대조');metric(s,'pending','최종 승인',1014,160,212,C.red,'training_ready=false');
 chart(s,['UNSUPPORTED','UNCERTAIN','CONTRADICTION','CITATION','QUALITY'],[{name:'제안 구절',values:[41,16,15,14,2],fill:C.blue}],54,311,682,265,{legend:false});
 box(s,770,311,456,265,C.paper,C.line,8);addText(s,'조정 결과',790,329,160,26,18,C.navy,true);table(s,[['처리','구절'],['제안 수용','70'],['보류','16'],['품질만','2']],790,371,218,151,[130,88],{size:14});addText(s,'문항 결정',1030,329,160,26,18,C.navy,true);table(s,[['결정','문항'],['동의','12'],['수정 제안','12'],['재검토','1']],1030,371,176,151,[112,64],{size:13});addText(s,'검수자 간 중복 문항이 없어 inter-annotator agreement는 계산할 수 없음',790,539,410,27,13,C.red,true);
 foot(s,'원 제출 의견은 보존 · 에이전트 조정안과 사람 최종 승인 분리');
 addNote('25문항에서 기존 68개 구절 의견을 받았고, 추가와 수정을 포함해 88개 조정안 구절을 만들었습니다. 라벨 분포는 unsupported 41, uncertain 16, contradiction 15, citation error 14, quality only 2입니다. 70개는 제안 수용, 16개는 보류, 2개는 품질만으로 정리됐습니다. 최종 사람 승인은 아직 pending이고 training ready도 false입니다.','project-docs/환각라벨링/pilot-25-human-review-v1/validation_report.json; project-docs/환각라벨링/pilot-25-human-review-v1/intake_manifest.json','의도적으로 고른 개발 자료, 독립 테스트 아님');
}

// 26 model eval design
{
 const s=p.slides.add();header(s,25,'KLUE·XLM-R·BGE-M3 비교는 같은 입력 계약으로 진행한다','3모델 × 생성답변 295건 = 885 추론 슬롯, 차단 5건은 별도 무호출 검증');
 table(s,[['후보','입력 계약','평가 상태','발표 가능한 결론'],['KLUE','질문·근거 window·답변 token','평가 진행 중','운영 주력 후보, 우열 미확정'],['XLM-R','동일 정본·offset·window','평가 진행 중','KLUE 오류 보완 가설 때 비교'],['BGE-M3','동일 정본·offset·window','평가 진행 중','추가 비용 대비 개선 확인 필요']],54,166,1172,227,[180,370,220,402],{size:14});
 const metrics=[['답변 단위','TP / FP / FN / TN\n정밀도·재현율·F1',C.blue],['구절 단위','문자 P/R/F1\nexact-span F1',C.teal],['운영 단위','자동 판정률·보류율\n검사 커버리지',C.orange],['분석 단위','회사·오류 유형·길이\n시간·VRAM·실패',C.purple]];metrics.forEach(([h,b,c],i)=>node(s,h,b,54+i*293,430,270,129,c));
 takeaway(s,'현재는 “평가 설계와 입력 정합성 완료”, 성능 숫자는 완료 후 별도 반영',C.navy);foot(s,'미승인 라벨 기준 점수는 잠정 평가로만 표시');
 addNote('세 후보는 같은 질문, 답변, 근거 window와 offset 계약으로 비교합니다. 기본 추론 슬롯은 885개이며 정상 차단 5건은 별도로 검사합니다. 답변 단위와 문자 구절 단위, 자동 판정과 보류, 회사와 오류 유형별 성능을 함께 보고해야 합니다. 현재는 평가 설계와 입력 정합성까지만 발표할 수 있고 성능 우열은 미확정입니다.','project-docs/환각라벨링/detector-300-workstation-v1/README.md; project-docs/환각라벨링/detector-300-workstation-v1/WORKSTATION_PROMPT.md','성능 숫자·모델 우열 생성 금지');
}

// 27 errors
{
 const s=p.slides.add();header(s,26,'오류는 결론·근거·인용 위치에서 다르게 발생한다','25문항 조정안의 대표 사례 · 최종 사람 승인 pending');
 const ex=[['CONTRADICTION','“인천을 제외해도 된다”','근거는 서울·경기(인천 포함)라고 명시','부정 범위가 뒤집힘',C.red],['UNSUPPORTED','“기존 배치의 잔여 FTE가 0.0”','다른 인력의 값을 재사용','주체 연결이 근거에 없음',C.orange],['CITATION_ERROR','답변에 “[3]” 표시','실제 prompt 인용은 [1], [2]만 존재','내용과 별개로 인용 위치 오류',C.blue]];
 ex.forEach(([tagv,q,e,r,c],i)=>{const y=164+i*135;box(s,54,y,1172,112,C.paper,C.line,8);tag(s,tagv,70,y+17,142,c);addText(s,q,230,y+15,360,30,19,C.ink,true);addText(s,e,612,y+15,410,31,15,C.muted);addText(s,r,230,y+59,792,32,15,c,true);addText(s,'답변',1042,y+16,72,20,12,C.muted,true);addText(s,'근거',1042,y+51,72,20,12,C.muted,true);circle(s,1120,y+17,14,c);circle(s,1120,y+52,14,C.teal);line(s,1127,y+31,1127,y+52,C.line,2);});
 box(s,54,584,1172,48,C.paleOrange,'#F2C98E',8);addText(s,'탐지기가 해야 할 일: 문장 전체를 틀렸다고 지우는 것이 아니라, 바뀐 조건·없는 주체·잘못된 인용 위치를 표시',72,596,1136,25,17,C.ink,true,{align:'center'});
 foot(s,'사례는 모델 예측을 정답으로 복사하지 않고 답변과 실제 생성 근거를 대조해 작성');
 addNote('첫 사례는 근거가 서울·경기, 인천 포함이라고 했는데 답변이 인천을 제외해도 된다고 말한 모순입니다. 두 번째는 다른 인력 값을 재사용해 잔여 FTE를 0으로 만든 근거 없음 사례입니다. 세 번째는 prompt에 1번과 2번 인용만 있는데 3번을 사용한 인용 오류입니다. 탐지기는 답변 전체를 지우기보다 잘못된 구절과 이유를 표시해야 합니다.','project-docs/환각라벨링/pilot-25-human-review-v1 조정사항 및 검수 산출물','대표 조정안이며 최종 사람 승인 pending');
}

// 28 integrated status
{
 const s=p.slides.add();header(s,27,'통합 평가는 검색·생성·라벨·탐지를 분리해 보고한다','자동 검사 통과와 모델 성능 확정은 같은 상태가 아니다');
 table(s,[['평가 축','현재 확인 범위','상태','다음 검증'],['데이터','137,745행·285,252첨부·51건 표본','수집·변환·원문대조 완료','누락 RFP 2건 확보'],['색인','223문서·3,275청크·7,195 window','해시·offset·권한 메타 확인','운영 index 연결'],['생성','295답변·정상 차단 5','정본·선택·hash 고정','질문 충족도·오류 유형 승인'],['사람 라벨','25문항·88 조정안 구절','접수·조정 완료 / 승인 pending','최종 승인·training export'],['탐지','3모델 × 295 = 885슬롯','입력 동결 / 평가 진행 중','P/R/F1·보류·커버리지'],['UI','51공고·저장답변·L1 로컬 질문','정적/실행 모드 검증','운영 인증·L2/L3 자유질문']],54,158,1172,366,[160,352,270,390],{size:13});
 const gauges=[['재현 가능한 자산','완료',C.teal],['생성 답변 보존','완료',C.teal],['사람 gold 라벨','대기',C.orange],['탐지 성능','평가 중',C.red]];gauges.forEach(([a,b,c],i)=>{const x=54+i*293;box(s,x,548,270,49,C.paper,C.line,8);addText(s,a,x+14,561,160,22,14,C.ink,true);tag(s,b,x+184,558,70,c);});
 foot(s,'성능이 끝나지 않은 칸은 수치 대신 상태와 필요한 다음 검증을 명시');
 addNote('현재 상태를 한 표로 정리했습니다. 데이터와 색인, 생성 답변 보존은 완료 범위가 있습니다. 사람 라벨은 접수와 조정까지 완료됐지만 최종 승인 대기입니다. 탐지기는 입력을 동결했지만 885슬롯 전체 성능 평가가 진행 중입니다. UI도 저장 결과와 L1 로컬 질문은 검증했지만 운영 인증과 L2·L3 자유 질문은 남았습니다.','project-docs/프로젝트_진행현황_팀공유_2026-09-11.md; 각 최신 README와 manifest','완료·pending·평가 중을 혼합하지 않음');
}

// 29 UI
{
 const s=p.slides.add();header(s,28,'데모에서는 답변보다 “근거 연결”을 먼저 보여준다','51개 공고 탐색 → 질문 → 실제 입력 근거 → 답변 → 의심 구절 순서');
 box(s,54,157,560,407,C.paper,C.line,8);s.images.add({blob:await fs.readFile(path.join(repo,'project-docs/데모개선/2026-09-14/rag-observatory.png')),contentType:'image/png',alt:'ASTRA 근거 관측 화면',fit:'contain',position:{left:70,top:173,width:528,height:375}});tag(s,'EVIDENCE OBSERVATORY',72,174,178,C.teal);
 box(s,646,157,580,407,C.paper,C.line,8);s.images.add({blob:await fs.readFile(path.join(repo,'project-docs/데모개선/2026-09-14/ux-question-workspace/desktop.png')),contentType:'image/png',alt:'ASTRA 질문 화면',fit:'contain',position:{left:662,top:173,width:548,height:375}});tag(s,'QUESTION WORKSPACE',664,174,166,C.blue);
 const seq=[['1','지도에서 공고 선택'],['2','질문 입력·모드 확인'],['3','답변의 인용 클릭'],['4','원문 근거·의심 구절 확인']];seq.forEach(([n,t],i)=>{const x=54+i*293;box(s,x,581,270,45,C.paper,C.line,8);circle(s,x+10,590,27,[C.blue,C.teal,C.orange,C.red][i]);addText(s,n,x+10,595,27,16,11,C.white,true,{align:'center'});addText(s,t,x+46,592,208,23,14,C.ink,true);});
 foot(s,'저장 결과 모드 · L1 실제 질문 모드 · 탐지 미실시 상태를 화면에서 구분');
 addNote('데모에서는 먼저 51개 공고와 문서 연결 구조를 보여줍니다. 이후 질문 화면에서 공고를 선택하고 질문을 입력한 뒤 답변의 인용을 눌러 실제 입력 근거를 확인합니다. 저장 결과 모드와 L1 실제 질문 모드, 탐지 미실시 상태를 화면에서 구분합니다. L2와 L3 자유 질문은 Live DB와 완전히 연결되지 않았습니다.','project-docs/데모개선/2026-09-14/README.md; project-docs/데모개선/2026-09-15/local-integration/README.md','저장 결과 재생을 실시간 생성으로 표현하지 않음');
}

// 30 conclusion
{
 const s=p.slides.add();header(s,29,'구현 자산은 남았고, 성능 검증은 계속된다','프로젝트의 의미는 좋은 숫자 하나가 아니라 추적 가능한 데이터·근거·권한·검증 구조');
 const cols=[['완료한 자산',['3개월 수집·변환 파이프라인','51건 원문 검수와 쟁점 기록','합성기업 5곳과 L2/L3 자료','223문서·3,275청크 색인','평가 300문항·정본 답변 295건'],C.teal],['검증한 구조',['tenant·회사·역할 기반 ACL','BM25 + E5 + RRF 검색','Qwen3-4B 로컬 GPU 생성','정본·prompt·근거 hash 고정','25문항 사람 검수 접수·조정'],C.blue],['남은 과제',['25문항 최종 사람 승인','295답변 전체 탐지 비교','운영 인증·인가·감사로그','L2/L3 자유질문 Live 연결','독립 평가 분할과 운영 지표'],C.orange]];
 cols.forEach(([h,arr,c],i)=>{const x=54+i*390;box(s,x,166,362,386,C.paper,C.line,10);box(s,x,166,362,9,c,c,0);addText(s,h,x+22,188,318,34,23,c,true);bullets(s,arr,x+22,252,316,252,17,C.ink,10);});
 takeaway(s,'AI가 입찰을 대신 확정하는 시스템보다, 사람이 근거와 오류 가능성을 더 빨리 확인하는 시스템',C.navy);foot(s,'발표 후 성능 수치가 확정되면 모델 비교·통합 평가 슬라이드만 갱신 가능');
 addNote('ASTRA는 3개월 수집과 51건 원문 검수, 합성기업 5곳, 223문서와 3,275청크, 평가 300문항과 295개의 정본 답변을 남겼습니다. 권한형 검색과 로컬 생성, 검수 구조도 연결했습니다. 남은 과제는 최종 사람 승인과 295답변 전체 탐지 평가, 운영 인증과 L2·L3 Live 연결입니다. 프로젝트의 결론은 사람이 근거를 더 빨리 확인하도록 돕는 시스템을 구축했다는 것입니다.','project-docs/PPT_최종발표_제작_인수인계_프롬프트.md; 각 최신 README와 manifest','목표 미달 범위를 그대로 공개');
}

// 31 appendix tests
{
 const s=p.slides.add();header(s,30,'APPENDIX A · 재현성과 오류 주입 검증','각 검사는 구조·계약을 확인하며 자유서술 전체의 정확성을 보장하지 않는다');
 table(s,[['구간','검사 규모','주요 검사','결과'],['가상기업 마스터','32 unit tests','스키마·날짜·인증·VAT·지분·참조','통과'],['C01 문서','24 + 32 = 56 tests','청크 offset·기대답 오염·L2/L3 혼입','통과'],['접근 규칙','20 cases / C01 189 metadata checks','타 tenant·역할·비활성 사용자','통과'],['RAG 워크스테이션','158 기존 + 9 신규 offline regressions','resume·hash·권한·retrieval 계약','통과'],['공개 데모','Python 9 + JS 구조 검사','타회사 ID·잘못된 offset·답변 교체·XSS','통과'],['로컬 통합','17 + 9 + 7 + 8 프로토콜/회귀','모델→detecting→done·취소·미설정','통과']],54,158,1172,345,[220,230,532,190],{size:13});
 box(s,54,530,1172,72,C.paleOrange,'#F0C887',8);addText(s,'검사 경계',72,545,120,23,15,C.orange,true);addText(s,'자동 검사는 파일 구조·정본·계산·프로토콜을 검증한다. 검색 Recall, 답변 정확도, 탐지 F1과 운영 보안은 별도 평가가 필요하다.',194,542,1006,37,15,C.ink,true);
 foot(s,'테스트 수는 서로 다른 단계의 실행 기록이며 중복을 합산한 총 테스트 수로 발표하지 않음');
 addNote('부록에는 재현성 검사를 모았습니다. 가상기업 마스터 32개, C01 문서 56개, 접근 규칙 20개와 189개 메타데이터 검사, RAG 워크스테이션 167개 오프라인 회귀, 데모와 로컬 통합 프로토콜 검사가 통과했습니다. 이 수는 단계별 기록이며 서로 겹칠 수 있어 하나의 총 테스트 수로 합산하지 않습니다.','project-docs/가상기업/v1/validation_report.json; project-docs/가상기업/v1/generated/C01/r1/README.md; project-docs/RAG파일럿/workstation-275/validation/tests.json; project-docs/데모개선 README','자동 검사와 모델 성능·운영 보안을 구분');
}

// 32 appendix ledger
{
 const s=p.slides.add();header(s,31,'APPENDIX B · 발표 수치 원장','본문 수치의 분모·정의·상태를 한 장에서 재확인');
 table(s,[['항목','값','분모·정의','상태'],['공고 행 / 최신 차수','137,745 / 124,522','4~6월 · 공고 차수 포함/최신','확정'],['첨부 / 사용 가능','285,252 / 246,797','어댑터 사용 가능 87%','확정'],['완전 공고','용역 28,852 · 물품 14,145 · 공사 8,082','공고문 + RFP/과업·규격서','확정'],['표본','51','4·5·6월 각 17','검수 완료'],['합성 원장','5사 · 45명 · 16프로젝트 · 111증빙','실제 기업 자료 아님','자동검사 완료'],['색인','223문서 · 3,275청크','L1 167/3002 · L2 34/159 · L3 22/114','로컬 색인'],['임베딩','7,195 window · 384차원','E5-small · 460/420 token','구축 완료'],['평가','300문항 · 5사×60','검색 코퍼스와 분리','구조 검증'],['생성','295답변 + 차단5','Qwen3-4B 로컬 GPU','정본 고정'],['사람 검수','25문항 · 88조정안 구절','최종 승인 전','pending'],['탐지 비교','885 슬롯','3모델 × 295답변','평가 진행 중']],54,151,1172,459,[235,300,432,205],{size:12});
 foot(s,'확정·검수 완료·구조 검증·pending·평가 진행 중을 같은 의미로 읽지 않음');
 addNote('이 장은 발표 수치 원장입니다. 각 값의 분모와 정의, 상태를 함께 적었습니다. 수집 확정값, 검수 완료, 로컬 색인, 구조 검증, 사람 승인 pending, 탐지 평가 진행 중을 서로 다른 상태로 읽어야 합니다. 질의응답에서 숫자의 의미를 확인할 때 사용합니다.','project-docs/데이터현황/3개월_통합현황.md; validation reports; index_manifest; final_summary','상태 정의를 유지');
}

// 33 appendix limits
{
 const s=p.slides.add();header(s,32,'APPENDIX C · 발표에서 넘지 않는 주장 경계','구현 사실과 성능 결론을 분리해야 결과가 재현 가능하다');
 const pairs=[['말할 수 있음','말하면 안 됨'],['51개 공고와 223문서의 연결 구조를 구축','전체 나라장터에 대한 검색 성능을 검증'],['295개 정본 답변과 생성 근거를 보존','RAG 정확도가 특정 비율이라고 주장'],['권한 정책으로 5건을 모델 호출 전에 차단','운영 인증·인가와 보안 감사를 완료'],['25문항 사람 의견을 접수하고 88구절 조정안 작성','25문항을 독립 gold 테스트로 사용'],['3모델 × 295답변 평가 구조를 준비','KLUE·XLM-R·BGE-M3 성능 우열 확정'],['저장 결과와 L1 로컬 질문 UI를 검증','L2·L3 자유 질문이 운영 DB와 연결']];
 table(s,pairs,54,158,1172,350,[586,586],{size:14,headerFill:C.navy});
 const calls=[['데이터','분모와 집계 기준 확인',C.blue],['모델','학습·개발·평가 분할 확인',C.teal],['사람','승인자·시점·대상 구절 기록',C.orange],['운영','인증·로그·실시간 모드 별도 검증',C.red]];calls.forEach(([h,b,c],i)=>node(s,h,b,54+i*293,536,270,72,c));
 foot(s,'미완료 결과는 자리와 평가 방법만 설계하고 “평가 진행 중”으로 표시');
 addNote('마지막 부록은 발표의 주장 경계입니다. 구축한 연결 구조와 정본 보존은 말할 수 있지만 전체 검색 성능이나 탐지 정확도를 만들어 말할 수는 없습니다. 파일럿 권한 정책과 운영 인증, 25문항 개발 검수와 독립 gold, 저장 결과 UI와 실시간 모드를 구분합니다. 이 경계를 지키는 것이 결과를 재현 가능하게 만듭니다.','project-docs/PPT_최종발표_제작_인수인계_프롬프트.md','검증되지 않은 성능·운영 완성 주장 금지');
}

if(p.slides.items.length!==33||notes.length!==33||facts.length!==33) throw new Error(`Expected 33 slides, got ${p.slides.items.length}/${notes.length}/${facts.length}`);
for(let i=0;i<33;i++)p.slides.items[i].speakerNotes.textFrame.setText(`${notes[i]}\n\n근거: ${facts[i].source}\n표현 제한: ${facts[i].limit}`);

const script=['# ASTRA 최종발표 내용 확장 초안 v2 · 발표 메모 초안','',`- 본문 30장 + 부록 3장`,'- 팀에서 발표 순서·문구·시간에 맞게 수정하기 위한 슬라이드별 핵심 설명 초안',''];
for(let i=0;i<33;i++){script.push(`## ${i+1}. ${slideTitles[i]}`,'',notes[i],'',`- 근거: ${facts[i].source}`,`- 표현 제한: ${facts[i].limit}`,'');}
await fs.writeFile(path.join(finalDir,'ASTRA_최종발표_내용확장_초안_v2_발표메모.md'),script.join('\n'),'utf8');
const verify=['# ASTRA 최종발표 내용 확장 초안 v2 · 사실 검증표','',`기준: origin/feature/sample-expansion-demo cb45470 + presentation/final-deck-v1 후속 개편`,'','| 슬라이드 | 제목 | 근거 | 표현 제한 |','|---:|---|---|---|'];
for(let i=0;i<33;i++)verify.push(`| ${i+1} | ${slideTitles[i]} | ${facts[i].source.replaceAll('|','/')} | ${facts[i].limit.replaceAll('|','/')} |`);
await fs.writeFile(path.join(finalDir,'ASTRA_최종발표_내용확장_초안_v2_사실검증표.md'),verify.join('\n')+'\n','utf8');

const candidate=path.join(build,'candidate-v2.pptx');
const finalPath=path.join(finalDir,'ASTRA_최종발표_내용확장_초안_v2.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const req={workspaceDir:repo,candidatePath:candidate,finalPath,pythonExecutable:runtimePython,integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','12','--require-native-table-slide','17','--require-native-table-slide','28'],explicitTotalSlideCount:33,requiredNativeTableOwnerSlides:[12,17,28],requiredNativeChartOwnerSlides:[6,9,13,23,25],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[F]},verifyArtifactToolImport:true,receiptPath:path.join(build,'ASTRA_최종발표_v2.validation.json')};
const result=await finalizePresentation(req);
console.log(JSON.stringify(result));
