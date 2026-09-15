import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import detector_v6_generate_parallel as run
from detector_v6_gemma_review import match
class RegenerationTests(unittest.TestCase):
 def test_only_question_and_evidence_are_sent(self):
  g=run.g
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);work=root/'work';out=root/'out';private=root/'private';calls=[]
   x=dict(question_id='q',question='질문',context='제공 근거',context_sha256=g.sha('제공 근거'),actual_answer='OLD_ANSWER_SECRET',expected_answer='GOLD_SECRET',evidence=[])
   path=private/'q.json';g.save(path,x);g.save(out/'generation_policy.json',dict(generator=dict(alias='local',context=4096),max_tokens=512))
   def post(route,payload):
    calls.append(str(payload))
    if route=='/apply-template':return {'prompt':'rendered'}
    if route=='/tokenize':return {'tokens':[1]}
    return {'choices':[{'message':{'content':'새로운 답변'},'finish_reason':'stop'}]}
   with patch.object(g,'WORK',work),patch.object(g,'OUT',out),patch.object(g,'post',post):
    self.assertEqual(run.one(path),('q','stop'));self.assertEqual(run.one(path),('q','skipped'))
   self.assertNotIn('OLD_ANSWER_SECRET',''.join(calls));self.assertNotIn('GOLD_SECRET',''.join(calls));self.assertEqual(g.load(path),x);self.assertEqual(g.load(work/'generated/q.json')['actual_answer'],'새로운 답변')
 def test_unicode_markdown_alignment(self):
  a,b,kind=match('조건은 **5일 이상** 입니다.','5일 이상');self.assertEqual('조건은 **5일 이상** 입니다.'[a:b],'5일 이상')
 def test_ambiguous_quote_is_held(self):
  with self.assertRaises(ValueError):match('5일 또는 5일','5일')
 def test_paraphrase_is_not_fake_exact_quote(self):
  with self.assertRaises(ValueError):match('승인이 필요합니다','승인 불필요')
if __name__=='__main__':unittest.main()
