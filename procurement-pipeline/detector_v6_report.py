"""Paired A/B/C/D metrics; explicit provisional-label coverage and no unknown-as-normal."""
import collections,random
import numpy as np
import detector_v6_generate as g
import klue_v6_select as s
from detector300_score import aggregate,score_one,expand,POS,MASK,prf
k=s.k

def detailed(qs,labels,preds,answers):
 rows=[];truth_unknown=[];operational=collections.Counter();by_type={}
 for q in qs:
  l=labels[q];p=preds[q];a=answers[q];row=score_one(l,p,a);assert row is not None;rows.append(row)
  known_positive=any(z['label'] in POS for z in l['spans']);unknown=not known_positive and any(z['label']=='uncertain' for z in l['spans']);warn=bool(p['spans'])
  if unknown:truth_unknown.append(q)
  else:operational['tp' if known_positive and warn else 'fn' if known_positive else 'fp' if warn else 'tn']+=1
  for typ in POS:
   n=len(a);domain=expand(l['reviewed_ranges'],n)&expand(p['checked_ranges'],n);domain-=expand([[z['start'],z['end']] for z in l['spans'] if z['label'] in MASK],n);gold=expand([[z['start'],z['end']] for z in l['spans'] if z['label']==typ],n)&domain;guess=expand([[z['start'],z['end']] for z in p['spans']],n)&domain
   counter=by_type.setdefault(typ,collections.Counter());counter['tp']+=len(gold&guess);counter['fn']+=len(gold-guess)
 metrics=aggregate(rows);normal=operational['fp']+operational['tn'];metrics['operational_whole_answer']=dict(**prf(operational['tp'],operational['fp'],operational['fn']),tn=operational['tn'],normal_answers=normal,false_positive_rate=operational['fp']/normal if normal else None,truth_unresolved=len(truth_unknown),truth_unresolved_ids=truth_unknown,automatic_decision_rate=1.0 if qs else None,detector_abstention_rate=0.0 if qs else None,abstained_actual_hallucinations=0,policy='raw warning presence; citation/quality-only warnings count as false warnings on factually normal answers; uncertain-only truth is unresolved and excluded, never normal')
 metrics['by_company']={c:aggregate([r for r in rows if r['question_id'].split('-')[2]==c]) for c in sorted({q.split('-')[2] for q in qs})};metrics['by_length']={name:aggregate([r for r in rows if (r['answer_characters']>=600)==long]) for name,long in [('lt600',False),('ge600',True)]};metrics['by_error_type']={t:dict(c,recall=c['tp']/(c['tp']+c['fn']) if c['tp']+c['fn'] else None,precision=None,precision_reason='detector has no subtype predictions') for t,c in by_type.items()}
 return metrics,rows

def run():
 split=g.load(g.OUT/'protocol.json')['split'];oldlabels=k.labels();newlabels={p.stem:g.load(p) for p in (g.OUT/'new_agent_labels').glob('*.json')};config=g.load(g.OUT/'selection.json')['selected'];oldpred={};newpred={};oldanswers={};newanswers={}
 for q in sorted(split):
  x=k.inputs(q);oldanswers[q]=x['actual_answer'];oldpred[q]={'A':k.pred_from(q,s.raw(q,'mil3'),'min2',.5),'B':g.load(g.OUT/'original_predictions'/f'{q}.json')}
 for q in newlabels:
  a=g.load(g.WORK/'generated'/f'{q}.json');newanswers[q]=a['actual_answer'];paths={arm:g.OUT/'new_predictions'/m/f'{q}.json' for arm,m in [('C','mil3'),('D',config['model'])]}
  if all(p.exists() for p in paths.values()):newpred[q]={arm:g.load(p) for arm,p in paths.items()}
 report=dict(status='provisional agent labels; human gold 0; historically exposed questions, not independent test',total_original_answers=295,new_labels=len(newlabels),new_generated=len(list((g.WORK/'generated').glob('*.json'))),pending_new_labels=sorted(set(split)-set(newlabels)),arms={'A':'original answers + v3 mil3/min2/.5','B':'original answers + v6 contrast3/min/.3','C':'new answers + v3 mil3/min2/.5','D':'new answers + v6 contrast3/min/.3'},original={},matched={})
 for group in ['train','dev','evaluation']:
  qs=sorted(q for q in split if split[q]==group);report['original'][group]={}
  for arm in ['A','B']:
   metrics,rows=detailed(qs,oldlabels,{q:oldpred[q][arm] for q in qs},oldanswers);report['original'][group][arm]=metrics
  matched=[q for q in qs if q in newpred];report['matched'][group]=dict(question_ids=matched,total_partition=len(qs),arms={})
  for arm in ['A','B','C','D']:
   labels,answers,preds=(oldlabels,oldanswers,oldpred) if arm in ['A','B'] else (newlabels,newanswers,newpred)
   metrics,rows=detailed(matched,labels,{q:preds[q][arm] for q in matched},answers);report['matched'][group]['arms'][arm]=metrics;g.save(g.OUT/'comparison_rows'/f'{group}-{arm}.json',rows)
  nl=[newlabels[q] for q in matched];old_positive=sum(any(z['label'] in POS for z in oldlabels[q]['spans']) for q in matched);new_positive=sum(any(z['label'] in POS for z in l['spans']) for l in nl);unknown=sum(not any(z['label'] in POS for z in l['spans']) and any(z['label']=='uncertain' for z in l['spans']) for l in nl)
  report['matched'][group]['generation_quality']=dict(matched_answers=len(matched),old_hallucinated_answers=old_positive,new_hallucinated_answers=new_positive,new_truth_unresolved=unknown,new_confirmed_hallucination_rate=new_positive/(len(matched)-unknown) if len(matched)>unknown else None,new_incidence_lower_bound=new_positive/len(matched) if matched else None,new_incidence_upper_bound=(new_positive+unknown)/len(matched) if matched else None,fulfillment=dict(collections.Counter(l['question_fulfillment'] for l in nl)),answers_with_omission=sum(bool(l['omission']) for l in nl),note='new truth independently reviewed by agent before reading detector results; no transfer of original spans; generation prompt pilot was exploratory, same questions/evidence not independent')
 g.save(g.OUT/'abcd_comparison.json',report);print({part:{arm:(z['answer_presence']['tp'],z['answer_presence']['fp']) for arm,z in item['arms'].items()} for part,item in report['matched'].items()});return report
if __name__=='__main__':run()
