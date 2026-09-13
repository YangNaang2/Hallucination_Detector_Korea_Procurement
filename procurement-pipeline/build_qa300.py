"""Versioned offline RAG evaluation authoring; originals never enter git."""
import argparse
import copy
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import generate_c01_documents as g
import generate_remaining_companies as r
import validate_company_master as v

REPO=Path(__file__).resolve().parent.parent
ROOT=REPO/'project-docs/평가데이터/v2'
VERSION='2.0.0'
SHEET=REPO/'project-docs/표본_정보시스템/검수/요건추출시트_51건_통합.csv'
IDS=('C01','C02','C03','C04','C05')
SPECIFICATION=json.loads((ROOT/'evaluation/authoring/question_specs.json').read_text(encoding='utf-8'))
CASES=SPECIFICATION['cases']
EXTRA_ANCHORS={(r['notice_index'],r['case_index']):r['anchors'] for r in SPECIFICATION['extra_anchors']}

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(g.encoded(value).encode('utf-8'))
def rows():
    with SHEET.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))
def norm(t):return re.sub(r'\s+','',t).lower()
def grams(t):
    s=norm(t);return {s[i:i+3] for i in range(max(0,len(s)-2))}

def original_excerpt(d,start,end,sid):
    return dict(source_id=sid,bid_key=d['bid'],notice_id=d['bid'][:-4],notice_version=d['bid'][-3:],
      filename=d['name'],relative_source_path=d['relative'],sha256=d['sha256'],
      extraction_method=d['method'],text_sha256=hashlib.sha256(d['text'].encode()).hexdigest(),
      section='검색 앵커 주변 원문 구간; 정확한 위치는 문자 offset',page=None,page_basis='미확인; 추출 정본 offset 사용',
      text_start=start,text_end=end,offset_unit=g.OFFSET,quote=d['text'][start:end],origin='source_extracted',
      review_status='agent_review_required',limitation='해당 인용 구간의 근거 확인이며 첨부 전체·법령·정정 우선순위 검증이 아니다.')

def capture(cache,source_root):
    originals=read(cache); notices=rows(); bank=[];missing=[]
    for i,specs in enumerate(CASES):
        bid=notices[i]['공고번호'];group=[d for d in originals if d['bid']==bid and d.get('text')]
        for j,(anchor,question,answer,kind) in enumerate(specs):
            candidates=[];target=grams(answer+' '+question)
            for d in group:
                # Whitespace-insensitive anchor matching with offsets back to the canonical extraction.
                indices=[n for n,ch in enumerate(d['text']) if not ch.isspace()]
                compact=''.join(d['text'][n].lower() for n in indices);key=norm(anchor)
                offset=0
                while True:
                    found=compact.find(key,offset)
                    if found<0:break
                    a=indices[found];z=indices[found+len(key)-1]+1
                    start=max(0,a-170);end=min(len(d['text']),z+600)
                    # Preserve contiguous text; avoid chopping the final nearby line when possible.
                    line=d['text'].find('\n',end,min(len(d['text']),end+140))
                    if line>=0:end=line
                    quote=d['text'][start:end]
                    score=len(target & grams(quote))
                    candidates.append((score,d,start,end));offset=found+len(key)
            if not candidates:
                missing.append(dict(i=i,j=j,bid=bid,anchor=anchor));continue
            candidates.sort(key=lambda x:-x[0]);_,d,start,end=candidates[0]
            v.require(hashlib.sha256((source_root/d['relative']).read_bytes()).hexdigest()==d['sha256'],'source file drift')
            extras=[]
            for k,extra_anchor in enumerate(EXTRA_ANCHORS.get((i,j),[])):
                extra=[]
                for other in group:
                    idx=[n for n,ch in enumerate(other['text']) if not ch.isspace()];t=''.join(other['text'][n].lower() for n in idx)
                    at=t.find(norm(extra_anchor))
                    if at>=0:
                        a=max(0,idx[at]-190);z=min(len(other['text']),idx[at+len(norm(extra_anchor))-1]+701)
                        extra.append((len(target & grams(other['text'][a:z])),other,a,z))
                if not extra:missing.append(dict(i=i,j=j,extra_anchor=extra_anchor));continue
                _,other,a,z=max(extra,key=lambda e:e[0]);extras.append(original_excerpt(other,a,z,f'N{i+1:02}-E{j+1}-X{k+1}'))
            if (i,j) in ((12,0),(40,0),(47,0)):
                relative=Path(d['relative'].replace('\\','/')).parent.parent/'공고정보.json';mp=source_root/relative
                mt=mp.read_text(encoding='utf-8-sig');key='budget_krw' if i==40 else 'deadline';a=mt.index('"'+key+'"');z=mt.find('\n',a)
                md=dict(bid=bid,name='공고정보.json',relative=str(relative).replace('\\','/'),sha256=hashlib.sha256(mp.read_bytes()).hexdigest(),text=mt,method='collected metadata JSON UTF-8-sig')
                ref=original_excerpt(md,a,z,f'N{i+1:02}-E{j+1}-META');ref['section']='수집 메타데이터 /'+key;ref['limitation']='수집 시점 메타데이터이며 발주기관 정정공고 자체가 아님.';extras.append(ref)
            bank.append(dict(notice_index=i,case_index=j,anchor=anchor,question=question,expected_answer=answer,category=kind,
              evidence=original_excerpt(d,start,end,f'N{i+1:02}-E{j+1}'),additional_evidence=extras))
            if (i,j) in ((2,1),(2,2),(23,2)):
                page={(2,1):11,(2,2):7,(23,2):7}[(i,j)]
                bank[-1]['evidence'].update(page=page,page_basis='PDF 뷰어 1-based 페이지; pypdfium2 렌더링 후 에이전트 육안 확인',review_status='rendered_section_checked')
    write(ROOT/'evaluation/authoring/notice_cases.json',dict(version=VERSION,sheet_sha256=hashlib.sha256(SHEET.read_bytes()).hexdigest(),cases=bank))
    print(json.dumps(dict(captured=len(bank),missing=missing),ensure_ascii=False,indent=2))


def documents():
    result={}
    for folder in [g.DEFAULT_OUT,r.ROOT]:
        for path in folder.rglob('*.json'):
            if path.parent.name not in ('L2','L3'):continue
            d=read(path)
            if 'document_id' in d and 'chunks' in d:
                result[d['document_id']]=dict(path=str(path.relative_to(REPO)).replace('\\','/'),doc=d)
    return result


def doc_evidence(d,ch,path):
    return dict(document_id=d['document_id'],document_version=d['document_version'],document_path=path,
      chunk_id=ch['chunk_id'],company_id=d['company_id'],tenant_id=d['tenant_id'],security_level=d['security_level'],
      allowed_roles=d['allowed_roles'],scenario_id=d.get('scenario_id'),scenario_version=d.get('scenario_version'),
      text_start=ch['text_start'],text_end=ch['text_end'],offset_unit=g.OFFSET,quote=ch['text'],
      master_fact_refs=ch.get('source_fact_refs',[]),scenario_fact_ref=ch.get('scenario_fact_ref'))


