"""Freeze references to existing answers for detector evaluation; never run inference."""
import argparse,collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'project-docs/환각라벨링/detector-300-workstation-v1/selected_inputs.json'
def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def build():
 src=ROOT/'project-docs/RAG파일럿/workstation-275/evaluation/effective_results.json'
 data=json.loads(src.read_text(encoding='utf-8'));rows=[]
 qs=[json.loads(s) for s in (ROOT/'project-docs/평가데이터/v2/evaluation/questions_300.jsonl').read_text(encoding='utf-8').splitlines() if s]
 assert len(data['records'])==300
 for selected in data['records']:
  path=selected['record_path'];record=json.loads((ROOT/path).read_text(encoding='utf-8'));answer=record['actual_answer']
  assert record['status']==selected['status'] and answer==selected['actual_answer'],path
  assert digest(answer)==selected['answer_sha256'],path
  rows.append(dict(question_id=selected['question_id'],company_id=selected['company_id'],record_path=path,record_file_sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),answer_sha256=digest(answer),answer_codepoints=len(answer),status=record['status'],llm_called=record['llm_called'],source_run=record['run_id'],prompt_sha256=record.get('prompt_sha256'),prompt_version=record.get('prompt_version'),prompt_evidence=record.get('prompt_evidence',[]),detector_target=record['status']=='generated'))
 assert len({r['question_id'] for r in rows})==300
 assert {r['question_id'] for r in rows}=={q['question_id'] for q in qs}
 assert collections.Counter(r['status'] for r in rows)=={'generated':295,'access_denied':5}
 assert all(not r['llm_called'] for r in rows if r['status']=='access_denied')
 return dict(version='1.0.0',purpose='detector_comparison_on_existing_answers',question_count=300,generated_answers=295,system_denials=5,models=['klue','xlmr','bgem3'],planned_inference_slots=885,predictions_complete=False,human_gold_finalized=False,selection_file_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),records=rows)
def main():
 p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args();result=build()
 if a.check:assert json.loads(OUT.read_text(encoding='utf-8'))==result,'Frozen selection changed; investigate before new version'
 else:OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS 300 selected records: 295 generated + 5 non-LLM denials; canonical answer hashes and record references match. No detector run.')
if __name__=='__main__':main()
