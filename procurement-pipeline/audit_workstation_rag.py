"""Post-run integrity and gold comparison. Never imported by RAG runtime."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
import statistics
import rag_pilot as p
from evaluate_rag_pilot import coverage


def audit(output,work,run_id):
    p.OUT=output;p.WORK=work;p.DB=work/'index.sqlite'
    state=p.read(output/'evaluation'/f'{run_id}-state.json')
    requests=p.read(output/'runtime/requests.json')
    chunks=p.load_chunks();registry=p.registry();canonical={c['chunk_id']:c for c in chunks}
    gold={q['question_id']:q for q in p.lines(p.V2/'evaluation/questions_300.jsonl')}
    reviews=[];bad=[];durations=[];all_results=[]
    for req in requests:
        qid=req['question_id'];attempts=state['attempts'].get(qid,[])
        if not attempts:continue
        latest=attempts[-1];path=output/latest['record_path']
        if not path.exists():continue
        record=p.read(path);all_results.append(record);issues=[]
        if record['request']!=req:issues.append('request_mismatch')
        permitted={c['chunk_id'] for c in p.eligible(req,chunks,registry)}
        retrieved={c['chunk_id']:c for c in record.get('retrieved',[])}
        if len(retrieved)!=len(record.get('retrieved',[])):issues.append('duplicate_retrieved_id')
        for cid,c in retrieved.items():
            source=canonical.get(cid)
            if cid not in permitted or source is None:issues.append('unauthorized_retrieved');continue
            for key in ['document_id','document_version','text_start','text_end','tenant_id','security_level','bid_key','scenario_id']:
                if c.get(key)!=source.get(key):issues.append('metadata_'+key)
            if c['text_sha256']!=p.digest(source['text']):issues.append('text_hash')
        evidence=record.get('prompt_evidence',[])
        if [c['citation'] for c in evidence]!=list(range(1,len(evidence)+1)):issues.append('citation_mapping')
        for c in evidence:
            source=canonical.get(c['chunk_id'])
            if c['chunk_id'] not in retrieved or c['chunk_id'] not in permitted:issues.append('unauthorized_prompt');continue
            if any(c[k]!=source[k] for k in ['text_start','text_end']):issues.append('prompt_offset')
            if c['text_sha256']!=p.digest(source['text']):issues.append('prompt_text_hash')
        if record['status']=='access_denied':
            if not p.request_policy(req,registry) or record.get('llm_called') or retrieved or evidence or record['actual_answer']!=p.DENIAL:issues.append('denial_integrity')
        if record.get('prompt_sha256'):
            private=work/'private_runs'/record['run_id']/(qid+'.prompt.json')
            if not private.exists():issues.append('private_prompt_missing')
            else:
                messages=p.read(private)
                if p.digest(json.dumps(messages,ensure_ascii=False))!=record['prompt_sha256']:issues.append('private_prompt_hash')
                sources=[canonical[c['chunk_id']] for c in evidence if c['chunk_id'] in canonical]
                if record.get('system_prompt_sha256')==p.digest(p.SYSTEM) and messages!=p.prompt(req,sources,chunks,registry):issues.append('prompt_reconstruction')
        answer=record.get('actual_answer') or ''
        citations=[int(n) for n in re.findall(r'\[(\d+)\]',answer)]
        invalid=[n for n in citations if n not in {c['citation'] for c in evidence}]
        q=gold[qid];annotations=q['public_notice_evidence']+q['company_evidence']
        used={c['chunk_id'] for c in evidence}
        checks=[coverage(e,[c for cid,c in retrieved.items() if cid in used]) for e in annotations]
        if record.get('generation_seconds') is not None:durations.append(record['generation_seconds'])
        if issues:bad.append(dict(question_id=qid,issues=sorted(set(issues))))
        reviews.append(dict(question_id=qid,split=q['split'],category=q['category'],question=req['question'],
            expected_answer=q['expected_answer'],actual_answer=record.get('actual_answer'),status=record['status'],
            record_path=latest['record_path'],integrity_issues=issues,invalid_citations=invalid,
            truncated=record.get('finish_reason')=='length',empty=record['status']=='generated' and not answer.strip(),
            prompt_evidence_checks=checks,agent_review='pending',human_approval='pending',hallucination_spans=None))
    counts=dict(Counter(r['status'] for r in reviews))
    report=dict(run_id=run_id,target_count=len(requests),record_count=len(reviews),not_started=len(requests)-len(reviews),
        counts=counts,integrity_failures=bad,truncated=sum(r['truncated'] for r in reviews),
        incomplete_attempts=sum(r['status'] not in ('generated','access_denied','retrieval_only') for r in reviews),
        invalid_citation_answers=sum(bool(r['invalid_citations']) for r in reviews),empty_answers=sum(r['empty'] for r in reviews),
        generation_seconds=dict(total=sum(durations),median=statistics.median(durations) if durations else None),
        semantic_correctness='requires_agent_content_review',human_approval='pending',hallucination_span_labeling='not_performed')
    p.dump(output/'evaluation'/f'{run_id}-audit.json',report)
    p.dump(output/'evaluation'/f'{run_id}-review-inputs.json',reviews)
    fields=['question_id','split','category','question','expected_answer','actual_answer','status','truncated','invalid_citations','agent_review','human_approval']
    with (output/'evaluation'/f'{run_id}-review.tsv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',delimiter='\t',lineterminator='\n');writer.writeheader();writer.writerows(reviews)
    print(json.dumps(report,ensure_ascii=False))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--run-id',required=True)
    args=parser.parse_args();audit(args.output.resolve(),args.work.resolve(),args.run_id)
