"""선정된 공고(prepare.py 산출 sampling.json 또는 ID 목록)의 원본 첨부·텍스트·메타데이터만 한 폴더로 모은다.

메인 워크스테이션으로 옮길 꾸러미를 만드는 단계(③ 선정한 데이터만 모으기). 원본은 복사만 하고 건드리지 않는다.
결과 폴더 구조:
  <out>/<bid_key>/공고정보.json            어댑터 manifest 행 (분야·예산·마감·첨부 상태)
  <out>/<bid_key>/원본/<원래 파일명>        raw 첨부 (사용 가능한 것)
  <out>/<bid_key>/텍스트/<원래 파일명>.jsonl page/section/text 구간
  <out>/선정목록.csv, <out>/누락보고.json     사용 불가 첨부(OCR 대상 등) 목록

사용 (워크스테이션, procurement-pipeline 폴더에서):
  python tools/g2b_export_selection.py --manifest <월 폴더>/adapter/manifest.jsonl --root <월 폴더> --ids 표본_2026-05_ids.txt --out export/2026-05
그 다음 export/2026-05 를 zip 으로 묶어 전달한다.
"""
import argparse
import csv
import json
from pathlib import Path
import re
import shutil


def safe(name):
    return re.sub(r'[\\/:*?"<>|]+', '_', name)[:150]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True, help='adapt_g2b.py 가 만든 adapter/manifest.jsonl')
    ap.add_argument('--root', required=True, help='월 폴더 (adapter 의 path/text_path 기준)')
    ap.add_argument('--ids', help='공고 키 목록 파일 (한 줄에 하나)')
    ap.add_argument('--sampling', help='prepare.py 의 sampling.json (ids 대신)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--all-attachments', action='store_true', help='사용 불가 첨부(실패·저품질)의 원본도 함께 복사 (OCR 용)')
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.out)
    if args.ids:
        wanted = [l.strip() for l in Path(args.ids).read_text(encoding='utf-8-sig').splitlines() if l.strip() and not l.startswith('#')]
    elif args.sampling:
        wanted = [k.replace('::', '-', 1) for k in json.loads(Path(args.sampling).read_text(encoding='utf-8'))['selected']]
    else:
        raise SystemExit('--ids 또는 --sampling 필요')
    wanted_set = set(wanted)
    rows = {}
    with Path(args.manifest).open(encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            key = f"{r['notice_id']}-{r['version']}"
            if key in wanted_set:
                rows[key] = r
    out.mkdir(parents=True, exist_ok=True)
    listing, missing_report = [], []
    for key in wanted:
        r = rows.get(key)
        if not r:
            missing_report.append(dict(bid_key=key, problem='manifest 에 없음'))
            continue
        d = out / key
        (d / '원본').mkdir(parents=True, exist_ok=True)
        (d / '텍스트').mkdir(parents=True, exist_ok=True)
        (d / '공고정보.json').write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf-8')
        copied, unusable = 0, []
        for a in r['attachments']:
            name = safe(a.get('name') or a.get('document_id') or 'unknown')
            if a.get('integrity_ok'):
                src_raw = root / a['path']
                src_txt = root / a['text_path']
                if src_raw.is_file():
                    shutil.copy2(src_raw, d / '원본' / name)
                if src_txt.is_file():
                    shutil.copy2(src_txt, d / '텍스트' / (name + '.jsonl'))
                copied += 1
            else:
                unusable.append(dict(name=a.get('name'), kind=a.get('kind'), reason=a.get('reason'), path=a.get('path')))
                if args.all_attachments and a.get('path') and (root / a['path']).is_file():
                    (d / '원본_사용불가').mkdir(exist_ok=True)
                    shutil.copy2(root / a['path'], d / '원본_사용불가' / name)
        listing.append(dict(bid_key=key, sector=r.get('sector'), title=r.get('title'), agency=r.get('agency'), budget_krw=r.get('budget_krw'),
                            deadline=r.get('deadline'), usable_docs=copied, unusable_docs=len(unusable),
                            unusable_names=' | '.join(u['name'] or '' for u in unusable)))
        if unusable:
            missing_report.append(dict(bid_key=key, problem='사용 불가 첨부', attachments=unusable))
    with (out / '선정목록.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(listing[0]) if listing else ['bid_key'])
        w.writeheader()
        w.writerows(listing)
    (out / '누락보고.json').write_text(json.dumps(missing_report, ensure_ascii=False, indent=1), encoding='utf-8')
    total = sum(l['usable_docs'] for l in listing)
    print(f'공고 {len(listing)}/{len(wanted)} 건, 사용 가능 문서 {total}개 복사, 사용 불가 첨부 {sum(l["unusable_docs"] for l in listing)}개 → {out}')


if __name__ == '__main__':
    main()
