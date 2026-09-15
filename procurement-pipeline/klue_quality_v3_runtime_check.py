"""Check label-free single-model runtime against cached experiment outputs."""
import time,torch
import klue_quality_v3_claims as c
from klue_quality_predict import KlueQualityDetector
k=c.k;torch.set_num_threads(4)
s=c.load(k.OUT/'claim_selection.json')['selected'];t=time.perf_counter();det=KlueQualityDetector(k.OUT/'runtime_selection.json',k.WORK/'checkpoints'/s['model']);loadtime=time.perf_counter()-t
t=time.perf_counter();k.forward(det.det,[10,11],[12,13]);torch.cuda.synchronize();warm=time.perf_counter()-t
qs=k.selected_ids('dev')[:3];seconds=[]
for q in qs:
 x=k.inputs(q);p=det.predict(x['context'],x['question'],x['actual_answer']);expected=c.predict(q,s)
 for key in ['spans','checked_ranges','unchecked_ranges','answer_sha256','context_sha256']:assert p[key]==expected[key],(q,key)
 seconds.append(p['inference_seconds'])
c.save(k.OUT/'runtime_validation.json',dict(records=qs,all_match=True,load_once=True,load_seconds=loadtime,warmup_seconds=warm,inference_seconds=seconds,uses_labels=False))
print('runtime: 3 records match; loaded once')
