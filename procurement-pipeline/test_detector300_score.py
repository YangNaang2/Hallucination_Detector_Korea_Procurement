import copy,unittest
from detector300 import sha
from detector300_score import score_one,prf

class Scoring(unittest.TestCase):
 def fixture(self):
  a='가🙂 abc'
  l=dict(question_id='q',answer_sha256=sha(a),context_sha256='c',reviewed_ranges=[[0,len(a)]],spans=[dict(start=0,end=2,quote=a[:2],label='contradiction')])
  p=dict(answer_sha256=sha(a),context_sha256='c',checked_ranges=[[0,len(a)]],spans=[dict(start=0,end=2,quote=a[:2])])
  return a,l,p
 def test_unicode_exact(self):
  a,l,p=self.fixture();s=score_one(l,p,a);self.assertEqual(s['characters']['f1'],1);self.assertEqual(s['exact_spans']['tp'],1)
 def test_unknown_not_negative(self):
  a,l,p=self.fixture();l['reviewed_ranges']=[];l['spans']=None;self.assertIsNone(score_one(l,p,a))
 def test_citation_and_uncertain_mask(self):
  for label in ['citation_error','uncertain','quality_only']:
   a,l,p=self.fixture();l['spans'][0]['label']=label;s=score_one(l,p,a);self.assertEqual(s['characters']['fp'],0);self.assertEqual(s['masked_characters'],2)
 def test_partial_exact_not_clipped(self):
  a,l,p=self.fixture();p['checked_ranges']=[[1,len(a)]];s=score_one(l,p,a);self.assertEqual(s['characters']['tp'],1);self.assertEqual(s['exact_spans']['tp'],0);self.assertEqual(s['excluded_gold_spans'],1)
 def test_boundary_mismatch(self):
  a,l,p=self.fixture();p['spans']=[dict(start=0,end=1,quote=a[:1])];s=score_one(l,p,a);self.assertEqual(s['exact_spans']['tp'],0);self.assertEqual(s['characters']['fn'],1)
 def test_zero_policy(self):
  self.assertIsNone(prf(0,0,0)['f1']);self.assertIsNone(prf(0,0,2)['precision']);self.assertEqual(prf(0,0,2)['recall'],0)
 def test_changed_input(self):
  a,l,p=self.fixture();p['answer_sha256']='other'
  with self.assertRaises(ValueError):score_one(l,p,a)
 def test_changed_context(self):
  a,l,p=self.fixture();p['context_sha256']='other'
  with self.assertRaises(ValueError):score_one(l,p,a)
 def test_bad_offset(self):
  a,l,p=self.fixture();p['spans'][0]['end']=30
  with self.assertRaises(ValueError):score_one(l,p,a)
 def test_duplicate_does_not_double_count(self):
  a,l,p=self.fixture();p['spans']*=2;s=score_one(l,p,a);self.assertEqual(s['characters']['tp'],2);self.assertEqual(s['exact_spans']['tp'],1)
 def test_paired_domain(self):
  a,l,p=self.fixture();s=score_one(l,p,a,{1,2,3});self.assertEqual(s['scored_characters'],3);self.assertEqual(s['characters']['tp'],1)
if __name__=='__main__':unittest.main()
