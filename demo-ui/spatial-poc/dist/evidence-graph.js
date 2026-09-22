const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const TYPES={
 ProcurementNotice:{label:'공고',color:'#356fe5',icon:'공'},Document:{label:'문서',color:'#1f91bd',icon:'문'},Requirement:{label:'요구 조건',color:'#e98a3c',icon:'조'},Company:{label:'기업',color:'#7b61d1',icon:'기'},Person:{label:'인력',color:'#9874d6',icon:'인'},Project:{label:'실적',color:'#dc7d3d',icon:'실'},Certification:{label:'인증',color:'#3e9e78',icon:'인'},Scenario:{label:'시나리오',color:'#8467bb',icon:'시'},Question:{label:'질문',color:'#294f9b',icon:'Q'},Answer:{label:'답변',color:'#18a99a',icon:'A'},EvidenceWindow:{label:'근거 구간',color:'#16a3a0',icon:'근'},Citation:{label:'인용',color:'#4d9a76',icon:'['},HallucinationSpan:{label:'의심 구절',color:'#d95757',icon:'!'},Review:{label:'검수',color:'#6f7d90',icon:'검'}
};
const MODES={
 evidence:{kicker:'EVIDENCE PATH',title:'질문에서 답변 근거까지',types:['Question','ProcurementNotice','Document','EvidenceWindow','Citation','Answer']},
 hallucination:{kicker:'HALLUCINATION REVIEW',title:'의심 구절과 검수 상태',types:['Question','Answer','HallucinationSpan','Review','Citation','EvidenceWindow','Document']},
 eligibility:{kicker:'BID ELIGIBILITY',title:'공고 조건과 기업 증빙',types:['ProcurementNotice','Requirement','Company','Person','Project','Certification','Scenario']},
 overview:{kicker:'DATA RELATIONSHIP',title:'ASTRA 데이터 전체 구조',types:Object.keys(TYPES)}
};
const EDGE_LABELS={NOTICE_HAS_DOCUMENT:'첨부',DOCUMENT_HAS_EVIDENCE_WINDOW:'포함',QUESTION_ABOUT_NOTICE:'질문 대상',QUESTION_RETRIEVED_EVIDENCE:'검색 근거',ANSWER_RESPONDS_TO_QUESTION:'응답',ANSWER_HAS_CITATION:'인용',CITATION_POINTS_TO_EVIDENCE:'근거 지시',HALLUCINATION_SPAN_IN_ANSWER:'답변 구간',REVIEW_REVIEWS_SPAN:'검수',NOTICE_REQUIRES_REQUIREMENT:'요구',COMPANY_SATISFIES_REQUIREMENT:'충족',COMPANY_MISSING_REQUIREMENT:'미충족',COMPANY_REQUIREMENT_UNRESOLVED:'판단 보류',COMPANY_HAS_PERSON:'소속',COMPANY_HAS_PROJECT:'보유 실적',COMPANY_HAS_CERTIFICATION:'보유 인증',SCENARIO_FOR_COMPANY:'기업 문맥',SCENARIO_FOR_NOTICE:'공고 문맥'};
const initialParams=new URLSearchParams(location.search),initialMode=initialParams.get('mode');
let graph={nodes:[],edges:[]},byId=new Map(),adj=new Map(),mode=MODES[initialMode]?initialMode:'evidence',enabled=new Set(MODES[MODES[initialMode]?initialMode:'evidence'].types),selected=null,query='',scale=1,tx=0,ty=0,positions=new Map(),drag=null,pan=null,serverMode=false;

function hash(value){let h=2166136261;for(const c of value)h=(h^c.charCodeAt(0))*16777619>>>0;return h;}
function text(value,n=38){const s=String(value??'');return s.length>n?s.slice(0,n-1)+'…':s;}
function rebuildIndex(){byId=new Map(graph.nodes.map(n=>[n.id,n]));adj=new Map(graph.nodes.map(n=>[n.id,[]]));for(const e of graph.edges){adj.get(e.source)?.push({node:e.target,edge:e});adj.get(e.target)?.push({node:e.source,edge:e});}}
function neighbors(id,depth=1){const found=new Set([id]),front=[id];for(let d=0;d<depth;d++){for(const current of [...front.splice(0)])for(const x of adj.get(current)||[])if(!found.has(x.node)){found.add(x.node);front.push(x.node);}}return found;}

