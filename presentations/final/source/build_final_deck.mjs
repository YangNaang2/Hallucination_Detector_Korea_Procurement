import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const finalDir=path.resolve(here,'..');
const repo=path.resolve(finalDir,'../..');
const build=path.join(repo,'.presentation-build','final-deck-v1');
const skill=process.env.SKILL_DIR;
const modules=process.env.RUNTIME_NODE_MODULES;
const runtimePython=process.env.RUNTIME_PYTHON;
if(!skill||!modules||!runtimePython) throw new Error('Missing bundled runtime environment');

const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,makeNativeBulletParagraphs,applyPresentationChartFont}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
await fs.mkdir(build,{recursive:true});
await fs.mkdir(path.join(finalDir,'rendered'),{recursive:true});

const p=Presentation.create({slideSize:{width:1280,height:720}});
const F='Noto Sans CJK KR';
const C={bg:'#07111E',bg2:'#0C1B2A',ink:'#F4F8FB',muted:'#A8BDCC',teal:'#2DD4BF',blue:'#4D8DFF',coral:'#FF6B57',amber:'#F6B94A',green:'#64D6A1',panel:'#102638',panel2:'#173247',line:'#355267',white:'#FFFFFF',paper:'#F2F7FA',darkInk:'#102A43',darkMuted:'#526D82',red:'#FF6B6B'};
const chapters=['문제의 현장','해결책 공개','데이터 기반','RAG 엔진','환각 검증','검증과 시연'];
const slideChapter=[0,0,0,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5];
const notes=[];

function addText(s,content,x,y,w,h,size=24,color=C.ink,bold=false,opts={}){
  const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  a.text=content;
  a.text.style={typeface:F,fontSize:size,color,bold,autoFit:'none',verticalAlignment:opts.verticalAlignment||'top',horizontalAlignment:opts.align||'left',insets:{left:opts.pad??0,right:opts.pad??0,top:opts.pad??0,bottom:opts.pad??0}};
  return a;
}
function box(s,x,y,w,h,fill=C.panel,line=C.line,radius=false){
  return s.shapes.add({geometry:radius?'roundRect':'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:line,width:1.2}});
}
function line(s,x1,y1,x2,y2,color=C.line,width=2){
  return s.shapes.add({geometry:'line',position:{left:x1,top:y1,width:x2-x1,height:y2-y1},fill:'none',line:{fill:color,width}});
}
function circle(s,x,y,d,fill,lineColor=fill){return s.shapes.add({geometry:'ellipse',position:{left:x,top:y,width:d,height:d},fill,line:{fill:lineColor,width:1}});}
function bullets(s,items,x,y,w,h,size=22,color=C.ink,space=8){
  const a=addText(s,'',x,y,w,h,size,color);
  a.text=makeNativeBulletParagraphs(items,{marginLeftPoints:15,hangingPoints:8,spaceAfterPoints:space});
  a.text.style={typeface:F,fontSize:size,color,autoFit:'none',verticalAlignment:'top',insets:{left:0,right:0,top:0,bottom:0}};
  return a;
}
function pill(s,t,x,y,w,color=C.teal,txt=C.bg){box(s,x,y,w,30,color,color,true);addText(s,t,x,y+4,w,22,14,txt,true,{align:'center'});}
function header(s,i,title,subtitle=''){
  s.background.fill=C.bg;
  const ch=slideChapter[i];
  addText(s,`CHAPTER ${String(ch+1).padStart(2,'0')}  ${chapters[ch]}`,54,28,480,24,14,C.teal,true);
  addText(s,title,54,62,1168,52,36,C.ink,true);
  if(subtitle)addText(s,subtitle,56,116,1140,34,18,C.muted,false);
  line(s,54,156,1226,156,C.line,1);
  const start=54,gap=8,total=1172,seg=(total-gap*5)/6;
  for(let n=0;n<6;n++)box(s,start+n*(seg+gap),690,seg,5,n===ch?C.coral:C.line,n===ch?C.coral:C.line);
  addText(s,String(i+1).padStart(2,'0'),1191,28,35,24,14,C.muted,true,{align:'right'});
}
function foot(s,t){addText(s,t,56,655,1168,28,15,C.muted,false);}
function arrow(s,a,b,color=C.blue){return s.shapes.connect(a,b,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:color,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});}
function node(s,h,b,x,y,w,hgt,accent=C.blue){const n=box(s,x,y,w,hgt,C.panel,C.line,true);box(s,x,y,7,hgt,accent,accent);addText(s,h,x+22,y+18,w-40,35,24,C.ink,true);addText(s,b,x+22,y+62,w-42,hgt-78,18,C.muted);return n;}
function table(s,values,x,y,w,h,widths,opts={}){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
  t.borders.assign({fill:opts.border||C.line,width:.8,style:'solid'});
  const all=t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length});
  all.assign({fill:opts.fill||C.panel,textStyle:{typeface:F,fontSize:opts.size||18,color:opts.color||C.ink},margins:{left:10,right:10,top:8,bottom:8},anchor:'center'});
  for(let j=0;j<values[0].length;j++){const c=t.getCell(0,j);c.fill=opts.headerFill||'#18415A';c.text.style={typeface:F,fontSize:opts.size||18,bold:true,color:C.white};}
  return t;
}
function metric(s,num,label,x,y,w,color=C.teal){addText(s,num,x,y,w,60,46,color,true);addText(s,label,x,y+64,w,45,18,C.muted);}

