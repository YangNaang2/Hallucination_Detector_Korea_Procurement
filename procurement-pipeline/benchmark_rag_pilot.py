"""Small synthetic CPU probe for thread choice, not a RAG performance benchmark."""
import json
import subprocess
import rag_pilot as p


if __name__=='__main__':
    command=[str(p.WORK/'llama-b10938/llama-bench.exe'),'-m','qwen/qwen2.5-1.5b-instruct-q4_k_m.gguf',
             '-p','128','-n','16','-t','2,4,8','-r','1','-ngl','0','-o','json']
    previous=p.OUT/'validation/cpu_probe.json'
    if previous.exists() and p.read(previous)['status']=='failed':
        p.dump(p.OUT/'validation/cpu_probe_startup_failure.json',p.read(previous))
    result=subprocess.run(command,cwd=p.WORK,capture_output=True,encoding='utf-8',errors='replace',timeout=300)
    if result.returncode:
        p.dump(p.OUT/'validation/cpu_probe.json',dict(status='failed',stderr=result.stderr))
        raise SystemExit(result.returncode)
    p.dump(p.OUT/'validation/cpu_probe.json',dict(status='complete',results=json.loads(result.stdout),
          command=command,limitation='1 repetition, short synthetic pp128/tg16; thread selection only, not 25-question latency'))
    for row in json.loads(result.stdout):
        print({k:v for k,v in row.items() if k in ['n_threads','n_prompt','n_gen','avg_ts']})