async function load(){
 const role=$('#role').value,company=$('#company').value;
 try{const r=await fetch(`/api/evidence-graph?role=${encodeURIComponent(role)}&company_id=${encodeURIComponent(company)}`);if(!r.ok)throw Error();graph=await r.json();serverMode=true;}
 catch{graph=await fetch('evidence-graph-public.json').then(r=>r.json());serverMode=false;if(role!=='viewer'){$('#role').value='viewer';}}
 rebuildIndex();selected=null;positions.clear();renderFilters();render();
 const session=graph.session;$('#scope-title').textContent=session&&session.role!=='viewer'?`${session.company_id} · ${session.role}`:'공개 L1 보기';
 $('#scope-copy').textContent=serverMode?'서버가 권한에 맞는 노드와 연결만 반환합니다.':'정적 공개 자료로 실행 중입니다. L2·L3는 로컬 ACL 서버가 필요합니다.';
 $('#status').textContent=`${serverMode?'서버 ACL':'정적 L1'} · 저장 데이터 ${graph.nodes.length}개 노드 · ${graph.edges.length}개 연결`;
}

function renderFilters(){
 const present=new Set(graph.nodes.map(n=>n.type));
 $('#type-filters').innerHTML=Object.entries(TYPES).filter(([k])=>present.has(k)).map(([k,v])=>`<label style="--node-color:${v.color}"><input type="checkbox" value="${k}" ${enabled.has(k)?'checked':''}><i></i>${v.label}</label>`).join('');
 $$('#type-filters input').forEach(input=>input.onchange=()=>{input.checked?enabled.add(input.value):enabled.delete(input.value);render();});
}

function candidateNodes(){
 let nodes=graph.nodes.filter(n=>enabled.has(n.type));
 const types=new Set(MODES[mode].types);nodes=nodes.filter(n=>types.has(n.type));
 if(query){const hits=new Set();for(const n of nodes){const hay=(n.label+' '+JSON.stringify(n.properties)).toLowerCase();if(hay.includes(query.toLowerCase()))for(const id of neighbors(n.id,1))hits.add(id);}nodes=nodes.filter(n=>hits.has(n.id));}
 const important=new Set();
 if(mode==='evidence'||mode==='hallucination')for(const n of nodes)if(['Question','Answer','HallucinationSpan','Review','EvidenceWindow','Citation'].includes(n.type))for(const id of neighbors(n.id,2))important.add(id);
 if(mode==='eligibility')for(const n of nodes)if(['Company','Requirement','Scenario'].includes(n.type))for(const id of neighbors(n.id,2))important.add(id);
 if(important.size)nodes=nodes.filter(n=>important.has(n.id));
 const priority={Question:0,Answer:0,HallucinationSpan:0,Review:1,Company:0,Requirement:0,Scenario:1,EvidenceWindow:1,Citation:2,ProcurementNotice:3,Document:4,Person:4,Project:3,Certification:3};
 nodes.sort((a,b)=>(priority[a.type]??5)-(priority[b.type]??5)||a.id.localeCompare(b.id));
 return nodes.slice(0,mode==='overview'?150:180);
}

function layout(nodes){
 const groups=new Map();for(const n of nodes){if(!groups.has(n.type))groups.set(n.type,[]);groups.get(n.type).push(n);}
 const columns={
  evidence:{Question:90,ProcurementNotice:310,Document:530,EvidenceWindow:760,Citation:980,Answer:1210},
  hallucination:{Question:90,Answer:310,HallucinationSpan:570,Review:790,Citation:990,EvidenceWindow:1200,Document:1410},
  eligibility:{ProcurementNotice:80,Requirement:300,Company:560,Person:800,Project:1020,Certification:1240,Scenario:1430},
  overview:{ProcurementNotice:120,Document:340,Question:520,EvidenceWindow:690,Citation:850,Answer:1010,HallucinationSpan:1190,Review:1360,Company:520,Requirement:690,Person:850,Project:1010,Certification:1170,Scenario:1360}
 }[mode];
 for(const [type,list] of groups){
  const x=columns[type]??750,rows=Math.max(1,list.length),step=Math.min(92,760/rows),start=70+(760-step*(rows-1))/2;
  list.forEach((n,i)=>{if(!positions.has(n.id))positions.set(n.id,{x:x+((hash(n.id)%29)-14),y:start+i*step+((hash(n.id+'y')%21)-10)});});
 }
}

