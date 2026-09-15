"""Link preserved pilot labels and explicit manual reviews; never fill unreviewed negatives."""
import json,re
from detector300 import ROOT,BASE,OUT,PRIVATE,load,save,sha,file_sha,frozen
from detector300_review_specs import SPECS

def jsonl(p):return [json.loads(l) for l in p.read_text().splitlines() if l]
def anchor_ref(x,needle,citation=None):
 for c in x['evidence']:
  if citation is not None and c['citation']!=citation:continue
  number=c['citation']
  m=re.search(r'^\['+str(number)+r'\][^\n]*\n(.*?)\n\[자료 '+str(number)+r' 끝\]',x['context'],re.S|re.M)
  if m and needle in m.group(1):
   offset=m.group(1).index(needle);start=m.start(1)+offset
   return dict(scope='prompt_context',citation=number,chunk_id=c['chunk_id'],text_sha256=c['text_sha256'],quote=needle,context_start=start,context_end=start+len(needle),source_start=c['text_start']+offset,source_end=c['text_start']+offset+len(needle))
 raise ValueError('anchor not in specified evidence chunk: '+str(citation)+' '+needle)

def build():
 pilot=ROOT/'project-docs/환각라벨링/pilot-25-v1/labels_draft.jsonl'
 adjud=ROOT/'project-docs/환각라벨링/pilot-25-human-review-v1/adjudication_proposals.jsonl'
 submitted=ROOT/'project-docs/환각라벨링/pilot-25-human-review-v1/submitted_reviews.jsonl'
 old={r['question_id']:r for r in jsonl(pilot)};adj={r['question_id']:r for r in jsonl(adjud)}
 rows=[];integrated=[]
 for r in frozen():
  if not r['detector_target']:continue
  q=r['question_id'];x=load(PRIVATE/'inputs'/f'{q}.json');a=x['actual_answer']
  row=dict(question_id=q,answer_sha256=r['answer_sha256'],context_sha256=x['context_sha256'],status='unreviewed',reviewed_ranges=[],spans=None,human_approval='pending',approved_spans=None,training_ready=False,posthoc_source_truth='not_evaluated')
  if q in old:
   o=old[q];assert o['answer_sha256']==r['answer_sha256'] and o['actual_answer']==a
   row.update(status='reused_agent_draft',reviewed_ranges=[[0,len(a)]],spans=[s|dict(label=(s['label'] or 'quality_only').lower()) for s in o['draft_spans']+o['review_candidates']],source=str(pilot.relative_to(ROOT)),source_sha256=file_sha(pilot),evidence=o['evidence'],note=o['agent_note'])
   d=adj[q];assert d['answer_sha256']==r['answer_sha256']
   integrated.append(row|dict(status='reused_adjudication_proposal',spans=[s|dict(label=(s['label'] or 'quality_only').lower()) for s in d['proposed_spans']],source=str(adjud.relative_to(ROOT)),source_sha256=file_sha(adjud),evidence=d['evidence']))
  elif q.removeprefix('ASTRA-300-') in SPECS:
   spec=SPECS[q.removeprefix('ASTRA-300-')];spans=[];evidence=[]
   for needle,label,reason,citation,anchor in spec['spans']:
    matches=list(re.finditer(re.escape(needle),a));assert matches,(q,needle)
    eid=f'{q}-E{len(evidence)+1}'
    evidence.append(anchor_ref(x,anchor,citation)|dict(evidence_id=eid))
    for m in matches:spans.append(dict(start=m.start(),end=m.end(),quote=m.group(),label=label,reason=reason,evidence_ids=[eid],human_decision='pending'))
   evidence.append(anchor_ref(x,spec['anchor'])|dict(evidence_id=q+'-REVIEW-ANCHOR'))
   row.update(status='agent_reviewed',reviewed_ranges=[[0,len(a)]],spans=spans,evidence=evidence,note=spec['note'],selection='manual_review_nonrandom',prediction_blind=True)
   integrated.append(row|dict(status='agent_draft_not_independently_adjudicated'))
  else:integrated.append(row.copy())
  for s in row['spans'] or []:assert a[s['start']:s['end']]==s['quote']
  rows.append(row)
 save(OUT/'annotation/agent_draft/labels.json',rows)
 save(OUT/'annotation/adjudicated/proposals.json',integrated)
 save(OUT/'annotation/human_submitted/references.json',dict(source=str(submitted.relative_to(ROOT)),sha256=file_sha(submitted),question_count=25,final_human_approval='pending'))
 save(OUT/'annotation/resume.json',dict(reviewed=sum(bool(r['reviewed_ranges']) for r in rows),remaining=[r['question_id'] for r in rows if not r['reviewed_ranges']],human_approval_pending=295,final_gold_count=0,annotation_rule='Read complete answer and complete recovered input before adding SPECS; do not use model predictions as gold.'))
 print('reviewed',sum(bool(r['reviewed_ranges']) for r in rows),'remaining',sum(not r['reviewed_ranges'] for r in rows))
if __name__=='__main__':build()
