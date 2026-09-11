"""adapt_g2b.py 로컬 테스트: 수집기 출력 구조를 가짜로 만들어 어댑터 → prepare.py 까지 통과하는지 확인한다."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NL = chr(10)


def write_jsonl(path, rows):
    with Path(path).open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + NL)


def fake_month(root):
    """공고 3건: A(공고문+제안요청서, 정정 001차), B(공고문만), C(저품질 과업지시서). A의 000차는 이전 차수."""
    root = Path(root)
    (root / 'raw' / 'aa').mkdir(parents=True)
    (root / 'parsed').mkdir()
    docs = {
        'aa01': ('입찰공고문.hwp', 'paragraph', '입찰공고 1. 입찰에 부치는 사항 사업명 데이터센터 증설 2. 입찰참가자격 최근 3년 실적 10억 이상 3. 제출서류 ' * 12, 0.98),
        'aa02': ('제안요청서.hwp', 'paragraph', '제안요청서 Ⅰ. 사업개요 서버 랙 50식을 설치하여야 한다. Ⅱ. 요구사항 클린룸 등급 ISO 7 이상이어야 한다. ' * 12, 0.97),
        'aa03': ('과업지시서.pdf', 'page', '과업지시서' + NL + '제1조 목적 이 과업은 납품 기한을 정한다.' + NL + '제2조 범위', 0.5),
    }
    for sha, (name, btype, text, q) in docs.items():
        (root / 'raw' / 'aa' / f'{sha}.{name.rsplit(".", 1)[1]}').write_bytes(b'x' * 100)
        (root / 'parsed' / f'{sha}.json').write_text(json.dumps(dict(
            document_id=sha, sha256=sha, source=dict(filename=name),
            parse=dict(status='parsed', detected_format='hwp', parser='fake', quality=q),
            text=text, blocks=[dict(type=btype, order=0, text=text)]), ensure_ascii=False), encoding='utf-8')

    def bid(no, order, name, business, mid=None, budget='1000000'):
        return {'bidNtceNo': no, 'bidNtceOrd': order, 'bidNtceNm': name, '_business_type_name': business,
                'pubPrcrmntMidClsfcNm': mid, 'dminsttNm': '발주기관', 'ntceInsttNm': '발주기관',
                'bidNtceDt': '2026-05-03 10:00:00', 'bidClseDt': '2026-05-20 10:00:00', 'asignBdgtAmt': budget, 'reNtceYn': 'N'}
    write_jsonl(root / 'bids.jsonl', [
        bid('R1', '000', '데이터센터 증설', '용역', 'SW 및 시스템 개발'),
        bid('R1', '001', '데이터센터 증설(정정)', '용역', 'SW 및 시스템 개발'),
        bid('R2', '000', '청소 용역', '용역', '시설물관리'),
        bid('R3', '000', '실태조사', '용역', '학술연구서비스'),
    ])
    ws = root.as_posix()

    def m(key, sha, name, status, extra=None):
        row = dict(status=status, bid=dict(bid_key=key), attachment=dict(filename=name))
        if status != 'skipped_duplicate':
            ext = name.rsplit('.', 1)[1]
            row.update(document_id=sha, raw_path=f'{ws}/raw/aa/{sha}.{ext}', parsed_path=f'{ws}/parsed/{sha}.json', cached=True)
        return row
    write_jsonl(root / 'manifest.jsonl', [
        m('R1-001', 'aa01', '입찰공고문.hwp', 'parsed'),
        # manifest 는 옛 failed 지만 나중에 재파싱되어 chunk_ready 에 들어간 문서: parsed 로 승격되어야 한다
        m('R1-001', 'aa02', '제안요청서.hwp', 'failed'),
        m('R1-001', None, '제안요청서.pdf', 'skipped_duplicate'),
        m('R1-000', 'aa01', '입찰공고문.hwp', 'parsed'),
        m('R2-000', 'aa01', '입찰공고문.hwp', 'parsed'),
        # 같은 문서가 다른 공고(R2)에도 붙어 있고 manifest 는 failed, chunk_ready 에는 R1 행만 있음
        # → parsed JSON 상태(parsed)를 보고 R2 에서도 parsed 로 승격되어야 한다
        m('R2-000', 'aa02', '제안요청서.hwp', 'failed'),
        m('R3-000', 'aa03', '과업지시서.pdf', 'low_quality'),
    ])
    write_jsonl(root / 'chunk_ready.jsonl', [
        dict(document_id='aa01', bid=dict(bid_key='R1-001'), attachment=dict(filename='입찰공고문.hwp'), parsed_path=f'{ws}/parsed/aa01.json', selection=dict(reason='single_attachment')),
        dict(document_id='aa02', bid=dict(bid_key='R1-001'), attachment=dict(filename='제안요청서.hwp'), parsed_path=f'{ws}/parsed/aa02.json', selection=dict(reason='same_name_multi_format_best_available')),
        dict(document_id='aa01', bid=dict(bid_key='R2-000'), attachment=dict(filename='입찰공고문.hwp'), parsed_path=f'{ws}/parsed/aa01.json', selection=dict(reason='single_attachment')),
    ])
    return root


class AdapterTest(unittest.TestCase):
    def test_adapter_then_prepare(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = fake_month(Path(tmp) / '2026-05')
            r = subprocess.run([sys.executable, str(HERE / 'adapt_g2b.py'), '--src', str(src)], capture_output=True, text=True, encoding='utf-8', errors='replace')
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = {(x['notice_id'], x['version']): x for x in map(json.loads, (src / 'adapter' / 'manifest.jsonl').open(encoding='utf-8'))}
            self.assertEqual(set(rows), {('R1', '001'), ('R2', '000'), ('R3', '000')}, '최신 차수만 남아야 한다')
            a = rows[('R1', '001')]
            self.assertEqual(a['sector'], '용역·SW 및 시스템 개발')
            self.assertEqual([x['kind'] for x in a['attachments']], ['notice', 'rfp'], 'skipped_duplicate 는 첨부에서 빠진다')
            self.assertTrue(all(x['integrity_ok'] for x in a['attachments']))
            self.assertEqual(a['budget_krw'], 1000000)
            c = rows[('R3', '000')]['attachments'][0]
            self.assertFalse(c['integrity_ok']); self.assertEqual(c['parse_status'], 'low_quality'); self.assertIsNone(c['text_path'])
            # 텍스트 JSONL: 문단 하나짜리 HWP가 제목 패턴으로 여러 구간이 되고 offset_scope 계약(page/section/text)을 지킨다
            secs = [json.loads(l) for l in (src / a['attachments'][1]['text_path']).open(encoding='utf-8')]
            self.assertGreater(len(secs), 1)
            self.assertTrue(all(set(s) == {'page', 'section', 'text'} for s in secs))
            report = json.loads((src / 'adapter' / 'adapt_report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['promoted_by_chunk_ready'], 2, 'chunk_ready 또는 parsed JSON 상태로 승격된 문서 2건')
            r2 = rows[('R2', '000')]
            self.assertEqual(sorted(x['kind'] for x in r2['attachments']), ['notice', 'rfp'])
            self.assertTrue(all(x['integrity_ok'] for x in r2['attachments']), 'R2 의 제안요청서도 parsed JSON 기준으로 사용 가능')
            self.assertEqual(report['notices_dropped_old_version'], 1)
            self.assertEqual(report['status']['skipped_duplicate'], 1)
            # prepare.py 가 그대로 받아서 완전 공고(공고문+제안요청서) 1건을 추천한다
            r = subprocess.run([sys.executable, str(HERE / 'prepare.py'), '--input', str(src / 'adapter' / 'manifest.jsonl'),
                                '--root', str(src), '--out', str(Path(tmp) / 'out'), '--n', '1', '--min-sector', '1'],
                               capture_output=True, text=True, encoding='utf-8', errors='replace')
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = json.loads((Path(tmp) / 'out' / 'sector_report.json').read_text(encoding='utf-8'))
            self.assertEqual(rep['recommended'], '용역·SW 및 시스템 개발')
            packets = [json.loads(l) for l in (Path(tmp) / 'out' / 'packets.jsonl').open(encoding='utf-8')]
            self.assertEqual(len(packets), 1)
            self.assertTrue(any('서버 랙 50식' in c['text'] for c in packets[0]['chunks']))


if __name__ == '__main__':
    unittest.main()
