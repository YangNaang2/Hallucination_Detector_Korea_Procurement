import csv
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def records(path):
    path = Path(path)
    with path.open(encoding='utf-8-sig', newline='') as f:
        if path.suffix.lower() == '.csv':
            for row in csv.DictReader(f):
                row['attachments'] = json.loads(row.get('attachments') or '[]')
                yield row
        else:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def jsonl(path, rows):
    with Path(path).open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
