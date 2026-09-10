from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
root=Path(__file__).parent
sectors=json.loads((root/'twin-export.json').read_text(encoding='utf-8'))
pdfmetrics.registerFont(TTFont('Korean','C:/Windows/Fonts/malgun.ttf'))
out=root/'dist'/'twin-pdfs';out.mkdir(exist_ok=True)
for s in sectors:
 c=canvas.Canvas(str(out/(s['id']+'.pdf')),pagesize=(595,842));c.setTitle(s['title']+' / 가상 문서 모음')
 for i,d in enumerate(s['docs']):
  c.setFillColor(HexColor('#0b192b'));c.rect(0,770,595,72,fill=1,stroke=0);c.setFillColor(HexColor('#adf1dd'));c.setFont('Korean',12);c.drawString(45,798,'ASTRA / VIRTUAL META-TWIN / 합성 문서')
  c.setFillColor(HexColor('#142338'));c.setFont('Korean',22);c.drawString(45,716,d['name']);c.setFont('Korean',12);c.drawString(45,685,s['title'][:35]);c.drawString(45,666,s['title'][35:]);c.setFont('Korean',10);c.drawString(45,653,d['id']+' | '+s['company']+' | '+str(i+1)+'/12')
  c.setStrokeColor(HexColor('#c7d1d8'));c.line(45,630,550,630);c.setFont('Korean',14);c.drawString(45,594,d['section']);c.setFont('Korean',12)
  lines=[];line=''
  for char in d['text']:
   if pdfmetrics.stringWidth(line+char,'Korean',12)>470:lines.append(line);line=''
   line+=char
  if line:lines.append(line)
  c.setFillColor(HexColor('#edf6dc'));c.rect(40,540-len(lines)*24,510,len(lines)*24+34,fill=1,stroke=0);c.setFillColor(HexColor('#182e3c'))
  for j,line in enumerate(lines):c.drawString(50,550-j*24,line)
  c.setFont('Korean',11);c.drawString(45,345,'설비 연결 ID');c.drawString(45,319,s['equipment'][0]['id']+' : '+s['equipment'][0]['label']);c.drawString(45,295,s['equipment'][1]['id']+' : '+s['equipment'][1]['label'])
  c.setFont('Korean',10);c.setFillColor(HexColor('#687481'));c.drawString(45,103,'실제 나라장터 공고가 아닙니다. 모델 평가·법적 근거로 사용할 수 없습니다.');c.drawString(45,82,'단일 수치 규칙 검사 및 문서-설비 연결을 위한 고정 시나리오입니다.')
  c.showPage()
 c.save()
print('4 PDFs / 48 pages generated from shared scenario data')