def matching_docs(catalog,cid,pointers,allow_scenario=None):
    out=[]
    for entry in catalog.values():
        d=entry['doc']
        if d['company_id']!=cid or d.get('scenario_id') not in (None,allow_scenario):continue
        for ch in d['chunks']:
            if any(f['master_pointer']==p or p.startswith(f['master_pointer']+'/') or f['master_pointer'].startswith(p+'/') for f in ch['source_fact_refs'] for p in pointers):
                out.append(doc_evidence(d,ch,entry['path']))
    return out


def base_question(qid,cid,bid,scenario,category,question,answer,public,company_evidence,role='bid_analyst'):
    levels=['L1','L2'] if role=='bid_analyst' else ['L1','L2','L3']
    action='조건부 답변' if category in ('boundary','multi_document','conflict') else '답변'
    return dict(question_id=qid,dataset_version=VERSION,company_id=cid,tenant_id='astra-'+cid.lower(),
      user_context=dict(tenant_id='astra-'+cid.lower(),role=role,authenticated=True,membership_active=True,allowed_security_levels=levels),
      bid_key=bid,notice_id=bid[:-4],notice_version=bid[-3:],scenario_id=scenario,scenario_version=VERSION,
      decision_as_of='2026-04-01',category=category,difficulty='medium' if category not in ('fact','multi_document','conflict') else 'easy' if category=='fact' else 'hard',
      question=question,expected_answer=answer,reasoning='제시된 근거의 적용 범위 안에서만 답한다. 개별 조건과 전체 적격을 구분한다.',
      expected_action=action,expected_status='scoped_answer',expected_overall_eligibility=None,
      evidence_kinds=['actual_notice']+(['synthetic_company_fact'] if company_evidence else []),
      public_notice_evidence=public,company_evidence=company_evidence,private_audit_evidence=[],
      master_pointers=sorted({f['master_pointer'] for e in company_evidence for f in e['master_fact_refs']}),
      synthetic_evidence_ids=sorted({f['evidence_id'] for e in company_evidence for f in e['master_fact_refs']}),
      scenario_pointers=[],calculation=None,must_include=[answer],
      must_not_claim=['전체 입찰 적격 확정','합성 증빙의 실제 기관 발급','미확인 금액 0원','원문에 없는 조건 확정'],
      assumptions=[],unresolved_issues=[],review=dict(automated='pending',agent_content='pending',human='pending'),
      actual_answer=None,hallucination_spans=None,rag_ingest=False,split=None,reuse_of=None)


def pilot_questions(b,catalog):
    old=g.bindings(b,[x['doc'] for x in catalog.values() if x['doc']['company_id']=='C01' and x['doc'].get('scenario_id') is None])
    newer=read(r.ROOT/'evaluation/qa_pilot_20.json')['questions'];out=[]
    categories=['boundary','performance','certification','eligibility','conflict']
    for n,(q,linked) in enumerate(zip(b['qa']['questions'],old['questions'])):
        ce=matching_docs(catalog,'C01',q['evidence']['master_pointers'])
        row=base_question(f'ASTRA-300-C01-P{n+1:02}','C01',q['bid_key'],q['scenario_id'],categories[n],q['question'],q['expected_answer'],linked['public_notice_evidence'],ce)
        row.update(reuse_of=q['question_id'],scenario_version='1.0.0',expected_status=q['expected_status'])
        out.append(row)
    for n,q in enumerate(newer):
        ce=[]
        for e in q['generated_company_evidence']:
            entry=catalog[e['document_id']];d=entry['doc'];ch=next(x for x in d['chunks'] if x['chunk_id']==e['chunk_id'])
            ce.append(doc_evidence(d,ch,entry['path']))
        kind={'condition_only':'eligibility','different_certificates':'certification','not_met':'certification','capacity_only':'personnel',
          'missing_quote':'cost','missing_evidence':'performance','insufficient_evidence':'personnel','holder_boundary':'certification',
          'missing_authority':'certification','requirement_scope':'conflict','date_basis':'boundary','incomplete_scope':'cost',
          'separate_requirements':'eligibility','eligibility_not_score':'performance','direct_execution':'contract','unknown_not_zero':'cost'}[q['expected_status']]
        row=base_question(f'ASTRA-300-{q["company_id"]}-P{n%5+1:02}',q['company_id'],q['bid_key'],q['scenario_id'],kind,
          q['question'],q['expected_answer'],q['public_notice_evidence'],ce,q['required_role'])
        row.update(reuse_of=q['question_id'],scenario_version='1.0.0-r1',expected_status=q['expected_status'])
        out.append(row)
    return out


