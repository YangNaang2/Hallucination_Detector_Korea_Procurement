"""Persist explicit agent evidence reviews; no automatic label decisions."""
import detector_v6_generate as g

def record(q,decisions,fulfillment='complete',omission='',note=''):
 x=g.load(g.PRIVATE/'inputs'/f'{q}.json');n=g.load(g.WORK/'generated'/f'{q}.json');spans=[]
 for d in decisions:
  quote,label,reason,citation=d;start=0;hits=[]
  while True:
   i=n['actual_answer'].find(quote,start)
   if i<0:break
   hits.append(i);start=i+len(quote)
  assert hits,(q,quote)
  for i in hits:spans.append(dict(start=i,end=i+len(quote),quote=quote,label=label,reason=reason,evidence_ids=[e['chunk_id'] for e in x['evidence'] if e['citation']==citation],human_decision='pending'))
 r=dict(question_id=q,answer_sha256=n['answer_sha256'],context_sha256=x['context_sha256'],spans=spans,reviewed_ranges=[[0,len(n['actual_answer'])]],review_status='agent evidence review; not human gold',human_approved=False,question_fulfillment=fulfillment,omission=omission,review_note=note)
 g.save(g.OUT/'new_agent_labels'/f'{q}.json',r)
