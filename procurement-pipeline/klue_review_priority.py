"""Single-KLUE review priority. Rank without labels; evaluate only afterwards."""
import argparse, math
import numpy as np
import klue_quality_v3_claims as c
k=c.k
OUT=k.OUT.parent/'results-v4'

def answer_score(raw,aggregation,reduction):
 v=k.combine(raw,aggregation)
 if reduction=='max':return float(v.max())
 if reduction=='mean':return float(v.mean())
 return float(np.sort(v)[-max(1,math.ceil(len(v)*.1)):].mean())

def ranked(scores):return sorted(scores,key=lambda q:(-scores[q],k.sha(q)))

def measure(scores,gold,budget):
 order=ranked(scores);n=len(order);count=math.floor(n*budget);chosen=set(order[:count]);pos={q for q in order if gold[q]};tp=len(chosen&pos);fp=count-tp;fn=len(pos)-tp;tn=n-len(pos)-fp
 return dict(answers=n,reviewed=count,positive_answers=len(pos),tp=tp,fp=fp,fn=fn,tn=tn,recall=tp/len(pos) if pos else None,precision=tp/count if count else None,false_alarm_rate=fp/(n-len(pos)) if n>len(pos) else None,random_expected_recall=count/n,maximum_possible_recall=min(count,len(pos))/len(pos) if pos else None)

def truths(qs):
 labels=k.labels();result={}
 for q in qs:
  x=k.inputs(q);base=k.load(k.BASE/'predictions/klue/common512-v2'/f'{q}.json');r=c.score_one(labels[q],base,x['actual_answer'],k.expand(base['checked_ranges'],len(x['actual_answer'])));result[q]=r['gold_positive']
 return result

def scores_for(qs,config):return {q:answer_score(c.raw(q,config['model']),config['aggregation'],config['reduction']) for q in qs}

def select():
 policy=dict(primary_budget=.6,secondary_budgets=[.3,.5],target_recall=.8,models=['epoch2','mil3'],aggregations=k.AGGS,reductions=['max','mean','top10mean'],selection='dev50 maximum recall at 60% review; tie recall at 30%, then first deterministic candidate; no evaluation tuning',tie='sha256 question_id, independent of labels',labels_sha256=k.file_sha(k.BASE/'annotation/adjudicated/proposals.json'),split_sha256=k.file_sha(k.OUT/'protocol.json'),source_sha256=k.file_sha(__file__),label_status='agent adjudication, not human gold',scope='batch triage only; does not improve error localization by itself')
 dest=OUT/'policy.json'
 if dest.exists():assert k.load(dest)==policy
 else:k.save(dest,policy)
 qs=k.selected_ids('dev');gold=truths(qs);curves=[]
 for model in policy['models']:
  for agg in policy['aggregations']:
   for reduction in policy['reductions']:
    config=dict(model=model,aggregation=agg,reduction=reduction);scores=scores_for(qs,config);curves.append(dict(config=config,metrics={str(b):measure(scores,gold,b) for b in [.3,.5,.6]}))
 best=max(curves,key=lambda r:(r['metrics']['0.6']['recall'],r['metrics']['0.3']['recall']))
 k.save(OUT/'dev-curves.json',curves);k.save(OUT/'selection.json',dict(selected=best,policy_sha256=k.file_sha(dest),checkpoint_sha256=k.file_sha((c.v.OLDWORK if best['config']['model']=='epoch2' else k.WORK)/'checkpoints'/best['config']['model']/'model.safetensors')));print(best)

def evaluate():
 policy=k.load(OUT/'policy.json');assert policy['source_sha256']==k.file_sha(__file__);assert policy['labels_sha256']==k.file_sha(k.BASE/'annotation/adjudicated/proposals.json');sel=k.load(OUT/'selection.json');assert sel['policy_sha256']==k.file_sha(OUT/'policy.json')
 qs=k.selected_ids('evaluation');gold=truths(qs);configs=dict(selected=sel['selected']['config'],previous_v3=dict(model='mil3',aggregation='min2',reduction='max'),previous_v2=dict(model='epoch2',aggregation='min',reduction='max'))
 out={};all_scores={}
 for name,config in configs.items():
  scores=scores_for(qs,config);all_scores[name]=scores;out[name]=dict(config=config,metrics={str(b):measure(scores,gold,b) for b in [.3,.5,.6]})
 k.save(OUT/'comparison.json',out);k.save(OUT/'evaluation-scores.json',all_scores)
 # Existing 295 includes training answers: queue only, never an independent score.
 scores=scores_for(k.selected_ids('train,dev,evaluation'),sel['selected']['config']);k.save(OUT/'review_queue.json',[dict(rank=i+1,question_id=q,priority=scores[q],split=k.protocol()['split'][q],review_status='unreviewed_in_this_round',human_approved=False) for i,q in enumerate(ranked(scores))]);print(out)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['select','evaluate']);a=p.parse_args();select() if a.command=='select' else evaluate()
