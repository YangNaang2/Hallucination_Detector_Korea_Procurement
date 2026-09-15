"""Single KLUE runtime. Load once, predict many. No access to evaluation labels."""
import argparse,json,time
from pathlib import Path
from klue_quality import MODEL,WORK,OUT,matrices,combine,sha,file_sha,ranges
from klue_quality_rules import rule_spans
class KlueQualityDetector:
 def __init__(self,selection=None,checkpoint=None):
  import sys
  from detector300 import ROOT
  sys.path.insert(0,str(ROOT));from demo.detector import HalluDetector
  self.selection=json.loads(Path(selection or OUT/'selection.json').read_text());self.config=self.selection['selected']
  folder=Path(checkpoint) if checkpoint else MODEL if self.config['model']=='base' else WORK/'checkpoints'/self.config['model']
  if file_sha(folder/'model.safetensors')!=self.selection['checkpoint_sha256']:raise ValueError('checkpoint identity mismatch')
  self.det=HalluDetector(str(folder),device='cuda')
 def predict(self,context,question,answer):
  x=dict(context=context,question=question,actual_answer=answer);profile=self.config['profile'];profile='legacy192' if profile=='saved' else profile
  t=time.perf_counter();r=matrices(self.det,x,profile);vals=combine(r,self.config['aggregation']);char={}
  for (s,e),v in zip(r['offsets'],vals):
   for i in range(s,e):char[i]=max(char.get(i,0),float(v))
  positive={i for i,v in char.items() if v>=self.config['threshold']};rules=rule_spans(answer,context) if self.selection['use_rules'] else []
  for rr in rules:positive.update(range(rr['start'],rr['end']))
  return dict(answer_sha256=sha(answer),context_sha256=sha(context),spans=[dict(start=s,end=e,quote=answer[s:e]) for s,e in ranges(positive)],checked_ranges=ranges(char),unchecked_ranges=ranges(set(range(len(answer)))-set(char)),rules=rules,inference_seconds=time.perf_counter()-t,window_count=sum(len(s['weights']) for s in r['segments']),label_status='model prediction, not approved truth',configuration=self.config)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--selection',type=Path);p.add_argument('--checkpoint',type=Path);a=p.parse_args()
 import torch
 torch.set_num_threads(4);det=KlueQualityDetector(a.selection,a.checkpoint)
 with a.input.open() as src,a.output.open('w') as dst:
  for line in src:
   x=json.loads(line);r=det.predict(x['context'],x['question'],x.get('answer',x.get('actual_answer','')));dst.write(json.dumps(r,ensure_ascii=False)+'\n');dst.flush()
