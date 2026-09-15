"""Conservative opt-in rules; uncertain extraction abstains. No question IDs or labels."""
import re
TOPICS=['하도급','우편','공동수급','계열사']
def rule_spans(answer,context):
 out=[]
 for topic in TOPICS:
  # Only explicit prohibition in an evidence line; exceptions/conditional clauses abstain.
  lines=[s for s in context.splitlines() if topic in s and re.search(r'(불가|불허|금지)',s)]
  lines=[s for s in lines if not re.search(r'경우|다만|예외|승인|허용|원칙|제외',s)]
  if not lines:continue
  for m in re.finditer(r'[^\n.!?]+[.!?]?',answer):
   sentence=m.group();plain=sentence.replace('*','')
   if topic not in plain or not re.search(r'가능하다|가능합니다|허용된다|허용됩니다|할 수 있다|할 수 있습니다',plain):continue
   if re.search(r'불가능|않|없|경우|다만|예외|승인|확인|여부|근거 부족|원칙',plain):continue
   out.append(dict(start=m.start(),end=m.end(),quote=m.group(),rule='explicit_prohibition_vs_affirmative',topic=topic,evidence=lines[0][:160]))
 return out
