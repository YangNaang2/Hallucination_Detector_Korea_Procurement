"""세 달 목록 파일(bids + chunk_ready)만으로 표본 공고를 고른다. 워크스테이션 없이 노트북에서 실행.

선정 조건: 최신 차수, 지정 분야, 공고문 + (제안요청서 또는 과업·규격서) 문서가 chunk_ready 에 있음, 예산 있음.
선정 방식: 월 → 기관 → 예산 자릿수(log10) 층을 순환하며 고정 seed 해시 순으로 뽑는다 (prepare.py 와 같은 규칙).
출력: 월별 ID 파일(prepare.py --ids 입력), 사람이 읽는 CSV.

사용:
  python tools/g2b_select_sample.py --src 2026-04=<4월 폴더> --src 2026-05=<5월 폴더> --src 2026-06=<6월 폴더> \
      --sector "용역·SW 및 시스템 개발" --sector "용역·운영 및 유지관리" --per-month 17 --out project-docs/표본
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from adapt_g2b import kind_of, sector_of  # noqa: E402


def read_jsonl(path):
    with Path(path).open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def norm_title(t):
    t = re.sub(r'\[.*?\]|\(.*?\)|재공고|긴급|재입찰|\d+차', '', t or '')
    return re.sub(r'\s+', '', t).lower()


def budget_of(b):
    for key in ('asignBdgtAmt', 'bdgtAmt', 'presmptPrce'):
        v = b.get(key)
        try:
            if v not in (None, ''):
                return int(float(v))
        except (TypeError, ValueError):
            pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', action='append', required=True, help='라벨=폴더 (bids.jsonl, chunk_ready.jsonl)')
    ap.add_argument('--sector', action='append', required=True)
    ap.add_argument('--per-month', type=int, default=17)
    ap.add_argument('--min-docs', type=int, default=2, help='공고당 최소 사용 문서 수')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sectors = set(args.sector)
    all_rows = []
    seen_titles = set()
    for item in args.src:
        label, folder = item.split('=', 1)
        folder = Path(folder)
        latest, info = {}, {}
        for b in read_jsonl(folder / 'bids.jsonl'):
            no, o = b['bidNtceNo'], b.get('bidNtceOrd') or '000'
            if o > latest.get(no, ''):
                latest[no] = o
            sec, biz, sub = sector_of(b)
            if sec in sectors:
                info[f'{no}-{o}'] = dict(sector=sec, title=b.get('bidNtceNm'), agency=b.get('dminsttNm') or b.get('ntceInsttNm'),
                                         budget=budget_of(b), deadline=b.get('bidClseDt'), month=(b.get('bidNtceDt') or '')[:7],
                                         method=b.get('cntrctCnclsMthdNm'), url=b.get('bidNtceDtlUrl'))
        keep = {f'{no}-{o}' for no, o in latest.items()} & set(info)
        docs = defaultdict(list)
        for c in read_jsonl(folder / 'chunk_ready.jsonl'):
            k = c['bid']['bid_key']
            if k in keep:
                docs[k].append((kind_of(c['attachment']['filename']), c['attachment']['filename']))
        strata = defaultdict(list)
        for k in keep:
            kinds = {d[0] for d in docs.get(k, [])}
            r = info[k]
            if 'notice' not in kinds or not (kinds & {'rfp', 'spec'}) or len(docs[k]) < args.min_docs or not r['budget']:
                continue
            band = int(math.log10(max(r['budget'], 1)))
            strata[(r['agency'], band)].append(k)
        def h(x):
            return hashlib.sha256(json.dumps(['seed42', x], ensure_ascii=False).encode()).hexdigest()
        # 층 안에서는 문서가 많은 공고를 먼저, 같으면 해시 순. 층 순회도 이름순이 아니라 해시 순(이름순이면 '(사)…' 기관만 뽑힌다).
        for ks in strata.values():
            ks.sort(key=lambda k: (-len(docs[k]), h(k)), reverse=True)  # pop() 이 끝에서 꺼내므로 역순 정렬
        order = sorted(strata, key=lambda s: h(list(s)))
        picked = []
        while len(picked) < args.per_month and any(strata.values()):
            for s in order:
                while strata[s] and len(picked) < args.per_month:
                    k = strata[s].pop()
                    t = norm_title(info[k]['title'])
                    if t in seen_titles:
                        continue  # 다른 달의 재공고·같은 사업 중복 제외
                    seen_titles.add(t)
                    picked.append(k)
                    break
        eligible = sum(len(v) for v in strata.values()) + len(picked)
        print(f'{label}: 후보 {eligible}건 중 {len(picked)}건 선정')
        (out / f'표본_{label}_ids.txt').write_text('\n'.join(picked) + '\n', encoding='utf-8')
        for k in picked:
            r = info[k]
            all_rows.append(dict(month=label, bid_key=k, sector=r['sector'], title=r['title'], agency=r['agency'], budget=r['budget'],
                                 method=r['method'], deadline=r['deadline'], docs=len(docs[k]),
                                 doc_kinds='/'.join(sorted({d[0] for d in docs[k]})),
                                 files=' | '.join(d[1] for d in docs[k]), url=r['url']))
    with (out / '표본_목록.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        w.writeheader()
        w.writerows(all_rows)
    print(f'총 {len(all_rows)}건 → {out}')


if __name__ == '__main__':
    main()
