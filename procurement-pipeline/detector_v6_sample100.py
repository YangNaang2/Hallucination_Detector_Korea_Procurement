"""One fixed post-experiment sample; never search seeds or tune on results."""
import argparse,collections,hashlib
from pathlib import Path
import detector_v6_report as r

def run(out):
 g=r.g;split=g.load(g.OUT/'protocol.json')['split'];pool=sorted(q for q in split if split[q]!='train')
 policy=dict(scope='original generated answers; exclude current train partition; historically exposed development/comparison, NOT independent test',selection='first 100 IDs sorted by SHA256 of fixed prefix v6-sample100-once: plus question_id; no predictions or labels used for selection; one draw only',candidate_count=len(pool),question_ids=sorted(pool,key=lambda q:hashlib.sha256(('v6-sample100-once:'+q).encode()).hexdigest())[:100],human_approved=False,labels='reuse existing evidence-based provisional agent labels; not 100 fresh human annotations')
 path=g.OUT/'sample100/policy.json'
 if path.exists():assert g.load(path)==policy
 else:g.save(path,policy)
 qs=policy['question_ids'];assert len(qs)==len(set(qs))==100 and all(split[q]!='train' for q in qs)
 answers={q:r.k.inputs(q)['actual_answer'] for q in qs};labels=r.k.labels();report=dict(policy_sha256=g.file_sha(path),partitions=dict(collections.Counter(split[q] for q in qs)),arms={})
 for arm in ['v3','v6']:
  preds={q:r.k.pred_from(q,r.s.raw(q,'mil3'),'min2',.5) if arm=='v3' else g.load(g.OUT/'original_predictions'/f'{q}.json') for q in qs}
  met,rows=r.detailed(qs,labels,preds,answers);z=met['operational_whole_answer'];den=z['tp']+z['tn']+z['fp']+z['fn'];z['accuracy']=(z['tp']+z['tn'])/den if den else None;z['scored_answers']=den;report['arms'][arm]=met;g.save(g.OUT/'sample100'/f'{arm}-rows.json',rows)
 g.save(g.OUT/'sample100/results.json',report)
 text='''# 기존 답변 100건 잠정 평가

RAG 시스템의 300개 평가 레코드 중 생성 답변은 295건이며 접근 차단은 5건입니다. 현재 학습 분할을 제외한 개발·비교 자료 113건에서 예측·정답을 사용하지 않는 고정 해시 순서로 100건을 한 번 선정했습니다. **이미 노출된 자료에 대한 사후 탐색 평가이며 독립 테스트가 아닙니다. 기존 에이전트 근거 대조 라벨을 재사용했고, 100건의 새 사람 검수가 아닙니다.**

정확도는 (TP+TN)/(TP+TN+FP+FN)입니다. 판단 불확실한 정답은 정상으로 계산하지 않고 제외합니다. 모델은 보류하지 않으며 모든 100건에서 자동 경고 여부를 냈습니다.

| 모델 | 채점 가능 / 선정 | 정확도 | 정밀도 | 재현율 | 답변 F1 | TP / FP / FN / TN | 문자 F1 |
|---|---:|---:|---:|---:|---:|---|---:|
'''
 for arm,met in report['arms'].items():
  z=met['operational_whole_answer'];pct=lambda n:f'{100*n:.2f}%'
  text+=f"| {arm} | {z['scored_answers']} / 100 | {pct(z['accuracy'])} | {pct(z['precision'])} | {pct(z['recall'])} | {pct(z['f1'])} | {z['tp']} / {z['fp']} / {z['fn']} / {z['tn']} | {pct(met['characters']['f1'])} |\n"
 text+='\n문자 지표는 기존 마스킹 정책을 유지합니다. 답변 지표는 실제 경고 유무 기준이며, 정답이 불확실한 사례를 제외한 분모를 명시합니다. 성공 사례 50건 데모와 이 100건 평가는 서로 다른 목적입니다. 80%에 맞추기 위한 재추출·라벨 변경·임계값 변경은 하지 않았습니다.\n'
 (g.OUT/'sample100/README.md').write_text(text);out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'KLUE_100건_실제평가.md').write_text(text)
 print(text)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)
