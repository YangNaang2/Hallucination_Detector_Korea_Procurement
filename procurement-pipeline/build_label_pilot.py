"""Reproduce an evaluation-only agent draft. No inference, indexing or approval."""
import argparse, collections, csv, hashlib, html, json, re, sqlite3, subprocess
from pathlib import Path
from label_pilot_specs import SPECS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'project-docs/환각라벨링/pilot-25-v1'
BASE = ROOT / 'project-docs/RAG파일럿/workstation-275/evaluation'
REV = '772bfd5'
SUPPLEMENTAL = {
    'C03-N48-E1': ('L1-R26BK01605618-000-5fc0a50d45533973-CH-00000','11:00'),
    'C02-N46-E2': ('L1-R26BK01505476-000-b81b01796f0a6bcf-CH-00000','본점소재지(대구)'),
    'C05-S03': ('C05-STAFF-1.0.0-r1-CH-877ae65cc809','고용 형태'),
    'C02-S03': ('C02-STAFF-1.0.0-r1-CH-81cbb0e01cdb','기준일 잔여 FTE'),
}
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p, d): p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def validate(rows):
    assert len(rows)==25 and len({r['question_id'] for r in rows})==25
    assert collections.Counter(r['company_id'] for r in rows)=={f'C{i:02}':5 for i in range(1,6)}
    for r in rows:
        assert r['human_approval']=='pending' and r['training_ready'] is False
        assert sha(r['actual_answer'].encode())==r['answer_sha256']
        assert r['approved_spans'] is None
        refs={e['evidence_id'] for e in r['evidence']}
        for s in r['draft_spans']+r['review_candidates']:
            assert 0<=s['start']<s['end']<=len(r['actual_answer'])
            assert r['actual_answer'][s['start']:s['end']]==s['quote']
            assert s['evidence_ids'] and set(s['evidence_ids'])<=refs
            assert s['human_decision']=='pending'
        for e in r['evidence']:
            assert e['end']-e['start']==len(e['quote'])
            assert e['company_id'] in (None,r['company_id'])
            assert e['scope'] in ('prompt_context','reference_only_not_in_prompt')
    return True