function nodeSvg(n){
 const p=positions.get(n.id),base=TYPES[n.type]||{color:'#64748b',icon:'·',label:n.type},statusColor=n.type==='Requirement'?({충족:'#2c9a68',미충족:'#d95757',자료부족:'#e98a3c',원문충돌:'#9a6bd0'}[n.properties.status]):null,t={...base,color:statusColor||base.color};const w=n.type==='HallucinationSpan'?150:136;
 const selectedClass=selected===n.id?' selected':'';
 return `<g class="graph-node${selectedClass}" data-id="${esc(n.id)}" style="--node-color:${t.color}" transform="translate(${p.x},${p.y})" tabindex="0" role="button" aria-label="${esc(t.label+' '+n.label)}">
 <rect class="shape" x="${-w/2}" y="-25" rx="10" width="${w}" height="50"/><rect class="accent" x="${-w/2}" y="-25" rx="10" width="32" height="50"/><text class="icon" x="${-w/2+16}" y="4">${esc(t.icon)}</text>
 <text class="label" x="${-w/2+39}" y="-3">${esc(text(n.label,19))}</text><text class="sub" x="${-w/2+39}" y="12">${esc(t.label)}</text>
 <rect class="access-pill" x="${w/2-24}" y="-20" width="18" height="10" rx="5"/><text class="access-text" x="${w/2-15}" y="-12" text-anchor="middle">${n.access.level}</text></g>`;
}
function edgeSvg(e,isActive){const a=positions.get(e.source),b=positions.get(e.target);if(!a||!b)return'';const dx=Math.max(45,Math.abs(b.x-a.x)*.45),d=`M${a.x},${a.y} C${a.x+(b.x>=a.x?dx:-dx)},${a.y} ${b.x-(b.x>=a.x?dx:-dx)},${b.y} ${b.x},${b.y}`;const relation=e.type==='COMPANY_SATISFIES_REQUIREMENT'?' success':e.type==='COMPANY_MISSING_REQUIREMENT'?' failure':e.type==='COMPANY_REQUIREMENT_UNRESOLVED'?' unresolved':'';const label=isActive?`<text class="edge-label" x="${(a.x+b.x)/2}" y="${(a.y+b.y)/2-5}" text-anchor="middle">${esc(EDGE_LABELS[e.type]||e.type)}</text>`:'';return `<path class="edge${isActive?' active':''}${relation}" data-edge="${esc(e.id)}" d="${d}"/>${label}`;}

