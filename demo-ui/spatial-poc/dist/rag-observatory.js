import {createSavedSource,canApplyResult} from './rag-source.mjs';
import {renderAnswer,escapeHTML as esc} from './rag-render.mjs';
import {createGraph} from './rag-graph.js';
const $=s=>document.querySelector(s);let data,notices,source,graph,bid,current=null,epoch=0,controller=null;
function openDialog(id){const d=$(id);if(!d.open)d.showModal();}
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>b.closest('dialog').close());
function info(title,html){$('#info-title').textContent=title;$('#info-content').innerHTML=html;openDialog('#info-dialog');}
function clearAnswer(){current=null;$('#answer').innerHTML='<div class="empty"><span>↗</span><h3>예시 질문으로 시작하세요</h3><p>저장 결과를 선택하면 답변과 입력 근거를 확인할 수 있습니다.</p></div>';$('#answered-question').textContent='';$('#quality').textContent='';$('#highlights').checked=false;['copy','sources','highlights'].forEach(id=>$('#'+id).disabled=true);$('#source-dialog').close();graph?.setCase(null);}
function chooseNotice(id,push=true){
 const n=notices.find(n=>n.id===id);if(!n)return;
 controller?.abort();epoch++;bid=id;clearAnswer();$('#question').value='';$('#notice-title').textContent=n.title;$('#notice-title').title=n.title;
 $('#notice-link').href='public-notices.html?bid='+encodeURIComponent(bid);
 const examples=source.examples(bid);$('#examples').innerHTML=examples.length?examples.map(c=>'<button type="button" data-example="'+esc(c.id)+'">'+esc(c.question)+'</button>').join(''):'<p>이 공고에는 공개 저장 예시가 없습니다. 공고 요건은 지도에서 확인할 수 있습니다.</p>';
 if(!examples.length)$('#answer').innerHTML='<div class="empty"><span>↗</span><h3>저장 답변이 없는 공고입니다</h3><p>공고 지도에서 요건을 살펴보거나, 저장 예시가 있는 공고를 선택해 주세요.</p></div>';
 $('#status').textContent=examples.length?'예시 질문을 선택하고 저장 답변을 확인하세요.':'생성 서버 미연결 · 새 답변 생성은 아직 사용할 수 없습니다.';
 $('#notice-dialog').close();const u=new URL(location.href);u.searchParams.set('bid',bid);if(push)history.pushState({bid},'',u);else history.replaceState({bid},'',u);
}
function render(){if(!current)return;$('#answer').innerHTML=renderAnswer(current.answer,current.contexts,current.spans,$('#highlights').checked);$('#answered-question').textContent=current.question;
 $('#quality').innerHTML=current.quality_notes.map(t=>'<p>추가 확인 · '+esc(t)+'</p>').join('');}