// 1. Cover
{
 const s=p.slides.add();s.background.fill=C.bg;
 circle(s,910,-130,560,'#0C2F42','#0C2F42');circle(s,1010,10,360,'#103F4A','#103F4A');circle(s,-140,540,310,'#25192A','#25192A');
 addText(s,'ASTRA',64,52,260,42,26,C.teal,true);
 addText(s,'권한에 맞는 근거로 답하고\n의심 구절을 표시하는 조달 검토 시스템',64,168,920,164,50,C.ink,true);
 addText(s,'나라장터 공개 공고 · 합성 기업 자료 · 로컬 RAG · 구절 단위 환각 검증',68,365,900,42,23,C.muted);
 line(s,68,445,590,445,C.coral,5);
 addText(s,'ko-LettuceDetect / ASTRA  ·  B1조 최종발표',68,478,750,35,20,C.ink,true);
 addText(s,'2026.10.02',68,524,320,30,18,C.muted);
 addText(s,'PUBLIC L1',979,381,180,26,15,C.blue,true);addText(s,'SYNTHETIC L2',979,426,180,26,15,C.teal,true);addText(s,'SYNTHETIC L3',979,471,180,26,15,C.coral,true);
 [0,1,2].forEach(i=>{circle(s,930,383+i*45,16,[C.blue,C.teal,C.coral][i]);line(s,946,391+i*45,968,391+i*45,[C.blue,C.teal,C.coral][i],2);});
 notes.push(`오늘 소개할 ASTRA는 나라장터 공고를 대신 판단하는 자동 낙찰 시스템이 아닙니다. 입찰 담당자가 공개 공고와 회사 자료를 함께 검토할 때, 현재 권한으로 볼 수 있는 근거만 검색하고 로컬 모델의 답변에서 문서가 지지하지 않는 구절을 다시 확인하도록 돕는 시스템입니다. 발표에서는 문제, 데이터, 권한형 RAG, 환각 검증, 현재 검증 상태와 데모 순서로 설명하겠습니다.\n\n근거: project-docs/PPT_최종발표_제작_인수인계_프롬프트.md; project-docs/프로젝트_진행현황_팀공유_2026-09-11.md`);
}

// 2. Problem cases
{
 const s=p.slides.add();header(s,1,'입찰 검토는 문서 한 장을 읽는 일이 아니다','조건, 버전, 제출 방식이 서로 얽히면 같은 문장도 결론이 달라진다');
 const cases=[
  ['평가 기준의 불명확성','권익위는 향후 유사 공고에서\n적격심사 정보를 더 명확히 제공하도록 의견표명','원문 확인'],
  ['정정공고의 영향','업종 코드 1468 → 1469\n입찰 일정도 함께 정정된 공개 사례','버전 고정'],
  ['문서 간 충돌과 누락','51건 표본에서 일정, 실적 범위,\n공동수급 표현의 재확인 항목을 별도 기록','추가 확인']
 ];
 cases.forEach(([h,b,tag],i)=>{const x=54+i*402;box(s,x,202,370,280,C.panel,C.line,true);pill(s,tag,x+22,222,112,[C.blue,C.coral,C.amber][i],C.white);addText(s,h,x+22,276,326,44,27,C.ink,true);addText(s,b,x+22,345,326,95,20,C.muted);});
 addText(s,'외부 생성형 AI에 회사 내부 자료를 보내면 처리 경계를 통제하기 어렵고, 근거가 있어도 답변 오류는 남는다.',54,529,1172,45,24,C.ink,true);
 foot(s,'공식 사례와 51건 검수 기록에서 확인한 문제만 사용 · 자동 적격 판정이나 분쟁 해결을 주장하지 않음');
 notes.push(`첫 번째 문제는 평가 기준을 얼마나 구체적으로 제공했는가입니다. 권익위 공개 의결문에서는 낙찰자 선정 취소 요청과 별개로, 향후 유사 공고에서 평가 방법을 더 명확하게 제공하라는 의견이 제시됐습니다. 두 번째는 정정공고입니다. 실제 공개 공고에서 참가 업종 코드와 일정이 함께 바뀌었습니다. 세 번째는 우리 51건 원문 대조에서 확인한 문서 간 표현 차이입니다. 일정, 실적 범위, 공동수급 조건은 한 파일만 읽고 확정하기 어려웠습니다. 여기에 회사 내부 자료를 외부 모델로 전송할 때의 보안 문제와, 근거를 줘도 답변이 틀릴 수 있다는 문제가 더해집니다.\n\n근거: presentations/week3/3주차_진행보고_발표원고.md; project-docs/표본_정보시스템/검수/51건_통합_검토내역.md; presentations/week3/source/acrc_order_excerpt.png`);
}

// 3. Existing approach limitations
{
 const s=p.slides.add();header(s,2,'검색, 요약, 보안이 따로 움직이면 검토가 끝나지 않는다');
 const a=node(s,'키워드 검색','정확한 코드와 숫자는 찾지만\n표현이 다른 문맥을 놓칠 수 있음',56,227,330,210,C.blue);
 const b=node(s,'LLM 요약','읽는 시간은 줄이지만\n근거 없는 확정과 조건 누락이 남음',475,227,330,210,C.coral);
 const c=node(s,'접근 통제','자료는 보호하지만\n답변의 문서 지지 여부까지 검사하지 않음',894,227,330,210,C.teal);
 line(s,386,332,475,332,C.muted,2);line(s,805,332,894,332,C.muted,2);
 box(s,216,495,848,92,'#132E3C','#24526A',true);addText(s,'담당자는 답을 받은 뒤에도 권한, 최신 버전, 원문 근거를 다시 확인해야 한다',244,520,792,50,27,C.ink,true,{align:'center'});
 foot(s,'단순 키워드, 범용 LLM, 문서 권한을 각각 비판하는 비교 수치는 만들지 않음');
 notes.push(`기존 도구 각각은 필요한 기능을 가지고 있습니다. 키워드 검색은 공고번호와 업종 코드 같은 정확한 문자열에 강합니다. 생성 모델은 긴 문서를 빠르게 요약합니다. 접근 통제는 자료의 열람 범위를 제한합니다. 하지만 세 기능이 분리되면 담당자는 답변을 받은 뒤에 다시 최신 공고인지, 회사 권한에 맞는 자료인지, 문서가 실제로 그 주장을 지지하는지 확인해야 합니다. ASTRA는 이 확인 순서를 하나의 요청 안에 묶는 데 초점을 맞췄습니다. 이 슬라이드는 성능 비교가 아니라 업무 흐름의 단절을 설명합니다.\n\n근거: procurement-pipeline/rag_pilot.py; procurement-pipeline/security_schema.py; project-docs/나라장터_문제정의_1차리서치_팀원용.md`);
}

