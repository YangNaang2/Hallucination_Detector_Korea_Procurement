"""Local-only complete answer/context review viewer; never exports full contexts to Git."""
import html,json
from detector300 import ROOT,OUT,PRIVATE,load,save,file_sha

def main():
 labels=load(OUT/'annotation/agent_draft/labels.json');cards=[]
 for r in labels:
  x=load(PRIVATE/'inputs'/f'{r["question_id"]}.json')
  # Predictions deliberately absent, so reviewers can inspect inputs first.
  cards.append('<article><h2>'+html.escape(r['question_id'])+'</h2><p>'+html.escape(r['status'])+'</p><h3>'+html.escape(x['question'])+'</h3><pre>'+html.escape(x['actual_answer'])+'</pre><details><summary>당시 입력 근거 전체</summary><pre>'+html.escape(x['context'])+'</pre></details><details><summary>라벨 초안 · 미승인</summary><pre>'+html.escape(json.dumps(r,ensure_ascii=False,indent=2))+'</pre></details></article>')
 target=PRIVATE/'review.html';target.write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>탐지기 295답변 검수</title><style>body{max-width:1100px;margin:24px auto;font:16px/1.6 sans-serif}article{padding:24px;border:1px solid #bbb;margin:24px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}summary{cursor:pointer}</style><h1>295답변 입력 근거 검수 · 사람 승인 전</h1><p>원답변은 수정하지 않습니다. 미검토는 정상 라벨이 아닙니다. 탐지 예측은 초안 작성 후 별도로 확인하세요.</p>'+''.join(cards)+'</html>',encoding='utf-8')
 save(OUT/'annotation/review_package.json',dict(private_viewer='work/detector300/review.html',sha256=file_sha(target),records=295,full_evidence_git_export=False,browser_render_validation='not_performed',labels='annotation/agent_draft/labels.json',proposals='annotation/adjudicated/proposals.json',human_submissions='annotation/human_submitted/references.json',remaining='annotation/resume.json'))
 print(target)
if __name__=='__main__':main()
