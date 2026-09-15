"""Two-worker execution of the unchanged v6 free-form generation policy."""
import concurrent.futures,json,time
import detector_v6_generate as g

def one(path):
 p=g.load(g.OUT/'generation_policy.json');identity=g.jsha(p);x=g.load(path);q=x['question_id'];dest=g.WORK/'generated'/f'{q}.json'
 if dest.exists():
  r=g.load(dest);assert r['identity']==identity and r['context_sha256']==x['context_sha256'];return q,'skipped'
 assert g.sha(x['context'])==x['context_sha256'];messages=[dict(role='system',content=g.SYSTEM),dict(role='user',content='질문:\n'+x['question']+'\n\n실제 제공 근거:\n'+x['context'])]
 try:
  rendered=g.post('/apply-template',dict(messages=messages,chat_template_kwargs={'enable_thinking':False}))['prompt'];tokens=len(g.post('/tokenize',dict(content=rendered))['tokens'])
  if tokens+p['max_tokens']+16>p['generator']['context']:raise ValueError(f'full evidence prompt too long: {tokens}')
  start=time.perf_counter();response=g.post('/v1/chat/completions',dict(model=p['generator']['alias'],messages=messages,temperature=0,top_p=1,top_k=40,min_p=0,seed=916,max_tokens=p['max_tokens'],stream=False,cache_prompt=False,chat_template_kwargs={'enable_thinking':False}));choice=response['choices'][0];answer=choice['message']['content'];assert answer.strip()
  r=dict(question_id=q,actual_answer=answer,answer_sha256=g.sha(answer),context_sha256=x['context_sha256'],question_sha256=g.sha(x['question']),identity=identity,prompt_sha256=g.sha(rendered),prompt_tokens=tokens,finish_reason=choice['finish_reason'],usage=response.get('usage'),seconds=time.perf_counter()-start,source_evidence=x['evidence'],execution_source_sha256=g.file_sha(__file__))
  g.save(dest,r);g.save(g.OUT/'generation_records'/f'{q}.json',{k:v for k,v in r.items() if k!='actual_answer'});return q,r['finish_reason']
 except Exception as e:
  g.save(g.WORK/'generation_failures'/f'{q}.json',dict(question_id=q,error_type=type(e).__name__,error=str(e),identity=identity));return q,'FAILED '+str(e)
if __name__=='__main__':
 p=g.load(g.OUT/'generation_policy.json');assert p['source_sha256']==g.file_sha(g.__file__);assert p['inputs_sha256']==g.file_sha(g.V1.parent/'selected_inputs.json')
 g.save(g.OUT/'generation_execution.json',dict(workers=2,source_sha256=g.file_sha(__file__),policy_identity=g.jsha(p),prior_sequential_records_preserved=True,sampling='same deterministic seed and payload; backend batching may cause numerical variation; per-record outputs frozen'))
 paths=sorted((g.PRIVATE/'inputs').glob('*.json'));assert len(paths)==295
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for i,result in enumerate(pool.map(one,paths)):print(i+1,result,flush=True)
