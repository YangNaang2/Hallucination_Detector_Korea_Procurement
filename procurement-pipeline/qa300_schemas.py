"""Version 2 interchange contracts, using the repository's schema subset."""
def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
S={'type':'string','minLength':1};A={'type':'array'};B={'type':'boolean'};N={'type':'null'}
NS={'type':['string','null']};O={'type':'object'};NO={'type':['object','null']}


def schemas():
    props={k:S for k in ('question_id dataset_version company_id tenant_id bid_key notice_id notice_version scenario_id scenario_version decision_as_of category difficulty question expected_answer reasoning expected_action expected_status split decision_date_basis notice_name condition_scope source_nature').split()}
    props.update({k:A for k in ('evidence_kinds public_notice_evidence company_evidence private_audit_evidence master_pointers synthetic_evidence_ids scenario_pointers scenario_evidence_ids must_include must_not_claim assumptions unresolved_issues response_requirements').split()})
    props.update(expected_overall_eligibility=N,actual_answer=N,hallucination_spans=N,calculation=NO,reuse_of=NS,answer_evidence_excerpt=NS,rag_ingest={'type':'boolean','enum':[False]},review=O)
    props['user_context']=obj(dict(tenant_id=S,role=S,authenticated=B,membership_active=B,allowed_security_levels=A))
    props['company_id']={'type':'string','enum':['C01','C02','C03','C04','C05']}
    props['dataset_version']={'type':'string','enum':['2.0.0']}
    props['expected_action']={'type':'string','enum':['답변','조건부 답변','자료부족 안내','접근 거절']}
    props['split']={'type':'string','enum':['train','dev','test']}
    props['notice_version']={'type':'string','pattern':'^[0-9]{3}$'}
    q=obj(props);q.update(title='ASTRA question/expected answer/evidence v2',description='평가 전용. 실제 답변과 span은 null. 보안 증거는 관리자 전용으로 분리.')
    cp={k:S for k in ('chunk_id document_id document_version tenant_id security_level text offset_unit').split()}
    cp.update(allowed_roles=A,text_start={'type':'integer','minimum':0},text_end={'type':'integer','minimum':1},source_fact_refs=A,
      scenario_fact_ref=obj(dict(scenario_id=S,scenario_version=S,pointer=S)))
    dp={k:S for k in ('schema_version document_id document_version company_id tenant_id security_level master_dataset_id master_version scenario_id scenario_version notice_id notice_version review_status index_status human_approval content').split()}
    dp.update(allowed_roles=A,synthetic={'type':'boolean','enum':[True]},rag_ingest={'type':'boolean','enum':[False]},chunks={'type':'array','minItems':1,'items':obj(cp)})
    d=obj(dp);d.update(title='ASTRA synthetic scenario document v2',description='v1 문서 스키마를 변경하지 않고 scenario_fact_ref가 있는 새 문서에만 적용.')
    return {'schemas/question.schema.json':q,'schemas/generated_document.schema.json':d}
