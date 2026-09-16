"""Isolated follow-up cohort: explicit IDs, pinned resume, append-only attempts.

Preparation alone reads gold to project the existing allowlisted request schema.
Run/index/embedding never read the evaluation dataset. Review is post-run only.
"""
import argparse
from collections import Counter
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time

import rag_pilot as p

BASE = p.OUT
FOLLOWUP = p.ROOT / 'project-docs/RAG파일럿/workstation-275'
LOCAL = p.ROOT / 'work/rag-workstation-275'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unique(items, key):
    ids = [r[key] for r in items]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate IDs')
    return set(ids)


def prepare(dataset, id_path=None):
    questions = p.lines(dataset)
    all_ids = unique(questions, 'question_id')
    effective = p.read(BASE / 'evaluation/effective_results.json')['records']
    old_ids = unique(effective, 'question_id')
    actual = []
    for item in effective:
        record = p.read(p.safe_path(BASE, item['record_path']))
        if record['request']['question_id'] != item['question_id'] or record['status'] != item['status']:
            raise ValueError('effective selection differs from raw record')
        if record['status'] not in ('generated', 'access_denied'):
            raise ValueError('baseline has unfinished question')
        actual.append(record)
    if len(all_ids) != 300 or len(old_ids) != 25 or not old_ids <= all_ids:
        raise ValueError('baseline is not 25 unique completed IDs within 300')
    remaining = all_ids - old_ids
    ids = p.read(id_path) if id_path else sorted(remaining)
    if len(ids) != len(set(ids)) or not set(ids) <= all_ids:
        raise ValueError('invalid explicit ID list')
    if not id_path and len(ids) != 275:
        raise ValueError('remaining cohort is not 275')
    by_id = {q['question_id']: q for q in questions}
    requests = [p.context.evaluation_request(by_id[qid]) for qid in ids]
    for request in requests:
        p.no_gold(request)
    # Preparation may be rerun only if byte-identical; never overwrite an experiment.
    outputs = {
        'runtime/requests.json': requests,
        'runtime/question_ids.json': ids,
        'evaluation/selection.json': dict(count=len(ids), question_ids=ids,
            dataset_sha256=sha(dataset), baseline_unique_ids=sorted(old_ids),
            baseline_counts=dict(Counter(r['status'] for r in actual)),
            total_dataset=300, remaining_unexecuted=len(remaining),
            splits=dict(Counter(by_id[q]['split'] for q in ids)),
            selection_rule='Explicit IDs, otherwise dataset IDs minus effective raw result IDs; no row slicing.',
            gold_used_in_runtime=False, human_approval='pending', hallucination_spans=None),
    }
    for relative, value in outputs.items():
        dest = FOLLOWUP / relative
        if dest.exists() and p.read(dest) != value:
            raise ValueError('preparation would change existing cohort; use a new output directory')
        p.dump(dest, value)
    print('verified baseline', len(old_ids), 'remaining', len(remaining), 'selected', len(ids))


def source_inventory():
    manifest = p.read(BASE / 'index_manifest.json')
    docs = [d for d in manifest['documents'] if d['security_level'] == 'L1']
    rows = [dict(bid_key=d['bid_key'], document_id=d['document_id'],
        attachment_id=None, relative_path=d['path'].replace('\\', '/'),
        filename=d['filename'], binary_sha256=d['sha256'], text_sha256=d['text_sha256'],
        local_status='not_located', note='Upstream attachment ID is absent in baseline manifest; do not invent.') for d in docs]
    p.dump(FOLLOWUP / 'sources/required.json', dict(notices=sorted({d['bid_key'] for d in docs}),
        required_documents=rows, baseline_exclusions=manifest['skipped'],
        baseline_documents=223, baseline_parent_chunks=3275,
        source_cache_sha256=manifest['source_cache_sha256'],
        input_contract='source-texts.json entries: bid, relative, sha256, text, name, method. Transfer raw tree unchanged; do not substitute answer excerpts.'))
    dest = FOLLOWUP / 'sources/required.tsv'
    with dest.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    print('required public documents', len(rows), 'notices', len({d['bid_key'] for d in docs}), 'baseline exclusions',len(manifest['skipped']))


