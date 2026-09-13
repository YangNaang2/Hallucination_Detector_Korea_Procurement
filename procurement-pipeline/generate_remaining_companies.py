"""Offline C02-C05 generation. Common ledgers share the regression-protected C01 renderer."""
import argparse
import calendar
import copy
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import generate_c01_documents as g
import validate_company_master as v

ROOT = v.DEFAULT / 'generated/C02-C05/r1'
IDS = ('C02', 'C03', 'C04', 'C05')
REV = g.REVISION
BIDS = dict(C02='R26BK01474723-000', C03='R26BK01518315-000',
            C04='R26BK01574547-000', C05='R26BK01505744-000')


def qty(value, unit, origin='synthetic_setting', formula=None):
    return dict(value=value, unit=unit, origin=origin, formula=formula)


def money(x):
    return int(Decimal(x).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def company(b, cid):
    i = next(i for i,c in enumerate(b['master']['companies']) if c['company_id']==cid)
    return b['master']['companies'][i], f'/companies/{i}'


def capture_sources(cache, source_root):
    """Capture short reviewed excerpts, not full originals. Explicitly opt-in only."""
    items=json.loads(cache.read_text(encoding='utf-8')); result=[]
    selections=[
      ('A-BS-PERIOD','C02','(2).hwp','용역기간',380,'1. 견적입찰'),
      ('A-BS-CONFIRM','C02','(2).hwp','본 건은 물품공급',125,'1. 계약 전 확약서'),
      ('A-BS-SUPPORT','C02','.hwpx','본 공고는 기술지원협약서',99,'I. 사업개요'),
      ('A-BS-SLA','C02','.hwpx','2시간 이내',230,'I. 사업범위'),
      ('A-BS-PRORATA','C02','.hwpx','1개월 미만일 경우',110,'유지관리비 청구 및 지급'),
      ('A-IC-PERIOD','C03','일반공고문(원본).pdf','용 역 기 간',210,'1. 입찰에 부치는 사항'),
      ('A-IC-INFRA','C03','.hwpx','인천 블록체인 메인넷 구성도',500,'사업 개요'),
      ('A-IC-STAFF','C03','.hwpx','※  용역 수행조직 및 인원현황',550,'별지 제6호 및 제6-1호'),
      ('A-IC-PROOF','C03','.hwpx','주요사업실적 1부',110,'제출서류 목록 제9호/제9-1호'),
      ('A-CL-PERIOD','C04','.pdf','용역기간',300,'1. 입찰에 부치는 사항'),
      ('A-CL-SPEC','C04','.hwpx','사업대상 상세내역',1900,'사업대상 상세내역'),
      ('A-EN-PERIOD','C05','붙임 1.','용역기간',300,'1. 입찰에 부치는 사항'),
      ('A-EN-SPEC','C05','붙임 2.','PC 사양',790,'SFR-001'),
      ('A-EN-DIRECT','C05','붙임 1.','계약상대자는 본 과업을 직접 수행',85,'참가자격 및 직접 수행'),
    ]
    for sid,cid,name,key,length,section in selections:
        candidates=[d for d in items if d['bid']==BIDS[cid] and name in d['name'] and key in (d.get('text') or '')]
        v.require(len(candidates)==1, f'ambiguous/missing source {sid}: {len(candidates)}')
        d=candidates[0]; start=d['text'].index(key); end=min(start+length,len(d['text']))
        # Stop on a line boundary so an unrelated trailing requirement is not cut mid-sentence.
        boundary=d['text'].rfind('\n',start,end)
        if boundary>start+len(key):end=boundary
        raw=source_root/d['relative']; v.require(hashlib.sha256(raw.read_bytes()).hexdigest()==d['sha256'],'raw hash changed')
        result.append(dict(source_id=sid,notice_id=BIDS[cid][:-4],notice_version='000',bid_key=BIDS[cid],filename=d['name'],
          relative_source_path=d['relative'],sha256=d['sha256'],text_sha256=hashlib.sha256(d['text'].encode()).hexdigest(),
          extraction_method=d['method'],section=section,page=None,page_basis='미확인; 정본 추출문자 위치 사용',
          text_start=start,text_end=end,offset_unit=g.OFFSET,quote=d['text'][start:end],
          review_status='extracted_text_checked',origin='source_extracted'))
    d=next(d for d in items if d['bid']==BIDS['C02'] and '협약서.pdf' in d['name'])
    for page,amount,scope in [(1,32628780,'영상중계 및 통합플랫폼 SW'),(2,23691460,'망연계·방화벽·네트워크스위치')]:
        result.append(dict(source_id=f'A-BS-AGREEMENT-{page}',notice_id=BIDS['C02'][:-4],notice_version='000',bid_key=BIDS['C02'],
          filename=d['name'],relative_source_path=d['relative'],sha256=d['sha256'],text_sha256=None,
          extraction_method='manual visual transcription',section='제3조 협약금액',page=page,page_basis='PDF viewer 1-based',
          text_start=None,text_end=None,offset_unit=None,quote=f'금{amount:,}원/VAT포함' if page==1 else f'금{amount:,}/VAT포함',
          scope=scope,review_status='pdf_visual_checked',origin='source_extracted',
          limitation='스캔 PDF 페이지를 직접 읽은 짧은 전사. 회사에 발행된 견적이 아니며 공급권한을 증명하지 않음.'))
    return dict(version='1.0.0',rag_ingest=False,references=result)


def inputs(b):
    """Versioned planning choices; no changes to common company facts."""
    setup={
      'C02':('2026-05-01','2026-12-31',[(2,.5,'중급 유지관리 기술자')],
        '공고 명시 기간. 중급 기술자 잔여 0.5 FTE를 활용하는 내부 검토안이며 SLA 충족 보증이 아님.',
        ['기술지원 확약서 미확보(계약 전 제출 의무)','중급 기술자 1명의 부분 투입만으로 장애 2시간 도착·4시간 복구 및 대체 인력 확보 여부 미검증','장비 교체·부품 비용 범위 및 공급사 최종 적용 조건 미확정'],
        ['A-BS-PERIOD','S-BS-STAFF','A-BS-SLA','A-BS-CONFIRM','A-BS-SUPPORT','A-BS-AGREEMENT-1','A-BS-AGREEMENT-2']),
      'C03':('2026-06-01','2026-12-10',[(2,.4,'개발 조정 담당'),(3,.8,'기능 개발'),(4,.5,'개발·운영 보완'),(5,.2,'품질 검증'),(6,.2,'운영 지원')],
        '착수일은 합성 가정, 종료일만 공고 기준. 기존 공동수급 실패 사례를 보존한 별도의 단독 대안. 기능개선 범위·역할 배분은 협의 전 초안.',
        ['총괄책임자와 세부 개발 범위에 대한 발주처 협의 미완료','기술등급 및 제출용 경력·가입자 증명 확인 필요','기존 인프라 활용 전제이며 추가 상용SW·보안 도구 비용 미확정'],
        ['A-IC-PERIOD','A-IC-INFRA','A-IC-STAFF','S-IC-REGION']),
      'C04':('2026-06-01','2026-12-31',[(7,.15,'클라우드 조정'),(3,.25,'서비스 운영'),(8,.1,'보안 운영')],
        '공고의 7개월 가격 산정 기간 사용. 실제 개시일이 지연되면 서비스 정산과 배치를 다시 계산해야 함.',
        ['공급 대상 서비스 CSAP 증빙 missing','공급 계약·권한 missing','서버·스토리지·트래픽·보안·솔루션을 포함하는 전체 동일 규격 공급가격 미확정'],
        ['A-CL-PERIOD','A-CL-SPEC','S-CL-CSAP','S-CL-ISMS']),
      'C05':('2026-06-01','2026-11-30',[(7,.2,'EMS 관리'),(3,.8,'전력 제어 개발'),(4,.8,'SW 구현'),(6,.3,'품질 시험')],
        '착수일은 합성 가정이며 원문 계약일이 아님. 종료일까지 기존 자체 인력을 배치하는 대안; 장비 조달·시운전 상세 공정은 미확정.',
        ['PC·게이트웨이·서버랙·UPS·스위치·상용SW 전체 견적 미확보','시험설비 인터페이스와 현장 설치 조건 미확정','제출 일정의 요일 표기 및 계약 일정은 공식 확인 전 확정하지 않음'],
        ['A-EN-PERIOD','A-EN-SPEC','A-EN-DIRECT','S-EN-REG','S-EN-EXP'])}
    plans=[]
    for cid,(start,end,staff,note,holds,sources) in setup.items():
        c,base=company(b,cid)
        rows=[dict(assignment_id=f'{cid}-R1-A{i+1}',person_id=f'{cid}-P-{n:02}',start=start,end=end,
          allocation_fte=qty(fte,'FTE'),planned_work=work,origin='synthetic_setting',
          rationale='기존 확정 배치의 잔여 가용량 안에서 역할별로 책정한 내부 작업량; 발주기관 필수 인원·등급 판정 아님')
          for i,(n,fte,work) in enumerate(staff)]
        plans.append(dict(scenario_id=f'SC-{cid}-REVIEW-r1',company_id=cid,tenant_id=c['tenant_id'],security_level='L3',
          allowed_roles=['bid_approver'],version=REV,bid_key=BIDS[cid],mode='independent_draft_alternative',
          mutually_exclusive_group=f'{cid}-2026-OPTIONS',committed=False,actual_contract_start=None,
          planning_start=start,planning_end=end,start_origin='synthetic_setting' if cid in ('C03','C05') else 'source_extracted',
          end_origin='source_extracted',basis=note,source_ids=sources,staffing=rows,
          exercise_scope='내부 검토·비용 민감도만; 전체 참가자격 충족 또는 제출 승인 아님',
          holds=holds,other_direct_assumption=dict(item='내부 검토용 현장 방문 경비',
            quantity=qty({'C02':8,'C03':8,'C04':4,'C05':12}[cid],'visits'),unit_net=qty(150000 if cid!='C05' else 200000,'KRW/visit'),
            reason='교통·현장 소모품을 묶은 계획 가정. 실제 공공 운임표나 업체 견적이 아니며 숙박·장비 구매·상용 라이선스는 포함하지 않음'),
          supplier_quote_state='missing',supplier_quote_amount=None,bid_price=None,rag_ingest=False,
          human_approval='pending',index_status='not_indexed'))
    return dict(version=REV,master_sha256=g.digest(b['master']),rag_ingest=False,scenarios=plans,
      assumption_policy='가용 인력으로 제한한 합성 대안이다. 기존 확정 배치와만 합산하고, 여러 대안을 동시 실행하려면 committed 계획 전체로 재검증한다.',
      prorata_policy='내부 인건비는 양 끝 날짜 포함, 해당 월 실제 달력 일수 분모. 공고상 지급 일할 규칙과 구분(C02 유지관리 대금은 30일 기준).',
      rounding_policy='Decimal 중간값 유지; 최종 항목 원 단위 HALF_UP. 표시된 반올림 행 합계와 총액의 차이는 별도 기록.')


def months(start,end):
    a=date.fromisoformat(start); end=date.fromisoformat(end); parts=[]
    while a<=end:
        last=date(a.year,a.month,calendar.monthrange(a.year,a.month)[1]); z=min(last,end)
        parts.append(dict(month=a.strftime('%Y-%m'),days=(z-a).days+1,denominator=last.day,origin='calculated'))
        a=z+timedelta(days=1)
    return parts


def calculate(c,p):
    details=[]; raw_total=Decimal(0)
    v.unique([a['person_id'] for a in p['staffing']],'one aggregated assignment per person per scenario')
    for person in c['personnel']:
        v.validate_capacity(person,[a for a in p['staffing'] if a['person_id']==person['person_id']])
    for a in p['staffing']:
        person=next(x for x in c['personnel'] if x['person_id']==a['person_id'])
        v.validate_capacity(person,[a])
        v.require(person['joined_on']<=a['start'] and (person['employment_end'] is None or a['end']<=person['employment_end']),'plan outside employment')
        rate=next(x for x in c['l3_policy']['labor_rates'] if x['role']==person['role'])
        parts=months(a['start'],a['end']); pm=sum(Decimal(x['days'])/x['denominator'] for x in parts)*Decimal(str(a['allocation_fte']['value']))
        raw=Decimal(rate['monthly_base']['value'])*pm*(1+Decimal(str(rate['employer_burden']['value']))/100);raw_total+=raw
        details.append(dict(person_id=a['person_id'],master_role=person['role'],start=a['start'],end=a['end'],allocation_fte=a['allocation_fte'],
          month_prorata=parts,person_months_exact_decimal=str(pm),monthly_base=rate['monthly_base'],employer_burden=rate['employer_burden'],
          labor_net=qty(money(raw),'KRW','calculated','round_half_up(monthly_base * sum(days/month_days) * FTE * (1+burden/100))')))
    other=p['other_direct_assumption'];other_raw=Decimal(other['quantity']['value'])*Decimal(other['unit_net']['value'])
    direct=raw_total+other_raw;policy=c['l3_policy']
    scope_cost=direct*(1+Decimal(policy['overhead']['value'])/100+Decimal(policy['contingency']['value'])/100)
    reference=None
    if c['company_id']=='C02':
        # Two original agreement amounts, not a vendor quote issued to C02.
        gross=32628780+23691460; net=Decimal(gross)/Decimal('1.1')
        loaded=(direct+net)*(1+Decimal(policy['overhead']['value'])/100+Decimal(policy['contingency']['value'])/100)
        target=loaded/(1-Decimal(policy['target_gross_margin']['value'])/100)
        reference=dict(original_agreement_gross=qty(gross,'KRW','calculated','32628780 + 23691460 (A-BS-AGREEMENT-1/2)'),
          vat_basis='inclusive',vat_rate_assumption=qty(10,'percent'),
          conditional_scope_cost_net=qty(money(loaded),'KRW','calculated','(labor + assumed visits + public agreement gross/1.1) * (1+overhead/100+contingency/100)'),
          conditional_target_net=qty(money(target),'KRW','calculated','conditional_scope_cost_net before rounding / (1-target_gross_margin/100)'),
          conditional_target_gross=qty(money(target*Decimal('1.1')),'KRW','calculated','unrounded conditional target net * 1.1'),
          warning='공개 협약 금액을 가정 적용한 민감도 예시. 실제 견적·전체 수행원가·투찰금액이 아니며 부품 등 미확정 비용 제외.')
    return dict(currency='KRW',vat_basis='exclusive',origin='calculated',labor_lines=details,
      labor_net=qty(money(raw_total),'KRW','calculated','round_half_up(sum(unrounded labor lines))'),
      row_rounding_difference=qty(money(raw_total)-sum(x['labor_net']['value'] for x in details),'KRW','calculated','rounded total - sum(rounded rows)'),
      other_direct_net=qty(money(other_raw),'KRW','calculated','assumed visits * assumed unit cost'),
      scoped_direct_net=qty(money(direct),'KRW','calculated','unrounded labor + assumed visits'),
      scoped_cost_net=qty(money(scope_cost),'KRW','calculated','scoped direct * (1+overhead/100+contingency/100)'),
      scope='자체 인력과 합성 방문 경비만. 장비·클라우드·외부SW 및 전체 사업 원가는 아님.',
      public_price_sensitivity=reference,supplier_quote_state='missing',supplier_quote_net=None,total_project_cost=None,bid_price=None)


def external_refs():
    return [dict(reference_id='W-NCLOUD',url='https://www.gov-ncloud.com/charge/price',checked_on='2026-09-13',
      provider='NAVER CLOUD 공식 공공기관용 요금 소개',currency='KRW',region='대한민국',vat_basis='unconfirmed',
      product_scope='시간·사용량 기준 서비스별 요금 안내; 공고 전체 구성에 대한 확정 견적 없음',period='현재 안내; 2026년 6월 역사 가격 확인 아님',
      accepted_price=None,actual_supplier_quote_state='missing',
      result='서비스별 사양·용량·트래픽과 라이선스 조건을 확정해야 산정 가능. 실제 서비스 공급권한이나 가상 서비스 인증의 증거로 사용하지 않는다.'),
      dict(reference_id='W-DELL',url='https://www.dell.com/ko-kr/shop/dell-%EB%8D%B0%EC%8A%A4%ED%81%AC%ED%83%91/xps-%EB%8D%B0%EC%8A%A4%ED%81%AC%ED%83%91/spd/xps-8960-desktop',
      checked_on='2026-09-13',provider='Dell 대한민국 공식 제품 페이지',currency='KRW',region='대한민국',vat_basis='unconfirmed',
      product_scope='XPS 8960 구성 정보; PC·Office·모니터·랙·UPS·게이트웨이 전체 조합 아님',period='현재 조회; 공고 시점 가격 아님',
      accepted_price=None,actual_supplier_quote_state='missing',result='판매 불가 표시 및 동일 전체 구성 가격 확인 불가. 다른 사양의 시작가를 대입하지 않는다.')]


def make_doc(b,cid,suffix,blocks,p):
    c,base=company(b,cid);t=next(x for x in b['inventory']['documents'] if x['document_id']==f'{cid}-DOC-{suffix}')
    doc=copy.deepcopy(g.build_documents(b,cid)[0]);did=f'{cid}-{suffix}-{REV}'
    doc.update(document_id=did,template_id=t['document_id'],kind=t['kind'],title=t['title'],security_level=t['security_level'],
      allowed_roles=t['allowed_roles'],notice_id=p['bid_key'][:-4],notice_version=p['bid_key'][-3:],scenario_id=p['scenario_id'],
      content=f'# {t["title"]}\n\n{p["bid_key"]} / {p["scenario_id"]} / {REV}\n\n합성 검토 초안. 제출 승인·증빙 확보·색인 적재 모두 미완료.\n\n',chunks=[])
    for n,(title,payload,refs) in enumerate(blocks):
        text=g.render_block(title,payload,t['security_level'],c['snapshot_as_of'],c)
        text=text.replace('수치·날짜·보유 사실은 합성 원장의 설정이며 계산값은 별도 표시한다.',
          '회사 사실은 합성 원장 기준이다. 공고 추출값은 source_ids, 합성 계획값은 origin·basis, 계산값은 formula로 구분한다.')
        v.require(len(text)<=g.MAX_CHARS,f'oversize {cid} {suffix} {title}: {len(text)}')
        start=len(doc['content']);doc['content']+=text+'\n'
        doc['chunks'].append(dict(chunk_id=f'{did}-CH-{n+1:03}',document_id=did,document_version=REV,tenant_id=c['tenant_id'],
          security_level=t['security_level'],allowed_roles=t['allowed_roles'],text=text,text_start=start,text_end=start+len(text),offset_unit=g.OFFSET,source_fact_refs=refs))
    doc['content']=doc['content'].removesuffix('\n')
    return doc


def build(b,planned):
    docs=[];costs={};provenance=[];aug=copy.deepcopy(b);aug['plans']['scenarios']+=planned['scenarios']
    for p in planned['scenarios']:
        cid=p['company_id'];c,base=company(b,cid);common=g.build_documents(b,cid);docs+=common;cost=calculate(c,p);costs[cid]=cost
        def refs(field):
            value=v.pointer(b['master'],base+'/'+field)
            return g.fact_refs(base+'/'+field,value,c['headquarters']['evidence_id'])
        plan_blocks=[('배치 전제',dict(bid_key=p['bid_key'],scenario_id=p['scenario_id'],basis=p['basis'],
          actual_contract_start=None,start_origin=p['start_origin'],end_origin=p['end_origin'],source_ids=p['source_ids'],
          staffing_status='독립 합성 대안; 기존 배치와 합산 검증, 실행 미승인',
          constraint='문서에 나타난 자격·필수 증빙과 이행 의무를 별도 검토해야 한다. 이 초안은 전체 적격 판정이 아니다.'),refs('headquarters'))]
        for a in p['staffing']:
            index=next(i for i,x in enumerate(c['personnel']) if x['person_id']==a['person_id'])
            payload=copy.deepcopy(a);payload['existing_assignments']=c['personnel'][index]['existing_assignments']
            payload['employment_end']=c['personnel'][index]['employment_end']
            plan_blocks.append((a['person_id']+' 배치 초안',payload,refs(f'personnel/{index}')))
        docs.append(make_doc(aug,cid,'PLAN',plan_blocks,p))
        cost_blocks=[('계산 범위 및 미확정 총액',{k:x for k,x in cost.items() if k not in ('labor_lines','public_price_sensitivity')},refs('l3_policy'))]
        for line in cost['labor_lines']:
            idx=next(i for i,x in enumerate(c['personnel']) if x['person_id']==line['person_id'])
            cost_blocks.append((line['person_id']+' 인건비',line,refs(f'personnel/{idx}')+refs('l3_policy')))
        if cost['public_price_sensitivity']:cost_blocks.append(('공개 협약 금액 적용 민감도',cost['public_price_sensitivity'],refs('l3_policy')))
        docs.append(make_doc(aug,cid,'ESTIMATE',cost_blocks,p))
        quote_blocks=[('합성 직접 경비 가정',p['other_direct_assumption'],refs('l3_policy')),
          ('외부 견적 미확보',dict(supplier_quote_state='missing',supplier_quote_amount=None,
            pending=p['holds'],source_ids=p['source_ids'],
            external_reference_ids=['W-NCLOUD'] if cid=='C04' else ['W-DELL'] if cid=='C05' else [],
            resolution='확인된 인건비·방문 가정은 계산. 동일 규격 공급 조건과 실제 확보 상태는 별도로 남김.'),refs('l3_policy'))]
        if cid=='C02':quote_blocks.append(('공개 협약 가격의 범위',dict(source_ids=['A-BS-AGREEMENT-1','A-BS-AGREEMENT-2','A-BS-SUPPORT'],
          amount=cost['public_price_sensitivity']['original_agreement_gross'],vat_basis='inclusive',
          scope='영상중계·통합플랫폼 SW 및 네트워크·보안 HW 두 협약 합계. 확인일 2026-09-13; 공고의 2026년 과업 참고.',
          company_quote='missing; C02 명의 확약서·견적서 아님'),refs('l3_policy')))
        docs.append(make_doc(aug,cid,'QUOTE',quote_blocks,p))
        docs.append(make_doc(aug,cid,'BID',[('참여 보류 및 후속 확인',dict(bid_key=p['bid_key'],scenario_id=p['scenario_id'],
          status='hold_not_submission_ready',holds=p['holds'],bid_price=None,source_ids=p['source_ids'],
          decision_scope='전체 적격 여부 미확정. 원가 일부 산출과 공급권한·증빙 확보를 혼동하지 않는다.',
          approval_status='pending',alternative_group=p['mutually_exclusive_group']),refs('l3_policy'))],p))
    for d in docs:
        for ch in d['chunks']:
            p=next((p for p in planned['scenarios'] if p['scenario_id']==d['scenario_id']),None)
            provenance.append(dict(document_id=d['document_id'],chunk_id=ch['chunk_id'],company_id=d['company_id'],tenant_id=d['tenant_id'],
              security_level=d['security_level'],allowed_roles=d['allowed_roles'],document_version=d['document_version'],
              notice_id=d['notice_id'],notice_version=d['notice_version'],scenario_id=d['scenario_id'],master_fact_refs=ch['source_fact_refs'],
              planning_input_pointer=None if p is None else f'/scenarios/{IDS.index(d["company_id"])}',
              planning_input_access='L3 bid_approver only; provenance is audit-only and not retrievable',
              public_source_ids=[] if p is None else p['source_ids'],rag_ingest=False))
    return docs,costs,provenance,aug


# Evaluation definitions are separate from the generator inputs and never rendered as documents.
QA={
 'C02':[
  ('부산 본점 조건을 회사 설정으로 확인할 수 있는가?','본점은 부산이며 적용 시작일은 설립일이다. 이 개별 지역 조건의 합성 대조만 가능하며 실제 제출 증명이나 전체 적격을 확정하지 않는다.','condition_only','PROFILE',['headquarters'],['S-BS-REGION']),
  ('개발 직접생산 인증 만료가 유지관리 인증도 만료됐다는 뜻인가?','아니다. 개발 8111159901은 2026-03-31 만료, 유지관리 8111189901은 2027-12-31까지의 합성 기록이다. 공고 요구 품명과 유효기간을 각각 확인한다.','different_certificates','CERT',['certifications/1','certifications/2'],['S-BS-DIRECT']),
  ('중급 유지관리 기술자로 P-03을 대신 제시할 수 있는가?','P-03은 초급 기록으로 중급 이상을 대신할 수 없다. P-02의 중급 기록과 제출 증빙을 따로 확인해야 한다.','not_met','STAFF',['personnel/1','personnel/2'],['S-BS-STAFF']),
  ('P-02를 이번 과업에 0.5 FTE 더 배치하면 기존 업무와 충돌하는가?','기존 0.5와 신규 0.5의 합은 1.0 FTE로 원장 용량 범위다. 장애 대응 SLA나 실제 근무시간 충돌까지 검증한 것은 아니다.','capacity_only','PLAN',['personnel/1'],['S-BS-STAFF','A-BS-SLA']),
  ('공개 기술지원 협약 합계를 확보 견적으로 보고 투찰가를 확정해도 되는가?','아니다. 두 협약의 VAT 포함 합계 56,320,240원은 공개 참고액이며 C02 견적·확약서는 missing이다. 내부 민감도 계산은 가능하지만 총원가와 투찰가는 미확정이다.','missing_quote','QUOTE',['l3_policy'],['A-BS-AGREEMENT-1','A-BS-AGREEMENT-2','A-BS-CONFIRM'])],
 'C03':[
  ('인천 본점 요건을 단독 검토안에서 어떻게 확인하는가?','C03 본점은 인천 합성 설정이다. 이번 단독 대안은 기존 공동수급 지역 미충족 사례를 없애지 않는다. 개별 지역 조건만 검토하며 전체 적격 판정은 아니다.','condition_only','PROFILE',['headquarters'],['S-IC-REGION']),
      ('두 번째 블록체인 실적을 증빙 확보 완료로 세어도 되는가?','완료 실적 설정은 있으나 C03-PRJ-02의 증빙은 missing이다. 대장 생성으로 실제 실적 증명이 확보되지는 않는다.','missing_evidence','PERF',['projects/1'],['A-IC-PROOF']),
  ('6명의 직원 명부가 곧 제출 가능한 기술등급 증명인가?','아니다. 직무·경력 설정과 정식 기술등급·가입자 증빙은 다르다. 공고가 요구하는 제출 자료와 기술 평가 기준을 추가 대조해야 한다.','insufficient_evidence','STAFF',['personnel'],['A-IC-STAFF']),
  ('P-02의 신규 0.4 FTE 계획은 기존 0.5와 병행 가능한가?','겹치는 기간 합계는 0.9 FTE다. 용량 검사는 통과하지만 총괄책임자·기능 범위 및 발주처 승인은 미확정이다.','capacity_only','PLAN',['personnel/1'],['A-IC-STAFF']),
  ('인프라가 이미 있으므로 외부 비용을 0원으로 보고 투찰가를 정할 수 있는가?','아니다. 기존 인프라는 원문으로 확인했지만 상세 구성은 협의 후 열람이고 기능 범위도 협의 사항이다. 자체 인건비·합성 방문 경비만 계산하며 추가 비용과 총투찰가는 미확정이다.','unknown_not_zero','ESTIMATE',['l3_policy'],['A-IC-INFRA'])],
 'C04':[
  ('회사 ISO27001이 공급 서비스 CSAP 증빙을 대체하는가?','아니다. ISO27001은 회사 인증 기록이고 CSAP는 C04-SERVICE-01의 서비스 인증 항목으로 missing이다.','holder_boundary','CERT',['certifications/2','certifications/3','services/0'],['S-CL-CSAP']),
  ('서비스 설명 대장이 생겼으면 공급권한을 확보한 것인가?','아니다. 서비스의 supply_agreement_state는 missing이며 외부 업체 인증을 가상 서비스의 보유 증거로 붙일 수 없다.','missing_authority','CERT',['services/0'],['S-CL-CSAP']),
  ('ISMS 기준 준수 문구를 회사의 ISMS 인증 보유 요구로 확정해도 되는가?','해당 인용은 관리체계 기준 준수 요구다. 별도 인증 보유 조항 확인 없이 회사 인증 필수 조건으로 바꾸거나 ISO와 동일시하지 않는다.','requirement_scope','CERT',['certifications/2'],['S-CL-ISMS']),
  ('가격 산정의 7개월과 실제 계약 시작일은 같은 확정 사실인가?','아니다. 공고는 6월 1일~12월 31일 기준 7개월 가격 산정을 명시하나 지연 시 실제 개시일부터 정산한다. 현재 배치는 가격 기준 기간을 사용한 초안이다.','date_basis','PLAN',['personnel/6'],['A-CL-PERIOD']),
  ('서버 일부 공개 가격으로 전체 클라우드 원가를 확정할 수 있는가?','서버 외 스토리지·트래픽·보안·솔루션 조건까지 일치해야 한다. 자체 인력 원가만 계산됐고 전체 공급 견적과 총원가·투찰가는 null이다.','incomplete_scope','ESTIMATE',['l3_policy'],['A-CL-SPEC'])],
 'C05':[
  ('제조업 등록과 직접생산 품명 요건은 별도로 대조해야 하는가?','그렇다. 28123 제조업 등록과 3912110604 직접생산 인증은 서로 다른 레코드다. 원장의 각 증빙 상태와 공고 요건을 따로 확인하며 전체 적격을 확정하지 않는다.','separate_requirements','PROFILE',['registrations','certifications/1'],['S-EN-REG']),
  ('완료 EMS 실적 한 건이 평가 만점을 의미하는가?','아니다. C05-PRJ-01은 완료 및 합성 증빙 레코드가 있지만 참가요건의 실적과 평가 점수는 별도다. 인정 기간·내용·증빙을 대조해야 한다.','eligibility_not_score','PERF',['projects/0'],['S-EN-EXP']),
  ('PMS 완료 대장을 생성하면 두 번째 실적 증빙도 확보되는가?','아니다. C05-PRJ-02는 완료 설정과 별개로 증빙 상태가 missing이며 대장 생성으로 바뀌지 않는다.','missing_evidence','PERF',['projects/1'],['S-EN-EXP']),
  ('자체 인력 배치 초안이 하도급 허용 근거가 되는가?','아니다. 공고는 직접 수행과 하도급 불허를 명시한다. 초안은 기존 소속 인력의 배치이며 외부 하도급을 승인하지 않는다.','direct_execution','PLAN',['personnel/6','personnel/2'],['A-EN-DIRECT']),
  ('PC 두 세트 가격만 넣으면 장비 총액과 투찰가를 확정할 수 있는가?','아니다. PC 외 모니터·Office·랙·UPS·스위치 및 게이트웨이 3세트 등 요구 범위가 있다. 전체 동일 규격 견적은 missing이며 자체 인건비와 가정 경비 이외 총액은 미확정이다.','unknown_not_zero','QUOTE',['l3_policy'],['A-EN-SPEC'])]}


def qa_bindings(b,docs,sources):
    public={x['source_id']:x for x in sources}; questions=[]
    for cid in IDS:
        c,base=company(b,cid)
        for n,(question,answer,label,suffix,paths,sids) in enumerate(QA[cid],1):
            pointers=[base+'/'+x for x in paths];selected=[]
            # Common supporting documents may supplement the designated primary document.
            for d in docs:
                if d['company_id']!=cid:continue
                if d['template_id']!=f'{cid}-DOC-{suffix}' and d['scenario_id'] is not None:continue
                for ch in d['chunks']:
                    if any(f['master_pointer']==p or f['master_pointer'].startswith(p+'/') or p.startswith(f['master_pointer']+'/') for f in ch['source_fact_refs'] for p in pointers):
                        selected.append(dict(document_id=d['document_id'],document_version=d['document_version'],chunk_id=ch['chunk_id'],
                          company_id=cid,tenant_id=c['tenant_id'],security_level=d['security_level'],allowed_roles=d['allowed_roles'],
                          text_start=ch['text_start'],text_end=ch['text_end'],offset_unit=g.OFFSET,quote=ch['text'],master_fact_refs=ch['source_fact_refs']))
            # A primary document link is required even if its block references a broader company fact.
            v.require(any(e['document_id']==f'{cid}-{suffix}-{REV}' for e in selected),'primary QA evidence missing')
            questions.append(dict(question_id=f'QA-{cid}-R1-{n:02}',company_id=cid,tenant_id=c['tenant_id'],bid_key=BIDS[cid],
              notice_version='000',scenario_id=f'SC-{cid}-REVIEW-r1',question=question,expected_answer=answer,expected_status=label,
              required_role='cost_analyst' if suffix in ('QUOTE','ESTIMATE') else 'bid_analyst',
              must_not_claim=['전체 입찰 적격 확정','실제 기관 발급 증명서 확보','미확정 비용 0원','실제 RAG 성능 또는 환각 탐지 완료'],
              master_pointers=pointers,public_notice_evidence=[public[s] for s in sids],generated_company_evidence=selected,
              actual_answer=None,hallucination_spans=None,rag_ingest=False))
    return dict(version=REV,purpose='offline_evaluation_only',rag_ingest=False,questions=questions)


def validate(b,planned,docs,costs,qa,sources):
    v.validate_master(b['master'],b['schema'])
    v.require(planned==inputs(b),'planning input drift: review version and assumptions')
    expected,expected_costs,_,aug=build(b,planned)
    v.require(costs==expected_costs,'cost or margin calculation drift')
    v.require(len(docs)==36,'expected four times nine documents')
    for d,wanted in zip(docs,expected):
        v.validate_generated_document(d,aug)
        v.require(d==wanted,'master, text or metadata drift')
        for other in IDS+('C01',):
            v.require(other==d['company_id'] or other not in d['content'],'foreign company text')
        for key in ('expected_answer','expected_status','gold_label','must_not_claim'):
            v.require(key not in d['content'],'evaluation field in retrieval text')
    v.unique([x['chunk_id'] for d in docs for x in d['chunks']],'cross-document chunks')
    v.require(qa==qa_bindings(b,docs,sources),'QA content or evidence drift')
    checks=[]
    for d in docs:
        for tenant in ['astra-c01','astra-c02','astra-c03','astra-c04','astra-c05']:
            for role in ['bid_analyst','cost_analyst','bid_approver','viewer']:
                for auth,active in [(True,True),(False,True),(True,False)]:
                    session=dict(tenant_id=tenant,role=role,authenticated=auth,membership_active=active)
                    expected_allow=auth and active and tenant==d['tenant_id'] and role in d['allowed_roles']
                    for ch in d['chunks']:
                        v.require(v.can_access(session,ch)==expected_allow,'access boundary')
                    checks.append(dict(document_id=d['document_id'],session=session,allow=expected_allow,chunks=len(d['chunks'])))
    byid={d['document_id']:d for d in docs}
    for q in qa['questions']:
        v.require(all(e['bid_key']==q['bid_key'] for e in q['public_notice_evidence']),'QA wrong notice source')
        for e in q['generated_company_evidence']:
            d=byid[e['document_id']]
            v.require(d['content'][e['text_start']:e['text_end']]==e['quote'],'QA offset')
            v.require(v.can_access(dict(tenant_id=q['tenant_id'],role=q['required_role'],authenticated=True,membership_active=True),d),'QA unauthorized context')
    return dict(status='passed',documents=len(docs),chunks=sum(len(d['chunks']) for d in docs),qa_questions=len(qa['questions']),
      offline_access_chunk_checks=sum(x['chunks'] for x in checks),cases=checks)


def verify_source_files(sources,cache,source_root):
    """Optional original-file audit. Visual transcriptions have no fabricated text offsets."""
    items=json.loads(cache.read_text(encoding='utf-8'));checked=[]
    for s in sources:
        path=source_root/s['relative_source_path']
        v.require(hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'],'source original hash: '+s['source_id'])
        if s['text_start'] is not None:
            d=next(d for d in items if d['relative']==s['relative_source_path'])
            v.require(hashlib.sha256(d['text'].encode()).hexdigest()==s['text_sha256'],'source text hash')
            v.require(d['text'][s['text_start']:s['text_end']]==s['quote'],'source excerpt offset')
        else:
            v.require(s['page'] is not None and s['review_status']=='pdf_visual_checked','unlocated visual citation')
        checked.append(dict(source_id=s['source_id'],original_sha256_matched=True,
          text_offsets_matched=s['text_start'] is not None,visual_transcription_not_ocr_tested=s['text_start'] is None))
    return dict(status='passed',sources=len(checked),checks=checked,scope='원본 파일 해시와 추출 인용 자동 대조; 시각 전사는 에이전트의 별도 검토')


def artifacts(b,planned,sources):
    docs,costs,prov,_=build(b,planned);qa=qa_bindings(b,docs,sources);report=validate(b,planned,docs,costs,qa,sources)
    out={};all_entries=[]
    for cid in IDS:
        entries=[];schema=g.export_schema(b);schema['properties']['company_id']={'enum':[cid]}
        schema['$id']=f'urn:astra:{cid.lower()}-chunk-export:r1';schema['description']='회사별 원장·문서 버전 및 미적재 상태를 보존하는 JSONL 계약.'
        extra={key:{'type':['string','null']} for key in ('notice_id','notice_version','scenario_id','scenario_version')}
        schema['properties'].update(extra);schema['required']+=list(extra)
        out[f'{cid}/chunk_export.schema.json']=g.encoded(schema)
        for d in [d for d in docs if d['company_id']==cid]:
            stem=f'{cid}/{d["security_level"]}/{d["document_id"]}';rows=g.export_rows(d)
            for r in rows:
                r.update({key:d[key] for key in ('notice_id','notice_version','scenario_id')})
                r['scenario_version']=REV if d['scenario_id'] else None
            for r in rows:v.schema_check(r,schema)
            out[stem+'.md']=d['content'];out[stem+'.json']=g.encoded(d)
            out[stem+'.chunks.jsonl']=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows)
            entries.append(dict(document_id=d['document_id'],company_id=cid,tenant_id=d['tenant_id'],security_level=d['security_level'],
              allowed_roles=d['allowed_roles'],document_version=d['document_version'],notice_id=d['notice_id'],notice_version=d['notice_version'],
              scenario_id=d['scenario_id'],json_path=stem+'.json',markdown_path=stem+'.md',chunks_path=stem+'.chunks.jsonl',
              chunk_count=len(rows),content_sha256=hashlib.sha256(d['content'].encode()).hexdigest(),document_generation='generated',
              chunk_generation='generated',automated_validation='passed',human_approval='pending',review_status='unreviewed',rag_ingest=False,index_status='not_indexed'))
        out[f'{cid}/manifest.json']=g.encoded(dict(company_id=cid,documents=entries,path_base='C02-C05/r1',
          recursive_directory_ingest_allowed=False,retrieval_candidate_allowlist=[x['chunks_path'] for x in entries],
          evidence_registry=[dict(evidence_id=e['evidence_id'],master_status=e['status'],issued_evidence_document_generated=False)
                            for e in b['master']['evidence_registry'] if e['company_id']==cid]))
        all_entries+=entries
    out['evaluation/qa_pilot_20.json']=g.encoded(qa)
    out['evaluation/qa_pilot_20.md']='# 회사 4곳 검수 예제 20개\n\n평가 전용 · 검색 입력 금지 · 실제 답변/환각 구간 미생성\n\n'+'\n\n'.join(
      f'## {q["question_id"]} · {q["required_role"]}\n\n- 질문: {q["question"]}\n- 기대답: {q["expected_answer"]}\n- 원문: '+', '.join(e['source_id'] for e in q['public_notice_evidence'])+'\n- 생성 근거: '+', '.join(sorted({e['document_id'] for e in q['generated_company_evidence']})) for q in qa['questions'])+'\n'
    out['review/chunk_provenance.json']=g.encoded(dict(rag_ingest=False,purpose='audit_only_mixed_security',chunks=prov))
    out['review/cost_calculations.json']=g.encoded(dict(rag_ingest=False,companies=costs))
    out['review/external_price_review.json']=g.encoded(dict(rag_ingest=False,references=external_refs()))
    out['review/access_checks.json']=g.encoded(dict(scope='offline_metadata_policy_only',live_service_tested=False,cases=report.pop('cases')))
    out['manifest.json']=g.encoded(dict(version=REV,master_sha256=g.digest(b['master']),documents=all_entries,
      chunking=dict(strategy='one entity or scoped calculation per chunk; no overlap',max_characters=g.MAX_CHARS,offset_unit=g.OFFSET,
        token_count=None,reason='실적·인력·인증·원가 행의 조건을 한 덩어리로 유지. 임베딩 전 tokenizer 길이 확인 필요.'),
      recursive_directory_ingest_allowed=False,rag_ingest=False,index_status='not_indexed',human_approval='pending',
      retrieval_candidate_allowlist=[x['chunks_path'] for x in all_entries]))
    report.update(master_changed=False,c01_regression='verified by original byte check in main',
      limitations=['파일·메타데이터 검사이며 실제 RAG 검색 성능 및 서버 권한 검증이 아님','질문·기대답·근거만 생성; 모델 답변·환각 span 미생성',
        '원문 표·정본 인용과 합성 설정을 에이전트가 검토. 사람 승인은 pending','규격 전체·실제 공급권한·견적 미확정으로 모든 투찰금액 null'],
      per_company={cid:dict(documents=sum(d['company_id']==cid for d in docs),chunks=sum(len(d['chunks']) for d in docs if d['company_id']==cid)) for cid in IDS},
      external_llm_calls=0,db_writes=0,human_approval='pending',
      artifacts={k:hashlib.sha256(val.encode()).hexdigest() for k,val in out.items()})
    out['validation_report.json']=g.encoded(report)
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');ap.add_argument('--capture-sources',type=Path)
    ap.add_argument('--source-root',type=Path);ap.add_argument('--verify-sources',type=Path);a=ap.parse_args();b=v.load_bundle()
    if a.capture_sources:
        value=capture_sources(a.capture_sources,a.source_root);p=ROOT/'inputs/source_addenda.json';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(g.encoded(value).encode());print('Captured source addenda');return
    source=json.loads((ROOT/'inputs/source_addenda.json').read_text(encoding='utf-8'))
    if a.verify_sources:
        report=verify_source_files(b['sources']['references']+source['references'],a.verify_sources,a.source_root)
        (ROOT/'review/source_validation.json').write_bytes(g.encoded(report).encode())
        print(json.dumps(dict(status=report['status'],sources=report['sources'])));return
    planned=inputs(b);out=artifacts(b,planned,b['sources']['references']+source['references']);out['inputs/scenario_plans.json']=g.encoded(planned)
    g.write_or_check(b,g.DEFAULT_OUT,True)
    for name,content in out.items():
        p=ROOT/name
        if a.check:v.require(p.exists() and p.read_bytes()==content.encode(),'output drift: '+name)
        else:
            v.require(not p.exists() or p.read_bytes()==content.encode(),'immutable revision differs: '+name)
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content.encode())
    report=json.loads(out['validation_report.json']);print(json.dumps({k:report[k] for k in ('status','documents','chunks','qa_questions','per_company')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
