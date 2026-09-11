import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from common import jsonl
from prepare import audit, packet
from generate import validate, assemble


def fixture(root, n=8):
    rows=[]
    for i in range(n):
        attachments=[]
        for j,kind in enumerate(['notice','rfp','spec']):
            name=f'{i}-{j}.txt'
            (root/name).write_text('fixture source',encoding='utf-8')
            jsonl(root/(name+'.jsonl'),[dict(page=1,section='제4조',text='납품 필수 요건: 서버 랙 50식을 설치하여야 한다. 예산은 별도 공고 참조.')])
            attachments.append(dict(document_id=name,name=name,kind=kind,path=name,
                text_path=name+'.jsonl',download_status='ok',parse_status='ok',integrity_ok=True))
        rows.append(dict(notice_id=f'TEST{i}',version='1',sector='AI' if i<6 else '건설',
            title='가상 검증 공고',month='2026-05',agency=f'테스트기관{i%2}',budget_krw=100000000,
            attachments=attachments))
    jsonl(root/'manifest.jsonl',rows)
    return rows


class PipelineTest(unittest.TestCase):
    def test_missing_and_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();r=fixture(root)[0]
            r['attachments'].append(dict(r['attachments'][0]))
            a=audit(r,root)
            self.assertEqual(len(a['attachments']),3)
            self.assertTrue(a['complete'])
            (root/'0-2.txt').unlink()
            self.assertFalse(audit(r,root)['complete'])

    def test_quotes_and_no_invented_location(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();r=fixture(root)[0]
            p=packet(audit(r,root),root,1000)
            c=p['chunks'][0]
            v={'company_name':'가상 테스트기업','records':[
                dict(level=level,kind=kind,title='가상 자료',content='합성 가정: 금액 미설정',
                     chunk_id=c['chunk_id'],quote='서버 랙 50식을 설치하여야 한다.')
                for level,kind in [('L2','performance'),('L3','cost')]]}
            output=assemble(validate(v,p),p)
            self.assertEqual(output['records'][0]['security_level'],'L2')
            self.assertEqual(output['records'][1]['security_level'],'L3')
            self.assertNotIn('spatial_L2',output)
            self.assertTrue(output['company']['synthetic'])
            v['records'][0]['quote']='서버 랙 500식을 설치하여야 한다.'
            with self.assertRaises(ValueError):validate(v,p)

    def test_end_to_end_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();fixture(root)
            here=Path(__file__).parent
            subprocess.run([sys.executable,str(here/'prepare.py'),'--input',str(root/'manifest.jsonl'),
                '--root',d,'--out',str(root/'out'),'--n','4','--min-sector','3'],check=True)
            report=json.loads((root/'out/sector_report.json').read_text(encoding='utf-8'))
            self.assertEqual(report['recommended'],'AI')
            subprocess.run([sys.executable,str(here/'generate.py'),'--packets',str(root/'out/packets.jsonl'),
                '--out',str(root/'generated')],check=True)
            self.assertEqual(len(list((root/'generated/requests').glob('*.json'))),4)


if __name__=='__main__':unittest.main()
