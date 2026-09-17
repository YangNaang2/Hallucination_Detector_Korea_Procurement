import fs from 'node:fs';
import path from 'node:path';

const OUT=path.resolve('output/visuals/astra-rag-easy');
fs.mkdirSync(OUT,{recursive:true});
const C={bg:'#f6f9fc',ink:'#14233a',sub:'#52647b',line:'#d8e2ee',white:'#fff',blue:'#2563eb',teal:'#0f9f8f',purple:'#5b5bd6',orange:'#f59e0b',red:'#e4584b',navy:'#1e4970',slate:'#334155',pBlue:'#eaf1ff',pTeal:'#e8f8f5',pPurple:'#efedff',pOrange:'#fff2df',pRed:'#ffe9e6'};
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const txt=(x,y,s,z=20,w=500,c=C.ink,a='start')=>`<text x="${x}" y="${y}" font-family="Noto Sans CJK KR, Noto Sans KR, sans-serif" font-size="${z}" font-weight="${w}" fill="${c}" text-anchor="${a}">${esc(s)}</text>`;
const lns=(x,y,a,z=18,g=31,c=C.sub,w=500)=>a.map((s,i)=>txt(x,y+i*g,s,z,w,c)).join('');
const arrow=(x1,y1,x2,y2)=>`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#91a4bb" stroke-width="3" marker-end="url(#arrow)"/>`;
function base(n,title,sub){return `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><defs><filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#16314f" flood-opacity=".1"/></filter><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#91a4bb"/></marker></defs><rect width="1920" height="1080" fill="${C.bg}"/><rect width="18" height="1080" fill="${C.teal}"/>${txt(74,70,`ASTRA · 권한형 RAG 쉬운 설명 · ${n}/4`,18,800,C.teal)}${txt(74,128,title,46,800)}${txt(74,169,sub,21,500,C.sub)}<line x1="74" y1="193" x2="1846" y2="193" stroke="${C.line}"/>`;}
function foot(s){return `<line x1="74" y1="1024" x2="1846" y2="1024" stroke="${C.line}"/>${txt(74,1055,s,14,500,C.sub)}${txt(1846,1055,'ASTRA · ko-LettuceDetect',14,700,C.navy,'end')}</svg>`;}
function card(x,y,w,h,title,items,accent=C.blue,opt={}){return `<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="18" fill="${opt.fill||C.white}" stroke="${C.line}" filter="url(#shadow)"/><rect x="${x}" y="${y}" width="8" height="${h}" rx="4" fill="${accent}"/>${txt(x+28,y+43,title,opt.titleSize||24,800)}${lns(x+28,y+84,items,opt.bodySize||18,opt.gap||32,opt.bodyColor||C.sub,opt.bodyWeight||500)}</g>`;}
function docIcon(x,y,color,label,lock=false){return `<g><path d="M${x} ${y}h118l38 38v150H${x}z" fill="#fff" stroke="${color}" stroke-width="5"/><path d="M${x+118} ${y}v38h38" fill="none" stroke="${color}" stroke-width="5"/><rect x="${x+25}" y="${y+63}" width="105" height="10" rx="5" fill="${color}" opacity=".35"/><rect x="${x+25}" y="${y+91}" width="88" height="10" rx="5" fill="${color}" opacity=".35"/><rect x="${x+25}" y="${y+119}" width="102" height="10" rx="5" fill="${color}" opacity=".35"/>${lock?`<rect x="${x+94}" y="${y+139}" width="48" height="38" rx="8" fill="${color}"/><path d="M${x+104} ${y+140}v-10a14 14 0 0128 0v10" fill="none" stroke="${color}" stroke-width="7"/>`:''}${txt(x+78,y+221,label,23,900,color,'middle')}</g>`;}
function save(n,s){fs.writeFileSync(path.join(OUT,`ASTRA_RAG_청킹검색생성_${String(n).padStart(2,'0')}.svg`),s);}

