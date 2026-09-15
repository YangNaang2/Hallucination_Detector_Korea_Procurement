"""Development selection and one-time locked evaluation. Never tunes on evaluation."""
import argparse,json,collections
import numpy as np
from klue_quality import *
from klue_quality_rules import rule_spans

def rows_config(c,part,with_rules=False):
 qs=selected_ids(part);ls=labels();rows=[];preds=[]
 for q in qs:
  x=inputs(q);p=pred_from(q,raw_read(q,c['profile'],c['model']),c['aggregation'],c['threshold'])
  if with_rules:
   rr=rule_spans(x['actual_answer'],x['context']);p['rule_spans']=rr
   covered={i for s in p['spans']+rr for i in range(s['start'],s['end'])}
   p['spans']=[dict(start=s,end=e,quote=x['actual_answer'][s:e]) for s,e in ranges(covered)]
  base=load(BASE/'predictions/klue/common512-v2'/f'{q}.json');domain=expand(base['checked_ranges'],len(x['actual_answer']))
  assert expand(p['checked_ranges'],len(x['actual_answer']))==domain
  rows.append(score_one(ls[q],p,x['actual_answer'],domain));preds.append(p)
 return aggregate(rows),rows,preds
BASELINE=dict(model='base',profile='saved',aggregation='min',threshold=.5)
def select():
 dest=OUT/'selection.json'
 if dest.exists():print('already locked');return
 candidates=[]
 for model in ['base','epoch1','epoch2']:
  f=OUT/'experiments'/f'{model}-dev-best.json'
  if f.exists() and load(f):candidates.append(load(f))
 assert len(candidates)==3,'complete all declared development runs first'
 baseline,_,_=rows_config(BASELINE,'dev');chosen=max(candidates,key=lambda c:(c['characters']['f1'] or 0,-c['windows'],c['threshold']))
 if chosen['characters']['f1']<baseline['characters']['f1']:chosen=BASELINE
 plain,_,_=rows_config(chosen,'dev');ruled,_,_=rows_config(chosen,'dev',True)
 use_rules=(ruled['characters']['precision'] or 0)>=.4 and ruled['characters']['f1']>plain['characters']['f1']+.005
 decision=dict(selected=chosen,use_rules=use_rules,baseline_dev=baseline,selected_dev=plain,rules_dev=ruled,selection_source='dev only; P>=.40 then maximum char micro F1',locked_before_evaluation=True,protocol_sha256=file_sha(OUT/'protocol.json'),runner_sha256=file_sha(ROOT/'procurement-pipeline/klue_quality.py'),rules_sha256=file_sha(ROOT/'procurement-pipeline/klue_quality_rules.py'),checkpoint_sha256=file_sha((MODEL if chosen['model']=='base' else WORK/'checkpoints'/chosen['model'])/'model.safetensors'))
 save(dest,decision);print(json.dumps(decision,ensure_ascii=False,indent=2))
def bootstrap(a,b):
 by_a={r['question_id']:r for r in a};by_b={r['question_id']:r for r in b};groups=[[q for q in g if q in by_a] for g in protocol()['groups']];groups=[g for g in groups if g];rng=np.random.default_rng(913);ds=[]
 for _ in range(2000):
  qq=[q for i in rng.integers(0,len(groups),len(groups)) for q in groups[i]]
  def f(by):
   tp=sum(by[q]['characters']['tp'] for q in qq);fp=sum(by[q]['characters']['fp'] for q in qq);fn=sum(by[q]['characters']['fn'] for q in qq);return 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0
  ds.append(f(by_b)-f(by_a))
 return dict(unit='grouped notices and near duplicates',replicates=2000,seed=913,f1_delta_percentile95=np.quantile(ds,[.025,.975]).tolist(),caution='conditional on provisional labels and previously exposed material')
def final():
 decision=load(OUT/'selection.json');assert decision['runner_sha256']==file_sha(ROOT/'procurement-pipeline/klue_quality.py');assert decision['rules_sha256']==file_sha(ROOT/'procurement-pipeline/klue_quality_rules.py')
 c=decision['selected'];baseline,br,bp=rows_config(BASELINE,'evaluation');improved,ir,ip=rows_config(c,'evaluation');combined,cr,cp=rows_config(c,'evaluation',True)
 save(OUT/'evaluation/baseline-per-answer.json',br);save(OUT/'evaluation/selected-per-answer.json',ir);save(OUT/'evaluation/rules-per-answer.json',cr)
 for p in ip:save(OUT/'predictions/evaluation'/f'{p["question_id"]}.json',p)
 report=dict(baseline=baseline,selected_model_only=improved,selected_with_rules=combined,deploy_rules=decision['use_rules'],bootstrap=bootstrap(br,ir),final_gold_count=0,independent_test=False,selection=decision,by_company={},by_length={},cases=[])
 for name,rows in [('baseline',br),('selected',ir),('rules',cr)]:
  report['by_company'][name]={company:aggregate([r for r in rows if f'-{company}-' in r['question_id']]) for company in ['C01','C02','C03','C04','C05']}
  report['by_length'][name]={key:aggregate([r for r in rows if (r['answer_characters']>=600)==flag]) for key,flag in [('lt600',False),('ge600',True)]}
  # Error subtype recall and FN/FP remain distinct; no subtype precision invention.
 report['by_type']={};ls=labels()
 for name,preds in [('baseline',bp),('selected',ip)]:
  report['by_type'][name]={}
  for typ in sorted(POS):
   tp=fn=0
   for p in preds:
    q=p['question_id'];x=inputs(q);n=len(x['actual_answer']);l=ls[q];domain=expand(p['checked_ranges'],n)-expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in MASK],n)
    gold=expand([[s['start'],s['end']] for s in l['spans'] if s['label']==typ],n)&domain;guess=expand([[s['start'],s['end']] for s in p['spans']],n)&domain;tp+=len(gold&guess);fn+=len(gold-guess)
   report['by_type'][name][typ]=dict(tp=tp,fn=fn,recall=tp/(tp+fn) if tp+fn else None)
 for b,r in zip(br,ir):
  delta=(r['characters']['fp']+r['characters']['fn'])-(b['characters']['fp']+b['characters']['fn'])
  report['cases'].append(dict(question_id=r['question_id'],error_character_delta=delta,baseline=b['characters'],selected=r['characters'],fn_ranges=r['fn_ranges'],fp_ranges=r['fp_ranges']))
 report['cases']=sorted(report['cases'],key=lambda r:r['error_character_delta']);save(OUT/'evaluation/summary.json',report)
 # Ablations are predeclared comparisons after selection, not further model selection.
 ablations=[BASELINE,dict(model='base',profile='saved',aggregation='min',threshold=load(OUT/'experiments/base-dev-best.json')['threshold'])]
 # More relevant threshold-only ablation is selected separately on its own dev curve.
 saved=[r for r in load(OUT/'experiments/base-dev-curves.json') if r['profile']=='saved' and (r['characters']['precision'] or 0)>=.4]
 ablations[1]=max(saved,key=lambda r:r['characters']['f1'])
 if c['profile']!='saved':ablations.append(dict(model='base',profile=c['profile'],aggregation=c['aggregation'],threshold=c['threshold']))
 ab=[]
 for cfg in ablations:
  result,_,_=rows_config(cfg,'evaluation');ab.append(dict(config=cfg,result=result))
 save(OUT/'evaluation/ablations.json',ab)
 print(json.dumps({k:report[k] for k in ['baseline','selected_model_only','selected_with_rules','bootstrap']},ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['select','final']);a=p.parse_args();select() if a.command=='select' else final()
