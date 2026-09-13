"""Run in the user's HOST terminal: pinned Vulkan GPU model, loopback only.

No package installation, driver changes, reboot or shell interpolation. Ctrl-C stops
only this launcher's model process. Raw logs and GPU samples remain ignored work.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import signal
import subprocess
import threading
import time
import urllib.request

import rag_pilot as p


def main():
    work=p.ROOT/'work/rag-workstation-275';exe=work/'llama-vulkan/llama-b10938/llama-server'
    devices=subprocess.run([str(exe),'--list-devices'],capture_output=True,text=True,check=True)
    (work/'gpu-devices.txt').write_text(devices.stdout+devices.stderr)
    match=re.search(r'\b(Vulkan\d+)\s*:\s*[^\n]*NVIDIA',devices.stdout+devices.stderr)
    if not match:
        raise SystemExit('NVIDIA Vulkan device not available. See work/rag-workstation-275/gpu-devices.txt')
    gpu_device=match.group(1)
    profile=p.read(p.ROOT/'project-docs/RAG파일럿/v1/runtime/generation_profiles.json')['qwen3-4b']
    profile.update(alias='qwen3-4b-vulkan',endpoint='http://127.0.0.1:18769',
        batch=512,ubatch=512,threads=8,cache_type='f16',parallel_slots=4,
        backend='Vulkan',device=gpu_device,gpu_layers=999,profile_version='workstation-vulkan-v1')
    model=work/profile['model_path']
    with model.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=profile['model_sha256']:raise ValueError('model hash mismatch')
    key=work/'server.token'
    if not key.exists():
        fd=os.open(key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(32))
    logpath=work/'gpu-server.log'
    cmd=[str(exe),'-m',str(model),'--alias',profile['alias'],'--host','127.0.0.1','--port','18769',
        '-c','16384','-np','4','-ngl','999','--device',gpu_device,'-t','8','-tb','8','-b','512','-ub','512',
        '--cache-ram','0','-fa','on','--cache-type-k','f16','--cache-type-v','f16',
        '--no-cache-prompt','--no-context-shift','--no-webui','--api-key-file',str(key),
        '--cors-origins',profile['endpoint'],'--no-cors-credentials','--verbosity','5']
    done=threading.Event()
    def sample_gpu():
        with (work/'gpu-metrics.csv').open('a') as output:
            while not done.is_set():
                result=subprocess.run(['nvidia-smi','--query-gpu=timestamp,name,memory.total,memory.used,utilization.gpu,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True)
                output.write(result.stdout);output.flush();done.wait(2)
    sampler=threading.Thread(target=sample_gpu,daemon=True);sampler.start()
    with logpath.open('a') as log:
        process=subprocess.Popen(cmd,cwd=work,stdout=log,stderr=subprocess.STDOUT)
        p.dump(work/'gpu-server-process.json',dict(pid=process.pid,parent_pid=os.getpid(),scope='host',status='loading',log=str(logpath)))
        def stop(signum,frame):
            if process.poll() is None:process.terminate()
        signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
        try:
            for _ in range(120):
                if process.poll() is not None:raise RuntimeError('GPU server exited; inspect '+str(logpath))
                try:
                    req=urllib.request.Request(profile['endpoint']+'/v1/models',headers={'Authorization':'Bearer '+key.read_text().strip()})
                    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=2) as response:models=json.load(response)
                    if profile['alias'] in {m['id'] for m in models['data']}:break
                except Exception:time.sleep(1)
            else:raise RuntimeError('GPU server readiness timeout')
            p.dump(work/'active_generation.json',profile)
            p.dump(work/'gpu-server-process.json',dict(pid=process.pid,parent_pid=os.getpid(),scope='host',status='ready',log=str(logpath),profile=profile))
            print('GPU server ready on 127.0.0.1:18769. Keep this terminal open; Codex can continue.',flush=True)
            process.wait()
        finally:
            done.set();sampler.join(timeout=5)
            if process.poll() is None:process.terminate();process.wait(timeout=30)
            p.dump(work/'gpu-server-process.json',dict(pid=None,parent_pid=None,status='stopped',log=str(logpath),exit_code=process.returncode))


if __name__=='__main__':main()
