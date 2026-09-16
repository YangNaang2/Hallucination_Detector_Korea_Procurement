"""Exact public projection checks and meaningful corruption tests."""
import copy,hashlib,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=json.loads((ROOT/'demo-ui/spatial-poc/dist/rag-observatory.json').read_text(encoding='utf8'))
def validate(d):
 assert d['mode']=='saved_replay' and d['human_approval']=='pending'
 assert len(d['cases'])==4 and len({c['id'] for c in d['cases']})==4
 assert all(p['security_level']=='L1' and p['document_id'].startswith('L1-') for p in d['public_documents'])
 forbidden={'expected_answer','must_include','forbidden_claims','company_master','tenant_id','approved_spans'}
 def walk(v):
  if isinstance(v,dict):
   assert not forbidden&set(v)
   for x in v.values():walk(x)
  elif isinstance(v,list):
   for x in v:walk(x)
 walk(d)
 for c in d['cases']:
  assert c['human_approval']=='pending'
  assert hashlib.sha256(c['answer'].encode()).hexdigest()==c['answer_sha256']
  for x in c['contexts']:
   assert x['security_level']=='L1' and x['document_id'].startswith('L1-')
   assert x['text_end']-x['text_start']==len(x['text'])
   if x['scope']=='reference_only_not_in_prompt':assert x['citation'] is None
   else:assert x['scope']=='prompt_context' and isinstance(x['citation'],int)
  numbers=[x['citation'] for x in c['contexts'] if x['scope']=='prompt_context'];assert len(set(numbers))==len(numbers)
  for s in c['spans']:assert c['answer'][s['start']:s['end']]==s['quote']
class Tests(unittest.TestCase):
 def test_valid(self):validate(DATA)
 def reject(self,change):
  d=copy.deepcopy(DATA);change(d)
  with self.assertRaises(AssertionError):validate(d)
 def test_private_context(self):self.reject(lambda d:d['cases'][0]['contexts'][0].update(security_level='L2'))
 def test_foreign_document(self):self.reject(lambda d:d['cases'][0]['contexts'][0].update(document_id='C02-PRIVATE'))
 def test_offset(self):self.reject(lambda d:d['cases'][0]['contexts'][0].update(text_end=0))
 def test_answer(self):self.reject(lambda d:d['cases'][0].update(answer='정답으로 교체'))
 def test_span(self):self.reject(lambda d:d['cases'][0]['spans'][0].update(start=0))
 def test_answer_leak(self):self.reject(lambda d:d['cases'][0].update(expected_answer='leaked'))
 def test_supplement_as_input(self):self.reject(lambda d:d['cases'][-1]['contexts'][-1].update(citation=3))
 def test_fake_live(self):self.reject(lambda d:d.update(mode='live'))
if __name__=='__main__':unittest.main()