// 4. Goal
{
 const s=p.slides.add();header(s,3,'ASTRA의 목표','질문부터 근거 대조까지 같은 권한과 같은 문서 버전을 유지한다');
 const ns=[
  node(s,'권한 확인','회사, tenant, 역할,\n시나리오와 기준일',54,245,248,210,C.teal),
  node(s,'근거 검색','허용 문서 안에서\n키워드와 벡터 결합',365,245,248,210,C.blue),
  node(s,'로컬 생성','질문과 선택 근거로\n답변과 인용 생성',676,245,248,210,C.amber),
  node(s,'답변 검증','규칙 검사와 토큰 분류로\n의심 구절 표시',987,245,239,210,C.coral)
 ];
 for(let i=0;i<3;i++)arrow(s,ns[i],ns[i+1],C.muted);
 addText(s,'결과는 “참여 가능” 한 줄이 아니라 근거, 조건 상태, 자료부족, 의심 구절을 함께 보여준다.',76,520,1128,50,27,C.ink,true,{align:'center'});
 foot(s,'개별 조건 검토를 전체 입찰 적격 판정으로 확대하지 않음');
 notes.push(`프로젝트의 목표는 질문을 받는 순간부터 검증 결과를 보여줄 때까지 같은 권한과 같은 문서 버전을 유지하는 것입니다. 먼저 신뢰된 세션의 회사, tenant, 역할, 시나리오와 기준일로 검색 후보를 제한합니다. 그 안에서 키워드 검색과 벡터 검색을 결합합니다. 선택한 근거만 로컬 생성 모델에 보내고, 답변이 나오면 금액과 기간 같은 규칙 검사와 학습된 토큰 분류 탐지기를 별도로 적용합니다. 결과 화면은 단순한 가능 또는 불가능 대신, 근거와 조건 상태, 자료 부족, 의심 구절을 함께 제시하도록 설계했습니다.\n\n근거: procurement-pipeline/rag_pilot.py; demo-ui/spatial-poc/live-design/Live_RAG_전환설계.md`);
}

// 5. Overall pipeline — editable reconstruction of the supplied storyboard SVG
{
 const s=p.slides.add();header(s,4,'ASTRA 전체 파이프라인','Input, Process, Output을 먼저 보고 이후 슬라이드에서 구간별로 확대한다');
 addText(s,'구축 단계',54,188,120,28,18,C.blue,true);addText(s,'운영 단계',54,401,120,28,18,C.teal,true);
 const buildNodes=[
  node(s,'INPUT','공개 공고·첨부\n합성 기업 L2·L3\n평가용 질문',54,222,276,152,C.blue),
  node(s,'PROCESS','파싱·분류·청크화\n보안 등급과 메타데이터\n검색 색인 구축',501,222,276,152,C.teal),
  node(s,'OUTPUT','223개 문서 · 3,275개 청크\n평가 Q-A-R 300건\n재현 가능한 manifest',948,222,276,152,C.coral)
 ];
 arrow(s,buildNodes[0],buildNodes[1],C.muted);arrow(s,buildNodes[1],buildNodes[2],C.muted);
 const runNodes=[
  node(s,'INPUT','질문 · 선택 공고\n회사 · 역할 · 시나리오',54,435,276,152,C.blue),
  node(s,'PROCESS','권한 필터 → 하이브리드 검색\n로컬 생성 → 규칙·모델 검사',501,435,276,152,C.teal),
  node(s,'OUTPUT','답변 · 인용 · 근거\n조건 상태 · 의심 구절',948,435,276,152,C.coral)
 ];
 arrow(s,runNodes[0],runNodes[1],C.muted);arrow(s,runNodes[1],runNodes[2],C.muted);
 foot(s,'공개 공고와 합성 기업 자료 → 권한형 검색·로컬 생성·검증 → 근거와 의심 구절 표시');
 notes.push(`전체 구조는 입력, 처리, 출력의 세 구간으로 나뉩니다. 입력에는 나라장터 공개 공고와 합성 기업 자료가 들어갑니다. 처리 구간에서는 문서를 구조화하고 권한으로 후보를 줄인 뒤, 하이브리드 검색과 로컬 답변 생성을 수행합니다. 답변은 바로 끝나지 않고 규칙 검사와 환각 탐지 모델을 거칩니다. 출력은 답변, 출처, 관련 근거, 조건 상태와 의심 구절입니다. 이후 데이터 슬라이드에서는 입력을, RAG 슬라이드에서는 검색과 생성을, 환각 슬라이드에서는 답변 검증을 확대해 설명하겠습니다.\n\n시각자료: output/visuals/ASTRA_Input_Process_Output_Pipeline.svg`);
}

