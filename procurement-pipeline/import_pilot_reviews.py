"""Read returned XLSX without executing formulas; preserve v1 and approval boundaries."""
import argparse, collections, copy, csv, hashlib, html, json, re, shutil, sqlite3
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from review_pilot_return_specs import RELABEL, ADDITIONS, AGENT_CITATIONS, ISSUES
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'project-docs/환각라벨링/pilot-25-v1'
OUT=ROOT/'project-docs/환각라벨링/pilot-25-human-review-v1'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
FILES=['팀원1_검수시트_7문항.xlsx','팀원2_검수시트_6문항_박승형_20260915_1.xlsx','팀원3_검수시트_6문항_박지훈_20260915.xlsx','팀원4_검수시트_6문항.xlsx']
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def require(ok,msg):
 if not ok: raise ValueError(msg)
def workbook(path):
 result={}
 with ZipFile(path) as z:
  require(not any('externalLink' in n or n.endswith('vbaProject.bin') for n in z.namelist()),'External links/macros')
  ss=[''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)] if 'xl/sharedStrings.xml' in z.namelist() else []
  rel={e.attrib['Id']:e.attrib['Target'] for e in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
  for s in ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet',NS):
   target=rel[s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
   path_in_zip=target.lstrip('/') if target.startswith('/') else 'xl/'+target
   sheet={}
   for c in ET.fromstring(z.read(path_in_zip)).findall('.//m:sheetData/m:row/m:c',NS):
    require(c.find('m:f',NS) is None,'Formula forbidden: '+c.attrib['r'])
    require(c.attrib.get('t')!='e','Excel error cell')
    v=c.find('m:v',NS); value=v.text if v is not None and v.text else ''
    if c.attrib.get('t')=='s': value=ss[int(value)]
    elif c.attrib.get('t')=='inlineStr': value=''.join(c.find('m:is',NS).itertext())
    if value: sheet[c.attrib['r']]=value
   result[s.attrib['name']]=sheet
 return result

def compare_protected(original,submitted):
 require(set(original)<=set(submitted),'Missing original sheet')
 extras=set(submitted)-set(original)
 require(all(not submitted[n] for n in extras),'Nonempty extra sheet')
 diffs=[{'sheet':n,'kind':'empty_extra_sheet_ignored'} for n in sorted(extras)]
 for name,before in original.items():
  for address in sorted(set(before)|set(submitted[name])):
   col,row=re.fullmatch(r'([A-Z]+)(\d+)',address).groups()
   editable=int(row)>=5 and ((name=='검수목록' and col in ['F','G','H']) or (name=='구절판정' and col in ['I','J','K']))
   if not editable and before.get(address,'')!=submitted[name].get(address,''):
    old,new=before.get(address,''),submitted[name].get(address,'')
    recoverable=name in ['답변전문','근거'] and col=='C' and int(row)>=5 and old.strip()==new.strip()
    require(recoverable,'Protected content changed: '+name+'!'+address)
    diffs.append({'sheet':name,'cell':address,'kind':'boundary_whitespace_restored_from_v1','before_sha256':sha(old.encode()),'after_sha256':sha(new.encode()),'before_length':len(old),'after_length':len(new)})
 return diffs

def records(sheet):
 rows=sorted({int(re.sub('[A-Z]','',a)) for a in sheet if a.startswith('A') and int(a[1:])>=5})
 return [(row,{re.sub(r'\d','',a):v for a,v in sheet.items() if int(re.sub('[A-Z]','',a))==row}) for row in rows if sheet.get('A'+str(row))]

def locate(answer,quote,occurrence):
 starts=[m.start() for m in re.finditer(re.escape(quote),answer)]
 require(len(starts)>=occurrence,'Quote not found: '+quote)
 start=starts[occurrence-1]
 return start,start+len(quote)

def validate(rows,base):
 require(len(rows)==25 and len({r['question_id'] for r in rows})==25,'25 unique questions required')
 for r in rows:
  b=base[r['question_id']]
  require(r['actual_answer']==b['actual_answer'] and sha(r['actual_answer'].encode())==b['answer_sha256'],'Answer drift')
  require(r['human_approval']=='pending' and r['approved_spans'] is None and r['training_ready'] is False,'Approval escalation')
  require(r['tenant_id']==b['tenant_id'] and r['company_id']==b['company_id'],'Tenant drift')
  require(r['review']['decision'] in ['동의','수정 제안','재검토'],'Missing question review')
  require(bool(r['review']['reviewer'].strip()),'Missing reviewer')
  evidence={e['evidence_id']:e for e in r['evidence']}
  ids=set()
  for s in r['proposed_spans']:
   require(s['span_id'] not in ids,'Duplicate span ID'); ids.add(s['span_id'])
   require(0<=s['start']<s['end']<=len(r['actual_answer']) and r['actual_answer'][s['start']:s['end']]==s['quote'],'Offset/quote drift')
   require(s['label'] in [None,'CONTRADICTION','UNSUPPORTED','CITATION_ERROR','UNCERTAIN'],'Invalid label')
   require(bool(s['evidence_ids']) and all(x in evidence for x in s['evidence_ids']),'Missing evidence')
   for eid in s['evidence_ids']:
    e=evidence[eid]; require(e.get('company_id') in [None,r['company_id']],'Cross-tenant evidence')
   require(s['final_human_approval']=='pending','Span auto-approved')
   require(s['hallucination_target']==(s['label'] in ['CONTRADICTION','UNSUPPORTED'] and s['agent_disposition']!='quality_only'),'Target class leakage')
 return True

def context_anchor(r,con,citation):
 existing=next((e for e in r['evidence'] if e.get('citation')==citation and e['scope']=='prompt_context'),None)
 # Preserve old short excerpts; supplemental anchors expose complete needed chunk only,
 # not the source cache or a new prompt. This is an internal evaluation artifact.
 p=next(p for p in r['prompt_context_manifest'] if p['citation']==citation)
 c=json.loads(con.execute('SELECT payload FROM corpus WHERE chunk_id=?',(p['chunk_id'],)).fetchone()[0])
 require(sha(c['text'].encode())==p['text_sha256'],'Context hash mismatch')
 require(c.get('company_id') in [None,r['company_id']],'Cross-tenant context')
 eid=r['question_id'].replace('ASTRA-300-','')+f'-INPUT-{citation}'
 if not any(e['evidence_id']==eid for e in r['evidence']):
  r['evidence'].append(dict(evidence_id=eid,scope='prompt_context',citation=citation,chunk_id=p['chunk_id'],document_id=p['document_id'],document_version=p['document_version'],source_path=p['source_path'],company_id=c.get('company_id'),tenant_id=c.get('tenant_id'),security_level=c['security_level'],source_nature='real_notice' if c['security_level']=='L1' else 'synthetic_company',start=p['text_start'],end=p['text_end'],quote=c['text'],chunk_sha256=p['text_sha256']))
 return eid

def build(input_dir,index):
 base_rows=[json.loads(l) for l in (BASE/'labels_draft.jsonl').read_text(encoding='utf-8').splitlines()]
 base={r['question_id']:r for r in base_rows}; rows=copy.deepcopy(base_rows); lookup={r['question_id']:r for r in rows}
 assignments=load(BASE/'team-delivery/assignments.json')['groups']; manifests=[]; normalized=[]; seen=set(); span_seen=set()
 for group,filename in zip(assignments,FILES):
  team=group['team_id']; submitted_path=input_dir/filename
  if not submitted_path.exists(): submitted_path=input_dir/(team+'.xlsx')
  original_path=next((BASE/'team-delivery'/team).glob('*.xlsx'))
  original=workbook(original_path); submitted=workbook(submitted_path); deviations=compare_protected(original,submitted)
  qrows=records(submitted['검수목록']); srows=records(submitted['구절판정'])
  require({'ASTRA-300-'+r['A'] for _,r in qrows}==set(group['question_ids']),'Assignment mismatch')
  require(len(qrows)==group['target_count'] and len(srows)==group['span_rows'],'Row count mismatch')
  manifests.append(dict(team_id=team,original_filename=filename,archive=team+'.xlsx',sha256=sha(submitted_path.read_bytes()),template_sha256=sha(original_path.read_bytes()),question_count=len(qrows),span_count=len(srows),protected_cells_unchanged=not deviations,format_deviations=deviations,canonical_content_preserved=True))
  for row,r in qrows:
   qid='ASTRA-300-'+r['A']; require(qid not in seen,'Duplicate question'); seen.add(qid)
   review=dict(team_id=team,decision=r.get('F',''),reviewer=r.get('G',''),comment=r.get('H',''),source_cell=f'{team}.xlsx / 검수목록!F{row}:H{row}',workbook_sha256=manifests[-1]['sha256'])
   lookup[qid]['review']=review; normalized.append(dict(kind='question',question_id=qid,**review))
  for row,s in srows:
   qid='ASTRA-300-'+s['A']; sid=s['B']; require(sid not in span_seen,'Duplicate span');span_seen.add(sid)
   require(s.get('I','') in ['동의','수정','삭제','보류'],'Missing span decision')
   original_span=next(x for x in base[qid]['draft_spans']+base[qid]['review_candidates'] if x['span_id']==sid)
   require(s['C']==original_span['quote'] and int(s['G'])==original_span['start'] and int(s['H'])==original_span['end'],'Canonical span drift')
   rev=dict(decision=s['I'],replacement=s.get('J',''),comment=s.get('K',''),source_cell=f'{team}.xlsx / 구절판정!I{row}:K{row}')
   normalized.append(dict(kind='span',question_id=qid,span_id=sid,team_id=team,**rev))
   label,reason=RELABEL.get(sid,(original_span['label'],original_span['reason']))
   require(s['I']!='수정' or sid in RELABEL,'Unmapped revision requires review')
   proposal=dict(original_span,original_label=original_span['label'],label=label,reason=reason,review=rev,origin='existing_v1',agent_disposition='hold' if label=='UNCERTAIN' or s['I']=='보류' else 'accept_proposal',final_human_approval='pending',hallucination_target=label in ['CONTRADICTION','UNSUPPORTED'])
   lookup[qid].setdefault('proposed_spans',[]).append(proposal)
 require(seen==set(base),'Coverage mismatch')
 con=sqlite3.connect(index.resolve().as_uri()+'?mode=ro',uri=True)
 context_count=0
 for r in rows:
  r.setdefault('proposed_spans',[])
  for p in r['prompt_context_manifest']:
   c=json.loads(con.execute('SELECT payload FROM corpus WHERE chunk_id=?',(p['chunk_id'],)).fetchone()[0]); require(sha(c['text'].encode())==p['text_sha256'],'Prompt context mismatch'); context_count+=1
  for e in r['evidence']:
   c=json.loads(con.execute('SELECT payload FROM corpus WHERE chunk_id=?',(e['chunk_id'],)).fetchone()[0]); require(c['text'][e['start']-c['text_start']:e['end']-c['text_start']]==e['quote'],'Evidence quote drift')
  r.update(dataset_version='pilot-25-human-review-v1',review_received=True,human_approval='pending',approved_spans=None,training_ready=False,agent_review_status='proposal_not_approval',final_review_issues=[dict(kind=k,detail=d) for q,k,d in ISSUES if r['question_id'].endswith(q)])
 specs=[(x,'reviewer_addition') for x in ADDITIONS]
 specs += [(('C01-N43-E4',quote,1,None,'accept_proposal','CITATION_ERROR','동일 유형 조항 번호 오류를 전체 문장으로 확인: 실제 위치 '+actual,[2]),'agent_addition') for quote,actual in AGENT_CITATIONS]
 for i,(spec,origin) in enumerate(specs,1):
  q,quote,occ,reviewer_label,disposition,label,reason,citations=spec;r=lookup['ASTRA-300-'+q]
  start,end=locate(r['actual_answer'],quote,occ)
  ids=[context_anchor(r,con,c) for c in citations]
  if origin=='reviewer_addition': require(quote in r['review']['comment'],'Addition is not in reviewer note: '+quote)
  r['proposed_spans'].append(dict(span_id=f'{q}-R{i:02d}',start=start,end=end,quote=quote,label=label,reviewer_label=reviewer_label,reason=reason,evidence_ids=ids,origin=origin,agent_disposition=disposition,hallucination_target=label in ['CONTRADICTION','UNSUPPORTED'],final_human_approval='pending',review_source=r['review']['source_cell'],occurrence=occ))
 con.close(); validate(rows,base)
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'received').mkdir(exist_ok=True)
 for m in manifests:
  src=input_dir/m['original_filename']
  if not src.exists(): src=input_dir/m['archive']
  dest=OUT/'received'/m['archive']
  if dest.exists(): require(sha(dest.read_bytes())==m['sha256'],'Refusing to overwrite a different submission')
  elif src.resolve()!=dest.resolve(): shutil.copyfile(src,dest)
 dump(OUT/'intake_manifest.json',dict(version='1.0.0',received_on='2026-09-15',files=manifests,base_labels_sha256=sha((BASE/'labels_draft.jsonl').read_bytes())))
 for name,data in [('submitted_reviews.jsonl',normalized),('adjudication_proposals.jsonl',rows)]:
  (OUT/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data),encoding='utf-8')
 allspans=[s for r in rows for s in r['proposed_spans']]
 report=dict(question_count=len(rows),question_decisions=dict(collections.Counter(r['review']['decision'] for r in rows)),original_span_count=len(span_seen),original_span_decisions=dict(collections.Counter(r['decision'] for r in normalized if r['kind']=='span')),relabel_proposals=len(RELABEL),reviewer_additions=len(ADDITIONS),agent_additions=len(AGENT_CITATIONS),proposed_span_records=len(allspans),proposed_labels=dict(collections.Counter(s['label'] or 'QUALITY_ONLY' for s in allspans)),dispositions=dict(collections.Counter(s['agent_disposition'] for s in allspans)),original_protected_cells_unchanged=all(m['protected_cells_unchanged'] for m in manifests),canonical_content_preserved=True,boundary_whitespace_changes=sum(d.get('kind')=='boundary_whitespace_restored_from_v1' for m in manifests for d in m['format_deviations']),empty_extra_sheets=sum(d.get('kind')=='empty_extra_sheet_ignored' for m in manifests for d in m['format_deviations']),verified_prompt_chunks=context_count,validation='passed',human_approval='pending',training_ready=False,agent_review_scope='All 25 submitted question comments and 68 span comments read; changed/additional spans compared to answer and input evidence. Original HWP/PDF page rendering and source-wide word counts were not rerun.',source_cache_revalidation='not performed; immutable v1 anchors and stored prompt hashes matched read-only local index',inter_annotator_agreement='not computable: disjoint assignments, no independent overlapping double annotation')
 dump(OUT/'validation_report.json',report)
 with (OUT/'통합검수목록.tsv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f,delimiter='\t');w.writerow(['문항ID','팀','검수자','사람판정','의견','구절조정안수','최종승인'])
  for r in rows:w.writerow([r['question_id'],r['review']['team_id'],r['review']['reviewer'],r['review']['decision'],r['review']['comment'],len(r['proposed_spans']),'pending'])
 with (OUT/'구절조정목록.tsv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f,delimiter='\t');w.writerow(['문항ID','구절ID','정본구절','시작','끝','기존분류','제출분류','조정분류','처리제안','제안출처','이유','근거ID','최종승인'])
  for r in rows:
   for s in r['proposed_spans']:w.writerow([r['question_id'],s['span_id'],s['quote'],s['start'],s['end'],s.get('original_label',''),s.get('reviewer_label',''),s['label'] or 'QUALITY_ONLY',s['agent_disposition'],s['origin'],s['reason'],','.join(s['evidence_ids']),'pending'])
 render(rows,report)
 print(json.dumps(report,ensure_ascii=False))
 return rows,report

def render(rows,report):
 esc=html.escape; cards=[]
 for r in rows:
  answer=r['actual_answer'];spans=r['proposed_spans']; boundaries=sorted({0,len(answer)}|{s[k] for s in spans for k in ['start','end']}); parts=[]
  for a,b in zip(boundaries,boundaries[1:]):
   active=[s for s in spans if s['start']<=a and s['end']>=b and s['agent_disposition']!='quality_only']; text=esc(answer[a:b])
   if active:
    color='uncertain' if any(s['label']=='UNCERTAIN' for s in active) else ('citation' if all(s['label']=='CITATION_ERROR' for s in active) else 'error')
    text=f'<mark class="{color}" title="'+esc(' | '.join(s['span_id']+': '+s['reason'] for s in active),quote=True)+'">'+text+'</mark>'
   parts.append(text)
  items=''.join('<tr><td>'+esc(s['span_id'])+'</td><td>'+esc(s['quote'])+'</td><td>'+esc(s['label'] or '품질 메모')+'</td><td>'+esc(s['agent_disposition']+' · '+s['origin'])+'</td><td>'+esc(s['reason'])+'</td></tr>' for s in spans)
  ev=''.join('<details><summary>'+esc(e['evidence_id']+' · '+e['scope'])+'</summary><p>'+esc(e['source_path'])+'</p><pre>'+esc(e['quote'])+'</pre></details>' for e in r['evidence'])
  cards.append('<article id="'+esc(r['question_id'])+'"><h2>'+esc(r['question_id'])+'</h2><h3>'+esc(r['question'])+'</h3><p>'+esc(r['review']['team_id']+' / '+r['review']['reviewer']+' / '+r['review']['decision'])+'</p><pre class="answer">'+''.join(parts)+'</pre><details><summary>제출 의견 원문</summary><pre>'+esc(r['review']['comment'])+'</pre></details><details><summary>구절별 조정안 '+str(len(spans))+'건</summary><div class="scroll"><table><tr><th>ID</th><th>구절</th><th>분류</th><th>상태·제안자</th><th>이유</th></tr>'+items+'</table></div></details><details><summary>근거 확인</summary>'+ev+'</details></article>')
 page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASTRA 25문항 검수 통합 조정안</title><style>body{font:16px/1.7 system-ui;margin:24px auto;max-width:1100px;padding:0 16px;background:#f3f5f8;color:#172334}header,article{background:white;border:1px solid #ccd5e0;border-radius:12px;padding:24px;margin-bottom:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}.answer{border-left:4px solid #376cf3;padding:16px;background:#f6f8ff}summary{cursor:pointer;padding:10px;font-weight:650}mark{color:inherit}.error{background:#ffe29a}.citation{background:#cde8ff}.uncertain{background:#efdcfc;border-bottom:2px dotted #7e35a7}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #ccd5e0;padding:8px;vertical-align:top}.scroll{overflow:auto}th{background:#eef1f6}h2{font-size:20px}h1{font-size:28px}@media(max-width:650px){body{padding:0 8px}article,header{padding:16px}h1{font-size:24px}}</style><header><h1>ASTRA · 25문항 검수 통합 조정안</h1><p>팀원 4명 제출 완료 · 최종 승인 pending · 학습 내보내기 금지</p><p>노랑: 환각 구절 조정안 / 파랑: 인용 오류 / 보라 점선: 모호하여 보류. 원래 답변과 오류를 수정하지 않았습니다. 조정안은 사람의 최종 승인이 아닙니다.</p><p>회사 L2/L3 근거가 포함된 내부 평가 자료입니다. 공개 데모 폴더나 RAG 색인에 넣지 않습니다.</p></header>'+''.join(cards)+'</html>'
 (OUT/'review.html').write_text(page,encoding='utf-8')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,required=True);p.add_argument('--index',type=Path,required=True);a=p.parse_args();build(a.input_dir,a.index)
