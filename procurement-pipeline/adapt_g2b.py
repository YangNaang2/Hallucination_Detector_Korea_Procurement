"""나라장터 수집기 출력(bids/manifest/chunk_ready + parsed/*.json) -> prepare.py 입력 manifest 변환.

수집기 출력은 공고별 폴더가 아니라 SHA-256 기반 평탄 구조다. 이 어댑터는 원본을 옮기거나 지우지 않고,
목록 파일만 읽어 prepare.py 계약(공고 ID+버전별 행, attachments, page/section/text JSONL)으로 바꾼다.
표준 라이브러리만 사용한다. 데이터가 있는 워크스테이션에서 실행한다.

사용 예:
  python adapt_g2b.py --src /data/g2b/nara/2026-05
  python prepare.py --input /data/g2b/nara/2026-05/adapter/manifest.jsonl --root /data/g2b/nara/2026-05 --out out/2026-05
"""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re
import sys
from common import save

# 첨부 파일명으로 문서 종류 분류. notice/rfp/spec 3종이 prepare.py의 핵심 그룹이다.
KIND = [
    ('rfp', r'제안.?요청|\brfp\b'),
    ('spec', r'과업.?지시|과업.?내용|과업.?수행|과업.?설명|규격서|시방서|요구사항|사양서|과업서'),
    ('notice', r'입찰.?공고|공고문|공고서|재공고|긴급공고|\b공고\b'),
    ('eval', r'평가.?기준|심사.?기준|평가.?계획|심사.?계획|배점'),
    ('contract', r'특수조건|일반조건|계약.?조건|계약서'),
    ('estimate', r'내역서|산출.?내역|물량|단가'),
    ('form', r'서식|양식|신청서|확약서|서약서|위임장|체크리스트'),
]
# 줄바꿈 없는 HWP 본문을 조항 단위로 자르는 제목 패턴. 앞에 공백이 있어야 한다.
HEAD = re.compile(r'(?<=[\s>)\]】」])(?=(?:제\s?\d{1,3}\s?조(?:의\s?\d+)?\b|\d{1,2}\.\s(?=[가-힣A-Za-z(\[「])|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\.\s|[IVX]{1,4}\.\s(?=[가-힣])|[□■◆●]\s?[가-힣]))')
LINE_HEAD = re.compile(r'^\s*(제\s?\d{1,3}\s?조[^\n]{0,30}|\d{1,2}\.\s[^\n]{2,30}|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\.\s[^\n]{2,30})', re.M)


def kind_of(name):
    for kind, pattern in KIND:
        if re.search(pattern, name, re.I):
            return kind
    return 'other'


def sector_of(bid):
    """업무구분 + 세부 분류. 세부 분류가 없으면 업무구분만 남긴다(미분류 아님)."""
    business = bid.get('_business_type_name') or '미분류'
    sub = (bid.get('pubPrcrmntMidClsfcNm') or bid.get('dtilPrdctClsfcNoNm')
           or bid.get('mainCnsttyNm') or '').strip()
    return f'{business}·{sub}' if sub else business, business, sub or None


def budget_of(bid, fallback):
    for key in ('asignBdgtAmt', 'bdgtAmt', 'presmptPrce'):
        v = bid.get(key)
        try:
            if v not in (None, ''):
                return int(float(v))
        except (TypeError, ValueError):
            continue
    return fallback