function render(){
 const nodes=candidateNodes(),ids=new Set(nodes.map(n=>n.id));layout(nodes);const edges=graph.edges.filter(e=>ids.has(e.source)&&ids.has(e.target));const active=selected?neighbors(selected,1):new Set();
 $('#edges').innerHTML=edges.map(e=>edgeSvg(e,selected&&(e.source===selected||e.target===selected))).join('');
 $('#nodes').innerHTML=nodes.map(nodeSvg).join('');
 if(selected){$$('.graph-node').forEach(g=>g.classList.toggle('dim',!active.has(g.dataset.id)));$$('.edge').forEach(path=>{const e=graph.edges.find(x=>x.id===path.dataset.edge);path.classList.toggle('dim',e&&e.source!==selected&&e.target!==selected);});}
 $('#empty').hidden=nodes.length>0;$('#visible-count').textContent=`${nodes.length} 노드 · ${edges.length} 연결`;$('#mode-kicker').textContent=MODES[mode].kicker;$('#mode-title').textContent=MODES[mode].title;
 $$('.mode-tabs button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===mode)));
 const shownTypes=[...new Set(nodes.map(n=>n.type))];$('#legend').innerHTML=shownTypes.map(k=>`<span style="--node-color:${TYPES[k]?.color||'#64748b'}"><i></i>${esc(TYPES[k]?.label||k)}</span>`).join('')+`<span>→ 실제 저장 산출물의 방향 관계</span>`;
 bindNodes();renderDetail();applyTransform();
}

function bindNodes(){
 $$('.graph-node').forEach(g=>{
  const choose=()=>{selected=selected===g.dataset.id?null:g.dataset.id;render();};g.onclick=e=>{if(!g.dataset.moved)choose();delete g.dataset.moved;};g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}};
  g.onpointerdown=e=>{e.stopPropagation();const p=positions.get(g.dataset.id);drag={id:g.dataset.id,startX:e.clientX,startY:e.clientY,x:p.x,y:p.y};g.setPointerCapture(e.pointerId);};
  g.onpointermove=e=>{if(!drag||drag.id!==g.dataset.id)return;const dx=(e.clientX-drag.startX)/scale,dy=(e.clientY-drag.startY)/scale;if(Math.abs(dx)+Math.abs(dy)>3)g.dataset.moved='1';positions.set(drag.id,{x:drag.x+dx,y:drag.y+dy});renderGeometry();};g.onpointerup=()=>drag=null;
 });
}
function renderGeometry(){const ids=new Set($$('.graph-node').map(g=>g.dataset.id));for(const g of $$('.graph-node')){const p=positions.get(g.dataset.id);g.setAttribute('transform',`translate(${p.x},${p.y})`);}for(const path of $$('.edge')){const e=graph.edges.find(x=>x.id===path.dataset.edge);if(!e||!ids.has(e.source)||!ids.has(e.target))continue;const a=positions.get(e.source),b=positions.get(e.target),dx=Math.max(45,Math.abs(b.x-a.x)*.45);path.setAttribute('d',`M${a.x},${a.y} C${a.x+(b.x>=a.x?dx:-dx)},${a.y} ${b.x-(b.x>=a.x?dx:-dx)},${b.y} ${b.x},${b.y}`);}}

function prettyKey(key){return ({notice_id:'공고 ID',document_id:'문서 ID',question_id:'질문 ID',answer_sha256:'답변 해시',human_approval:'사람 승인',quality_notes:'품질 메모',character_start:'시작 offset',character_end:'끝 offset',review_status:'검수 상태',synthetic:'합성 데이터',status:'상태',reason:'판단 이유',follow_up:'추가 확인',scope:'범위',security_level:'보안 등급',chunks:'청크 수',filename:'파일명',text:'근거 원문',answer:'정본 답변',citation:'인용 번호',ranking_scores:'검색 순위',evidence_binding:'구간별 근거 연결'})[key]||key.replaceAll('_',' ');}
function valueHtml(value){if(value===null||value===undefined)return'기록 없음';if(typeof value==='boolean')return value?'예':'아니오';if(Array.isArray(value))return value.map(esc).join(' · ');if(typeof value==='object')return esc(JSON.stringify(value,null,2));return esc(value);}
function renderDetail(){
 const n=selected?byId.get(selected):null;$('#detail').hidden=!n;$('#detail-empty').hidden=!!n;if(!n)return;
 $('#detail-type').textContent=TYPES[n.type]?.label||n.type;$('#detail-access').textContent=`${n.access.level}${n.access.tenant_id?' · '+n.access.company_id:''}`;$('#detail-title').textContent=n.label;
 const status=n.properties.human_approval==='pending'?'사람 최종 승인 대기':n.properties.synthetic?'합성 시나리오 자료':'저장 산출물에서 확인됨';$('#detail-summary').textContent=status;
 const priority=['status','label','reason','text','answer','question_id','notice_id','filename','character_start','character_end'];const entries=Object.entries(n.properties).sort((a,b)=>(priority.indexOf(a[0])<0?99:priority.indexOf(a[0]))-(priority.indexOf(b[0])<0?99:priority.indexOf(b[0]))).slice(0,12);
 $('#detail-properties').innerHTML=entries.map(([k,v])=>`<div class="property"><b>${esc(prettyKey(k))}</b><span>${valueHtml(v)}</span></div>`).join('');
 const links=(adj.get(n.id)||[]).slice(0,20);$('#neighbors').innerHTML=links.map(x=>{const target=byId.get(x.node),t=TYPES[target?.type]||{color:'#64748b',label:target?.type};return `<button data-target="${esc(x.node)}" style="--node-color:${t.color}"><i></i><span>${esc(text(target?.label,28))}</span><small>${esc(EDGE_LABELS[x.edge.type]||x.edge.type)}</small></button>`;}).join('')||'<small>현재 권한과 필터에서 표시할 연결이 없습니다.</small>';
 $$('#neighbors button').forEach(b=>b.onclick=()=>{const target=byId.get(b.dataset.target);if(target){enabled.add(target.type);selected=target.id;renderFilters();render();}});
 $('#provenance').innerHTML=`<p><b>원본</b><br>${esc(n.provenance.source_path)}</p><p><b>JSON 위치</b><br>${esc(n.provenance.json_pointer)}</p><p><b>SHA-256</b><br>${esc(n.provenance.source_hash)}</p><p><b>Stable ID</b><br>${esc(n.stable_id)}</p>`;
}

