"""Bounded, resumable chat-completions jobs. Default: prepare only, no network."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error
from common import digest, records, save

from security_schema import SYSTEM, validate, assemble


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--packets',required=True)
    ap.add_argument('--out',default='generated')
    ap.add_argument('--model',default='local-model')
    ap.add_argument('--base-url',default='http://localhost:8000/v1')
    ap.add_argument('--execute',action='store_true')
    ap.add_argument('--workers',type=int,default=1)
    ap.add_argument('--limit',type=int,default=40)
    ap.add_argument('--max-input-bytes',type=int,default=45000)
    ap.add_argument('--max-output-tokens',type=int,default=3000)
    ap.add_argument('--retries',type=int,default=2)
    args=ap.parse_args()
    if not 1<=args.workers<=8 or args.limit<1 or args.retries<0:
        ap.error('workers 1..8, limit >= 1, retries >= 0')
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    jobs=[]
    for i,p in enumerate(records(args.packets)):
        if i>=args.limit: break
        messages=[dict(role='system',content=SYSTEM),dict(role='user',content=json.dumps(p,ensure_ascii=False))]
        size=len(json.dumps(messages,ensure_ascii=False).encode())
        if size>args.max_input_bytes:
            raise ValueError(f'input byte budget exceeded: {p["packet_id"]}; reduce prepare --max-chars')
        body=dict(model=args.model,messages=messages,temperature=0,max_tokens=args.max_output_tokens)
        key=digest({'body':body,'endpoint':args.base_url,'pipeline_version':2})
        jobs.append((key,p,body,size))
        save(out/'requests'/f'{key}.json',body)
    save(out/'plan.json',dict(jobs=len(jobs),execute=args.execute,
        max_attempts=len(jobs)*(args.retries+1),input_bytes=sum(j[3] for j in jobs),
        max_output_tokens_per_attempt=args.max_output_tokens,
        note='bytes are a payload cap, NOT a tokenizer count or price estimate'))
    if not args.execute:
        print(f'{len(jobs)} requests prepared, no LLM calls. Inspect requests/, then add --execute.')
        return
    url=args.base_url.rstrip('/')+'/chat/completions'
    if not url.startswith(('http://localhost:','http://127.0.0.1:','https://')):
        ap.error('use localhost HTTP or HTTPS')
    def run(job):
        key,p,body,size=job;target=out/'results'/f'{key}.json'
        if target.exists():
            cached=json.loads(target.read_text(encoding='utf-8'))
            if cached.get('packet_id')!=p['packet_id']:
                raise ValueError('cache packet mismatch')
            return dict(job=key,status='cached')
        for attempt in range(args.retries+1):
            try:
                headers={'Content-Type':'application/json'}
                token=os.environ.get('LLM_API_KEY')
                if token: headers['Authorization']='Bearer '+token
                req=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers,method='POST')
                with urllib.request.urlopen(req,timeout=180) as resp:
                    response=json.load(resp)
                choice=response['choices'][0]
                if choice.get('finish_reason')=='length':
                    raise ValueError('output truncated; increase output budget')
                raw=json.loads(choice['message']['content'])
                checked=validate(raw,p)
                product=assemble(checked,p)
                product['generation']={'job_id':key,'model':args.model,'usage':response.get('usage'),
                                       'attempt':attempt+1}
                save(target,product)
                return dict(job=key,status='ok')
            except (ValueError,KeyError,TypeError,urllib.error.URLError,TimeoutError) as exc:
                # Never log API credentials or full server response bodies.
                error=type(exc).__name__
                if attempt<args.retries: time.sleep(min(2**attempt,8))
        save(out/'errors'/f'{key}.json',dict(job=key,error=error,attempts=args.retries+1))
        return dict(job=key,status='failed',error=error)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        statuses=list(pool.map(run,jobs))
    save(out/'run_report.json',statuses)
    print({s:sum(r['status']==s for r in statuses) for s in ['ok','cached','failed']})
    if any(r['status']=='failed' for r in statuses): raise SystemExit(1)


if __name__=='__main__':main()