// 6. User query pipeline — editable reconstruction of the supplied pipeline SVG
{
 const s=p.slides.add();header(s,5,'사용자 질의 파이프라인','질문을 먼저 받고, 권한 밖 자료는 검색 후보가 되기 전에 제외한다');
 const steps=[
  ['01','질문 입력','공고·회사 선택\n자연어 질문',C.blue],
  ['02','세션 확인','tenant · 회사\n역할 · 시나리오',C.teal],
  ['03','권한 필터','허용된 문서만\n검색 후보로 유지',C.coral],
  ['04','근거 검색','키워드 + 벡터\nRRF 순위 결합',C.blue],
  ['05','로컬 생성','선택 근거로\n답변·인용 생성',C.amber],
  ['06','검증·표시','규칙 + 탐지기\n근거·의심 구절',C.teal]
 ];
 const cards=[];
 steps.forEach(([num,title,desc,color],i)=>{
  const row=i<3?0:1, col=i%3, x=54+col*408, y=205+row*207;
  const card=box(s,x,y,354,159,C.panel,C.line,true);box(s,x,y,64,159,color,color,true);
  addText(s,num,x+10,y+58,44,42,21,C.white,true,{align:'center'});
  addText(s,title,x+89,y+31,235,38,24,C.ink,true);
  addText(s,desc,x+89,y+80,235,58,18,C.muted,false);
  cards.push(card);
 });
 arrow(s,cards[0],cards[1],C.muted);arrow(s,cards[1],cards[2],C.muted);
 arrow(s,cards[3],cards[4],C.muted);arrow(s,cards[4],cards[5],C.muted);
 line(s,1201,364,1201,392,C.muted,2);line(s,1131,392,1201,392,C.muted,2);
 addText(s,'검색 범위 결정',456,573,368,30,18,C.teal,true,{align:'center'});
 foot(s,'브라우저의 역할 이름이 아니라 신뢰된 서버 세션이 검색 범위를 결정');
 notes.push(`사용자 흐름은 여섯 단계입니다. 공고와 회사를 선택하고 질문을 입력합니다. 서버는 세션의 회사, tenant, 역할과 시나리오를 확인합니다. 그 결과 허용된 문서만 남긴 뒤 하이브리드 검색을 수행합니다. 선택된 근거와 질문은 로컬 모델로 전달됩니다. 생성된 답변은 규칙 검사와 환각 탐지를 거치고, 화면에는 답변과 인용, 근거 문서, 의심 구절이 나타납니다. 여기서 중요한 점은 브라우저의 역할 이름을 바꾸는 것이 권한 변경이 아니라는 점입니다. 파일럿 정책과 실제 운영 인증 체계도 구분해서 설명합니다.\n\n시각자료: output/visuals/ASTRA_User_Query_Pipeline.svg; 근거: procurement-pipeline/rag_pilot.py`);
}

// 7. Collection and sample
{
 const s=p.slides.add();header(s,6,'4~6월 수집에서 51건 검수 표본까지','원본 보존, 파싱 결과, 활용 가능 여부를 분리해 기록했다');
 metric(s,'137,745','공고 행 · 차수 포함',54,189,250,C.blue);metric(s,'246,797','사용 가능 첨부 · 전체 285,252개',320,189,285,C.teal);metric(s,'51','정보시스템 구축·운영 표본',618,189,250,C.coral);
 box(s,54,326,742,288,C.paper,C.paper,true);
 const chart=s.charts.add('bar',{position:{left:82,top:354,width:685,height:228},categories:['용역','물품','공사'],series:[{name:'완전 공고',values:[28852,14145,8082],fill:C.blue}],barOptions:{direction:'column',grouping:'clustered'},hasLegend:false,dataLabels:{showValue:true,position:'outEnd'}});
 applyPresentationChartFont(chart,{fontFamily:F});
 addText(s,'업무구분별 완전 공고 수',76,331,330,28,18,C.darkInk,true);
 node(s,'수집·보존','OpenAPI 조회\n공고·첨부·해시',840,340,180,212,C.blue);node(s,'파싱·변환','CPU 파싱\n선택적 GPU OCR',1042,340,182,212,C.teal);
 addText(s,'4월 17건 · 5월 17건 · 6월 17건',850,570,360,30,20,C.ink,true,{align:'center'});
 foot(s,'완전 공고 = 공고문 + 제안요청서 또는 과업·규격서 · 기준 2026.09.11');
 notes.push(`수집기는 나라장터 OpenAPI에서 4월, 5월, 6월 공고와 첨부를 가져옵니다. 공고 행은 차수를 포함해 137,745건입니다. 첨부 285,252개 가운데 파이프라인에서 사용할 수 있다고 판정한 문서는 246,797개입니다. 그래프는 공고문과 제안요청서 또는 과업·규격서가 함께 있는 완전 공고의 업무별 수입니다. 이 중 정보시스템 구축과 운영 분야에서 월별 17건씩, 총 51건을 표본으로 선정해 조건을 대조했습니다. 모든 첨부가 정상 파싱됐다는 뜻은 아니며 읽을 수 없는 파일은 별도로 남겼습니다.\n\n근거: project-docs/데이터현황/3개월_통합현황.md; project-docs/표본_정보시스템/검수/재확인_원문대조_결과.md; procurement-pipeline/collector/g2b_rag_pipeline/README.md`);
}

// 8. L1 L2 L3
{
 const s=p.slides.add();header(s,7,'L1·L2·L3는 자료의 성격을 구분한다','공개 공고에서 출발해 비교용 합성 기업 자료를 만든다');
 const bands=[
  ['L1  공개','나라장터 공고·RFP·과업지시서','예산 10억 원',C.blue],
  ['L2  합성 내부','가상 기업의 실적·인력·인증','회사 실적 7억 원',C.teal],
  ['L3  합성 민감','원가·마진·투찰 검토','내부 원가 6.4억 원',C.coral]
 ];
 bands.forEach(([l,d,e,color],i)=>{const y=205+i*130;box(s,54,y,1170,102,C.panel,C.line,true);box(s,54,y,160,102,color,color,true);addText(s,l,66,y+31,136,40,24,C.white,true,{align:'center'});addText(s,d,248,y+21,480,35,25,C.ink,true);addText(s,e,788,y+22,400,34,25,color,true,{align:'right'});addText(s,i===0?'실제 공개 자료':'실제 기업 자료가 아닌 합성 설정',248,y+62,650,28,17,C.muted);});
 addText(s,'보안등급은 문서의 성격, 권한 필터는 누가 어떤 문서를 검색할 수 있는지 결정하는 정책이다.',86,606,1108,34,22,C.ink,true,{align:'center'});
 foot(s,'가상 기업 5곳 · L2/L3는 실제 업체의 기밀자료가 아님');
 notes.push(`L1은 실제 나라장터 공개 공고와 공개 첨부입니다. L2는 51건의 조건을 비교하기 위해 만든 가상 기업 5곳의 실적, 인력, 인증 자료입니다. L3는 같은 가상 기업의 원가와 마진, 투찰 검토 자료입니다. 같은 가격이라는 단어도 L1에서는 공개 예산, L2에서는 회사 실적액, L3에서는 내부 원가처럼 의미와 공개 범위가 다릅니다. L2와 L3는 실제 기업에서 받은 기밀자료가 아닙니다. 또한 문서에 L1, L2, L3를 붙이는 분류와 사용자의 접근 권한을 검사하는 과정은 별개입니다.\n\n근거: project-docs/가상기업/v1/README.md; project-docs/RAG파일럿/v1/index_manifest.json`);
}

