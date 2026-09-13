"""Semantic fault injection and regression tests for the four-company expansion."""
import copy
import json
import unittest
from decimal import Decimal

import generate_c01_documents as g
import generate_remaining_companies as r
import validate_company_master as v


class RemainingCompanies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=v.load_bundle();cls.plans=r.inputs(cls.b)
        cls.sources=cls.b['sources']['references']+json.loads((r.ROOT/'inputs/source_addenda.json').read_text(encoding='utf-8'))['references']
        cls.docs,cls.costs,cls.prov,cls.aug=r.build(cls.b,cls.plans)
        cls.qa=r.qa_bindings(cls.b,cls.docs,cls.sources)

    def validate_changed(self,docs=None,costs=None,qa=None,plans=None):
        return r.validate(self.b,plans or self.plans,docs or self.docs,costs or self.costs,qa or self.qa,self.sources)

    def test_valid(self):
        result=self.validate_changed()
        self.assertEqual((result['documents'],result['chunks'],result['qa_questions']),(36,140,20))

    def test_c01_byte_regression(self):
        self.assertEqual(g.write_or_check(self.b,g.DEFAULT_OUT,True)['chunks'],27)

    def test_reproducible_and_gold_independent(self):
        altered=copy.deepcopy(self.b);altered['qa']={'questions':[{'expected_answer':'INJECTED GOLD'}]}
        docs,_,_,_=r.build(altered,self.plans)
        self.assertEqual(docs,self.docs)
        self.assertEqual(r.artifacts(self.b,self.plans,self.sources),r.artifacts(self.b,self.plans,self.sources))

    def test_foreign_tenant(self):
        docs=copy.deepcopy(self.docs);docs[0]['chunks'][0]['tenant_id']='astra-c05'
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_foreign_pointer(self):
        docs=copy.deepcopy(self.docs);docs[0]['chunks'][0]['source_fact_refs'][0]['master_pointer']='/companies/4/headquarters'
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_l2_l3_pointer(self):
        docs=copy.deepcopy(self.docs);docs[0]['chunks'][0]['source_fact_refs'][0].update(master_pointer='/companies/1/l3_policy',evidence_id='SYN-EV-C02-COST-POLICY')
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_l2_ancestor_pointer(self):
        docs=copy.deepcopy(self.docs);docs[0]['chunks'][0]['source_fact_refs'][0]['master_pointer']='/companies/1'
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_offset(self):
        docs=copy.deepcopy(self.docs);docs[0]['chunks'][0]['text_start']+=1
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_role_escalation(self):
        docs=copy.deepcopy(self.docs);d=next(d for d in docs if d['template_id']=='C04-DOC-BID')
        d['allowed_roles'].append('bid_analyst')
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_duplicate_fte(self):
        p=copy.deepcopy(self.plans['scenarios'][0]);p['staffing'][0]['allocation_fte']['value']=.51
        with self.assertRaises(ValueError):r.calculate(r.company(self.b,'C02')[0],p)

    def test_double_assignment(self):
        p=copy.deepcopy(self.plans['scenarios'][0]);p['staffing'].append(copy.deepcopy(p['staffing'][0]))
        with self.assertRaises(ValueError):r.calculate(r.company(self.b,'C02')[0],p)

    def test_employment_end(self):
        p=copy.deepcopy(self.plans['scenarios'][1]);p['staffing']=[copy.deepcopy(p['staffing'][-1])]
        p['staffing'][0]['end']='2027-01-01'
        with self.assertRaises(ValueError):r.calculate(r.company(self.b,'C03')[0],p)

    def test_wrong_cost(self):
        costs=copy.deepcopy(self.costs);costs['C02']['labor_net']['value']+=100
        with self.assertRaises(ValueError):self.validate_changed(costs=costs)

    def test_unknown_to_zero(self):
        costs=copy.deepcopy(self.costs);costs['C05']['supplier_quote_net']=0
        with self.assertRaises(ValueError):self.validate_changed(costs=costs)

    def test_expired_cert_positive(self):
        c,_=r.company(self.b,'C02');self.assertFalse(v.cert_valid(c['certifications'][2],'2026-04-01'))
        self.assertTrue(v.cert_valid(c['certifications'][1],'2026-04-24'))
        docs=copy.deepcopy(self.docs);d=next(d for d in docs if d['template_id']=='C02-DOC-CERT')
        d['content']=d['content'].replace('유효 확인 불가 또는 만료','현재 유효')
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_missing_evidence_forged(self):
        docs=copy.deepcopy(self.docs);d=next(d for d in docs if d['template_id']=='C03-DOC-PERF')
        d['content']=d['content'].replace('missing — 증빙 미확보','실제 증빙 확보 완료')
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_service_holder(self):
        c,_=r.company(self.b,'C04');cert=c['certifications'][3]
        self.assertEqual((cert['holder_type'],cert['holder_id'],cert['evidence_state']),('service','C04-SERVICE-01','missing'))
        d=next(d for d in self.docs if d['template_id']=='C04-DOC-CERT')
        service=d['chunks'][-1]
        self.assertEqual(service['source_fact_refs'],[{'master_pointer':'/companies/3/services/0','evidence_id':'SYN-EV-C04-CERT-04'}])

    def test_joint_share_not_double_applied(self):
        c,_=r.company(self.b,'C04');p=c['projects'][0]
        self.assertEqual((p['contract_amount']['gross']['value'],p['joint_share']['value'],p['amount_scope']),(154000000,40,'joint_total'))
        self.assertEqual(Decimal(p['contract_amount']['gross']['value'])*Decimal('.4'),Decimal(61600000))
        self.assertTrue(c['projects'][1]['subcontractor'])

    def test_prorata_and_labor(self):
        self.assertEqual(r.months('2026-12-01','2026-12-10'),[dict(month='2026-12',days=10,denominator=31,origin='calculated')])
        self.assertEqual(self.costs['C02']['labor_net']['value'],20515600) # 4,310,000 * .5 * 8 * 1.19
        self.assertEqual(self.costs['C02']['public_price_sensitivity']['original_agreement_gross']['value'],56320240)
        self.assertIsNone(self.costs['C02']['bid_price'])

    def test_margin_denominator(self):
        x=self.costs['C02']['public_price_sensitivity']
        # Revenue margin is division by .84, never cost times 1.16.
        approx=x['conditional_scope_cost_net']['value']/0.84
        self.assertLess(abs(x['conditional_target_net']['value']-approx),2)

    def test_gold_field_in_document(self):
        docs=copy.deepcopy(self.docs);docs[0]['content']+='\nexpected_answer: 통과\n'
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_qa_wrong_quote(self):
        qa=copy.deepcopy(self.qa);qa['questions'][0]['generated_company_evidence'][0]['quote']='위조 인용'
        with self.assertRaises(ValueError):self.validate_changed(qa=qa)

    def test_qa_foreign_source(self):
        qa=copy.deepcopy(self.qa);qa['questions'][0]['public_notice_evidence']=qa['questions'][10]['public_notice_evidence']
        with self.assertRaises(ValueError):self.validate_changed(qa=qa)

    def test_qa_l3_role(self):
        qa=copy.deepcopy(self.qa);qa['questions'][4]['required_role']='bid_analyst'
        with self.assertRaises(ValueError):self.validate_changed(qa=qa)

    def test_master_version(self):
        docs=copy.deepcopy(self.docs);docs[0]['master_version']='9.0.0'
        with self.assertRaises(ValueError):self.validate_changed(docs=docs)

    def test_planning_fact_change(self):
        plans=copy.deepcopy(self.plans);plans['scenarios'][0]['actual_contract_start']='2026-05-01'
        with self.assertRaises(ValueError):self.validate_changed(plans=plans)

    def test_all_fields_and_manifest_isolation(self):
        artifacts=r.artifacts(self.b,self.plans,self.sources);m=json.loads(artifacts['manifest.json'])
        self.assertFalse(m['recursive_directory_ingest_allowed'])
        for p in m['retrieval_candidate_allowlist']:
            self.assertTrue(p.endswith('.chunks.jsonl'));self.assertNotIn('evaluation',p)
            for row in map(json.loads,artifacts[p].splitlines()):
                self.assertFalse(row['rag_ingest']);self.assertEqual(row['index_status'],'not_indexed')
                self.assertIn('scenario_id',row);self.assertIn('notice_version',row)
        self.assertTrue(all(q['actual_answer'] is None and q['hallucination_spans'] is None for q in self.qa['questions']))


if __name__=='__main__':unittest.main()
