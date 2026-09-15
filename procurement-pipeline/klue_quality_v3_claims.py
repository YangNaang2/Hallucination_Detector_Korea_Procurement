"""Dev-only selection of contiguous claim scores; no extra model or labels."""
import argparse, copy, json, re
import numpy as np
import klue_quality_v3 as v
k=v.k
from detector300 import load,save,file_sha
from detector300_score import aggregate,score_one,prf

def raw(q,model):
 folder=v.OLDWORK if model=='epoch2' else k.WORK
 return load(folder/'matrices'/model/'repeat192'/f'{q}.json')

def smooth(r,answer,agg,mode):
 vals=k.combine(r,agg)
 if mode!='raw':
  pattern=r'\n+|[.!?。](?:\s+|$)' if mode=='sentence_mean' else r'\n+|[,;.!?。](?:\s+|$)'
  bounds=[0]+[m.end() for m in re.finditer(pattern,answer)]+[len(answer)]
  for a,b in zip(bounds,bounds[1:]):
   ix=[i for i,(s,e) in enumerate(r['offsets']) if a<=s<b]
   if ix:vals[ix]=float(np.mean(vals[ix]))
 return dict(offsets=r['offsets'],segments=[dict(start=0,end=len(vals),weights=[1],probabilities=[vals.tolist()])])

def predict(q,c):return k.pred_from(q,smooth(raw(q,c['model']),k.inputs(q)['actual_answer'],c['aggregation'],c['mode']),'min',c['threshold'])

def choose():
 policy=k.OUT/'claim_policy.json'
 if not policy.exists():save(policy,dict(models=['epoch2','mil1','mil2','mil3'],modes=['raw','sentence_mean','clause_mean'],aggregations=k.AGGS,thresholds=k.THRESHOLDS,criterion='dev precision >= .4 then max character F1; ties raw, fewer windows, higher threshold',source_sha256=file_sha(__file__),regression='Only after selection lock; exposed historical 63'))
 assert load(policy)['source_sha256']==file_sha(__file__)
 ls=k.labels();results=[]
 for model in load(policy)['models']:
  for agg in k.AGGS:
   for mode in load(policy)['modes']:
    vs=[];ys=[]
    for q in k.selected_ids('dev'):
     x=k.inputs(q);r=smooth(raw(q,model),x['actual_answer'],agg,mode);vals=k.combine(r,'min');n=len(x['actual_answer']);cv=np.full(n,np.nan)
     for (s,e),p in zip(r['offsets'],vals):cv[s:e]=np.fmax(cv[s:e],p)
     mask=k.expand([[s['start'],s['end']] for s in ls[q]['spans'] if s['label'] in k.MASK],n);gold=k.expand([[s['start'],s['end']] for s in ls[q]['spans'] if s['label'] in k.POS],n)
     valid=[i for i in range(n) if np.isfinite(cv[i]) and i not in mask];vs.extend(cv[valid]);ys.extend(i in gold for i in valid)
    a=np.array(vs);y=np.array(ys)
    for t in k.THRESHOLDS:
     z=a>=t;results.append(dict(model=model,aggregation=agg,mode=mode,threshold=t,characters=prf(int((z&y).sum()),int((z&~y).sum()),int((~z&y).sum()))))
 save(k.OUT/'experiments/claim-dev-curves.json',results)
 eligible=[r for r in results if (r['characters']['precision'] or 0)>=.4]
 best=max(eligible,key=lambda r:(r['characters']['f1'] or 0,r['mode']=='raw',r['threshold']))
 save(k.OUT/'claim_selection.json',dict(selected=best,source='dev50 only',policy_sha256=file_sha(policy),human_gold=False,independent_test=False));print(json.dumps(best))

def report():
 c=load(k.OUT/'claim_selection.json')['selected'];rows=[]
 for q in k.selected_ids('evaluation'):
  x=k.inputs(q);p=predict(q,c);base=load(k.BASE/'predictions/klue/common512-v2'/f'{q}.json');domain=k.expand(base['checked_ranges'],len(x['actual_answer']));assert k.expand(p['checked_ranges'],len(x['actual_answer']))==domain
  rows.append(score_one(k.labels()[q],p,x['actual_answer'],domain));save(k.OUT/'predictions'/f'{q}.json',p)
 save(k.OUT/'regression.json',dict(config=c,metrics=aggregate(rows),per_answer=rows,human_gold=False,independent_test=False));print(json.dumps(aggregate(rows)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['choose','report']);a=p.parse_args();choose() if a.command=='choose' else report()
