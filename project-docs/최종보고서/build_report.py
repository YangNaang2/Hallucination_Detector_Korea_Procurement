"""Build the A4 report PDF and editable Markdown from reviewed source.

Requirements: reportlab, pypdf, pillow; build_assets.py additionally needs matplotlib.
Set REPORT_FONT / REPORT_FONT_BOLD for a Korean TrueType family on other systems.
No source documents, models, indexes or private data are bundled by this script.
"""
from __future__ import annotations
import hashlib
import html
import json
import os
import re
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle, Image, Spacer, HRFlowable
from PIL import Image as PILImage
from pypdf import PdfReader
from report_content import PAGES, TITLE, SUBTITLE, AUTHORS, DATE

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DEST=ROOT/'output/pdf/Blue_Jay_공공입찰_AI_종합보고서.pdf'
DEST.parent.mkdir(parents=True,exist_ok=True)
W,H=A4; LEFT=68; RIGHT=68; WIDTH=W-LEFT-RIGHT
NAVY=colors.HexColor('#183454'); BLUE=colors.HexColor('#24598B')
GREY=colors.HexColor('#5E6771'); LIGHT=colors.HexColor('#F0F2F4')
FONT=Path(os.environ.get('REPORT_FONT','C:/Windows/Fonts/malgun.ttf'))
BOLD=Path(os.environ.get('REPORT_FONT_BOLD','C:/Windows/Fonts/malgunbd.ttf'))
pdfmetrics.registerFont(TTFont('KR',str(FONT)))
pdfmetrics.registerFont(TTFont('KR-Bold',str(BOLD)))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KR-Bold',italic='KR',boldItalic='KR-Bold')

def esc(s):return html.escape(str(s)).replace('\n','<br/>')

def styles(reference=False):
    size=8.7 if reference else 10.2
    lead=12.9 if reference else 17.2
    return {
      'p':ParagraphStyle('p',fontName='KR',fontSize=size,leading=lead,textColor=colors.HexColor('#20252A'),wordWrap='CJK',alignment=TA_JUSTIFY),
      'h':ParagraphStyle('h',fontName='KR-Bold',fontSize=11.2,leading=17.5,textColor=GREY,wordWrap='CJK'),
      'note':ParagraphStyle('note',fontName='KR',fontSize=9,leading=14.3,textColor=GREY,wordWrap='CJK'),
      'caption':ParagraphStyle('caption',fontName='KR',fontSize=8.6,leading=13.2,textColor=GREY,wordWrap='CJK'),
      'cell':ParagraphStyle('cell',fontName='KR',fontSize=8.9,leading=13.5,textColor=colors.HexColor('#242A31'),wordWrap='CJK'),
      'th':ParagraphStyle('th',fontName='KR-Bold',fontSize=9,leading=13.5,textColor=colors.black,wordWrap='CJK'),
      'eq':ParagraphStyle('eq',fontName='KR-Bold',fontSize=10.3,leading=18,textColor=NAVY,alignment=TA_CENTER,wordWrap='CJK'),
    }

def block_flows(blocks,reference=False):
    st=styles(reference);out=[]
    for b in blocks:
        kind=b[0]
        if kind in ('p','h','note','equation'):
            key='eq' if kind=='equation' else kind
            if kind=='h':out.append(Spacer(1,4))
            out.append(Paragraph(esc(b[1]),st[key]));out.append(Spacer(1,7 if reference else (9 if kind!='h' else 7)))
        elif kind=='table':
            _,caption,headers,rows,widths=b
            out.append(Paragraph(esc(caption),st['caption']));out.append(Spacer(1,5))
            cells=[[Paragraph(esc(x),st['th']) for x in headers]]+[[Paragraph(esc(x),st['cell']) for x in row] for row in rows]
            widths=[WIDTH*x for x in widths] if widths else [WIDTH/len(headers)]*len(headers)
            t=Table(cells,colWidths=widths,hAlign='LEFT',repeatRows=1)
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('VALIGN',(0,0),(-1,-1),'TOP'),
              ('GRID',(0,0),(-1,-1),.45,colors.HexColor('#818890')),
              ('LINEABOVE',(0,0),(-1,0),.75,colors.HexColor('#353E47')),
              ('LEFTPADDING',(0,0),(-1,-1),6.5),('RIGHTPADDING',(0,0),(-1,-1),6.5),
              ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            out.extend([t,Spacer(1,11)])
        elif kind=='figure':
            _,filename,caption,maxh=b;fp=HERE/'assets'/filename
            with PILImage.open(fp) as im:iw,ih=im.size
            factor=min(WIDTH/iw,maxh/ih);image=Image(str(fp),width=iw*factor,height=ih*factor);image.hAlign='CENTER'
            out.extend([image,Spacer(1,5),Paragraph(esc(caption),st['caption']),Spacer(1,11)])
        else:raise ValueError(kind)
    return out

