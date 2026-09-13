"""Structural/numeric/permission checks; not a semantic truth oracle."""
import hashlib
import json
import re
from collections import Counter,defaultdict
from datetime import date
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

import build_qa300 as x
import generate_c01_documents as g
import generate_remaining_companies as r
import validate_company_master as v
import context_qa300 as context

FORBIDDEN={'expected_answer','must_not_claim','must_include','question_id','expected_status','hallucination_spans'}


def qrows(output):return [json.loads(line) for line in output['evaluation/questions_300.jsonl'].splitlines()]
def newdocs(output):return [d for k,d in output.items() if k.startswith('retrieval/') and k.endswith('.json')]
def digest_bytes(value):return hashlib.sha256(value).hexdigest()


def check_source(ref,cache=None,source_root=None):
    v.require(ref['origin']=='source_extracted','real source disguised')
    v.require(ref['bid_key']==ref['notice_id']+'-'+ref['notice_version'],'source notice version')
    v.require(ref['quote'] and ref['sha256'],'source metadata')
    if ref['text_start'] is not None:
        v.require(ref['text_sha256'],'source canonical hash missing')
        v.require(ref['text_end']-ref['text_start']==len(ref['quote']),'source offset length')
        if cache is not None:
            d=next((d for d in cache if d['bid']==ref['bid_key'] and d['name']==ref['filename']),None)
            if d is None and ref['filename']=='공고정보.json' and source_root:
                d={'text':(Path(source_root)/ref['relative_source_path']).read_text(encoding='utf-8-sig')}
            v.require(d is not None,'source cache document missing')
            v.require(digest_bytes(d['text'].encode())==ref['text_sha256'],'source canonical hash')
            v.require(d['text'][ref['text_start']:ref['text_end']]==ref['quote'],'source offset quote')
    else:v.require(ref['page'] is not None and ref['page_basis'],'manual PDF location')
    if source_root:
        root=Path(source_root).resolve();p=(root/ref['relative_source_path'].replace('\\','/')).resolve()
        v.require(p.is_relative_to(root),'source path traversal')
        v.require(digest_bytes(p.read_bytes())==ref['sha256'],'source binary hash')


def check_plan(p,b):
    c,base=r.company(b,p['company_id']);v.require(p['tenant_id']==c['tenant_id'],'scenario tenant')
    v.require(p['baseline_master_sha256']==g.digest(b['master']),'baseline altered')
    change=p['state_change'];v.require(change['origin']=='synthetic_setting' and p['synthetic'],'synthetic state masquerade')
    baseline=c['known_absences'][0]['state'] if p['company_id']=='C01' else 'expired_'+c['certifications'][-1]['valid_until'] if p['company_id']=='C02' else c['certifications'][-1]['evidence_state'] if p['company_id']=='C04' else c['projects'][1]['evidence_state']
    v.require(change['baseline']==baseline,'baseline missing/expired state changed')
    date.fromisoformat(change['effective_from'])
    if change['effective_until']:v.require(change['effective_from']<=change['effective_until'],'certification interval')
    v.require(context.state_at(p,'2026-03-01')==change['baseline'],'retroactive state')
    if p['company_id']=='C02':v.require(context.state_at(p,'2026-04-01')=='expired_2026-03-31','expired certificate made valid')
    if p['company_id']=='C04':v.require(change['holder_type']=='service','CSAP holder')
    for person in c['personnel']:
        v.validate_capacity(person,[a for a in p['staffing'] if a['person_id']==person['person_id']])
    v.unique([a['person_id'] for a in p['staffing']],'duplicate staffing person')
    v.require(all(a['person_id'] in {n['person_id'] for n in c['personnel']} for a in p['staffing']),'foreign person')
    calc=p['calculation'];v.require(calc['vat_rate']['value']==10 and calc['vat_basis']=='exclusive','VAT basis')
    external=0
    for price in p['prices']:
        v.require(price['price_origin']=='synthetic_setting' and price['actual_supplier_quote_state']=='missing','synthetic price masquerade')
        v.require(price['quantity']['value']>0 and price['unit_net']['value']>0,'unknown cost zero')
        v.require(price['net']['value']==price['quantity']['value']*price['unit_net']['value'],'price multiplication')
        external+=price['net']['value']
    v.require(external==calc['synthetic_external_net'],'external cost sum')
    # Recompute labor using calendar month fractions and master rates, not generator output equality.
    labor=Decimal(0)
    for a in p['staffing']:
        person=next(n for n in c['personnel'] if n['person_id']==a['person_id'])
        rate=next(t for t in c['l3_policy']['labor_rates'] if t['role']==person['role'])
        fractions=sum(Decimal(t['days'])/Decimal(t['denominator']) for t in r.months(a['start'],a['end']))
        labor+=fractions*Decimal(str(a['allocation_fte']['value']))*Decimal(rate['monthly_base']['value'])*(1+Decimal(rate['employer_burden']['value'])/100)
    direct0=r.money(labor+Decimal(p['cost_basis']['other_direct_net']['value']))
    v.require(direct0==calc['scoped_direct_net'],'staff labor cost inconsistent')
    public=calc['original_agreement_gross'];v.require(public==(56320240 if p['company_id']=='C02' else None),'public agreement amount')
    direct=Decimal(direct0)+Decimal(external)+(Decimal(public)/Decimal('1.1') if public else 0)
    policy=c['l3_policy']
    for a,z in [('overhead_percent','overhead'),('contingency_percent','contingency'),('margin_percent','target_gross_margin')]:
        v.require(calc[a]==policy[z]['value'],'master cost policy changed')
    cost=direct*(1+Decimal(calc['overhead_percent'])/100+Decimal(calc['contingency_percent'])/100)
    target=cost/(1-Decimal(calc['margin_percent'])/100)
    v.require((calc['assumed_cost_net'],calc['target_net'],calc['target_gross'])==(r.money(cost),r.money(target),r.money(target*Decimal('1.1'))),'margin/VAT/rounding')
    v.require(p['actual_bid_price'] is None and p['actual_supplier_quote_state']=='missing','exercise made actual bid')


