"""KLUE-only quality experiments. Frozen grouped split, private scores, locked selection."""
import argparse, json, re, time, sys, random, math, collections, difflib
from pathlib import Path
import numpy as np
from detector300 import ROOT, OUT as BASE, PRIVATE, load, save, sha, file_sha, jsha, ranges, windows
from detector300_score import score_one,aggregate,expand,POS,MASK
OUT=BASE.parent/'results-v2';WORK=ROOT/'work/quality-v2'
MODEL=Path('/home/piai/바탕화면/ko_lettucedetect/runs/klue')
THRESHOLDS=[.00001,.00003,.0001,.0003,.001,.003,.01,.02,.03,.05,.075,.1,.15,.2,.3,.4,.5,.6,.7,.8,.9]
AGGS=['min','min2','mean','q25','max','relevance']
def inputs(q):return load(PRIVATE/'inputs'/f'{q}.json')
def labels():return {r['question_id']:r for r in load(BASE/'annotation/adjudicated/proposals.json')}
def freeze():
 dest=OUT/'protocol.json'
 if dest.exists():print('frozen protocol exists');return
 qs=[json.loads(l) for l in (ROOT/'project-docs/평가데이터/v2/evaluation/questions_300.jsonl').read_text().splitlines()];ls=labels();qs=[q for q in qs if q['question_id'] in ls]
 parent={q['question_id']:q['question_id'] for q in qs}
 def find(a):
  while parent[a]!=a:a=parent[a]
  return a
 def union(a,b):parent[find(b)]=find(a)
 near=[]
 for i,a in enumerate(qs):
  for b in qs[i+1:]:
   same=a['bid_key']==b['bid_key'];xa=inputs(a['question_id']);xb=inputs(b['question_id'])
   # Input-only leakage audit, no prediction or label-based group construction.
   sim=difflib.SequenceMatcher(None,xa['question'],xb['question']).ratio()
   duplicate=sha(xa['actual_answer'])==sha(xb['actual_answer'])
   if same or sim>=.9 or duplicate:
    union(a['question_id'],b['question_id'])
    if not same:near.append(dict(a=a['question_id'],b=b['question_id'],question_similarity=sim,duplicate_answer=duplicate))
 groups=collections.defaultdict(list)
 for q in qs:groups[find(q['question_id'])].append(q['question_id'])
 gs=sorted(groups.values(),key=lambda g:sha('klue-v2-fixed-20260915|'+','.join(sorted(g))))
 splits={};ng=len(gs)
 for i,g in enumerate(gs):
  split='train' if i<int(ng*.6) else 'dev' if i<int(ng*.8) else 'evaluation'
  for q in g:splits[q]=split
 protocol=dict(version='klue-quality-v2',baseline_commit='5381e0a',labels_sha256=file_sha(BASE/'annotation/adjudicated/proposals.json'),inputs_sha256=file_sha(BASE.parent/'selected_inputs.json'),groups=gs,split=splits,counts=dict(collections.Counter(splits.values())),near_duplicate_links=near,selection_policy='maximize dev character micro F1 among precision>=0.40; if none qualify retain baseline; tie: fewer windows then higher threshold. Precision target is provisional, not deployment approval.',thresholds=THRESHOLDS,profiles=['legacy192','repeat192','claim96'],aggregations=AGGS,finetuning=dict(epochs=2,lr=5e-6,positive_weight=2,freeze_bottom_layers=6,seed=20260915,train_labels='unapproved agent/adjudication proposals; never human gold',windows='top2 lexical relevance per answer segment; no heldout training'),evaluation_policy='lock selection before evaluation; paired fixed baseline coverage; no test-driven retuning',limitations='All 295 previously exposed development material; evaluation partition is prospective experiment lock only, not independent test. Human gold 0.',rules_policy='citation diagnostics separate/masked; numeric rules only when unambiguous extraction, otherwise abstain; no qid/expected-answer rules')
 save(dest,protocol);print(protocol['counts'],'groups',ng)
def protocol():
 p=load(OUT/'protocol.json');assert p['labels_sha256']==file_sha(BASE/'annotation/adjudicated/proposals.json');assert p['inputs_sha256']==file_sha(BASE.parent/'selected_inputs.json');return p