def configure():
    p.OUT = FOLLOWUP
    p.WORK = LOCAL
    p.DB = LOCAL / 'index.sqlite'
    LOCAL.mkdir(parents=True, exist_ok=True)
    profile_path=LOCAL/'active_generation.json'
    if profile_path.exists():
        endpoint=p.read(profile_path).get('endpoint','http://127.0.0.1:18767')
        if endpoint not in ('http://127.0.0.1:18767','http://127.0.0.1:18769'):
            raise ValueError('only pinned loopback inference endpoints allowed')
        p.ENDPOINT=endpoint


def fingerprint(requests):
    return dict(requests_sha256=sha(requests), index_sha256=sha(FOLLOWUP / 'index_manifest.json'),
        embedding_sha256=sha(FOLLOWUP / 'embedding_config.json'),
        vectors_sha256=sha(LOCAL / 'vectors.npz'), queries_sha256=sha(LOCAL / 'query_vectors.npz'),
        generation=p.generation_profile(),
        code={f.name:sha(f) for f in sorted((p.ROOT/'procurement-pipeline').glob('*.py'))})


def run_batch(run_id, limit=None, retry=False):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', run_id):
        raise ValueError('unsafe run ID')
    configure()
    requests_path = FOLLOWUP / 'runtime/requests.json'
    requests = p.read(requests_path)
    unique(requests, 'question_id')
    for request in requests:
        p.no_gold(request)
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', request['question_id']):
            raise ValueError('unsafe question ID')
    # Check missing inputs before creating any attempted question or failure result.
    config = fingerprint(requests_path)
    config['generation_model_sha256_verified'] = sha(LOCAL / config['generation']['model_path'])
    if config['generation_model_sha256_verified'] != config['generation']['model_sha256']:
        raise ValueError('generation weights changed')
    p.load_chunks()
    p.check_server(config['generation'])
    state_path = FOLLOWUP / 'evaluation' / (run_id + '-state.json')
    with (LOCAL/'batch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = p.read(state_path) if state_path.exists() else dict(run_id=run_id,
            code_head=p.repo_hash(), config=config, attempts={}, human_approval='pending',
            hallucination_spans=None, selection_policy='Latest attempted result, including failed/interrupted; no success-based selection.')
        if state['config'] != config:
            raise ValueError('resume configuration changed; create a NEW run ID')
        state.update(pid=os.getpid(), current_question=None)
        p.dump(state_path, state)
        count = 0
        try:
            for req in requests:
                qid = req['question_id']; attempts = state['attempts'].setdefault(qid, [])
                # Reconcile process death after result commit and before state commit.
                if attempts and attempts[-1]['status'] == 'running':
                    prev = attempts[-1]; result = FOLLOWUP / prev['record_path']
                    if result.exists():
                        prev['status'] = p.read(result)['status']
                        if prev['status'] == 'generation_running':
                            record = p.read(result)
                            record['status'] = 'interrupted'
                            p.dump(result, record)
                            prev['status'] = 'interrupted'
                    else:
                        prev['status'] = 'interrupted'
                    p.dump(state_path, state)
                if attempts and (attempts[-1]['status'] in ('generated','access_denied') or not retry):
                    continue
                if limit is not None and count >= limit:
                    break
                attempt_id = f'{run_id}-{qid}-a{len(attempts)+1:03}'
                relative = f'evaluation/runs/{attempt_id}/{qid}.json'
                attempt = dict(attempt_id=attempt_id, record_path=relative, status='running')
                attempts.append(attempt); state['current_question'] = qid
                p.dump(state_path, state)
                started = time.monotonic()
                try:
                    p.run(attempt_id, use_dense=True, execute=True, purpose=True,
                          only=[qid], requests_path=requests_path)
                    record = p.read(FOLLOWUP / relative)
                    if record['request'] != req:
                        raise ValueError('stored request mismatch')
                    if record['status'] == 'generated' and not (record['actual_answer'] or '').strip():
                        record['status'] = 'empty_response'
                        p.dump(FOLLOWUP / relative, record)
                    attempt['status'] = record['status']
                except Exception as exc:
                    attempt['status'] = 'timeout' if isinstance(exc, TimeoutError) else 'execution_failed'
                    # No fabricated answer, and exception content may contain private data.
                    if not (FOLLOWUP / relative).exists():
                        p.dump(FOLLOWUP / relative, dict(run_id=attempt_id, request=req,
                            status=attempt['status'], error_type=type(exc).__name__, actual_answer=None,
                            retrieved=[], prompt_evidence=[], search_seconds=None, generation_seconds=None,
                            human_approval='pending', hallucination_spans=None, llm_called=None))
                attempt['wall_seconds'] = time.monotonic() - started
                count += 1
                p.dump(state_path, state)
                print('batch',run_id,'attempted',count, 'latest',dict(Counter(a[-1]['status'] for a in state['attempts'].values() if a)),flush=True)
        finally:
            state.update(pid=None, current_question=None)
            p.dump(state_path, state)


