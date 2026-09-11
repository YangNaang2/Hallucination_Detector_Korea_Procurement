"""Streaming manifest audit -> sector recommendation -> stratified evidence packets."""
import argparse
from collections import Counter, defaultdict
import math
from pathlib import Path
import re
import sqlite3
from common import digest, records, save, jsonl

GROUPS = {
    'notice': r'입찰.?공고|공고서',
    'rfp': r'제안.?요청|\brfp\b',
    'spec': r'과업.?지시|과업.?내용|과업.?수행|과업.?설명|규격서|시방서|요구사항',
}
KEY = re.compile(r'자격|실적|인증|납품|수량|규격|서버|랙|클린룸|예산|기간|기한|필수|하여야|해야')


def audit(row, root):
    if not row.get('notice_id') or not row.get('version'):
        raise ValueError('notice_id and version required')
    row['sector'] = row.get('sector') or '미분류'
    good, seen, attachments = set(), set(), []
    for i, original in enumerate(row.get('attachments', [])):
        a = dict(original)
        identity = a.get('sha256') or a.get('path') or a.get('document_id') or f'unknown-{i}'
        if identity in seen:
            continue
        seen.add(identity)
        # 실패/저품질 첨부는 path·text_path가 None으로 올 수 있다. 없는 경로로 취급한다.
        path = (root / (a.get('path') or '__missing__')).resolve()
        text_path = (root / (a.get('text_path') or '__missing__')).resolve()
        # A filename alone is never evidence of an intact, parsed attachment.
        a['usable'] = bool(path.is_relative_to(root) and text_path.is_relative_to(root)
                           and path.is_file() and path.stat().st_size > 0
                           and a.get('download_status') == 'ok'
                           and a.get('parse_status') == 'ok'
                           and text_path.is_file() and text_path.stat().st_size > 0
                           and a.get('integrity_ok') is True)
        label = a.get('kind') or a.get('name', '')
        a['groups'] = [g for g, pattern in GROUPS.items()
                       if label == g or re.search(pattern, label, re.I)]
        if a['usable']:
            good.update(a['groups'])
        attachments.append(a)
    row['attachments'] = attachments
    # 실데이터(2026-05 표본)에서는 공고문+제안요청서 또는 공고문+과업지시서 구성이 대부분이고 3종이 모두 있는 공고는 드물다.
    # '완전' = 공고문 1건 + 요건 문서(제안요청서/과업·규격서) 1건 이상.
    row['complete'] = 'notice' in good and bool(good & {'rfp', 'spec'})
    row['groups_found'] = sorted(good)
    row['usable_docs'] = sum(a['usable'] for a in attachments)
    return row