def selected_ids(part):return sorted(q for q,s in protocol()['split'].items() if s in part.split(','))
def segments(tok,x,profile):
 e=tok(x['actual_answer'],add_special_tokens=False,return_offsets_mapping=True);ids=e['input_ids'];off=e['offset_mapping'];n=len(ids)
 if profile!='claim96':return ids,off,[(s,min(s+192,n)) for s in range(0,n,192)]
 # Sentence/newline boundaries from answer only; hard cap 96 and 16-token overlap.
 bounds={m.end() for m in re.finditer(r'[.!?。](?:\s|$)|\n',x['actual_answer'])};ss=[];s=0
 while s<n:
  cap=min(s+96,n);ends=[i+1 for i in range(s+32,cap) if off[i][1] in bounds];end=max(ends) if ends else cap
  ss.append((s,end))
  if end==n:break
  s=max(s+1,end-16)
 return ids,off,ss

def lexical(a,b):
 def terms(s):return set(re.findall(r'[가-힣A-Za-z0-9]{2,}',s.lower()))
 aa=terms(a);bb=terms(b);return len(aa&bb)/max(1,len(aa))
def make_windows(det,x,profile):
 tok=det.tok;ids,off,segs=segments(tok,x,profile)
 header=tok(f"질문: {x['question'].strip()}\n\n문서:\n",add_special_tokens=False)['input_ids']
 body=tok(x['context'].strip(),add_special_tokens=False)['input_ids']
 full=tok(f"질문: {x['question'].strip()}\n\n문서:\n{x['context'].strip()}",add_special_tokens=False)['input_ids']
 batches=[]
 for s,e in segs:
  budget=512-(e-s)-det.n_special
  context=full if profile=='legacy192' else body;prefix=[] if profile=='legacy192' else header
  budget-=len(prefix);assert budget>0
  ws=[]
  for a,b in windows(len(context),budget):
   p=prefix+context[a:b];rel=lexical(x['question']+' '+x['actual_answer'][off[s][0]:off[e-1][1]],tok.decode(context[a:b]))
   ws.append(dict(prompt=p,answer=ids[s:e],relevance=rel,prompt_range=[a,b]))
  batches.append((s,e,ws))
 return ids,off,batches

def forward(det,prompt,ans,bf16=True):
 import torch
 ids=([det.cls_id] if det.cls_id is not None else [])+prompt+([det.sep_id] if det.sep_id is not None else [])
 start=len(ids);ids+=ans+([det.sep_id] if det.sep_id is not None else []);assert len(ids)<=512
 t=torch.tensor([ids],device='cuda')
 with torch.no_grad(),torch.autocast('cuda',dtype=torch.bfloat16,enabled=bf16):z=det.model(input_ids=t,attention_mask=torch.ones_like(t)).logits
 return z[0,start:start+len(ans)].float().softmax(-1)[:,1].cpu().numpy()
def matrices(det,x,profile,bf16=True):
 ids,off,batches=make_windows(det,x,profile);result=[]
 for s,e,ws in batches:
  result.append(dict(start=s,end=e,weights=[w['relevance'] for w in ws],prompt_ranges=[w['prompt_range'] for w in ws],probabilities=[forward(det,w['prompt'],w['answer'],bf16).tolist() for w in ws]))
 return dict(offsets=off,segments=result)
def combine(raw,agg):
 n=len(raw['offsets']);vals=np.full(n,-1.,dtype=float)
 for seg in raw['segments']:
  a=np.asarray(seg['probabilities']);w=np.asarray(seg['weights']);w=(w+.01)/(w+.01).sum()
  v=a.min(0) if agg=='min' else np.sort(a,axis=0)[min(1,len(a)-1)] if agg=='min2' else a.mean(0) if agg=='mean' else np.quantile(a,.25,axis=0) if agg=='q25' else a.max(0) if agg=='max' else (a*w[:,None]).sum(0)
  s,e=seg['start'],seg['end'];vals[s:e]=np.maximum(vals[s:e],v)
 assert np.isfinite(vals).all() and (vals>=0).all();return vals

def pred_from(q,raw,agg,threshold):
 x=inputs(q);a=x['actual_answer'];vals=combine(raw,agg);char={}
 for (s,e),v in zip(raw['offsets'],vals):
  assert 0<=s<e<=len(a)
  for i in range(s,e):char[i]=max(char.get(i,0),float(v))
 return dict(question_id=q,answer_sha256=x['answer_sha256'],context_sha256=x['context_sha256'],checked_ranges=ranges(char),unchecked_ranges=ranges(set(range(len(a)))-set(char)),spans=[dict(start=s,end=e,quote=a[s:e]) for s,e in ranges(i for i,v in char.items() if v>=threshold)])
def raw_path(q,profile,model):return WORK/'matrices'/model/profile/f'{q}.json'
def raw_read(q,profile,model='base'):
 if profile=='saved':
  p=load(PRIVATE/'probabilities/klue/common512-v2'/f'{q}.json')
  return dict(offsets=[[s,e] for s,e,_ in p],segments=[dict(start=0,end=len(p),weights=[1],probabilities=[[v for _,_,v in p]])])
 return load(raw_path(q,profile,model))
