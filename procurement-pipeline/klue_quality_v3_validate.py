"""Validate all selected predictions and produce paired historical diagnostics."""
import json,random,subprocess
from pathlib import Path
import numpy as np
import klue_quality_v3_claims as c
k=c.k;load=c.load;save=c.save

def main():
 p=k.protocol();sel=load(k.OUT/'claim_selection.json');s=sel['selected'];assert s['mode']=='raw'
 assert sel['policy_sha256']==k.file_sha(k.OUT/'claim_policy.json')
 assert load(k.OUT/'claim_policy.json')['source_sha256']==k.file_sha(k.ROOT/'procurement-pipeline/klue_quality_v3_claims.py')
 assert p['v3']['source_sha256']==k.file_sha(k.ROOT/'procurement-pipeline/klue_quality_v3.py')
 assert p['split']==load(c.v.OLD/'protocol.json')['split']
 assert not subprocess.check_output(['git','diff','99de4b7','--',str(k.BASE),str(c.v.OLD)])
 folder=k.WORK/'checkpoints'/s['model'];ck=k.file_sha(folder/'model.safetensors');assert ck==load(k.OUT/'training'/f"{s['model']}.json")['checkpoint_sha256']
 assert k.file_sha(k.MODEL/'model.safetensors')=='74523acd66c826c32d9d34954b99e41667286dec3f1e027d708266a7591dd782'
 train=set(k.selected_ids('train'))
 for f in (k.OUT/'training').glob('*.json'):assert set(load(f)['train_ids'])==train
 manifest=load(k.WORK/'matrices'/s['model']/'manifest.json');assert manifest['weights_sha256']==ck
 total=0;peak=0;windows=0
 for q in p['split']:
  x=k.inputs(q);r=c.raw(q,s['model']);assert k.sha(x['actual_answer'])==x['answer_sha256']==r['answer_sha256'];assert k.sha(x['context'])==x['context_sha256']==r['context_sha256'];assert r['identity']==manifest['identity']
  for seg in r['segments']:
   a=np.asarray(seg['probabilities']);assert a.shape==(len(seg['weights']),seg['end']-seg['start']);assert np.isfinite(a).all() and (a>=0).all() and (a<=1).all()
  pred=c.predict(q,s);base=load(k.BASE/'predictions/klue/common512-v2'/f'{q}.json');assert pred['checked_ranges']==base['checked_ranges'];assert all(x['actual_answer'][a:b].isspace() for a,b in pred['unchecked_ranges'])
  for sp in pred['spans']:assert x['actual_answer'][sp['start']:sp['end']]==sp['quote']
  pred.update(configuration=s,checkpoint_sha256=ck,split=p['split'][q],human_approval='pending',status='completed');save(k.OUT/'predictions/all295'/f'{q}.json',pred)
  total+=r['seconds'];peak=max(peak,r['peak_allocated']);windows+=r['window_count']
 save(k.OUT/'runtime_selection.json',dict(selected=dict(s,profile='repeat192'),checkpoint_sha256=ck,use_rules=False))
 old=load(c.v.OLD/'evaluation/selected-per-answer.json');new=load(k.OUT/'regression.json')['per_answer'];ob={r['question_id']:r for r in old};nb={r['question_id']:r for r in new};assert set(ob)==set(nb)
 groups=[[q for q in g if q in nb] for g in p['groups']];groups=[g for g in groups if g];rng=random.Random(916);deltas=[]
 for _ in range(2000):
  qs=[q for g in rng.choices(groups,k=len(groups)) for q in g];deltas.append(c.aggregate([nb[q] for q in qs])['characters']['f1']-c.aggregate([ob[q] for q in qs])['characters']['f1'])
 by={};questions={x['question_id']:x for x in map(json.loads,(k.ROOT/'project-docs/평가데이터/v2/evaluation/questions_300.jsonl').read_text().splitlines())}
 for company in sorted({questions[q]['company_id'] for q in nb}):by[company]={name:c.aggregate([r for r in rows if questions[r['question_id']]['company_id']==company]) for name,rows in [('v2',old),('v3',new)]}
 lengths={name:{group:c.aggregate([r for r in rows if (r['answer_characters']>=600)==long]) for group,long in [('lt600',False),('ge600',True)]} for name,rows in [('v2',old),('v3',new)]}
 type_recall={}
 for typ in sorted(k.POS):
  tp=fn=0
  for q in nb:
   l=k.labels()[q];a=k.inputs(q)['actual_answer'];domain=k.expand(load(k.BASE/'predictions/klue/common512-v2'/f'{q}.json')['checked_ranges'],len(a));domain &= k.expand(l['reviewed_ranges'],len(a));domain-=k.expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in k.MASK],len(a));gold=k.expand([[s['start'],s['end']] for s in l['spans'] if s['label']==typ],len(a))&domain;pred=k.expand([[s['start'],s['end']] for s in c.predict(q,sel['selected'])['spans']],len(a))&domain;tp+=len(gold&pred);fn+=len(gold-pred)
  type_recall[typ]=dict(tp=tp,fn=fn,recall=tp/(tp+fn) if tp+fn else None)
 changes=[dict(question_id=q,old_errors=ob[q]['characters']['fp']+ob[q]['characters']['fn'],new_errors=nb[q]['characters']['fp']+nb[q]['characters']['fn']) for q in nb];changes.sort(key=lambda r:r['new_errors']-r['old_errors'])
 save(k.OUT/'comparison.json',dict(v2=c.aggregate(old),v3=c.aggregate(new),by_company=by,by_length=lengths,v3_by_error_type=type_recall,improved_cases=changes[:5],worsened_cases=changes[-5:],paired_group_bootstrap=dict(replicates=2000,delta_f1_95_percentile=np.quantile(deltas,[.025,.975]).tolist(),limitation='conditional on unapproved labels and exposed data; not independent evidence')))
 save(k.OUT/'validation.json',dict(completed=295,failed=0,windows=windows,inference_seconds=total,peak_allocated_bytes=peak,all_nonwhitespace_checked=True,original_inputs_labels_weights_and_v2_preserved=True,split_unchanged=True,selection_commit='76d9b1e',human_gold_count=0,llama_server_preserved=Path('/proc/4922/comm').read_text().strip()=='llama-server'))
 print(json.dumps(load(k.OUT/'validation.json')))
if __name__=='__main__':main()
