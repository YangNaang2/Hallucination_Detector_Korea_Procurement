"""Report figures. Run with matplotlib, numpy and a Korean font installed.

Every numeric plot is an explicit transcription of a cited report table;
it does not run or re-evaluate models. dashboard.png is captured separately.
"""
from pathlib import Path
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'assets'
OUT.mkdir(exist_ok=True)
FONT = Path(os.environ.get('REPORT_FONT', 'C:/Windows/Fonts/malgun.ttf'))
fm.fontManager.addfont(str(FONT))
plt.rcParams.update({'font.family': fm.FontProperties(fname=str(FONT)).get_name(),
                     'font.size': 10, 'axes.unicode_minus': False,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#A3ADB9', 'text.color': '#17263B',
                     'axes.labelcolor': '#17263B', 'xtick.color': '#41536A',
                     'ytick.color': '#41536A', 'savefig.facecolor': 'white'})
NAVY='#203D60'; BLUE='#326ED1'; TEAL='#208E87'; AMBER='#CE9031'; RED='#B74645'
GREY='#718095'; LIGHT='#EEF3F8'

def save(fig, name):
    fig.savefig(OUT/name, dpi=260, bbox_inches='tight', pad_inches=.09)
    plt.close(fig)

def box(ax,x,y,w,h,title,body,color=BLUE):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.01,rounding_size=0.02',
                 ec='#C9D3DD',fc='white',lw=1))
    ax.add_patch(Rectangle((x+.01,y+h-.07),w-.02,.05,color=color))
    ax.text(x+w/2,y+h-.115,title,ha='center',va='center',fontsize=10.5,weight='bold')
    ax.text(x+w/2,y+.09,body,ha='center',va='center',fontsize=9.2,linespacing=1.6)

def diagrams():
    fig,ax=plt.subplots(figsize=(6.45,3.1));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    xs=[.015,.355,.695]
    data=[('① 질문 입력','선택 공고 · 질문\n회사 · 사용자 역할'),
          ('② 권한 확인','L1 / L2 / L3 범위\n다른 회사 자료 차단'),
          ('③ 근거 검색','키워드 + 의미 검색\n관련 Parent 선정'),
          ('④ 답변 생성','질문 + 선정 근거\n로컬 LLM · 인용번호'),
          ('⑤ 환각 탐지','답변 토큰과 근거 대조\n의심 구절 · 미검사 구간'),
          ('⑥ 결과 검토','답변 · 형광펜 · 출처\n원문 근거 열람')]
    for i,(title,body) in enumerate(data):
        x=xs[i%3]; y=.54 if i<3 else .06
        box(ax,x,y,.285,.38,title,body,BLUE if i<3 else TEAL)
        if i%3<2: ax.annotate('',xy=(x+.33,y+.2),xytext=(x+.291,y+.2),arrowprops={'arrowstyle':'-|>','color':GREY,'lw':1.3})
    ax.plot([.837,.837,.157],[.53,.497,.497],color=GREY,lw=1.2)
    ax.annotate('',xy=(.157,.454),xytext=(.157,.497),arrowprops={'arrowstyle':'-|>','color':GREY,'lw':1.2})
    save(fig,'user_pipeline.png')

    fig,ax=plt.subplots(figsize=(6.45,2.4));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    ax.add_patch(FancyBboxPatch((.03,.60),.94,.30,boxstyle='round,pad=.012',ec=NAVY,fc=LIGHT))
    ax.text(.5,.80,'Parent  ·  최대 1,800자',ha='center',weight='bold',fontsize=12)
    ax.text(.5,.68,'사람과 생성 모델이 읽을 근거 문맥 · 인접 Parent는 240자 겹침',ha='center',fontsize=9.5)
    for x,label in [(.05,'Window 1'),(.34,'Window 2'),(.63,'Window 3')]:
        ax.add_patch(Rectangle((x,.23),.30,.22,fc='#E0ECFA',ec=BLUE))
        ax.text(x+.15,.37,label,ha='center',fontsize=10,weight='bold')
        ax.text(x+.15,.27,'최대 384토큰',ha='center',fontsize=9)
    for x in [.34,.63]:ax.add_patch(Rectangle((x,.23),.018,.22,fc=TEAL,alpha=.75))
    ax.annotate('',xy=(.50,.45),xytext=(.50,.585),arrowprops={'arrowstyle':'-|>','color':GREY})
    ax.text(.5,.08,'인접 Window 40토큰 겹침 → 의미 검색 → 원래 Parent로 연결',ha='center',fontsize=9.5,color=TEAL)
    save(fig,'chunking.png')

    fig,ax=plt.subplots(figsize=(6.45,2.3));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    labels=[('원본 라벨','영어 환각 구절'),('태그 삽입','<HAL> … </HAL>'),('한국어 번역','Gemma-3-12B'),('위치 복원','태그 제거 + offset'),('자동 검사','17,537건 통과')]
    for i,(title,body) in enumerate(labels):
        x=.005+i*.204
        ax.add_patch(FancyBboxPatch((x,.48),.174,.35,boxstyle='round,pad=.006',ec='#BDCADA',fc=LIGHT))
        ax.text(x+.087,.71,title,ha='center',weight='bold',fontsize=10)
        ax.text(x+.087,.56,body,ha='center',fontsize=7.8)
        if i<4:ax.annotate('',xy=(x+.199,.64),xytext=(x+.176,.64),arrowprops={'arrowstyle':'-|>','color':GREY})
    ax.text(.5,.28,'“조건은 <HAL>5개사 이하</HAL>입니다.”',ha='center',fontsize=11,color=NAVY)
    ax.text(.5,.10,'태그의 순서·짝·구간을 확인하고 한국어 문자열에서 위치를 다시 계산',ha='center',fontsize=9.5)
    save(fig,'translation.png')