// page 1
{
 let s=base(1,'L1·L2·L3는 “문서 종류”이자 검색 권한의 경계다','같은 질문이라도 사용자의 회사와 역할에 따라 검색 가능한 문서 묶음이 먼저 달라진다.');
 s+=docIcon(130,255,C.blue,'L1 공개',false); s+=docIcon(495,255,C.teal,'L2 회사 내부',true); s+=docIcon(860,255,C.red,'L3 민감',true);
 s+=card(74,515,330,270,'L1 · 공개 공고',['167개 문서','3,002개 parent 청크','viewer 포함 모든 역할','공고문·RFP·과업·규격'],C.blue,{fill:C.pBlue,bodyColor:C.ink});
 s+=card(439,515,330,270,'L2 · 회사 자료',['34개 문서','159개 parent 청크','자기 회사 bid_analyst 이상','실적·인력·인증 자료'],C.teal,{fill:C.pTeal,bodyColor:C.ink});
 s+=card(804,515,330,270,'L3 · 민감 자료',['22개 문서','114개 parent 청크','자기 회사 cost/approver','원가·견적·승인 자료'],C.red,{fill:C.pRed,bodyColor:C.ink});
 s+=`<rect x="1190" y="235" width="656" height="550" rx="22" fill="#fff" stroke="${C.line}" filter="url(#shadow)"/>${txt(1224,283,'검색 전에 통과해야 하는 문',28,800)}`;
 const gates=[['로그인','authenticated'],['소속','membership_active'],['조직','tenant_id'],['회사','company_id'],['역할','allowed_roles'],['상황','scenario_id']];
 gates.forEach((d,i)=>{const x=1224+(i%2)*290,y=320+Math.floor(i/2)*112;s+=`<rect x="${x}" y="${y}" width="265" height="86" rx="14" fill="${i%2?C.pTeal:C.pBlue}"/>${txt(x+18,y+33,d[0],18,800,C.ink)}${txt(x+18,y+64,d[1],15,600,C.sub)}`;});
 s+=`<rect x="1224" y="665" width="556" height="84" rx="14" fill="${C.pOrange}"/>${txt(1250,701,'권한이 없으면 검색·LLM 호출 전에 차단',19,800,C.ink)}${txt(1250,729,'정상 access_denied를 답변 실패로 세지 않음',15,600,C.sub)}`;
 s+=card(74,825,1772,155,'전체 색인 규모',['223개 문서 → 3,275개 parent 청크. 읽을 수 없는 16개 문서는 색인에서 제외하되 실패 사유는 보존했다.','L1/L2/L3는 답변을 만든 뒤 가리는 장식이 아니라, 검색 후보를 만들기 전에 적용하는 보안 경계다.'],C.navy,{bodySize:20,gap:42,fill:'#eef4fa',bodyColor:C.ink});
 save(1,s+foot('근거: workstation-275/index_manifest.json · security_schema.py · rag_pilot.py 역할 정책'));
}

