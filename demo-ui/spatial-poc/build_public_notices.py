"""Build the public demo projection from the sample manifest and reviewed sheet.

No source attachments, company documents, answers or inferred site coordinates.
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'project-docs/표본_정보시스템'
with (SOURCE / '검수/요건추출시트_51건_통합.csv').open(encoding='utf-8-sig', newline='') as f:
    sheet = list(csv.DictReader(f))
with (SOURCE / '표본_목록.csv').open(encoding='utf-8-sig', newline='') as f:
    samples = list(csv.DictReader(f))
by_id = {r['공고번호']: r for r in sheet}
assert len(by_id) == len(sheet) == len(samples) == 51
fields = {
    '참가자격_업종면허': '참가 자격', '실적조건_금액건수기간': '실적 조건',
    '투입인력_등급인원자격': '인력 조건', '인증요구_ISO_CMMI_GS_SW사업자': '인증',
    '예산_추정가_하도급비율': '금액·하도급', '일정_마감_개찰_사업기간': '일정',
    '평가배점_기술가격': '평가', '특이조건_지역제한_공동수급_보안': '특이 조건',
    '근거문서_쪽수': '근거 문서·위치', '검토메모': '검토 메모',
}
records = []
for m in samples:
    r = by_id[m['bid_key']]
    assert int(r['예산(공고정보)']) == int(m['budget'])
    requirements = [{'label': label, 'text': r[key]} for key, label in fields.items() if r[key].strip()]
    records.append(dict(id=m['bid_key'], title=m['title'].strip(), agency=m['agency'],
                        budget=int(m['budget']), month=m['month'], sector=m['sector'],
                        deadline=m['deadline'] or None, url=m['url'],
                        attachmentCount=int(m['docs']), requirements=requirements,
                        reviewAvailable=bool(requirements), conditionMentions=[label for label, pattern in {"지역": "지역|본점|본사", "직접생산": "직접생산", "공동수급": "공동수급|공동이행|분담이행", "하도급": "하도급", "서비스 인증": "CSAP|서비스 인증"}.items() if re.search(pattern, " ".join(x["text"] for x in requirements), re.I)]))
payload = dict(scope='나라장터 정보시스템 구축·운영 표본', records=records,
               source='표본_목록.csv / 요건추출시트_51건_통합.csv',
               locationPolicy='기관명에 명시된 지역의 대표점이며 기관 주소·사업장·참가기업 위치가 아님')
target = Path(__file__).parent / 'dist/public-notices.json'
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(f'{len(records)} notices, {sum(r["reviewAvailable"] for r in records)} extraction sheets -> {target.name}')
