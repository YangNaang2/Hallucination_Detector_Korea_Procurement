"""Compose the latest, explicitly rerun records without cherry-picking successful answers."""
from collections import Counter
import csv
import sys
import rag_pilot as p


def records(run):
    return {f.stem:p.read(f) for f in (p.OUT/'evaluation/runs'/run).glob('*.json')}


def reviews(run):
    return {q['question_id']:q for q in p.read(p.OUT/'evaluation'/f'{run}-content-review.json')['questions']}


def finalize(base, followup):
    original, newer = records(base), records(followup)
    selected = {r['question_id'] for r in p.read(p.OUT/'runtime/requests.json')}
    assert set(original)==selected and len(original)==25
    assert set(newer)<=selected and newer
    old_review, new_review = reviews(base), reviews(followup)
    assert set(old_review)==set(original) and set(new_review)==set(newer)
    gold={q['question_id']:q for q in p.lines(p.V2/'evaluation/questions_300.jsonl')}
    effective=[]
    for qid in sorted(selected):
        chosen=followup if qid in newer else base
        r=newer[qid] if qid in newer else original[qid]
        v=new_review[qid] if qid in newer else old_review[qid]
        assert r['request']==original[qid]['request'], 'follow-up changed question/session/scenario'
        effective.append(dict(question_id=qid, company_id=r['request']['company_id'], selected_run=chosen,
            record_path=f'evaluation/runs/{chosen}/{qid}.json',
            review_path=f'evaluation/{chosen}-content-review.json',
            status=r['status'], agent_verdict=v['verdict'], baseline_verdict=old_review[qid]['verdict'],
            followup_applied=qid in newer, human_approval='pending', hallucination_spans=None))
    report=dict(base_run=base,followup_run=followup,unique_questions=len(effective),
        counts=dict(Counter(r['status'] for r in effective)),
        company_counts=dict(Counter(r['company_id'] for r in effective)),
        agent_review_counts=dict(Counter(r['agent_verdict'] for r in effective)),
        rerun_questions=sorted(newer), records=effective,
        selection_policy='Every follow-up record supersedes its base record even if worse or failed; originals retained.',
        interpretation='Development cohort across recorded code versions. Verdict counts include omissions/citation defects and are not hallucination rates or independent benchmark accuracy.',
        human_approval='pending', hallucination_span_labeling='not_performed')
    p.dump(p.OUT/'evaluation/effective_results.json',report)
    with (p.OUT/'evaluation/effective_review.tsv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter='\t')
        w.writerow(['question_id','company','selected_run','question','expected_answer','actual_answer','agent_verdict','agent_notes','previous_answer_if_rerun','human_approval'])
        for row in effective:
            qid=row['question_id'];r=newer.get(qid,original[qid]);v=new_review.get(qid,old_review[qid]);q=gold[qid]
            w.writerow([qid,row['company_id'],row['selected_run'],q['question'],q['expected_answer'],r['actual_answer'],v['verdict'],v['finding'],original[qid]['actual_answer'] if qid in newer else '', 'pending'])
    print({k:v for k,v in report.items() if k!='records'})


if __name__=='__main__':finalize(*sys.argv[1:])