def measure(flows):return sum(f.wrap(WIDTH,10000)[1] for f in flows)

def draw_flows(c,flows,y):
    for f in flows:
        w,h=f.wrap(WIDTH,10000)
        x=LEFT+(WIDTH-w)/2 if isinstance(f,Image) else LEFT
        f.drawOn(c,x,y-h);y-=h
    return y

def footer(c,num,source=''):
    c.setStrokeColor(colors.HexColor('#CDD1D5'));c.setLineWidth(.35);c.line(LEFT,64,W-RIGHT,64)
    if source:
        st=ParagraphStyle('src',fontName='KR',fontSize=7.1,leading=10,textColor=GREY,wordWrap='CJK')
        p=Paragraph(esc(source),st);_,h=p.wrap(WIDTH,100);p.drawOn(c,LEFT,57-h)
    c.setFillColor(GREY);c.setFont('KR',8);c.drawCentredString(W/2,25,str(num))

def cover(c):
    c.setFillColor(colors.black)
    c.setFont('KR-Bold',27);c.drawCentredString(W/2,660,'종합 보고서')
    c.setFont('KR-Bold',23)
    for i,line in enumerate(TITLE.splitlines()):c.drawCentredString(W/2,571-i*40,line)
    c.setFont('KR',11.5);c.drawCentredString(W/2,469,SUBTITLE)
    c.setFont('KR-Bold',17);c.drawCentredString(W/2,393,'Blue Jay  |  B1조')
    c.setFont('KR',12);c.drawCentredString(W/2,345,AUTHORS)
    c.setFont('KR',12);c.drawCentredString(W/2,238,'포스코 청년 AI·Big Data 아카데미 34기')
    c.setFont('KR',12);c.drawCentredString(W/2,199,DATE)
    c.bookmarkPage('cover');c.addOutlineEntry('표지','cover',level=0);c.showPage()

def content_page(c,page,index,num):
    y=H-67;part=page['part'];title=page['title']
    c.bookmarkPage(f'content{index}')
    c.addOutlineEntry((part+' — ' if part else '')+title,f'content{index}',level=0)
    if part:
        sty=ParagraphStyle('part',fontName='KR-Bold',fontSize=16,leading=23,textColor=NAVY,wordWrap='CJK')
        pp=Paragraph(esc(part),sty);_,ph=pp.wrap(WIDTH,100);pp.drawOn(c,LEFT,y-ph);y-=ph+13
    sty=ParagraphStyle('title',fontName='KR-Bold',fontSize=14.1,leading=21.2,textColor=BLUE if index else colors.black,wordWrap='CJK')
    pp=Paragraph(esc(title),sty);_,ph=pp.wrap(WIDTH,100);pp.drawOn(c,LEFT,y-ph);y-=ph+15
    flows=block_flows(page['blocks'],reference=title.startswith('참고문헌'))
    used=measure(flows);bottom=draw_flows(c,flows,y)
    footer(c,num,page['source']);c.showPage()
    return {'page':num,'title':title,'content_top':round(y,1),'content_height':round(used,1),'content_bottom':round(bottom,1),'overflow':bottom<81}

