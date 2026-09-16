import json,csv,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def validate():
 manifest=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
 for item in manifest['files']:
  p=(ROOT/item['path']).resolve()
  assert p.is_relative_to(ROOT.resolve()),'path outside package'
  assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'],item['path']
 qs=[json.loads(x) for x in (ROOT/'project-docs/평가데이터/v2/evaluation/questions_300.jsonl').read_text(encoding='utf-8').splitlines() if x]
 assert len(qs)==300 and len({x['question_id'] for x in qs})==300
 assert len({x['bid_key'] for x in qs})==51
 from collections import Counter
 assert dict(Counter(x['company_id'] for x in qs))=={f'C{i:02}':60 for i in range(1,6)}
 sheet=list(csv.DictReader((ROOT/'project-docs/표본_정보시스템/검수/요건추출시트_51건_통합.csv').open(encoding='utf-8-sig')))
 assert len(sheet)==51
 baseline=[json.loads(x) for x in (ROOT/'baseline/answers_300.jsonl').read_text(encoding='utf-8').splitlines()]
 assert {x['question_id'] for x in baseline}=={x['question_id'] for x in qs}
 assert Counter(x['status'] for x in baseline)=={'generated':295,'access_denied':5}
 slots=[json.loads(x) for x in (ROOT/'results_template.jsonl').read_text(encoding='utf-8').splitlines()]
 assert len(slots)==900 and all(x['actual_answer'] is None and x['status']=='not_run' for x in slots)
 for q in qs:
  for e in q.get('company_evidence',[]):
   assert (ROOT/e['document_path']).is_file(),e['document_path']
 print('PASS: file hashes, 51 sheet rows, 300 questions, 5 companies x 60, baseline 295+5, 900 empty slots, company evidence paths')
if __name__=='__main__':validate()
