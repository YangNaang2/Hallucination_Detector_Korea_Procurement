"""Dev-selected warning continuity filter, never treating abstention as normal."""
import argparse,copy
import klue_v6_select as s
k=s.k
OUT=k.OUT/'span_filter'
def apply(pred,answer,minimum):
 p=copy.deepcopy(pred);merged=[]
 for z in p['spans']:
  if merged and answer[merged[-1]['end']:z['start']].isspace():merged[-1]['end']=z['end']
  else:merged.append(dict(z))
 p['spans']=[dict(start=z['start'],end=z['end'],quote=answer[z['start']:z['end']]) for z in merged if sum(not c.isspace() for c in answer[z['start']:z['end']])>=minimum]
 return p

def evaluate(part,minimum):
 rows=[]
 for q in k.selected_ids(part):
  x=k.inputs(q);p=k.load(k.OUT/'original_predictions'/f'{q}.json');p=apply(p,x['actual_answer'],minimum);rows.append(s.score_one(k.labels()[q],p,x['actual_answer']))
 return s.aggregate(rows),rows

def select():
 policy=dict(minimum_nonspace_characters=[1,4,8,12],base='fixed contrast3/repeat192/min/.3',selection='dev FPR <= .20, maximize recall then answer F1; success recall>=.5; no abstention',limitation='short numeric or negation errors may be suppressed; historically exposed data, exploratory',source_sha256=k.file_sha(__file__))
 dest=OUT/'policy.json'
 if dest.exists():assert k.load(dest)==policy
 else:k.save(dest,policy)
 curves=[]
 for n in policy['minimum_nonspace_characters']:
  m,_=evaluate('dev',n);a=m['answer_presence'];curves.append(dict(minimum=n,metrics=m,fpr=a['fp']/(a['fp']+m['answer_tn'])))
 eligible=[c for c in curves if c['fpr']<=.2];best=max(eligible,key=lambda c:(c['metrics']['answer_presence']['recall'],c['metrics']['answer_presence']['f1'])) if eligible else None
 k.save(OUT/'selection.json',dict(curves=curves,selected=best));print(best)

def report():
 selected=k.load(OUT/'selection.json')['selected'];assert selected
 for part in ['train','dev','evaluation']:
  m,rows=evaluate(part,selected['minimum']);k.save(OUT/f'{part}.json',dict(metrics=m,rows=rows));print(part,m['answer_presence'],m['answer_tn'],m['characters'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['select','report']);a=p.parse_args();select() if a.command=='select' else report()
