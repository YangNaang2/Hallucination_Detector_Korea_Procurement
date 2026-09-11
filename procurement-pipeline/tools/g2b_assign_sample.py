"""표본 목록(g2b_select_sample.py 의 표본_목록.csv)을 팀원 N명에게 고르게 배분한다.

문서 수가 많은 공고부터 스네이크 순서로 나눠 문서 부담을 맞추고, 월·분야는 자연히 섞인다.
--names 로 실명을 주면 담당 열에 실명이 들어간다 (쉼표 구분, 순서대로 담당1..N).

사용:
  python tools/g2b_assign_sample.py --list project-docs/표본_정보시스템/표본_목록.csv --n 6 --out project-docs/표본_정보시스템/배분표.csv [--names 홍길동,김철수,...]
"""
import argparse
from collections import Counter, defaultdict
import csv
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', required=True)
    ap.add_argument('--n', type=int, default=6)
    ap.add_argument('--names', default=None)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    names = [s.strip() for s in args.names.split(',')] if args.names else [f'담당{i + 1}' for i in range(args.n)]
    rows = list(csv.DictReader(Path(args.list).open(encoding='utf-8-sig', newline='')))
    rows.sort(key=lambda r: (-int(r['docs']), r['month'], r['bid_key']))
    order = list(range(args.n)) + list(range(args.n - 1, -1, -1))
    assign = defaultdict(list)
    for i, r in enumerate(rows):
        assign[order[i % (2 * args.n)]].append(r)
    out = []
    for m in range(args.n):
        for r in assign[m]:
            out.append(dict(담당=names[m], 월=r['month'], 공고번호=r['bid_key'], 분야=r['sector'].replace('용역·', ''), 공고명=r['title'],
                            기관=r['agency'], 예산=int(r['budget']), 문서수=int(r['docs']), 문서종류=r['doc_kinds'], 첨부파일=r['files'], URL=r['url']))
    with Path(args.out).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for m in range(args.n):
        rs = assign[m]
        mon = Counter(r['month'][-2:] for r in rs)
        sec = Counter('SW' if 'SW' in r['sector'] else '운영' for r in rs)
        print(f"{names[m]}: 공고 {len(rs)}건, 문서 {sum(int(r['docs']) for r in rs)}개, 월 {dict(sorted(mon.items()))}, 분야 {dict(sec)}")
    print('→', args.out)


if __name__ == '__main__':
    main()
