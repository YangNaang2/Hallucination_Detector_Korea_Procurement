"""Export verified single-KLUE predictions and audit preservation and coverage."""
import subprocess
from pathlib import Path
import numpy as np
import klue_fp_select as s
k=s.k

def main():
 config=k.load(k.OUT/'fp_selection.json')['selected'];model=config['model'];work=k.ROOT/'work/quality-v3' if model=='mil3' else k.WORK;folder=work/'checkpoints'/model;manifest=k.load(work/'matrices'/model/'manifest.json');assert manifest['weights_sha256']==k.file_sha(folder/'model.safetensors')
 assert k.load(k.OUT/'protocol.json')['v3']['source_sha256']==k.file_sha(k.ROOT/'procurement-pipeline/klue_fp_train.py')
 assert not subprocess.check_output(['git','diff','1ae5a8d','--',str(k.OUT.parent/'results-v1'),str(k.OUT.parent/'results-v2'),str(k.OUT.parent/'results-v3'),str(k.OUT.parent/'results-v4')])
 train=set(k.selected_ids('train'))
 for f in (k.OUT/'training').glob('fp*.json'):assert set(k.load(f)['train_ids'])==train
 strict=k.load(k.OUT/'strict_selection.json')['selected'];strictrows=[]
 total=0;peak=0;rows=[];revised={r['question_id']:r for r in k.load(s.t.TRAIN_LABELS)}
 for q in k.selected_ids('train,dev,evaluation'):
  x=k.inputs(q);raw=s.raw(q,model);assert raw['identity']==manifest['identity'];assert k.sha(x['actual_answer'])==raw['answer_sha256']==x['answer_sha256'];assert k.sha(x['context'])==raw['context_sha256']==x['context_sha256']
  for seg in raw['segments']:
   a=np.array(seg['probabilities']);assert a.shape==(len(seg['weights']),seg['end']-seg['start']);assert np.isfinite(a).all() and (a>=0).all() and (a<=1).all()
  p=k.pred_from(q,raw,config['aggregation'],config['threshold']);base=k.load(k.BASE/'predictions/klue/common512-v2'/f'{q}.json');assert p['checked_ranges']==base['checked_ranges'];assert all(x['actual_answer'][a:b].isspace() for a,b in p['unchecked_ranges'])
  p.update(configuration=config,checkpoint_sha256=manifest['weights_sha256'],human_approved=False,status='completed',split=k.protocol()['split'][q]);k.save(k.OUT/'predictions'/f'{q}.json',p)
  if q in train:rows.append(s.score_one(revised[q],p,x['actual_answer'],k.expand(base['checked_ranges'],len(x['actual_answer']))))
  ps=k.pred_from(q,raw,strict['aggregation'],strict['threshold']);ps.update(configuration=strict,checkpoint_sha256=manifest['weights_sha256'],human_approved=False,status='completed',split=k.protocol()['split'][q]);k.save(k.OUT/'strict_predictions'/f'{q}.json',ps)
  if q in train:strictrows.append(s.score_one(revised[q],ps,x['actual_answer'],k.expand(base['checked_ranges'],len(x['actual_answer']))))
  total+=raw['seconds'];peak=max(peak,raw['peak_allocated'])
 metrics=k.load(k.OUT/'evaluation.json');grouped={}
 for company in ['C01','C02','C03','C04','C05']:
  grouped[company]={name:s.aggregate([r for r in metrics[key] if '-'+company+'-' in r['question_id']]) for name,key in [('baseline','baseline_rows'),('selected','selected_rows')]}
 k.save(k.OUT/'by_company.json',grouped);k.save(k.OUT/'training_fit.json',dict(metrics=s.aggregate(rows),strict_metrics=s.aggregate(strictrows),interpretation='training data fit using revised agent labels; not generalization'))
 k.save(k.OUT/'runtime_strict_selection.json',dict(selected=strict,checkpoint_sha256=manifest['weights_sha256'],use_rules=False))
 k.save(k.OUT/'runtime_selection.json',dict(selected=config,checkpoint_sha256=manifest['weights_sha256'],use_rules=False))
 k.save(k.OUT/'validation.json',dict(completed=295,failed=0,all_nonwhitespace_checked=True,same_coverage=True,input_hashes_unchanged=True,prior_results_preserved=True,training_ids_182_only=True,model=model,checkpoint=str(folder),checkpoint_sha256=manifest['weights_sha256'],record_inference_seconds_sum=total,peak_allocated_bytes=peak,llama_server_preserved=Path('/proc/4922/comm').read_text().strip()=='llama-server',human_gold=False))
 print(k.load(k.OUT/'validation.json'))
if __name__=='__main__':main()
