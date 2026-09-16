"""Pinned Linux setup, public downloads only; never executes the Windows installer."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

import rag_pilot as p
import setup_rag_pilot as old


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--work',type=Path,default=p.ROOT/'work/rag-workstation-275')
    args=parser.parse_args(); work=args.work.resolve()
    work.mkdir(parents=True,exist_ok=True)
    records=[]
    for repo,revision,folder,names in old.MODELS:
        if folder=='qwen': continue
        metadata=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true',timeout=60))
        files={f['rfilename']:f for f in metadata['siblings']}
        for name in names:
            if name not in files: continue
            record=old.download(f'https://huggingface.co/{repo}/resolve/{revision}/{name}',work/folder/name)
            expected=files[name].get('lfs',{}).get('sha256')
            if expected and record['sha256']!=expected: raise ValueError('weight hash mismatch')
            records.append(record|dict(repo=repo,revision=revision,upstream_sha256=expected))
            p.dump(work/'downloads.json',records)
    model=work/'qwen3/Qwen3-4B-Q4_K_M.gguf'
    profile=p.read(p.ROOT/'project-docs/RAG파일럿/v1/runtime/generation_profiles.json')['qwen3-4b']
    with model.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=profile['model_sha256']:
            raise ValueError('model differs from pilot')
    p.dump(work/'active_generation.json',profile)
    url='https://github.com/ggml-org/llama.cpp/releases/download/b10938/llama-b10938-bin-ubuntu-x64.tar.gz'
    record=old.download(url,work/'llama-b10938-ubuntu.tar.gz')
    if record['sha256']!='adbd216b2453b79e3874a406bee21e59d1b0ba06df567102ab8a69aa3dd200dd':
        raise ValueError('runtime release digest mismatch')
    records.append(record)
    with tarfile.open(work/'llama-b10938-ubuntu.tar.gz') as archive:
        archive.extractall(work/'llama-b10938',filter='data')
    p.dump(work/'downloads.json',records)
    print('pinned Qwen3/E5 and Linux CPU runtime downloaded; GPU acceleration not claimed')


if __name__=='__main__':main()