// page 2
{
 let s=base(2,'긴 문서는 parent 청크와 embedding window로 두 번 나눈다','사람이 읽는 근거 단위와 임베딩 모델이 처리하는 계산 단위를 분리해 원문 연결과 검색 성능을 함께 지킨다.');
 s+=`<rect x="74" y="235" width="370" height="275" rx="20" fill="#fff" stroke="${C.line}" filter="url(#shadow)"/>${docIcon(175,245,C.navy,'원본 문서',false)}${txt(259,495,'document_id · version · SHA-256',15,700,C.sub,'middle')}`;
 s+=arrow(455,372,520,372);
 s+=card(532,235,520,275,'① Parent chunk · 사람이 읽는 근거',['최대 1,800자','앞뒤 overlap 240자','문단·의미 단위를 가능한 한 보존','Unicode [start,end)로 원문 위치 연결','생성·인용에는 parent 원문 사용'],C.blue,{fill:C.pBlue,bodyColor:C.ink});
 s+=arrow(1064,372,1129,372);
 s+=card(1141,235,705,275,'② Embedding window · 모델 계산 단위',['multilingual-e5-small · 384차원','모델 입력 한도 512 token','window 460 token · stride 420','총 7,195개 window','parent 하나의 점수에 최대 3개 window 사용'],C.teal,{fill:C.pTeal,bodyColor:C.ink});
 s+=txt(74,570,'겹쳐 자르는 이유',28,800);
 s+=`<rect x="74" y="610" width="1772" height="180" rx="18" fill="#fff" stroke="${C.line}" filter="url(#shadow)"/>`;
 const segs=[['앞 문맥',74,370,C.pBlue,C.blue],['핵심 조건 A',380,470,C.pTeal,C.teal],['핵심 조건 B',790,470,C.pOrange,C.orange],['뒤 문맥',1200,370,C.pPurple,C.purple]];
 segs.forEach(d=>{s+=`<rect x="${d[1]+35}" y="650" width="${d[2]}" height="72" rx="14" fill="${d[3]}" stroke="${d[4]}"/>${txt(d[1]+35+d[2]/2,694,d[0],20,800,d[4],'middle')}`;});
 s+=arrow(470,748,715,748);s+=arrow(900,748,1145,748);
 s+=txt(610,755,'overlap 240자',16,700,C.sub,'middle');s+=txt(1040,755,'다음 window와 겹침',16,700,C.sub,'middle');
 s+=card(74,830,560,140,'경계 누락 완화',['중요 조건이 자르는 지점에 있어도','앞·뒤 window 중 하나에 남는다.'],C.orange,{bodySize:18,gap:32});
 s+=card(660,830,560,140,'원문 추적 유지',['청크마다 문서 ID와 문자 위치를 저장해','검색 결과를 실제 원문으로 되돌린다.'],C.purple,{bodySize:18,gap:32});
 s+=card(1246,830,600,140,'생성 근거는 읽기 쉽게',['검색 계산은 작은 window로 하되','LLM에는 선택된 parent 원문을 전달한다.'],C.red,{bodySize:18,gap:32});
 save(2,s+foot('Parent 1,800자/overlap 240자 · embedding 460/stride 420 · Unicode code point [start,end)'));
}

// page 3
{
 let s=base(3,'하이브리드 검색은 “정확한 단어”와 “비슷한 의미”를 함께 찾는다','한쪽 검색의 약점을 다른 쪽이 보완하고, RRF가 두 순위를 공통 parent 기준으로 합친다.');
 s+=`<circle cx="220" cy="350" r="112" fill="${C.pBlue}" stroke="${C.blue}" stroke-width="4"/><circle cx="170" cy="320" r="36" fill="none" stroke="${C.blue}" stroke-width="12"/><line x1="197" y1="347" x2="250" y2="400" stroke="${C.blue}" stroke-width="12" stroke-linecap="round"/>${txt(220,492,'사용자 질문',26,900,C.blue,'middle')}`;
 s+=arrow(340,350,425,350);
 s+=card(438,235,450,300,'A · Lexical 검색',['한국어 2글자 단위로 일치 탐색','영어·제품명·숫자는 exact 처리','금액·날짜·인증 코드에 강함','표현이 달라지면 놓칠 수 있음'],C.blue,{fill:C.pBlue,bodyColor:C.ink,bodySize:19,gap:41});
 s+=card(438,565,450,300,'B · Dense 검색',['질문과 window를 E5로 임베딩','단어가 달라도 의미가 비슷하면 탐색','패러프레이즈·설명형 질문에 강함','숫자·고유명사를 흐릴 수 있음'],C.teal,{fill:C.pTeal,bodyColor:C.ink,bodySize:19,gap:41});
 s+=arrow(900,385,1005,500);s+=arrow(900,715,1005,600);
 s+=`<rect x="1018" y="400" width="355" height="300" rx="26" fill="${C.pOrange}" stroke="${C.orange}" stroke-width="4" filter="url(#shadow)"/>${txt(1195,463,'RRF 순위 결합',30,900,C.orange,'middle')}${txt(1195,520,'각 검색의 순위만 이용',19,700,C.ink,'middle')}${txt(1195,560,'RRF(d)=Σ 1/(60+rank)',19,800,C.navy,'middle')}${txt(1195,610,'점수 크기가 달라도 결합 가능',17,600,C.sub,'middle')}${txt(1195,650,'같은 parent로 다시 집계',17,600,C.sub,'middle')}`;
 s+=arrow(1385,550,1465,550);
 s+=card(1478,350,368,400,'최종 검색 결과',['parent 최대 6개','중복 window는 한 근거로 통합','문서·회사·권한 metadata 유지','생성 prompt에는 최대 4개','citation [1]~[4] 부여'],C.red,{bodySize:19,gap:43});
 s+=card(74,890,1772,92,'쉽게 말하면',['키워드 검색은 “똑같이 쓰인 말”을, 임베딩 검색은 “뜻이 비슷한 말”을 찾는다. RRF는 두 추천 목록에서 자주 상위에 나온 근거를 우선한다.'],C.navy,{bodySize:20,gap:32,fill:'#eef4fa',bodyColor:C.ink});
 save(3,s+foot('현재 구현은 lexical+dense+RRF이며, 별도 그래프 DB 기반 GraphRAG가 아니다.'));
}

