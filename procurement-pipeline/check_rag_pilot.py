"""Persist regression and corpus integrity diagnostics; no claim of semantic safety."""
import io
import unittest
from collections import Counter
import rag_pilot as p


def main():
    chunks=p.load_chunks()
    questions=p.lines(p.V2/'evaluation/questions_300.jsonl')
    exact_matches=[]
    for q in questions:
        for c in chunks:
            if len(q['question'])>=20 and q['question'] in c['text']:
                exact_matches.append(dict(question_id=q['question_id'],chunk_id=c['chunk_id']))
    tests=unittest.TestSuite()
    for pattern in ['test_company_master.py','test_c01_documents.py','test_remaining_companies.py','test_qa300.py','test_rag_pilot.py']:
        tests.addTests(unittest.defaultTestLoader.discover(str(p.ROOT/'procurement-pipeline'),pattern=pattern))
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(tests)
    (p.OUT/'validation').mkdir(parents=True,exist_ok=True)
    (p.OUT/'validation/tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    p.dump(p.OUT/'validation/tests.json',dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
          passed=result.wasSuccessful(),exact_question_matches_in_corpus=exact_matches,
          corpus_records=len(chunks),corpus_record_hash='verified',
          source_note='원천 바이너리 해시·정본 offset 검사; 원본 OCR/표 파싱 완전성은 별도',
          automatic_scope='schema/IDs/amounts/ACL/tenant/scenario/offsets/gold-field isolation/whole-question literal matches',
          limitation='자유서술 의미상 환각·정보유출 또는 모델 지침 준수를 보장하지 않음.',
          human_approval='pending'))
    print('tests',result.testsRun,'passed',result.wasSuccessful(),'exact question matches',len(exact_matches),flush=True)
    if not result.wasSuccessful():raise SystemExit(1)


if __name__=='__main__':main()
