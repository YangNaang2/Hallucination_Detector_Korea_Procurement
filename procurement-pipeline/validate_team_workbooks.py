"""Read-only XLSX validation against the original 25 annotation drafts."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / 'project-docs/환각라벨링/pilot-25-v1'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def cells(z, sheet, strings):
    tree = ET.fromstring(z.read(f'xl/worksheets/sheet{sheet}.xml'))
    rows = []
    for row in tree.findall('.//m:sheetData/m:row', NS):
        if int(row.attrib['r']) < 5:
            continue
        values = {}
        for c in row.findall('m:c', NS):
            assert c.get('t') != 'e', c.attrib
            v = c.find('m:v', NS)
            text = v.text if v is not None else ''.join(c.find('m:is', NS).itertext()) if c.find('m:is', NS) is not None else ''
            if c.get('t') == 's':
                text = strings[int(text)]
            values[''.join(x for x in c.attrib['r'] if x.isalpha())] = text
        if values.get('A'):
            rows.append(values)
    return rows


def main():
    labels = {r['question_id'].removeprefix('ASTRA-300-'): r for r in map(json.loads, (PILOT / 'labels_draft.jsonl').read_text(encoding='utf8').splitlines())}
    delivery = PILOT / 'team-delivery'
    groups = json.loads((delivery / 'assignments.json').read_text(encoding='utf8'))['groups']
    report = {'workbooks': [], 'human_approval': 'pending', 'export_runtime_exit_code': 1,
              'export_limitation': 'Artifact runtime reported export success then exited 1 without an error. ZIP/XML and exact content independently verified.',
              'scope': 'Structural and exact content checks; no human label approval.'}
    for group in groups:
        workbook = next((delivery / group['team_id']).glob('*.xlsx'))
        expected = {q.removeprefix('ASTRA-300-') for q in group['question_ids']}
        with zipfile.ZipFile(workbook) as z:
            assert z.testzip() is None
            strings = [''.join(s.itertext()) for s in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
            sheets = ET.fromstring(z.read('xl/workbook.xml')).findall('m:sheets/m:sheet', NS)
            assert len(sheets) == 6
            index = cells(z, 1, strings)
            assert {r['A'] for r in index} == expected and len(index) == len(expected)
            assert all(r['F'] == 'pending' for r in index)
            spans = cells(z, 2, strings)
            assert len(spans) == group['span_rows'] and all(r['I'] == 'pending' for r in spans)
            for r in spans:
                assert labels[r['A']]['actual_answer'][int(r['G']):int(r['H'])] == r['C']
            parts = cells(z, 4, strings)
            for q in expected:
                pieces = sorted([r for r in parts if r['A'] == q], key=lambda r: int(r['B']))
                assert ''.join(r['C'] for r in pieces) == labels[q]['actual_answer']
                for p in pieces:
                    assert labels[q]['actual_answer'][int(p['D']):int(p['E'])] == p['C']
            for r in cells(z, 6, strings):
                assert r['C'] == labels[r['A']]['expected_answer']
            report['workbooks'].append({'team_id': group['team_id'], 'questions': len(index), 'span_rows': len(spans), 'sheets': 6, 'exact_answers_and_offsets': 'passed'})
    (delivery / 'workbook_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