// 9. Evaluation data
{
 const s=p.slides.add();header(s,8,'300개 Q-A-R은 검색 코퍼스가 아니라 평가 기준이다');
 const n1=node(s,'51건 요건 추출','참가자격, 실적, 인력,\n인증, 일정, 금액, 공동수급',54,227,300,220,C.blue);
 const n2=node(s,'가상 기업 5곳','강점과 제약이 다른\n합성 회사 자료',490,227,300,220,C.teal);
 const n3=node(s,'평가 300건','회사별 60건\n질문 + 기대답 + 근거',926,227,300,220,C.coral);
 arrow(s,n1,n2,C.muted);arrow(s,n2,n3,C.muted);
 addText(s,'RAG 검색 DB',103,500,210,30,18,C.blue,true,{align:'center'});addText(s,'≠',376,493,42,42,30,C.coral,true,{align:'center'});addText(s,'평가 질문·기대답',453,500,250,30,18,C.coral,true,{align:'center'});
 addText(s,'생성 답변 295건',798,493,190,35,24,C.ink,true);addText(s,'정상 접근 차단 5건',1008,493,218,35,24,C.teal,true);
 addText(s,'25문항은 팀원 검수 접수 완료, 최종 사람 승인과 학습 내보내기는 pending',252,577,778,32,21,C.amber,true,{align:'center'});
 foot(s,'기대답과 라벨은 생성 입력에서 제거 · 사람 승인 pending');
 notes.push(`평가 데이터는 요건추출시트에서 출발합니다. 51건의 참가자격, 실적, 인력, 인증, 일정, 금액과 공동수급 조건을 정리하고, 강점과 제약이 다른 합성 기업 5곳을 설계했습니다. 각 회사당 60문항으로 총 300개의 질문, 기대답, 근거를 만들었습니다. 이 300개는 검색 코퍼스가 아니라 검색과 생성, 환각 탐지를 평가하기 위한 기준입니다. 워크스테이션 실행에는 실제 생성 답변 295건과 권한 때문에 모델을 호출하지 않은 정상 차단 5건이 있습니다. 25문항은 팀원 검수가 접수됐지만 최종 사람 승인은 아직 남아 있습니다.\n\n근거: project-docs/평가데이터/v2/validation/report.json; project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json; project-docs/환각라벨링/pilot-25-human-review-v1/README.md`);
}

// 10. Access filter table
{
 const s=p.slides.add();header(s,9,'권한 필터는 검색 전에 문서 후보를 제한한다','역할, 회사, tenant, 시나리오를 서버가 함께 검사한다');
 table(s,[['역할','L1 공개','L2 회사','L3 민감','파일럿 접근 범위'],['viewer','허용','차단','차단','공개 공고'],['bid_analyst','허용','허용','차단','실적·인력·인증'],['cost_analyst','허용','허용','허용','원가 검토'],['bid_approver','허용','허용','허용','승인 검토']],54,213,760,322,[180,120,120,120,220],{size:18});
 node(s,'세션에서 확인','authenticated\nmembership_active\ntenant · company · role',855,213,369,160,C.teal);
 node(s,'검색 전에 강제','허용된 문서의 벡터만 점수 계산\n문서 보기·다운로드도 같은 정책',855,397,369,138,C.blue);
 addText(s,'파일럿 정책 구현  /  운영 인증·인가 시스템은 추가 구현 필요',854,561,370,45,18,C.amber,true,{align:'center'});
 foot(s,'브라우저에서 역할 이름을 바꿔도 접근 권한이 확장되지 않는 구조');
 notes.push(`파일럿의 역할 정책은 네 가지입니다. viewer는 공개 L1만 봅니다. bid analyst는 해당 회사의 L2까지, cost analyst와 bid approver는 허용된 시나리오의 L3까지 접근할 수 있습니다. 역할만 맞으면 끝나는 것이 아니라 로그인 상태, 멤버십, tenant, 회사, 시나리오와 기준일을 함께 확인합니다. 중요한 구현 포인트는 전역 검색을 끝낸 뒤 결과를 숨기는 방식이 아니라, 허용된 문서만 남긴 뒤 키워드와 벡터 점수를 계산한다는 점입니다. 다만 이 표는 파일럿 정책이며 실제 운영용 인증과 인가 체계는 후속 구현 범위입니다.\n\n근거: procurement-pipeline/rag_pilot.py ROLE_LEVELS; project-docs/평가데이터/v2/retrieval_manifest.json`);
}

// 11. Hybrid retrieval
{
 const s=p.slides.add();header(s,10,'정확한 용어와 의미가 비슷한 표현을 함께 찾는다');
 const k=node(s,'키워드 검색','한국어 2글자 부분어와\n영문·숫자 단어의 BM25 형태 점수\n코드·금액·날짜에 유리',54,222,342,250,C.blue);
 const v=node(s,'벡터 검색','multilingual-e5-small\n문장 표현이 달라도 의미가 가까운\n청크 후보를 찾음',470,222,342,250,C.teal);
 const rr=node(s,'순위 결합','각 검색 순위를 RRF(k=60)로 결합\n상위 부모 청크 최대 6개 선정\n생성에는 우선 최대 4개 사용',886,222,340,250,C.coral);
 arrow(s,k,v,C.muted);arrow(s,v,rr,C.muted);
 box(s,169,514,942,78,'#132E3C','#24526A',true);addText(s,'권한 필터 → 키워드 순위 + 벡터 순위 → RRF 결합 → 상위 근거',190,535,900,40,27,C.ink,true,{align:'center'});
 foot(s,'현재 파일럿은 권한형 하이브리드 RAG · 별도 그래프 DB 기반 GraphRAG로 표현하지 않음');
 notes.push(`검색은 두 방식을 결합합니다. 키워드 쪽은 한국어 두 글자 부분어와 영문, 숫자 단어를 이용한 BM25 형태의 점수를 사용합니다. 공고번호, 업종 코드, 금액과 날짜 같은 정확한 표현에 유리합니다. 벡터 쪽은 multilingual E5 small로 의미가 비슷한 문맥을 찾습니다. 두 결과는 RRF의 k 60 설정으로 순위를 결합하고, 기본 top k는 6입니다. 생성에는 문맥 예산을 고려해 상위 부모 청크를 우선 최대 4개 사용합니다. 이 구조는 하이브리드 RAG이며, 별도 그래프 데이터베이스로 다단계 관계 추론을 완성한 GraphRAG라고 부르지 않습니다.\n\n근거: project-docs/RAG파일럿/v1/README.md; procurement-pipeline/rag_pilot.py; procurement-pipeline/rag_pilot_embedding.py`);
}

