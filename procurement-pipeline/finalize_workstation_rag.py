"""Post-run selection and review export; never imported by retrieval/generation."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import rag_pilot as p

OUT = p.ROOT / 'project-docs/RAG파일럿/workstation-275'
INITIAL = 'workstation275-gpu-v1'
REPAIR = 'routing-repair-v2'


def unique_rows(rows):
    result = {}
    for row in rows:
        qid = row['question_id']
        if qid in result:
            raise ValueError('duplicate question: ' + qid)
        result[qid] = row
    return result


def select_latest(initial, replacements, required_ids):
    if set(replacements) != set(required_ids) or not set(replacements) <= set(initial):
        raise ValueError('replacement scope differs from recorded retrieval impact')
    # A failed newer attempt is selected too. Never retain an earlier success
    # because its answer or execution status looks better.
    return initial | replacements


def state_records(output, run_id):
    state = p.read(output / 'evaluation' / (run_id + '-state.json'))
    result = {}
    for qid, attempts in state['attempts'].items():
        if not attempts:
            continue
        attempt = attempts[-1]
        path = output / attempt['record_path']
        record = p.read(path)
        if record['request']['question_id'] != qid or record['status'] != attempt['status']:
            raise ValueError('checkpoint/raw record mismatch')
        result[qid] = dict(question_id=qid, record=record,
            record_path=str(path.relative_to(p.ROOT)), run_id=run_id,
            attempts=len(attempts), condition=run_id)
    return result


def write_tsv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter='\t',
            lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def main():
    gold = unique_rows(p.lines(p.V2 / 'evaluation/questions_300.jsonl'))
    initial_rows = []
    audits = []
    for shard in ('w1', 'w2', 'w3', 'w4'):
        output = OUT / 'shards' / shard
        initial_rows.extend(state_records(output, INITIAL).values())
        audits.append(p.read(output / 'evaluation' / (INITIAL + '-audit.json')))
    initial = unique_rows(initial_rows)
    requested = set(p.read(OUT / 'runtime/question_ids.json'))
    if set(initial) != requested or len(initial) != 275:
        raise ValueError('initial cohort is not exactly the requested 275')
    repair_output = OUT / 'repair-v2'
    replacements = state_records(repair_output, REPAIR)
    impacts = p.read(OUT / 'validation/routing-impact.json')['records']
    affected = {r['question_id'] for r in impacts if not r['baseline']}
    selected = select_latest(initial, replacements, affected)
    reviews = unique_rows(p.read(OUT / 'evaluation' / (INITIAL + '-content-review.json'))['records'])
    repair_reviews = unique_rows(p.read(repair_output / 'evaluation' / (REPAIR + '-content-review.json'))['records'])
    if set(reviews) != requested or set(repair_reviews) != affected:
        raise ValueError('agent review coverage differs from execution')
    reviews.update(repair_reviews)
    audits.append(p.read(repair_output / 'evaluation' / (REPAIR + '-audit.json')))
    if any(a['integrity_failures'] for a in audits):
        raise ValueError('unresolved integrity failures')
    original = p.read(p.OUT / 'evaluation/effective_results.json')['records']
    if len(original) != 25 or requested & {r['question_id'] for r in original}:
        raise ValueError('baseline overlap/count')
    with (p.OUT / 'evaluation/effective_review.tsv').open(encoding='utf-8-sig') as stream:
        original_reviews = {r['question_id']:r for r in csv.DictReader(stream, delimiter='\t')}
    all_rows = dict(selected)
    for item in original:
        qid = item['question_id']; path = p.OUT / item['record_path']
        all_rows[qid] = dict(question_id=qid, record=p.read(path),
            record_path=str(path.relative_to(p.ROOT)), run_id=item['selected_run'],
            condition='preserved-v1', attempts=None)
        reviews[qid] = dict(judgment=item['agent_verdict'], reason=original_reviews[qid]['agent_notes'])
    if set(all_rows) != set(gold) or len(all_rows) != 300:
        raise ValueError('integrated IDs differ from the 300 dataset')
    exported = []; links = []; comparisons = []
    for qid, item in sorted(all_rows.items()):
        record = item['record']; answer = record.get('actual_answer'); q = gold[qid]
        if record['request']['question_id'] != qid:
            raise ValueError('baseline record mismatch')
        text_hash = p.digest(answer) if answer is not None else None
        citations = {c['citation'] for c in record.get('prompt_evidence', [])}
        invalid = sorted(set(int(x) for x in re.findall(r'\[(\d+)\]', answer or '')) - citations)
        exported.append(dict(question_id=qid, company_id=q['company_id'], split=q['split'],
            cohort='new275' if qid in requested else 'original25', condition=item['condition'],
            run_id=item['run_id'], record_path=item['record_path'], status=record['status'],
            question=q['question'], expected_answer=q['expected_answer'], actual_answer=answer,
            agent_review=reviews[qid]['judgment'], agent_notes=reviews[qid]['reason'],
            truncated=record.get('finish_reason') == 'length', invalid_citations=invalid,
            answer_sha256=text_hash, human_approval='pending', hallucination_spans=None))
        links.append(dict(question_id=qid, record_path=item['record_path'],
            record_sha256=hashlib.sha256((p.ROOT / item['record_path']).read_bytes()).hexdigest(),
            answer_sha256=text_hash, answer_field='actual_answer', prompt_sha256=record.get('prompt_sha256'),
            prompt_evidence=record.get('prompt_evidence', []), hallucination_spans=None,
            human_approval='pending'))
        if qid in affected:
            previous = initial[qid]
            old_review = next(r for r in p.read(OUT / 'evaluation' / (INITIAL + '-content-review.json'))['records'] if r['question_id']==qid)
            comparisons.append(dict(question_id=qid, previous_record=previous['record_path'],
                selected_record=item['record_path'], previous_answer=previous['record']['actual_answer'],
                selected_answer=answer, previous_judgment=old_review['judgment'],
                selected_judgment=reviews[qid]['judgment'], notes=reviews[qid]['reason']))
    new = [r for r in exported if r['cohort']=='new275']
    summary = dict(unique_questions=300, counts=dict(Counter(r['status'] for r in exported)),
        new275_counts=dict(Counter(r['status'] for r in new)),
        new275_agent_review_counts=dict(Counter(r['agent_review'] for r in new)),
        new275_truncated=sum(r['truncated'] for r in new),
        new275_invalid_citation_answers=sum(bool(r['invalid_citations']) for r in new),
        original25_preserved=True, selected_repair_ids=sorted(affected),
        initial_attempt_count=sum(r['attempts'] for r in initial.values()),
        repair_attempt_count=sum(r['attempts'] for r in replacements.values()),
        selection_policy='All changed-retrieval IDs use latest repair attempt, including failure; others latest initial attempt. Original v1 25 unchanged. Regression is separate.',
        interpretation='Mixed conditions and agent review rubric; not independent single-condition accuracy. All 275 were exposed to post-run review before routing repairs.',
        human_approval='pending', hallucination_span_labeling='not_performed')
    p.dump(OUT / 'evaluation/effective_results.json', summary | dict(records=exported))
    p.dump(OUT / 'evaluation/final_summary.json', summary)
    p.dump(OUT / 'evaluation/labeling_handoff.json', dict(records=links, answer_strings_immutable=True,
        note='Read actual_answer exactly from record_path; offsets/hashes refer to canonical source chunks, not generated answer spans. No spans have been labeled. Raw prompts remain ignored locally.'))
    p.dump(OUT / 'evaluation/repair_comparison.json', comparisons)
    write_tsv(OUT / 'evaluation/effective_review.tsv', exported, list(exported[0]))
    write_tsv(OUT / 'evaluation/integrated_status.tsv', exported,
        ['question_id','company_id','split','cohort','condition','run_id','status','agent_review','record_path','human_approval'])
    write_tsv(OUT / 'evaluation/repair_comparison.tsv', comparisons, list(comparisons[0]))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
