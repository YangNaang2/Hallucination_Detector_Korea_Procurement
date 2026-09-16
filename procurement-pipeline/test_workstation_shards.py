from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import rag_pilot as p
import run_workstation_shards as s

class ShardTests(unittest.TestCase):
    def setup_tree(self,root):
        out=root/'out';work=root/'work';work.mkdir()
        requests=p.read(s.OUT/'runtime/requests.json')
        p.dump(out/'runtime/requests.json',requests)
        for name in ['index_manifest.json','embedding_config.json']:p.dump(out/name,{'corpus_hash':'test'})
        for name in ['index.sqlite','vectors.npz','query_vectors.npz','e5','qwen3','active_generation.json','server.token']:(work/name).touch()
        return out,work,requests
    def test_partition_covers_exact_275_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,work,requests=self.setup_tree(Path(tmp))
            with patch.object(s,'OUT',out),patch.object(s,'WORK',work):
                s.prepare(4);s.prepare(4)
                ids=[r['question_id'] for i in range(1,5) for r in p.read(out/f'shards/w{i}/runtime/requests.json')]
                self.assertEqual(len(ids),275);self.assertEqual(len(set(ids)),275)
                self.assertEqual(set(ids),{r['question_id'] for r in requests})
                with self.assertRaises(ValueError):s.prepare(2)
    def test_gold_field_in_shard_requests_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            out,work,requests=self.setup_tree(Path(tmp));requests[0]['expected_answer']='secret';p.dump(out/'runtime/requests.json',requests)
            with patch.object(s,'OUT',out),patch.object(s,'WORK',work):
                with self.assertRaises(ValueError):s.prepare(4)

if __name__=='__main__':unittest.main()
