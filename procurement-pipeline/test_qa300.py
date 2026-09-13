"""Meaningful negative fixtures for v2; no model or network calls."""
import copy
import csv
import io
import json
import unittest

import build_qa300 as x
import validate_qa300 as check
import context_qa300 as ctx
import validate_company_master as v


class QA300Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=x.build();cls.b=v.load_bundle()

    def setUp(self):
        self.out=copy.deepcopy(self.original);self.qs=check.qrows(self.out);self.docs=check.newdocs(self.out)
        self.plans=self.out['scenarios/scenario_extensions.json']['scenarios']

    def invalid_q(self):
        with self.assertRaises(ValueError):check.check_questions(self.qs,self.docs,self.b)

    def invalid_docs(self):
        with self.assertRaises(ValueError):check.check_docs(self.docs,self.plans,self.b)

    def test_full_valid(self):
        self.assertEqual(check.validate(self.out)['questions'],300)
        for split in ('train','dev','test'):
            self.assertTrue(any(q['split']==split and q['calculation'] is not None for q in self.qs))
            self.assertTrue(any(q['split']==split and q['expected_action']=='접근 거절' for q in self.qs))

    def test_csv_roundtrip(self):
        rows=list(csv.DictReader(io.StringIO(self.out['evaluation/questions_300.csv'].removeprefix('\ufeff'))))
        self.assertEqual(len(rows),300)
        for a,b in zip(rows,self.qs):
            self.assertEqual(a['question_id'],b['question_id']);self.assertEqual(a['question'],b['question'])
            self.assertEqual(a['expected_answer'],b['expected_answer']);self.assertEqual(json.loads(a['company_evidence']),b['company_evidence'])
            self.assertEqual(json.loads(a['answer_evidence_excerpt']),b['answer_evidence_excerpt'])

    def test_missing_question(self):self.qs.pop();self.invalid_q()
    def test_duplicate_id(self):self.qs[1]['question_id']=self.qs[0]['question_id'];self.invalid_q()
    def test_duplicate_wording(self):self.qs[1]['question']=self.qs[0]['question'];self.invalid_q()
    def test_wrong_company_count(self):self.qs[0]['company_id']='C02';self.invalid_q()
    def test_wrong_notice_version(self):self.qs[0]['notice_version']='099';self.invalid_q()
    def test_wrong_answer_quote(self):
        q=next(q for q in self.qs if q['company_evidence']);q['company_evidence'][0]['quote']+='오류';self.invalid_q()
    def test_wrong_offset(self):self.docs[0]['chunks'][0]['text_start']+=1;self.invalid_docs()
    def test_foreign_tenant_doc(self):self.docs[0]['tenant_id']='astra-c05';self.invalid_docs()
    def test_foreign_pointer(self):self.docs[0]['chunks'][0]['source_fact_refs'][0]['master_pointer']='/companies/4/company_name';self.invalid_docs()
    def test_l3_pointer_in_l2(self):self.docs[0]['chunks'][0]['source_fact_refs'][0]['master_pointer']='/companies/0/l3_policy';self.invalid_docs()
    def test_l3_scenario_pointer_in_l2(self):self.docs[0]['chunks'][0]['scenario_fact_ref']['pointer']='/scenarios/0/calculation';self.invalid_docs()
    def test_foreign_scenario(self):self.docs[0]['chunks'][0]['scenario_fact_ref']['scenario_id']='SC-QA300-C05-A';self.invalid_docs()
    def test_expired_certificate_changed(self):
        self.plans[1]['state_change']['effective_from']='2026-04-01'
        with self.assertRaisesRegex(ValueError,'expired'):check.check_plan(self.plans[1],self.b)
    def test_csap_holder_company(self):
        self.plans[3]['state_change']['holder_type']='company'
        with self.assertRaisesRegex(ValueError,'holder'):check.check_plan(self.plans[3],self.b)
    def test_duplicate_fte(self):
        self.plans[1]['staffing'][0]['allocation_fte']['value']=.51
        with self.assertRaisesRegex(ValueError,'overlapping'):check.check_plan(self.plans[1],self.b)
    def test_vat_error(self):
        self.plans[0]['calculation']['target_gross']+=1
        with self.assertRaisesRegex(ValueError,'VAT'):check.check_plan(self.plans[0],self.b)
    def test_unit_price_error(self):
        self.plans[0]['prices'][0]['net']['value']+=1
        with self.assertRaisesRegex(ValueError,'multiplication'):check.check_plan(self.plans[0],self.b)
    def test_synthetic_price_as_real(self):
        self.plans[0]['prices'][0]['price_origin']='source_extracted'
        with self.assertRaisesRegex(ValueError,'masquerade'):check.check_plan(self.plans[0],self.b)
    def test_synthetic_certificate_as_real(self):
        self.plans[0]['state_change']['origin']='source_extracted'
        with self.assertRaisesRegex(ValueError,'masquerade'):check.check_plan(self.plans[0],self.b)
    def test_gold_field_in_doc(self):self.docs[0]['expected_answer']='정답';self.invalid_docs()
    def test_gold_field_in_text(self):self.docs[0]['content']+=' expected_answer';self.invalid_docs()
    def test_free_text_number_changed(self):
        ch=self.docs[0]['chunks'][0];ch['text']=ch['text'].replace('0036','0037')
        start,end=ch['text_start'],ch['text_end'];self.docs[0]['content']=self.docs[0]['content'][:start]+ch['text']+self.docs[0]['content'][end:]
        self.invalid_docs()
    def test_unapproved_index(self):self.docs[0]['rag_ingest']=True;self.invalid_docs()
    def test_denied_answer_contains_private_amount(self):
        next(q for q in self.qs if q['expected_action']=='접근 거절')['expected_answer']='권한 없지만 10,000원입니다.';self.invalid_q()
    def test_foreign_session_answer(self):
        q=next(q for q in self.qs if q['company_evidence']);q['user_context']['tenant_id']='astra-c05';self.invalid_q()
    def test_source_origin_forged(self):
        q=next(q for q in self.qs if q['public_notice_evidence']);q['public_notice_evidence'][0]['origin']='synthetic_setting';self.invalid_q()
    def test_bid_split_leak(self):
        self.qs[0]['split']='dev' if self.qs[0]['split']!='dev' else 'test';self.invalid_q()
    def test_model_completion_not_invented(self):self.qs[0]['actual_answer']='가짜 실행 답변';self.invalid_q()
    def test_state_dates(self):
        self.assertEqual(ctx.state_at(self.plans[1],'2026-04-01'),'expired_2026-03-31')
        self.assertEqual(ctx.state_at(self.plans[1],'2026-04-02'),'synthetic_record')
        self.assertEqual(ctx.state_at(self.plans[3],'2027-05-20'),'expired_synthetic_assumption')
    def test_missing_baseline_repaired(self):
        self.plans[2]['state_change']['baseline']='synthetic_record'
        with self.assertRaisesRegex(ValueError,'baseline'):check.check_plan(self.plans[2],self.b)
    def test_raw_quote_same_length_mutation(self):
        ref=dict(origin='source_extracted',bid_key='R26BK01234567-000',notice_id='R26BK01234567',notice_version='000',
          filename='fixture.txt',sha256='fixture',text_sha256=check.digest_bytes('abc'.encode()),quote='axc',text_start=0,text_end=3)
        with self.assertRaisesRegex(ValueError,'quote'):check.check_source(ref,[dict(bid=ref['bid_key'],name='fixture.txt',text='abc')])
    def test_missing_field_schema(self):
        q=copy.deepcopy(self.qs[0]);q.pop('user_context')
        with self.assertRaises(ValueError):v.schema_check(q,self.out['schemas/question.schema.json'])
    def test_cost_question_inconsistent(self):
        q=next(q for q in self.qs if q['calculation']);q['calculation']['target_net']+=1
        self.out['evaluation/questions_300.jsonl']=''.join(json.dumps(q,ensure_ascii=False)+'\n' for q in self.qs)
        with self.assertRaisesRegex(ValueError,'question calculation'):check.validate(self.out)
    def test_query_scope(self):
        session=dict(tenant_id='astra-c02',role='bid_analyst',authenticated=True,membership_active=True,allowed_security_levels=['L1','L2'])
        p=self.plans[1];docs=self.docs+[e['doc'] for e in x.documents().values()]
        selected=ctx.select(session,docs,'C02',p,'2026-06-01')['documents']
        self.assertTrue(selected)
        self.assertTrue(all(d['company_id']=='C02' and d['security_level']=='L2' for d in selected))
        self.assertFalse(any(d['document_id'].startswith('C02-CERT-') for d in selected))
        self.assertTrue(any('QA300-STATE' in d['document_id'] for d in selected))
        old=ctx.select(session,docs,'C02',p,'2026-04-01')['documents']
        self.assertFalse(any('QA300-STATE' in d['document_id'] for d in old))
        self.assertTrue(any(d['document_id'].startswith('C02-CERT-') for d in old))
    def test_future_request_excludes_gold_and_oracle_evidence(self):
        q=next(q for q in self.qs if q['private_audit_evidence'])
        request=ctx.evaluation_request(q)
        self.assertEqual(set(request),{'question_id','question','company_id','user_context','bid_key','scenario_id','scenario_version','decision_as_of'})
        q['expected_answer']='changed gold';q['private_audit_evidence']=['hidden']
        self.assertEqual(ctx.evaluation_request(q),request)


if __name__=='__main__':unittest.main()
