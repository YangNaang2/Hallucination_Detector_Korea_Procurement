"""Audit originals, training provenance and generation progress without inventing labels."""
import json,subprocess
from pathlib import Path
import klue_v6_select as s
import detector_v6_generate as g
k=s.k

def run():
 policy=g.load(g.OUT/'protocol.json');assert policy['v3']['source_sha256']==g.file_sha(g.ROOT/'procurement-pipeline/klue_v6_train.py');assert policy['v3']['synthetic_source_sha256']==g.file_sha(g.ROOT/'procurement-pipeline/klue_v6_synthetic.py')
 cases=g.load(k.WORK/'synthetic-cases.json');train=set(k.selected_ids('train'))
 for c in cases:
  assert c['source_question_id'] in train;x=k.inputs(c['source_question_id']);assert c['source_quote'] in x['context'];assert c['context_sha256']==x['context_sha256']
  if c['kind']=='exact_supported_source':assert c['answer']==c['source_quote'] and c['positive_range'] is None
  else:a,b=c['positive_range'];assert c['answer'][a:b] not in x['context']
 assert not subprocess.check_output(['git','diff','83a8964','--',*[str(g.V1.parent/f'results-v{i}') for i in range(1,6)],str(g.V1.parent/'selected_inputs.json')])
 selected=g.load(g.OUT/'selection.json')['selected'];old_times=[]
 for q in k.selected_ids('train,dev,evaluation'):
  x=k.inputs(q);r=s.raw(q,selected['model']);assert r['answer_sha256']==g.sha(x['actual_answer']) and r['context_sha256']==g.sha(x['context']);pred=k.pred_from(q,r,selected['aggregation'],selected['threshold']);baseline=g.load(g.V1/'predictions/klue/common512-v2'/f'{q}.json');assert pred['checked_ranges']==baseline['checked_ranges'];pred.update(configuration=selected,status='completed',human_approved=False);g.save(g.OUT/'original_predictions'/f'{q}.json',pred);old_times.append(r['seconds'])
 ablation,rows=s.evaluate(k.selected_ids('evaluation'),dict(selected,model='fp1'));g.save(g.OUT/'matched_operating_point_ablation.json',dict(v5_at_same_operating_point=ablation,v6=g.load(g.OUT/'original_comparison.json')['selected'],interpretation='same profile/aggregation/threshold; original revised labels and synthetic augmentation changes bundled; no new configuration selection'))
 generated=list((g.WORK/'generated').glob('*.json'));statuses={};newslots={};unchecked_glyphs=[]
 for path in generated:
  r=g.load(path);x=g.load(g.PRIVATE/'inputs'/path.name);assert r['identity']==g.jsha(g.load(g.OUT/'generation_policy.json'));assert g.sha(r['actual_answer'])==r['answer_sha256'];assert r['context_sha256']==x['context_sha256'];statuses[r['finish_reason']]=statuses.get(r['finish_reason'],0)+1
 for model in ['mil3',selected['model']]:
  ps=list((g.OUT/'new_predictions'/model).glob('*.json'));newslots[model]=len(ps)
  for path in ps:
   p=g.load(path);a=g.load(g.WORK/'generated'/path.name);assert p['answer_sha256']==a['answer_sha256'];assert all(a['actual_answer'][x['start']:x['end']]==x['quote'] for x in p['spans'])
   for b,e in p['unchecked_ranges']:
    text=a['actual_answer'][b:e]
    if not text.isspace():
     assert all(c.isspace() or c=='\uf06d' for c in text),(path.name,b,e,repr(text))
     unchecked_glyphs.append(dict(model=model,question_id=path.stem,start=b,end=e,text=text,reason='tokenizer omitted private-use document bullet; remains unchecked, not counted as covered'))
 agent=list((g.OUT/'new_agent_labels').glob('*.json'))
 for path in agent:
  l=g.load(path);a=g.load(g.WORK/'generated'/path.name);assert l['answer_sha256']==a['answer_sha256'];assert all(a['actual_answer'][s['start']:s['end']]==s['quote'] for s in l['spans'])
 g.save(g.OUT/'validation-progress.json',dict(original_prediction_slots=295,original_inputs_and_results_preserved=True,synthetic_training_cases=len(cases),train_only=True,generated=len(generated),generation_status=statuses,new_prediction_slots=newslots,unchecked_private_use_glyphs=unchecked_glyphs,agent_reviewed=len(agent),human_gold=0,original_inference_seconds=sum(old_times),llama_server_preserved=Path('/proc/4922/comm').read_text().strip()=='llama-server',complete=len(generated)==295 and all(v==295 for v in newslots.values()) and len(agent)==295))
 print(g.load(g.OUT/'validation-progress.json'))
if __name__=='__main__':run()
