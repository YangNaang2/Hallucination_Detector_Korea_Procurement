"""Separate native-endpoint recovery pilot; never merged into the frozen chat run."""
import time
import detector_v6_generate as g
original_post=g.post
def recovery_post(route,payload):
 g.ENDPOINT='http://127.0.0.1:18769' if route=='/apply-template' else 'http://127.0.0.1:18771'
 return original_post(route,payload)
g.post=recovery_post
OUT=g.OUT/'generation_recovery_raw';WORK=g.WORK/'generation_recovery_raw'
def run():
 p=g.load(g.OUT/'generation_policy.json');policy=dict(parent_identity=g.jsha(p),run_id='v6-raw-recovery-1',server_flags='--no-jinja --chat-template chatml',endpoint='http://127.0.0.1:18771',rendering='original server /apply-template; exact original chat prompt preserved',route='/completion',seed=916,n_predict=512,temperature=0,top_k=40,top_p=1,min_p=0,source_sha256=g.file_sha(__file__),reason='two repeated peg-native chat parser failures; preserve raw completion; separate run and metrics');dest=OUT/'policy.json'
 if dest.exists():assert g.load(dest)==policy
 else:g.save(dest,policy)
 for q in ['ASTRA-300-C05-N18-E3','ASTRA-300-C05-N34-E2']:
  target=WORK/f'{q}.json'
  if target.exists():assert g.load(target)['identity']==g.jsha(policy);continue
  x=g.load(g.PRIVATE/'inputs'/f'{q}.json');messages=[dict(role='system',content=g.SYSTEM),dict(role='user',content='질문:\n'+x['question']+'\n\n실제 제공 근거:\n'+x['context'])];prompt=g.post('/apply-template',dict(messages=messages,chat_template_kwargs={'enable_thinking':False}))['prompt'];start=time.perf_counter();r=g.post('/completion',dict(prompt=prompt,temperature=0,top_k=40,top_p=1,min_p=0,seed=916,n_predict=512,cache_prompt=False,stream=False));g.save(target,dict(question_id=q,identity=g.jsha(policy),raw_response=r,context_sha256=x['context_sha256'],prompt_sha256=g.sha(prompt),seconds=time.perf_counter()-start));g.save(OUT/f'{q}.json',dict(question_id=q,identity=g.jsha(policy),raw_content_sha256=g.sha(r.get('content','')),context_sha256=x['context_sha256'],seconds=time.perf_counter()-start,content_length=len(r.get('content','')),stop=r.get('stop_type'),not_merged_into_parent=True));print(q,repr(r.get('content','')[:250]),flush=True)
if __name__=='__main__':run()
