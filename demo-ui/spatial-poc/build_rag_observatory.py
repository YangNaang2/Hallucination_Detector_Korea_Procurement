"""Public L1-only replay projection; never a RAG index or authentication service."""
import json,sqlite3,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def main():
 labels=[json.loads(l) for l in (ROOT/'project-docs/환각라벨링/pilot-25-v1/labels_draft.jsonl').read_text(encoding='utf8').splitlines()]
 ids={'ASTRA-300-C01-N01-E1','ASTRA-300-C01-N07-E5','ASTRA-300-C02-N41-E2','ASTRA-300-C03-N48-E1'}
 db=sqlite3.connect((ROOT/'work/rag-pilot/index.sqlite').as_uri()+'?mode=ro',uri=True)
 cases=[]
 for r in labels:
  if r['question_id'] not in ids:continue
  assert all(m['security_level']=='L1' for m in r['prompt_context_manifest'])
  contexts=[]
  for m in r['prompt_context_manifest']:
   p=json.loads(db.execute('select payload from corpus where chunk_id=?',(m['chunk_id'],)).fetchone()[0]);assert p['security_level']=='L1' and p['company_id'] is None
   assert hashlib.sha256(p['text'].encode()).hexdigest()==m['text_sha256']
   contexts.append({k:p[k] for k in ['chunk_id','document_id','document_version','filename','text','text_start','text_end','security_level'] }|{'citation':m['citation'],'scope':'prompt_context'})
  for e in r['evidence']:
   if e['scope']=='prompt_context':continue
   assert e['security_level']=='L1' and e['company_id'] is None
   contexts.append({'chunk_id':e['chunk_id'],'document_id':e['document_id'],'document_version':e['document_version'],'filename':e['source_path'].replace('\\','/').split('/')[-1],'text':e['quote'],'text_start':e['start'],'text_end':e['end'],'citation':None,'scope':'reference_only_not_in_prompt','security_level':'L1'})
  spans=[{k:s[k] for k in ['start','end','quote','label','reason']} for s in r['draft_spans']+r['review_candidates']]
  for s in spans:assert r['actual_answer'][s['start']:s['end']]==s['quote']
  cases.append({'id':r['question_id'],'bid':r['bid_key'],'question':r['question'],'answer':r['actual_answer'],'answer_sha256':r['answer_sha256'],'contexts':contexts,'spans':spans,'quality_notes':r['quality_issues'],'human_approval':'pending','mode':'saved_replay'})
 manifest=load('project-docs/RAG파일럿/v1/index_manifest.json');summary=load('project-docs/RAG파일럿/workstation-275/evaluation/final_summary.json')
 docs=[]
 for d in manifest['documents']:
  if d['security_level']!='L1':continue
  count=db.execute('select count(*) from corpus where json_extract(payload,\'$.document_id\')=?',(d['document_id'],)).fetchone()[0]
  docs.append({k:d[k] for k in ['document_id','bid_key','filename','security_level']}|{'chunks':count})
 payload={'mode':'saved_replay','scope':'公開L1のみ'.replace('公開L1のみ','공개 L1 문서만; 권한 서버·실시간 추론 아님'),'stats':{'documents':manifest['document_count'],'chunks':manifest['chunk_count'],'security_documents':manifest['security_documents'],'security_chunks':manifest['security_chunks'],'questions':summary['unique_questions'],'generated':summary['counts']['generated'],'denied':summary['counts']['access_denied']},'public_documents':docs,'cases':cases,'source_revision':'772bfd5','human_approval':'pending'}
 (ROOT/'demo-ui/spatial-poc/dist/rag-observatory.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8');db.close();print(len(cases),'L1 replay cases;',len(docs),'public document metadata nodes')
if __name__=='__main__':main()
