"""Foreground Linux CPU baseline server; terminate this process to stop its child."""
import argparse
import hashlib
import os
from pathlib import Path
import secrets
import signal
import subprocess

import rag_pilot as p


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--work',type=Path,default=p.ROOT/'work/rag-workstation-275')
    args=parser.parse_args();work=args.work.resolve()
    profile=p.read(work/'active_generation.json')
    model=work/profile['model_path']
    with model.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=profile['model_sha256']:
            raise ValueError('model SHA differs from selected profile')
    key=work/'server.token'
    if not key.exists():
        fd=os.open(key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(32))
    exe=work/'llama-b10938/llama-b10938/llama-server'
    cmd=[str(exe),'-m',str(model),'--alias',profile['alias'],'--host','127.0.0.1','--port','18767',
        '-c',str(profile['context']),'-np','1','-t','8','-tb','8','-b','128','-ub','32','-ngl','0',
        '--cache-ram','0','-fa','on','--cache-type-k',profile['cache_type'],'--cache-type-v',profile['cache_type'],
        '--no-cache-prompt','--no-context-shift','--no-webui','--api-key-file',str(key),
        '--cors-origins','http://127.0.0.1:18767','--no-cors-credentials']
    with (work/'server.log').open('a') as log:
        process=subprocess.Popen(cmd,cwd=work,stdout=log,stderr=subprocess.STDOUT)
        p.dump(work/'server-process.json',dict(pid=process.pid,parent_pid=os.getpid(),log=str(work/'server.log'),
            device='cpu',gpu_acceleration=False,executable=str(exe)))
        def stop(signum,frame):
            if process.poll() is None:process.terminate()
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        try: code=process.wait()
        finally:
            if process.poll() is None:
                process.terminate();process.wait(timeout=30)
            p.dump(work/'server-process.json',dict(pid=None,parent_pid=None,exit_code=process.returncode,log=str(work/'server.log')))
    raise SystemExit(code)


if __name__=='__main__':main()