// 12. Grounded generation
{
 const s=p.slides.add();header(s,11,'생성 모델에는 실제 선택 근거만 전달한다','평가 정답과 금지 주장 목록은 런타임 입력에서 제거한다');
 box(s,54,205,515,364,C.panel,C.line,true);addText(s,'로컬 LLM 입력',80,229,460,36,27,C.teal,true);
 const input=['시스템 규칙','사용자 질문','[1] 파일명 + 근거 원문','[2] 파일명 + 근거 원문','문서 ID·버전·offset은 감사 기록'];
 input.forEach((t,i)=>{circle(s,84,291+i*51,24,i<2?C.blue:C.teal);addText(s,String(i+1),84,294+i*51,24,17,13,C.bg,true,{align:'center'});addText(s,t,122,289+i*51,410,28,19,C.ink,i<2);});
 box(s,611,205,613,364,C.panel,C.line,true);addText(s,'저장된 실행 결과',638,229,540,36,27,C.coral,true);
 metric(s,'295','Qwen3-4B Q4_K_M 생성 답변',640,293,270,C.coral);metric(s,'5','LLM 미호출 정상 차단',933,293,260,C.teal);
 addText(s,'근거 번호가 유효해도 주장을 지지한다는 보장은 없음',640,431,530,28,19,C.amber,true);
 addText(s,'출력 잘림 4건 · 잘못된 인용번호 1건을 그대로 보존',640,475,530,28,19,C.muted);
 foot(s,'로컬 GPU 생성 · 외부 추론·유료 API 미사용 · 사람 승인 pending');
 notes.push(`생성 입력에는 시스템 규칙, 사용자 질문, 그리고 검색에서 선택한 실제 근거가 번호와 파일명과 함께 들어갑니다. 문서 ID, 버전, 원문 해시와 문자 위치는 감사 기록에 남깁니다. 평가용 기대답과 금지 주장, 환각 라벨은 런타임 입력에서 차단합니다. 최종 워크스테이션 기록은 Qwen3 4B GGUF Q4_K_M 모델의 생성 답변 295건과, 모델을 호출하지 않은 정상 권한 차단 5건입니다. 출력 잘림 4건과 잘못된 인용번호 1건도 결과를 고쳐 쓰지 않고 남겼습니다. 인용번호가 형식상 맞아도 주장을 실제로 지지하는지는 별도로 검토해야 합니다.\n\n근거: project-docs/RAG파일럿/workstation-275/README.md; project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json`);
}

// 13. Detector structure
{
 const s=p.slides.add();header(s,12,'환각 탐지는 답변과 실제 생성 근거를 직접 비교한다','문장 전체 O/X 대신 의심 구절의 Unicode 문자 위치를 반환한다');
 const ns=[
  node(s,'생성 근거 + 답변','당시 프롬프트에 들어간 근거\n정본 답변 문자열',54,230,245,224,C.blue),
  node(s,'윈도우·토큰 정렬','긴 문맥을 나누고\n답변 토큰 offset 유지',364,230,245,224,C.teal),
  node(s,'토큰 분류','KLUE · XLM-R · BGE-M3\n근거 없음 / 모순 후보',674,230,245,224,C.amber),
  node(s,'문자 구절 표시','토큰을 Unicode [start,end)로\n되돌려 UI 형광펜 표시',984,230,242,224,C.coral)
 ];
 for(let i=0;i<3;i++)arrow(s,ns[i],ns[i+1],C.muted);
 box(s,170,505,940,84,'#132E3C','#24526A',true);addText(s,'규칙 검증: 금액 · VAT · 날짜 · 자격 · FTE     /     학습 탐지: 문서가 지지하지 않는 구절',196,531,888,35,22,C.ink,true,{align:'center'});
 foot(s,'검색 임베딩 모델과 환각 탐지용 체크포인트를 구분');
 notes.push(`탐지기는 세상의 사실을 직접 판정하는 모델이 아닙니다. 당시 답변 생성에 실제로 사용한 근거와 정본 답변을 함께 입력하고, 문서가 답변 토큰을 지지하는지 분류합니다. 긴 답변은 윈도우로 나누되 답변 토큰의 위치를 유지하고, 마지막에는 Unicode 문자 위치로 되돌려 UI에서 형광펜으로 표시합니다. KLUE, XLM-R, BGE-M3는 환각 탐지 후보입니다. 별도로 금액, VAT, 날짜, 자격, FTE처럼 명시적인 항목은 규칙 검사로 대조합니다. 검색용 E5 임베딩과 탐지용 체크포인트도 서로 다른 구성요소입니다.\n\n근거: project-docs/환각라벨링/detector-300-workstation-v1/WORKSTATION_PROMPT.md; demo-ui/spatial-poc/detector_bridge.py`);
}

