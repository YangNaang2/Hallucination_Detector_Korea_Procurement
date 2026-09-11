"""월별 prepare.py 산출물(sector_report.csv)을 합쳐 세 달 통합 분야 표를 만든다.

각 월의 sector_report.csv 는 모든 분야 행을 담고 있으므로(적격 여부만 다름) 분야별로 공고·첨부·사용 가능·완전 공고 수를 더한다.
정렬: 업무구분 필터(--business) 안에서 완전 공고 수 순. 점수는 참고용으로 통합 Wilson 하한을 다시 계산한다.

사용:
  python tools/g2b_merge_sector_reports.py --report 2026-04=path/a.csv --report 2026-05=path/b.csv --report 2026-06=path/c.csv --out merged.csv [--business 용역] [--min-complete 40]
"""
import argparse
from collections import defaultdict
import csv
import math
from pathlib import Path


def wilson(k, n):
    if not n:
        return 0.0
    z = 1.96
    p = k / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='append', required=True, help='라벨=csv경로 (여러 번)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--business', default=None)
    ap.add_argument('--min-complete', type=int, default=40)
    args = ap.parse_args()
    labels, agg = [], defaultdict(lambda: defaultdict(int))
    per_month = defaultdict(dict)
    for item in args.report:
        label, path = item.split('=', 1)
        labels.append(label)
        with Path(path).open(encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                s = r['sector']
                for k in ('notices', 'attachments', 'usable_docs', 'complete'):
                    agg[s][k] += int(r[k])
                per_month[s][label] = int(r['complete'])
    rows = []
    for s, a in agg.items():
        biz = s.split('·', 1)[0]
        in_scope = args.business is None or biz == args.business
        row = dict(sector=s, business=biz, notices=a['notices'], attachments=a['attachments'], usable_docs=a['usable_docs'],
                   complete=a['complete'], complete_rate=round(a['complete'] / a['notices'], 3),
                   usable_rate=round(a['usable_docs'] / max(a['attachments'], 1), 3),
                   score=round(0.8 * wilson(a['complete'], a['notices']) + 0.2 * a['usable_docs'] / max(a['attachments'], 1), 3),
                   eligible=in_scope and s != '미분류' and a['complete'] >= args.min_complete)
        for label in labels:
            row[f'complete_{label}'] = per_month[s].get(label, 0)
        rows.append(row)
    rows.sort(key=lambda r: (r['eligible'], r['complete'], r['score']), reverse=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'분야 {len(rows)}개, 적격 {sum(r["eligible"] for r in rows)}개 → {out}')
    for r in rows[:15]:
        months = ' / '.join(str(r[f'complete_{l}']) for l in labels)
        print(f"  {r['sector'][:26]:26s} 공고 {r['notices']:6d} 완전 {r['complete']:6d} ({r['complete_rate']:.0%}) | {months}")


if __name__ == '__main__':
    main()