def main():
    global FOLLOWUP, LOCAL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','sources','index','embed','run','summarize'])
    parser.add_argument('--output',type=Path,default=FOLLOWUP)
    parser.add_argument('--work',type=Path,default=LOCAL)
    parser.add_argument('--dataset',type=Path,default=p.V2/'evaluation/questions_300.jsonl')
    parser.add_argument('--ids',type=Path)
    parser.add_argument('--source-cache',type=Path)
    parser.add_argument('--source-root',type=Path)
    parser.add_argument('--run-id')
    parser.add_argument('--limit',type=int)
    parser.add_argument('--retry-failed',action='store_true')
    args=parser.parse_args()
    FOLLOWUP=args.output.resolve(); LOCAL=args.work.resolve()
    if FOLLOWUP == BASE.resolve() or LOCAL == p.WORK.resolve():
        parser.error('follow-up paths must preserve original pilot')
    if args.action=='prepare': prepare(args.dataset,args.ids)
    elif args.action=='sources': source_inventory()
    elif args.action=='index':
        if not args.source_cache or not args.source_root: parser.error('source cache and root required')
        configure()
        if p.DB.exists() or (FOLLOWUP/'index_manifest.json').exists():
            parser.error('existing index must be preserved; use new output/work paths')
        p.build_index(args.source_cache,args.source_root)
    elif args.action=='embed':
        configure()
        import rag_pilot_embedding as embedding
        embedding.MODEL=LOCAL/'e5'
        if (LOCAL/'vectors.npz').exists():
            parser.error('existing document vectors must be preserved; use new output/work paths')
        queries_exist=(LOCAL/'query_vectors.npz').exists()
        if queries_exist:
            import numpy as np
            with np.load(LOCAL/'query_vectors.npz',allow_pickle=False) as data:
                expected=[p.digest(r['question']) for r in p.read(FOLLOWUP/'runtime/requests.json')]
                if data['hashes'].tolist()!=expected or str(data['revision'])!=embedding.REVISION:
                    parser.error('existing query vectors do not match selected requests/model')
        embedding.build()
        if not queries_exist: embedding.query_vectors()
    elif args.action=='run':
        if not args.run_id: parser.error('--run-id required')
        if args.limit is not None and args.limit<1: parser.error('positive --limit required')
        run_batch(args.run_id,args.limit,args.retry_failed)
    else:
        if not args.run_id: parser.error('--run-id required')
        summarize(args.run_id)


def summarize(run_id):
    """Latest attempts, including failures; never pools conditions into accuracy."""
    state=p.read(FOLLOWUP/'evaluation'/f'{run_id}-state.json')
    requests=p.read(FOLLOWUP/'runtime/requests.json')
    rows=[]
    for req in requests:
        attempts=state['attempts'].get(req['question_id'],[])
        latest=attempts[-1] if attempts else {}
        record=p.read(FOLLOWUP/latest['record_path']) if latest and (FOLLOWUP/latest['record_path']).exists() else {}
        rows.append(dict(question_id=req['question_id'],question=req['question'],
            status=record.get('status',latest.get('status','not_started')), actual_answer=record.get('actual_answer'),
            record_path=latest.get('record_path'), attempt_count=len(attempts),
            answer_truncated=record.get('finish_reason')=='length',
            agent_review='pending',human_approval='pending',hallucination_spans=None))
    report=dict(run_id=run_id,target_count=len(requests),counts=dict(Counter(r['status'] for r in rows)),
        records=rows, config=state['config'],selection_policy=state['selection_policy'],
        quality='Not yet content-reviewed; counts are execution states, not accuracy.',human_approval='pending')
    p.dump(FOLLOWUP/'evaluation'/f'{run_id}-effective.json',report)
    with (FOLLOWUP/'evaluation'/f'{run_id}-review.tsv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),delimiter='\t', lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    print(report['counts'])


if __name__=='__main__':main()
