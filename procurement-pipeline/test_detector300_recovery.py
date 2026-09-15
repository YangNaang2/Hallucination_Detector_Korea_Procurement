"""Injection checks using the first frozen real record, without editing originals."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import detector300 as d

class Recovery(unittest.TestCase):
 def setUp(self):
  self.record=d.load(d.BASE/'selected_inputs.json')['records'][0]
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)
  # Minimal source fixture: no historical prompt reconstruction reached for injected corruption.
  e=self.record['prompt_evidence'][0]
  self.chunk=dict(chunk_id=e['chunk_id'],text='fixture',text_start=0,text_end=7,security_level='L1',sha256='source',document_id='doc',document_version='v')
  (self.path/'source.json').write_text(json.dumps([dict(sha256='source',text='fixture')]))
  (self.path/'index').write_text('readonly-fixture')
 def execute(self,chunk,allowed):
  connection=SimpleNamespace(execute=lambda sql:[(chunk['chunk_id'],json.dumps(chunk))],close=lambda:None)
  args=SimpleNamespace(index=self.path/'index',source_cache=self.path/'source.json',cache_root=self.path)
  with patch.object(d,'OUT',self.path/'out'),patch.object(d,'PRIVATE',self.path/'private'),patch.object(d,'frozen',return_value=[self.record]),patch.object(d.sqlite3,'connect',return_value=connection),patch('rag_pilot.eligible',return_value=allowed):d.recover(args)
  return d.load(self.path/'out/inputs/recovery.json')['records'][0]
 def test_wrong_company_acl_held(self):
  r=self.execute(self.chunk,[]);self.assertEqual(r['status'],'held');self.assertEqual(r['reason'],'ACL mismatch')
 def test_evidence_hash_held(self):
  r=self.execute(self.chunk,[self.chunk]);self.assertEqual(r['status'],'held');self.assertEqual(r['reason'],'chunk hash mismatch')
 def test_missing_records_frozen(self):
  import prepare_detector300_handoff as h
  changed=d.load(d.BASE/'selected_inputs.json');changed['records']=changed['records'][:-1]
  with patch.object(h,'build',return_value=changed):
   with self.assertRaises(AssertionError):d.frozen()
if __name__=='__main__':unittest.main()
