"""Post-selected success examples, explicitly not a performance benchmark."""
import collections
from pathlib import Path
import detector_v6_report as r

def run():
 g=r.g;split=g.load(g.OUT/'protocol.json')['split'];labels=r.k.labels();pool={'normal':[],'detected':[]};preds={};answers={}
 for q in sorted(split,key=lambda q:({'evaluation':0,'dev':1,'train':2}[split[q]],q)):
  l=labels[q];p=g.load(g.OUT/'original_predictions'/f'{q}.json');a=r.k.inputs(q)['actual_answer'];z=r.score_one(l,p,a);preds[q]=p;answers[q]=a
  if not l['spans'] and not p['spans']:pool['normal'].append(q)
  if any(s['label'] in r.POS for s in l['spans']) and not any(s['label']=='uncertain' for s in l['spans']) and z['characters']['tp']>0 and z['characters']['precision']>=.5:pool['detected'].append(q)
 qs=pool['normal'][:50]+pool['detected'][:50];assert len(qs)==len(set(qs))==100
 met,rows=r.detailed(qs,labels,preds,answers);z=met['operational_whole_answer'];assert z['fp']==z['fn']==0 and z['tp']==z['tn']==50
 counts=dict(collections.Counter(split[q] for q in qs));met['operational_whole_answer']['accuracy']=1.
 manifest=dict(purpose='post-selected successful examples; NOT model performance estimate',selection='50 label-empty no-warning + 50 actual positive with overlapping warnings and character precision >= .5; no uncertain labels; evaluation then dev then train then ID; selected AFTER viewing labels and predictions',partition_counts=counts,human_approved=False,model=g.load(g.OUT/'selection.json')['selected'],code_sha256=g.file_sha(__file__),labels_sha256=g.jsha(labels),source_answers=295,question_ids=qs,metrics=met)
 g.save(g.OUT/'showcase100/manifest.json',manifest);g.save(g.OUT/'showcase100/rows.json',rows)
 c=met['characters'];e=met['exact_spans'];text=f'''# 정답 확인 후 선별한 성공 사례 100건

**성공 사례를 사후 선별한 시연용 집합입니다. 전체 성능이나 독립 테스트 결과가 아닙니다. 기존 사람 미승인 에이전트 라벨 기준입니다.**

- 원본 생성 답변 295건에서 정상 무경고 50건, 실제 환각 구절을 포착한 50건을 골랐습니다.
- 학습 {counts.get('train',0)}건, 개발 {counts.get('dev',0)}건, 기존 노출 비교 {counts.get('evaluation',0)}건입니다.
- 선별 집합의 답변 정확도·정밀도·재현율·F1: 모두 **100%** (TP 50, TN 50, FP 0, FN 0). 맞힌 답변만 골랐으므로 생기는 값이며 모델의 일반 성능을 입증하지 않습니다.
- 선별 집합의 문자 정밀도 **{100*c['precision']:.2f}%**, 재현율 **{100*c['recall']:.2f}%**, F1 **{100*c['f1']:.2f}%**. 정확한 구절 경계 exact-span F1 **{100*e['f1']:.2f}%**. 오류 구절 전체를 완벽하게 탐지했다는 뜻이 아닙니다.
- 별도로 고정 추출한 100건의 실제 잠정 평가에서는 채점 가능 96건의 정확도가 **67.71%**였습니다.

발표 문구: “정상 답변 무경고와 환각 포착이 성공한 사례 100건을 선별하여 시스템 동작을 시연했습니다.”

| ID | 사례 | 자료 구분 |
|---|---|---|
'''
 for q in qs:text+=f"| {q} | {'정상 무경고' if q in pool['normal'] else '환각 구절 포착'} | {split[q]} |\n"
 (g.OUT/'showcase100/README.md').write_text(text)
 out=Path('/home/piai/Documents/Codex/2026-09-15/yangnaang2-ko-lettucedetect-fetch-origin-feature/outputs');(out/'KLUE_선별성공_100건.md').write_text(text)
 print(dict(counts=counts,answer=z,characters=c,exact=e))
if __name__=='__main__':run()
