/** Build the 7-slide week-three deck with the bundled Artifact Tool.
 * Required environment: RUNTIME_NODE_MODULES, RUNTIME_PYTHON, PRESENTATION_SKILL,
 * BUSINESS_REVIEW_TEMPLATE. No source procurement files or model weights are used.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const repo=path.resolve(root,'../..');
const build=path.join(root,'.build');
const skill=process.env.PRESENTATION_SKILL;
const modules=process.env.RUNTIME_NODE_MODULES;
const template=process.env.BUSINESS_REVIEW_TEMPLATE;
if(!skill||!modules||!template||!process.env.RUNTIME_PYTHON) throw new Error('Missing bundled runtime environment');
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(path.join(modules,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,makeNativeBulletParagraphs}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
await fs.mkdir(build,{recursive:true});

// Import and retain the supplied template's layouts, masters and visual system.
const cache=path.join(build,'template.json');
let raw;
try {raw=JSON.parse(await fs.readFile(cache,'utf8'));}
catch {const imported=await PresentationFile.importPptx(await FileBlob.load(template));raw=imported.toProto();await fs.writeFile(cache,JSON.stringify(raw));}
// JSON caches serialize Uint8Array font payloads as keyed objects.
for(const font of raw.fonts??[])for(const face of font.embeddedFonts??[]){
 if(face.data && !(face.data instanceof Uint8Array))face.data=Uint8Array.from(Object.values(face.data));
}
const originals=raw.slides;
const chosen=[0,8,6,6,4,8,11];
raw.slides=chosen.map((n,i)=>{const s=structuredClone(originals[n]);s.id=`week3-${i}`;s.index=i;return s;});
// Keep the original content placeholders and chrome relevant to each layout.
const keep=[null,['532','533','7','8'],['532','533','3'],['532','533','3'],null,['532','533','7','8'],null];
raw.slides.forEach((s,i)=>{if(keep[i])s.elements=s.elements.filter(e=>keep[i].includes(e.id));});
// Template body placeholders inherit bullets on import unless buNone is
// explicitly retained at every local paragraph level.
for(const s of raw.slides)for(const e of s.elements){
 for(const l of e.levelsStyles??[])if(l.paragraphStyle)Object.assign(l.paragraphStyle,{bulletCharacter:'',marginLeft:0,indent:0,spaceBeforePoints:0,spaceAfterPoints:0});
}
// Keep the template timeline, but trim its original off-canvas endpoint.
for(const e of raw.slides[6].elements){
 if(e.bbox && e.bbox.xEmu+e.bbox.widthEmu>12192000 && e.bbox.heightEmu===0)e.bbox.widthEmu=12192000-e.bbox.xEmu;
}
// Unused illustrative template charts are not evidence for this project.
raw.charts=[];
const p=Presentation.load(raw);
const C={blue:'#3456BF',ink:'#161C2C',muted:'#5B6476',line:'#CBD1DD',paper:'#F8FAFC',rose:'#AD3B65',green:'#196C63'};
const KF='Malgun Gothic';

function shape(s,id){const x=s.shapes.items.find(x=>x.id===id);if(!x)throw new Error(`Missing template shape ${id}`);return x;}
function text(s,content,x,y,w,h,size=24,color=C.ink,bold=false){
 const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=content;a.text.style={typeface:KF,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'top',insets:{left:0,right:0,top:0,bottom:0}};return a;
}
function change(s,id,content,{x,y,w,h,size=24,color=C.ink,bold=false}={}){
 const a=shape(s,id);a.text=content.split('\n').map(line=>({runs:[line],bulletCharacter:'',marginLeft:0,indent:0,spaceBefore:0,spaceAfter:0,paragraphStyle:{bulletCharacter:'',marginLeft:0,indent:0,spaceBeforePoints:0,spaceAfterPoints:0}}));
 a.text.style={typeface:KF,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'top',insets:{left:0,right:0,top:0,bottom:0}};
 const o={};if(x!==undefined)o.left=x;if(y!==undefined)o.top=y;if(w!==undefined)o.width=w;if(h!==undefined)o.height=h;
 if(Object.keys(o).length)a.position=o;return a;
}
function bullets(s,items,x,y,w,h,size=23,color=C.ink){
 const a=text(s,'',x,y,w,h,size,color);a.text=makeNativeBulletParagraphs(items,{marginLeftPoints:13,hangingPoints:8,spaceAfterPoints:10});return a;
}
function title(s,t,idx,id='533'){
 change(s,id,t,{x:41,y:40,w:1198,h:66,size:36,color:C.blue,bold:true});
 if(s.shapes.items.some(x=>x.id==='532'))change(s,'532',String(idx),{x:1218,y:670,w:30,h:25,size:16});
}
function table(s,values,x,y,w,h,widths,size=22){
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
 t.borders.assign({fill:C.line,width:.7,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({fill:C.paper,textStyle:{typeface:KF,fontSize:size,color:C.ink},margins:{left:10,right:10,top:10,bottom:9},anchor:'center'});
 for(let j=0;j<values[0].length;j++){const c=t.getCell(0,j);c.fill='#E8EDF9';c.text.style={typeface:KF,fontSize:size,bold:true,color:C.blue};}
 t.rows[0].height=54;return t;
}
function node(s,name,status,detail,x,y,w,h){
 const n=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:C.paper,line:{fill:C.line,width:1.3}});
 text(s,status,x+15,y+13,w-30,25,17,C.muted);
 text(s,name,x+15,y+47,w-30,62,25,C.blue,true);
 text(s,detail,x+15,y+116,w-30,h-122,20,C.ink);
 return n;
}

// 0. Template cover, expanded only enough to fit Korean title text.
{
const s=p.slides.items[0];
change(s,'10','포스코 AI·Big Data 아카데미 B1조',{x:63,y:58,w:1050,h:38,size:24,color:'#98A1B2'});
change(s,'4','한국어 환각 탐지와 공간 시각화 기반\n나라장터 입찰 검토 시스템',{x:60,y:153,w:1160,h:200,size:49,color:C.blue,bold:true});
change(s,'6','3주차 중간 보고 · 2026.09.12 기준',{x:63,y:484,w:1080,h:40,size:24,color:C.blue,bold:true});
change(s,'5','문서 근거를 확인하는 RAG와 ASTRA 공간 탐색 프로토타입\n\n양진우 외 팀원 5명',{x:63,y:548,w:1110,h:102,size:23,color:C.muted});
const divider=shape(s,'7');divider.position={left:0,top:413,width:1280,height:0};
}
// 1. Template explanatory column plus editable comparison table.
{
const s=p.slides.items[1];title(s,'입찰 조건과 AI 답변의 근거 검토',1);
change(s,'8','공고·정정·회사 증빙의 대조',{x:41,y:154,w:405,h:82,size:29,bold:true});
change(s,'7','공식 사례\n입찰 취소 이의에 대한\n권익위 시정권고 (2019)\n\n연구 질문\n번역 데이터로 학습한 탐지기가\n실제 한국어 공고에서도\n의심 구절을 찾을 수 있는가?',{x:41,y:260,w:405,h:330,size:24});
table(s,[['접근','역할·선행연구','확인할 지표'],['일반 RAG','검색과 답변 생성','Recall@K\nHit Rate·지연'],['GraphRAG','관계·커뮤니티 기반\n전역 질의 요약','관계 확장 전후\n검색·근거 정확도'],['LettuceDetect\n계열','문맥 기반\n토큰·구간 탐지','환각 P/R/F1\nspan F1'],['우리 적용','한국어 탐지·숫자 규칙\n원문·공간 UI','오판·보류율\n검토 시간']],488,158,750,420,[162,310,278],22);
text(s,'과제·평가 단위가 달라 선행연구 성능 숫자를 직접 순위화하지 않음',488,605,750,49,20,C.muted);
text(s,'출처: 권익위(2019), RAGTruth(2024), LettuceDetect·Turk-LettuceDetect, GraphRAG',41,664,1135,27,15,C.muted);
}
// 2. Explicitly requested editable architecture diagram.
{
const s=p.slides.items[2];title(s,'검색·생성·탐지와 공간 UI 아키텍처',2);
change(s,'3','입력 문서와 답변을 같은 버전으로 연결하는 목표 흐름',{x:41,y:126,w:1190,h:45,size:27});
const a=node(s,'수집·구조화','파이프라인·집계 완료','공고·첨부 버전 / SHA-256\n파싱·어댑터·SQLite\n페이지·조항 근거 청킹',41,208,270,215);
const b=node(s,'권한 검색·답변','실연결 예정','원본 BGE-M3 임베딩\npgvector·Gemma\n회사 + 문서 권한 검사',348,208,270,215);
const c=node(s,'한국어 답변 검증','모델 개발 완료 / 통합 예정','학습한 토큰 탐지기\n별도 숫자·기간 규칙\n인용 청크 연결 검증',655,208,270,215);
const d=node(s,'원문·공간 검토','시연 목업 동작','의심 구간 하이라이트\n근거 원문·관계 그래프\n공고·과업 선택',962,208,276,215);
for(const [u,v] of [[a,b],[b,c],[c,d]])s.shapes.connect(u,v,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:C.blue,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});
text(s,'공간 엔진',41,462,250,42,26,C.blue,true);
text(s,'Reality: MapLibre + OpenFreeMap + DEM\nVirtual: Three.js 합성 도시·설비',41,518,560,84,24);
text(s,'Live 연동 설계',655,462,550,42,26,C.blue,true);
text(s,'FastAPI REST + POST NDJSON / 동일 snapshot\nGraphRAG 관계 확장 검색은 후속 구현·평가',655,518,580,84,23);
text(s,'검색용 원본 BGE-M3와 학습한 탐지기는 별도 모델 역할. 전체 통합 완료를 뜻하지 않음',41,642,1150,43,20,C.muted);
}
// 3. Two evidence streams in the template's two-column composition.
{
const s=p.slides.items[3];title(s,'데이터와 한국어 탐지 모델 준비 현황',3);
change(s,'3','학습·평가 완료 기록과 실데이터 집계를 구분',{x:41,y:132,w:1160,h:47,size:28});
text(s,'한국어 환각 탐지',41,211,560,48,29,C.blue,true);
bullets(s,['RAGTruth 환각 구간을 <HAL> 태그로 감싸 한국어 번역','태그 검사·문자 위치 재계산 후 이진 토큰 분류 학습','KLUE-RoBERTa, XLM-RoBERTa, BGE-M3 학습','숫자 변조는 확인된 취약점. 나라장터 적용 성능은 평가 예정'],41,278,553,297,23);
text(s,'성능값은 원본 실험 조건 재확인 후 사용\n자동 태그 검사가 번역 의미 보존을 보장하지 않음',41,609,553,64,20,C.muted);
text(s,'4~6월 공고 행 137,745건',656,211,582,45,30,C.blue,true);
text(s,'차수 포함 / 최신 차수 124,522건',656,260,582,38,23);
table(s,[['타깃 분야','공고','완전 공고'],['SW·시스템 개발','2,163','984'],['운영·유지관리','1,313','681'],['합계','3,476','1,665']],656,318,582,234,[302,140,140],23);
text(s,'표본 51건 (월별 17건) 선정·수집',656,575,582,40,25,C.blue,true);
text(s,'완전 공고 = 공고문 + (RFP 또는 과업·규격)\n선정 이유는 실적·인력·인증·단가 검토의 적합성',656,624,582,56,19,C.muted);
}
// 4. Template screenshot column and three explanatory cards.
{
const s=p.slides.items[4];title(s,'광역·사옥·설비 공간 탐색 프로토타입',4);
change(s,'5','합성 자료 기반의 3단계 탐색 동작',{x:41,y:137,w:600,h:47,size:27});
change(s,'3','문서·과업·설비 ID를 연결한 시연\nGraphRAG·생성·탐지 모델은 미연결',{x:41,y:587,w:595,h:84,size:23,color:C.muted});
const macro=await fs.readFile(path.join(root,'source/astra_macro.png'));
s.images.add({blob:macro,contentType:'image/png',alt:'합성 자료 기반 ASTRA 광역 시연 화면. 화면 숫자는 가상 예시.',fit:'contain',position:{left:41,top:194,width:590,height:333}});
text(s,'합성 데이터 기반 실제 데모 캡처',41,542,590,36,21,C.blue);
change(s,'28','광역 / Macro',{x:698,y:197,w:510,h:36,size:25,color:C.blue,bold:true});
change(s,'27','가상 특구·현실 지도 앵커 탐색\n실제 공고 밀집도 데이터는 미연결',{x:698,y:239,w:510,h:61,size:22});
change(s,'6','사옥 / Building',{x:698,y:356,w:510,h:36,size:25,color:C.blue,bold:true});
change(s,'4','카메라 보간 이동, 포탈·HUD 전개\n합성 좌표와 선택 공고 화면 동기화',{x:698,y:398,w:510,h:61,size:22});
change(s,'9','설비 / Interior',{x:698,y:508,w:510,h:36,size:25,color:C.blue,bold:true});
change(s,'8','외벽 와이어프레임·설비 강조\n실제 BIM 절단·실측 설비는 아님',{x:698,y:550,w:510,h:61,size:22});
text(s,'화면의 구 공간 L1/L2/L3 표기는 문서 보안 등급과 별개',41,678,1150,27,17,C.muted);
}
// 5. Evaluation table: every unmeasured result explicitly remains unmeasured.
{
const s=p.slides.items[5];title(s,'평가 지표와 검증 설계',5);
change(s,'8','같은 공고·회사·질문으로\n비교 조건 고정',{x:41,y:164,w:405,h:100,size:29,bold:true});
change(s,'7','일반 RAG\n+ 한국어 환각 탐지\n+ 숫자·기간 규칙\n\nGraphRAG는 구현 후 비교\n\n계획\n질문 300개 / 교차 검수 100건\n권한 차단 테스트 20개',{x:41,y:298,w:415,h:322,size:24});
table(s,[['평가 축','지표·조건','상태'],['환각 탐지','환각 P/R/F1·span F1\n숫자 변조 재현율','공고 평가 예정'],['검색·근거','Recall@K·Hit Rate\n인용 청크 정확도','정답 근거 준비'],['참가 조건','잘못된 충족 판정률\n전체 정확도·보류율','실측 전'],['응답 지연','첫 토큰·전체 검증\np50 / p95','실측 전'],['3D·사용성','프레임 시간 p95\n검토 시간·성공률','60 FPS는 목표']],488,159,750,438,[154,370,226],21);
text(s,'임계값은 개발 자료에서 고정. 오류 건수·분모·보류율을 함께 보고',488,622,750,49,20,C.muted);
}
// 6. Reuse native timeline and milestone positions.
{
const s=p.slides.items[6];
change(s,'11','실제 공고 연결과 최종 검증 일정',{x:41,y:40,w:1198,h:68,size:36,color:C.blue,bold:true});
change(s,'4','6',{x:1218,y:670,w:30,h:25,size:16});
text(s,'첫 연결 기준: 실제 공고 1건 + 합성 기업 1곳 + 질문 5개 검수',41,150,1190,53,28);
change(s,'9','9/13~19',{x:41,y:303,w:355,h:43,size:24,color:C.blue,bold:true});
change(s,'13','9/18~26',{x:452,y:303,w:350,h:43,size:24,color:C.blue,bold:true});
change(s,'14','9/24~10/2',{x:864,y:303,w:374,h:43,size:24,color:C.blue,bold:true});
change(s,'16','요건·평가 자산\n\n팀장·데이터·평가 담당\n요건 추출·합성 기업 5곳 검수\n질문 300개 준비',{x:41,y:409,w:369,h:191,size:23});
change(s,'17','백엔드·UI 통합\n\n팀장·UI·인프라 담당\nRAG·탐지·NDJSON 연결\n원문·노드 강조·권한 차단',{x:452,y:409,w:369,h:191,size:23});
change(s,'18','평가·발표\n\n전원\n라벨링·교차 검수·9/29 집계\n9/30 자료 정리·10/2 발표',{x:864,y:409,w:374,h:191,size:23});
text(s,'후속 확장: GraphRAG 관계 검색 비교, 설비 모델 개선, 권한 적용 Live DB 스트리밍',41,630,1150,52,23,C.muted);
}

// Speaker notes contain the complete requested script, layout and references.
const md=await fs.readFile(path.join(root,'3주차_중간발표_슬라이드원고.md'),'utf8');
const chunks=md.split(/^## 슬라이드 /m).slice(1);
if(chunks.length!==7)throw new Error('Expected 7 source sections');
for(let i=0;i<7;i++){
 const note=('슬라이드 '+chunks[i]).split('\n## 발표 전 반드시')[0];
 const withLinks=note.replace(/\]\(\.\.\/\.\.\/([^)]*)\)/g,(_,tail)=>`](https://github.com/YangNaang2/ko-lettucedetect/blob/c6858e4/${tail})`);
 p.slides.items[i].speakerNotes.textFrame.setText(withLinks);
}

const rev=process.env.DECK_REVISION||'v1';
const candidate=path.join(build,`candidate-${rev}.pptx`);
const finalPath=path.join(root,'output',`3주차_중간발표_초안_${rev}.pptx`);
await fs.mkdir(path.dirname(finalPath),{recursive:true});
await(await PresentationFile.exportPptx(p)).save(candidate);
await fs.writeFile(path.join(build,`authored-${rev}.json`),JSON.stringify(p.toProto()));
for(let i=0;i<7;i++){
 const s=p.slides.items[i];
 await fs.writeFile(path.join(build,`slide-${i}-${rev}.png`),new Uint8Array(await(await s.export({format:'png',scale:1})).arrayBuffer()));
 await fs.writeFile(path.join(build,`slide-${i}-${rev}.layout.json`),await(await s.export({format:'layout'})).text());
 console.log('Rendered',i);
}
const final=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,
 pythonExecutable:process.env.RUNTIME_PYTHON,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','2','--require-native-table-slide','4','--require-native-table-slide','6'],
 explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[2,4,6],requiredNativeChartOwnerSlides:[],
 // The reference does not supply Korean glyphs. Korean adaptation uses one
 // locally available family while retaining the reference geometry and colors.
 fontPolicy:{basis:'design',families:[KF]},
 verifyArtifactToolImport:true,receiptPath:path.join(build,`validation-${rev}.json`)});
console.log(JSON.stringify(final));
// The PPTX is finalized only after every awaited export and validation succeeds.
process.exit(0);
