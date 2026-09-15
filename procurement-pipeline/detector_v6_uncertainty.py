"""Bid-group bootstrap for the exposed paired comparison; not independent-test CI."""
import numpy as np
import detector_v6_generate as g
from detector300_score import prf,score_one

def run():
 report=g.load(g.OUT/'abcd_comparison.json');protocol=g.load(g.OUT/'protocol.json');mapping={q:i for i,group in enumerate(protocol['groups']) for q in group};rng=np.random.default_rng(916);out={}
 for part in ['train','dev','evaluation']:
  out[part]={}
  for arm in ['A','B','C','D']:
   rows=g.load(g.OUT/'comparison_rows'/f'{part}-{arm}.json');groups=sorted({mapping[r['question_id']] for r in rows});vectors=[]
   for grp in groups:
    rs=[r for r in rows if mapping[r['question_id']]==grp];vectors.append([sum(r['answer_presence'][z] for r in rs) for z in ['tp','fp','fn']]+[sum(r['answer_tn'] for r in rs)]+[sum(r['characters'][z] for r in rs) for z in ['tp','fp','fn']])
   if not vectors:continue
   a=np.array(vectors);samples=a[rng.integers(0,len(a),size=(2000,len(a)))].sum(1);stats={}
   for name,values in [('answer_recall',samples[:,0]/np.maximum(1,samples[:,0]+samples[:,2])),('normal_fpr',samples[:,1]/np.maximum(1,samples[:,1]+samples[:,3])),('character_f1',2*samples[:,4]/np.maximum(1,2*samples[:,4]+samples[:,5]+samples[:,6]))]:
    # Undefined denominators excluded from confidence intervals.
    denom=samples[:,0]+samples[:,2] if name=='answer_recall' else samples[:,1]+samples[:,3] if name=='normal_fpr' else 2*samples[:,4]+samples[:,5]+samples[:,6];valid=values[denom>0];stats[name]=dict(interval95=np.quantile(valid,[.025,.975]).tolist() if len(valid) else None,valid_resamples=len(valid))
   out[part][arm]=dict(groups=len(groups),answers=len(rows),metrics=stats)
 g.save(g.OUT/'group_bootstrap.json',dict(seed=916,resamples=2000,unit='frozen bid/leakage group',scope='legacy masked metrics on agent labels; exposed comparison; not generalization confidence; intervals exclude undefined denominators',results=out))
 # Same unchanged predictions scored against both versions of explicitly revised new labels.
 changes=[]
 for path in (g.OUT/'new_label_revision_history').glob('*.json'):
  history=g.load(path);old=history['before'];q=old['question_id'];new=g.load(g.OUT/'new_agent_labels'/f'{q}.json');a=g.load(g.WORK/'generated'/f'{q}.json')['actual_answer'];models={}
  for model in ['mil3','contrast3']:
   pred=g.load(g.OUT/'new_predictions'/model/f'{q}.json');models[model]=dict(before=score_one(old,pred,a),after=score_one(new,pred,a))
  changes.append(dict(question_id=q,reason=history['reason'],same_predictions=True,scores=models))
 g.save(g.OUT/'label_revision_effect.json',dict(original_labels_changed=False,new_label_changes=changes))
if __name__=='__main__':run()