// page 4 with real screenshot
{
 const shotPath=path.resolve('project-docs/데모개선/2026-09-14/rag-observatory.png');
 // The repository asset has a .png suffix but its actual bytes are JPEG/JFIF.
 const shot=fs.existsSync(shotPath)?`data:image/jpeg;base64,${fs.readFileSync(shotPath).toString('base64')}`:'';
 let s=base(4,'검색된 근거만 로컬 LLM에 넣고 답변·인용을 함께 저장한다','권한 확인부터 검색, 근거 선택, 생성, 의심 구절 검토까지 한 요청의 추적 정보를 보존한다.');
 const flow=[
  ['① 세션·ACL','회사·역할·시나리오',C.blue],['② 허용 문서 검색','lexical+dense',C.teal],['③ RRF·parent','상위 6개 근거',C.orange],['④ Prompt 구성','최대 4개·인용번호',C.purple],['⑤ Qwen3-4B','로컬 GPU 생성',C.red],['⑥ 저장·검수','답변·근거·hash',C.navy]
 ];
 flow.forEach((d,i)=>{const x=74+i*295;s+=`<rect x="${x}" y="225" width="270" height="118" rx="16" fill="${d[2]}"/>${txt(x+135,268,d[0],20,900,'#fff','middle')}${txt(x+135,306,d[1],15,600,'#edf5ff','middle')}`;if(i<5)s+=arrow(x+273,284,x+290,284);});
 s+=`<rect x="74" y="382" width="910" height="548" rx="20" fill="#fff" stroke="${C.line}" filter="url(#shadow)"/>${shot?`<image href="${shot}" x="102" y="410" width="854" height="492" preserveAspectRatio="xMidYMid meet"/>`:''}`;
 s+=card(1014,382,832,235,'로컬 생성 설정',['Qwen3-4B · GGUF Q4_K_M','context 4,096 · max tokens 768','temperature 0.7 · top_p 0.8 · top_k 20','RTX A5000 · 37/37 layers GPU offload','기록된 peak GPU memory 5,588 MiB'],C.red,{bodySize:19,gap:35});
 s+=card(1014,645,400,285,'Prompt에 들어가는 것',['사용자 질문','허용된 근거 parent 원문','[1]~[4] citation 번호','답변 형식 지시'],C.teal,{bodySize:18,gap:42,fill:C.pTeal,bodyColor:C.ink});
 s+=card(1440,645,406,285,'Prompt에 넣지 않는 것',['평가 기대답','환각 정답 라벨','예상 모델 판정','다른 회사의 비허용 문서'],C.orange,{bodySize:18,gap:42,fill:C.pOrange,bodyColor:C.ink});
 s+=`<rect x="74" y="951" width="1772" height="45" rx="12" fill="#eef4fa"/>${txt(102,981,'저장 결과: question_id · actual_answer · citation · evidence chunk/offset · prompt/config/code/model hash · 실행 상태',18,800,C.navy)}`;
 save(4,s+foot('실제 데모 화면과 구조를 함께 표시 · 저장 답변 재생과 실시간 생성 모드는 UI에서 구분'));
}
console.log(`generated 4 SVGs in ${OUT}`);
