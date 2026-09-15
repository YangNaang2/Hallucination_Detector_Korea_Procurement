"""C/D comparison inference on new answers; no review labels are accessed."""
import argparse,time,sys
import detector_v6_generate as g
import klue_quality as k
WORK=g.ROOT/'work/quality-v6-new'
def run(watch):
 import torch
 sys.path.insert(0,str(g.ROOT));from demo.detector import HalluDetector
 torch.set_num_threads(4);selection=g.load(g.OUT/'selection.json')['selected'];configs={'mil3':dict(model='mil3',profile='repeat192',aggregation='min2',threshold=.5),selection['model']:selection};detectors={};manifests={}
 for name,config in configs.items():
  folder=g.ROOT/('work/quality-v3/checkpoints/mil3' if name=='mil3' else 'work/quality-v6-detector/checkpoints/'+name);identity=g.jsha(dict(config=config,source=g.file_sha(__file__),weights=g.file_sha(folder/'model.safetensors'),generation=g.file_sha(g.OUT/'generation_policy.json')));manifests[name]=dict(identity=identity,checkpoint_sha256=g.file_sha(folder/'model.safetensors'),configuration=config)
  path=WORK/'matrices'/name/'manifest.json'
  if path.exists():assert g.load(path)==manifests[name]
  else:g.save(path,manifests[name])
  detectors[name]=HalluDetector(str(folder),device='cuda')
 seen=set();idle=0
 while True:
  paths=sorted((g.WORK/'generated').glob('*.json'));todo=[p for p in paths if p.stem not in seen]
  for path in todo:
   n=g.load(path);x=g.load(g.PRIVATE/'inputs'/path.name);x.update(actual_answer=n['actual_answer'],answer_sha256=n['answer_sha256']);q=path.stem;assert g.sha(x['actual_answer'])==x['answer_sha256'] and g.sha(x['context'])==x['context_sha256']
   for name,det in detectors.items():
    dest=WORK/'matrices'/name/path.name
    if dest.exists():
     old=g.load(dest);assert old['identity']==manifests[name]['identity'] and old['answer_sha256']==x['answer_sha256'];continue
    start=time.perf_counter();r=k.matrices(det,x,'repeat192');r.update(question_id=q,answer_sha256=x['answer_sha256'],context_sha256=x['context_sha256'],identity=manifests[name]['identity'],seconds=time.perf_counter()-start);g.save(dest,r)
    vals=k.combine(r,configs[name]['aggregation']);chars={}
    for (a,b),v in zip(r['offsets'],vals):
     for i in range(a,b):chars[i]=max(chars.get(i,0),float(v))
    pred=dict(question_id=q,answer_sha256=x['answer_sha256'],context_sha256=x['context_sha256'],spans=[dict(start=a,end=b,quote=x['actual_answer'][a:b]) for a,b in k.ranges(i for i,v in chars.items() if v>=configs[name]['threshold'])],checked_ranges=k.ranges(chars),unchecked_ranges=k.ranges(set(range(len(x['actual_answer'])))-set(chars)),configuration=configs[name],checkpoint_sha256=manifests[name]['checkpoint_sha256'],status='completed',human_approved=False);g.save(g.OUT/'new_predictions'/name/path.name,pred)
   seen.add(q);print('new inference',len(seen),q,flush=True)
  if len(seen)==295 or not watch:return
  idle=0 if todo else idle+1
  if idle>=120:return
  time.sleep(2)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');a=p.parse_args();run(a.watch)
