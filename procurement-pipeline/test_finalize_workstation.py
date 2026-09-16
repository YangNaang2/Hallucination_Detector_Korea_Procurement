import unittest
from finalize_workstation_rag import unique_rows, select_latest


class SelectionTests(unittest.TestCase):
    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            unique_rows([{'question_id':'q'}, {'question_id':'q'}])

    def test_newer_failure_cannot_be_hidden_by_old_success(self):
        old = {'q': {'status':'generated', 'answer':'old'}}
        new = {'q': {'status':'timeout', 'answer':None}}
        self.assertEqual(select_latest(old, new, ['q']), new)
        self.assertEqual(old['q']['answer'], 'old')

    def test_incomplete_or_expanded_override_scope_rejected(self):
        for initial, replacements, required in [({'q':1},{},['q']), ({'q':1},{'r':2},['r'])]:
            with self.assertRaises(ValueError):
                select_latest(initial, replacements, required)


if __name__ == '__main__':
    unittest.main()
