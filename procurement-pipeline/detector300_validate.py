"""Validate actual frozen inputs, annotation anchors and all saved prediction slots."""
import argparse, collections, re, sqlite3, subprocess
from detector300 import ROOT, OUT, PRIVATE, load, save, sha, file_sha, frozen
from detector300_score import expand, validate, MODELS

def main():
 p=argparse.ArgumentParser();p.add_argument('--index',required=True);p.add_argument('--source-cache',required=True);a=p.parse_args()
 from pathlib import Path
 con=sqlite3.connect(Path(a.index).resolve().as_uri()+'?mode=ro',uri=True)
 import json
 corpus={k:json.loads(v) for k,v in con.execute('SELECT chunk_id,payload FROM corpus')};con.close()
 sources={r['sha256']:r['text'] for r in load(a.source_cache)}
 labels=load(OUT/'annotation/agent_draft/labels.json');proposals=load(OUT/'annotation/adjudicated/proposals.json')
 targets={r['question_id']:r for r in frozen() if r['detector_target']}
 assert len(targets)==295 and {r['question_id'] for r in labels}==set(targets)
 assert len(labels)==len(proposals)==295
 anchors=chunks=slots=probabilities=0;counts=collections.Counter()
 for row in labels:
  q=row['question_id'];x=load(PRIVATE/'inputs'/f'{q}.json');answer=x['actual_answer'];n=len(answer)
  assert sha(answer)==targets[q]['answer_sha256']==row['answer_sha256']
  assert sha(x['context'])==row['context_sha256']
  assert row['reviewed_ranges']==[[0,n]] and row['human_approval']=='pending' and not row['training_ready']
  for c in x['evidence']:
   chunk=corpus[c['chunk_id']];body=chunk['text']
   assert sha(body)==c['text_sha256']
   source=sources[chunk['sha256']] if chunk['security_level']=='L1' else load(ROOT/chunk['path'])['content']
   assert source[c['text_start']:c['text_end']]==body
   if c['company_id']:assert c['company_id']==targets[q]['company_id']
   chunks+=1
  if row['status']=='agent_reviewed':
   for e in row['evidence']:
    c=next(c for c in x['evidence'] if c['chunk_id']==e['chunk_id'] and c['citation']==e['citation'])
    m=re.search(r'^\['+str(c['citation'])+r'\][^\n]*\n(.*?)\n\[자료 '+str(c['citation'])+r' 끝\]',x['context'],re.S|re.M)
    assert m and m.group(1)==corpus[c['chunk_id']]['text']
    assert x['context'][e['context_start']:e['context_end']]==e['quote']
    assert c['text_start']+e['context_start']-m.start(1)==e['source_start']
    assert c['text_start']+e['context_end']-m.start(1)==e['source_end']
    assert c['text_sha256']==e['text_sha256'];anchors+=1
   for i,s in enumerate(row['spans']):
    for t in row['spans'][i+1:]:assert max(s['start'],t['start'])>=min(s['end'],t['end']),q
  for model in MODELS:
   pred=load(OUT/'predictions'/model/'common512-v2'/f'{q}.json')
   validate(row,pred,answer)
   manifest=load(OUT/'predictions'/model/'common512-v2'/'manifest.json') if (OUT/'predictions'/model/'common512-v2'/'manifest.json').exists() else None
   assert manifest and manifest['identity_sha256']==pred['identity_sha256']
   assert pred['model']==model and pred['run_id']=='common512-v2' and pred['status']=='completed'
   checked=expand(pred['checked_ranges'],n);unchecked=expand(pred['unchecked_ranges'],n)
   assert checked.isdisjoint(unchecked) and checked|unchecked==set(range(n))
   assert all(answer[i].isspace() for i in unchecked)
   probs=load(PRIVATE/'probabilities'/model/'common512-v2'/f'{q}.json');domain=set();positive=set()
   assert len(probs)==pred['answer_tokens']
   for s,e,v in probs:
    assert 0<=s<e<=n and 0<=v<=1
    domain.update(range(s,e))
    if v>=.5:positive.update(range(s,e))
   assert domain==checked
   assert positive==expand([[s['start'],s['end']] for s in pred['spans']],n)
   probabilities+=len(probs);slots+=1;counts[model]+=1
 for row in proposals:
  assert row['human_approval']=='pending' and row['reviewed_ranges']
  answer=load(PRIVATE/'inputs'/f'{row["question_id"]}.json')['actual_answer']
  for s in row['spans']:assert answer[s['start']:s['end']]==s['quote']
 protected=['project-docs/환각라벨링/pilot-25-v1','project-docs/환각라벨링/pilot-25-human-review-v1']
 assert not subprocess.check_output(['git','diff','6bfbc94','--',*protected],cwd=ROOT)
 denials=load(OUT/'inputs/denials.json');assert len(denials)==5 and all(d['status']=='verified' and d['llm_not_called'] and d['fixed_denial_only'] for d in denials)
 report=dict(reviewed_answers=295,unreviewed_answers=0,prediction_slots=slots,successful_prediction_records=dict(counts),manual_evidence_anchors_verified=anchors,canonical_chunks_verified=chunks,probability_offsets_verified=probabilities,non_whitespace_unchecked=0,pilot25_originals_unchanged=True,denials_verified=5,final_gold_count=0,human_approval_pending=295,index_sha256=file_sha(a.index),source_cache_sha256=file_sha(a.source_cache),checks=['canonical answer and context hashes','all 295 complete review ranges','citation-scoped anchors and canonical source offsets','no overlapping new manual spans','all 885 probability/coverage/threshold identities','preserved pilot25 against handoff commit','no inferred human approval'])
 save(OUT/'validation-final.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
