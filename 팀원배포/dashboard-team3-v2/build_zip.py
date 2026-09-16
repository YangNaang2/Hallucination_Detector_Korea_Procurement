"""Allowlisted source ZIP, no raw files, weights, database, or keys."""
import hashlib,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/delivery/ASTRA-dashboard-team3.zip'

def main():
 files={}
 def add(path,target=None):
  p=ROOT/path
  if not p.is_file():raise FileNotFoundError(p)
  files[target or path]=p.read_bytes()
 code='demo-ui/spatial-poc/'
 for name in ['integrated_server.py','l1_server.py','detector_bridge.py','start_integrated.ps1','smoke_detector.py','smoke_live_integration.py','test_l1_server.py','test_integration.py','test-rag-http.mjs','test-rag-ux.mjs','test-detection-http.mjs']:
  add(code+name)
 for sub,ext in [('dist',{'.html','.css','.js','.mjs','.json','.svg'}),('internal-review',{'.html','.js','.css'}),('live-design',{'.mjs','.ts','.md'})]:
  for p in sorted((ROOT/code/sub).iterdir()):
   if p.is_file() and p.suffix in ext:add(p.relative_to(ROOT).as_posix())
 for name in ['rag_pilot.py','context_qa300.py','rag_pilot_routing.py','rag_pilot_calculation.py','validate_company_master.py','start_rag_pilot_server.ps1']:
  add('procurement-pipeline/'+name)
 for name in ['config.py','demo/detector.py']:add(name)
 for name in ['index_manifest.json','SOURCE_TRANSFER.md','runtime/generation_profiles.json']:add('project-docs/RAG파일럿/v1/'+name)
 for name in ['adjudication_proposals.jsonl','submitted_reviews.jsonl','intake_manifest.json','README.md','조정사항.md','통합검수목록.tsv','구절조정목록.tsv','received/T01.xlsx','received/T02.xlsx','received/T03.xlsx','received/T04.xlsx']:
  add('project-docs/환각라벨링/pilot-25-human-review-v1/'+name)
 for name in ['.env.example','requirements-detector.txt','checkpoints.json','detector-smoke.json','live-integration-smoke.json']:
  add('팀원배포/dashboard-integration-v1/'+name,name)
 add('팀원배포/dashboard-team3-v2/README.md','먼저읽기.md');add('팀원배포/dashboard-team3-v2/start.cmd','실행.cmd')
 info=dict(base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files=[dict(path=k,bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in sorted(files.items())],excludes=['weights','index DB','raw originals','keys','virtualenv'],members=3)
 files['PACKAGE_MANIFEST.json']=json.dumps(info,ensure_ascii=False,indent=2).encode()
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in sorted(files.items()):z.writestr('ASTRA-dashboard/'+name,data)
 with zipfile.ZipFile(OUT) as z:assert z.testzip() is None
 digest=hashlib.sha256(OUT.read_bytes()).hexdigest();OUT.with_suffix('.zip.sha256').write_text(digest+'  '+OUT.name+'\n')
 print(json.dumps(dict(zip=str(OUT),bytes=OUT.stat().st_size,files=len(files),sha256=digest),ensure_ascii=False))
if __name__=='__main__':main()
