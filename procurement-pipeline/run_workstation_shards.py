"""Fixed disjoint request shards, one shared local model, independent checkpoints."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import rag_pilot as p

OUT=p.ROOT/'project-docs/RAG파일럿/workstation-275'
WORK=p.ROOT/'work/rag-workstation-275'


def prepare(count):
    requests=p.read(OUT/'runtime/requests.json')
    if len(requests)!=275 or len({r['question_id'] for r in requests})!=275:raise ValueError('invalid 275 cohort')
    for request in requests:p.no_gold(request)
    shared=['index.sqlite','vectors.npz','query_vectors.npz','e5','qwen3','active_generation.json','server.token']
    for name in shared:
        if not (WORK/name).exists():raise ValueError('shared input missing: '+name)
    plan=dict(shards=count,selection_rule='Fixed sorted request order round-robin; no gold/category/answer routing.',
        items=[dict(shard=f'w{i+1}',question_ids=[r['question_id'] for r in requests[i::count]]) for i in range(count)])
    planfile=OUT/'runtime/shard_plan.json'
    if planfile.exists() and p.read(planfile)!=plan:raise ValueError('existing partition differs')
    for i in range(count):
        name=f'w{i+1}';out=OUT/'shards'/name;local=WORK/'shards'/name
        local.mkdir(parents=True,exist_ok=True)
        for relative in ['index_manifest.json','embedding_config.json']:
            target=out/relative;data=p.read(OUT/relative)
            if target.exists() and p.read(target)!=data:raise ValueError('shard index changed')
            p.dump(target,data)
        cohort=requests[i::count];target=out/'runtime/requests.json'
        if target.exists() and p.read(target)!=cohort:raise ValueError('existing shard requests changed')
        p.dump(target,cohort)
        for resource in shared:
            dest=local/resource
            if not dest.exists():dest.symlink_to(WORK/resource,target_is_directory=(WORK/resource).is_dir())
            elif dest.resolve()!=(WORK/resource).resolve():raise ValueError('unexpected shard resource')
    p.dump(planfile,plan)
    print('prepared',count,'disjoint shards', [len(x['question_ids']) for x in plan['items']])


def run(run_id,limit,retry):
    if not p.re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',run_id):raise ValueError('unsafe run ID')
    plan=p.read(OUT/'runtime/shard_plan.json');profile=p.read(WORK/'active_generation.json')
    if plan['shards']>profile.get('parallel_slots',1):raise ValueError('workers exceed server slots')
    children=[];logs=[]
    def stop(signum,frame):
        for child in children:
            if child.poll() is None:child.terminate()
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    try:
        for item in plan['items']:
            shard=item['shard'];log=WORK/f'{run_id}-{shard}.log';stream=log.open('a');logs.append(stream)
            cmd=[sys.executable,str(p.ROOT/'procurement-pipeline/workstation_rag.py'),'run',
                '--output',str(OUT/'shards'/shard),'--work',str(WORK/'shards'/shard),'--run-id',run_id]
            if limit is not None:cmd+=['--limit',str(limit)]
            if retry:cmd+=['--retry-failed']
            env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',OMP_NUM_THREADS='1')
            child=subprocess.Popen(cmd,cwd=p.ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
            children.append(child)
        p.dump(WORK/'coordinator.json',dict(run_id=run_id,pid=os.getpid(),children=[c.pid for c in children],
            shards=plan['shards'],limit_per_shard=limit,log_paths=[s.name for s in logs],
            pid_scope='This process namespace only; do not kill these numeric PIDs from another exec session.'))
        previous=None
        while any(c.poll() is None for c in children):
            counts={}
            for item in plan['items']:
                state=OUT/'shards'/item['shard']/'evaluation'/f'{run_id}-state.json'
                if state.exists():
                    data=p.read(state);counts[item['shard']]={}
                    for attempts in data['attempts'].values():
                        if attempts:
                            status=attempts[-1]['status'];counts[item['shard']][status]=counts[item['shard']].get(status,0)+1
            if counts!=previous:print(counts,flush=True);previous=counts
            time.sleep(5)
        codes=[c.wait() for c in children]
        p.dump(WORK/'coordinator.json',dict(run_id=run_id,pid=None,children=[],exit_codes=codes,log_paths=[s.name for s in logs]))
        if any(codes):raise SystemExit('worker failure: '+str(codes))
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for stream in logs:stream.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run']);ap.add_argument('--shards',type=int,default=4)
    ap.add_argument('--run-id',default='workstation275-v1');ap.add_argument('--limit',type=int);ap.add_argument('--retry-failed',action='store_true')
    args=ap.parse_args()
    if args.shards<1 or args.shards>4:ap.error('1-4 shards supported')
    if args.action=='prepare':prepare(args.shards)
    else:run(args.run_id,args.limit,args.retry_failed)
