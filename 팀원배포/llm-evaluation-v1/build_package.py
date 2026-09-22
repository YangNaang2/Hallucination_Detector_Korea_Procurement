"""Build a source-only evaluation handoff. Does not run or download models."""
import collections,hashlib,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'work/delivery/ASTRA-LLM-evaluation-one-person.zip'

def main():
 tracked=subprocess.check_output(['git','-c','core.quotepath=false','ls-files','-z'],cwd=ROOT).decode().split('\0')
 files={}
 def add(rel,target=None):
  p=ROOT/rel
  if not p.is_file():raise FileNotFoundError(rel)
  files[target or rel]=p.read_bytes()
 for rel in tracked:
  p=Path(rel)
  if rel.startswith(('project-docs/평가데이터/v2/','project-docs/가상기업/v1/')) and p.suffix in {'.md','.json','.jsonl','.csv','.tsv'}:add(rel)
  if rel.startswith('procurement-pipeline/') and p.suffix in {'.py','.md','.txt','.ps1','.sh'}:add(rel)
 for name in ['요건추출시트_51건_통합.csv','51건_통합_검토내역.md','재확인_원문대조_결과.md','재확인_원문파일_식별.json']:
  add('project-docs/표본_정보시스템/검수/'+name)
 for name in ['README.md','SOURCE_TRANSFER.md','index_manifest.json','runtime/generation_profiles.json','runtime/requests.json']:
  add('project-docs/RAG파일럿/v1/'+name)
 for name in ['README.md','evaluation/effective_results.json','evaluation/effective_review.tsv','evaluation/final_summary.json','evaluation/repair_comparison.tsv','index_manifest.json','runtime/requests.json','embedding_config.json']:
  add('project-docs/RAG파일럿/workstation-275/'+name)
 for name in ['README.md','조정사항.md','adjudication_proposals.jsonl','submitted_reviews.jsonl']:
  add('project-docs/환각라벨링/pilot-25-human-review-v1/'+name)
 for rel in ['project-docs/프로젝트_진행현황_팀공유_2026-09-11.md','project-docs/데이터현황/3개월_통합현황.md']:add(rel)
 effective=json.loads((ROOT/'project-docs/RAG파일럿/workstation-275/evaluation/effective_results.json').read_text(encoding='utf-8'))
 records=effective['records']
 for rec in records:add(rec['record_path'])
 files['baseline/answers_300.jsonl']=(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records)).encode()
 qs=[json.loads(l) for l in (ROOT/'project-docs/평가데이터/v2/evaluation/questions_300.jsonl').read_text(encoding='utf-8').splitlines() if l]
 slots=[]
 for model in ['llama','qwen','exaone']:
  for q in qs:
   slots.append(dict(model_family=model,model_id=None,model_revision=None,run_id=None,question_id=q['question_id'],status='not_run',actual_answer=None,prompt_sha256=None,context_snapshot_sha256=None,finish_reason=None,error=None,ttft_seconds=None,generation_seconds=None,total_seconds=None,score=None,score_reason=None,human_approval='pending'))
 files['results_template.jsonl']=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in slots).encode()
 plan=dict(version='1.0.0',status='design_not_executed',assignee_count=1,model_candidates=['llama','qwen','exaone'],models_selected=False,primary_track='fixed-retrieval',rubric_version='1.0',questions=300,companies=dict(collections.Counter(q['company_id'] for q in qs)),notices=len({q['bid_key'] for q in qs}),categories=dict(collections.Counter(q['category'] for q in qs)),expected_actions=dict(collections.Counter(q['expected_action'] for q in qs)),slots_if_three_models=900,expected_generation_targets_if_acl_preserved=885,source_cache_included=False,index_included=False,model_weights_included=False,prior_results='mixed_conditions_reference_only',span_gold='not_finalized_for_new_answers')
 files['experiment_plan.json']=json.dumps(plan,ensure_ascii=False,indent=2).encode()
 for name in ['README.md','metrics.md','담당자_AI프롬프트.md','validate_package.py','validation.json']:
  files[name]=(HERE/name).read_bytes()
 manifest=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=[dict(path=k,size=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in sorted(files.items())])
 files['PACKAGE_MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in sorted(files.items()):z.writestr('ASTRA-LLM-evaluation/'+name,data)
 with zipfile.ZipFile(OUT) as z:assert z.testzip() is None
 digest=hashlib.sha256(OUT.read_bytes()).hexdigest();OUT.with_suffix('.zip.sha256').write_text(digest+'  '+OUT.name+'\n')
 print(json.dumps(dict(zip=str(OUT),files=len(files),bytes=OUT.stat().st_size,sha256=digest),ensure_ascii=False))
if __name__=='__main__':main()
