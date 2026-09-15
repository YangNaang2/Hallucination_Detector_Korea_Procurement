"""Checkpoint/training-format diagnostics; historical evaluation is not a new test."""
import sys,json,time,collections
import numpy as np
from klue_quality import *
def main():
 import torch
 sys.path.insert(0,str(ROOT));from demo.detector import HalluDetector
 from src.dataset import encode_example
 torch.set_num_threads(4);det=HalluDetector(str(MODEL),device='cuda');data=Path('/home/piai/바탕화면/ko_lettucedetect/work/ko_ragtruth_full.jsonl')
 records=[json.loads(l) for l in data.read_text().splitlines()];counts=collections.Counter(r.get('split') for r in records);test=[r for r in records if r.get('split')=='test']
 if not test:test=[r for r in records if r.get('split') in ['eval','validation']]
 picked=[]
 for task in sorted({r.get('task_type','unknown') for r in test}):picked.extend(sorted([r for r in test if r.get('task_type','unknown')==task],key=lambda r:sha(str(r.get('id',r.get('answer')))))[:12])
 truth=[];pred=[];diff=[];cut=0
 for r in picked:
  e=encode_example(r,det.tok,512);ii=e['input_ids'];ll=np.array(e['labels']);ix=np.flatnonzero(ll!=-100);assert len(ii)<=512
  t=torch.tensor([ii],device='cuda')
  with torch.no_grad(),torch.autocast('cuda',dtype=torch.bfloat16):z=det.model(input_ids=t,attention_mask=torch.ones_like(t)).logits.float().softmax(-1)[0,:,1].cpu().numpy()
  pp=forward(det,ii[1:ix[0]-1],ii[ix[0]:ix[-1]+1]);diff.append(float(np.max(np.abs(pp-z[ix]))));truth.extend(ll[ix]);pred.extend(z[ix]>=.5);cut+=e['truncated']
 from detector300_score import prf
 y=np.array(truth,dtype=bool);z=np.array(pred,dtype=bool)
 comparisons=[]
 for q in selected_ids('dev'):
  raw=raw_read(q,'legacy192');saved=raw_read(q,'saved');assert raw['offsets']==saved['offsets'];delta=np.max(np.abs(combine(raw,'min')-combine(saved,'min')));comparisons.append(float(delta))
 rep=dict(model_sha256=file_sha(MODEL/'model.safetensors'),training_data_sha256=file_sha(data),available_split_counts=dict(counts),historical_eval_sample=len(picked),historical_sample_positive_token_metrics=prf(int((y&z).sum()),int((~y&z).sum()),int((y&~z).sum())),historical_sample_truncated=cut,training_wrapper_probability_max_difference=max(diff),baseline_dev50_reproduction_max_difference=max(comparisons),new_independent_labels_found=False,interpretation='Historical translated RAGTruth heldout was already used during original training/evaluation. Small deterministic sample is implementation regression only.',max_position_embeddings=det.model.config.max_position_embeddings,label_mapping=det.model.config.id2label,format='CLS question+context SEP answer SEP; no token_type_ids in either training or inference; context/padding loss masked -100',known_shift='historical training truncates prompt head; production windows aggregate min over every evidence window; BF16 diagnostic stored separately')
 save(OUT/'diagnostics.json',rep);print(json.dumps(rep,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
