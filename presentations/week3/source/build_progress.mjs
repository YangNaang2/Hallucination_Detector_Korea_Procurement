/** Build the 8-slide focused week-three report with the bundled Artifact Tool.
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
const chosen=[6,6,6,6,6,6,6,6];
raw.slides=chosen.map((n,i)=>{const s=structuredClone(originals[n]);s.id=`week3-${i}`;s.index=i;return s;});
// Keep the original content placeholders and chrome relevant to each layout.
const keep=Array.from({length:8},()=>['532','533','3']);
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

const {compose}=await import('./progress_slides.mjs');
compose({p,C,text,change,title,table,bullets,node});
const md=await fs.readFile(path.join(root,'3주차_진행보고_발표원고.md'),'utf8');
const sections=md.split(/^## 슬라이드 /m).slice(1);
if(sections.length!==8)throw new Error('Expected eight slide notes');
sections.forEach((section,i)=>p.slides.items[i].speakerNotes.textFrame.setText('슬라이드 '+section));
const rev=process.env.DECK_REVISION||'progress-v1';
const candidate=path.join(build,`candidate-${rev}.pptx`);
const finalPath=path.join(root,'output',`3주차_진행보고_${rev}.pptx`);
await fs.mkdir(path.dirname(finalPath),{recursive:true});
await(await PresentationFile.exportPptx(p)).save(candidate);
for(let i=0;i<8;i++){
 await fs.writeFile(path.join(build,`${rev}-${i+1}.png`),new Uint8Array(await(await p.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
 console.log('Rendered',i+1);
}
const owners=[4,5,6];
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,
 pythonExecutable:process.env.RUNTIME_PYTHON,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...owners.flatMap(n=>['--require-native-table-slide',String(n)])],
 explicitTotalSlideCount:8,requiredNativeTableOwnerSlides:owners,requiredNativeChartOwnerSlides:[],
 fontPolicy:{basis:'design',families:[KF]},verifyArtifactToolImport:true,
 receiptPath:path.join(build,`validation-${rev}.json`)});
console.log(JSON.stringify(result));
const final=await PresentationFile.importPptx(await FileBlob.load(finalPath));
if(final.slides.items.length!==8)throw new Error('Final count mismatch');
for(let i=0;i<8;i++){
 await fs.writeFile(path.join(build,`final-${rev}-${i+1}.png`),new Uint8Array(await(await final.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
 console.log('Final rendered',i+1);
}
process.exit(0);
