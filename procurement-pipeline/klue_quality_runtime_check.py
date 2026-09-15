"""Validate the single-model runtime against cached dev predictions and time warmup."""
import json,time
from klue_quality import *
from klue_quality_predict import KlueQualityDetector

def main():
 import torch
 torch.set_num_threads(4);t=time.perf_counter();det=KlueQualityDetector();torch.cuda.synchronize();load_seconds=time.perf_counter()-t
 t=time.perf_counter();det.predict('예산은 100원이다.','예산은 얼마인가?','예산은 200원이다.');torch.cuda.synchronize();warmup_seconds=time.perf_counter()-t
 c=load(OUT/'selection.json')['selected'];records=[]
 for q in selected_ids('dev')[:3]:
  x=inputs(q);torch.cuda.reset_peak_memory_stats();r=det.predict(x['context'],x['question'],x['actual_answer']);p=pred_from(q,raw_read(q,c['profile'],c['model']),c['aggregation'],c['threshold'])
  assert r['spans']==p['spans'] and r['checked_ranges']==p['checked_ranges'];records.append(dict(question_id=q,seconds=r['inference_seconds'],windows=r['window_count'],peak_allocated_bytes=torch.cuda.max_memory_allocated()))
 save(OUT/'runtime_validation.json',dict(load_seconds=load_seconds,warmup_seconds=warmup_seconds,records=records,prediction_equality=True,models_loaded=1,device='CUDA',synthetic_warmup_excluded_from_scores=True))
 print('runtime equality passed',records)
if __name__=='__main__':main()