def check_docs(docs,plans,b):
    bundle={'scenarios':plans}
    for d in docs:
        cid=d['company_id'];c,base=r.company(b,cid)
        p=next(p for p in plans if p['scenario_id']==d['scenario_id'])
        v.require(d['tenant_id']==c['tenant_id'] and p['company_id']==cid,'doc foreign tenant')
        v.require(d['document_version']==x.VERSION and d['scenario_version']==p['version'],'doc version')
        v.require(d['security_level']==('L3' if '-COST-' in d['document_id'] else 'L2'),'doc level')
        v.require(d['allowed_roles']==(['cost_analyst','bid_approver'] if d['security_level']=='L3' else ['bid_analyst','cost_analyst','bid_approver']),'role boundary')
        v.require(d['human_approval']=='pending' and not d['rag_ingest'] and d['index_status']=='not_indexed','approval/ingestion state')
        for ptr,obj in v.walk(d):
            if isinstance(obj,dict):v.require(not (FORBIDDEN & obj.keys()),'evaluation fields in retrieval')
        for key in FORBIDDEN:v.require(key not in d['content'],'evaluation field in text')
        v.unique([ch['chunk_id'] for ch in d['chunks']],'chunk IDs')
        for ch in d['chunks']:
            for k in ('document_id','document_version','tenant_id','security_level','allowed_roles'):v.require(ch[k]==d[k],'chunk metadata')
            v.require(d['content'][ch['text_start']:ch['text_end']]==ch['text'],'chunk offset')
            v.require(ch['offset_unit']==g.OFFSET and 0<len(ch['text'])<=5000,'chunk offset unit/size')
            for f in ch['source_fact_refs']:
                v.pointer(b['master'],f['master_pointer'])
                v.require(f['master_pointer'].startswith(base+'/') and f['evidence_id'] in c['evidence_ids'],'master pointer/tenant')
                v.require(d['security_level']=='L3' or '/l3_policy' not in f['master_pointer'],'L3 pointer in L2')
            ref=ch['scenario_fact_ref'];v.require(ref['scenario_id']==p['scenario_id'] and ref['scenario_version']==p['version'],'chunk scenario')
            v.require(ref['pointer'].startswith('/scenarios/'+str(plans.index(p))+'/'),'foreign scenario pointer')
            value=v.pointer(bundle,ref['pointer'])
            field=ref['pointer'].split('/')[3]
            v.require(d['security_level']=='L3' or field not in ('prices','calculation','cost_basis','labor_lines','other_direct_net'),'L3 scenario ref in L2')
            # The renderer must contain the selected atom, preventing an altered unknown value.
            title=ch['text'].splitlines()[0].removeprefix('## ')
            rendered=g.render_block(title,{field:value},d['security_level'],p['effective_as_of'],c)
            v.require(ch['text']==rendered,'scenario body value mismatch')


