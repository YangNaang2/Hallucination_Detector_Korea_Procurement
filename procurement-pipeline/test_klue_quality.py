import unittest
import numpy as np
from klue_quality import combine, lexical, protocol, OUT, BASE, file_sha
class Quality(unittest.TestCase):
 def test_aggregation_outlier(self):
  r={'offsets':[[0,1],[1,2]],'segments':[{'start':0,'end':2,'weights':[0,1,1],'probabilities':[[.01,.1],[.8,.9],[.9,.8]]}]}
  self.assertTrue(np.allclose(combine(r,'min'),[.01,.1]))
  self.assertTrue(np.allclose(combine(r,'min2'),[.8,.8]))
  self.assertTrue(np.all(combine(r,'relevance')>combine(r,'mean')))
 def test_overlap_max(self):
  r={'offsets':[[0,1]],'segments':[{'start':0,'end':1,'weights':[1],'probabilities':[[.2]]},{'start':0,'end':1,'weights':[1],'probabilities':[[.7]]}]}
  self.assertAlmostEqual(combine(r,'min')[0],.7)
 def test_protocol_groups_no_leakage(self):
  p=protocol()
  for g in p['groups']:self.assertEqual(len({p['split'][q] for q in g}),1)
  self.assertEqual(len(p['split']),295)
 def test_frozen_label_identity(self):
  self.assertEqual(protocol()['labels_sha256'],file_sha(BASE/'annotation/adjudicated/proposals.json'))
 def test_relevance_no_label(self):
  self.assertGreater(lexical('예산 금액','예산 금액 100원'),lexical('예산 금액','보안 자료 삭제'))
if __name__=='__main__':unittest.main()

class Rules(unittest.TestCase):
 def test_prohibition(self):
  from klue_quality_rules import rule_spans
  self.assertTrue(rule_spans('하도급이 가능합니다.','본 사업은 하도급 불가'))
 def test_exception_abstain(self):
  from klue_quality_rules import rule_spans
  self.assertFalse(rule_spans('하도급이 가능합니다.','원칙상 하도급 불가. 다만 승인 시 허용'))
 def test_negative_not_positive(self):
  from klue_quality_rules import rule_spans
  self.assertFalse(rule_spans('하도급은 불가능합니다.','하도급 불가'))
