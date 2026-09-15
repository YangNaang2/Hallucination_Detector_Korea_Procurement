"""Evidence-complete MIL training; no label changes or heldout tuning."""
import argparse,sys,time,random,json
import numpy as np
import klue_quality as k
from detector300 import ROOT,load,save,file_sha,jsha
OLD=k.OUT;OLDWORK=k.WORK;k.OUT=OLD.parent/'results-v5';k.WORK=ROOT/'work/quality-v5'
TRAIN_LABELS=OLD.parent/'results-v4/annotation/agent-revised-labels.json'
k.MODEL=ROOT/'work/quality-v3/checkpoints/mil3'
def freeze():
 if (k.OUT/'protocol.json').exists():return
 p=load(OLD/'protocol.json');p.update(version='klue-fp-v5',target='dev answer false positive rate <= .20, maximize answer F1; recall >= .50 required for success',evaluation_policy='previous evaluation63 is now exposed historical regression; no claim of independent test',v3=dict(epochs=3,lr=5e-6,positive_weight=1,objective='negative-weight4 BCE of min window logits; normal answers oversampled twice; starts v3 mil3',source_sha256=file_sha(__file__),training_labels_sha256=file_sha(TRAIN_LABELS),negative_weight=4,normal_oversampling=2,start_checkpoint=file_sha(k.MODEL/'model.safetensors'),label_policy='v1 frozen; review suggestions separate; human approval pending'))
 save(k.OUT/'protocol.json',p)
def train():
 import torch
 sys.path.insert(0,str(ROOT));from demo.detector import HalluDetector
 torch.set_num_threads(4);torch.manual_seed(916);det=HalluDetector(str(k.MODEL),device='cuda');labs={r['question_id']:r for r in load(TRAIN_LABELS)};assert file_sha(TRAIN_LABELS)==load(k.OUT/'protocol.json')['v3']['training_labels_sha256'];bags=[]
 for q in k.selected_ids('train'):
  x=k.inputs(q);ids,off,batches=k.make_windows(det,x,'repeat192');n=len(x['actual_answer']);pos=k.expand([[s['start'],s['end']] for s in labs[q]['spans'] if s['label'] in k.POS],n);mask=k.expand([[s['start'],s['end']] for s in labs[q]['spans'] if s['label'] in k.MASK],n)
  yy=[-100 if set(range(s,e))&mask else int(bool(set(range(s,e))&pos)) for s,e in off]
  for s,e,ws in batches:
   if any(v!=-100 for v in yy[s:e]):
    bags.extend([(q,ws,yy[s:e])]*(2 if not pos else 1))
 for name,param in det.model.named_parameters():
  if name.startswith('roberta.embeddings.') or any(name.startswith(f'roberta.encoder.layer.{i}.') for i in range(6)):param.requires_grad=False
 opt=torch.optim.AdamW([p for p in det.model.parameters() if p.requires_grad],lr=5e-6,weight_decay=.01)
 checkpoint=k.WORK/'train-state.pt';identity=jsha(dict(protocol=file_sha(k.OUT/'protocol.json'),code=file_sha(__file__),base=file_sha(k.MODEL/'model.safetensors')));start=0
 if checkpoint.exists():
  st=torch.load(checkpoint,weights_only=False,map_location='cpu');assert st['identity']==identity;det.model.load_state_dict(st['model']);opt.load_state_dict(st['opt']);start=st['epoch'];torch.set_rng_state(st['rng']);torch.cuda.set_rng_state(st['cuda_rng'])
 for ep in range(start,3):
  det.model.train();order=list(range(len(bags)));random.Random(916+ep).shuffle(order);losses=[];t=time.perf_counter()
  for step,i in enumerate(order):
   q,ws,yy=bags[i];all_logits=[];opt.zero_grad()
   for lo in range(0,len(ws),4):
    batch=ws[lo:lo+4];seqs=[];starts=[]
    for w in batch:
     prefix=[det.cls_id]+w['prompt']+[det.sep_id];starts.append(len(prefix));seqs.append(prefix+w['answer']+[det.sep_id])
    length=max(map(len,seqs));ii=torch.tensor([a+[det.tok.pad_token_id]*(length-len(a)) for a in seqs],device='cuda');att=torch.tensor([[1]*len(a)+[0]*(length-len(a)) for a in seqs],device='cuda')
    with torch.autocast('cuda',dtype=torch.bfloat16):z=det.model(input_ids=ii,attention_mask=att).logits
    all_logits.extend(z[j,s:s+len(yy),1].float()-z[j,s:s+len(yy),0].float() for j,s in enumerate(starts))
   joint=torch.stack(all_logits).min(0).values;y=torch.tensor(yy,device='cuda');valid=y!=-100;loss=torch.nn.functional.binary_cross_entropy_with_logits(joint[valid],y[valid].float(),weight=torch.where(y[valid]==0,4.,1.));loss.backward();torch.nn.utils.clip_grad_norm_(det.model.parameters(),1);opt.step();losses.append(float(loss.detach()))
   if step%50==0:print('MIL',ep+1,step,len(order),np.mean(losses),flush=True)
  folder=k.WORK/'checkpoints'/f'fp{ep+1}';det.model.save_pretrained(folder);det.tok.save_pretrained(folder);checkpoint.parent.mkdir(parents=True,exist_ok=True);tmp=checkpoint.with_suffix('.tmp');torch.save(dict(identity=identity,epoch=ep+1,model=det.model.state_dict(),opt=opt.state_dict(),rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state()),tmp);tmp.replace(checkpoint)
  save(k.OUT/'training'/f'fp{ep+1}.json',dict(epoch=ep+1,bags=len(bags),loss=float(np.mean(losses)),seconds=time.perf_counter()-t,checkpoint_sha256=file_sha(folder/'model.safetensors'),train_ids=k.selected_ids('train'),labels='unapproved',identity=identity))
 print('training complete',flush=True)
def select():
 if (k.OUT/'selection.json').exists():return
 cs=[load(k.OUT/'experiments'/f'mil{i}-dev-best.json') for i in range(1,4)];cs=[c for c in cs if c]
 prior=load(OLD/'selection.json')['selected'];best=max(cs,key=lambda c:c['characters']['f1']) if cs else None
 save(k.OUT/'selection.json',dict(candidate=best,previous=prior,improves_dev=bool(best and best['characters']['f1']>prior['characters']['f1']),human_gold=False,evaluation_status='already exposed historical regression only'))
 print(json.dumps(best))
def report():
 c=load(k.OUT/'selection.json')['candidate'];result,rows=k.evaluate_config(k.selected_ids('evaluation'),c['profile'],c['aggregation'],c['threshold'],c['model']);save(k.OUT/'regression.json',dict(config=c,metrics=result,per_answer=rows,independent_test=False,human_gold=False));print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command');p.add_argument('--model',default='mil1');p.add_argument('--part',default='dev');a=p.parse_args()
 if a.command=='freeze':freeze()
 elif a.command=='train':train()
 elif a.command=='infer':k.infer(a.part,a.model,['repeat192'])
 elif a.command=='sweep':k.sweep(a.model,['repeat192'])
 elif a.command=='select':select()
 elif a.command=='report':report()
