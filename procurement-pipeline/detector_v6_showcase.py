"""Build an explicitly post-selected demonstration, never a benchmark."""
import argparse,collections,html
from pathlib import Path
import detector_v6_report as r

def build(destination):
 g=r.g;split=g.load(g.OUT/'protocol.json')['split'];labels=r.k.labels();buckets={'normal':[],'detected':[]}
 for q in sorted(split,key=lambda q:({'evaluation':0,'dev':1,'train':2}[split[q]],q)):
  x=r.k.inputs(q);l=labels[q];p=g.load(g.OUT/'original_predictions'/f'{q}.json');score=r.score_one(l,p,x['actual_answer'])
  category=None
  if not l['spans'] and not p['spans']:category='normal'
  if any(s['label'] in r.POS for s in l['spans']) and not any(s['label']=='uncertain' for s in l['spans']) and score['characters']['tp']>0 and score['characters']['precision']>=.5:category='detected'
  if category:buckets[category].append(dict(question_id=q,partition=split[q],category=category,answer_sha256=g.sha(x['actual_answer']),context_sha256=g.sha(x['context']),labels=l['spans'],warnings=p['spans'],character_metrics=score['characters']))
 chosen=buckets['normal'][:25]+buckets['detected'][:25];assert len(chosen)==50
 counts=dict(collections.Counter(z['partition'] for z in chosen))
 report=dict(title='정답 확인 후 선별한 KLUE 동작 시연 50건',purpose='post-selected success demonstration; NOT evaluation or generalization evidence',selection='fixed current v6 predictions, 25 label-empty no-warning answers; 25 positive answers with character overlap and warning precision >= .5; no uncertain label; evaluation then dev then train, ID order',source_answers=295,source_access_denials=5,selected=50,partition_counts=counts,model=g.load(g.OUT/'selection.json')['selected'],human_approved=False,all_partitions_historically_exposed=True,source_label_path=str(r.k.LABELS) if hasattr(r.k,'LABELS') else 'results-v1/annotation/adjudicated/proposals.json',labels_digest=g.jsha(labels),code_sha256=g.file_sha(__file__),candidates={key:len(value) for key,value in buckets.items()},cases=chosen)
 g.save(g.OUT/'showcase/manifest.json',report)
 destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
 summary=f'''# KLUE 성공 사례 시연 50건

**정답을 확인한 뒤 선별한 데모입니다. 전체 성능·독립 테스트 결과가 아닙니다. 라벨은 사람 최종 승인 전입니다.**

- 원본: 생성 답변 295건. 접근 차단 5건은 별도 보존.
- 선정: 정상 무경고 25건 + 실제 환각 구절을 포착한 25건.
- 구성: 비교 자료 {counts.get('evaluation',0)}건, 개발 자료 {counts.get('dev',0)}건, 학습 자료 {counts.get('train',0)}건. 모두 이전에 노출된 자료입니다.
- 환각 사례는 경고 문자와 정답 오류 문자가 겹치고, 경고 문자 정밀도가 50% 이상인 사례입니다. 모든 오류 구절을 정확히 찾았다는 뜻은 아닙니다.

## 전체 비교 결과도 함께 제시

동일한 기존 비교 63건·잠정 라벨 기준입니다.

| 구성 | 정상 오탐 / 28 | 환각 포착 / 35 | 답변 정밀도 | 답변 재현율 | 답변 F1 | 문자 F1 |
|---|---:|---:|---:|---:|---:|---:|
| 기존 v3 | 21 | 32 | 60.38% | 91.43% | 72.73% | 31.13% |
| v6 후보 | 14 | 27 | 65.85% | 77.14% | 71.05% | 24.89% |

오탐은 7건 감소했지만 환각을 5건 더 놓쳤습니다. **정상 오탐 0건 및 전반적 성능 개선 목표는 미달입니다.**

## 발표 문구

> KLUE 기반 환각 탐지 시스템을 구현하고 295개 기존 답변에 적용했습니다. 여기서는 정상 답변을 경고하지 않은 사례와 실제 환각 구절을 포착한 사례 50건을 선별해 동작을 시연합니다. 이 사례집은 전체 정확도를 나타내지 않습니다. 전체 비교에서는 정상 오탐 감소와 환각 누락 증가의 상충 관계가 남아 있습니다.

‘50건에서 100% 정확도’, ‘환각 탐지 성공률 100%’, ‘전체 프로젝트 성능 검증 완료’로 발표하지 않습니다.

## 사례 목록

| ID | 구분 | 자료 구분 |
|---|---|---|
'''
 partnames={'train':'학습','dev':'개발','evaluation':'노출된 비교'}
 for z in chosen:summary+=f"| {z['question_id']} | {'정상 무경고' if z['category']=='normal' else '환각 구절 포착'} | {partnames[z['partition']]} |\n"
 (destination/'KLUE_선별시연_50건.md').write_text(summary)
 (g.OUT/'showcase/README.md').write_text(summary)
 page=['<!doctype html><html lang="ko"><meta charset="utf-8"><title>KLUE 선별 시연 50건</title><style>body{font:16px/1.65 sans-serif;max-width:1100px;margin:35px auto;padding:20px;background:#fafafa;color:#17202a}header{position:sticky;top:0;background:#fff4cc;padding:16px;border:2px solid #c98800}article{background:white;border:1px solid #ddd;padding:20px;margin:24px 0}pre{white-space:pre-wrap;font:inherit}mark{background:#ffd3d3}small{color:#555}details{border-top:1px solid #ddd;padding:10px}h1{font-size:25px}</style>']
 page.append('<header><h1>정답 확인 후 선별한 성공 사례 50건</h1><b>전체 성능·독립 평가가 아닙니다. 잠정 에이전트 라벨입니다.</b><br>기존 비교 63건: v6 정상 오탐 14/28, 환각 포착 27/35. 목표 미달.</header>')
 for z in chosen:
  x=r.k.inputs(z['question_id']);a=x['actual_answer'];warn=set()
  for span in z['warnings']:warn.update(range(span['start'],span['end']))
  pieces=[];opened=False
  for i,ch in enumerate(a):
   active=i in warn
   if active!=opened:pieces.append('<mark>' if active else '</mark>');opened=active
   pieces.append(html.escape(ch))
  if opened:pieces.append('</mark>')
  page.append(f"<article><h2>{html.escape(z['question_id'])} · {'정상 무경고' if z['category']=='normal' else '환각 구절 포착'}</h2><small>{partnames[z['partition']]} 자료 · 정답 확인 후 선별 · 빨간색은 실제 모델 경고</small><h3>{html.escape(x['question'])}</h3><pre>{''.join(pieces)}</pre><details><summary>잠정 오류 라벨과 근거 연결</summary>")
  if not z['labels']:page.append('<p>기존 잠정 라벨에 오류 구절 없음. 모델 경고 없음.</p>')
  for span in z['labels']:page.append('<pre>'+html.escape(str(span))+'</pre>')
  page.append('<p>실제 생성 근거 ID: '+html.escape(', '.join(e['chunk_id'] for e in x['evidence']))+'</p></details></article>')
 page.append('</html>');(destination/'KLUE_선별시연_50건.html').write_text('\n'.join(page))
 print(dict(selected=len(chosen),partitions=counts,candidates=report['candidates']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);build(p.parse_args().output)
