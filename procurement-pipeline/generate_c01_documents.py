"""Deterministic, offline C01 document pilot. No LLM, database, or service calls."""
import argparse
import copy
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import validate_company_master as v

DEFAULT_OUT = v.DEFAULT / 'generated/C01/r1'
REVISION = '1.0.0-r1'
OFFSET = 'Unicode code point, end exclusive'
MAX_CHARS = 5000  # Whole entities remain atomic; oversize records require review.

LABELS = dict(company_name='회사명',founded_on='설립일',enterprise_size='기업 규모',headquarters='본점',region='지역',
 effective_from='적용 시작일',effective_to='적용 종료일',address='상세 주소',coordinates='좌표',location_kind='위치 종류',
 registration_id='등록 레코드 ID',code='업종·인증 코드',name='명칭',holder_id='보유 주체 ID',registered_on='등록일',valid_until='유효 종료일',
 status='상태',evidence_id='합성 증빙 레코드 ID',kind='종류',state='보유 상태',as_of='기준일',
 project_id='실적 ID',title='사업명',domain='분야',customer='고객',customer_id='가상 고객 ID',type='유형',synthetic='합성 여부',
 contract_amount='계약금액',currency='통화',vat_basis='VAT 기준',gross='총액',net='공급가액',vat='VAT',vat_rate='VAT 가정 요율',rounding='반올림 정책',
 contracted_on='계약일',started_on='수행 시작일',scheduled_end='예정 종료일',completed_on='완료일',joint_share='공동수급 지분',subcontractor='하도급 수행 여부',
 recognized_amount_policy='실적 인정 주의사항',evidence_state='증빙 확보 상태',amount_scope='금액 범위',
 person_id='인력 ID',display_name='가상 인력명',company_id='회사 ID',role='직무',career_started_on='경력 시작일',career_years_policy='경력 산정 주의사항',
 joined_on='입사일',employment_end='고용 종료일',employment_type='고용 형태',qualifications='자격',qualification_id='자격 레코드 ID',grade='등급',issued_on='발급 설정일',
 capacity_fte='보유·가용 FTE',availability='배치 가능 기간',start='시작일',end='종료일',existing_assignments='기존 확정 배치',assignment_id='배치 ID',allocation_fte='투입 FTE',
 certification_id='인증 레코드 ID',label='인증명',holder_type='보유 주체 유형',issuer='발급 주체 설정',valid_from='유효 시작일',validity_policy='날짜별 유효성 정책',
 security_level='보안등급',origin='값의 성격',labor_rates='직무별 인건비',monthly_base='1인·1개월 기준급',employer_burden='사업주 부담 가정',
 overhead='간접비 가정',contingency='예비비 가정',target_gross_margin='목표 매출대비 마진',minimum_gross_margin='최저 매출대비 마진',
 approval_role='승인 역할',strategy='내부 정책',formula='산식',missing_quote_policy='미확보 견적 처리',
 snapshot_validity='기준일에서의 합성 인증 상태',remaining_fte='기준일 잔여 FTE')
VALUES = {'synthetic_record':'synthetic_record — 합성 레코드 존재, 실제 발급문서 아님',
 'missing':'missing — 증빙 미확보', 'not_held':'not_held — 미보유', 'registered':'registered — 합성 등록 설정',
 'completed':'completed — 완료', 'in_progress':'in_progress — 진행 중', 'permanent':'permanent — 정규직',
 'fixed_term':'fixed_term — 기간제', 'inclusive':'inclusive — VAT 포함', 'exclusive':'exclusive — VAT 제외',
 'joint_total':'joint_total — 공동사업 전체 계약액', 'company_contract':'company_contract — 해당 회사 계약액',
 'fictional_public_institution':'가상 공공기관', 'fictional_private_company':'가상 민간회사', 'region_only':'광역 지역만 표시'}


def digest(x):
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def encoded(x):
    return json.dumps(x,ensure_ascii=False,indent=2)+'\n'


