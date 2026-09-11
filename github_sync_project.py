"""Copy first-party project assets into the existing private repository; never copy credentials."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parent
repo=root/'ko_lettucedetect'
count=0
def copy(src,dst):
    global count
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst);count+=1
for src in (root/'demo-ui').rglob('*'):
    if not src.is_file():continue
    rel=src.relative_to(root/'demo-ui')
    if any(part in ('__pycache__','.git','node_modules') for part in rel.parts):continue
    if src.name.startswith('.env') and src.name!='.env.example':continue
    if src.name in ('twin-pdf-check.png','twin-export.json'):continue
    if src.suffix in ('.pyc','.log','.npz','.safetensors','.bin'):continue
    copy(src,repo/'demo-ui'/rel)
for pattern in ('*.md','*.svg','워크스테이션_명령어.txt'):
    for src in root.glob(pattern):copy(src,repo/'project-docs'/src.name)
copy(root/'Finding_Hallucination.html',repo/'presentations'/'Finding_Hallucination.html')
for src in (root/'발표자료_소스').rglob('*'):
    if src.is_file() and '__pycache__' not in src.parts:
        copy(src,repo/'presentations'/'source'/src.relative_to(root/'발표자료_소스'))
for src in root.glob('AI프로젝트_아이디어*'):
    if src.suffix in ('.pdf','.pptx'):copy(src,repo/'presentations'/src.name)
print(f'Prepared {count} project assets; credentials and raw datasets excluded.')
