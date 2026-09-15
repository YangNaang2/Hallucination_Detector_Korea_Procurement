import unittest
from detector300_labels import anchor_ref

class EvidenceAnchors(unittest.TestCase):
 def setUp(self):
  self.x={'context':'회사: C01\n\n[1] 공개 원문 A\n첫째 앵커\n[자료 1 끝]\n\n[2] 공개 원문 B\n🙂 둘째 앵커\n[자료 2 끝]',
   'evidence':[{'citation':1,'chunk_id':'a','text_sha256':'ha','text_start':10},
               {'citation':2,'chunk_id':'b','text_sha256':'hb','text_start':100}]}
 def test_citation_cannot_borrow_other_chunk(self):
  with self.assertRaises(ValueError):anchor_ref(self.x,'둘째',1)
 def test_header_is_not_evidence(self):
  with self.assertRaises(ValueError):anchor_ref(self.x,'회사: C01')
 def test_find_actual_citation_and_unicode_offsets(self):
  a=anchor_ref(self.x,'둘째')
  self.assertEqual((a['citation'],a['chunk_id'],a['source_start'],a['source_end']),(2,'b',102,104))
  self.assertEqual(self.x['context'][a['context_start']:a['context_end']],a['quote'])
 def test_table_reference_is_not_citation_boundary(self):
  self.x['context']=self.x['context'].replace('첫째 앵커','| source_ids [2] | key |\n첫째 앵커')
  a=anchor_ref(self.x,'둘째',2)
  self.assertEqual(a['source_start'],102)
  with self.assertRaises(ValueError):anchor_ref(self.x,'첫째',2)
if __name__=='__main__':unittest.main()