def infer(part,model='base',profile_names=None):
 import torch
 sys.path.insert(0,str(ROOT));from demo.detector import HalluDetector
 torch.set_num_threads(4);folder=MODEL if model=='base' else WORK/'checkpoints'/model
 profiles=profile_names or protocol()['profiles'];qs=selected_ids(part)
 identity=jsha(dict(code=file_sha(Path(__file__)),weights=file_sha(folder/'model.safetensors'),protocol=file_sha(OUT/'protocol.json'),profiles=profiles,model=model))
 mf=WORK/'matrices'/model/'manifest.json'
 if mf.exists():assert load(mf)['identity']==identity,'resume identity mismatch'
 else:save(mf,dict(identity=identity,checkpoint=str(folder),weights_sha256=file_sha(folder/'model.safetensors'),profiles=profiles))
 todo=[(q,p) for q in qs for p in profiles if not raw_path(q,p,model).exists()]
 if not todo:print('all complete',model,part);return
 t=time.perf_counter();det=HalluDetector(str(folder),device='cuda');loadtime=time.perf_counter()-t
 forward(det,[10,11],[12,13]);torch.cuda.synchronize();timings=[]
 for i,(q,p) in enumerate(todo):
  x=inputs(q);assert sha(x['context'])==x['context_sha256'] and sha(x['actual_answer'])==x['answer_sha256']
  t=time.perf_counter();torch.cuda.reset_peak_memory_stats();r=matrices(det,x,p);torch.cuda.synchronize()
  r.update(question_id=q,answer_sha256=x['answer_sha256'],context_sha256=x['context_sha256'],identity=identity,seconds=time.perf_counter()-t,peak_allocated=torch.cuda.max_memory_allocated(),window_count=sum(len(z['weights']) for z in r['segments']))
  save(raw_path(q,p,model),r);timings.append(dict(q=q,profile=p,seconds=r['seconds'],windows=r['window_count']))
  if i%20==0:print(model,i+1,len(todo),q,p,flush=True)
 save(OUT/'runs'/f'{model}-{part}.json',dict(identity=identity,load_seconds=loadtime,records=timings))
 if model=='base' and part=='dev':
  # Deterministic input-only dev diagnostic, never heldout selection.
  q=qs[0];x=inputs(q);r=matrices(det,x,'legacy192',False);b=raw_read(q,'legacy192');diff=np.abs(combine(r,'min')-combine(b,'min'))
  save(OUT/'dtype_diagnostic.json',dict(question_id=q,max_abs=float(diff.max()),mean_abs=float(diff.mean()),threshold05_disagreements=int(((combine(r,'min')>=.5)!=(combine(b,'min')>=.5)).sum())))
 del det;torch.cuda.empty_cache()

def evaluate_config(qs,profile,agg,threshold,model='base'):
 ls=labels();rows=[]
 for q in qs:
  x=inputs(q);raw=raw_read(q,profile,model);p=pred_from(q,raw,agg,threshold);base=load(BASE/'predictions/klue/common512-v2'/f'{q}.json');domain=expand(base['checked_ranges'],len(x['actual_answer']))
  assert expand(p['checked_ranges'],len(x['actual_answer']))==domain,'coverage changed'
  rows.append(score_one(ls[q],p,x['actual_answer'],domain))
 return aggregate(rows),rows

def sweep(model='base',profiles=None):
 qs=selected_ids('dev');ls=labels();results=[]
 for profile in profiles or ['saved']+protocol()['profiles']:
  for agg in ['min'] if profile=='saved' else AGGS:
   # One vectorized pass per aggregation. Threshold curve never sees evaluation labels.
   vs=[];ys=[];window_count=0
   for q in qs:
    x=inputs(q);raw=raw_read(q,profile,model);values=combine(raw,agg);c=np.full(len(x['actual_answer']),np.nan)
    for (s,e),v in zip(raw['offsets'],values):c[s:e]=np.fmax(c[s:e],v)
    l=ls[q];mask=expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in MASK],len(c));gold=expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in POS],len(c))
    valid=[i for i in range(len(c)) if np.isfinite(c[i]) and i not in mask];vs.extend(c[valid]);ys.extend(i in gold for i in valid);window_count+=raw.get('window_count',0)
   v=np.array(vs);y=np.array(ys,dtype=bool)
   for threshold in THRESHOLDS:
    z=v>=threshold;tp=int((z&y).sum());fp=int((z&~y).sum());fn=int((~z&y).sum());from detector300_score import prf
    results.append(dict(model=model,profile=profile,aggregation=agg,threshold=threshold,windows=window_count,characters=prf(tp,fp,fn)))
 save(OUT/'experiments'/f'{model}-dev-curves.json',results)
 eligible=[r for r in results if (r['characters']['precision'] or 0)>=.4]
 best=max(eligible,key=lambda r:(r['characters']['f1'] or 0,-r['windows'],r['threshold'])) if eligible else None
 save(OUT/'experiments'/f'{model}-dev-best.json',best);print(json.dumps(best,ensure_ascii=False))