function evidence(i){if(!current||!current.contexts[i])return;const c=current.contexts[i];graph.select(i);
 $('#source-nav').innerHTML=current.contexts.map((c,j)=>'<button data-source="'+j+'" aria-pressed="'+(i===j)+'">'+(c.citation===null?'추가 자료':'근거 ['+c.citation+']')+'</button>').join('');
 $('#evidence').innerHTML='<p class="badge">'+(c.scope==='prompt_context'?'생성 시 사용한 근거':'사후 추가 자료 · 생성 입력에 없었음')+'</p><h3>'+esc(c.filename)+'</h3><p class="muted">아래 구간이 답변의 모든 주장을 지지한다고 보장하지 않습니다.</p><pre>'+esc(c.text)+'</pre><details><summary>추적 정보</summary><code>문서 '+esc(c.document_id)+'</code><code>청크 '+esc(c.chunk_id)+'</code><p>버전 '+esc(c.document_version)+' · L1</p><p>정본 문자 ['+c.text_start+', '+c.text_end+') · Unicode 코드 포인트 · 0부터, 끝 제외</p></details>';
 openDialog('#source-dialog');
}
$('#ask-form').onsubmit=async e=>{e.preventDefault();const question=$('#question').value.trim();if(!question){$('#status').textContent='질문을 입력하거나 예시를 선택해 주세요.';$('#question').focus();return;}
 const requestBid=bid,requestEpoch=++epoch;controller?.abort();controller=new AbortController();clearAnswer();
 try{const result=await source.ask({bid:requestBid,question},controller.signal);if(!canApplyResult(requestEpoch,epoch,requestBid,bid))return;current=result;render();graph.setCase(current);['copy','sources','highlights'].forEach(id=>$('#'+id).disabled=false);$('#status').textContent='저장 답변 표시 · '+(current.quality_notes.some(t=>t.includes('잘림'))?'출력 잘림 · 추가 확인 필요':current.quality_notes.length?'추가 확인 필요 · 검수 메모 참조':'새 검색·생성은 실행하지 않았습니다.');}
 catch(error){if(error.name!=='AbortError')$('#status').textContent=error.message;}
};
$('#examples').onclick=e=>{const b=e.target.closest('[data-example]');if(!b)return;$('#question').value=data.cases.find(c=>c.id===b.dataset.example).question;$('#status').textContent='예시 선택됨 · 저장 답변 확인을 눌러 주세요.';$('#run').focus();};
$('#highlights').onchange=render;$('#sources').onclick=()=>evidence(0);
$('#answer').onclick=e=>{const b=e.target.closest('[data-citation]');if(b)evidence(current.contexts.findIndex(c=>c.citation===Number(b.dataset.citation)));};
$('#source-nav').onclick=e=>{const b=e.target.closest('[data-source]');if(b)evidence(Number(b.dataset.source));};
$('#copy').onclick=async()=>{if(!current)return;try{await navigator.clipboard.writeText(current.answer);$('#status').textContent='정본 답변을 복사했습니다.';}catch{$('#status').textContent='클립보드 접근이 거부되었습니다. 답변을 선택해 직접 복사해 주세요.';}};
function noticeOptions(){const q=$('#notice-search').value.toLowerCase();$('#notice-options').innerHTML=notices.filter(n=>(n.id+n.title).toLowerCase().includes(q)).map(n=>'<button data-bid="'+esc(n.id)+'">'+esc(n.title)+'<small>'+esc(n.id)+(source.examples(n.id).length?' · 저장 예시 있음':'')+'</small></button>').join('')||'<p>일치하는 공고가 없습니다.</p>';}
$('#change-notice').onclick=()=>{noticeOptions();openDialog('#notice-dialog');$('#notice-search').focus();};$('#notice-search').oninput=noticeOptions;
$('#notice-options').onclick=e=>{const b=e.target.closest('[data-bid]');if(b)chooseNotice(b.dataset.bid);};
window.onpopstate=()=>chooseNotice(new URL(location.href).searchParams.get('bid')||notices[0].id,false);
$('#collapse').onclick=()=>{$('#graph-body').hidden=!$('#graph-body').hidden;$('#collapse').textContent=$('#graph-body').hidden?'펼치기':'접기';$('#collapse').setAttribute('aria-expanded',String(!$('#graph-body').hidden));graph.syncFlow();};
function expand(value){$('.graph').classList.toggle('expanded',value);$('#expand').setAttribute('aria-pressed',String(value));$('#expand').textContent=value?'축소':'확대';if(value){$('#graph-body').hidden=false;$('#collapse').textContent='접기';$('#collapse').setAttribute('aria-expanded','true');}graph.syncFlow();}
$('#expand').onclick=()=>expand(!$('.graph').classList.contains('expanded'));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&$('.graph').classList.contains('expanded')){expand(false);$('#expand').focus();}});
$('#connection').onclick=()=>info('연결 상태','<p class="badge">저장 결과 모드 · 생성 서버 미연결</p><p>자유 질문을 처리하는 서버에 연결하지 않았습니다.</p><table><tr><th>모델</th><th>이 화면의 상태</th></tr><tr><td>Qwen3-4B</td><td>기존 실행 결과 표시만 가능</td></tr><tr><td>Gemma</td><td>미연결 · 실행 선택 불가</td></tr></table><details><summary>연결 설계</summary><p>로컬 설치 여부와 서버 연결은 다릅니다. 현재 모델 프로세스나 외부 API를 호출하지 않습니다. 향후 서버 계약, 세션 인증, 취소 및 스트림 검증을 연결해야 합니다.</p></details>');
$('#data-button').onclick=()=>{const s=data.stats;info('데이터 현황','<p>기존 파일럿 기록입니다. 이 화면에서 새로 실행한 수가 아닙니다.</p><table><tr><td>공고</td><td>51건</td></tr><tr><td>전체 색인 문서 / 청크</td><td>'+s.documents+' / '+s.chunks+'</td></tr><tr><td>기존 생성 답변 / 정상 차단</td><td>'+s.generated+' / '+s.denied+'</td></tr><tr><td>공개 재생 예시</td><td>'+data.cases.length+'개 · L1만</td></tr></table><details><summary>기술 정보</summary><p>기준 실행 '+esc(data.source_revision)+' · 사람 승인 pending</p><p>L2·L3 본문은 이 화면에 제공하지 않습니다. 이 재생 JSON은 검색 코퍼스가 아닙니다.</p><a href="rag-pipeline.svg">파이프라인 구조도</a></details>');};
$('#settings-button').onclick=()=>info('권한 시연 설정','<p class="badge">실제 인증 기능 아님</p><p>현재 공개 L1 문서만 볼 수 있습니다. 회사·역할 선택으로 L2·L3 권한을 부여하지 않습니다.</p><label>회사 문맥 <select disabled><option>공개 자료 검토</option></select></label><label>역할 <select disabled><option>미인증 · 공개 L1</option></select></label><p class="muted">회사별 문서 접근은 향후 서버 세션과 권한 필터 연결 후 제공됩니다. 팀 내부 라벨 검수 화면은 별도 파일입니다.</p>');
$('#states-button').onclick=()=>{info('UI 상태 시연','<p class="badge">화면 상태 예제 · 실제 RAG 실행 아님</p><div><button data-state="loading">로딩</button><button data-state="error">오류</button><button data-state="missing">자료부족</button></div><div id="state-preview" role="status">상태를 선택하세요.</div>');};
$('#info-content').onclick=e=>{const s=e.target.closest('[data-state]')?.dataset.state;if(!s)return;$('#state-preview').innerHTML=({loading:'<p>시연: 답변을 기다리는 화면</p><button data-state="cancel">취소</button>',cancel:'<p>시연: 요청이 취소되었습니다.</p>',error:'<p>시연: 연결 오류가 발생했습니다.</p><button data-state="loading">재시도 시연</button>',missing:'<p>시연: 제공된 문서만으로 확인하기 어렵습니다. 추가 자료가 필요합니다.</p>'})[s];};
try{const responses=await Promise.all(['rag-observatory.json','public-notices.json'].map(async u=>{const r=await fetch(u);if(!r.ok)throw Error('자료 응답 오류');return r.json();}));[data,{records:notices}]=responses;source=createSavedSource(data);
graph=createGraph({data,onSource:evidence,onNotice:chooseNotice,onAnswer:()=>$('#answer').scrollIntoView({block:'nearest'}),onDocument:d=>{if(!d)return;$('#source-nav').innerHTML='';$('#evidence').innerHTML='<h3>'+esc(d.filename)+'</h3><p>공개 문서 정보입니다. 전체 원문은 이 서버에 제공되지 않습니다.</p><details><summary>추적 정보</summary><code>'+esc(d.document_id)+'</code><p>청크 '+d.chunks+'개</p></details>';openDialog('#source-dialog');}});
const requested=new URL(location.href).searchParams.get('bid');chooseNotice(notices.some(n=>n.id===requested)?requested:data.cases[0].bid,false);
if(requested&&!notices.some(n=>n.id===requested))$('#status').textContent='해당 공고를 찾지 못해 저장 예시 공고를 열었습니다.';
}catch(e){$('#status').textContent='자료를 불러오지 못했습니다. 로컬 서버와 파일을 확인한 뒤 새로고침해 주세요.';console.error(e);}
