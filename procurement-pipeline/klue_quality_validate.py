"""Full artifact integrity validation after the locked evaluation."""
import json,subprocess
from klue_quality import *
def main():
 p=protocol();sel=load(OUT/'selection.json');assert sel['protocol_sha256']==file_sha(OUT/'protocol.json');assert sel['runner_sha256']==file_sha(ROOT/'procurement-pipeline/klue_quality.py')
 rows=labels();slots=0;window_count=0;times=0;peak=0
 for q in p['split']:
  x=inputs(q);assert sha(x['actual_answer'])==x['answer_sha256'];assert sha(x['context'])==x['context_sha256']
  raw=raw_read(q,sel['selected']['profile'],sel['selected']['model']);assert raw['answer_sha256']==x['answer_sha256'] and raw['context_sha256']==x['context_sha256']
  manifest=load(WORK/'matrices'/sel['selected']['model']/'manifest.json');assert raw['identity']==manifest['identity']
  for seg in raw['segments']:
   mat=np.asarray(seg['probabilities']);assert mat.shape==(len(seg['weights']),seg['end']-seg['start']);assert np.isfinite(mat).all() and (mat>=0).all() and (mat<=1).all()
  pred=pred_from(q,raw,sel['selected']['aggregation'],sel['selected']['threshold']);base=load(BASE/'predictions/klue/common512-v2'/f'{q}.json');assert pred['checked_ranges']==base['checked_ranges']
  assert all(x['actual_answer'][s:e].isspace() for s,e in pred['unchecked_ranges'])
  for s in pred['spans']:assert x['actual_answer'][s['start']:s['end']]==s['quote']
  pred.update(split=p['split'][q],status='completed',model='klue',checkpoint_sha256=sel['checkpoint_sha256'],configuration=sel['selected'],human_approval='pending')
  save(OUT/'predictions/all295'/f'{q}.json',pred)
  slots+=1;window_count+=raw['window_count'];times+=raw['seconds'];peak=max(peak,raw['peak_allocated'])
 protected=['project-docs/환각라벨링/detector-300-workstation-v1/results-v1','project-docs/환각라벨링/pilot-25-v1','project-docs/환각라벨링/pilot-25-human-review-v1']
 assert not subprocess.check_output(['git','diff','5381e0a','--',*protected])
 assert len(set(p['split']))==295
 train=set(selected_ids('train'));evaluation=set(selected_ids('evaluation'));dev=set(selected_ids('dev'));assert not train&evaluation and not dev&evaluation
 for f in (OUT/'training').glob('epoch*.json'):assert set(load(f)['train_question_ids'])==train
 assert file_sha(MODEL/'model.safetensors')==load(OUT/'diagnostics.json')['model_sha256']
 assert not load(OUT/'answer_similarity_audit.json')['cross_split_pairs']
 save(OUT/'validation.json',dict(completed_selected_slots=slots,failed=0,non_whitespace_unchecked=0,full_same_baseline_coverage=True,window_count=window_count,record_wall_seconds_sum=times,peak_allocated_bytes=peak,baseline_and_pilot_preserved=True,train_dev_evaluation_counts=p['counts'],frozen_selection_commit='831cf07',tests='run test_detector300*.py and test_klue_quality.py',original_weights_preserved=True,original_llama_server_preserved=Path('/proc/4922/comm').read_text().strip()=='llama-server',final_gold_count=0,all295_not_independent_score='train182 seen by fine-tuning; only evaluation63 used for final paired comparison'))
 print('verified selected 295, original artifacts, coverage and split')
if __name__=='__main__':main()