function applyTransform(){$('#viewport').setAttribute('transform',`translate(${tx} ${ty}) scale(${scale})`);$('#zoom-value').textContent=Math.round(scale*100)+'%';}
function zoom(next,cx=750,cy=450){const old=scale;scale=Math.max(.45,Math.min(2.4,next));tx=cx-(cx-tx)*(scale/old);ty=cy-(cy-ty)*(scale/old);applyTransform();}
$('#graph').onwheel=e=>{e.preventDefault();const r=$('#graph').getBoundingClientRect(),cx=(e.clientX-r.left)/r.width*1500,cy=(e.clientY-r.top)/r.height*900;zoom(scale*(e.deltaY>0?.9:1.1),cx,cy);};
$('#graph').onpointerdown=e=>{if(e.target.closest('.graph-node'))return;pan={x:e.clientX,y:e.clientY,tx,ty};$('#graph').setPointerCapture(e.pointerId);};$('#graph').onpointermove=e=>{if(!pan)return;const r=$('#graph').getBoundingClientRect();tx=pan.tx+(e.clientX-pan.x)*1500/r.width;ty=pan.ty+(e.clientY-pan.y)*900/r.height;applyTransform();};$('#graph').onpointerup=()=>pan=null;
$('#fit').onclick=()=>{scale=1;tx=0;ty=0;applyTransform();};$('#zoom-in').onclick=()=>zoom(scale*1.15);$('#zoom-out').onclick=()=>zoom(scale*.87);
$$('.mode-tabs button').forEach(b=>b.onclick=()=>{mode=b.dataset.mode;enabled=new Set(MODES[mode].types);selected=null;positions.clear();renderFilters();render();});
$('#search').oninput=e=>{query=e.target.value.trim();selected=null;render();};document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement.tagName!=='INPUT'){e.preventDefault();$('#search').focus();}});
$('#all-types').onclick=()=>{enabled=new Set(MODES[mode].types);renderFilters();render();};
$$('[data-journey]').forEach(b=>b.onclick=()=>{const map={question:['evidence','Question'],span:['hallucination','HallucinationSpan'],company:['eligibility','Company']};[mode]=map[b.dataset.journey];enabled=new Set(MODES[mode].types);selected=graph.nodes.find(n=>n.type===map[b.dataset.journey][1])?.id||null;positions.clear();renderFilters();render();});
if(['viewer','bid_analyst','cost_analyst','bid_approver'].includes(initialParams.get('role')))$('#role').value=initialParams.get('role');
if(['C01','C02','C03','C04','C05'].includes(initialParams.get('company_id')))$('#company').value=initialParams.get('company_id');
$('#role').onchange=load;$('#company').onchange=()=>{if($('#role').value!=='viewer')load();};
await load().catch(e=>{$('#status').textContent='그래프 데이터를 불러오지 못했습니다.';console.error(e);});
