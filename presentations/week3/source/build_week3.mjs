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
const chosen=[0,6,6,6,6,6,6];
raw.slides=chosen.map((n,i)=>{const s=structuredClone(originals[n]);s.id=`week3-${i}`;s.index=i;return s;});
// Keep the original content placeholders and chrome relevant to each layout.
const keep=[null,['532','533','3'],[],['532','533','3'],['532','533','3'],['532','533','3'],['532','533','3']];
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
change(s,'4','한국어 환각 탐지와 권한 기반 RAG\n나라장터 입찰 검토 시스템',{x:60,y:153,w:1160,h:200,size:49,color:C.blue,bold:true});
change(s,'6','3주차 중간 보고 · 2026.09.12 기준',{x:63,y:484,w:1080,h:40,size:24,color:C.blue,bold:true});
change(s,'5','Finding Hallucination · 허용된 근거로 답하고, 의심 구간을 확인하다\n\n양진우 외 팀원 5명',{x:63,y:548,w:1110,h:102,size:23,color:C.muted});
const divider=shape(s,'7');divider.position={left:0,top:413,width:1280,height:0};
}
// 1. Background rewritten from the supplied MD; unverified absolute claims omitted.
{
const s=p.slides.items[1];title(s,'입찰 제안팀에는 답변 검증과 문서 보호가 함께 필요하다',2);
change(s,'3','대상: 정보시스템 구축·운영 입찰을 준비하는 기업의 제안팀',{x:41,y:135,w:1190,h:48,size:27});
text(s,'문서 근거가 있어도 생기는 오류',41,224,560,47,28,C.blue,true);
bullets(s,['RAG 답변에도 근거 없는 내용과 모순이 남을 수 있음','자격·실적·기간 등 조건을 원문과 다시 대조해야 함'],41,286,550,154,25);
text(s,'서로 다른 공개 범위의 자료',655,224,585,47,28,C.blue,true);
bullets(s,['공개 RFP와 사내 실적·인력·원가를 함께 검토','질문자의 회사·담당 프로젝트·승인 조건에 따라 검색 범위를 제한'],655,286,578,154,25);
text(s,'왜 나라장터 RFP인가',41,484,550,45,28,C.blue,true);
text(s,'공개 공고를 확보할 수 있고, 자격요건과\n회사 증빙을 대조하는 업무 흐름이 분명함',41,548,560,91,24);
text(s,'왜 사내 실행을 지향하는가',655,484,580,45,28,C.blue,true);
text(s,'민감 자료의 처리 경계를 통제하는 설계\n로컬 서버 자원에 맞춘 모델 구성 검토',655,548,580,91,24);
text(s,'근거: RAGTruth(ACL 2024), 첨부 추진배경 MD, 팀공유 문서 · 로컬 운영은 목표',41,674,1160,24,16,C.muted);
}
// 2. User-supplied SVG structure, edited for evidence and presentation legibility.
{
const s=p.slides.items[2];
const svg=await fs.readFile(path.join(root,'source/보안RAG_전체구조_글꼴윤곽.svg'));
s.images.add({blob:svg,contentType:'image/svg+xml',alt:'학습 파이프라인과 권한 기반 질의 처리 목표 구조. 학습 완료와 통합 예정 상태 구분.',fit:'contain',position:{left:0,top:0,width:1280,height:720}});
}
// 3. Two evidence streams in the template's two-column composition.
{
const s=p.slides.items[3];title(s,'데이터와 한국어 탐지 모델 준비 현황',4);
change(s,'3','학습·평가 완료 기록과 실데이터 집계를 구분',{x:41,y:132,w:1160,h:47,size:28});
text(s,'한국어 환각 탐지',656,211,560,48,29,C.blue,true);
bullets(s,['RAGTruth 환각 구간을 <HAL> 태그로 감싸 한국어 번역','태그 검사·문자 위치 재계산 후 이진 토큰 분류 학습','KLUE-RoBERTa, XLM-RoBERTa, BGE-M3 학습','숫자 변조는 확인된 취약점. 나라장터 적용 성능은 평가 예정'],656,278,553,297,23);
text(s,'성능값은 원본 실험 조건 재확인 후 사용\n자동 태그 검사가 번역 의미 보존을 보장하지 않음',656,609,553,64,20,C.muted);
text(s,'4~6월 공고 행 137,745건',41,211,582,45,30,C.blue,true);
text(s,'차수 포함 / 최신 차수 124,522건',41,260,582,38,23);
table(s,[['타깃 분야','공고','완전 공고'],['SW·시스템 개발','2,163','984'],['운영·유지관리','1,313','681'],['합계','3,476','1,665']],41,318,582,234,[302,140,140],23);
text(s,'표본 51건 (월별 17건) 선정·수집',41,575,582,40,25,C.blue,true);
text(s,'완전 공고 = 공고문 + (RFP 또는 과업·규격)\n선정 이유는 실적·인력·인증·단가 검토의 적합성',41,624,582,56,19,C.muted);
}
// 4. Project goal and the meaning of authorization, replacing private 3D content.
{
const s=p.slides.items[4];title(s,'프로젝트 목표와 비취인가 개념의 적용 범위',5);
change(s,'3','입찰 담당자가 허용된 자료로 조건을 검토하고, 답변의 의심 구간을 원문에서 확인',{x:41,y:134,w:1190,h:77,size:27});
table(s,[['자료 등급 · 프로젝트 예시','보호할 내용','접근 조건 설계'],['L1 공개','공고문 · RFP · 과업 문서','공개 문서 열람'],['L2 대외비','회사 실적 · 인력 · 인증','회사 일치 + 프로젝트 배정 + 문서 권한'],['L3 기밀','원가 · 투찰 전략 · 마진','L2 조건 + 해당 자료 승인 + 유효기간']],41,239,1197,266,[285,365,547],23);
text(s,'비취인가 = 비밀취급인가',41,548,550,43,28,C.blue,true);
text(s,'발표의 L1~L3는 사내 문서 분류 예시\n국가 비밀 등급·인가 취득을 뜻하지 않음',41,605,560,73,23);
text(s,'등급은 데이터에, 접근은 요청 조건에',655,548,580,43,28,C.blue,true);
text(s,'높은 직급이어도 다른 프로젝트는 거부\n배정·승인·유효기간 충족 시 필요한 자료 허용',655,605,580,73,23);
}
// 5. Runtime detail moved out of the overall diagram; no evaluation metrics.
{
const s=p.slides.items[5];title(s,'한 질문에서 근거·권한·의심 구간을 연결하는 방식',6);
change(s,'3','설계 단계: 질문 + 공고 버전 + 회사 자료 버전을 하나의 요청으로 고정',{x:41,y:135,w:1190,h:48,size:27});
const a=node(s,'권한을 먼저 확인','서버 검색 경계','회사·프로젝트·승인\n허용된 청크만 검색\n권한 밖 자료 제외',41,226,370,208);
const b=node(s,'근거로 답변 생성','RAG + 로컬 Gemma','원본 BGE-M3 검색\n인가 문맥으로 생성\n탐지기도 같은 문맥 사용',452,226,370,208);
const c=node(s,'검토 결과 표시','근거 + 의심 구간','학습 탐지와 규칙 분리\n원문·인용 위치 연결\n자료 부족 시 판단 보류',864,226,374,208);
for(const [u,v] of [[a,b],[b,c]])s.shapes.connect(u,v,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:C.blue,width:2},tail:{type:'triangle',width:'sm',length:'sm'}});
text(s,'Live 연결 설계',41,479,550,45,28,C.blue,true);
text(s,'FastAPI REST + POST NDJSON\nPostgreSQL / pgvector · 청크 ID·문서 해시\n원문·다운로드·그래프에도 같은 권한 적용',41,544,570,117,23);
text(s,'GraphRAG의 후속 역할',655,479,580,45,28,C.blue,true);
text(s,'요건과 증빙의 관계를 따라 검색 후보 확장\n확장된 노드에도 동일한 권한 검사\n현재 관계 검색은 실제 서비스 미연결',655,544,580,117,23);
}
// 6. Concrete delivery schedule from the latest team assignment document.
{
const s=p.slides.items[6];title(s,'10월 2일 발표까지, 담당자와 제출물 중심으로 연결',7);
change(s,'3','최초 연결 목표: 실제 공고 1건 + 합성 기업 1곳 + 질문 5개를 사람이 검수',{x:41,y:135,w:1190,h:68,size:27});
table(s,[['기한','담당','제출물 · 완료 조건'],['9/13~19','전원 / 팀장 / 팀원 1~3','요건 시트 51건 · 합성 기업 5곳 검수\n공고 요건과 기업 증빙을 ID·문서 버전으로 연결'],['9/18~22','팀장 / 팀원 1','권한 검색 + Gemma + 탐지 API\n한 질문의 답변·근거·의심 구간을 같은 버전으로 반환'],['9/22~26','팀원 4 / 팀장','답변 스트리밍 · 원문 하이라이트 연결\n무승인 차단 / 조건부 허용 / 타 회사·프로젝트 차단'],['9/27~30','팀원 5 / 전원','오류 사례 조정 · 발표 자료 · 시연 대본\n동일한 시나리오를 리허설에서 재현'],['10/2','전원','최종 발표 · 구현 범위와 후속 과제 설명']],41,239,1197,361,[170,245,782],22);
text(s,'일정·수량은 계획입니다. 기업 L2/L3 자료는 합성하며, 실제 인증·인가와 API 연결은 구현 예정입니다.',41,636,1160,59,21,C.muted);
}