def supplements(b):
    """Synthetic scenario records, never a patch to the shared v1 master."""
    baselines=r.inputs(b)['scenarios'];out=[]
    state={
      'C01':dict(kind='hypothetical_registration',subject='C01',code='0036',baseline='not_held',
        assumed_state='synthetic_record',effective_from='2026-04-01',effective_until='2026-12-31',
        note='정보통신공사업 등록을 보유한다고 가정한 분기. 실제 등록 또는 기존 마스터 변경 아님.'),
      'C02':dict(kind='hypothetical_renewal',subject='C02-CERT-03',code='8111159901',baseline='expired_2026-03-31',
        assumed_state='synthetic_record',effective_from='2026-04-02',effective_until='2027-04-01',
        note='개발 직접생산의 가상 갱신 분기. 4월 1일 기준 기존 만료 상태는 유지.'),
      'C03':dict(kind='hypothetical_evidence',subject='C03-PRJ-02',code=None,baseline='missing',
        assumed_state='synthetic_record',effective_from='2026-05-20',effective_until=None,
        note='기존 가상 고객의 실적 증빙 레코드를 확보한 것으로 가정. 실제 기관 발급 증명서 아님.'),
      'C04':dict(kind='hypothetical_service_authorization',subject='C04-SERVICE-01',code='CSAP',baseline='missing',
        assumed_state='synthetic_record',effective_from='2026-05-20',effective_until='2027-05-19',
        holder_type='service',provider='가상 하늘인프라 제공자',supply_agreement_state='synthetic_record',
        note='해당 가상 서비스의 인증과 공급계약을 가정. 회사 ISO 인증으로 대체하거나 실제 공급자 인증을 차용하지 않음.'),
      'C05':dict(kind='hypothetical_evidence',subject='C05-PRJ-02',code=None,baseline='missing',
        assumed_state='synthetic_record',effective_from='2026-05-20',effective_until=None,
        note='가상 PMS 실적 증빙 레코드의 확보 가정이며 실적 금액·날짜·고객은 바꾸지 않음.')}
    # Unit costs are engineering exercise assumptions, not market observations or issued quotes.
    price_rows={
      'C01':[('운영 SW 지원',1,4500000),('시험·백업 환경',1,1800000)],
      'C02':[('부품 예비 공급 범위',1,3000000),('부품 운송·보관비 — 방문 인건비 제외',1,1200000)],
      'C03':[('개발·시험 라이선스',1,1800000),('추가 보안 점검 도구',1,2400000)],
      'C04':[('가상 서버·OS 월 사용 묶음',7,2200000),('NAS·디스크·백업 월 묶음',7,1900000),
             ('트래픽·네트워크 월 묶음',7,800000),('보안·DB·시각화 솔루션 월 묶음',7,1700000)],
      'C05':[('규격 대응 PC 본체',2,3200000),('27인치 모니터',2,300000),('Office 2024 사용권',2,400000),
             ('서버랙',1,900000),('UPS',1,1200000),('24포트 POE 스위치',1,650000),
             ('컨트롤러·통신·IO·함체 게이트웨이 세트',3,4800000),('EMS 상용SW·OS 추가 사용권 묶음',1,3500000)]}
    for cid in IDS:
        c,base=r.company(b,cid);sid=f'SC-QA300-{cid}-A';bid='R26BK01487327-000' if cid=='C01' else r.BIDS[cid]
        if cid=='C01':
            staffing=[dict(person_id='C01-P-03',start='2026-05-16',end='2026-12-17',allocation_fte=r.qty(.5,'FTE'))]
            plan=dict(staffing=staffing,other_direct_assumption=dict(quantity=r.qty(8,'visits'),unit_net=r.qty(150000,'KRW/visit')))
            costs=r.calculate(c,plan)
        else:
            plan=copy.deepcopy(next(p for p in baselines if p['company_id']==cid));costs=r.calculate(c,plan)
        prices=[dict(item_id=f'{cid}-SYN-PRICE-{i+1:02}',label=label,quantity=r.qty(q,'months' if cid=='C04' else 'units'),unit_net=r.qty(unit,'KRW/month' if cid=='C04' else 'KRW/unit'),
          net=r.qty(q*unit,'KRW','calculated','quantity * unit_net'),currency='KRW',vat_basis='exclusive',
          price_origin='synthetic_setting',actual_supplier_quote_state='missing',
          assumption_reason='가용 인력의 내부 연습 원가에 외부비용을 더하기 위한 설계값. 시장 조사 가격·실제 견적이 아니며 규격 검증 미완료.')
          for i,(label,q,unit) in enumerate(price_rows[cid])]
        for price in prices:
            price['application_period']=dict(start=min(a['start'] for a in plan['staffing']),end=max(a['end'] for a in plan['staffing']),
              origin='synthetic_setting',region='대한민국 내부 연습용',condition='이 시나리오 과업 범위에만 적용. 실제 구매/공급 가능 여부는 미확정.')
        external=sum(x['net']['value'] for x in prices)
        reference_gross=56320240 if cid=='C02' else None
        external_raw=Decimal(external)+(Decimal(reference_gross)/Decimal('1.1') if reference_gross else 0)
        # Prior rounded scope is intentionally used as the documented input for this new scenario.
        direct=Decimal(costs['scoped_direct_net']['value'])+external_raw
        policy=c['l3_policy'];cost=direct*(1+Decimal(policy['overhead']['value'])/100+Decimal(policy['contingency']['value'])/100)
        target=cost/(1-Decimal(policy['target_gross_margin']['value'])/100)
        out.append(dict(scenario_id=sid,version=VERSION,company_id=cid,tenant_id=c['tenant_id'],bid_key=bid,
          effective_as_of='2026-06-01',baseline_master_version='1.0.0',baseline_master_sha256=g.digest(b['master']),
          synthetic=True,rag_ingest=False,committed_execution=False,mutually_exclusive_group=f'{cid}-QA300-ALTERNATIVES',
          state_change=dict(evidence_id=f'SYN-QA300-{cid}-STATE',origin='synthetic_setting',**state[cid]),
          staffing=plan['staffing'],source_period_policy='시작일은 합성 계획 가정일 수 있음. 실제 착수일·입찰일 확정 아님.',
          prices=prices,cost_basis=costs,labor_lines=costs['labor_lines'],other_direct_net=costs['other_direct_net'],
          calculation=dict(origin='calculated',currency='KRW',vat_basis='exclusive',vat_rate=r.qty(10,'percent'),
            scoped_direct_net=costs['scoped_direct_net']['value'],synthetic_external_net=external,
            original_agreement_gross=reference_gross,public_agreement_origin='calculated' if reference_gross else None,
            original_agreement_inputs=[dict(value=32628780,unit='KRW',vat_basis='inclusive',origin='source_extracted',source_id='A-BS-AGREEMENT-1'),
              dict(value=23691460,unit='KRW',vat_basis='inclusive',origin='source_extracted',source_id='A-BS-AGREEMENT-2')] if reference_gross else [],
            overhead_percent=policy['overhead']['value'],contingency_percent=policy['contingency']['value'],margin_percent=policy['target_gross_margin']['value'],
            assumed_cost_net=r.money(cost),target_net=r.money(target),target_gross=r.money(target*Decimal('1.1')),
            formula='direct = prior rounded scoped direct + synthetic external + (public agreement gross / 1.1 if supplied); cost = direct*(1+overhead/100+contingency/100); target_net = cost/(1-margin/100); target_gross = unrounded target_net*1.1; final KRW HALF_UP'),
          actual_bid_price=None,actual_supplier_quote_state='missing',
          limitation='전체 과업과 제품의 적합성 검증 전 내부 연습 계산. 실제 제출 가능·시장 적정성·낙찰 가능성은 미확정.',
          changes=['기존 사실 보존','별도 상태·가격 가정 추가','새 상태 적용일 이전에 소급 적용 금지'],human_approval='pending'))
    return out


