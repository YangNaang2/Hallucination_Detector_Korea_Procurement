import copy,json,unittest
from build_label_pilot import OUT,validate

class LabelChecks(unittest.TestCase):
    def setUp(self):self.rows=[json.loads(x) for x in (OUT/'labels_draft.jsonl').read_text(encoding='utf-8').splitlines()]
    def test_valid(self):self.assertTrue(validate(self.rows))
    def rejected(self,fn):
        r=copy.deepcopy(self.rows);fn(r)
        with self.assertRaises(AssertionError):validate(r)
    def test_offset_shift(self):self.rejected(lambda r:r[0]['draft_spans'][0].update(start=0))
    def test_answer_change(self):self.rejected(lambda r:r[0].update(actual_answer=r[0]['actual_answer']+'x'))
    def test_wrong_company(self):self.rejected(lambda r:r[0]['evidence'][0].update(company_id='C05'))
    def test_missing_evidence(self):self.rejected(lambda r:r[0]['draft_spans'][0].update(evidence_ids=['missing']))
    def test_false_approval(self):self.rejected(lambda r:r[0].update(human_approval='approved'))
    def test_premature_training(self):self.rejected(lambda r:r[0].update(training_ready=True))
    def test_duplicate(self):self.rejected(lambda r:r.__setitem__(1,copy.deepcopy(r[0])))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LabelChecks))
    (OUT/'test_report.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'scope':'structural checks and seven deliberate corruptions; not semantic correctness or human approval'},indent=2)+'\n',encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
