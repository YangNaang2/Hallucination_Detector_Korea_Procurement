"""Evidence-based training-label revision. Original reviewer submissions untouched."""
import copy
import klue_review_priority as r
k=r.k

def main():
 source=k.BASE/'annotation/adjudicated/proposals.json';labels=k.load(source);by={x['question_id']:x for x in labels};changes=[]
 q='ASTRA-300-C03-N48-E1';x=k.inputs(q);span=next(s for s in by[q]['spans'] if s['start']==360 and s['end']==382);assert span['label']=='unsupported';assert x['actual_answer'][360:382]==span['quote'];before=copy.deepcopy(span)
 reason='현재 명시된 제출기한을 최종 마감일로 바꾸어 말한 것만으로 변경 불가능성을 단정한 것은 아니다. 실제 근거 [1]에 제출 종료 시각이 존재한다. 다른 메타데이터만/고정 주장 라벨은 그대로 유지한다.'
 span.update(label='supported',reason=reason,hallucination_target=False,agent_revision_status='approved_by_agent_under_user_delegation',previous_annotation=before)
 changes.append(dict(question_id=q,operation='replace_label',start=360,end=382,old='unsupported',new='supported',quote=span['quote'],reason=reason,evidence_quote='전자입찰(가격입찰, 제안발표회 자료) 제출기간',answer_sha256=x['answer_sha256'],context_sha256=x['context_sha256']))
 q='ASTRA-300-C05-N12-E4';x=k.inputs(q);quote='**부품 교체가 전혀 없을 경우**는 공고문에 명시된 **하드웨어 유지관리**의 범위를 벗어난 것으로 간주될 수 있으나';start=x['actual_answer'].index(quote);reason='근거 [2] MAR-002는 교체할 경우의 부품 조건을 정한다. 실제 교체가 발생하지 않으면 하드웨어 유지관리 범위 밖이라는 규정은 없다. 인용번호 오류와 별도인 근거 없는 조건 확장이다.'
 span=dict(start=start,end=start+len(quote),quote=quote,label='unsupported',reason=reason,evidence_ids=[q+'-INPUT-2'],human_decision='pending',final_human_approval='pending',agent_revision_status='approved_by_agent_under_user_delegation');by[q]['spans'].append(span)
 changes.append(dict(question_id=q,operation='add_span',**span,answer_sha256=x['answer_sha256'],context_sha256=x['context_sha256']))
 for change in changes:
  q=change['question_id'];assert k.protocol()['split'][q]=='train';x=k.inputs(q);assert x['actual_answer'][change['start']:change['end']]==change['quote']
 k.save(r.OUT/'annotation/agent-revised-labels.json',labels)
 k.save(r.OUT/'annotation/revisions.json',dict(source_sha256=k.file_sha(source),revised_sha256=k.file_sha(r.OUT/'annotation/agent-revised-labels.json'),status='agent-approved changes only; all other annotations retain original status; no human gold',authorization='User delegated judgement and changes in this task',review_scope='Two span decisions, not fresh full review of 295',changes=changes,retained=[dict(question_id='ASTRA-300-C05-N25-E1',decision='retain unsupported proposal-evaluation penalty claim: actual evidence only describes operational duties')]))
 # Compare identical predictions using both label versions. Training data, not effectiveness claim.
 old={x['question_id']:x for x in k.load(source)};qs=sorted({x['question_id'] for x in changes});report={}
 for model,path in [('original',k.BASE/'predictions/klue/common512-v2'),('v2',r.c.v.OLD/'predictions/all295'),('v3',k.OUT/'predictions/all295')]:
  report[model]={}
  for version,ls in [('original_labels',old),('agent_revised',by)]:
   rows=[]
   for q in qs:
    x=k.inputs(q);p=k.load(path/f'{q}.json');domain=k.expand(k.load(k.BASE/'predictions/klue/common512-v2'/f'{q}.json')['checked_ranges'],len(x['actual_answer']));rows.append(r.c.score_one(ls[q],p,x['actual_answer'],domain))
   report[model][version]=r.c.aggregate(rows)
 k.save(r.OUT/'annotation/paired-relabel-audit.json',dict(scope='Only two changed training answers; label effect, not model improvement',comparison=report,evaluation63_labels_unchanged=all(old[q]==by[q] for q in k.selected_ids('evaluation'))))
 print('2 evidence-based training label changes; comparison labels unchanged; all 3 models rescored on changed records')
if __name__=='__main__':main()
