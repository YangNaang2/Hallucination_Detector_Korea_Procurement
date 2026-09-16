"""Mutation and boundary tests for the offline company design contract."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import validate_company_master as v


def access_cases(bundle):
    docs={d['document_id']:d for d in bundle['inventory']['documents']}
    public={'security_level':'L1','public':True}
    session=lambda tenant,role,auth=True,active=True: dict(tenant_id=tenant,role=role,authenticated=auth,membership_active=active)
    cases=[
        ('guest_public',{},public,True),
        ('guest_nonpublic_L1',{},dict(security_level='L1',public=False),False),
        ('guest_L2',{},docs['C01-DOC-PERF'],False),
        ('own_viewer_L2',session('astra-c01','viewer'),docs['C01-DOC-PERF'],False),
        ('own_analyst_L2',session('astra-c01','bid_analyst'),docs['C01-DOC-PERF'],True),
        ('own_cost_analyst_L2',session('astra-c01','cost_analyst'),docs['C01-DOC-PERF'],True),
        ('own_approver_L2',session('astra-c01','bid_approver'),docs['C01-DOC-PERF'],True),
        ('foreign_analyst_L2',session('astra-c02','bid_analyst'),docs['C01-DOC-PERF'],False),
        ('foreign_approver_L2',session('astra-c02','bid_approver'),docs['C01-DOC-PERF'],False),
        ('own_analyst_cost',session('astra-c01','bid_analyst'),docs['C01-DOC-COST'],False),
        ('own_cost_analyst_cost',session('astra-c01','cost_analyst'),docs['C01-DOC-COST'],True),
        ('own_approver_cost',session('astra-c01','bid_approver'),docs['C01-DOC-COST'],True),
        ('foreign_approver_cost',session('astra-c02','bid_approver'),docs['C01-DOC-COST'],False),
        ('cost_analyst_strategy',session('astra-c01','cost_analyst'),docs['C01-DOC-BID'],False),
        ('approver_strategy',session('astra-c01','bid_approver'),docs['C01-DOC-BID'],True),
        ('inactive_membership',session('astra-c01','bid_approver',active=False),docs['C01-DOC-BID'],False),
        ('unauthenticated_role',session('astra-c01','bid_approver',auth=False),docs['C01-DOC-BID'],False),
        ('unknown_role',session('astra-c01','admin'),docs['C01-DOC-BID'],False),
        ('missing_tenant',session(None,'bid_approver'),docs['C01-DOC-BID'],False),
        ('unknown_level',session('astra-c01','bid_approver'),dict(security_level='L4',tenant_id='astra-c01',allowed_roles=['bid_approver']),False),
    ]
    return [dict(case_id=name,session=s,document_id=d.get('document_id',name),
                 expected=expected,actual=v.can_access(s,d)) for name,s,d,expected in cases]


class CompanyMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=v.load_bundle()

    def rejects(self, change):
        b=copy.deepcopy(self.base); change(b)
        with self.assertRaises((ValueError,KeyError,IndexError)):
            v.validate_bundle(b)

    def test_valid_bundle(self):
        self.assertEqual(v.validate_bundle(self.base)['status'],'passed')

    def test_csv_content_change_not_accepted_as_line_ending_change(self):
        original = Path.read_bytes
        target = v.REPO / self.base['analysis']['input_files'][0]['path']
        def mutated(path):
            data = original(path)
            return data + b'changed' if path == target else data
        with patch.object(Path, 'read_bytes', mutated):
            with self.assertRaisesRegex(ValueError, 'input CSV changed'):
                v.validate_bundle(self.base)

    def test_duplicate_person(self):
        self.rejects(lambda b:b['master']['companies'][0]['personnel'][1].update(person_id='C01-P-01'))

    def test_pre_founding_project(self):
        self.rejects(lambda b:b['master']['companies'][0]['projects'][0].update(contracted_on='2010-01-01'))

    def test_career_after_joining(self):
        self.rejects(lambda b:b['master']['companies'][0]['personnel'][0].update(career_started_on='2025-01-01'))

    def test_completion_after_snapshot(self):
        self.rejects(lambda b:b['master']['companies'][0]['projects'][0].update(completed_on='2026-08-01'))

    def test_invalid_calendar_date(self):
        self.rejects(lambda b:b['master']['companies'][0].update(founded_on='2014-02-30'))

    def test_bad_vat(self):
        self.rejects(lambda b:b['master']['companies'][0]['projects'][0]['contract_amount']['vat'].update(value=1))

    def test_wrong_headcount(self):
        self.rejects(lambda b:b['master']['companies'][0]['headcount'].update(value=13))

    def test_missing_certificate_cannot_gain_dates(self):
        self.rejects(lambda b:b['master']['companies'][3]['certifications'][3].update(valid_until='2030-01-01'))

    def test_certificate_date_boundaries(self):
        cert=next(x for x in self.base['master']['companies'][1]['certifications'] if x['code']=='8111159901')
        self.assertTrue(v.cert_valid(cert,'2026-03-31'))
        self.assertFalse(v.cert_valid(cert,'2026-04-01'))

    def test_service_certificate_wrong_holder(self):
        self.rejects(lambda b:b['master']['companies'][3]['certifications'][3].update(holder_id='C04'))

    def test_foreign_evidence(self):
        self.rejects(lambda b:b['master']['companies'][0]['projects'][0].update(evidence_id='SYN-EV-C02-PRJ-01'))

    def test_bad_margin(self):
        self.rejects(lambda b:b['master']['companies'][0]['l3_policy']['target_gross_margin'].update(value=100))

    def test_staff_overlap(self):
        def change(b):
            p=b['master']['companies'][0]['personnel'][0]
            extra=copy.deepcopy(p['existing_assignments'][0]);extra['assignment_id']='C01-P-01-A02'
            extra['allocation_fte']['value']=.1;p['existing_assignments'].append(extra)
        self.rejects(change)

    def test_capacity_exact_boundary_and_one_extra(self):
        person=copy.deepcopy(self.base['master']['companies'][1]['personnel'][1])
        extra=dict(start='2026-05-01',end='2026-12-31',allocation_fte=dict(value=.5))
        v.validate_capacity(person,[extra])
        extra['allocation_fte']['value']=.51
        with self.assertRaises(ValueError):v.validate_capacity(person,[extra])

    def test_scenario_foreign_person(self):
        self.rejects(lambda b:b['plans']['scenarios'][0]['staffing'][0].update(person_id='C02-P-03'))

    def test_joint_share_sum(self):
        self.rejects(lambda b:b['plans']['scenarios'][1]['joint_members'][0]['share'].update(value=81))

    def test_mapping_source_wrong_notice(self):
        self.rejects(lambda b:b['mappings']['mappings'][0].update(source_ids=['S-CL-CSAP']))

    def test_visual_reference_rejects_fake_offset(self):
        self.rejects(lambda b:next(r for r in b['sources']['references'] if r['source_id']=='S-IC-REGION').update(text_start=100))

    def test_joint_amount_scope(self):
        self.rejects(lambda b:b['master']['companies'][0]['projects'][3].update(amount_scope='company_contract'))

    def test_mapping_cannot_claim_eligible(self):
        self.rejects(lambda b:b['mappings']['mappings'][0].update(overall_eligibility=True))

    def test_boundary_tracks_master_amount(self):
        self.rejects(lambda b:b['mappings']['mappings'][0]['comparison']['left'].update(value=70000001))

    def test_planned_document_not_ingested(self):
        self.rejects(lambda b:b['inventory']['documents'][0].update(rag_ingest=True))

    def test_l3_pointer_in_l2(self):
        self.rejects(lambda b:b['inventory']['documents'][0].update(master_pointers=['/companies/0/l3_policy']))

    def test_gold_isolation(self):
        self.rejects(lambda b:b['qa'].update(rag_ingest=True))

    def test_span_label_not_invented(self):
        self.rejects(lambda b:b['qa']['questions'][0].update(hallucination_spans=[]))

    def test_access_matrix(self):
        cases=access_cases(self.base)
        self.assertEqual(len(cases),20)
        for case in cases:
            with self.subTest(case=case['case_id']):self.assertIs(case['actual'],case['expected'])

    def fixture_document(self):
        template=self.base['inventory']['documents'][0]
        text='가상 기업 기준 정보'
        d=dict(schema_version='1.0.0',document_id='C01-PROFILE-test',template_id=template['document_id'],
          document_version='test-1',master_version='1.0.0',master_dataset_id=self.base['master']['dataset_id'],company_id='C01',tenant_id='astra-c01',
          security_level='L2',allowed_roles=template['allowed_roles'],synthetic=True,kind='company_profile',
          title='가상 테스트 문서',content=text,notice_id=None,notice_version=None,scenario_id=None,
          review_status='unreviewed',rag_ingest=False,chunks=[])
        d['chunks']=[dict(chunk_id='test-chunk-1',document_id=d['document_id'],document_version=d['document_version'],tenant_id=d['tenant_id'],
          security_level=d['security_level'],allowed_roles=d['allowed_roles'],text=text,text_start=0,text_end=len(text),
          offset_unit='Unicode code point, end exclusive',source_fact_refs=[dict(master_pointer='/companies/0/headquarters',evidence_id='SYN-EV-C01-HQ')])]
        return d

    def test_future_document_contract(self):
        self.assertTrue(v.validate_generated_document(self.fixture_document(),self.base))

    def test_future_document_rejects_mixed_tenant(self):
        d=self.fixture_document();d['chunks'][0]['tenant_id']='astra-c02'
        with self.assertRaises(ValueError):v.validate_generated_document(d,self.base)

    def test_future_document_rejects_answer_field(self):
        d=self.fixture_document();d['expected_answer']='gold leaked'
        with self.assertRaises(ValueError):v.validate_generated_document(d,self.base)

    def test_future_document_rejects_unreviewed_ingest(self):
        d=self.fixture_document();d['rag_ingest']=True
        with self.assertRaises(ValueError):v.validate_generated_document(d,self.base)

    def test_future_document_rejects_wrong_offset(self):
        d=self.fixture_document();d['chunks'][0]['text_end']-=1
        with self.assertRaises(ValueError):v.validate_generated_document(d,self.base)


if __name__=='__main__':
    unittest.main()