def check_questions(qs,docs,b,cache=None,source_root=None,full=True):
    if full:
        v.require(len(qs)==300,'question count')
        v.require(Counter(q['company_id'] for q in qs)=={c:60 for c in x.IDS},'company distribution')
        v.require({q['bid_key'] for q in qs}=={row['공고번호'] for row in x.rows()},'notice coverage')
        v.require(sum(q['reuse_of'] is not None for q in qs)==25,'pilot accounting')
    v.unique([q['question_id'] for q in qs],'question IDs');v.unique([x.norm(q['question']) for q in qs],'duplicate question wording')
    catalog={d['document_id']:d for d in docs};catalog.update({k:entry['doc'] for k,entry in x.documents().items()})
    bid_splits=defaultdict(set);scenario_splits=defaultdict(set);sources={};link_count=0
    for q in qs:
        v.require(q['dataset_version']==x.VERSION and q['notice_id']+'-'+q['notice_version']==q['bid_key'],'question version')
        v.require(q['tenant_id']=='astra-'+q['company_id'].lower(),'question company tenant')
        v.require(q['expected_answer'] and q['question'] and q['must_include'],'empty answer')
        v.require(q['actual_answer'] is None and q['hallucination_spans'] is None and not q['rag_ingest'] and q['review']['human']=='pending','false completion')
        date.fromisoformat(q['decision_as_of']);bid_splits[q['bid_key']].add(q['split']);scenario_splits[q['scenario_id']].add(q['split'])
        for e in q['public_notice_evidence']:
            v.require(e['bid_key']==q['bid_key'],'foreign notice')
            if e['source_id'] in sources:v.require(sources[e['source_id']]==e,'conflicting source ID')
            sources[e['source_id']]=e
        for group in ('company_evidence','private_audit_evidence'):
            for e in q[group]:
                d=catalog[e['document_id']];ch=next(c for c in d['chunks'] if c['chunk_id']==e['chunk_id'])
                for k in ('document_version','tenant_id','security_level','allowed_roles'):v.require(e[k]==d[k],'evidence metadata')
                v.require(e['quote']==ch['text'] and e['text_start']==ch['text_start'] and e['text_end']==ch['text_end'],'evidence quotation/offset')
                v.require(e['company_id']==q['company_id'],'foreign company evidence')
                if group=='company_evidence':
                    v.require(v.can_access(q['user_context'],d) and d['security_level'] in q['user_context']['allowed_security_levels'],'unauthorized answer evidence')
                    v.require(d.get('scenario_id') in (None,q['scenario_id']),'wrong scenario evidence')
                    if d.get('scenario_version'):v.require(d['scenario_version']==q['scenario_version'],'wrong scenario version')
                else:v.require(not v.can_access(q['user_context'],d),'denial case actually allowed')
                link_count+=1
        if q['expected_action']=='접근 거절':
            v.require(not q['company_evidence'] and not q['public_notice_evidence'] and q['private_audit_evidence'],'denial evidence leakage')
            v.require(not re.search(r'\d[\d,]*\s*원|SYN-EV-|FTE|KRW',q['expected_answer']),'denial answer leakage')
        else:v.require(q['public_notice_evidence'] or q['company_evidence'],'missing evidence')
        for ptr in q['master_pointers']:
            v.pointer(b['master'],ptr);v.require(ptr.startswith('/companies/'+str(x.IDS.index(q['company_id']))+'/'),'foreign question pointer')
    v.require(all(len(s)==1 for s in bid_splits.values()) and all(len(s)==1 for s in scenario_splits.values()),'split leakage')
    for ref in sources.values():check_source(ref,cache,source_root)
    return dict(unique_notice_excerpts=len(sources),company_chunk_links=link_count)


def validate(output,source_cache=None,source_root=None):
    b=v.load_bundle();v.validate_master(b['master'],b['schema'])
    qs=qrows(output);docs=newdocs(output);plans=output['scenarios/scenario_extensions.json']['scenarios']
    for q in qs:v.schema_check(q,output['schemas/question.schema.json'])
    for d in docs:v.schema_check(d,output['schemas/generated_document.schema.json'])
    for p in plans:check_plan(p,b)
    check_docs(docs,plans,b)
    # A small independently checked mixed bundle precedes full validation.
    sample=[q for cid in x.IDS for q in [a for a in qs if a['company_id']==cid and ('-P01' in a['question_id'] or '-S0' in a['question_id'])]]
    check_questions(sample,docs,b,full=False)
    cache=x.read(source_cache) if source_cache else None
    links=check_questions(qs,docs,b,cache,source_root)
    for q in qs:
        if q['calculation'] is not None:
            p=next(p for p in plans if p['scenario_id']==q['scenario_id'])
            v.require(q['calculation']==p['calculation'],'question calculation differs from scenario')
        for ptr in q['scenario_pointers']:v.pointer({'scenarios':plans},ptr)
        if '-S0' in q['question_id']:
            p=next(p for p in plans if p['scenario_id']==q['scenario_id'])
            v.require(q['scenario_version']==p['version'],'scenario question version')
    for relative,sha in output['validation/baseline_hashes.json'].items():v.require(digest_bytes((x.REPO/relative).read_bytes())==sha,'baseline regression')
    g.write_or_check(b,g.DEFAULT_OUT,True)
    # Exact re-render protects free text generated from scenario data; it does not prove arbitrary prose truthful.
    v.require(docs==x.supplement_docs(b,plans),'document reproducibility')
    return dict(status='passed',version=x.VERSION,questions=len(qs),sample_questions=len(sample),
      companies=dict(Counter(q['company_id'] for q in qs)),notices=len({q['bid_key'] for q in qs}),
      new_documents=len(docs),new_chunks=sum(len(d['chunks']) for d in docs),**links,
      source_checks=dict(canonical_offsets='passed' if cache else 'not_run_without_local_cache',binary_hashes='passed' if source_root else 'not_run_without_local_sources'),
      baseline_regression='v1/r1 hashes and C01 byte regeneration passed',human_approval='pending',actual_answers=0,span_labels=0,
      limitations=['문자열·참조 검사는 의미적 정답 보증이나 RAG 성능 평가가 아니다.','기존 수동 PDF 3개 인용은 원래 페이지 대조 상태를 보존; 자동 문자 offset 검사 대상 아님.',
        '자유서술 신규 질문의 동일 의미 중복·표 해석·법적 조건은 사람 검수 필요.'])
