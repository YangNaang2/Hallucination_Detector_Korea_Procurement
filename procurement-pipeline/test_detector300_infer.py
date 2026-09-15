import unittest
import numpy as np
from detector300 import infer

class Tokenizer:
 def __call__(self,text,**kwargs):
  if kwargs.get('return_offsets_mapping'):
   return dict(input_ids=list(range(10000,10000+len(text))),offset_mapping=[(i,i+1) for i in range(len(text))])
  return dict(input_ids=list(range(len(text))))
class Detector:
 tok=Tokenizer();max_length=512;n_special=3
 def __init__(self):self.calls=[]
 def _forward(self,p,a):
  assert p and a and len(p)+len(a)+3<=512
  self.calls.append((p,a));return np.full(len(a),.6)
 def _aggregate(self,m):return m.min(axis=0)
class Inference(unittest.TestCase):
 def test_long_answer_preserves_context_unicode(self):
  det=Detector();answer='가🙂 e\u0301\n'*120;x=dict(actual_answer=answer,question='질문',context='근거'*600)
  r,t=infer(det,x)
  self.assertEqual(r['checked_ranges'],[[0,len(answer)]]);self.assertEqual(r['unchecked_ranges'],[])
  self.assertEqual(r['spans'][0]['quote'],answer)
  self.assertEqual(len(t),len(answer))
  for start in range(0,len(answer),192):
   calls=[p for p,a in det.calls if a[0]==10000+start]
   self.assertEqual(set(i for p in calls for i in p),set(range(r['prompt_tokens'])))
 def test_no_special_token_span(self):
  d=Detector();r,_=infer(d,dict(actual_answer='🙂',question='q',context='c'))
  self.assertEqual(r['spans'][0]['start'],0);self.assertEqual(r['spans'][0]['end'],1)
if __name__=='__main__':unittest.main()