def flatten(value, path=''):
    if isinstance(value,dict) and set(value)=={'value','unit','origin','formula'}:
        origin={'synthetic_setting':'합성 설정값','calculated':'계산값','source_extracted':'원문 추출값'}[value['origin']]
        text=f'{value["value"]:,} {value["unit"]} · {origin}'
        if value['formula']:text+=' · 산식: '+value['formula']
        yield path,text
    elif isinstance(value,dict):
        for key,item in value.items():
            label=LABELS.get(key,key)
            yield from flatten(item,path+' / '+label if path else label)
    elif isinstance(value,list):
        if not value:yield path,'등록 항목 없음 (임의 보완하지 않음)'
        for i,item in enumerate(value,1):yield from flatten(item,f'{path} [{i}]')
    else:
        if value is None:text='null — 미설정/해당 없음; 유효·완료·0원으로 간주하지 않음'
        elif type(value) is bool:text='예' if value else '아니오'
        else:text=VALUES.get(str(value),str(value))
        yield path,text


def evidence_ids(value):
    return sorted({x['evidence_id'] for _,x in v.walk(value) if isinstance(x,dict) and 'evidence_id' in x})


def fact_refs(ptr,value,fallback):
    return [dict(master_pointer=ptr,evidence_id=e) for e in (evidence_ids(value) or [fallback])]


def render_block(title, payload, level, snapshot):
    def safe(s):return s.replace('|','\\|').replace('\n','<br>')
    lines=[f'## {title}','',f'가상 한빛IT · C01 · astra-c01 · {level} · 상태 기준일 {snapshot}',
      '', '합성 자료 기반 내부 대장. 실제 발급 증명서가 아니다. 수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.',
      '문서 생성은 증빙 확보와 다르다. missing은 그대로 미확보 상태다.','', '| 항목 | 값 |','|---|---|']
    lines += [f'| {safe(k)} | {safe(val)} |' for k,val in flatten(payload)]
    return '\n'.join(lines)+'\n'


def build_documents(bundle):
    """Read only master + inventory: gold/mapping data must not affect content."""
    master=bundle['master']; c=master['companies'][0]
    v.require(c['company_id']=='C01','C01 company position changed; review pointers')
    base='/companies/0'; ev=c['headquarters']['evidence_id']; specs={}
    profile={k:c[k] for k in ('company_name','founded_on','enterprise_size','headquarters')}
    specs['PROFILE']=[('기업 및 본점',profile,[dict(master_pointer=base+'/'+k,evidence_id=ev) for k in profile])]
    for i,r in enumerate(c['registrations']):specs['PROFILE'].append((r['registration_id'],r,fact_refs(f'{base}/registrations/{i}',r,ev)))
    for i,r in enumerate(c['known_absences']):specs['PROFILE'].append(('미보유 등록 '+r['code'],r,fact_refs(f'{base}/known_absences/{i}',r,ev)))
    for suffix,field,idkey in [('PERF','projects','project_id'),('STAFF','personnel','person_id'),('CERT','certifications','certification_id')]:
        specs[suffix]=[]
        for i,r in enumerate(c[field]):
            payload=copy.deepcopy(r)
            if field=='personnel':
                used=sum(Decimal(str(a['allocation_fte']['value'])) for a in r['existing_assignments'] if a['start']<=c['snapshot_as_of']<=a['end'])
                payload['remaining_fte']=dict(value=float(Decimal(str(r['capacity_fte']['value']))-used),unit='FTE',origin='calculated',formula='기준일 capacity_fte - 기존 확정 배치 FTE 합; 신규 과업 배치 확정 아님')
            if field=='certifications':
                payload['snapshot_validity']='합성 레코드의 날짜 범위 내' if v.cert_valid(r,c['snapshot_as_of']) else '유효 확인 불가 또는 만료'
            specs[suffix].append((r[idkey],payload,fact_refs(f'{base}/{field}/{i}',r,ev)))
    policy=c['l3_policy']; ptr=base+'/l3_policy'
    specs['COST']=[('원가·마진 공통 정책',{k:val for k,val in policy.items() if k!='labor_rates'},fact_refs(ptr,policy,policy['evidence_id']))]
    for i,r in enumerate(policy['labor_rates']):
        payload=dict(currency=policy['currency'],vat_basis=policy['vat_basis'],**r)
        refs=fact_refs(f'{ptr}/labor_rates/{i}',r,policy['evidence_id'])
        refs += [dict(master_pointer=ptr+'/'+k,evidence_id=policy['evidence_id']) for k in ('currency','vat_basis')]
        specs['COST'].append((r['role']+' 표준 인건비',payload,refs))
    docs=[]
    for suffix,blocks in specs.items():
        t=next(t for t in bundle['inventory']['documents'] if t['document_id']=='C01-DOC-'+suffix)
        did=f'C01-{suffix}-{REVISION}'
        doc=dict(schema_version='1.0.0',document_id=did,template_id=t['document_id'],document_version=REVISION,
          master_version=master['data_version'],master_dataset_id=master['dataset_id'],company_id='C01',tenant_id=c['tenant_id'],
          security_level=t['security_level'],allowed_roles=t['allowed_roles'],synthetic=True,kind=t['kind'],title=t['title'],
          notice_id=None,notice_version=None,scenario_id=None,review_status='unreviewed',rag_ingest=False,
          content=f'# {t["title"]}\n\n문서 버전 {REVISION} / 마스터 {master["data_version"]}. 합성 자료 기반 내부 대장.\n\n',chunks=[])
        for title,payload,refs in blocks:
            text=render_block(title,payload,t['security_level'],c['snapshot_as_of'])
            v.require(len(text)<=MAX_CHARS,f'oversize atomic entity {title}; review rather than truncate')
            start=len(doc['content']);doc['content']+=text+'\n'
            doc['chunks'].append(dict(chunk_id=did+'-CH-'+digest(refs)[:12],document_id=did,document_version=REVISION,
              tenant_id=c['tenant_id'],security_level=t['security_level'],allowed_roles=t['allowed_roles'],text=text,text_start=start,text_end=start+len(text),
              offset_unit=OFFSET,source_fact_refs=refs))
        doc['content']=doc['content'].removesuffix('\n')
        docs.append(doc)
    return docs


