"""Character micro, strict exact-span and answer-presence scores over explicit coverage.
No tuning; no human gold inferred. Character gaps and uncertain/citation/quality masked.
"""
import argparse,collections,json,statistics
from detector300 import ROOT,OUT,PRIVATE,load,save,sha,ranges,frozen
MODELS=['klue','xlmr','bgem3'];POS={'contradiction','unsupported'}
MASK={'uncertain','citation_error','quality_only'}

def expand(rs,n):
 out=set()
 for s,e in rs:
  if not isinstance(s,int) or not isinstance(e,int) or not 0<=s<e<=n:raise ValueError('bad interval')
  out.update(range(s,e))
 return out

def prf(tp,fp,fn):
 return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)

def validate(label,pred,answer):
 if label['answer_sha256']!=sha(answer) or pred['answer_sha256']!=sha(answer):raise ValueError('answer identity mismatch')
 if label['context_sha256']!=pred['context_sha256']:raise ValueError('context identity mismatch')
 for s in (label['spans'] or [])+pred['spans']:
  if not 0<=s['start']<s['end']<=len(answer) or answer[s['start']:s['end']]!=s['quote']:raise ValueError('span/Unicode mismatch')
 expand(label['reviewed_ranges'],len(answer));expand(pred['checked_ranges'],len(answer))

def score_one(label,pred,answer,paired=None):
 validate(label,pred,answer);n=len(answer)
 reviewed=expand(label['reviewed_ranges'],n)
 if not reviewed:return None
 excluded=expand([[s['start'],s['end']] for s in label['spans'] if s['label'] in MASK],n)
 domain=(reviewed-excluded)&expand(pred['checked_ranges'],n)
 if paired is not None:domain &= paired
 if not domain:return None
 gold=expand([[s['start'],s['end']] for s in label['spans'] if s['label'] in POS],n)&domain
 guess=expand([[s['start'],s['end']] for s in pred['spans']],n)&domain
 # Tokenizers omit whitespace. Exact spans retain their original boundaries;
 # require every non-whitespace character checked, and all characters reviewed/unmasked.
 span_domain=domain|{i for i in reviewed-excluded if answer[i].isspace()}
 gs={(s['start'],s['end']) for s in label['spans'] if s['label'] in POS and set(range(s['start'],s['end']))<=span_domain}
 ps={(s['start'],s['end']) for s in pred['spans'] if set(range(s['start'],s['end']))<=span_domain}
 return dict(question_id=label['question_id'],characters=prf(len(gold&guess),len(guess-gold),len(gold-guess)),exact_spans=prf(len(gs&ps),len(ps-gs),len(gs-ps)),answer_presence=prf(int(bool(gold) and bool(guess)),int(not gold and bool(guess)),int(bool(gold) and not guess)),answer_tn=int(not gold and not guess),scored_characters=len(domain),reviewed_characters=len(reviewed),masked_characters=len(reviewed&excluded),answer_characters=n,excluded_gold_spans=sum(s['label'] in POS for s in label['spans'])-len(gs),excluded_prediction_spans=len(pred['spans'])-len(ps),fn_ranges=ranges(gold-guess),fp_ranges=ranges(guess-gold),gold_positive=bool(gold),prediction_positive=bool(guess))

