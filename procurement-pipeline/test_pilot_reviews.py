"""Regression and injected failures for returned review integration; no inference."""
import copy,json,unittest
from pathlib import Path
from import_pilot_reviews import BASE,OUT,load,validate,compare_protected,locate,dump

class ReviewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows=[json.loads(l) for l in (OUT/'adjudication_proposals.jsonl').read_text(encoding='utf-8').splitlines()]
  cls.base={r['question_id']:r for r in [json.loads(l) for l in (BASE/'labels_draft.jsonl').read_text(encoding='utf-8').splitlines()]}
 def rejected(self,mutate):
  rows=copy.deepcopy(self.rows);mutate(rows)
  with self.assertRaises(ValueError):validate(rows,self.base)
 def test_valid(self):self.assertTrue(validate(self.rows,self.base))
 def test_answer_change(self):self.rejected(lambda rs:rs[0].update(actual_answer=rs[0]['actual_answer']+'!'))
 def test_duplicate_question(self):self.rejected(lambda rs:rs.__setitem__(1,copy.deepcopy(rs[0])))
 def test_offset(self):self.rejected(lambda rs:rs[0]['proposed_spans'][0].update(start=0))
 def test_false_quote(self):self.rejected(lambda rs:rs[0]['proposed_spans'][0].update(quote='다른 문장'))
 def test_cross_tenant(self):self.rejected(lambda rs:rs[0].update(tenant_id='astra-c05'))
 def test_cross_company_evidence(self):self.rejected(lambda rs:rs[0]['evidence'][0].update(company_id='C05'))
 def test_unknown_evidence(self):self.rejected(lambda rs:rs[0]['proposed_spans'][0].update(evidence_ids=['missing']))
 def test_no_auto_approval(self):self.rejected(lambda rs:rs[0].update(human_approval='approved',approved_spans=[],training_ready=True))
 def test_span_approval(self):self.rejected(lambda rs:rs[0]['proposed_spans'][0].update(final_human_approval='approved'))
 def test_uncertain_not_positive(self):
  def mutation(rs):
   s=next(s for r in rs for s in r['proposed_spans'] if s['label']=='UNCERTAIN');s['hallucination_target']=True
  self.rejected(mutation)
 def test_missing_reviewer(self):self.rejected(lambda rs:rs[0]['review'].update(reviewer=''))
 def test_protected_actual_edit(self):
  with self.assertRaises(ValueError):compare_protected({'답변전문':{'C5':'0.5 FTE'}},{'답변전문':{'C5':'0.9 FTE'}})
 def test_boundary_whitespace_is_logged(self):
  diffs=compare_protected({'답변전문':{'C5':' text \n'}},{'답변전문':{'C5':'text'}})
  self.assertEqual(len(diffs),1);self.assertEqual(diffs[0]['kind'],'boundary_whitespace_restored_from_v1')
 def test_internal_whitespace_rejected(self):
  with self.assertRaises(ValueError):compare_protected({'답변전문':{'C5':'a b'}},{'답변전문':{'C5':'ab'}})
 def test_nonempty_extra_sheet(self):
  with self.assertRaises(ValueError):compare_protected({'검수목록':{}},{'검수목록':{},'Sheet7':{'A1':'unexpected'}})
 def test_occurrence_and_unicode(self):
  self.assertEqual(locate('😀가 가','가',2),(3,4))
 def test_review_coverage(self):
  report=load(OUT/'validation_report.json');self.assertEqual(report['question_count'],25);self.assertEqual(report['original_span_count'],68)
  self.assertEqual(report['reviewer_additions'],14);self.assertEqual(report['agent_additions'],6)
 def test_no_generation_or_training(self):
  for r in self.rows:self.assertFalse(r['training_ready']);self.assertIsNone(r['approved_spans'])

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReviewTests);res=unittest.TextTestRunner(verbosity=2).run(suite)
 dump(OUT/'test_report.json',dict(tests_run=res.testsRun,failures=len(res.failures),errors=len(res.errors),passed=res.wasSuccessful(),scope='Structural regression and injected corruption/approval/tenant failures; not semantic model accuracy'))
 raise SystemExit(not res.wasSuccessful())