// 14. Model comparison pending
{
 const s=p.slides.add();header(s,13,'나라장터 도메인 모델 비교는 평가 진행 중','체크포인트 존재와 검증된 성능을 구분한다');
 table(s,[['후보','입력 길이 설계','평가 상태','발표 가능한 결론'],['KLUE','512 기반 윈도우','평가 진행 중','성능 우열 미확정'],['XLM-R','512 기반 윈도우','평가 진행 중','성능 우열 미확정'],['BGE-M3','장문 체크포인트 후보','평가 진행 중','성능 우열 미확정']],54,205,1172,268,[210,250,250,462],{size:19});
 box(s,54,507,1172,103,'#132E3C','#24526A',true);addText(s,'보고 예정  데이터 범위 · 사람 정답지 상태 · 기준일 · threshold · 잘림 처리 · Precision · Recall · Span F1',80,532,1118,44,22,C.ink,true,{align:'center'});
 pill(s,'평가 진행 중',1038,118,170,C.coral,C.white);
 foot(s,'기준 브랜치에는 295답변 × 3모델의 완료 결과가 없음 · 검증되지 않은 수치 미사용');
 notes.push(`세 후보 모델의 체크포인트와 어댑터는 준비되어 있지만, 기준 브랜치에는 나라장터 295답변에 대한 세 모델의 완료 평가 결과가 없습니다. 따라서 이 슬라이드에서는 모델 크기나 기존 다른 도메인의 점수로 우열을 주장하지 않습니다. 최종 비교에서는 데이터 범위, 사람 정답지 승인 상태, 평가 기준일, 임계값, 긴 답변 잘림 처리, Precision, Recall과 Span F1을 함께 보고해야 합니다. 결과 파일이 고정되기 전까지는 평가 진행 중으로 표시합니다. 체크포인트가 있다는 사실과 운영 성능이 검증됐다는 주장은 다릅니다.\n\n근거: project-docs/환각라벨링/detector-300-workstation-v1/README.md; WORKSTATION_PROMPT.md`);
}

// 15. Error cases
{
 const s=p.slides.add();header(s,14,'오류는 결론, 근거, 인용 위치에서 각각 발생한다','25문항 통합 조정안의 대표 사례 · 최종 사람 승인 pending');
 const rows=[
  ['모순','“인천을 제외해도 된다”','원문은 서울·경기(인천 포함)','CONTRADICTION'],
  ['근거 없음','“기존 배치의 잔여 FTE가 0.0”','다른 인력의 값을 목표 인력에 재사용','UNSUPPORTED'],
  ['인용 오류','답변의 “[3]”','실제 프롬프트 인용은 [1], [2]뿐','CITATION_ERROR']
 ];
 rows.forEach(([kind,quote,reason,label],i)=>{const y=202+i*132;box(s,54,y,1172,105,C.panel,C.line,true);pill(s,kind,72,y+18,112,[C.coral,C.amber,C.blue][i],C.white);addText(s,quote,212,y+17,380,34,23,C.ink,true);addText(s,reason,610,y+17,430,55,19,C.muted);addText(s,label,1026,y+62,170,23,14,[C.coral,C.amber,C.blue][i],true,{align:'right'});});
 addText(s,'모델 예측 비교',54,611,190,26,17,C.muted,true);addText(s,'평가 진행 중',244,609,180,29,20,C.coral,true);
 addText(s,'출력 잘림 4건과 잘못된 인용번호 1건은 생성 품질 이슈로 별도 추적',560,609,666,29,18,C.amber,true,{align:'right'});
 foot(s,'조정안 88구절 중 채택 제안 70 · 보류 16 · 품질 메모 2 · approved_spans=null');
 notes.push(`사람 검수 패키지에서 대표 오류를 세 가지로 나눴습니다. 첫째, 원문은 서울과 경기, 인천 포함이라고 했는데 답변은 인천을 제외해도 된다고 결론 낸 모순입니다. 둘째, 다른 인력 레코드의 0.0 FTE 값을 목표 인력의 잔여값으로 옮겨 쓴 근거 없는 주장입니다. 셋째, 실제 프롬프트에는 근거 1과 2만 있는데 답변이 근거 3을 인용한 경우입니다. 이 구절들은 통합 조정안이며 최종 사람 승인은 아직 pending입니다. 모델 예측과의 비교도 평가 진행 중입니다. 생성 단계의 출력 잘림과 잘못된 인용번호는 별도 품질 문제로 추적합니다.\n\n근거: project-docs/환각라벨링/pilot-25-human-review-v1/구절조정목록.tsv; validation_report.json; project-docs/RAG파일럿/workstation-275/README.md`);
}

// 16. Integrated evaluation
{
 const s=p.slides.add();header(s,15,'통합 평가는 검색, 생성, 탐지를 따로 보고한다');
 table(s,[['평가 축','현재 확인 범위','상태','다음 검증'],['검색','223문서 · 3,275청크 색인','구조·해시 확인','검색 품질 지표'],['생성','295답변 · 정상 차단 5건','실행 완료','사람 승인 확대'],['사람 라벨','25문항 제출 검수','최종 승인 pending','조정안 확정'],['환각 탐지','3모델 × 295답변 = 885슬롯','평가 진행 중','P/R/Span F1']],54,202,1172,340,[205,290,260,417],{size:18});
 box(s,171,580,938,58,'#132E3C','#24526A',true);addText(s,'자동 검사 통과 ≠ 사람 승인 완료     탐지 구절 0개 ≠ 답변 정확',192,596,896,30,22,C.ink,true,{align:'center'});
 foot(s,'검색·생성·탐지 점수를 하나의 종합 정확도로 합치지 않음');
 notes.push(`통합 평가에서는 검색, 생성, 사람 라벨과 환각 탐지를 하나의 숫자로 합치지 않습니다. 현재 색인은 223문서와 3,275청크의 구조와 해시가 확인됐습니다. 생성은 295답변과 정상 권한 차단 5건이 완료됐습니다. 사람 라벨은 25문항의 제출 검수가 접수됐지만 최종 승인 단계가 남았습니다. 세 탐지기 비교는 295답변씩 총 885개 추론 슬롯으로 계획되어 있으며 기준 브랜치에서는 평가 진행 중입니다. 자동 구조 검사를 통과했다는 사실을 의미적 정답 승인으로 바꾸지 않고, 탐지 구절이 없다는 결과도 답변 정확성으로 해석하지 않습니다.\n\n근거: project-docs/RAG파일럿/v1/index_manifest.json; workstation-275/evaluation/final_summary.json; project-docs/환각라벨링/detector-300-workstation-v1/README.md`);
}

