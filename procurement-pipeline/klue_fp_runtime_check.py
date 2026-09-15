"""Verify the explicit v5 single-model runtime and resume identity."""
import time,torch
import klue_fp_select as s
from klue_quality_predict import KlueQualityDetector
k=s.k
if __name__=='__main__':
 torch.set_num_threads(4);cfg=k.load(k.OUT/'fp_selection.json')['selected'];v=k.load(k.OUT/'validation.json');t=time.perf_counter();det=KlueQualityDetector(k.OUT/'runtime_selection.json',v['checkpoint']);load=time.perf_counter()-t;t=time.perf_counter();k.forward(det.det,[10,11],[12,13]);torch.cuda.synchronize();warm=time.perf_counter()-t
 qs=k.selected_ids('dev')[:3]
 for q in qs:
  x=k.inputs(q);pred=det.predict(x['context'],x['question'],x['actual_answer']);expected=k.load(k.OUT/'predictions'/f'{q}.json')
  for key in ['spans','checked_ranges','unchecked_ranges','answer_sha256','context_sha256']:assert pred[key]==expected[key]
 k.save(k.OUT/'runtime_validation.json',dict(questions=qs,predictions_equal=True,loaded_once=True,load_seconds=load,warmup_seconds=warm,labels_used_by_runtime=False));print('3 runtime predictions equal')
