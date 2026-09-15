"""Construct transparent post-selected demos at prescribed answer correctness rates."""
import collections,html
from pathlib import Path
import detector_v6_report as r

def run():
 g=r.g;split=g.load(g.OUT/'protocol.json')['split'];labels=r.k.labels();pool={k:[] for k in ['TP','TN','FP','FN']};preds={};answers={}
 for q in sorted(split,key=lambda q:({'evaluation':0,'dev':1,'train':2}[split[q]],q)):
  l=labels[q];p=g.load(g.OUT/'original_predictions'/f'{q}.json');a=r.k.inputs(q)['actual_answer'];preds[q]=p;answers[q]=a
  positive=any(s['label'] in r.POS for s in l['spans'])
  if any(s['label']=='uncertain' for s in l['spans']) or (not positive and l['spans']):continue
  score=r.score_one(l,p,a)
  if positive and p['spans'] and (score['characters']['tp']==0 or score['characters']['precision']<.5):continue
  kind='TP' if positive and p['spans'] else 'FN' if positive else 'FP' if p['spans'] else 'TN';pool[kind].append(q)
 out=Path('/home/piai/Documents/Codex/2026-09-15/yangnaang2-ko-lettucedetect-fetch-origin-feature/outputs');out.mkdir(parents=True,exist_ok=True)
 for rate,quotas in [(80,dict(TP=40,TN=40,FP=10,FN=10)),(85,dict(TP=42,TN=43,FP=7,FN=8))]:
  chosen=[(q,kind) for kind,n in quotas.items() for q in pool[kind][:n]];qs=[q for q,kind in chosen];assert len(qs)==len(set(qs))==100
  metrics,rows=r.detailed(qs,labels,preds,answers);z=metrics['operational_whole_answer'];assert all(z[k.lower()]==n for k,n in quotas.items());assert z['tp']+z['tn']==rate
  counts=dict(collections.Counter(split[q] for q in qs));manifest=dict(title=f'{rate}% 사후 구성 시연 세트',not_benchmark=True,selection_uses_ground_truth_and_predictions=True,purpose='Demonstration composed to target a prescribed answer correctness rate; NOT measured general model performance',requested_correct_rate=rate/100,actual_composed_correct_rate=(z['tp']+z['tn'])/100,quotas=quotas,partition_counts=counts,all_material_previously_exposed=True,human_approved=False,code_sha256=g.file_sha(__file__),labels_sha256=g.jsha(labels),configuration=g.load(g.OUT/'selection.json')['selected'],cases=[dict(question_id=q,outcome=kind,partition=split[q],answer_sha256=g.sha(answers[q]),prediction_sha256=g.jsha(preds[q]),label_sha256=g.jsha(labels[q])) for q,kind in chosen],metrics=metrics)
  target=g.OUT/f'demo-variants/{rate}';g.save(target/'manifest.json',manifest);g.save(target/'rows.json',rows)
  pct=lambda x:f'{x*100:.2f}%'
  text=f'''# {rate}% 사후 구성 시연 세트 — 모델 성능 평가 아님

**정답과 기존 예측을 확인한 뒤, 정답 판정이 {rate}건이 되도록 100건을 의도적으로 골랐습니다. 정상 50건·환각 50건입니다. 전체 정확도·독립 테스트 결과로 사용할 수 없습니다. 원본 답변·라벨·모델 예측은 변경하지 않았습니다. 사람 최종 승인 전 라벨입니다.**

| 구성 지표 | 값 |
|---|---:|
| 의도적으로 구성한 정답 비율 | {rate}/100 |
| 환각 포착 TP | {z['tp']} |
| 정상 무경고 TN | {z['tn']} |
| 정상 오탐 FP | {z['fp']} |
| 환각 누락 FN | {z['fn']} |
| 해당 선별 집합의 정밀도 | {pct(z['precision'])} |
| 해당 선별 집합의 재현율 | {pct(z['recall'])} |
| 해당 선별 집합의 답변 F1 | {pct(z['f1'])} |
| 해당 선별 집합의 문자 F1 | {pct(metrics['characters']['f1'])} |

자료 구성: 학습 {counts.get('train',0)}건, 개발 {counts.get('dev',0)}건, 노출된 비교 {counts.get('evaluation',0)}건. 성공률을 맞추기 위한 사후 선정이므로 일반화 성능을 추정할 수 없습니다. 별도 고정 100건의 실제 잠정 평가 정확도는 채점 가능 96건 기준 67.71%였습니다.

발표 설명: “성공과 실패 사례를 함께 보여주기 위해 정답 비율을 {rate}%로 구성한 시연 세트입니다.”

| ID | 사례 | 자료 분할 |
|---|---|---|
'''
  for q,kind in chosen:text+=f'| {q} | {kind} | {split[q]} |\n'
  (target/'README.md').write_text(text);(out/f'KLUE_사후구성_시연_{rate}.md').write_text(text)
  page=['<!doctype html><html lang="ko"><meta charset="utf-8"><title>사후 구성 시연 '+str(rate)+'%</title><style>body{font:16px/1.6 sans-serif;max-width:1050px;margin:30px auto;padding:15px;background:#f5f7fa}header{position:sticky;top:0;background:#fff0cb;border:2px solid #be8100;padding:16px}h1{font-size:24px}article{background:white;padding:20px;margin:18px 0;border:1px solid #ddd}pre{white-space:pre-wrap;font:inherit}mark{background:#ffd2d2}summary{cursor:pointer}</style>']
  page.append(f'<header><h1>{rate}% 사후 구성 시연 · 모델 성능 평가 아님</h1><b>정답과 예측을 보고 비율을 맞춘 100건입니다.</b><br>정상 50건 / 환각 50건 · TP {z["tp"]} / TN {z["tn"]} / FP {z["fp"]} / FN {z["fn"]}<br>학습 {counts.get("train",0)}건 포함 · 잠정 에이전트 라벨 · 독립 평가 아님</header>')
  names={'TP':'환각 포착','TN':'정상 무경고','FP':'정상 오탐','FN':'환각 누락'}
  for q,kind in chosen:
   a=answers[q];warn=set()
   for span in preds[q]['spans']:warn.update(range(span['start'],span['end']))
   parts=[];active=False
   for i,ch in enumerate(a):
    on=i in warn
    if on!=active:parts.append('<mark>' if on else '</mark>');active=on
    parts.append(html.escape(ch))
   if active:parts.append('</mark>')
   page.append(f'<article><h2>{html.escape(q)} — {names[kind]}</h2><p>{split[q]} · 사후 선별 · 빨간색은 모델 경고</p><h3>{html.escape(r.k.inputs(q)["question"])}</h3><pre>{"".join(parts)}</pre><details><summary>기존 잠정 라벨</summary><pre>{html.escape(str(labels[q]["spans"]))}</pre></details></article>')
  page.append('</html>');(out/f'KLUE_사후구성_시연_{rate}.html').write_text('\n'.join(page))
  print(dict(rate=rate,quotas=quotas,partitions=counts,precision=z['precision'],recall=z['recall'],f1=z['f1'],character_f1=metrics['characters']['f1']))
if __name__=='__main__':run()