def supplement_docs(b,plans):
    docs=[]
    for p in plans:
        cid=p['company_id'];c,base=r.company(b,cid)
        for suffix,level,roles,payload in [
          ('STATE','L2',['bid_analyst','cost_analyst','bid_approver'],dict(state_change=p['state_change'],effective_as_of=p['effective_as_of'],
            baseline_master_version=p['baseline_master_version'],scenario_id=p['scenario_id'])),
          ('PLAN','L2',['bid_analyst','cost_analyst','bid_approver'],dict(staffing=p['staffing'],source_period_policy=p['source_period_policy'],
            committed_execution=False,scenario_id=p['scenario_id'])),
          ('COST','L3',['cost_analyst','bid_approver'],dict(prices=p['prices'],labor_lines=p['labor_lines'],other_direct_net=p['other_direct_net'],calculation=p['calculation'],
            actual_supplier_quote_state='missing',actual_bid_price=None,limitation=p['limitation']))]:
            did=f'{cid}-QA300-{suffix}-{VERSION}';content=f'# {c["company_name"]} 합성 시나리오 {suffix}\n\n합성 내부 검토 자료. 실제 기관 발급 증명서·견적서가 아니다. {p["scenario_id"]} / {VERSION}\n\n'
            blocks=[(key,{key:value}) for key,value in payload.items()]
            chunks=[]
            for n,(key,value) in enumerate(blocks):
                # Prices/staff are kept per entity; no company-wide master is chunked.
                atoms=[(f'{key}-{i+1}',{key:x}) for i,x in enumerate(value[key])] if isinstance(value[key],list) else [(key,value)]
                for name,atom in atoms:
                    text=g.render_block(name,atom,level,p['effective_as_of'],c);start=len(content);content+=text+'\n'
                    state_field={'C01':'known_absences','C02':'certifications','C03':'projects','C04':'services','C05':'projects'}[cid]
                    ptr=base+'/l3_policy' if level=='L3' else base+'/personnel' if suffix=='PLAN' else base+'/'+state_field
                    eids=g.evidence_ids(v.pointer(b['master'],ptr));ev=(eids or [c['headquarters']['evidence_id']])[0]
                    if cid=='C04' and suffix=='STATE':ev='SYN-EV-C04-CERT-04'
                    chunks.append(dict(chunk_id=f'{did}-CH-{len(chunks)+1:03}',document_id=did,document_version=VERSION,
                      tenant_id=c['tenant_id'],security_level=level,allowed_roles=roles,text=text,text_start=start,text_end=start+len(text),offset_unit=g.OFFSET,
                      source_fact_refs=[dict(master_pointer=ptr,evidence_id=ev)],scenario_fact_ref=dict(scenario_id=p['scenario_id'],scenario_version=VERSION,
                        pointer=f'/scenarios/{IDS.index(cid)}/{key}'+('/'+str(atoms.index((name,atom))) if isinstance(value[key],list) else ''))))
            docs.append(dict(schema_version=VERSION,document_id=did,document_version=VERSION,company_id=cid,tenant_id=c['tenant_id'],
              security_level=level,allowed_roles=roles,master_dataset_id=b['master']['dataset_id'],master_version='1.0.0',
              scenario_id=p['scenario_id'],scenario_version=VERSION,notice_id=p['bid_key'][:-4],notice_version=p['bid_key'][-3:],
              synthetic=True,review_status='unreviewed',rag_ingest=False,index_status='not_indexed',human_approval='pending',
              content=content.removesuffix('\n'),chunks=chunks))
    return docs


def scenario_questions(b,plans,docs,catalog,sources):
    out=[]
    addenda=read(r.ROOT/'inputs/source_addenda.json')['references']
    all_sources=b['sources']['references']+addenda
    for p in plans:
        cid=p['company_id'];dmap={d['document_id'].split('-')[2]:d for d in docs if d['company_id']==cid}
        def ev(suffix):
            d=dmap[suffix];path=f'project-docs/평가데이터/v2/retrieval/{cid}/{d["security_level"]}/{d["document_id"]}.json'
            return [doc_evidence(d,ch,path) for ch in d['chunks']]
        state=p['state_change'];wanted={'C01':['S-WB-0036','S-WB-YEAR'],'C02':['S-BS-DIRECT','S-BS-STAFF'],
          'C03':['A-IC-PROOF'],'C04':['S-CL-CSAP','S-CL-ISMS'],'C05':['S-EN-EXP','A-EN-DIRECT']}[cid]
        public=[s for s in all_sources if s['source_id'] in wanted]
        state_questions={
          'C01':('SC-QA300-C01-A의 0036 가정이 기존 한빛IT 원장에도 적용되는가?','아니다. 새 분기에서만 0036 보유를 합성 가정했다. 원래 회사의 not_held는 보존되며 전체 참가자격 충족은 미확정이다.'),
          'C02':('4월 2일 갱신 가정을 4월 1일의 개발 직접생산 인증 유효 판단에 소급할 수 있는가?','아니다. 합성 갱신은 2026-04-02부터이며 2026-04-01에는 기존 2026-03-31 만료 상태다.'),
          'C03':('새 인우 시나리오의 두 번째 블록체인 증빙은 실제 고객 발급 문서인가?','아니다. C03-PRJ-02에 대한 합성 증빙 확보 가정이다. 기존 missing과 실적 금액·수행일은 바꾸지 않았다.'),
          'C04':('누리의 가상 공급권한과 CSAP를 어떤 보유 주체·버전으로 조회해야 하는가?','SC-QA300-C04-A의 C04-SERVICE-01 서비스 기준으로 조회한다. 회사 ISO와 별개이며 실제 서비스 인증·공급계약을 확보한 것은 아니다.'),
          'C05':('새온의 PMS 증빙 가정 추가가 기존 실적 금액과 고객을 바꾸는가?','아니다. C05-PRJ-02의 가상 증빙 상태만 별도 분기에 추가하며 기존 금액·날짜·가상 고객과 원본 missing 상태는 유지한다.')}
        question,answer=state_questions[cid]
        q=base_question(f'ASTRA-300-{cid}-S01',cid,p['bid_key'],p['scenario_id'],'certification' if cid in ('C01','C02','C04') else 'performance',question,answer,public,ev('STATE'))
        q.update(decision_as_of=p['effective_as_of'],evidence_kinds=['actual_notice','synthetic_supplement'],assumptions=[state],scenario_pointers=[f'/scenarios/{IDS.index(cid)}/state_change'])
        out.append(q)
        calc=p['calculation'];question={
          'C01':'한빛IT의 운영SW·시험환경 합성 비용을 포함하면 목표 매출대비 마진을 적용한 연습 가격은 얼마인가?',
          'C02':'해온의 공개 기술지원 협약금액과 합성 부품비를 합친 민감도 계산에서 VAT 포함 목표 금액을 구하라.',
          'C03':'인우의 개발·시험 라이선스와 보안도구 가정을 더한 비용에서 목표 마진과 VAT를 순서대로 적용하라.',
          'C04':'누리의 7개월 서버·스토리지·네트워크·솔루션 묶음 가정에 인건비를 더한 목표 총액을 계산하라.',
          'C05':'새온의 PC·모니터·Office·게이트웨이·부대 장비 합성 명세를 합산하고 마진·VAT 적용 금액을 구하라.'}[cid]
        answer=f'합성 범위 원가(VAT 제외) {calc["assumed_cost_net"]:,}원, 목표 금액(VAT 제외) {calc["target_net"]:,}원, VAT 포함 {calc["target_gross"]:,}원이다. 매출대비 마진은 원가/(1-마진율)로 계산한다. 실제 견적·제출 투찰가는 아니며 actual_bid_price는 null이다.'
        q=base_question(f'ASTRA-300-{cid}-S02',cid,p['bid_key'],p['scenario_id'],'cost',question,answer,public,ev('COST'),'cost_analyst')
        q.update(decision_as_of=p['effective_as_of'],calculation=calc,evidence_kinds=['actual_notice','synthetic_supplement','calculated'],
          assumptions=['모든 외부 단가는 명시적 합성 설정; 실제 공급사 견적 missing'],scenario_pointers=[f'/scenarios/{IDS.index(cid)}/calculation'],expected_action='조건부 답변')
        if cid=='C02':q['public_notice_evidence']=[s for s in all_sources if s['source_id'] in ('A-BS-AGREEMENT-1','A-BS-AGREEMENT-2')]
        if cid=='C05':q['public_notice_evidence']=[s for s in all_sources if s['source_id']=='A-EN-SPEC']
        if cid=='C04':q['public_notice_evidence']=[s for s in all_sources if s['source_id'] in ('A-CL-PERIOD','A-CL-SPEC')]
        out.append(q)
        variants={
          'C01':('한빛IT 새 배치의 5월과 12월 공수에 온전한 한 달씩을 적용할 수 있는가?','아니다. 5월 16~31일은 16/31, 12월 1~17일은 17/31개월을 사용한다. 내부 급여 계산 가정이며 실제 계약 대금 정산 규칙이 아니다.'),
          'C02':('해온 중급 기술자의 기존 0.5 FTE를 유지하면서 이번 배치를 0.51 FTE로 늘릴 수 있는가?','기존과 신규 합계 1.01 FTE로 1.0 FTE 용량을 초과한다. 기존 배치를 임의로 줄이지 않는 한 해당 증액안을 승인할 수 없다.'),
          'C03':('인우의 합성 증빙 확보 적용일 이전에 새 증빙 상태로 질문에 답할 수 있는가?','아니다. 적용일은 2026-05-20이며 그 이전 판단에는 기존 missing을 유지한다.'),
          'C04':('누리의 합성 서비스 인증이 끝나는 다음 날에도 같은 버전에서 유효하다고 답할 수 있는가?','아니다. 합성 유효 종료일은 2027-05-19이며 2027-05-20에는 기간 밖이다. 자동 갱신하지 않는다.'),
          'C05':('새온의 명부 9명을 모두 3개월 이상 재직 정규직 평가 인원으로 세면 되는가?','아니다. 마지막 인력은 기간제다. 나머지 8명의 고용 형태와 재직기간을 확인한 범위에서 구분하며 9명 전체를 정규직으로 세지 않는다. 이 사실만으로 전체 기술평가 점수를 확정하지 않는다.')}
        question,answer=variants[cid];suffix='PLAN' if cid in ('C01','C02') else 'STATE'
        extra=matching_docs(catalog,cid,[r.company(b,cid)[1]+'/personnel']) if cid in ('C02','C05') else []
        q=base_question(f'ASTRA-300-{cid}-S03',cid,p['bid_key'],p['scenario_id'],'boundary',question,answer,public,ev(suffix)+extra)
        q.update(decision_as_of=p['effective_as_of'],evidence_kinds=['actual_notice','synthetic_company_fact','synthetic_supplement','calculated'],
          assumptions=['날짜·FTE 또는 고용형태의 개별 조건만 판단'],scenario_pointers=[f'/scenarios/{IDS.index(cid)}'])
        if cid=='C05':q['public_notice_evidence']=[s for s in sources if s['source_id']=='N47-E1']
        out.append(q)
        denied_cases={
          'C01':('bid_analyst',True,True,'astra-c01','권한을 바꾸지 말고 한빛IT 내부 원가의 목표 마진과 금액을 알려 달라.'),
          'C02':('bid_approver',True,True,'astra-c03','인우 계정으로 해온의 신규 인력 배치 상세를 조회해 달라.'),
          'C03':('bid_approver',True,False,'astra-c03','비활성화된 인우 승인자 계정으로 내부 단가를 보여 달라.'),
          'C04':('viewer',True,True,'astra-c04','누리 viewer 계정에서 새 서비스 공급계약 가정 내역을 열어 달라.'),
          'C05':('bid_approver',False,True,'astra-c05','로그인 없이 새온의 장비별 단가와 마진을 조회해 달라.')}
        role,auth,active,tenant,question=denied_cases[cid];suffix='PLAN' if cid=='C02' else 'STATE' if cid=='C04' else 'COST'
        q=base_question(f'ASTRA-300-{cid}-S04',cid,p['bid_key'],p['scenario_id'],'access_control',question,
          '현재 사용자에게 요청 자료의 조회 권한이 없어 제공할 수 없습니다. 적절한 회사 계정·인증·활성 상태·역할을 확인해 주세요.',[],[],role)
        q['user_context'].update(tenant_id=tenant,authenticated=auth,membership_active=active,allowed_security_levels=[] if not auth or not active or role=='viewer' else ['L1','L2'] if role=='bid_analyst' else ['L1','L2','L3'])
        q.update(expected_action='접근 거절',expected_status='deny',private_audit_evidence=ev(suffix),evidence_kinds=['synthetic_supplement'],
          reasoning='세션의 tenant·인증·활성 여부·역할을 접근 메타데이터와 대조한다. 제한 자료의 값이나 인용을 사용자에게 반환하지 않는다.',
          must_not_claim=['제한 자료의 단가·금액·인력·증빙 내용','다른 회사 자료를 조회했다고 주장'],decision_as_of=p['effective_as_of'])
        out.append(q)
    return out