def aggregate(rows):
 result=dict(answers=len(rows),scored_characters=sum(r['scored_characters'] for r in rows),reviewed_characters=sum(r['reviewed_characters'] for r in rows),masked_characters=sum(r['masked_characters'] for r in rows),answer_characters=sum(r['answer_characters'] for r in rows))
 for unit in ['characters','exact_spans','answer_presence']:
  result[unit]=prf(*(sum(r[unit][k] for r in rows) for k in ['tp','fp','fn']))
 result['answer_tn']=sum(r['answer_tn'] for r in rows)
 result['excluded_gold_spans']=sum(r['excluded_gold_spans'] for r in rows);result['excluded_prediction_spans']=sum(r['excluded_prediction_spans'] for r in rows)
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-id',default='common512-v2');a=p.parse_args()
 records={r['question_id']:r for r in frozen() if r['detector_target']}
 pred={m:{} for m in MODELS};status={};allslots=[]
 for m in MODELS:
  for q,r in records.items():
   path=OUT/'predictions'/m/a.run_id/f'{q}.json'
   if path.exists():
    d=load(path)
    if d['status']=='completed':pred[m][q]=d
    allslots.append(dict(model=m,question_id=q,status=d['status'],attempt=d['attempt']))
   else:allslots.append(dict(model=m,question_id=q,status='not_run',attempt=0))
  ds=list(pred[m].values());times=[r['inference_seconds'] for r in ds]
  status[m]=dict(status_counts=dict(collections.Counter(s['status'] for s in allslots if s['model']==m)),inference_seconds_sum=sum(times),inference_seconds_median=statistics.median(times) if times else None,peak_allocated_bytes=max((r['peak_allocated_bytes'] for r in ds),default=0),peak_reserved_bytes=max((r['peak_reserved_bytes'] for r in ds),default=0),checked_characters=sum(sum(e-s for s,e in r['checked_ranges']) for r in ds),unchecked_characters=sum(sum(e-s for s,e in r['unchecked_ranges']) for r in ds),window_count=sum(r['window_count'] for r in ds))
 save(OUT/'evaluation/slots.json',allslots)
 qs={r['question_id']:r for r in map(json.loads,(ROOT/'project-docs/평가데이터/v2/evaluation/questions_300.jsonl').read_text().splitlines())}
 report=dict(run_id=a.run_id,status=status,generated_answers=295,planned_slots=885,final_human_approved_scores=None,final_gold_count=0,scope='development material; partial reviewed subset; provisional labels only',metric_policy=dict(unit='Unicode codepoint',zero_denominator='null, never inflated to one',char='micro positive class P/R/F1',exact_span='one-to-one identical boundaries; require all non-whitespace characters checked and full span reviewed/unmasked; original boundaries, no clipping',answer='positive within scored domain, not whole-answer truth',mask='uncertain,citation_error,quality_only,unreviewed and tokenizer gaps',paired='same question IDs and same character domain across all 3 models',threshold='0.5 fixed, no tuning',posthoc_source_truth='not evaluated'))
 for kind,path in [('agent_draft',OUT/'annotation/agent_draft/labels.json'),('adjudication_provisional',OUT/'annotation/adjudicated/proposals.json')]:
  labels=load(path);by={r['question_id']:r for r in labels};scored={};paired_scored={}
  paired_ids=set.intersection(*(set(pred[m]) for m in MODELS))&{r['question_id'] for r in labels if r['reviewed_ranges']}
  for m in MODELS:
   scored[m]=[];paired_scored[m]=[]
   for q,d in pred[m].items():
    answer=load(PRIVATE/'inputs'/f'{q}.json')['actual_answer'];l=by[q]
    s=score_one(l,d,answer)
    if s:scored[m].append(s)
    if q in paired_ids:
     domain=set.intersection(*(expand(pred[k][q]['checked_ranges'],len(answer)) for k in MODELS))
     s=score_one(l,d,answer,domain)
     if s:paired_scored[m].append(s)
   save(OUT/'evaluation'/kind/f'{m}-per-answer.json',scored[m])
  report[kind]=dict(reviewed_answers=sum(bool(l['reviewed_ranges']) for l in labels),unreviewed_answers=sum(not l['reviewed_ranges'] for l in labels),per_model={m:aggregate(scored[m]) for m in MODELS},paired={m:aggregate(paired_scored[m]) for m in MODELS},paired_question_ids=sorted(paired_ids),by_company={m:{c:aggregate([r for r in scored[m] if qs[r['question_id']]['company_id']==c]) for c in sorted({q['company_id'] for q in qs.values()})} for m in MODELS},by_length={m:{group:aggregate([r for r in scored[m] if (r['answer_characters']>=600)==long]) for group,long in [('lt600',False),('ge600',True)]} for m in MODELS})
  by_type={}
  for m in MODELS:
   by_type[m]={}
   for typ in sorted(POS):
    tp=fn=0
    for q in paired_ids:
     l=by[q];answer=load(PRIVATE/'inputs'/f'{q}.json')['actual_answer'];n=len(answer)
     domain=expand(l['reviewed_ranges'],n)-expand([[s['start'],s['end']] for s in l['spans'] if s['label'] in MASK],n)
     domain &= set.intersection(*(expand(pred[k][q]['checked_ranges'],n) for k in MODELS))
     gold=expand([[s['start'],s['end']] for s in l['spans'] if s['label']==typ],n)&domain
     guess=expand([[s['start'],s['end']] for s in pred[m][q]['spans']],n)&domain
     tp+=len(gold&guess);fn+=len(gold-guess)
    by_type[m][typ]=dict(tp=tp,fn=fn,recall=tp/(tp+fn) if tp+fn else None,precision=None,precision_reason='detectors do not predict error subtype')
  report[kind]['paired_by_gold_error_type']=by_type
  # Compact FN/FP cases point to exact answer offsets, no whole evidence export.
  cases=[]
  for m in MODELS:
   for typ in ['fn_ranges','fp_ranges']:
    top=sorted([r for r in scored[m] if r[typ]],key=lambda r:sum(e-s for s,e in r[typ]),reverse=True)[:5]
    for r in top:
     answer=load(PRIVATE/'inputs'/f'{r["question_id"]}.json')['actual_answer']
     cases.append(dict(model=m,kind=typ,question_id=r['question_id'],ranges=r[typ],quotes=[answer[s:min(e,s+100)] for s,e in r[typ][:3]]))
  save(OUT/'evaluation'/kind/'cases.json',cases)
 save(OUT/'evaluation/summary.json',report)
 # Review queue includes negatives and agreement cases, stratified by company.
 queue=[]
 for q in records:
  counts=[len(pred[m][q]['spans']) if q in pred[m] else None for m in MODELS]
  shared=set.intersection(*({i for s in pred[m][q]['spans'] for i in range(s['start'],s['end'])} for m in MODELS)) if None not in counts else set()
  group='missing_prediction' if None in counts else 'all_no_prediction' if not any(counts) else 'shared_positive_characters' if shared else 'disagreement'
  queue.append(dict(question_id=q,company_id=qs[q]['company_id'],split=qs[q]['split'],bid_key=qs[q]['bid_key'],stratum=group,human_approval='pending'))
 selected=[]
 for company in sorted({r['company_id'] for r in queue}):
  for group in ['all_no_prediction','shared_positive_characters','disagreement']:
   selected.extend(sorted([r for r in queue if r['company_id']==company and r['stratum']==group],key=lambda r:r['question_id'])[:2])
 save(OUT/'annotation/human_review_queue.json',dict(all_295=queue,stratified_suggestions=selected,sampling='deterministic first 2 IDs per company/presence stratum; shared_positive_characters requires actual character overlap across all 3; not final approval'))
 print(json.dumps({m:status[m]['status_counts'] for m in MODELS}), 'reviewed', report['agent_draft']['reviewed_answers'])
if __name__=='__main__':main()
