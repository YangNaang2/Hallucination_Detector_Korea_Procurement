"""Post-run gold comparison only. Never called by index/retrieval/prompt construction."""
from collections import Counter
import re
import rag_pilot as p


def coverage(evidence, retrieved):
    if evidence.get('chunk_id'):
        return dict(kind='company_chunk', hit=any(c['chunk_id']==evidence['chunk_id'] for c in retrieved))
    a, b = evidence.get('text_start'), evidence.get('text_end')
    if a is None or b is None:
        return dict(kind='manual_pdf', hit=None, reason='page-based source; requires content review')
    matching = [c for c in retrieved if c.get('sha256')==evidence.get('sha256') and c.get('bid_key')==evidence.get('bid_key')]
    spans = sorted((max(a,c['text_start']),min(b,c['text_end'])) for c in matching if max(a,c['text_start'])<min(b,c['text_end']))
    total, end = 0, a
    for start, stop in spans:
        total += max(0, stop-max(start,end))
        end = max(end,stop)
    return dict(kind='source_interval', hit=total>0, quoted_interval_coverage=round(total/max(1,b-a),4),
                note='골든 인용 전체가 최소 정답 구간은 아님. 교집합은 정답 근거 충족 판정이 아님.')


def evaluate(run_id):
    qs = {q['question_id']:q for q in p.lines(p.V2/'evaluation/questions_300.jsonl')}
    report = []
    for path in sorted((p.OUT/'evaluation/runs'/run_id).glob('*.json')):
        r = p.read(path)
        q = qs[r['request']['question_id']]
        evidence = q['public_notice_evidence'] + q['company_evidence']
        checks = [coverage(e,r['retrieved']) for e in evidence]
        used_ids = {x['chunk_id'] for x in r.get('prompt_evidence',[])}
        prompt_checks = [coverage(e,[c for c in r['retrieved'] if c['chunk_id'] in used_ids]) for e in evidence]
        answer = r['actual_answer'] or ''
        citations = [int(x) for x in re.findall(r'\[(\d+)\]',answer)]
        report.append(dict(question_id=q['question_id'], status=r['status'], category=q['category'],
           expected_action=q['expected_action'], evidence_checks=checks,
           prompt_evidence_checks=prompt_checks,
           prompt_any_annotated_evidence_hit=any(c['hit'] is True for c in prompt_checks),
           context_budget_dropped_chunks=len(r['retrieved'])-len(used_ids),
           any_annotated_evidence_hit=any(c['hit'] is True for c in checks),
           all_checkable_annotated_evidence_hit=bool(checks) and all(c['hit'] is True for c in checks),
           correct_denial=(r['status']=='access_denied') if q['expected_action']=='접근 거절' else None,
           citation_numbers_valid=all(n in {e['citation'] for e in r.get('prompt_evidence',[])} for n in citations),
           citation_count=len(citations), answer_truncated=r.get('finish_reason')=='length',
           answer_semantic_correctness='agent_review_pending', human_approval='pending',
           search_seconds=r['search_seconds'], generation_seconds=r['generation_seconds']))
    answered = [r for r in report if r['status']!='access_denied']
    output = dict(run_id=run_id, counts=dict(Counter(r['status'] for r in report)), questions=report,
        any_annotated_evidence_hit=sum(r['any_annotated_evidence_hit'] for r in answered),
        all_checkable_annotated_evidence_hit=sum(r['all_checkable_annotated_evidence_hit'] for r in answered),
        non_denied_questions=len(answered),
        limitation='근거 ID/구간 대응 진단. Recall@K·답변 정확도·환각률이 아님. 인용 번호 유효성은 주장 지지 여부가 아님.')
    p.dump(p.OUT/'evaluation'/f'{run_id}-assessment.json',output)
    print(run_id,output['counts'],'any/all evidence',output['any_annotated_evidence_hit'],output['all_checkable_annotated_evidence_hit'])


if __name__ == '__main__':
    import sys
    evaluate(sys.argv[1])
