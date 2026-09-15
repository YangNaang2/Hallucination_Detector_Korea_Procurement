import unittest
from klue_review_priority import measure,ranked
class ReviewPriorityTests(unittest.TestCase):
 def test_false_alarms_and_misses(self):
  m=measure({'a':.9,'b':.8,'c':.1,'d':.05},{'a':True,'b':False,'c':True,'d':False},.5)
  self.assertEqual((m['tp'],m['fp'],m['fn'],m['tn']),(1,1,1,1));self.assertEqual(m['recall'],.5)
 def test_budget_caps_recall(self):
  scores={str(i):float(i) for i in range(10)};m=measure(scores,{q:True for q in scores},.3)
  self.assertEqual(m['reviewed'],3);self.assertEqual(m['maximum_possible_recall'],.3)
 def test_ties_ignore_input_order(self):
  self.assertEqual(ranked({'a':1,'b':1}),ranked({'b':1,'a':1}))
 def test_zero_budget_and_no_positives(self):
  m=measure({'a':.9},{'a':False},0);self.assertIsNone(m['recall']);self.assertIsNone(m['precision']);self.assertEqual(m['reviewed'],0)
if __name__=='__main__':unittest.main()
