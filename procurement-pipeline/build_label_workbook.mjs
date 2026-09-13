import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire(path.join(process.cwd(),'runner.cjs'));
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const root=path.resolve(process.argv[2]);
const out=path.join(root,'project-docs/환각라벨링/pilot-25-v1');
const rows=(await fs.readFile(path.join(out,'labels_draft.jsonl'),'utf8')).trim().split('\n').map(JSON.parse);
const workbook=Workbook.create();
const short=r=>r.question_id.replace('ASTRA-300-','');
const sheets=[];
function sheet(name,title,subtitle,headers,data,widths,heights){
 const sh=workbook.worksheets.add(name);sheets.push(sh);sh.showGridLines=false;
 const all=sh.getRangeByIndexes(0,0,data.length+4,headers.length);
 all.format.font={name:'Malgun Gothic',size:11,color:'#172235'};
 all.format.verticalAlignment='top';all.format.wrapText=true;
 sh.getRange('A1').values=[[title]];sh.getRange('A1').format.font={name:'Malgun Gothic',size:15,bold:true};
 // Keep headings in a single wide column, without merged working cells.
 sh.getRange('A2').values=[[subtitle]];sh.getRange('A2').format.font={size:10,color:'#526279'};
 sh.getRange('A1').format.rowHeight=45;sh.getRange('A2').format.rowHeight=65;
 sh.getRangeByIndexes(3,0,1,headers.length).values=[headers];
 sh.getRangeByIndexes(3,0,1,headers.length).format={fill:'#263B59',font:{name:'Malgun Gothic',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,wrapText:true};
 if(data.length)sh.getRangeByIndexes(4,0,data.length,headers.length).values=data.map(row=>row.map(x=>typeof x==='string'&&x.startsWith('=')?"'"+x:x));
 widths.forEach((w,i)=>sh.getRangeByIndexes(0,i,data.length+4,1).format.columnWidth=w);
 data.forEach((r,i)=>{sh.getRangeByIndexes(i+4,0,1,headers.length).format.rowHeight=typeof heights==='function'?heights(r):heights;
 if(i%2===1)sh.getRangeByIndexes(i+4,0,1,headers.length).format.fill='#F1F4F8';});
 sh.freezePanes.freezeRows(4);
 sh.tables.add(sh.getRangeByIndexes(3,0,data.length+1,headers.length),true,'Table'+sheets.length);
 return sh;
}
const index=sheet('검수목록','ASTRA 답변 25개 검수','사람 승인 pending · 노란 칸에 의견 입력',
 ['문항 ID','회사','질문','초안 구절 수','품질·추가 확인','사람 판정','검수자','검수 의견'],
 rows.map(r=>[short(r),r.company_id,r.question,r.draft_spans.length,r.quality_issues.join('\n'),'pending','','']),
 [32,10,55,12,52,18,16,50],r=>Math.max(75,Math.min(150,30+Math.ceil(r[4].length/40)*16)));
index.getRange('D5:D29').setNumberFormat('0');
index.getRange('F5:H29').format.fill='#FFF2CC';
index.getRange('F5:F29').dataValidation={rule:{type:'list',values:['pending','동의','수정 제안','재검토']}};
const spans=[];
for(const r of rows)for(const s of [...r.draft_spans,...r.review_candidates])spans.push([short(r),s.span_id,s.quote,s.label,s.reason,s.evidence_ids.join(', '),s.start,s.end,'pending','','']);
const sp=sheet('구절판정','오류 구절과 보류 후보','위치: 원시 답변의 Unicode [start,end)',
 ['문항 ID','구절 ID','실제 구절','초안 분류','판단 이유','근거 ID','시작','끝','사람 판정','수정 구절·위치','검수 의견'],spans,[27,29,65,22,62,40,10,10,18,45,45],r=>Math.max(70,Math.min(160,30+Math.ceil(Math.max(r[2].length/60,r[4].length/55))*17)));
sp.getRangeByIndexes(4,6,spans.length,2).setNumberFormat('0');sp.getRangeByIndexes(4,8,spans.length,3).format.fill='#FFF2CC';
sp.getRangeByIndexes(4,8,spans.length,1).dataValidation={rule:{type:'list',values:['pending','동의','수정','삭제','보류']}};
const ev=[];for(const r of rows)for(const e of r.evidence)ev.push([e.evidence_id,e.scope==='prompt_context'?'생성 시 입력':'추가 검수 전용',e.quote,e.source_path,e.document_id,e.document_version,e.start,e.end,e.security_level]);
sheet('근거','원문 근거 발췌','추가 검수 전용 근거는 모델이 보지 않음',
 ['근거 ID','근거 범위','정확한 인용','원문 파일','문서 ID','버전','시작','끝','등급'],ev,[30,20,85,60,45,30,10,10,10],r=>Math.max(100,Math.min(240,25+Math.ceil(r[2].length/65)*17)));
const parts=[];
for(const r of rows){
 // Preserve slices exactly. Split long answers into readable cells, never rewrite them.
 let pos=0,seq=0;
 while(pos<r.actual_answer.length){
  let end=Math.min(r.actual_answer.length,pos+260);if(end<r.actual_answer.length){const nl=r.actual_answer.lastIndexOf('\n',end);if(nl>pos+80)end=nl+1;}
  const piece=r.actual_answer.slice(pos,end);
  // Data uses Python code-point offsets; count code points for JS slice prefixes.
  parts.push([short(r),++seq,piece,[...r.actual_answer.slice(0,pos)].length,[...r.actual_answer.slice(0,end)].length]);pos=end;
 }
}
sheet('답변전문','원시 답변 전문','문항별 순서대로 이어 붙이면 원문과 동일',
 ['문항 ID','순서','원시 답변 구간','시작','끝'],parts,[32,10,100,12,12],r=>Math.max(55,25+Math.max(Math.ceil(r[2].length/75),r[2].split('\n').length)*17));
const guide=[
 ['검토 순서','질문과 답변, 실제 입력 근거를 먼저 읽고 구절별 동의·수정·삭제·보류를 기록한다.'],
 ['CONTRADICTION','입력 근거에 반하는 주장. 증빙 missing을 존재로 바꾸거나 서비스 보유 주체를 회사로 바꾸는 경우.'],
 ['UNSUPPORTED','입력에 지지 근거가 없는 추가 주장. 현실의 거짓이나 법적 위법성을 확정하는 분류가 아니다.'],
 ['CITATION_ERROR','존재하지 않는 번호·잘못된 페이지 등 출처 오류. 환각 토큰 학습 목표와 분리한다.'],
 ['UNCERTAIN','범위가 모호한 표현. 확정 양성·음성으로 학습하지 말고 사람에게 판정을 맡긴다.'],
 ['누락·반복·잘림','업무 품질 문제로 별도 기록. 답변에 없는 구절을 새로 만들지 않는다.'],
 ['문자 위치','0부터 시작, 끝 제외. 원시 Markdown·공백·LF를 유지하는 Unicode code point 기준이다.'],
 ['추가 검수 근거','원래 입력에서 빠진 원문은 참고 전용이며 모델 입력에 소급 포함하지 않는다.'],
 ['사람 승인','현재 모두 pending. 엑셀 의견이 자동 승인·학습 입력이 되지 않는다. 교차검수와 최종 조정이 필요하다.'],
 ['대표성','회사별 5개 의도 표본이며 기존 개발 노출 자료다. 전체 오류율이나 독립 성능 지표로 쓰지 않는다.'],
 ['기대답·상세 지침','review.html에서 질문·기대답·형광펜·근거를 함께 볼 수 있다. 자세한 기준은 GUIDELINES.md에 있다.']
];
sheet('기준','구절 라벨링 기준','에이전트 초안 · 학습 사용 전 사람 검수', ['항목','기준'],guide,[32,105],r=>Math.max(55,25+Math.ceil(r[1].length/80)*18));
sheet('문항해설','기대답과 에이전트 설명','기대답은 원문 증거를 대체하지 않음',
 ['문항 ID','질문','기대답','에이전트 설명'],rows.map(r=>[short(r),r.question,r.expected_answer,r.agent_note]),[32,55,75,80],r=>Math.max(85,30+Math.ceil(Math.max(r[2].length/60,r[3].length/65))*18));
await fs.mkdir(path.join(root,'work/labeling-pilot/previews'),{recursive:true});
for(const sh of sheets){
 const preview=await workbook.render({sheetName:sh.name,range:sh.name==='기준'?'A1:B8':sh.name==='답변전문'?'A1:E7':sh.name==='근거'||sh.name==='문항해설'?'A1:D6':sh.name==='구절판정'?'A1:F7':'A1:H7',scale:1,format:'png'});
 await fs.writeFile(path.join(root,'work/labeling-pilot/previews',sh.name+'.png'),new Uint8Array(await preview.arrayBuffer()));
}
console.log((await workbook.inspect({kind:'table',range:'검수목록!A4:H7',include:'values',tableMaxRows:4,tableMaxCols:8,maxChars:1800})).ndjson);
console.log((await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:10},maxChars:1000})).ndjson);
const dest=path.join(out,'검수시트_25개.xlsx');const xlsx=await SpreadsheetFile.exportXlsx(workbook);await xlsx.save(dest);
console.log(JSON.stringify({output:dest,answers:rows.length,span_rows:spans.length,evidence_rows:ev.length,answer_blocks:parts.length,sheets:sheets.length}));