def train():
 import torch
 sys.path.insert(0,str(ROOT));from demo.detector import HalluDetector
 torch.set_num_threads(4);torch.manual_seed(20260915);random.seed(20260915);det=HalluDetector(str(MODEL),device='cuda');ls=labels();samples=[]
 # Supervise top2 related windows; this approximation is recorded, not a new gold claim.
 for q in selected_ids('train'):
  x=inputs(q);ids,off,batches=make_windows(det,x,'repeat192');l=ls[q];n=len(x['actual_answer']);pos=expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in POS],n);mask=expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in MASK],n)
  yy=[-100 if set(range(s,e))&mask else int(bool(set(range(s,e))&pos)) for s,e in off]
  for s,e,ws in batches:
   for w in sorted(ws,key=lambda w:w['relevance'],reverse=True)[:2]:
    prompt=[det.cls_id]+w['prompt']+[det.sep_id];ii=prompt+w['answer']+[det.sep_id];ll=[-100]*len(prompt)+yy[s:e]+[-100]
    if any(v!=-100 for v in ll):samples.append((ii,ll))
 for name,param in det.model.named_parameters():
  if name.startswith('roberta.embeddings.') or any(name.startswith(f'roberta.encoder.layer.{i}.') for i in range(6)):param.requires_grad=False
 opt=torch.optim.AdamW([p for p in det.model.parameters() if p.requires_grad],lr=5e-6,weight_decay=.01);ck=WORK/'training-state.pt';start=0
 identity=jsha(dict(code=file_sha(Path(__file__)),protocol=file_sha(OUT/'protocol.json'),base=file_sha(MODEL/'model.safetensors')))
 if ck.exists():
  state=torch.load(ck,map_location='cpu',weights_only=False);assert state['identity']==identity;det.model.load_state_dict(state['model']);opt.load_state_dict(state['optimizer']);start=state['epoch'];torch.set_rng_state(state['rng']);torch.cuda.set_rng_state(state['cuda_rng'])
 for epoch in range(start,2):
  det.model.train();order=list(range(len(samples)));random.Random(20260915+epoch).shuffle(order);total=0;t=time.perf_counter();opt.zero_grad()
  for j,i in enumerate(order):
   ii,ll=samples[i];tens=torch.tensor([ii],device='cuda');yy=torch.tensor(ll,device='cuda')
   with torch.autocast('cuda',dtype=torch.bfloat16):
    z=det.model(input_ids=tens,attention_mask=torch.ones_like(tens)).logits.float();loss=torch.nn.functional.cross_entropy(z.view(-1,2),yy,weight=torch.tensor([1.,2.],device='cuda'),ignore_index=-100)
   (loss/4).backward();total+=float(loss.detach())
   if (j+1)%4==0 or j+1==len(order):torch.nn.utils.clip_grad_norm_(det.model.parameters(),1.);opt.step();opt.zero_grad()
   if j%100==0:print('train',epoch+1,j,len(order),'loss',round(total/(j+1),4),flush=True)
  folder=WORK/'checkpoints'/f'epoch{epoch+1}';det.model.save_pretrained(folder);det.tok.save_pretrained(folder)
  tmp=ck.with_suffix('.tmp');torch.save(dict(identity=identity,epoch=epoch+1,model=det.model.state_dict(),optimizer=opt.state_dict(),rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state()),tmp);tmp.replace(ck)
  save(OUT/'training'/f'epoch{epoch+1}.json',dict(samples=len(samples),loss=total/len(samples),seconds=time.perf_counter()-t,checkpoint=str(folder),sha256=file_sha(folder/'model.safetensors'),identity=identity,train_question_ids=selected_ids('train'),label_status='unapproved'))
 del det;torch.cuda.empty_cache()

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','infer','sweep','train']);p.add_argument('--part',default='dev');p.add_argument('--model',default='base');p.add_argument('--profiles');a=p.parse_args();profiles=a.profiles.split(',') if a.profiles else None
 if a.command=='freeze':freeze()
 elif a.command=='infer':infer(a.part,a.model,profiles)
 elif a.command=='sweep':sweep(a.model,profiles)
 else:train()
if __name__=='__main__':main()