def wilson(k, n):
    if not n:
        return 0
    z = 1.96
    p = k / n
    return (p + z*z/(2*n) - z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / (1+z*z/n)


def packet(row, root, max_chars):
    chunks = []
    for i, a in enumerate(row['attachments']):
        if not a['usable']:
            continue
        # Existing parser output, one JSON object per page/section; no PDF/HWP parsing here.
        for p in records(root / a['text_path']):
            text = p.get('text', '')
            for start in range(0, len(text), 700):
                excerpt = text[start:start+850]
                score = len(KEY.findall(excerpt))
                chunks.append(dict(document_id=a.get('document_id') or f'doc-{i}',
                    document_version_id=digest([row['notice_id'],row['version'],a.get('sha256'),i]),
                    page=p.get('page'), section=p.get('section'), text_start=start,
                    text_end=start+len(excerpt), text=excerpt, score=score))
    # Round robin across documents, with high-value sections first per document.
    by_doc = defaultdict(list)
    for c in sorted(chunks, key=lambda c: -c['score']):
        by_doc[c['document_id']].append(c)
    selected, used = [], 0
    while any(by_doc.values()):
        for values in by_doc.values():
            if not values:
                continue
            c = values.pop(0)
            if used + len(c['text']) > max_chars:
                continue
            c.pop('score')
            c['chunk_id'] = digest(c)[:24]
            selected.append(c)
            used += len(c['text'])
    if not selected:
        raise ValueError('no extracted text chunks')
    fields = ['notice_id','version','title','sector','agency','budget_krw','deadline','location','month']
    result = {'metadata': {k:row.get(k) for k in fields}, 'chunks': selected,
              'text_chars':used, 'selection':'keyword + document round robin; not exhaustive'}
    result['packet_id'] = digest(result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--root', required=True)
    ap.add_argument('--out', default='out')
    ap.add_argument('--n', type=int, default=40)
    ap.add_argument('--min-sector', type=int, default=30)
    ap.add_argument('--max-chars', type=int, default=10000)
    args = ap.parse_args()
    if min(args.n,args.min_sector,args.max_chars) <= 0:
        ap.error('limits must be positive')
    root, out = Path(args.root).resolve(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(out / 'audit.sqlite')
    db.execute('DROP TABLE IF EXISTS notices')
    db.execute('CREATE TABLE notices (id TEXT PRIMARY KEY, payload TEXT)')
    import json
    conflicts, duplicates = 0, 0
    # On-disk index keeps the full 130k corpus out of Python RAM.
    for row in records(args.input):
        row = audit(row, root)
        key = f"{row['notice_id']}::{row['version']}"
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
        existing = db.execute('SELECT payload FROM notices WHERE id=?',(key,)).fetchone()
        if existing:
            if existing[0] != payload:
                conflicts += 1
            else:
                duplicates += 1
            continue
        db.execute('INSERT INTO notices VALUES (?,?)',(key,payload))
    db.commit()
    if conflicts:
        raise ValueError(f'{conflicts} conflicting notice/version rows; merge manifests first')
    stats = defaultdict(Counter)
    candidates = defaultdict(list)
    for key, payload in db.execute('SELECT id,payload FROM notices'):
        r = json.loads(payload)
        s = stats[r['sector']]
        s.update(notices=1, attachments=len(r['attachments']), usable_docs=r['usable_docs'],
                 complete=int(r['complete']))
        if r['complete']:
            candidates[r['sector']].append((key,r.get('month') or 'unknown',r.get('agency') or 'unknown',
                                           r.get('budget_krw')))
    ranking = []
    for sector, s in stats.items():
        rate = s['complete']/s['notices']
        usable = s['usable_docs']/max(s['attachments'],1)
        ranking.append(dict(sector=sector, **s, complete_rate=rate,
            usable_rate=usable, score=.8*wilson(s['complete'],s['notices'])+.2*usable,
            eligible=sector!='미분류' and s['notices']>=args.min_sector and s['complete']>=args.n))
    ranking.sort(key=lambda r:(r['eligible'],r['score'],r['complete']), reverse=True)
    chosen = next((r['sector'] for r in ranking if r['eligible']),None)
    save(out/'sector_report.json',dict(ranking=ranking,recommended=chosen,duplicate_rows=duplicates,
        unit='notice_id + version', note='structural completeness, not semantic/legal completeness'))
    import csv
    if ranking:
        with (out/'sector_report.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(ranking[0]));w.writeheader();w.writerows(ranking)
    if not chosen:
        print('추천 보류: 최소 모수/완전 공고 수 부족. sector_report.json 확인')
        return
    strata = defaultdict(list)
    for key, month, agency, budget in candidates[chosen]:
        try:
            band = int(math.log10(max(float(budget),1)))
        except (ValueError,TypeError):
            band = 'unknown'
        strata[(month,agency,str(band))].append(key)
    for keys in strata.values():
        keys.sort(key=lambda k:digest(['seed42',k]))
    picked=[]
    while len(picked)<args.n and any(strata.values()):
        for k in sorted(strata):
            if strata[k] and len(picked)<args.n:
                picked.append(strata[k].pop())
    packets=[]
    for key in picked:
        row=json.loads(db.execute('SELECT payload FROM notices WHERE id=?',(key,)).fetchone()[0])
        packets.append(packet(row,root,args.max_chars))
    jsonl(out/'packets.jsonl', packets)
    save(out/'sampling.json',dict(sector=chosen,selected=picked,n=len(picked),
        method='equal round robin: month/agency/log10 budget; demo diversity, not unbiased evaluation',
        total_text_chars=sum(p['text_chars'] for p in packets)))
    db.close()
    print(f'{chosen}: {len(packets)}건 → {out}/packets.jsonl (LLM 호출 0회)')


if __name__ == '__main__':
    main()
