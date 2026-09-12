import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
const root=path.dirname(fileURLToPath(import.meta.url));
const {FileBlob,SpreadsheetFile}=await import(pathToFileURL(path.join(process.env.RUNTIME_NODE_MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const input=process.argv[2];
if(!input)throw new Error('Supply the submitted workbook path');
const w=await SpreadsheetFile.importXlsx(await FileBlob.load(input));
const s=w.worksheets.getItem('팀원3');
const changes=[];
function edit(cell,fn,reason){const before=s.getRange(cell).values[0][0];const after=fn(before);if(before===after)throw new Error('No change '+cell);s.getRange(cell).values=[[after]];changes.push({cell,before,after,reason});}
function replace(cell,from,to,reason){edit(cell,v=>{if(!v.includes(from))throw new Error('Missing text '+cell);return v.replace(from,to);},reason);}
replace('F9','정규직 경력 10년 초과 인력','정규직 경력 요건 원문 표기: 관련 근무경력이 10년 이상 초과자(정확히 10년 포함 여부 미확인)','본문의 경력 경계값 단정을 검토메모와 일치시킴');
replace('H9','전원 정규직·관련 경력 10년 초과(증빙)','전원 정규직; 경력 요건 원문 표기: 관련 근무경력이 10년 이상 초과자; 별지5: 근무경력 10년 이상만 기재; 정확히 10년 포함 여부 미확인(증빙)','이상·초과의 충돌을 보존하고 임의 기준 선택을 제거');
replace('L2','100점→90점 환산식 미기재; 차등점수제 미적용; 가격 산식 미기재; 배점표 합계 100점을 기술점수 90점으로 환산(제안요청서 58면 "평가배점 = 기술 평가점수(90점) + 입찰가격 평가점수(10점)")','배점표 합계 100점과 기술 반영 90점을 병기; 구체적인 환산식·반올림 방식 미확인; 차등점수제 미적용; 가격 산식 미기재; 근거: 제안요청서 58면 "평가배점 = 기술 평가점수(90점) + 입찰가격 평가점수(10점)"','확인된 배점과 추정 환산 방법을 분리');
edit('O2',v=>v+'; [미확인] 기술 배점표 합계 100점과 종합평가 기술 반영 90점은 구분해 사용. 구체적인 환산식·반올림 규칙은 추가 근거 확인 전 정답으로 확정하지 않음','배점 환산 검토 과제를 기록');
replace('K4','납품기한(과업기간) 계약체결일로부터 270일(9개월); 추진 일정(안) 2026.6~2027.2(9개월)로 270일과 정합, ※ 최종계약일에 따라 상호협의 변동 가능','납품기한(과업기간) 계약체결일로부터 270일; 추진 일정(안) 2026.6~2027.2(9개월); 일수와 월 단위 일정을 병기(정확한 종료일 및 일치 여부 미확인); ※ 최종계약일에 따라 상호협의 변동 가능','270일과 달력상 9개월의 동일성 단정 제거');
replace('K4','최종보고회 사업종료로부터 14일 이내(과업종료일 14일 전후)','최종보고회: 기존 추출에 사업종료로부터 14일 이내 / 과업종료일 14일 전후가 병기됨; 원문 문구·종료 전후 여부 재확인 필요','서로 다른 기간 표현을 원문 재확인 대상으로 보류');
edit('O4',v=>v+'; [미확인] 일정 표현 재확인: 계약체결일로부터 270일과 추진 일정(안) 2026.6~2027.2(9개월)을 같은 종료일로 간주하지 않음. 최종보고회는 기존 추출의 종료로부터 14일 이내 / 종료일 14일 전후 중 원문 표현과 적용 시점을 재확인해야 하며, 확인 전 날짜 계산 정답에 사용하지 않음','정답 생성에서 보류할 일정 항목 명시');
edit('O7',v=>v+'; [미확인] 대금 지급 일정: 추출된 분기(3개월)별 연 2회 지급과 용역기간 2026.6.2~12.31(7개월)의 관계 재확인 필요. 지급 대상 기간·횟수·잔여기간 정산 방식을 원문에서 확인하기 전 지급일·지급액을 계산해 확정하지 않음(과업내용서 Ⅱ.5, 변환본 8~9면)','누락된 지급 기간 검토 항목 추가; 기존 수치 유지');
replace('O3',"현행 제도상 적정 표현은 국가보안기술연구소장이며 '국가정보원 인증'은 구 규정 또는 부정확한 표현으로 추정되나, 정정공고·최종 계약문서를 확인할 수 없어 입찰 최종 적용 값은 미확인","어느 표현이 본 사업에 최종 적용되는지는 정정공고·최종 계약문서·발주기관 회신 미확인으로 확정하지 않음. 현행 제도상 적정성 판단은 이 요건 추출의 확정 근거에서 제외","외부 출처 없는 제도 해석 제거");
replace('O3','현행 「소프트웨어사업 계약 및 관리감독에 관한 지침」상 FP 사업에서 투입인력 수·인적사항·투입기간 요구는 제한되므로 규정상 해당 문구가 부적정할 가능성이 높으나, 삭제·정정 근거가 확인되지 않아','삭제·정정 근거가 확인되지 않아','규정 위반 가능성을 추정하는 문장 제거; 공고 안의 병존 사실 유지');
replace('O5','공동수급사 인력이 정량평가 인원에 산입되는지 상충하는 해석이 가능하며 문언상 대표사 한정 해석이 다소 우세하나, 정정공고·발주기관 질의회신 없이 최종값으로 확정하지 않음','공동수급사 인력이 정량평가 인원에 산입되는지 문서 표현이 달라, 정정공고·발주기관 질의회신 없이 어느 해석도 최종값으로 확정하지 않음','근거 없는 해석 우열 판단 제거');
replace('O9','제안 준비 시 요건 미충족 위험을 줄이기 위해 내부적으로 10년 초과 인력을 적용하는 보수적 대응은 가능하나 이는 최종 적용값이 아님','정확히 10년인 인력의 충족 여부는 미확인으로 유지하고, 추가 근거 확인 전 충족·미충족 정답으로 확정하지 않음','입찰 대응 제안 대신 데이터 검수 기준으로 정리');
for(const cell of ['N3','N5','N6','N7','N8','N9','N10'])edit(cell,v=>v+'; [쪽수 식별] 위 변환본 쪽수는 제출 시트의 표기이며 원본 쪽수와 동일하다고 간주하지 않음. 사용한 변환 파일명·버전은 미확인으로, 재검수 시 해당 파일과 조항 번호를 함께 대조할 것.','변환본 식별 한계를 표시; 기존 쪽수·조항 유지');
const output=path.join(root,'요건추출시트_팀원3_검토수정.xlsx');
// Existing layout is preserved. These are values-only changes.
console.log((await w.inspect({kind:'region',sheetId:'팀원3',range:'H9:H9',maxChars:1600})).ndjson);
console.log((await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:700})).ndjson);
const preview=await w.render({sheetName:'팀원3',range:'H9:H9',scale:1});
await fs.writeFile(path.join(process.env.TEMP,'team3-after.png'),new Uint8Array(await preview.arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(w)).save(output);
const groups=new Map();for(const c of changes){if(!groups.has(c.cell))groups.set(c.cell,[]);groups.get(c.cell).push(c.reason);}
const report='# 팀원3 요건추출시트 검토 수정 내역\n\n'+
'제출 원본은 수정하지 않았다. 원본 공고 HWP/PDF를 새로 대조한 사실 검증본이 아니라, 제출 시트의 내부 일관성과 확정·미확인 구분을 보완한 수정본이다. 담당 10건, 원래 15개 열과 서식을 유지했다.\n\n'+
'변경 원칙: 확인된 금액·날짜·쪽수는 임의 교체하지 않는다. 원문 기재, 기존 추출, 추가 검토가 필요한 해석을 구분한다. 미확인 항목은 자동 정답 생성 시 보류하거나 근거 부족 응답의 검토 대상으로 사용한다.\n\n'+
'| 셀 | 수정 내용 |\n|---|---|\n'+[...groups].map(([cell,rs])=>'| '+cell+' | '+rs.join('; ')+' |').join('\n')+
'\n\n원문 재확인이 필요한 항목: 경력 10년 경계값, 기술점수 환산식, 최종보고회 시점, 지급 기간·횟수, 변환본 파일 식별. 제도 판단·발주기관의 최종 해석은 이 수정으로 확정하지 않았다.\n';
await fs.writeFile(path.join(root,'팀원3_검토수정_내역.md'),report);
await fs.writeFile(path.join(process.env.TEMP,'team3-changes.json'),JSON.stringify(changes));
execFileSync(process.env.RUNTIME_PYTHON,path.join(root,'preserve_workbook_package.py')?[path.join(root,'preserve_workbook_package.py'),input,output]:[],{stdio:'inherit'});
await fs.rename(output+'.inspect.ndjson',path.join(process.env.TEMP,'team3-export.inspect.ndjson')).catch(()=>{});
console.log('SAVED',output,'changed cells',groups.size);