def toc(c,indices,num,continued=False):
    c.bookmarkPage(f'toc{num}');c.addOutlineEntry('목차'+(' (계속)' if continued else ''),f'toc{num}',level=0)
    c.setFont('KR-Bold',18);c.setFillColor(colors.black);c.drawString(LEFT,H-84,'목차'+(' (계속)' if continued else ''))
    y=H-124
    for i in indices:
        page=PAGES[i];pn=2 if i==0 else i+4
        if page['part']:
            y-=5;c.setFont('KR-Bold',11);c.setFillColor(NAVY);c.drawString(LEFT,y,page['part']);y-=23
        txt=page['title'];font='KR';size=9.8;c.setFont(font,size);c.setFillColor(colors.HexColor('#313B47'))
        c.drawString(LEFT+10,y,txt)
        tw=pdfmetrics.stringWidth(txt,font,size)
        c.setStrokeColor(colors.HexColor('#ACB4BD'));c.setDash(1,2);c.setLineWidth(.4)
        if LEFT+tw+30<W-RIGHT-24:c.line(LEFT+tw+26,y+2,W-RIGHT-25,y+2)
        c.setDash();c.drawRightString(W-RIGHT,y,str(pn));c.linkRect('',f'content{i}',(LEFT,y-4,W-RIGHT,y+13),relative=0,thickness=0)
        y-=21
    footer(c,num);c.showPage()
    return {'page':num,'title':'목차','content_bottom':round(y,1),'overflow':y<80}

def markdown():
    chunks=[f'# {TITLE.replace(chr(10), " ")}\n\n{SUBTITLE}\n\n{AUTHORS}\n\n{DATE}\n']
    for pg in PAGES:
        if pg['part']:chunks.append('\n# '+pg['part'])
        chunks.append('\n## '+pg['title']+'\n')
        for b in pg['blocks']:
            k=b[0]
            if k=='h':chunks.append('### '+b[1]+'\n')
            elif k=='p':chunks.append(b[1]+'\n')
            elif k=='note':chunks.append('> '+b[1]+'\n')
            elif k=='equation':chunks.append('**'+b[1]+'**\n')
            elif k=='figure':chunks.append(f'![{b[2]}](assets/{b[1]})\n\n{b[2]}\n')
            elif k=='table':
                clean=lambda v:str(v).replace('|','／').replace('\n','<br>')
                chunks.append(b[1]+'\n\n| '+' | '.join(map(clean,b[2]))+' |\n| '+' | '.join(['---']*len(b[2]))+' |\n'+'\n'.join('| '+' | '.join(map(clean,row))+' |' for row in b[3])+'\n')
        chunks.append('*출처: '+pg['source']+'*\n')
    (HERE/'Blue_Jay_종합보고서_원고.md').write_text('\n'.join(chunks),encoding='utf-8')

def main():
    c=Canvas(str(DEST),pagesize=A4,pageCompression=1)
    c.setTitle('Blue Jay — 공공입찰 AI 어시스턴트 종합 보고서')
    c.setAuthor('B1조 | '+AUTHORS);c.setSubject(SUBTITLE);c.setCreator('ReportLab · reviewed project evidence')
    layout=[];cover(c)
    layout.append(content_page(c,PAGES[0],0,2))
    layout.append(toc(c,range(0,20),3))
    layout.append(toc(c,range(20,len(PAGES)),4,True))
    for i,page in enumerate(PAGES[1:],1):layout.append(content_page(c,page,i,i+4))
    c.save();markdown()
    reader=PdfReader(DEST)
    text='\n'.join(p.extract_text() or '' for p in reader.pages)
    report={'status':'pending_visual_review','pdf':str(DEST.relative_to(ROOT)).replace('\\','/'),
       'pages':len(reader.pages),'expected_pages':len(PAGES)+3,'a4_all_pages':all(abs(float(p.mediabox.width)-W)<.1 and abs(float(p.mediabox.height)-H)<.1 for p in reader.pages),
       'extractable_characters':len(text),'sha256':hashlib.sha256(DEST.read_bytes()).hexdigest(),
       'overflow_pages':[x['page'] for x in layout if x['overflow']],'layout':layout,
       'required_terms':{s:s in text for s in ['137,745','300','17,537','0.7385','합성','사후 선별','참고문헌']},
       'figures':len(list((HERE/'assets').glob('*.png'))),
       'model_execution':'not_performed','human_approval':'not_recorded'}
    (HERE/'검증결과.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='layout'},ensure_ascii=False,indent=2))
    if report['overflow_pages']:raise SystemExit('Layout overflow: '+str(report['overflow_pages']))

if __name__=='__main__':main()
