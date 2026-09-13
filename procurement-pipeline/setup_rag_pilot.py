"""Download pinned public model/runtime files only. Never uploads project data."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/rag-pilot'
MODELS = [
    ('Qwen/Qwen3-4B-GGUF', 'bc640142c66e1fdd12af0bd68f40445458f3869b',
     'qwen3', ['Qwen3-4B-Q4_K_M.gguf', 'LICENSE', 'README.md']),
    ('Qwen/Qwen2.5-1.5B-Instruct-GGUF', '91cad51170dc346986eccefdc2dd33a9da36ead9',
     'qwen', ['qwen2.5-1.5b-instruct-q4_k_m.gguf', 'LICENSE']),
    ('intfloat/multilingual-e5-small', '614241f622f53c4eeff9890bdc4f31cfecc418b3',
     'e5', ['config.json', 'model.safetensors', 'tokenizer.json', 'tokenizer_config.json',
            'special_tokens_map.json', 'sentencepiece.bpe.model', 'README.md']),
]


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        part = dest.with_suffix(dest.suffix + '.part')
        print('download', dest.name, flush=True)
        with urllib.request.urlopen(url, timeout=90) as src, part.open('wb') as out:
            while block := src.read(1024 * 1024):
                out.write(block)
        part.replace(dest)
    return dict(path=dest.relative_to(ROOT).as_posix(), url=url, bytes=dest.stat().st_size,
                sha256=hashlib.file_digest(dest.open('rb'), 'sha256').hexdigest())


def main():
    records = []
    for repo, revision, folder, names in MODELS:
        metadata = json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}/revision/{revision}?blobs=true', timeout=30))
        files = {x['rfilename']: x for x in metadata['siblings']}
        for name in names:
            if name not in files:
                continue
            record = download(f'https://huggingface.co/{repo}/resolve/{revision}/{name}', WORK / folder / name)
            expected = files[name].get('lfs', {}).get('sha256')
            if expected and record['sha256'] != expected:
                raise ValueError('model hash mismatch: ' + name)
            records.append(record | dict(repo=repo, revision=revision, license=metadata.get('cardData', {}).get('license')))
    url = 'https://github.com/ggml-org/llama.cpp/releases/download/b10938/llama-b10938-bin-win-cpu-x64.zip'
    archive = WORK / 'llama-b10938.zip'
    records.append(download(url, archive))
    target = WORK / 'llama-b10938'
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if not (target / name).resolve().is_relative_to(target.resolve()):
                raise ValueError('unsafe archive path')
        z.extractall(target)
    (WORK / 'downloads.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    print('download complete', len(records), flush=True)


if __name__ == '__main__':
    main()
