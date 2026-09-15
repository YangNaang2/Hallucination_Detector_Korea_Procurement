"""Select false-positive control on dev only; preserve fixed comparison domain."""
import argparse
import numpy as np
import klue_v6_train as t
k=t.k
from detector300_score import aggregate,score_one,prf

def raw(q,model):
 work=k.ROOT/'work/quality-v3' if model=='mil3' else k.ROOT/'work/quality-v5' if model=='fp1' else k.WORK
 return k.load(work/'matrices'/model/'repeat192'/f'{q}.json')
def evaluate(qs,config):
 rows=[]
 for q in qs:
  x=k.inputs(q);p=k.pred_from(q,raw(q,config['model']),config['aggregation'],config['threshold']);base=k.load(k.BASE/'predictions/klue/common512-v2'/f'{q}.json');assert p['checked_ranges']==base['checked_ranges'];rows.append(score_one(k.labels()[q],p,x['actual_answer'],k.expand(base['checked_ranges'],len(x['actual_answer']))))
 return aggregate(rows),rows

def select():
 policy=dict(models=['fp1','contrast1','contrast2','contrast3'],thresholds=k.THRESHOLDS+[.95,.97,.99,.995,.999],aggregations=k.AGGS,selection='dev answer false-alarm rate <= .20; maximize answer F1 then character F1; success requires recall >= .50; ties first candidate',source_sha256=k.file_sha(__file__),baseline='v3 mil3 min2 .5',labels='frozen v1 comparison labels; v4 revisions only used for training')
 dest=k.OUT/'selection_policy.json'
 if dest.exists():assert k.load(dest)==policy
 else:k.save(dest,policy)
 qs=k.selected_ids('dev');ls=k.labels();curves=[]
 for model in policy['models']:
  for agg in policy['aggregations']:
   arrays=[];truth=[]
   for q in qs:
    x=k.inputs(q);r=raw(q,model);v=k.combine(r,agg);n=len(x['actual_answer']);cv=np.full(n,np.nan)
    for (a,b),z in zip(r['offsets'],v):cv[a:b]=np.fmax(cv[a:b],z)
    l=ls[q];mask=k.expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in k.MASK],n);gold=k.expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in k.POS],n);reviewed=k.expand(l['reviewed_ranges'],n);valid=[i for i in range(n) if np.isfinite(cv[i]) and i in reviewed and i not in mask];arrays.append(cv[valid]);truth.append(np.array([i in gold for i in valid]))
   maxes=np.array([a.max() for a in arrays]);ys=np.array([y.any() for y in truth]);vv=np.concatenate(arrays);yy=np.concatenate(truth)
   for threshold in policy['thresholds']:
    ap=maxes>=threshold;z=vv>=threshold;tp=int((ap&ys).sum());fp=int((ap&~ys).sum());fn=int((~ap&ys).sum());tn=int((~ap&~ys).sum());curves.append(dict(model=model,profile='repeat192',aggregation=agg,threshold=threshold,answer=prf(tp,fp,fn),tn=tn,false_alarm_rate=fp/(fp+tn),characters=prf(int((z&yy).sum()),int((z&~yy).sum()),int((~z&yy).sum()))))
 eligible=[r for r in curves if r['false_alarm_rate']<=.2];best=max(eligible,key=lambda r:(r['answer']['f1'] or 0,r['characters']['f1'] or 0));full,_=evaluate(qs,best);assert full['characters']==best['characters'] and full['answer_presence']==best['answer'] and full['answer_tn']==best['tn'];k.save(k.OUT/'dev_curves.json',curves);k.save(k.OUT/'selection.json',dict(selected=best,policy_sha256=k.file_sha(dest),dev_success=best['answer']['recall']>=.5));print(best)

def report():
 assert k.load(k.OUT/'selection_policy.json')['source_sha256']==k.file_sha(__file__)
 s=k.load(k.OUT/'selection.json');assert s['policy_sha256']==k.file_sha(k.OUT/'selection_policy.json');config=s['selected'];old,oldrows=evaluate(k.selected_ids('evaluation'),dict(model='mil3',aggregation='min2',threshold=.5));new,rows=evaluate(k.selected_ids('evaluation'),config)
 fpr=new['answer_presence']['fp']/(new['answer_presence']['fp']+new['answer_tn']);success=fpr<=.2 and new['answer_presence']['recall']>=.5
 k.save(k.OUT/'original_comparison.json',dict(baseline=old,selected=new,false_alarm_rate=fpr,success=success,baseline_rows=oldrows,selected_rows=rows,human_gold=False,independent_test=False));print(dict(baseline=old,selected=new,false_alarm_rate=fpr,success=success))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['select','report']);a=p.parse_args();select() if a.command=='select' else report()
