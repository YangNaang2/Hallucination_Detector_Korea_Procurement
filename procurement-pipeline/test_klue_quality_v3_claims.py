import unittest
import klue_quality_v3_claims as c

class ClaimTests(unittest.TestCase):
 def test_independent_sentences_and_unicode(self):
  r={'offsets':[[0,1],[1,2],[3,4],[4,5]],'segments':[{'start':0,'end':4,'weights':[1],'probabilities':[[.8,.4,.1,.1]]}]}
  s=c.smooth(r,'가. 나.','min','sentence_mean')
  self.assertEqual(s['offsets'],r['offsets'])
  self.assertAlmostEqual(s['segments'][0]['probabilities'][0][0],.6)
  self.assertAlmostEqual(s['segments'][0]['probabilities'][0][2],.1)
 def test_raw_retains_window_aggregation(self):
  r={'offsets':[[0,1],[1,2]],'segments':[{'start':0,'end':2,'weights':[1,1],'probabilities':[[.8,.4],[.3,.6]]}]}
  self.assertEqual(c.smooth(r,'정상','min','raw')['segments'][0]['probabilities'][0],[.3,.4])
if __name__=='__main__':unittest.main()