def export_rows(doc):
    return [dict(company_id=doc['company_id'],master_dataset_id=doc['master_dataset_id'],master_version=doc['master_version'],
      synthetic=True,review_status=doc['review_status'],rag_ingest=False,index_status='not_indexed',**ch) for ch in doc['chunks']]


def export_schema(b):
    schema=copy.deepcopy(b['document_schema']['properties']['chunks']['items'])
    extras=dict(company_id={'enum':['C01']},master_dataset_id={'type':'string','minLength':1},
      master_version={'type':'string','minLength':1},synthetic={'enum':[True]},review_status={'enum':['unreviewed']},
      rag_ingest={'enum':[False]},index_status={'enum':['not_indexed']})
    schema['properties'].update(extras);schema['required']+=list(extras)
    schema.update({'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:astra:c01-pilot-chunk-export:r1',
                   'description':'C01 r1 전용 JSONL 행 계약. 문서 내부 청크에 회사·마스터 버전·적재 상태를 추가한 외부 전송 형식.'})
    return schema


def plan_review(b):
    c=b['master']['companies'][0];p=copy.deepcopy(next(x for x in b['plans']['scenarios'] if x['scenario_id']=='SC-WB-C01'))
    staffing=p['staffing'];a=staffing[0];person=next(x for x in c['personnel'] if x['person_id']==a['person_id'])
    v.validate_capacity(person,[a])
    rate=next(x for x in c['l3_policy']['labor_rates'] if x['role']==person['role'])
    cost=(Decimal(str(rate['monthly_base']['value']))*Decimal(str(a['allocation_fte']['value']))*(1+Decimal(str(rate['employer_burden']['value']))/100)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
    return dict(schema_version='1.0.0',company_id='C01',tenant_id='astra-c01',security_level='L3',allowed_roles=['cost_analyst','bid_approver'],
      rag_ingest=False,purpose='offline_planning_review_only',source_scenario=p,
      execution_gate='blocked_not_a_submission_plan',blockers=[
       dict(code='SOLO_0036_NOT_HELD',source_ids=['S-WB-0036'],master_pointer='/companies/0/known_absences/0',note='현재 단독 모드의 0036 조건 미충족. 업체 사실 변경 또는 임의 공동수급 승인 금지.'),
       dict(code='NOTICE_YEAR_UNRESOLVED',source_ids=['S-WB-YEAR','S-WB-DEADLINE','S-WB-AMOUNT'],master_pointer=None,note='2025-04-24 말미 날짜와 2026-05-15 제출 일정의 연도 불일치. 최근 3년 실적 계산 보류.')],
      staffing_check='existing_plus_this_independent_draft_within_capacity',
      staffing_basis='기존 시나리오의 날짜·0.5 FTE를 그대로 재사용한 합성 대안; 발주기관 필수 투입량·실제 착수일이 아님',
      cost_example=dict(value=int(cost),unit='KRW/full_month',origin='calculated',vat_basis='exclusive',
         scope='C01-P-03 한 명의 온전한 1개월 0.5 FTE 직접 인건비 예시만. 전체 견적·투찰가 아님',
         formula='round_half_up(monthly_base * 0.5 * (1 + employer_burden / 100))',
         master_pointers=['/companies/0/personnel/2','/companies/0/l3_policy/labor_rates/1']),
      period_person_months=None,supplier_quote_amount=None,total_direct_cost=None,total_cost=None,bid_price=None,
      missing_inputs=['실제 착수일·과업별 필요 인원·투입률','월 중 종료의 공수/일할계산 정책','외부 견적·기타 직접비','참여 방식 해소 및 공식 공고 기준일'],
      approval_status='not_approved',index_status='not_indexed')


def bindings(b,docs):
    refs={r['source_id']:r for r in b['sources']['references']}; byq=[]
    for q in b['qa']['questions']:
        matches=[]
        for d in docs:
            if d['security_level']!='L2':continue
            for ch in d['chunks']:
                if any(a['master_pointer']==p or a['master_pointer'].startswith(p+'/') or p.startswith(a['master_pointer']+'/')
                       for a in ch['source_fact_refs'] for p in q['evidence']['master_pointers']):
                    matches.append(dict(document_id=d['document_id'],document_version=d['document_version'],chunk_id=ch['chunk_id'],
                      text_start=ch['text_start'],text_end=ch['text_end'],offset_unit=OFFSET,quote=ch['text'],
                      master_fact_refs=ch['source_fact_refs'],tenant_id=d['tenant_id'],security_level=d['security_level']))
        v.require(matches,'no L2 evidence for '+q['question_id'])
        byq.append(dict(question_id=q['question_id'],bid_key=q['bid_key'],company_id='C01',scenario_id=q['scenario_id'],
          original_qa_file='../../../../evaluation/qa_pilot_5.json',original_master_pointers=q['evidence']['master_pointers'],
          original_synthetic_evidence_ids=q['evidence']['synthetic_evidence_ids'],public_notice_evidence=[refs[s] for s in q['evidence']['source_ids']],
          generated_company_evidence=matches,check='pointer_and_quote_linked_not_retrieval_benchmark',actual_answer=None,hallucination_spans=None))
    return dict(schema_version='1.0.0',rag_ingest=False,purpose='offline_evaluation_only',master_dataset_id=b['master']['dataset_id'],master_version=b['master']['data_version'],
                original_qa_sha256=digest(b['qa']),questions=byq)


def validate_documents(b,docs):
    v.validate_master(b['master'],b['schema'])
    expected=build_documents(b)
    v.require(len(docs)==5,'five common documents required')
    for actual,wanted in zip(docs,expected):
        v.validate_generated_document(actual,b)
        v.require(actual==wanted,'master/render/metadata drift in '+actual['document_id'])
        # Exact rendering is the primary fidelity check. This is an additional guard.
        for key in ('expected_answer','gold_label','must_not_claim','expected_status'):
            v.require(key not in actual['content'],'evaluation field in document')
        for cid in ('C02','C03','C04','C05'):
            v.require(cid not in actual['content'],'other tenant text')
    v.unique([ch['chunk_id'] for d in docs for ch in d['chunks']],'all generated chunk IDs')
    return True


def validate_bindings(b,docs,linked):
    v.require(linked['rag_ingest'] is False and len(linked['questions'])==5,'evaluation isolation/count')
    byid={d['document_id']:d for d in docs}
    for row,q in zip(linked['questions'],b['qa']['questions']):
        v.require(row['question_id']==q['question_id'] and row['bid_key']==q['bid_key'],'QA identity')
        public={r['source_id']:r for r in b['sources']['references']}
        v.require(row['public_notice_evidence']==[public[s] for s in q['evidence']['source_ids']],'public evidence mismatch')
        all_ptrs=[];all_eids=set()
        for e in row['generated_company_evidence']:
            d=byid[e['document_id']];ch=next(ch for ch in d['chunks'] if ch['chunk_id']==e['chunk_id'])
            v.require(d['security_level']=='L2' and e['security_level']=='L2' and e['tenant_id']=='astra-c01','QA company evidence permissions')
            v.require(e['document_version']==d['document_version'],'QA document version')
            v.require(e['quote']==ch['text'] and e['text_start']==ch['text_start'] and e['text_end']==ch['text_end'],'QA quote offsets')
            v.require(e['master_fact_refs']==ch['source_fact_refs'],'QA fact refs')
            all_ptrs += [f['master_pointer'] for f in ch['source_fact_refs']]
            all_eids |= {f['evidence_id'] for f in ch['source_fact_refs']}
        for p in q['evidence']['master_pointers']:
            v.require(any(a==p or a.startswith(p+'/') or p.startswith(a+'/') for a in all_ptrs),'uncovered QA pointer')
        v.require(set(q['evidence']['synthetic_evidence_ids'])<=all_eids,'missing QA evidence IDs')
    return True


def access_checks(docs):
    sessions=[('own_analyst','astra-c01','bid_analyst',True,True),('own_cost','astra-c01','cost_analyst',True,True),
      ('own_approver','astra-c01','bid_approver',True,True),('own_viewer','astra-c01','viewer',True,True),
      ('foreign_approver','astra-c02','bid_approver',True,True),('unauthenticated','astra-c01','bid_approver',False,True),
      ('inactive','astra-c01','bid_approver',True,False)]
    rows=[]
    for name,tenant,role,auth,active in sessions:
        session=dict(tenant_id=tenant,role=role,authenticated=auth,membership_active=active)
        for d in docs:
            expected=auth and active and tenant=='astra-c01' and (role in ('cost_analyst','bid_approver') or role=='bid_analyst' and d['security_level']=='L2')
            actual=[v.can_access(session,ch) for ch in d['chunks']]
            v.require(all(a==expected for a in actual),'chunk access rule mismatch')
            rows.append(dict(session_case=name,document_id=d['document_id'],expected_allow=expected,chunks_checked=len(actual),passed=True))
    return dict(scope='offline_metadata_policy_only',live_service_tested=False,chunk_checks=sum(r['chunks_checked'] for r in rows),cases=rows)


def artifacts(b):
    docs=build_documents(b);validate_documents(b,docs);out={};entries=[]
    row_schema=export_schema(b);out['chunk_export.schema.json']=encoded(row_schema)
    for d in docs:
        stem=d['security_level']+'/'+d['document_id']
        out[stem+'.md']=d['content'];out[stem+'.json']=encoded(d)
        rows=export_rows(d)
        for row in rows:v.schema_check(row,row_schema)
        out[stem+'.chunks.jsonl']=''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows)
        entries.append(dict(document_id=d['document_id'],template_id=d['template_id'],company_id='C01',tenant_id=d['tenant_id'],
           security_level=d['security_level'],allowed_roles=d['allowed_roles'],json_path=stem+'.json',markdown_path=stem+'.md',chunks_path=stem+'.chunks.jsonl',
           document_version=REVISION,content_sha256=hashlib.sha256(d['content'].encode()).hexdigest(),chunk_count=len(d['chunks']),
           document_generation='generated',chunk_generation='generated',automated_validation='passed',human_approval='pending',
           review_status='unreviewed',rag_ingest=False,index_status='not_indexed'))
    manifest=dict(schema_version='1.0.0',company_id='C01',tenant_id='astra-c01',documents=entries,
      master_dataset_id=b['master']['dataset_id'],master_data_version=b['master']['data_version'],master_canonical_sha256=digest(b['master']),
      chunking=dict(strategy='whole semantic entity; no overlap; no mid-entity truncation',max_characters=MAX_CHARS,
                    offset_unit=OFFSET,token_count=None,note='문자 상한은 토큰 수가 아님; 실제 임베딩 모델의 tokenizer 검사가 적재 전 필요'),
      evidence_status_policy='master remains unchanged; generated ledger is not an issued evidence document',
      retrieval_input_allowlist=[e['chunks_path'] for e in entries],recursive_directory_ingest_allowed=False,
      evidence_registry=[dict(evidence_id=e['evidence_id'],master_status=e['status'],issued_evidence_document_generated=False,
           ledger_document_ids=[d['document_id'] for d in docs if any(f['evidence_id']==e['evidence_id'] for ch in d['chunks'] for f in ch['source_fact_refs'])])
          for e in b['master']['evidence_registry'] if e['company_id']=='C01'])
    out['manifest.json']=encoded(manifest)
    linked=bindings(b,docs);validate_bindings(b,docs,linked)
    out['evaluation/qa_document_bindings.json']=encoded(linked)
    access=access_checks(docs);out['review/access_checks.json']=encoded(access)
    plan=plan_review(b);out['review/scenario_review.json']=encoded(plan)
    out['review/scenario_review.md']='# 한빛IT 대표 공고 검토 초안\n\nL3 · astra-c01 · cost_analyst/bid_approver · 검색 적재 금지.\n\n'+render_block('실행 차단 및 제한된 원가 예시',plan,'L3',b['master']['snapshot_as_of'])
    lengths=[len(ch['text']) for d in docs for ch in d['chunks']]
    report=dict(schema_version='1.0.0',status='passed',documents=len(docs),chunks=len(lengths),
      chunk_characters=dict(min=min(lengths),max=max(lengths),total=sum(lengths)),qa_bindings=5,
      master_changed=False,external_llm_calls=0,db_writes=0,span_labels_generated=0,
      offline_permission_chunk_checks=access['chunk_checks'],checks=['strict document schema','master projection exact rendering','certificate dates and missing states','money/VAT and FTE via master validator',
              'source pointers and offsets','JSONL metadata matches document','gold isolated by separate output and allowlist','draft cost Decimal calculation'],
      limits=['실제 검색 성능·모델 답변·권한 서버를 검사하지 않았다.','정형 원장 투영의 일치 검증이며 일반 자유서술 문서의 무환각을 보장하지 않는다.',
              '검수 승인 대기, 벡터 DB 미적재.','공고 원문 참조는 기존 대조 결과를 사용; 이번에 새로운 원문 재파싱은 하지 않았다.'],
      artifacts={k:hashlib.sha256(val.encode()).hexdigest() for k,val in out.items()})
    out['validation_report.json']=encoded(report)
    return out


def write_or_check(b,folder,check=False):
    outputs=artifacts(b)
    if check:
        for name,content in outputs.items():
            path=folder/name
            v.require(path.exists() and path.read_bytes()==content.encode('utf-8'),'output drift: '+name)
    else:
        # Same version is immutable: do not overwrite edited outputs silently.
        for name,content in outputs.items():
            p=folder/name
            v.require(not p.exists() or p.read_bytes()==content.encode('utf-8'),'existing revision differs; review and bump output revision: '+name)
        for name,content in outputs.items():
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content.encode('utf-8'))
    return json.loads(outputs['validation_report.json'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--out',type=Path,default=DEFAULT_OUT)
    a=p.parse_args();b=v.load_bundle();report=write_or_check(b,a.out,a.check)
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