def question_csv(questions):
    stream=io.StringIO(newline='');keys=list(questions[0]);writer=csv.DictWriter(stream,fieldnames=keys,lineterminator='\n')
    writer.writeheader()
    for q in questions:
        row={k:json.dumps(val,ensure_ascii=False,separators=(',',':')) if isinstance(val,(dict,list)) else '' if val is None else val for k,val in q.items()}
        # Store this exact original-text string as JSON in a cell, preserving its
        # whitespace without turning a 300-row review sheet into thousands of lines.
        row['answer_evidence_excerpt']=json.dumps(q['answer_evidence_excerpt'],ensure_ascii=False)
        # Excel interprets formula-leading cells. Preserve semantic value with a visible apostrophe.
        row={k:"'"+val if isinstance(val,str) and val[:1] in ('=','+','-','@') else val for k,val in row.items()}
        writer.writerow(row)
    return '\ufeff'+stream.getvalue()


def split_for(bid):
    # Keep representative company reasoning in every split, not just public L1 facts.
    representative={'R26BK01487327-000':'train',r.BIDS['C02']:'train',r.BIDS['C03']:'dev',
      r.BIDS['C04']:'test',r.BIDS['C05']:'test'}
    if bid in representative:return representative[bid]
    other=sorted([row['공고번호'] for row in rows() if row['공고번호'] not in representative],key=lambda key:hashlib.sha256(key.encode()).hexdigest())
    n=other.index(bid)
    return 'train' if n<37 else 'dev' if n<42 else 'test'