// 17. Demo
{
 const s=p.slides.add();header(s,16,'라이브 데모는 실행 모드를 먼저 밝힌다','공고 선택부터 답변·근거·의심 구절 확인까지');
 const img=await fs.readFile(path.join(repo,'presentations/week3/source/astra_building.png'));
 s.images.add({blob:new Uint8Array(img),contentType:'image/jpeg',alt:'ASTRA 공간형 시연 UI 목업 화면',fit:'cover',position:{left:54,top:190,width:735,height:414}});
 box(s,54,190,735,414,'none',C.line,true);pill(s,'기존 공간 UI 목업',74,208,174,C.coral,C.white);
 const steps=[['1','지도에서 공고 선택'],['2','저장 예시 또는 자유 질문'],['3','답변·출처·근거 경로 확인'],['4','환각 의심 구절 형광펜 확인']];
 steps.forEach(([n,t],i)=>{circle(s,838,203+i*83,34,[C.blue,C.teal,C.amber,C.coral][i]);addText(s,n,838,209+i*83,34,20,15,C.bg,true,{align:'center'});addText(s,t,890,206+i*83,315,40,20,C.ink,true);});
 box(s,827,542,399,62,'#132E3C','#24526A',true);addText(s,'저장 결과 재생 · L1 테스트 · 실제 생성 모드 구분',844,557,365,35,18,C.amber,true,{align:'center'});
 foot(s,'로그인·역할 선택 UI는 시연용 목업 · 실제 운영 인증으로 설명하지 않음');
 notes.push(`데모에서는 먼저 실행 모드를 말하겠습니다. 저장 결과 재생인지, L1 테스트 서버인지, 실제 생성 모델 모드인지 구분합니다. 지도에서 공고를 선택하고 질문을 실행한 뒤, 답변과 출처, 실제 생성에 사용한 근거 경로를 확인합니다. 탐지기가 연결된 경우에는 의심 구절을 형광펜으로 보여줍니다. 화면에 그래프가 있어도 완성형 GraphRAG라고 설명하지 않습니다. 또한 기존 공간형 UI의 로그인과 역할 선택은 시연용 목업입니다. 실제 운영 인증과 L2·L3 자유 질문은 후속 연결 범위입니다.\n\n시각자료: presentations/week3/source/astra_building.png; 근거: demo-ui/spatial-poc/dist/rag-observatory.js; L1_SERVER.md`);
}

// 18. Outcome and limits
{
 const s=p.slides.add();header(s,17,'구현 자산은 남았고, 성능 검증은 계속된다');
 const cols=[
  ['구현 완료',['4~6월 수집·파싱·변환 파이프라인','51건 표본과 합성 기업 5곳','223문서·3,275청크 파일럿 색인','300문항과 295 생성 답변'],C.teal],
  ['현재 한계',['탐지 3종 비교 결과 미완료','25문항 최종 사람 승인 pending','운영 인증·인가 미연결','L2·L3 자유 질문과 Live DB 미연결'],C.coral],
  ['다음 단계',['전체 295답변 탐지 평가','사람 승인 라벨과 오류 분석','운영 인증과 UI 실연결','데모 모드와 실시간 모드 분리 검증'],C.blue]
 ];
 cols.forEach(([h,items,color],i)=>{const x=54+i*402;box(s,x,202,370,360,C.panel,C.line,true);box(s,x,202,370,8,color,color);addText(s,h,x+22,226,326,38,28,color,true);bullets(s,items,x+22,295,326,230,20,C.ink,10);});
 addText(s,'AI가 대신 확정하는 시스템보다, 사람이 근거를 더 빨리 확인하는 시스템',115,604,1050,35,27,C.ink,true,{align:'center'});
 foot(s,'최종 발표 전 확인: 데모 서버 상태 · 사람 승인 범위 · 탐지 평가 결과 반영 여부');
 notes.push(`이번 프로젝트는 수집과 파싱, 51건 표본, 가상 기업 5곳, 파일럿 색인 223문서와 3,275청크, 평가 300문항과 295개의 생성 답변을 재현 가능한 자산으로 남겼습니다. 반면 탐지기 세 종의 나라장터 비교 성능, 25문항의 최종 사람 승인, 운영 인증과 인가, L2와 L3 자유 질문, Live DB 연결은 아직 남아 있습니다. 다음 단계는 295답변 전체 탐지 평가와 사람 승인 라벨을 고정하고, 운영 인증과 UI를 실제 서버에 연결하는 것입니다. ASTRA의 방향은 AI가 입찰 여부를 대신 확정하는 것이 아니라, 담당자가 근거와 오류 가능성을 더 빠르게 확인하도록 돕는 것입니다.\n\n근거: project-docs/PPT_최종발표_제작_인수인계_프롬프트.md; 각 산출물의 최신 README와 manifest`);
}

if(p.slides.items.length!==18||notes.length!==18) throw new Error('Expected 18 slides and notes');
for(let i=0;i<18;i++)p.slides.items[i].speakerNotes.textFrame.setText(notes[i]);

const candidate=path.join(build,'candidate-v1.pptx');
const finalPath=path.join(finalDir,'ASTRA_최종발표_v1.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);

const requirements={
 workspaceDir:repo,candidatePath:candidate,finalPath,
 pythonExecutable:runtimePython,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','10','--require-native-table-slide','14','--require-native-table-slide','16'],
 explicitTotalSlideCount:18,
 requiredNativeTableOwnerSlides:[10,14,16],
 requiredNativeChartOwnerSlides:[7],
 materializeLiteralChartWorkbooks:true,
 fontPolicy:{basis:'design',families:[F]},
 verifyArtifactToolImport:true,
 receiptPath:path.join(build,'ASTRA_최종발표_v1.validation.json')
};
const result=await finalizePresentation(requirements);
console.log(JSON.stringify(result));