def sections(parsed, max_len=3000, min_len=200):
    """parsed.json blocks -> [{page, section, text}]. HWP는 page 없이 문단 하나이므로 제목 패턴으로 자른다."""
    out = []
    for block in parsed.get('blocks') or [{'type': 'paragraph', 'order': 0, 'text': parsed.get('text', '')}]:
        text = (block.get('text') or '').strip()
        if not text:
            continue
        page = block.get('order', 0) + 1 if block.get('type') == 'page' else None
        if '\n' in text:
            pieces = [text]
            m = LINE_HEAD.search(text)
            label = m.group(1).strip() if m else None
            for piece in pieces:
                out.append(dict(page=page, section=label, text=piece))
            continue
        pieces, buf = [], ''
        for piece in HEAD.split(text):
            if len(buf) + len(piece) < min_len or not buf:
                buf += piece
            else:
                pieces.append(buf)
                buf = piece
        if buf:
            pieces.append(buf)
        for piece in pieces:
            label = piece[:30].strip()
            n = 0
            while piece:
                if len(piece) <= max_len:
                    part, piece = piece, ''
                else:
                    # 문장 끝(다. / 함. / 음. / 마침표+공백)에서 자른다. 없으면 max_len에서 자른다.
                    cut = max(piece.rfind(m, min_len, max_len) for m in ('다. ', '함. ', '음. ', '. ', '다.', '함 ', '음 '))
                    cut = cut + 2 if cut > 0 else max_len
                    part, piece = piece[:cut], piece[cut:]
                part = part.strip()
                if part:
                    out.append(dict(page=page, section=label if n == 0 else f'{label} (계속 {n})', text=part))
                    n += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='bids.jsonl, manifest.jsonl, chunk_ready.jsonl, parsed/ 가 있는 월 폴더')
    ap.add_argument('--out', help='출력 폴더 (기본: <src>/adapter)')
    ap.add_argument('--root', help='prepare.py --root 와 같은 값 (기본: <src>)')
    ap.add_argument('--all-versions', action='store_true', help='정정·재공고 이전 차수도 남긴다 (기본: 공고번호별 최신 차수만)')
    ap.add_argument('--no-text', action='store_true', help='텍스트 JSONL 생성 생략 (집계만)')
    ap.add_argument('--min-quality', type=float, default=0.9)
    ap.add_argument('--limit', type=int, default=0, help='테스트용: 앞에서 N개 공고만')
    args = ap.parse_args()
    src = Path(args.src).resolve()
    out = Path(args.out).resolve() if args.out else src / 'adapter'
    root = Path(args.root).resolve() if args.root else src
    for name in ('bids.jsonl', 'manifest.jsonl', 'chunk_ready.jsonl'):
        if not (src / name).is_file():
            sys.exit(f'없음: {src / name}')
    (out / 'text').mkdir(parents=True, exist_ok=True)

    def rel(p):
        p = Path(p)
        if not p.is_absolute():
            p = src / p
        try:
            return p.resolve().relative_to(root).as_posix()
        except ValueError:
            return None

    def read_jsonl(path):
        with Path(path).open(encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)

    # 1) 최신 차수 파악 (공고번호별 최대 bidNtceOrd)
    latest = {}
    for b in read_jsonl(src / 'bids.jsonl'):
        no, order = b.get('bidNtceNo'), b.get('bidNtceOrd') or '000'
        if no and order > latest.get(no, ''):
            latest[no] = order

    # 2) manifest: 공고별 첨부 상태 (skipped_duplicate는 대체본이므로 첨부 목록에서 제외, 집계만)
    # chunk_ready 가 최종 인덱스다. 실패 문서를 나중에 따로 재파싱해 chunk_ready 에만 추가한 경우(manifest 는 옛 failed 그대로)
    # 를 위해, chunk_ready 에 있으면 manifest 상태와 무관하게 parsed 로 본다(실제 parsed JSON 내용은 아래서 다시 검사).
    selected = {}
    for c in read_jsonl(src / 'chunk_ready.jsonl'):
        selected[(c['bid']['bid_key'], c['document_id'])] = c.get('parsed_path')
    attachments = defaultdict(list)
    status_count = Counter()
    promoted = 0
    seen_pairs = set()
    parsed_status_cache = {}

    def peek_parse_status(path):
        try:
            return (json.loads(Path(path).read_text(encoding='utf-8')).get('parse') or {}).get('status')
        except (OSError, ValueError):
            return None
    group_summary_rows = 0
    for m in read_jsonl(src / 'manifest.jsonl'):
        status_count[m['status']] += 1
        if m['status'] == 'skipped_duplicate':
            continue
        if 'attachment' not in m:
            # 같은 이름 다중 포맷 묶음에서 후보가 전부 실패/저품질이라 선택된 첨부가 없는 경우의 요약 행
            # (키: bid, duplicate_group, candidates, candidate_attempts, reason). 첨부 단위 기록이 아니므로 건너뛴다.
            group_summary_rows += 1
            continue
        key = m['bid']['bid_key']
        doc_id = m.get('document_id')
        status, parsed_path = m['status'], m.get('parsed_path')
        if (key, doc_id) in selected:
            if status != 'parsed':
                promoted += 1
                status = 'parsed'
            parsed_path = parsed_path or selected[(key, doc_id)]
        elif status == 'failed' and parsed_path and doc_id:
            # 같은 파일이 여러 공고에 붙은 경우, 재파싱 도구는 첫 공고에만 chunk_ready 행을 추가한다.
            # parsed JSON 은 문서 단위로 갱신되므로 그 상태가 parsed 면 다른 공고에서도 parsed 로 본다.
            if doc_id not in parsed_status_cache:
                parsed_status_cache[doc_id] = peek_parse_status(parsed_path)
            if parsed_status_cache[doc_id] == 'parsed':
                promoted += 1
                status = 'parsed'
        seen_pairs.add((key, doc_id))
        attachments[key].append((doc_id, m['attachment'].get('filename') or '', m.get('raw_path'), parsed_path,
                                 status, (key, doc_id) in selected))
    # chunk_ready 에만 있고 manifest 에 없는 문서도 첨부로 넣는다 (raw 경로는 parsed JSON 의 source.raw_path 에서 찾는다).
    only_in_chunk_ready = 0
    for c in read_jsonl(src / 'chunk_ready.jsonl'):
        key, doc_id = c['bid']['bid_key'], c['document_id']
        if (key, doc_id) in seen_pairs:
            continue
        only_in_chunk_ready += 1
        attachments[key].append((doc_id, c['attachment'].get('filename') or '', None, c.get('parsed_path'), 'parsed', True))

    # 3) bids 순회 → 공고 행 생성 + 텍스트 변환
    report = dict(status=dict(status_count), notices_total=0, notices_kept=0, notices_dropped_old_version=0,
                  attachments=0, usable=0, kind=Counter(), reason=Counter(), sector=Counter(), missing_file=0)
    rows_out = out / 'manifest.jsonl'
    with rows_out.open('w', encoding='utf-8') as fo:
        for b in read_jsonl(src / 'bids.jsonl'):
            report['notices_total'] += 1
            no, order = b.get('bidNtceNo'), b.get('bidNtceOrd') or '000'
            if not no:
                continue
            if not args.all_versions and latest.get(no) != order:
                report['notices_dropped_old_version'] += 1
                continue
            if args.limit and report['notices_kept'] >= args.limit:
                break
            key = f'{no}-{order}'
            sector, business, sub = sector_of(b)
            row = dict(notice_id=no, version=order, sector=sector, business_type=business, sub_sector=sub,
                       month=(b.get('bidNtceDt') or '')[:7] or None, title=b.get('bidNtceNm'),
                       agency=b.get('dminsttNm') or b.get('ntceInsttNm'), notice_org=b.get('ntceInsttNm'),
                       budget_krw=budget_of(b, None), deadline=b.get('bidClseDt') or None,
                       is_renotice=b.get('reNtceYn') == 'Y', location=None,
                       detail_url=b.get('bidNtceDtlUrl') or b.get('bidNtceUrl'), attachments=[])
            for doc_id, name, raw_path, parsed_path, status, is_selected in attachments.get(key, []):
                kind = kind_of(name)
                a = dict(document_id=doc_id, name=name, kind=kind, path=rel(raw_path) if raw_path else None,
                         sha256=doc_id, download_status='ok' if status in ('parsed', 'low_quality') else status,
                         parse_status={'parsed': 'ok'}.get(status, status), integrity_ok=False,
                         selected=is_selected, text_path=None, quality=None, text_chars=0)
                reason = None
                if status == 'parsed':
                    parsed_file = Path(parsed_path) if parsed_path else None
                    parsed = None
                    if not (parsed_file and parsed_file.is_file()):
                        reason = 'parsed_missing'
                    else:
                        try:
                            parsed = json.loads(parsed_file.read_text(encoding='utf-8'))
                        except (OSError, ValueError):
                            reason = 'parsed_unreadable'
                    if parsed is not None and not raw_path:
                        raw_path = (parsed.get('source') or {}).get('raw_path')
                        a['path'] = rel(raw_path) if raw_path else None
                    raw_file = Path(raw_path) if raw_path else None
                    if parsed is not None and not (raw_file and raw_file.is_file() and raw_file.stat().st_size > 0):
                        reason = 'raw_missing'
                    elif parsed is not None:
                        pstatus = (parsed.get('parse') or {}).get('status', 'parsed')
                        a['quality'] = (parsed.get('parse') or {}).get('quality')
                        secs = sections(parsed)
                        a['text_chars'] = sum(len(s['text']) for s in secs)
                        if pstatus != 'parsed':
                            reason = f'parsed_json_status_{pstatus}'
                            a['parse_status'] = pstatus
                        elif a['text_chars'] < 100:
                            reason = 'text_too_short'
                        elif a['quality'] is not None and a['quality'] < args.min_quality:
                            reason = 'quality_below_threshold'
                        elif a['path'] is None:
                            reason = 'raw_outside_root'
                        else:
                            text_file = out / 'text' / f'{doc_id}.jsonl'
                            if not args.no_text:
                                with text_file.open('w', encoding='utf-8') as ft:
                                    for s in secs:
                                        ft.write(json.dumps(s, ensure_ascii=False) + '\n')
                            a['text_path'] = rel(text_file)
                            if a['text_path'] is None:
                                reason = 'text_outside_root'
                            elif args.no_text:
                                reason = 'text_skipped'
                            else:
                                a['integrity_ok'] = True
                    if reason in ('raw_missing', 'parsed_missing'):
                        report['missing_file'] += 1
                else:
                    reason = status
                a['reason'] = reason
                report['attachments'] += 1
                report['usable'] += int(a['integrity_ok'])
                report['kind'][kind] += 1
                report['reason'][reason or 'ok'] += 1
                row['attachments'].append(a)
            report['notices_kept'] += 1
            report['sector'][sector] += 1
            fo.write(json.dumps(row, ensure_ascii=False) + '\n')
    report['promoted_by_chunk_ready'] = promoted
    report['only_in_chunk_ready'] = only_in_chunk_ready
    report['manifest_group_summary_rows_skipped'] = group_summary_rows
    report['kind'] = dict(report['kind'])
    report['reason'] = dict(report['reason'])
    report['sector'] = dict(Counter(report['sector']).most_common(60))
    report['note'] = ('usable = parsed + raw/parsed 파일 존재 + 본문 100자 이상 + quality>=min. '
                      '내용의 완전성은 보장하지 않는다. skipped_duplicate 는 같은 이름의 다른 형식이라 첨부 목록에서 뺐다.')
    save(out / 'adapt_report.json', report)
    print(f"공고 {report['notices_kept']}/{report['notices_total']} (이전 차수 제외 {report['notices_dropped_old_version']}), "
          f"첨부 {report['attachments']} 중 사용 가능 {report['usable']} → {rows_out}")


if __name__ == '__main__':
    main()