def build(index, cache):
    corpus={k:json.loads(v) for k,v in sqlite3.connect(index.resolve().as_uri()+'?mode=ro',uri=True).execute('SELECT chunk_id,payload FROM corpus')}
    rawtexts={r['sha256']:r['text'] for r in load(cache)}
    effective=load(BASE/'effective_results.json')['records']
    rows=[]
    for short, spec in sorted(SPECS.items()):
        qid='ASTRA-300-'+short; r=next(x for x in effective if x['question_id']==qid)
        blob=subprocess.check_output(['git','show',REV+':'+r['record_path']],cwd=ROOT)
        raw=json.loads(blob); answer=raw['actual_answer']
        assert answer==r['actual_answer'] and sha(answer.encode())==r['answer_sha256']
        evidence=[]; context=[]
        for p in raw['prompt_evidence']:
            c=corpus[p['chunk_id']]; text=c['text']
            assert sha(text.encode())==p['text_sha256']
            if c['security_level']=='L1': canonical=rawtexts[c['sha256']]
            else: canonical=load(ROOT/c['path'])['content']
            assert canonical[p['text_start']:p['text_end']]==text
            context.append(p | {'document_id':c['document_id'],'document_version':c['document_version'],'source_path':c['path'],'security_level':c['security_level'],'company_id':c.get('company_id')})
            if p['citation'] not in spec['anchors']:continue
            needle=spec['anchors'][p['citation']];i=text.find(needle)
            assert i>=0,(qid,needle)
            start=max(0,i-100);end=min(len(text),i+len(needle)+260)
            quote=text[start:end]
            evidence.append(dict(evidence_id=f'{short}-E{p["citation"]}',scope='prompt_context',citation=p['citation'],chunk_id=c['chunk_id'],document_id=c['document_id'],document_version=c['document_version'],source_path=c['path'],company_id=c.get('company_id'),tenant_id=c.get('tenant_id'),security_level=c['security_level'],source_nature='real_notice' if c['security_level']=='L1' else 'synthetic_company',start=p['text_start']+start,end=p['text_start']+end,quote=quote,chunk_sha256=p['text_sha256'],source_fact_refs=c.get('source_fact_refs',[])))
        refs=[e['evidence_id'] for e in evidence]
        if short in SUPPLEMENTAL:
            cid,needle=SUPPLEMENTAL[short]; c=corpus[cid];text=c['text'];i=text.index(needle)
            start=max(0,i-100);end=min(len(text),i+len(needle)+200)
            canonical=rawtexts[c['sha256']] if c['security_level']=='L1' else load(ROOT/c['path'])['content']
            assert canonical[c['text_start']:c['text_end']]==text
            evidence.append(dict(evidence_id=short+'-REFERENCE',scope='reference_only_not_in_prompt',citation=None,chunk_id=cid,document_id=c['document_id'],document_version=c['document_version'],source_path=c['path'],company_id=c.get('company_id'),tenant_id=c.get('tenant_id'),security_level=c['security_level'],source_nature='real_notice' if c['security_level']=='L1' else 'synthetic_company',start=c['text_start']+start,end=c['text_start']+end,quote=text[start:end],chunk_sha256=sha(text.encode()),source_fact_refs=c.get('source_fact_refs',[])))
        spans=[];candidates=[]
        for target,label,reason in spec['spans']:
            matches=list(re.finditer(re.escape(target),answer));assert matches,(qid,target)
            for m in matches:
                spans.append(dict(start=m.start(),end=m.end(),quote=m.group(),label=label,reason=reason,evidence_ids=refs,human_decision='pending',hallucination_target=label in ['CONTRADICTION','UNSUPPORTED']))
        for target,reason in spec['candidates']:
            matches=list(re.finditer(re.escape(target),answer));assert matches,(qid,target)
            for m in matches:candidates.append(dict(start=m.start(),end=m.end(),quote=m.group(),label='UNCERTAIN',reason=reason,evidence_ids=refs,human_decision='pending',hallucination_target=False))
        spans.sort(key=lambda s:(s['start'],s['end']))
        for i,s in enumerate(spans):s['span_id']=f'{short}-S{i+1:02}'
        for i,s in enumerate(candidates):s['span_id']=f'{short}-U{i+1:02}'
        issues=list(spec['issues'])
        if raw.get('finish_reason')=='length' and '출력 잘림' not in issues:issues.append('출력 잘림')
        if r['invalid_citations']:issues.append('존재하지 않는 인용번호 '+str(r['invalid_citations']))
        rows.append(dict(question_id=qid,company_id=r['company_id'],tenant_id=raw['request']['user_context']['tenant_id'],user_context=raw['request']['user_context'],bid_key=raw['request']['bid_key'],scenario_id=raw['request'].get('scenario_id'),scenario_version=raw['request'].get('scenario_version'),split=r['split'],cohort=r['cohort'],record_path=r['record_path'],source_revision=REV,record_git_blob_sha256=sha(blob),answer_sha256=r['answer_sha256'],question=r['question'],expected_answer=r['expected_answer'],actual_answer=answer,previous_agent_review=r['agent_review'],agent_note=spec['note'],draft_spans=spans,review_candidates=candidates,quality_issues=issues,evidence=evidence,prompt_context_manifest=context,annotation_scope='Input-grounded agent draft; snippets are navigational, entire supplied context was reviewed. Additional missing source is not silently included in model input.',annotation_coverage='agent_draft_requires_second_review',offset_unit='Unicode code point; zero-based; end-exclusive; original answer including Markdown and LF',human_approval='pending',reviewer=None,approved_spans=None,training_ready=False))
    validate(rows)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'labels_draft.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    write(OUT/'selection.json',dict(source_revision=REV,question_ids=[r['question_id'] for r in rows],selection_policy='Purposeful 5/company. All 4 truncated answers and the invalid-citation answer; calculation/absence/expiry/entity/normal examples. Not prevalence sample; no new holdout.',prior_split_preserved=True,training_export_permitted=False))
    fields=['question_id','company_id','question','expected_answer','actual_answer','agent_note','quality_issues','draft_span_count','human_approval','reviewer','human_note']
    with (OUT/'review_25.tsv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fields,delimiter='\t');w.writeheader()
        for r in rows:w.writerow({k:(len(r['draft_spans']) if k=='draft_span_count' else '; '.join(r[k]) if k=='quality_issues' else r.get(k,'')) for k in fields})
    report=dict(records=25,companies=dict(collections.Counter(r['company_id'] for r in rows)),draft_spans=sum(len(r['draft_spans']) for r in rows),hallucination_candidate_spans=sum(s['hallucination_target'] for r in rows for s in r['draft_spans']),uncertain_candidates=sum(len(r['review_candidates']) for r in rows),no_positive_span_answers=sum(not any(s['hallucination_target'] for s in r['draft_spans']) for r in rows),truncated_answers=sum('출력 잘림' in r['quality_issues'] for r in rows),invalid_citation_answers=sum(bool(next(x for x in effective if x['question_id']==r['question_id'])['invalid_citations']) for r in rows),evidence_excerpts=sum(len(r['evidence']) for r in rows),checks='answer hashes, raw git blobs, exact span slices, exact source slices, context hashes, 5/company, reference IDs, company isolation, pending approval',human_approval='pending',model_runs=0)
    write(OUT/'validation_report.json',report)
    cards=[]
    for r in rows:
        marked=[];cursor=0
        for s in sorted(r['draft_spans']+r['review_candidates'],key=lambda s:s['start']):
            if s['start']<cursor:continue
            marked.append(html.escape(r['actual_answer'][cursor:s['start']]))
            marked.append('<mark class="'+s['label']+'" title="'+html.escape(s['label']+': '+s['reason'],quote=True)+'">'+html.escape(s['quote'])+'</mark>');cursor=s['end']
        marked.append(html.escape(r['actual_answer'][cursor:]))
        ev=''.join('<details><summary>'+html.escape(e['evidence_id']+' / '+e['security_level']+' / '+('생성 시 입력' if e['scope']=='prompt_context' else '추가 검수 전용: 모델이 보지 않음'))+'</summary><pre>'+html.escape(e['quote'])+'</pre><p>'+html.escape(e['source_path']+f" / [{e['start']}, {e['end']})")+'</p></details>' for e in r['evidence'])
        cards.append('<article id="'+r['question_id']+'"><h2>'+html.escape(r['question_id'])+'</h2><h3>'+html.escape(r['question'])+'</h3><p>'+html.escape(r['agent_note'])+'</p><pre>'+''.join(marked)+'</pre><details><summary>기대답 · 업무 품질 메모</summary><p>'+html.escape(r['expected_answer'])+'</p><p>'+html.escape(' / '.join(r['quality_issues']))+'</p></details>'+ev+'</article>')
    (OUT/'review.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>ASTRA 구절 라벨 초안 25개</title><style>body{font:16px/1.65 system-ui;background:#f4f6fa;color:#172235;max-width:1100px;margin:32px auto;padding:0 24px}article{background:white;padding:26px;margin:24px 0;border:1px solid #d8dfeb;border-radius:8px}h2{font-size:17px;color:#334b75}h3{font-size:21px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}mark{background:#ffe3a3}.CITATION_ERROR{background:#d7eaff}.UNCERTAIN{background:transparent;text-decoration:underline dotted #ab6c00}summary{cursor:pointer;color:#345782}details{margin:12px 0}p{overflow-wrap:anywhere}</style><h1>ASTRA 구절 라벨 초안 25개</h1><p>노란색은 환각 의심 초안, 파란색은 인용 오류, 점선은 모호한 검토 후보입니다. 마우스를 올리면 이유가 표시됩니다. 사람 승인 pending. 검수용 근거 발췌이며 RAG 입력·공개 UI로 배포하지 않습니다.</p>'+''.join(cards)+'</html>',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--source-cache',type=Path,required=True);a=p.parse_args();build(a.index,a.source_cache)
