"""Post-run audit only. Never imported by the retrieval/generation runtime."""
from collections import Counter
import csv
import json
import statistics
import sys

import rag_pilot as p
import evaluate_rag_pilot as evaluation


def summarize(run_id):
    evaluation.evaluate(run_id)
    records = [p.read(f) for f in sorted((p.OUT/'evaluation/runs'/run_id).glob('*.json'))]
    selected = {r['question_id'] for r in p.read(p.OUT/'runtime/requests.json')}
    gold = {q['question_id']: q for q in p.lines(p.V2/'evaluation/questions_300.jsonl')}
    chunks, reg = p.load_chunks(), p.registry()
    by_id = {c['chunk_id']: c for c in chunks}
    failures, inspected = [], 0
    for r in records:
        req = r['request']; qid = req['question_id']
        allowed = {c['chunk_id'] for c in p.eligible(req, chunks, reg)}
        for c in r['retrieved']:
            inspected += 1
            source = by_id.get(c['chunk_id'])
            if c['chunk_id'] not in allowed or source is None:
                failures.append([qid, 'unauthorized/unknown retrieved chunk']); continue
            if any(c[k] != source[k] for k in ['document_id','document_version','text_start','text_end','tenant_id','security_level']):
                failures.append([qid, 'metadata mismatch'])
            if c['text_sha256'] != p.digest(source['text']):
                failures.append([qid, 'source text hash mismatch'])
        selected_ids = {c['chunk_id'] for c in r['retrieved']}
        for c in r.get('prompt_evidence', []):
            if c['chunk_id'] not in selected_ids or c['chunk_id'] not in allowed:
                failures.append([qid, 'prompt evidence outside authorized retrieval'])
        if r['status'] == 'access_denied':
            if not p.request_policy(req, reg) or r['llm_called'] or r['retrieved'] or r.get('prompt_evidence') or r['actual_answer'] != p.DENIAL:
                failures.append([qid, 'invalid denial path'])
        if r.get('hallucination_spans') is not None:
            failures.append([qid, 'unexpected span labeling'])
    ids = [r['request']['question_id'] for r in records]
    durations = [r['generation_seconds'] for r in records if r['status']=='generated']
    review_path = p.OUT/'evaluation'/f'{run_id}-content-review.json'
    review = p.read(review_path) if review_path.exists() else {'questions': [], 'human_approval': 'pending'}
    reviewed = {q['question_id']: q for q in review['questions']}
    report = dict(run_id=run_id, counts=dict(Counter(r['status'] for r in records)),
        company_counts=dict(Counter(r['request']['company_id'] for r in records)),
        selected_25_complete=len(ids)==25 and len(set(ids))==25 and set(ids)==selected,
        inspected_retrieved_chunks=inspected, integrity_failures=failures,
        generation_seconds=dict(total=sum(durations), median=statistics.median(durations) if durations else None,
            minimum=min(durations) if durations else None, maximum=max(durations) if durations else None),
        timing_scope='Successful local HTTP generation only; model/index/query encoding/preflight/retries excluded. Wall-clock may include host scheduling or suspension.',
        agent_review_counts=dict(Counter(v['verdict'] for v in reviewed.values())),
        agent_review_complete=bool(ids) and set(reviewed)==set(ids),
        human_approval='pending', hallucination_span_labeling='not_performed',
        limitation='Finite offline fixture audit. Not a production authentication or universal non-leakage guarantee.')
    p.dump(p.OUT/'evaluation'/f'{run_id}-summary.json', report)
    # Gold and actual answers are deliberately confined to the evaluation directory.
    with (p.OUT/'evaluation'/f'{run_id}-review.tsv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f,delimiter='\t')
        writer.writerow(['question_id','company','question','expected_answer','actual_answer','execution_status','agent_verdict','agent_notes','human_approval'])
        for r in records:
            qid=r['request']['question_id'];q=gold[qid];v=reviewed.get(qid,{})
            writer.writerow([qid,q['company_id'],q['question'],q['expected_answer'],r['actual_answer'],r['status'],v.get('verdict','pending'),v.get('finding',''),'pending'])
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__': summarize(sys.argv[1])