def charts():
    fig,ax=plt.subplots(figsize=(6.45,3.05));y=np.arange(3);a=[50717,32673,38839];b=[28852,14145,8082]
    ax.barh(y-.16,a,height=.29,color=NAVY,label='최신 공고')
    ax.barh(y+.16,b,height=.29,color=TEAL,label='완전 공고')
    for i,(v,w) in enumerate(zip(a,b)):
        ax.text(v+700,i-.16,f'{v:,}',va='center',fontsize=9)
        ax.text(w+700,i+.16,f'{w:,}',va='center',fontsize=9)
    ax.set(yticks=y,yticklabels=['용역','물품','공사'],xlim=(0,63000),xlabel='공고 수 (건)')
    ax.invert_yaxis();ax.legend(loc='lower right',frameon=False,ncol=2,fontsize=9)
    ax.set_xticks([0,20000,40000,60000],['0','20,000','40,000','60,000']);ax.grid(axis='x',alpha=.12);ax.set_axisbelow(True)
    fig.tight_layout();save(fig,'collection.png')

    fig,ax=plt.subplots(figsize=(6.45,2.75));x=np.arange(4)
    for dx,vals,col,lab in [(-.17,[47.95,60.01,73.97,72.35],GREY,'256토큰'),(.17,[50,60.96,74.66,72.70],TEAL,'384토큰')]:
        bars=ax.bar(x+dx,vals,.30,color=col,label=lab)
        ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=8.6)
    ax.set(xticks=x,xticklabels=['Hit@1','MRR@6','Hit@4','문자 커버리지'],ylim=(0,92),ylabel='비율 (%)')
    ax.legend(loc='upper left',ncol=2,frameon=False,fontsize=9);ax.grid(axis='y',alpha=.12);ax.set_axisbelow(True)
    fig.tight_layout();save(fig,'retrieval_metrics.png')

    names=['Qwen3-14B','Qwen3-8B','Llama3.1-8B','Kanana1.5-8B','Qwen3-4B','Gemma3-4B','Mi:dm2.0Mini','Kanana1.5-2.1B','Qwen3-1.7B','Gemma3-1B']
    mem=[14.81,8.28,8.19,8.16,4.46,4.06,2.88,2.60,2.25,1.04];secs=[47.8,26.4,21.8,29.2,15.2,12.3,6.1,12.3,8.1,7.5]
    fig,ax=plt.subplots(figsize=(6.45,3.9));y=np.arange(10)
    ax.barh(y,mem,color=[TEAL if i==1 else NAVY for i in range(10)],height=.60)
    for i,(m,s) in enumerate(zip(mem,secs)):ax.text(m+.13,i,f'{m:.2f} GB  /  {s:.1f}초',va='center',fontsize=8.1)
    ax.set(yticks=y,yticklabels=names,xlim=(0,19.8),xlabel='최종 PPT의 메모리 측정값 (GB)');ax.invert_yaxis()
    ax.axvline(10,color=AMBER,ls='--',lw=1);ax.text(10.1,-.76,'10GB 기준',fontsize=8.3,color=AMBER)
    ax.grid(axis='x',alpha=.12);ax.set_axisbelow(True);fig.tight_layout();save(fig,'llm_memory.png')

    fig,ax=plt.subplots(figsize=(6.45,2.75));names=['XLM-R','KLUE','BGE-M3'];vals=[.6527,.6980,.7385]
    bars=ax.bar(names,vals,width=.48,color=[GREY,BLUE,TEAL]);ax.bar_label(bars,fmt='%.4f',padding=5,fontsize=12)
    ax.set(ylim=(0,.87),ylabel='토큰 Macro F1');ax.grid(axis='y',alpha=.12);ax.set_axisbelow(True)
    fig.tight_layout();save(fig,'detector_f1.png')

    fig,ax=plt.subplots(figsize=(5.6,3.25));ax.set(xlim=(0,2),ylim=(0,2));ax.set_aspect('equal')
    vals=[(0,1,'환각 포착 (TP)',40,BLUE),(1,1,'환각 미탐 (FN)',10,RED),(0,0,'정상 오탐 (FP)',10,AMBER),(1,0,'정상 통과 (TN)',40,TEAL)]
    for x,y,t,n,c in vals:
        ax.add_patch(Rectangle((x,y),1,1,fc=c,ec='white',lw=3));ax.text(x+.5,y+.66,t,ha='center',color='white',fontsize=10);ax.text(x+.5,y+.31,f'{n}건',ha='center',color='white',fontsize=24,weight='bold')
    ax.set(xticks=[.5,1.5],xticklabels=['경고','경고 없음'],yticks=[.5,1.5],yticklabels=['정상 답변','환각 답변']);ax.xaxis.tick_top();ax.tick_params(length=0,pad=9)
    for s in ax.spines.values():s.set_visible(False)
    fig.tight_layout();save(fig,'confusion.png')

    fig,ax=plt.subplots(figsize=(6.45,2.0));values=[2.2,8.8,17.8,71.2];colors=[RED,BLUE,AMBER,TEAL];labels=['환각 미탐','환각 경고','정상 오탐','정상 통과'];left=0
    for i,(v,c) in enumerate(zip(values,colors)):
        ax.barh(0,v,left=left,color=c,height=.40,edgecolor='white')
        if i>0:ax.text(left+v/2,0,f'{v:.1f}%',ha='center',va='center',color='white',weight='bold',fontsize=10)
        left+=v
    ax.annotate('2.2%',xy=(1.1,-.20),xytext=(1.1,-.42),ha='center',fontsize=10,color=RED,arrowprops={'arrowstyle':'-','color':RED})
    ax.set(xlim=(0,100),ylim=(-.65,.5));ax.axis('off')
    ax.legend([Rectangle((0,0),1,1,fc=c) for c in colors],labels,ncol=4,frameon=False,loc='upper center',bbox_to_anchor=(.5,1.25),fontsize=9)
    save(fig,'hypothesis.png')

if __name__=='__main__':
    diagrams(); charts()
    print('Created 9 analytic/technical figures; dashboard capture is separate.')
