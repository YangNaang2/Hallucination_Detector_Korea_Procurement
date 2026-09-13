"""Fidelity, isolation and boundary regressions for generated C01 ledgers."""
import copy
import tempfile
import unittest
from pathlib import Path

import generate_c01_documents as g
import validate_company_master as v


class DocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b=v.load_bundle();cls.docs=g.build_documents(cls.b)

    def reject(self,mutate):
        docs=copy.deepcopy(self.docs);mutate(docs)
        with self.assertRaises((ValueError,KeyError)):
            g.validate_documents(self.b,docs)

    def test_valid_documents(self):
        self.assertTrue(g.validate_documents(self.b,self.docs))

    def test_amount_boundary_and_atomic_entities(self):
        perf=self.docs[1]
        self.assertEqual(len(perf['chunks']),4)
        self.assertIn('70,000,000 KRW',perf['chunks'][0]['text'])
        self.assertIn('69,999,999 KRW',perf['chunks'][1]['text'])
        self.assertNotIn('C01-PRJ-02',perf['chunks'][0]['text'])
        self.assertIn('VAT 포함',perf['chunks'][0]['text'])

    def test_wrong_amount(self):
        self.reject(lambda ds:ds[1].update(content=ds[1]['content'].replace('69,999,999','70,000,000')))

    def test_missing_not_repaired(self):
        self.assertIn('| 증빙 확보 상태 | missing — 증빙 미확보 |',self.docs[1]['chunks'][2]['text'])
        self.reject(lambda ds:ds[1].update(content=ds[1]['content'].replace('| 증빙 확보 상태 | missing — 증빙 미확보 |','| 증빙 확보 상태 | 확인 완료 |')))

    def test_in_progress_not_completed(self):
        self.assertIn('in_progress — 진행 중',self.docs[1]['chunks'][3]['text'])
        self.assertIn('joint_total — 공동사업 전체 계약액',self.docs[1]['chunks'][3]['text'])

    def test_foreign_tenant_metadata(self):
        self.reject(lambda ds:ds[0]['chunks'][0].update(tenant_id='astra-c02'))

    def test_foreign_source_pointer(self):
        self.reject(lambda ds:ds[0]['chunks'][0]['source_fact_refs'][0].update(master_pointer='/companies/1/company_name'))

    def test_l3_pointer_in_l2(self):
        self.reject(lambda ds:ds[0]['chunks'][0]['source_fact_refs'][0].update(master_pointer='/companies/0/l3_policy'))

    def test_l3_text_in_l2(self):
        self.reject(lambda ds:ds[0].update(content=ds[0]['content']+'\n비공개 원가율 12%'))

    def test_expired_cert_not_shown_as_valid(self):
        b=copy.deepcopy(self.b);b['master']['companies'][0]['certifications'][1]['valid_until']='2026-03-31'
        fresh=g.build_documents(b)
        self.assertIn('유효 확인 불가 또는 만료',fresh[3]['chunks'][1]['text'])
        with self.assertRaises(ValueError):g.validate_documents(b,self.docs)

    def test_overallocated_personnel_rejected(self):
        b=copy.deepcopy(self.b);p=b['master']['companies'][0]['personnel'][0]
        extra=copy.deepcopy(p['existing_assignments'][0]);extra['assignment_id']='BAD-SECOND';p['existing_assignments'].append(extra)
        with self.assertRaises(ValueError):g.validate_documents(b,g.build_documents(b))

    def test_offset_mutation(self):
        self.reject(lambda ds:ds[0]['chunks'][0].update(text_end=2))

    def test_evidence_id_mutation(self):
        self.reject(lambda ds:ds[1]['chunks'][0]['source_fact_refs'][0].update(evidence_id='SYN-EV-C02-PRJ-01'))

    def test_copied_gold_field(self):
        self.reject(lambda ds:ds[0].update(expected_answer='answer'))

    def test_gold_has_no_influence_on_company_content(self):
        b=copy.deepcopy(self.b)
        for q in b['qa']['questions']:q['expected_answer']='POISON_GOLD';q['question']='POISON_QUESTION'
        b['mappings']={};b['sources']={}
        self.assertEqual(g.build_documents(b),self.docs)

    def test_qa_links_and_wrong_quote(self):
        links=g.bindings(self.b,self.docs)
        self.assertTrue(g.validate_bindings(self.b,self.docs,links))
        links['questions'][0]['generated_company_evidence'][0]['quote']='wrong'
        with self.assertRaises(ValueError):g.validate_bindings(self.b,self.docs,links)

    def test_qa_missing_company_fact(self):
        links=g.bindings(self.b,self.docs);links['questions'][3]['generated_company_evidence']=[]
        with self.assertRaises(ValueError):g.validate_bindings(self.b,self.docs,links)

    def test_qa_wrong_notice(self):
        links=g.bindings(self.b,self.docs);links['questions'][0]['bid_key']='R26BK01487327-001'
        with self.assertRaises(ValueError):g.validate_bindings(self.b,self.docs,links)

    def test_cost_is_partial_and_unknowns_remain_null(self):
        plan=g.plan_review(self.b)
        self.assertEqual(plan['cost_example']['value'],2436700)
        for key in ('period_person_months','supplier_quote_amount','total_direct_cost','total_cost','bid_price'):
            self.assertIsNone(plan[key])
        self.assertEqual(plan['execution_gate'],'blocked_not_a_submission_plan')

    def test_cost_chunks_preserve_vat_basis(self):
        for ch in self.docs[4]['chunks']:self.assertIn('VAT 제외',ch['text'])

    def test_chunk_access_policy(self):
        result=g.access_checks(self.docs)
        self.assertEqual(result['chunk_checks'],189)
        self.assertFalse(result['live_service_tested'])

    def test_state_and_evidence_file_separation(self):
        import json
        outputs=g.artifacts(self.b);m=json.loads(outputs['manifest.json'])
        for row in m['evidence_registry']:self.assertFalse(row['issued_evidence_document_generated'])
        for d in m['documents']:
            self.assertEqual(d['document_generation'],'generated')
            self.assertEqual(d['human_approval'],'pending');self.assertFalse(d['rag_ingest'])
        self.assertTrue(all('/' in p and not p.startswith(('evaluation/','review/')) for p in m['retrieval_input_allowlist']))

    def test_export_row_schema_rejects_gold_and_foreign_company(self):
        row=g.export_rows(self.docs[0])[0];schema=g.export_schema(self.b)
        v.schema_check(row,schema)
        for key,value in [('company_id','C02'),('expected_answer','leak')]:
            changed=copy.deepcopy(row);changed[key]=value
            with self.assertRaises(ValueError):v.schema_check(changed,schema)

    def test_reproducibility_and_jsonl_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);g.write_or_check(self.b,p);g.write_or_check(self.b,p,True)
            f=next(p.glob('L2/*.chunks.jsonl'));f.write_text(f.read_text(encoding='utf-8').replace('astra-c01','astra-c02'),encoding='utf-8')
            with self.assertRaises(ValueError):g.write_or_check(self.b,p,True)
            with self.assertRaises(ValueError):g.write_or_check(self.b,p)


if __name__=='__main__':unittest.main()
