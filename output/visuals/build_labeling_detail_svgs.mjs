import fs from 'node:fs';
import path from 'node:path';

const OUT = path.resolve('output/visuals/astra-labeling-detail');
fs.mkdirSync(OUT, { recursive: true });

const C = {
  bg:'#f6f9fc', ink:'#14233a', sub:'#52647b', line:'#d8e2ee', white:'#ffffff',
  blue:'#2563eb', teal:'#0f9f8f', purple:'#5b5bd6', orange:'#f59e0b', red:'#e4584b', navy:'#1e4970', slate:'#334155',
  paleBlue:'#eaf1ff', paleTeal:'#e8f8f5', palePurple:'#efedff', paleOrange:'#fff2df', paleRed:'#ffe9e6'
};

const esc = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
function text(x,y,value,size=20,weight=500,color=C.ink,anchor='start') {
  return `<text x="${x}" y="${y}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}" font-family="Noto Sans CJK KR, Noto Sans KR, sans-serif">${esc(value)}</text>`;
}
function lines(x,y,items,size=18,gap=31,color=C.sub,weight=500) {
  return items.map((s,i)=>text(x,y+i*gap,s,size,weight,color)).join('');
}
function card(x,y,w,h,title,items,accent=C.blue,opts={}) {
  const titleSize=opts.titleSize||23, bodySize=opts.bodySize||18, gap=opts.gap||31;
  return `<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="18" fill="${opts.fill||C.white}" stroke="${C.line}" filter="url(#shadow)"/><rect x="${x}" y="${y}" width="8" height="${h}" rx="4" fill="${accent}"/>${text(x+28,y+42,title,titleSize,800,C.ink)}${lines(x+28,y+80,items,bodySize,gap,opts.bodyColor||C.sub,opts.bodyWeight||500)}</g>`;
}
function pill(x,y,w,label,fill,color='#fff') { return `<rect x="${x}" y="${y}" width="${w}" height="42" rx="12" fill="${fill}"/>${text(x+w/2,y+29,label,18,800,color,'middle')}`; }
function arrow(x1,y1,x2,y2){return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#91a4bb" stroke-width="3" marker-end="url(#arrow)"/>`;}
function base(page,titleText,subtitleText,section='환각 구간 라벨링 상세 설명') {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><defs><filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#16314f" flood-opacity="0.10"/></filter><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#91a4bb"/></marker></defs><rect width="1920" height="1080" fill="${C.bg}"/><rect width="18" height="1080" fill="${C.teal}"/>${text(74,70,`ASTRA · ${section} · ${page}/9`,18,800,C.teal)}${text(74,128,titleText,46,800,C.ink)}${text(74,169,subtitleText,21,500,C.sub)}<line x1="74" y1="193" x2="1846" y2="193" stroke="${C.line}"/>`;
}
function footer(note){return `<line x1="74" y1="1024" x2="1846" y2="1024" stroke="${C.line}"/>${text(74,1055,note,14,500,C.sub)}${text(1846,1055,'ASTRA · ko-LettuceDetect',14,700,C.navy,'end')}</svg>`;}
function save(n,body){fs.writeFileSync(path.join(OUT,`ASTRA_환각구간라벨링_상세_${String(n).padStart(2,'0')}.svg`),body);}

// 1. overview
{
 let s=base(1,'정본 답변에서 서비스 경고까지, 한 줄로 이어진다','각 단계가 이전 단계의 원본·근거·상태를 보존해야 결과를 다시 검증할 수 있다.');
 const xs=[74,293,512,731,950,1169,1388,1607];
 const data=[
  ['① 정본 고정','질문·답변·해시'],['② 근거 복원','실제 입력 chunk'],['③ 주장 분해','최소 의미 단위'],['④ 근거 대조','지지·모순·부재'],
  ['⑤ 구간 표시','문자 [start,end)'],['⑥ 사람 조정','보류·승인 분리'],['⑦ 모델 평가','KLUE·임계값'],['⑧ UI 사용','강조·근거 이동']
 ];
 data.forEach((d,i)=>{s+=`<rect x="${xs[i]}" y="245" width="190" height="120" rx="16" fill="${[C.blue,C.teal,C.purple,C.orange,C.red,C.navy,C.slate,C.blue][i]}"/>${text(xs[i]+95,286,d[0],20,800,'#fff','middle')}${text(xs[i]+95,326,d[1],15,600,'#eaf2ff','middle')}`; if(i<7)s+=arrow(xs[i]+192,305,xs[i+1]-8,305);});
 s+=card(74,414,550,245,'변하지 않아야 하는 것',['• 실제 생성 답변 문자열과 줄바꿈','• 당시 모델에 제공된 근거와 인용 순서','• 문서·청크·답변의 SHA-256','• Unicode 문자 위치와 질문 ID'],C.blue);
 s+=card(650,414,570,245,'판단하며 추가되는 것',['• 주장별 오류 유형과 최소 구간','• 구절을 지지/반박하는 근거 ID','• 판단 이유와 검수자의 처리','• 보류·승인·학습 가능 상태'],C.teal);
 s+=card(1246,414,600,245,'서로 섞으면 안 되는 것',['• 모델 예측 ↔ 정답 라벨','• 에이전트 초안 ↔ 사람 승인','• 인용 오류 ↔ 내용 환각','• 품질 문제 ↔ 근거 모순'],C.red);
 s+=card(74,690,1772,270,'왜 이 순서가 필요한가?',['답변을 먼저 바꾸거나 나중에 찾은 근거를 당시 입력처럼 넣으면 평가 대상 자체가 달라진다.','구간 위치가 틀리면 모델 학습과 화면 강조가 다른 글자를 가리킨다.','애매한 문장을 정상으로 세면 오탐은 줄어 보이지만 실제 성능이 좋아진 것은 아니다.','따라서 정본 → 근거 → 구절 → 검수 → 승인 → 학습/평가 순서를 고정한다.'],C.orange,{bodySize:20,gap:39,fill:C.paleOrange,bodyColor:C.ink});
 save(1,s+footer('근거: pilot-25 GUIDELINES, detector300 입력·라벨·검증 코드, results-v1~v6 README'));
}

// 2. canonical inputs
{
 let s=base(2,'1단계 · 평가 대상을 먼저 얼린다','질문 300건 중 생성 답변 295건과 정상 접근 차단 5건을 다른 평가 대상으로 관리한다.');
 s+=card(74,230,540,260,'300개 평가 레코드',['질문 ID와 회사·공고·시나리오','질문·기대답·근거 연결','공고 그룹 기준 분할 정보','평가 정답은 생성 요청에서 제외'],C.blue);
 s+=card(640,230,540,260,'295개 detector 대상',['실제 생성 답변 actual_answer','생성 당시 prompt context','실제 선택 evidence 목록','answer/context/evidence hash'],C.teal);
 s+=card(1206,230,640,260,'5개 정상 접근 차단',['LLM 호출 전에 access_denied','답변 실패나 빈 답변이 아님','환각 탐지 학습·추론에서 제외','별도 보안 정책 검사로 보존'],C.red);
 s+=text(74,548,'입력 무결성 검사',28,800,C.ink);
 const checks=[
  ['ID','300개 고유·누락 없음'],['정본','답변 문자열 byte/문자 일치'],['근거','chunk ID·citation·hash 연결'],['분리','정답·라벨이 생성 입력에 없음'],['차단','5건 detector_target=false'],['재개','설정 hash가 같을 때만 skip']
 ];
 checks.forEach((d,i)=>{const x=74+i*295;s+=`<rect x="${x}" y="585" width="270" height="130" rx="15" fill="${i%2?C.paleTeal:C.paleBlue}" stroke="${C.line}"/>${pill(x+18,603,82,d[0],i%2?C.teal:C.blue)}${text(x+18,678,d[1],17,700,C.ink)}`;});
 s+=card(74,758,1772,210,'핵심 불변조건',['정본 답변을 다시 생성하거나 맞춤법을 고친 뒤 같은 ID로 덮어쓰지 않는다. 새 답변은 새 run_id로 저장한다.','다른 설정의 결과를 이어붙이지 않는다. resume은 입력·모델·코드·설정 식별자가 모두 같은 경우에만 허용한다.','접근 차단을 정상 답변으로 포함하거나, 미검수 답변을 정상으로 간주하지 않는다.'],C.navy,{bodySize:20,gap:42,fill:'#eef4fa',bodyColor:C.ink});
 save(2,s+footer('실행 시작점: python procurement-pipeline/prepare_detector300_handoff.py --check'));
}

// 3. evidence reconstruction
{
 let s=base(3,'2단계 · “당시 모델이 본 근거”를 복원한다','정답 문서 전체가 아니라 생성 시점에 실제 전달된 citation·chunk·범위를 기준으로 지지 여부를 판단한다.');
 s+=card(74,230,520,315,'Prompt context에서 복원',['[1] … [자료 1 끝] 블록 식별','citation 번호와 evidence 순서 확인','chunk_id·text_sha256 대조','context_start/end 위치 계산','source_start/end 원문 위치 연결'],C.purple);
 s+=arrow(606,387,664,387);
 s+=card(676,230,520,315,'답변 주장과 연결',['질문이 요구한 대상·시점 확인','주체·숫자·날짜·금액 추출','자격·의무·가능·예외 범위 확인','직접 지지·명시 모순·근거 부재','판단 이유와 evidence_ids 기록'],C.orange);
 s+=arrow(1208,387,1266,387);
 s+=card(1278,230,568,315,'사후 자료는 별도 취급',['나중에 찾은 원문은 reference_only','검색 누락과 생성 환각을 구분','후대 문서로 당시 답변을 소급 정당화 금지','원문끼리 충돌하면 임의 합성 금지','법률 결론은 전문가 확인 대상으로 보류'],C.red);
 s+=text(74,605,'비교할 때 보는 네 층',28,800,C.ink);
 const layers=[
  ['질문','무엇을 묻고 있는가?','대상·범위·요구 형식'],
  ['근거','모델이 무엇을 보았는가?','citation·chunk·기준일'],
  ['답변','어떤 주장을 했는가?','주체·조건·수치·결론'],
  ['시나리오','그 시점에 유효한가?','회사·공고·역할·날짜']
 ];
 layers.forEach((d,i)=>{const x=74+i*443;s+=`<rect x="${x}" y="645" width="417" height="205" rx="18" fill="${[C.paleBlue,C.paleTeal,C.paleOrange,C.palePurple][i]}" stroke="${C.line}"/>${pill(x+22,669,105,d[0],[C.blue,C.teal,C.orange,C.purple][i])}${text(x+22,754,d[1],21,800,C.ink)}${text(x+22,795,d[2],17,600,C.sub)}`;});
 s+=`<rect x="74" y="879" width="1772" height="90" rx="18" fill="#eef4fa" stroke="${C.line}" filter="url(#shadow)"/><rect x="74" y="879" width="8" height="90" rx="4" fill="${C.navy}"/>`;
 s+=text(103,915,'판정 기준의 중심',18,800,C.navy);
 s+=text(103,950,'“현실에서 참인가?”보다 “생성 입력 근거가 이 주장을 지지하는가?”를 먼저 판정한다.',22,800,C.ink);
 save(3,s+footer('근거 anchor에는 citation, chunk_id, text_sha256, quote, context/source start·end를 함께 기록'));
}

// 4. decision tree
{
 let s=base(4,'3단계 · 각 주장에 같은 판정 순서를 적용한다','한 문장에 정상 표현과 오류 표현이 섞일 수 있으므로 주장 단위로 분해한 뒤 아래 순서로 판단한다.');
 const steps=[
  [74,238,320,'① 근거가 직접 지지?','예 → 정상(O)','바꿔 말해도 의미가 같으면 정상',C.teal],
  [430,238,320,'② 근거와 명시적 모순?','예 → CONTRADICTION','허용↔금지, 있음↔없음, 주체 변경',C.red],
  [786,238,320,'③ 지지 근거가 없음?','예 → UNSUPPORTED','근거 밖 수치·조건·단정',C.orange],
  [1142,238,320,'④ 인용 연결만 틀림?','예 → CITATION_ERROR','없는 [3], 잘못된 페이지·출처',C.blue],
  [1498,238,348,'⑤ 의미·범위가 모호?','예 → UNCERTAIN/HOLD','정상으로 세지 않고 재검토',C.purple]
 ];
 steps.forEach(d=>{s+=card(d[0],d[1],d[2],225,d[3],[d[4],d[5]],d[6],{bodySize:17,gap:38});});
 s+=text(74,525,'환각과 분리하는 품질 문제',28,800,C.ink);
 const qs=[
  ['누락','필요한 답을 쓰지 않음','존재하지 않는 구절을 환각 span으로 만들지 않음'],
  ['잘림','출력 길이 때문에 문장이 끝나지 않음','finish_reason·토큰 한도 문제로 별도 기록'],
  ['반복','같은 내용을 여러 번 출력','반복 자체는 품질; 거짓이면 각 위치를 라벨'],
  ['검색 누락','중요 근거가 모델 입력에 없음','생성 오류와 검색 오류를 분리'],
  ['권한 차단','정책상 문서를 볼 수 없음','정상 보안 결과로 별도 평가']
 ];
 qs.forEach((d,i)=>{const x=74+i*354;s+=`<rect x="${x}" y="565" width="328" height="205" rx="16" fill="${i%2?C.paleTeal:C.white}" stroke="${C.line}"/>${text(x+22,607,d[0],22,800,C.ink)}${text(x+22,648,d[1],17,700,C.sub)}${text(x+22,696,d[2],15,500,C.sub)}`;});
 s+=card(74,805,1772,165,'중요한 예외',['일반 상식·상투적 유보 문구를 무조건 환각으로 칠하지 않는다. 반대로 수치 계산이 맞아도 그 수치를 적용한 대상·기간·VAT·마진 의미가 틀리면 해당 역할 표현을 표시한다.','한 주장에 라벨이 겹치거나 원문끼리 충돌하면 억지로 하나로 합치지 않고 조정 대상으로 남긴다.'],C.orange,{bodySize:19,gap:42,fill:C.paleOrange,bodyColor:C.ink});
 save(4,s+footer('판정 코드: CONTRADICTION · UNSUPPORTED · CITATION_ERROR · UNCERTAIN / 품질 메모 별도'));
}

// 5. span boundary
{
 let s=base(5,'4단계 · 틀린 의미를 유지하는 최소 구간만 표시한다','정확한 구간은 학습 정답이자 화면의 형광펜 위치이므로 원시 답변 문자열과 완전히 일치해야 한다.');
 s+=card(74,230,850,250,'구간 경계 원칙',['• 0부터 시작하는 Unicode code point 위치','• [start,end): start 포함, end 직전까지','• Markdown·공백·줄바꿈(LF)·오타를 그대로 보존','• Excel 행 번호·UTF-8 byte·JS UTF-16 index와 다름','• 같은 오류가 반복되면 실제 출현 위치마다 기록'],C.blue);
 s+=card(950,230,896,250,'최소 구간 선택 원칙',['• 맞는 주변 문장을 통째로 칠하지 않음','• 첫 결론이 틀리고 뒤 설명이 맞으면 첫 결론만','• 숫자는 맞고 적용 의미가 틀리면 의미가 드러나는 구절','• 다른 오류가 겹치면 별도 span 또는 조정 대상','• 답변에 없는 “누락 내용”을 가상 span으로 만들지 않음'],C.teal);
 s+=text(74,545,'구체적인 예',28,800,C.ink);
 s+=`<rect x="74" y="578" width="1772" height="230" rx="20" fill="#fff" stroke="${C.line}" filter="url(#shadow)"/>`;
 s+=text(105,625,'답변 원문',18,800,C.navy); s+=text(240,625,'“이 공고는 공동수급으로',25,700,C.ink); s+=`<rect x="581" y="592" width="250" height="44" rx="8" fill="${C.paleRed}"/>`;s+=text(595,625,'참여할 수 있습니다.',25,800,'#b63b32');s+=text(838,625,'”',25,700,C.ink);
 s+=text(105,681,'저장 구간',18,800,C.navy);s+=text(240,681,'start=14 · end=25 · quote="참여할 수 있습니다."',21,700,C.ink);
 s+=text(105,736,'저장 이유',18,800,C.navy);s+=text(240,736,'“공동수급”이라는 주제는 맞고, 허용 여부를 반대로 말한 서술만 모순이기 때문',20,600,C.sub);
 s+=card(74,840,545,130,'문자열 검증',['actual_answer[start:end] == quote','하나라도 다르면 저장 실패'],C.red,{bodySize:18,gap:31});
 s+=card(646,840,570,130,'토큰 변환 검증',['문자 span ↔ tokenizer offset 정합','window 잘림·마스크 확인'],C.purple,{bodySize:18,gap:31});
 s+=card(1243,840,603,130,'화면 검증',['저장 좌표와 UI 형광펜이 동일','원문 근거 위치로 이동 가능'],C.orange,{bodySize:18,gap:31});
 save(5,s+footer('정확한 구간 경계가 없으면 문자 F1, exact-span F1, 모델 학습과 UI 강조가 모두 흔들린다.'));
}

// 6. review states
{
 let s=base(6,'5단계 · 초안, 사람 의견, 조정안, 최종 승인을 분리한다','누가 어떤 근거로 바꿨는지 추적하고, 승인 전 라벨을 학습 정답으로 내보내지 않는다.');
 const stages=[
  ['A. 에이전트 초안','근거 대조 후보 span','예측 결과와 분리','human_approval=pending',C.blue],
  ['B. 사람 제출 의견','동의·수정·재검토','원본 파일·해시 보존','서로 다른 문항 배정 가능',C.teal],
  ['C. 통합 조정안','구·신 라벨과 이유','근거 anchor·출처 기록','보류/품질 메모 분리',C.orange],
  ['D. 최종 사람 승인','승인자·시각·대상 span','approved_spans 확정','training_ready=true 가능',C.red]
 ];
 stages.forEach((d,i)=>{const x=74+i*443;s+=card(x,235,417,260,d[0],d.slice(1,4),d[4],{bodySize:17,gap:42});if(i<3)s+=arrow(x+419,365,x+438,365);});
 s+=text(74,555,'현재 25문항 검수의 실제 상태',28,800,C.ink);
 const stats=[['25','검수 문항'],['68','기존 구절','동의 65 · 수정 3'],['88','통합 구절'],['70','채택 제안'],['16','보류'],['0','최종 승인']];
 stats.forEach((d,i)=>{const x=74+i*295;s+=`<rect x="${x}" y="590" width="270" height="130" rx="16" fill="${i===5?C.paleRed:(i%2?C.paleTeal:C.paleBlue)}" stroke="${C.line}"/>${text(x+22,637,d[0],34,900,i===5?C.red:(i%2?C.teal:C.blue))}${text(x+22,673,d[1],18,800,C.ink)}${d[2]?text(x+22,702,d[2],14,500,C.sub):''}`;});
 s+=card(74,758,860,205,'왜 검수자 간 일치도를 아직 계산하지 않았나?',['팀원별로 서로 다른 문항을 맡아 같은 사례를 독립적으로 이중 검수하지 않았다.','따라서 IAA를 만들 수 없으며, 25문항은 의도 표본이자 개발 노출 자료다.'],C.purple,{bodySize:19,gap:43,fill:C.palePurple,bodyColor:C.ink});
 s+=card(960,758,886,205,'승인 전 처리',['UNCERTAIN·HOLD·미검수 토큰은 정상(O)으로 채우지 않는다.','학습에서는 마스킹/제외하고, 평가에서는 unknown 또는 보류로 공개한다.'],C.red,{bodySize:19,gap:43,fill:C.paleRed,bodyColor:C.ink});
 save(6,s+footer('현재 상태: submitted review 접수 완료 · final human approval pending · training_ready=false'));
}

// 7. schema and validation
{
 let s=base(7,'6단계 · 사람이 읽은 결과를 재현 가능한 데이터로 저장한다','답변·근거 식별자, 구간, 이유, 승인 상태를 함께 저장해야 학습과 평가가 같은 대상을 본다.');
 s+=card(74,230,850,500,'레코드 구조 예시',[
  '{','  question_id: "ASTRA-300-…",','  answer_sha256: "…",  context_sha256: "…",','  status: "agent_reviewed",','  reviewed_ranges: [[0, 답변길이]],','  spans: [{','    start, end, quote,','    label, reason, evidence_ids,','    human_decision: "pending"','  }],','  human_approval: "pending",','  approved_spans: null,','  training_ready: false','}'
 ],C.navy,{bodySize:17,gap:28,fill:'#eef4fa',bodyColor:C.ink});
 s+=card(950,230,896,230,'근거 anchor 구조',['scope · citation · chunk_id','text_sha256 · quote','context_start/end','source_start/end · evidence_id'],C.purple,{bodySize:19,gap:35});
 s+=card(950,488,896,242,'상태가 표현하는 의미',['unreviewed: 아직 전체 답변을 읽지 않음','agent_draft: 에이전트 후보, gold 아님','adjudication_proposal: 조정 제안','human_approval=pending: 최종 승인 전','training_ready=true: 승인·검증 후에만 가능'],C.orange,{bodySize:18,gap:32});
 s+=text(74,790,'자동 검증 게이트',28,800,C.ink);
 const gates=[['완전성','295개 ID 중복·누락'],['정합성','quote와 문자열 slice 일치'],['근거성','anchor가 지정 chunk에 존재'],['보존','원본·제출본·수정 이력 해시'],['누출','예측으로 gold를 만들지 않음']];
 gates.forEach((d,i)=>{const x=74+i*354;s+=`<rect x="${x}" y="825" width="328" height="140" rx="16" fill="${i%2?C.paleTeal:C.paleBlue}" stroke="${C.line}"/>${text(x+22,868,d[0],21,800,C.ink)}${text(x+22,910,d[1],16,600,C.sub)}`;});
 save(7,s+footer('대형 확률 배열·private prompt·가중치는 Git 제외, 소형 manifest·검증·코드·변경 이력은 보존'));
}

// 8. model and metrics
{
 let s=base(8,'7단계 · 승인 구간을 KLUE 학습·평가·서비스로 연결한다','모델 단독 결과, 규칙 결합 결과와 답변/문자/구간 단위 지표를 서로 분리해 본다.');
 s+=card(74,230,420,260,'① 문자 → 토큰',['승인 span을 토큰 위치로 변환','환각 토큰=1, 정상 토큰=0','보류·미검수 토큰은 mask','질문·근거·답변 형식 고정'],C.blue);
 s+=arrow(506,360,550,360);
 s+=card(562,230,420,260,'② 근거 window',['긴 근거를 여러 window로 분할','같은 답변 토큰을 각 window와 비교','한 근거가 지지하면 정상 가능','window 집계 방식은 개발 자료에서 선택'],C.teal);
 s+=arrow(994,360,1038,360);
 s+=card(1050,230,370,260,'③ 점수·임계값',['토큰별 의심 확률','문장/절/연속 구절 통합 후보','정상 오탐과 환각 누락 trade-off','임계값은 개발 자료로만 선택'],C.orange);
 s+=arrow(1432,360,1476,360);
 s+=card(1488,230,358,260,'④ 출력',['의심 구절과 점수','답변 전체 경고 여부','보류/검수 우선순위','근거·설정·모델 hash'],C.red);
 s+=text(74,550,'서로 다른 평가 단위',28,800,C.ink);
 s+=card(74,585,540,210,'답변 단위',['TP/FP/FN/TN','정밀도·재현율·F1·정확도','“어떤 답변에 오류가 있는가”'],C.blue,{bodySize:19,gap:37});
 s+=card(640,585,540,210,'문자 단위',['문자 위치별 P/R/F1','경고 범위가 넓으면 FP 증가','“틀린 문자를 얼마나 맞혔는가”'],C.teal,{bodySize:19,gap:37});
 s+=card(1206,585,640,210,'Exact-span 단위',['시작·끝 경계가 모두 같아야 정답','답변 포착률이 높아도 0일 수 있음','서비스의 정확한 형광펜 품질을 반영'],C.purple,{bodySize:19,gap:37});
 s+=card(74,830,1772,140,'서비스에서는',['의심 구절을 강조하고 관련 근거로 이동시키되, 모델 경고를 최종 판정으로 표시하지 않는다. 정상/환각/보류 상태와 근거를 함께 보여 사람이 확인하게 한다.','금액·날짜·자격·의무 조건 규칙을 결합하면 KLUE 단독 성능과 결합 성능을 별도로 보고한다.'],C.navy,{bodySize:19,gap:38,fill:'#eef4fa',bodyColor:C.ink});
 save(8,s+footer('KLUE 주력 · XLM-R/BGE-M3는 비교 보존 · 독립 개선 가설이 있을 때만 제한적으로 재실행'));
}

// 9. interpretation and demo sets
{
 let s=base(9,'8단계 · 라벨 자료의 범위를 지켜 결과를 해석한다','같은 100건이라도 추출 방식과 라벨 승인 상태가 다르면 성능 수치의 의미가 완전히 달라진다.');
 const cols=[
  ['역사 비교 63건','개발 과정에서 반복 노출','사람 최종 승인 전','탐색·회귀 비교용',C.purple],
  ['고정 100건','학습 제외 113건에서','예측·라벨 비의존 해시 추출','채점 가능 96건·잠정 평가',C.blue],
  ['80% 시연 100건','정답·예측 확인 후 선정','TP40·TN40·FP10·FN10','전체 성능 추정 금지',C.orange],
  ['85% 시연 100건','정답·예측 확인 후 선정','TP42·TN43·FP7·FN8','전체 성능 추정 금지',C.red]
 ];
 cols.forEach((d,i)=>{const x=74+i*443;s+=card(x,235,417,270,d[0],d.slice(1,4),d[4],{bodySize:17,gap:42});});
 s+=text(74,565,'질문을 받았을 때의 권장 답변',28,800,C.ink);
 s+=card(74,600,1772,225,'“80%·85%는 어떻게 나온 수치인가요?”',['“두 파일은 모델의 일반 성능을 추정하려고 무작위로 만든 평가세트가 아닙니다.”','“성공과 실패 사례를 함께 시연하기 위해 기존 잠정 라벨과 예측을 확인한 뒤 정답 비율을 80%와 85%로 맞춘 구성입니다.”','“별도 고정 100건의 채점 가능 96건에서 v6 잠정 정확도는 67.71%였고, 이 역시 과거 노출 자료라 독립 성능으로 부르지 않습니다.”'],C.orange,{bodySize:20,gap:42,fill:C.paleOrange,bodyColor:C.ink});
 s+=card(74,855,555,120,'말할 수 있는 것',['구간 라벨링 절차와 파이프라인 구축','오탐·누락 trade-off를 실제로 측정'],C.teal,{bodySize:17,gap:31});
 s+=card(656,855,555,120,'아직 말할 수 없는 것',['운영에서 검증된 80/85% 성능','임의 질문에 대한 일반화 정확도'],C.red,{bodySize:17,gap:31});
 s+=card(1238,855,608,120,'다음 검증',['독립 문서·질문·사람 승인 라벨','회사·오류유형별 불확실성 구간'],C.blue,{bodySize:17,gap:31});
 save(9,s+footer('시연 세트는 UI 흐름 설명용 · 성능 발표에는 고정 추출·승인 라벨·미노출 평가가 필요'));
}

console.log(`generated 9 SVGs in ${OUT}`);
