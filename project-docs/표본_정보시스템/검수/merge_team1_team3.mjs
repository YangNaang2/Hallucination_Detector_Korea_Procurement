import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
const root=path.dirname(fileURLToPath(import.meta.url));
const {Workbook}=await import(pathToFileURL(path.join(process.env.RUNTIME_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const input=JSON.parse(await fs.readFile(path.join(process.env.TEMP,'merge-requirements-input.json'),'utf8'));
const original=structuredClone(input.team1);
const encode=rows=>rows.map(r=>r.map(v=>'"'+String(v??'').replaceAll('"','""')+'"').join(',')).join('\r\n')+'\r\n';
const w=await Workbook.fromCSV(encode(original),{sheetName:'요건추출'});
const s=w.worksheets.getItem('요건추출');
const changes=[];
function edit(cell,fn,reason){const before=s.getRange(cell).values[0][0];const after=fn(before);assert.notEqual(after,before,cell);s.getRange(cell).values=[[after]];changes.push({cell,reason,before,after});}
function replace(cell,from,to,reason){edit(cell,v=>{assert.ok(v.includes(from),cell+' missing phrase');return v.replace(from,to);},reason);}
const append=(cell,t,why)=>edit(cell,v=>v+'; '+t,why);
replace('M11','입찰공고문과 제안요청서가 다르면 입찰공고서 우선','기존 추출에는 입찰공고서 우선으로 기재되어 있으나 검토메모는 우선순위 미확인으로 상충함; 우선순위 조항의 원문·위치 재확인 전 최종 적용값 미확인','우선순위 단정과 메모의 모순을 확인 과제로 전환');
replace('O11','보름 차이이며 어느 문서가 우선하는지는 문서에서 확인하지 못함','보름 차이임. 기존 특이조건에는 입찰공고서 우선으로 적혀 있으나 그 조항의 근거 위치가 확인되지 않아, 우선순위 조항 원문·적용 범위를 재확인하기 전 최종 종료일 미확인','본문과 메모의 우선순위 판단 일치');
append('N11','[쪽수 확인 범위] 위 HWP 쪽수 미확인 표기와 6.1의 실제 43쪽 확인 표기가 혼재함. 사용한 원본·변환본 파일과 페이지 기준을 재확인할 것. 43쪽은 제출자의 기존 기재이며 이번 검수에서 재확인한 값이 아님. 다른 조항은 항목 번호로 추적','확인·미확인 쪽수 혼재 및 확인 주체 표시');
replace('G6','참가 제한 없음;','참가자격 조항에는 실적 제한 미기재; 제출서식의 최소 실적 기재 요구와의 관계 및 실적 없는 업체의 참가 가능 여부 미확인;','자격 제한 없음과 최소 실적 요구의 관계 보류');
append('O6','[미확인] 별지 제4호의 단일규모 일천만원 이상 실적 1개 이상 기재 요구가 참가자격 제한인지 제출자료 작성 기준인지 원문·발주기관 확인 필요. 실적이 없는 업체를 참가 가능 또는 불가로 확정하지 않음','실적 없는 기업 정답 생성 보류');
replace('K7','기산점은 세 문서 모두 계약체결일로 동일하고 제안요청서 4.추진일정도 120일을 M1~M4로 표기','제안요청서 4.추진일정은 120일을 M1~M4로 표기하나, 계약체결일(착수일)의 의미와 120일·달력상 4개월의 종료일 동일성은 미확인','기산점 및 일수·개월 동일성 단정 제거');
append('O7','[미확인] 사업기간은 문서별 계약체결일(착수일)부터 120일 / 계약체결일부터 4개월 / 계약일부터 120일을 병기. 계약일·착수일 관계와 실제 종료일을 추가 확인하기 전 단일 종료일로 계산하지 않음','기간 차이 검토 과제 추가');
replace('O3','SW기술성 평가표의 합계와 기술배점이 맞지 않음','SW기술성 평가표의 척도와 최종 기술 반영 점수가 다름(오류 여부 미확인)','100점 평가표와 90점 반영을 오류로 단정하지 않음');
append('L3','세부 기술평가표 합계 100점과 최종 기술 반영 90점은 구분; 구체적 환산·반올림 규칙 미확인','점수 환산의 확인 범위 명시');
append('H8','경계값 주의: 위 7~10명·4~7명은 기존 추출의 범위 표기이며 이상·미만 포함 여부 미확인. 정확히 7명·10명의 점수는 원문 구간 기호 확인 전 확정하지 않음','인력 점수 구간의 경계 중복 보류');
append('H10','경계값 주의: 위 17~20·14~17·11~14는 기존 추출 표기로 이상·미만 포함 여부 미확인. 정확히 14·17·20점의 환산값은 원문 구간 기호 확인 전 확정하지 않음','인력 환산 점수의 경계 중복 보류');
replace('O8','같은 날 계약해도 종료일이 3주가량 벌어질 수 있음','종료일 차이는 실제 계약일·착수일 및 달력에 따라 달라지므로 일수로 확정하지 않음','조건 없는 대략적 기간 차이 수치 제거');
replace('L8','행정안전부 예규 제344호 — 2025.11.24. 일부개정·2025.12.1. 시행이며 제안요청서 39쪽은 개정일을, 41쪽은 시행일을 인용','행정안전부 예규 제344호 — 제안요청서 39쪽 2025.11.24., 41쪽 2025.12.1. 표기 병기; 개정일·시행일 구분은 공식 원문 출처 재확인 필요','법령 날짜 해석을 공식 출처 재확인 대상으로 분리');
replace('O12','국가법령정보센터 기준 같은 예규의 연혁으로, 제40호(2026.1.2. 시행)가 현행이고 제721호(2024.9.13.)는 직전 개정판. 부처명이 다른 것은 2026년 조직 개편에 따른 것이며, 공고문은 현행판·제안요청서는 구판을 인용한 상태','두 문서의 예규 명칭·번호·일자는 위와 같이 병기. 현행 여부·개정 관계·부처명 변경 사유는 공식 연혁 원문 출처 미확인으로 확정하지 않음','외부 출처가 없는 현행 법령·조직 개편 판단 제거');
replace('O7','직접 제출 공고라 수집 값이 빠진 것으로 보임','직접 제출 일정은 원문에 있으나 수집값 누락 원인은 미확인','수집 누락 원인 추정 제거');
replace('O9','나라장터 전자입찰이 아니라 방문 접수 공고라 수집 단계에서 값이 빠진 것으로 보이며','방문 접수 일정은 공고서에 있으나 수집값 누락 원인은 미확인이며','수집 누락 원인 추정 제거');
replace('O2','공고문 2.입찰참가자격이 직접생산확인증명서와 중소기업·소상공인확인서를 요구해 실제로는 제한경쟁이며, 공고문 표기만 \'경쟁입찰\'로 되어 있음','공고문 2.입찰참가자격에는 직접생산확인증명서와 중소기업·소상공인확인서 요구가 있음. 경쟁입찰이라는 일반 표현과 제한경쟁입찰 표기의 차이를 기록하며, 이것만으로 계약방법의 실질적 상충을 확정하지 않음','일반 표현과 구체적 계약방식 표기의 차이로 분류');
append('O2','[적용범위] 하도급 불허 조항과 하도급 계약 시의 일반 보안특약 병존만으로 하도급 허용을 추론하지 않음. 정량 5점·정성 85점의 구성 자체는 오류로 분류하지 않음','보편 조항 병존·평가 구성 자체를 오류로 취급하지 않음');
// Preserve the 51-row template and join only the ten reviewed team-3 records by ID.
assert.deepEqual(input.team3[0],original[0]);
const index=new Map(original.slice(1).map((r,i)=>[r[1],i+2]));
assert.equal(index.size,51);
for(const r of input.team3.slice(1)){
 const line=index.get(r[1]);assert.ok(line);assert.equal(r[0],'팀원3');
 assert.deepEqual(original[line-1].slice(0,5),r.slice(0,5));
 assert.ok(original[line-1].slice(5).every(v=>v===''));
 s.getRange(`F${line}:O${line}`).values=[r.slice(5)];
}
const result=s.getRange('A1:O52').values.map(r=>r.map(v=>v??''));
const expectedIds=input.allocation.map(r=>r.공고번호).sort();
assert.deepEqual(result.slice(1).map(r=>r[1]).sort(),expectedIds);
let filled=0;for(let i=1;i<result.length;i++){
 const r=result[i];assert.deepEqual(r.slice(0,5),original[i].slice(0,5));
 if(r[0]==='팀원1'||r[0]==='팀원3'){assert.ok(r.slice(5).every(v=>String(v).trim()));filled++;}
 else assert.deepEqual(r,original[i]);
}
assert.equal(filled,21); // Team 1: 11 records, team 3: 10 records.
for(const r of input.team3.slice(1))assert.deepEqual(result[index.get(r[1])-1],r);
console.log((await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!',options:{useRegex:true,maxResults:10},maxChars:500})).ndjson);
await fs.writeFile(path.join(root,'요건추출시트_팀원1_3_통합.csv'),'\uFEFF'+encode(result),'utf8');
const log='# 팀원1 보완 및 팀원1·3 통합 내역\n\n'+
'팀원1 제출 CSV를 보완하고, 팀원3 검토수정 XLSX의 10건을 공고번호로 병합했다. 51건 중 팀원1 11건 + 팀원3 10건 = 21건 작성, 다른 팀원 30건은 미작성 상태 그대로다. 제출 원본과 팀원3 수정본은 변경하지 않았다. 기존 15개 열·행 순서·공고 기본정보를 유지했다.\n\n'+
'이번 보완은 제출 시트의 내부 일관성 정리다. 원천 공고 HWP/PDF 전량 재검증이나 법령 현행성 확인을 수행한 결과가 아니다. 미확인은 원문·정정공고·회신을 확인할 때까지 확정 정답에 사용하지 않는다.\n\n'+
'| 팀원1 원본 셀 | 보완 내용 |\n|---|---|\n'+changes.map(c=>`| ${c.cell} | ${c.reason} |`).join('\n')+
'\n\n점수 구간은 원문 수치를 임의 수정하지 않고 경계 포함 여부 미확인으로 표시했다. 팀원3의 10건은 이전 검토수정본 값과 전 셀이 동일함을 확인했다. 팀원2·4·5의 미작성 행은 기존 작성 자료를 덮어쓰는 용도로 사용하지 않는다.\n';
await fs.writeFile(path.join(root,'팀원1_3_통합_변경내역.md'),log);
console.log(JSON.stringify({records:51,completed:filled,unfilled:51-filled,team1EditedCells:new Set(changes.map(c=>c.cell)).size,team3Preserved:10}));
