import unittest
from detector300 import ranges, windows,validate_mapping,sha,jsha

class Contracts(unittest.TestCase):
 def test_mapping(self):
  for m in [{'0':'HALLUCINATED','1':'SUPPORTED'},{'0':'LABEL_0','1':'LABEL_1'}]:
   with self.assertRaises(ValueError):validate_mapping({'id2label':m,'architectures':['RobertaForTokenClassification']})
 def test_head(self):
  with self.assertRaises(ValueError):validate_mapping({'id2label':{'0':'SUPPORTED','1':'HALLUCINATED'},'architectures':['XLMRobertaModel']})
 def test_unicode_ranges(self):
  s='가🙂 e\u0301\n'; spans=ranges([0,1,1,4]);self.assertEqual(spans,[[0,2],[4,5]]);self.assertEqual(s[:2],'가🙂')
 def test_all_evidence_windows(self):
  for n in [1,2,191,192,193,512,2000]:
   for budget in [1,2,17,317]:
    w=windows(n,budget);self.assertEqual(set(range(n)),{i for a,b in w for i in range(a,b)});self.assertTrue(all(b-a<=budget for a,b in w))
 def test_canonical_hash(self):
  self.assertNotEqual(sha('가\n'),sha('가\r\n'));self.assertEqual(jsha({'a':1,'b':2}),jsha({'b':2,'a':1}))
 def test_unchecked_not_negative(self):
  self.assertEqual(ranges(set(range(5))-{0,1,4}),[[2,4]])
if __name__=='__main__':unittest.main()