// Speaker notes contain the complete requested script, layout and references.
const md=await fs.readFile(path.join(root,'3주차_중간발표_슬라이드원고_v5.md'),'utf8');
const chunks=md.split(/^## 슬라이드 /m).slice(1);
if(chunks.length!==7)throw new Error('Expected 7 source sections');
for(let i=0;i<7;i++){
 const note=('슬라이드 '+chunks[i]).split('\n## 발표 전 반드시')[0];
 const withLinks=note.replace(/\]\(\.\.\/\.\.\/([^)]*)\)/g,(_,tail)=>`](https://github.com/YangNaang2/ko-lettucedetect/blob/c6858e4/${tail})`);
 p.slides.items[i].speakerNotes.textFrame.setText(withLinks);
}

const rev=process.env.DECK_REVISION||'v5';
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
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','4','--require-native-table-slide','5','--require-native-table-slide','7'],
 explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[4,5,7],requiredNativeChartOwnerSlides:[],
 // The reference does not supply Korean glyphs. Korean adaptation uses one
 // locally available family while retaining the reference geometry and colors.
 fontPolicy:{basis:'design',families:[KF]},
 verifyArtifactToolImport:true,receiptPath:path.join(build,`validation-${rev}.json`)});
console.log(JSON.stringify(final));
// The PPTX is finalized only after every awaited export and validation succeeds.
process.exit(0);