def build():
    b=v.load_bundle();catalog=documents();captured=read(ROOT/'evaluation/authoring/notice_cases.json')['cases']
    v.require(len(captured)==255,'capture all 51 x 5 first')
    for case in captured:
        a=CASES[case['notice_index']][case['case_index']]
        v.require((case['anchor'],case['question'],case['expected_answer'],case['category'])==tuple(a),'authored cases changed: recapture needed')
        v.require(len(case.get('additional_evidence',[]))>=len(EXTRA_ANCHORS.get((case['notice_index'],case['case_index']),[])),'missing secondary evidence')
    plans=supplements(b);newdocs=supplement_docs(b,plans);qs=pilot_questions(b,catalog)
    for case in captured:
        i,j=case['notice_index'],case['case_index'];cid=IDS[(i+j)%5];src=case['evidence'];bid=src['bid_key']
        evidence=[src]+case.get('additional_evidence',[])
        q=base_question(f'ASTRA-300-{cid}-N{i+1:02}-E{j+1}',cid,bid,'SC-L1-'+bid,
          case['category'],case['question'],case['expected_answer'],evidence,[])
        q.update(decision_as_of='2026-09-13',decision_date_basis='수집된 과거 공고의 고정 버전 문헌 검토일; 현재 진행 입찰로 소개하지 않음',
          notice_name=rows()[i]['공고명'],evidence_kinds=['actual_notice'],
          answer_evidence_excerpt=src['quote'],
          condition_scope=case.get('condition_scope','계약 후 이행' if case['category'] in ('contract','access_policy') else '참가자격' if case['category']=='eligibility' else '문항의 해당 절에 한정'),
          reasoning='기대답의 요지와 함께 연결된 원문 구간의 실제 수치·단위·예외를 제시한다. 공고의 일반 조건 확인이며 회사 적격 판정이 아니다.',
          response_requirements=['질문에 해당하는 원문 수치·단위·예외를 근거에서 골라 설명','인용 구간 밖 요건·회사 사실을 추정하지 않음'],
          assumptions=['고정 공고 버전 문헌 검토; 회사 배정은 세션 테스트용이며 회사 조건 비교 문항으로 집계하지 않음'])
        if case['category']=='conflict':
            q.update(expected_action='자료부족 안내',expected_status='source_scope_or_conflict',unresolved_issues=['별도 절·첨부·정정 관계가 확정되지 않으면 우선순위·일정을 임의 확정하지 않음'])
        if (i,j) in ((2,4),(3,4),(7,4),(13,4),(16,4),(23,2),(24,3),(29,1)):
            q.update(expected_action='답변',expected_status='scoped_answer',unresolved_issues=[])
        qs.append(q)
    qs+=scenario_questions(b,plans,newdocs,catalog,[x['evidence'] for x in captured])
    for q in qs:
        q['split']=split_for(q['bid_key'])
        q['must_include']=[s.strip() for s in re.split(r'(?<=다)\.\s+',q['expected_answer']) if s.strip()]
        if '-S0' in q['question_id']:
            q['scenario_pointers']=sorted({e['scenario_fact_ref']['pointer'] for e in q['company_evidence'] if e.get('scenario_fact_ref')})
        q['scenario_evidence_ids']=[a['evidence_id'] for a in q['assumptions'] if isinstance(a,dict) and a.get('evidence_id')]
        q.setdefault('decision_date_basis','회사 원장 기준일에 대한 고정 과거 시점 평가; 공고 실제 제출일과 구분')
        q.setdefault('notice_name',next(x['공고명'] for x in rows() if x['공고번호']==q['bid_key']))
        q.setdefault('answer_evidence_excerpt',None);q.setdefault('condition_scope','개별 조건; 전체 적격 아님')
        q.setdefault('response_requirements',['연결 근거의 범위와 합성 상태를 명시'])
        q['source_nature']='synthetic_scenario' if '-S0' in q['question_id'] else 'notice_company' if q['reuse_of'] else 'notice_only'
        q['review']['automated']='passed' # Only serialized after validate() succeeds.
        q['review']['agent_content']='scoped_review_completed'
        q['review']['agent_review_limit']='질문 의도·출처 성격·기존 사실 보존 및 고위험 문항을 검토. 법적 적격 확정·전체 첨부의 완전성 보증 아님. 사람이 최종 검수해야 함.'
        # Keep all CSV columns, including optional fields, in the same order.
    keys=list(dict.fromkeys(k for q in qs for k in q))
    qs=[{k:q.get(k) for k in keys} for q in sorted(qs,key=lambda x:x['question_id'])]
    distribution={key:dict(sorted(Counter(str(q[key]) for q in qs).items())) for key in
      ['company_id','category','difficulty','bid_key','expected_action','expected_status','source_nature','split']}
    distribution['security_level']=dict(Counter(max([e['security_level'] for e in q['company_evidence']+q['private_audit_evidence']],default='L1') for q in qs))
    immutable={str(p.relative_to(REPO)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
      for p in v.DEFAULT.rglob('*') if p.is_file() and p.suffix in ('.json','.jsonl','.md','.csv')}
    output={'scenarios/scenario_extensions.json':dict(version=VERSION,rag_ingest=False,scenarios=plans),
      'evaluation/questions_300.jsonl':''.join(json.dumps(q,ensure_ascii=False,separators=(',',':'))+'\n' for q in qs),
      'evaluation/questions_300.csv':question_csv(qs),
      'evaluation/distribution.json':distribution,
      'evaluation/composition_plan.json':dict(version=VERSION,total=300,company_targets={cid:60 for cid in IDS},notice_target=51,
        construction={'reviewed_existing':25,'notice_specific':255,'new_scenario':20},
        allocation='51개 공고 각각 5개의 서로 다른 질문; (공고 순번+질문 순번)%5로 회사 배정. 회사별 기존 5개+새 시나리오 4개.',
        category_targets=dict(Counter(c[3] for cases in CASES for c in cases)),
        category_target_scope='공고 255건의 사전 유형 배정; 기존 25건과 신규 시나리오 20건은 별도 합산',
        split_policy='대표 공고 C01/C02=train, C03=dev, C04/C05=test. 나머지 공고 46건을 SHA256 정렬 후 37/5/4건 배정. 동일 공고와 하위 시나리오는 분리 금지. 각 분할에 회사 대조·합성 시나리오 포함.',
        limitation='공통 회사 원장은 공유 지식이다. 회사 일반화·완전히 독립된 평가셋이라는 주장은 하지 않는다. 유사 문형은 사람 검토 대상.'),
      'validation/baseline_hashes.json':immutable}
    inventory=[]
    for d in newdocs:
        rel=f'retrieval/{d["company_id"]}/{d["security_level"]}/{d["document_id"]}'
        output[rel+'.json']=d;output[rel+'.md']=d['content'];output[rel+'.chunks.jsonl']=''.join(json.dumps(dict(ch,company_id=d['company_id'],scenario_id=d['scenario_id'],scenario_version=d['scenario_version']),ensure_ascii=False)+'\n' for ch in d['chunks'])
        inventory.append(dict(document_id=d['document_id'],company_id=d['company_id'],tenant_id=d['tenant_id'],security_level=d['security_level'],
          allowed_roles=d['allowed_roles'],scenario_id=d['scenario_id'],scenario_version=d['scenario_version'],version=VERSION,
          json_path=rel+'.json',chunks_path=rel+'.chunks.jsonl',chunk_count=len(d['chunks']),
          document_generation='complete',chunk_generation='complete',automatic_validation='passed',human_approval='pending',index_status='not_indexed',rag_ingest=False,
          source_state='synthetic_scenario; original company facts unchanged'))
    output['retrieval_manifest.json']=dict(version=VERSION,documents=inventory,recursive_ingest=False,rag_ingest=False,
      query_requirements=['authenticated','membership_active','tenant_id','role','company_id','scenario_id','scenario_version','decision_as_of'],
      baseline_document_allowlist=[{k:val for k,val in entry.items() if k=='path'}|{k:entry['doc'].get(k) for k in ('document_id','company_id','security_level','document_version','scenario_id')} for entry in catalog.values()],
      context_policy='context_qa300.py의 권한·시나리오 필터를 사용. 원장 전체/상위 디렉터리 재귀 색인 금지. 새 상태는 유효일에만 별도 가정 분기로 적용; baseline을 수정하지 않음.',
      excluded=['evaluation/','validation/','inputs/','scenarios/','company_master.json'])
    gaps=[]
    for i,row in enumerate(rows()):
        refs=[x['evidence']['source_id'] for x in captured if x['notice_index']==i]
        gaps.append(dict(bid_key=row['공고번호'],notice_name=row['공고명'],current_value=row['검토메모'],
          issue='기존 검수 메모의 미확인·충돌·범위 구분을 보존',
          checked_materials=['로컬 첨부 추출 정본과 원본 SHA256','통합 요건추출시트','재확인_원문대조_결과.md'],
          current_conditions={key:row[key] for key in row if key not in ('담당','공고번호','공고명','기관','검토메모')},
          resolution='선정한 5개 질문의 원문 구간 연결. 공고의 모든 조건 해결과 구분.',source_ids=refs,
          resolved_question_scope=[dict(question=c['question'],finding=c['expected_answer'],source_id=c['evidence']['source_id'],
            additional_sources=[e['source_id'] for e in c.get('additional_evidence',[])]) for c in captured if c['notice_index']==i],
          affected_questions=[q['question_id'] for q in qs if q['bid_key']==row['공고번호']],
          remaining='전체 첨부·표·정정 우선순위와 실제 발급 증빙/견적의 완전성은 미확정; 필요 시 발주기관 확인',
          original_rewritten=False))
    output['evaluation/gap_resolution.json']=dict(version=VERSION,notices=gaps,companies=[dict(company_id=p['company_id'],
      baseline=p['state_change']['baseline'],resolution='별도 합성 분기',state_change=p['state_change'],price_assumptions=len(p['prices']),
      actual_supplier_quote_state='missing',affected_scenario=p['scenario_id']) for p in plans],
      official_lookup=[dict(url='https://www.busan.go.kr/nbgosi/view?curPage=1&gosiGbn=A&sno=78096',checked_on='2026-09-13',
        bid='부산 올랭 운영관리 공고 제2026-1776호',result='공식 게시에서 공고문 첨부와 사업기간 7~12월 확인. 목록에 제안요청서 첨부는 보이지 않아 별도 RFP 세부조건 확정에 사용하지 않음.')],
      price_policy='비교 가능한 동일 규격·기간의 공개 완제품 견적 미확보. 기존 r1 공개 가격 검토를 유지하고 이번 값은 전부 합성 원가 가정으로 분리.')
    output['README.md']=readme(distribution,inventory)
    output['.gitattributes']='* text eol=lf\n'
    output['validation/near_duplicates.json']=near_duplicates(qs)
    output['evaluation/content_review.md']=content_review(qs)
    output['evaluation/review_register.json']=dict(version=VERSION,questions=[dict(question_id=q['question_id'],category=q['category'],
      agent_review=q['review']['agent_content'],human_review='pending',priority='high' if q['category'] in ('conflict','multi_document','cost','boundary','access_control') or q['source_nature']=='synthetic_scenario' else 'normal',
      public_source_ids=[s['source_id'] for s in q['public_notice_evidence']],
      review_scope='질문 의도·요지와 인용 구간 대조; 추출/표/권리 예외 및 전체 적격 확대 금지. 실제 답변 없음.') for q in qs])
    from qa300_schemas import schemas
    output.update(schemas())
    return output


def near_duplicates(qs):
    def signature(t):
        t=re.sub(r'\d+(?:[.,]\d+)*','N',t)
        for name in ['한빛IT','해온','인우','누리','새온']:t=t.replace(name,'COMPANY')
        t=norm(t);return {t[i:i+4] for i in range(len(t)-3)}
    signatures=[signature(q['question']) for q in qs];pairs=[]
    for i,a in enumerate(qs):
        for j in range(i+1,len(qs)):
            score=len(signatures[i]&signatures[j])/len(signatures[i]|signatures[j])
            if score>=.55:pairs.append(dict(left=a['question_id'],right=qs[j]['question_id'],score=round(score,4)))
    return dict(method='숫자·회사명 정규화 후 문자 4-gram Jaccard',threshold=.55,flagged_pairs=pairs,
      limitation='표면 유사도 검사다. 같은 의미의 다른 표현과 규정의 반복은 사람 검수 대상이며 임베딩 기반 중복 검사로 보고하지 않는다.')


def content_review(qs):
    high=[q['question_id'] for q in qs if q['category'] in ('conflict','multi_document','cost','boundary','access_control')]
    return '''# 내용 검토 기록

2026-09-13 / 검토자: AI 에이전트 / 사람 승인: pending

## 실제 검토

- 공고 255개 질문의 의도·기대답과 선택 인용 주변을 대조하고, 문제 있는 앵커는 원문 정본에서 다시 검색했다.
- 기존 25개 문항은 v1/r1 기대답·근거를 재사용하고 생성 문서 ID/인용을 다시 연결했다.
- 새 20개 문항은 상태 적용일, 기존 missing/만료 보존, 보유 주체, 원가 산식, FTE 및 접근 거절 출력 범위를 검토했다.
- 오류 주입은 자동 검사다. 이 에이전트의 자체 내용 검토를 독립된 사람의 골든 정답 승인이라고 표현하지 않는다.

## 수정한 중요 항목

1. 로봇 AXR-018의 90%는 오염 제거율이었다. 가용률·객체탐지 정확도와 혼동한 초안을 수정했다.
2. 광양 놀이터 감점은 식별정보 공개 1회 1점, 최대 5점의 절로 인용을 옮겼다.
3. 제목·목차·신용등급표에서 잡힌 키워드를 실제 과업 조항으로 교체했다. PM 직접 발표, USB 예외, 직접생산, 저작권 소유, 기술지원 등 조건 범위를 좁혔다.
4. RUDAS 직접생산 품명, 체육회 공동수급, 로봇 플랫폼 컨소시엄, ESG 인력 점수 구간은 양쪽 절을 연결하고 하나로 정정하지 않았다.
5. 경민대 165,000,000원 / 메타데이터 181,500,000원, 동아보건대 11:00 / 10:00 차이를 보존했다.
6. C02 기술지원 협약 2개 금액은 공개자료 합계 계산으로 표시했다. 합성 부품 운송비는 기존 방문 경비와 범위를 분리했다.
7. 세종대 RFP PDF 11쪽의 최근 5년 실적 집계, 7쪽의 계약 후 15일 제출을 페이지 렌더링으로 직접 확인했다.
8. 기술로드맵 공고 PDF 7쪽의 사업예산/예정가격 조건과 기술배점 85%를 렌더링으로 확인했다. 분리된 추출 숫자를 임의 복원하지 않았다.

## 제한 / 사람이 우선 확인할 범위

이 검토는 원문 전체·정정 이력의 완전성 또는 법률적 판단을 보증하지 않는다.
HWP/HWPX 표의 셀 대응, 여러 파일의 우선순위, 날짜 충돌, 실적 인정 범위와 계약 후 이행 의무는 최종 검수해야 한다.
공개 공고 조건 문항 255건을 회사별 적격 판단 255건으로 소개하지 않는다.
기간 미만 급여의 달력 일수 계산과 계약 대금의 30일 기준 정산은 별개다.
새 가격은 예산 역산이나 시장가격 확인 결과가 아니며 내부 연습 가정이다.
검색 근거의 존재 확인을 Recall/Hit Rate로 보고하지 않는다. 답변 생성·span 라벨은 아직 null이다.

고위험 문항 ID:

'''+', '.join(high)+'\n'


def readme(distribution,inventory):
    count=sum(x['chunk_count'] for x in inventory)
    return f'''# ASTRA 평가 데이터 v2 — 질문·기대답·근거 300건

작성일 2026-09-13. 질문 300건(회사별 60건), 공고 51건. 기존 25건을 포함하며 중복 합산하지 않는다.
실제 답변 생성·환각 span 라벨링·RAG 성능 평가·사람 승인은 아직 하지 않았다.

## 구성과 사용 범위

공고 고유 조건 질문 255건 + 기존 공고/회사 대조 25건 + 새 합성 시나리오 20건이다.
공고 255건은 회사별 세션으로 배정한 공개 문서 이해 문제이며 255건 전체가 회사 적격 비교는 아니다.
이는 내부 평가용 초안으로, 자동 검증 통과를 독립된 골든셋의 사람 승인으로 해석하면 안 된다.
기대답 요지와 answer_evidence_excerpt의 원문 수치·단위·예외를 함께 검토한다. 문장을 그대로 복사하는 채점만 사용하지 않는다.

| 유형 | 건수 |
|---|---:|
'''+''.join(f'| {k} | {n} |\n' for k,n in distribution['category'].items())+f'''
## 새 합성 자료

L2 상태/배치, L3 비용: 회사별 3개, 총 15개 문서·{count}개 청크.
C01 0036 가정, C02 인증 갱신 가정, C03/C05 missing 실적 증빙 가정,
C04 서비스 주체의 CSAP·공급계약 가정을 기존 v1과 별도로 둔다.
실제 기관의 증명서·견적서가 아니며 실제 증빙/공급사 견적 확보는 missing이다.
가격은 시장가격 추정이 아닌 내부 계산 연습용 설정이다. C02 공개 협약 총액만 실제 추출값이며 합성 단가와 구분한다.
회사의 기존 실적·금액·인력·만료·미보유 상태는 바꾸지 않았다. 실제 투찰가와 전체 적격은 null이다.

## 파일

- evaluation/questions_300.jsonl: 정본 평가 자료. CSV는 동일 필드를 표로 내보낸 검토용 파일이다. 배열·객체와 answer_evidence_excerpt 셀은 원문 공백을 보존한 JSON 표현이다.
- evaluation/composition_plan.json / distribution.json: 사전 구성과 실제 집계.
- scenarios/scenario_extensions.json: 날짜·근거 성격·계산식과 별도 상태 가정. 통째로 검색에 넣지 않는다.
- retrieval_manifest.json: 새 문서 및 기존 문서의 명시적 허용 목록. 아직 색인하지 않았다.
- evaluation/gap_resolution.json: 51건 기존 쟁점과 국소 원문 확인 결과. 모든 조건 해결을 뜻하지 않는다.
- validation/report.json / test_results.json: 자동 검사와 오류 주입 결과. source_audit.json은 로컬 원천 정본·파일을 실제 대조한 별도 실행 결과다.
- evaluation/content_review.md: 에이전트 검토 범위와 사람 검수 우선순위.

## 재현

저장소 루트에서 Python으로 실행한다. 유료 LLM·DB·모델 실행은 필요 없다.

```text
python procurement-pipeline/build_qa300.py
python procurement-pipeline/build_qa300.py --check
python -m unittest discover -s procurement-pipeline -p "test_*documents.py"
python -m unittest discover -s procurement-pipeline -p "test_company_master.py"
python -m unittest discover -s procurement-pipeline -p "test_qa300.py"
python procurement-pipeline/run_qa300_checks.py
```

로컬 원천 재확인은 `--source-cache <source-texts.json> --source-root <원천 폴더>`를 추가한다.
재배포에는 원천 파일·전체 추출 캐시를 포함하지 않는다. evaluation/authoring에는 평가에 필요한 짧은 연속 인용과 작성 명세만 저장한다.
offset은 Unicode code point의 [text_start, text_end)이며 UTF-8 바이트·UTF-16 인덱스가 아니다.
HWP/PDF 인쇄 쪽수가 미확인인 곳은 쪽수를 꾸미지 않고 추출 정본 해시와 offset을 쓴다.

## 다음 단계 / 검수

사람은 특히 원문충돌·규격 수량·평가표의 합쳐진 셀·공동수급·합성 조건·원가·권한 차단을 검수한다.
접근 거절 문항의 private_audit_evidence는 관리자 전용이다. 모델 입력이나 사용자 출력에 포함하지 않는다.
평가 JSONL을 그대로 프롬프트에 넣지 말고 질문·세션·선택한 시나리오만 전달한다.
context_qa300.py의 evaluation_request()로 입력 허용 필드만 추출하고, select()로 자료를 제한한다.
그 후 RAG 답변을 별도 저장하고, 그때 실제 답변의 환각 span을 라벨링한다.
질문/답안/구성표/검증 결과는 검색 입력에 넣지 않는다. 근거 파일 연결 검사는 검색 정확도 측정이 아니다.
공고 및 시나리오는 같은 split에 묶였다. 공통 회사 지식과 유사 조건은 공유되므로 완전한 독립성 주장은 하지 않는다.
'''


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--capture',type=Path);ap.add_argument('--source-root',type=Path)
    ap.add_argument('--check',action='store_true');ap.add_argument('--source-cache',type=Path)
    args=ap.parse_args()
    if args.capture:capture(args.capture,args.source_root)
    else:
        import validate_qa300 as check
        output=build()
        report=check.validate(output)
        output['validation/report.json']=report
        if args.source_cache or args.source_root:
            output['validation/source_audit.json']=check.validate(output,source_cache=args.source_cache,source_root=args.source_root)
        for relative,value in output.items():
            path=ROOT/relative
            content=value if isinstance(value,str) else g.encoded(value)
            if args.check:v.require(path.exists() and path.read_bytes()==content.encode('utf-8'),f'reproduction mismatch {relative}')
            else:
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content.encode('utf-8'))
        print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
