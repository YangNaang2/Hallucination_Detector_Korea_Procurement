"""Train-only exact source statements and numeric counterfactuals. Not test data."""
import re
from detector300 import sha,save

def build(k,det):
 cases=[];seen=set();bags=[]
 for q in k.selected_ids('train'):
  x=k.inputs(q);count=0
  for line in x['context'].splitlines():
   line=line.strip().lstrip('○⚪•- ')
   if not 35<=len(line)<=220 or not re.search(r'[가-힣]',line):continue
   matches=list(re.finditer(r'(?<![\dA-Za-z])\d{1,4}(?=\s*(?:%|명|원|년|월|일|개월|개|시간))',line))
   if not matches or sha(line) in seen:continue
   m=matches[0];new=str(int(m.group())+7)
   if new in x['context']:continue
   seen.add(sha(line));bad=line[:m.start()]+new+line[m.end():]
   for answer,span,typ in [(line,None,'exact_supported_source'),(bad,[m.start(),m.start()+len(new)],'synthetic_numeric_counterfactual')]:
    xx=dict(x,question='제공 문서의 해당 조건을 설명해 주세요.',actual_answer=answer);ids,off,bs=k.make_windows(det,xx,'repeat192');yy=[int(bool(span and a<span[1] and b>span[0])) for a,b in off]
    for a,b,ws in bs:bags.append((q,ws,yy[a:b]))
    cases.append(dict(source_question_id=q,kind=typ,answer=answer,positive_range=span,context_sha256=x['context_sha256'],source_quote=line))
   count+=1
   if count>=2:break
 save(k.WORK/'synthetic-cases.json',cases)
 return bags,dict(count=len(cases),source_ids=sorted({c['source_question_id'] for c in cases}),policy='train-only exact quotes and one numeric +7 mutation absent from full context; synthetic, not human labels')
