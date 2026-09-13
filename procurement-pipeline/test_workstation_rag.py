import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import rag_pilot as p
import workstation_rag as w


class WorkstationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.old=(p.OUT,p.WORK,p.DB,w.FOLLOWUP,w.LOCAL)
        w.FOLLOWUP=self.root/'out'; w.LOCAL=self.root/'work'
        self.request=copy.deepcopy(p.read(w.BASE/'runtime/requests.json')[0])
        p.dump(w.FOLLOWUP/'runtime/requests.json',[self.request])
    def tearDown(self):
        p.OUT,p.WORK,p.DB,w.FOLLOWUP,w.LOCAL=self.old
        self.temp.cleanup()
    def test_windows_path_and_escape(self):
        self.assertEqual(p.safe_path(self.root,r'export\notice\file.hwp'),self.root/'export/notice/file.hwp')
        for value in (r'..\secret',r'C:\secret','/etc/passwd',r'\\server\share'):
            with self.assertRaises(ValueError):p.safe_path(self.root,value)
    def test_atomic_failed_serialization_preserves_old(self):
        file=self.root/'state.json';p.dump(file,{'complete':True})
        with self.assertRaises(TypeError):p.dump(file,{'invalid':object()})
        self.assertEqual(p.read(file),{'complete':True})
    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):w.unique([{'id':1},{'id':1}],'id')
    def test_prepare_real_set_difference_and_no_gold(self):
        w.FOLLOWUP=self.root/'prepared'
        w.prepare(p.V2/'evaluation/questions_300.jsonl')
        reqs=p.read(w.FOLLOWUP/'runtime/requests.json')
        self.assertEqual(len(reqs),275)
        old={r['question_id'] for r in p.read(w.BASE/'evaluation/effective_results.json')['records']}
        self.assertFalse(old & {r['question_id'] for r in reqs})
        for req in reqs:p.no_gold(req)
    def fake_run(self,run_id,**kwargs):
        p.dump(w.FOLLOWUP/f'evaluation/runs/{run_id}/{self.request["question_id"]}.json',
            dict(request=self.request,status='generated',actual_answer='mock',llm_called=True))
    def run_mocked(self,**kwargs):
        config=dict(generation={'model_path':'fake.gguf','model_sha256':'hash'},version=kwargs.pop('version',1))
        with patch.object(w,'fingerprint',return_value=config),patch.object(w,'sha',return_value='hash'),patch.object(p,'check_server'),patch.object(p,'load_chunks'),patch.object(p,'run',side_effect=self.fake_run) as run:
            w.run_batch('test',**kwargs)
            return run.call_count
    def test_resume_does_not_duplicate_success(self):
        self.assertEqual(self.run_mocked(),1)
        self.assertEqual(self.run_mocked(),0)
    def test_changed_config_rejected(self):
        self.run_mocked()
        with self.assertRaises(ValueError):self.run_mocked(version=2)
    def test_exception_record_and_explicit_retry(self):
        real=self.fake_run
        self.fake_run=lambda *args,**kwargs:(_ for _ in ()).throw(RuntimeError('private exception'))
        self.run_mocked()
        state=p.read(w.FOLLOWUP/'evaluation/test-state.json')
        attempt=state['attempts'][self.request['question_id']][-1]
        record=p.read(w.FOLLOWUP/attempt['record_path'])
        self.assertIsNone(record['actual_answer'])
        self.assertNotIn('private exception',str(record))
        self.assertEqual(self.run_mocked(),0)
        self.fake_run=real
        self.assertEqual(self.run_mocked(retry=True),1)
        self.assertTrue((w.FOLLOWUP/attempt['record_path']).exists())
    def test_interrupted_state_recovers_saved_record(self):
        self.run_mocked()
        path=w.FOLLOWUP/'evaluation/test-state.json';state=p.read(path)
        state['attempts'][self.request['question_id']][-1]['status']='running'
        p.dump(path,state)
        self.assertEqual(self.run_mocked(),0)
        self.assertEqual(p.read(path)['attempts'][self.request['question_id']][-1]['status'],'generated')

    def test_interrupted_http_checkpoint_is_not_completion(self):
        self.run_mocked()
        path=w.FOLLOWUP/'evaluation/test-state.json';state=p.read(path)
        attempt=state['attempts'][self.request['question_id']][-1]
        attempt['status']='running'
        result=w.FOLLOWUP/attempt['record_path'];record=p.read(result)
        record.update(status='generation_running',actual_answer=None)
        p.dump(result,record);p.dump(path,state)
        self.assertEqual(self.run_mocked(),0)
        self.assertEqual(p.read(result)['status'],'interrupted')
        self.assertIsNone(p.read(result)['actual_answer'])


if __name__=='__main__':unittest.main()
