"""수집기 목록 파일(bids.jsonl + chunk_ready.jsonl)만으로 월별 분야 현황을 미리 집계한다.

워크스테이션에서 adapt_g2b.py + prepare.py 를 돌리기 전에, 노트북에 있는 목록 파일만으로
업무구분·세부분야별 공고 수와 '완전 공고'(공고문 + 제안요청서/과업지시서) 수를 뽑는다.
파일 실재·품질 검사는 하지 않으므로 워크스테이션 집계보다 조금 후하게 나온다.

사용:
  python tools/g2b_preview_stats.py --src "C:/.../5월_데이터확인" --month 2026-05 --out project-docs/데이터현황
여러 달을 합치려면 --src 를 여러 번 준다:
  python tools/g2b_preview_stats.py --src A --src B --src C --month all --out project-docs/데이터현황
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from adapt_g2b import kind_of, sector_of  # noqa: E402


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def collect(src):
    src = Path(src)
    latest, info, month_of = {}, {}, {}
    for b in read_jsonl(src / 'bids.jsonl'):
        no, o = b['bidNtceNo'], b.get('bidNtceOrd') or '000'
        if o > latest.get(no, ''):
            latest[no] = o
        info[f'{no}-{o}'] = sector_of(b)
        month_of[f'{no}-{o}'] = (b.get('bidNtceDt') or '')[:7]
    keep = {f'{no}-{o}' for no, o in latest.items()}
    groups = defaultdict(set)
    for c in read_jsonl(src / 'chunk_ready.jsonl'):
        k = c['bid']['bid_key']
        if k in keep:
            groups[k].add(kind_of(c['attachment']['filename']))
    rows = []
    for k in keep:
        sector, biz, sub = info[k]
        g = groups.get(k, set())
        rows.append(dict(month=month_of[k], business=biz, sector=sector, has_doc=bool(g),
                         complete='notice' in g and bool(g & {'rfp', 'spec'}),
                         has_notice='notice' in g, has_rfp='rfp' in g, has_spec='spec' in g))
    return rows, len(info)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', action='append', required=True, help='bids.jsonl, chunk_ready.jsonl 이 있는 폴더 (여러 번 가능)')
    ap.add_argument('--month', required=True, help='파일 이름용 라벨, 예: 2026-05 또는 all')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows, versions = [], 0
    for s in args.src:
        r, v = collect(s)
        rows += r
        versions += v
    agg = defaultdict(Counter)
    for r in rows:
        # 세부분류가 없으면 sector == business 이므로 같은 키를 두 번 세지 않도록 set 으로 만든다
        for key in {(r['business'], r['business']), (r['business'], r['sector'])}:
            a = agg[key]
            a['notices'] += 1
            a['has_doc'] += r['has_doc']
            a['complete'] += r['complete']
            a['has_notice'] += r['has_notice']
            a['has_rfp'] += r['has_rfp']
            a['has_spec'] += r['has_spec']
    table = []
    for (biz, sector), a in agg.items():
        table.append(dict(business=biz, sector=sector, level='업무구분' if biz == sector else '세부분야',
                          notices=a['notices'], has_doc=a['has_doc'], complete=a['complete'],
                          complete_rate=round(a['complete'] / a['notices'], 3),
                          has_notice=a['has_notice'], has_rfp=a['has_rfp'], has_spec=a['has_spec']))
    table.sort(key=lambda t: (t['level'] != '업무구분', -t['complete']))
    path = out / f'{args.month}_분야별_완전공고.csv'
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    months = Counter(r['month'] for r in rows)
    print(f'공고 행(차수 포함) {versions} → 최신 차수 {len(rows)} | 월별 {dict(months)}')
    for t in table:
        if t['level'] == '업무구분':
            print(f"  {t['business']:4s} 공고 {t['notices']:6d} | 문서 있음 {t['has_doc']:6d} | 완전 {t['complete']:6d} ({t['complete_rate']:.0%})")
    print('→', path)


if __name__ == '__main__':
    main()
