"""Secondary zero-dev-FP operating point, locked before comparison."""
import argparse
import klue_fp_select as s
k=s.k
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','report']);a=p.parse_args();dest=k.OUT/'strict_selection.json'
 if a.command=='freeze':
  assert not (k.OUT/'evaluation.json').exists(),'freeze before comparison only'
  curves=k.load(k.OUT/'fp_dev_curves.json');best=max([r for r in curves if r['false_alarm_rate']==0],key=lambda r:r['answer']['f1'] or 0);k.save(dest,dict(selected=best,secondary=True,policy='zero dev false positives then max dev answer F1; no recall guarantee',source_sha256=k.file_sha(__file__)));print(best)
 else:
  selected=k.load(dest);assert selected['source_sha256']==k.file_sha(__file__);result,rows=s.evaluate(k.selected_ids('evaluation'),selected['selected']);k.save(k.OUT/'strict_evaluation.json',dict(metrics=result,rows=rows,independent_test=False,human_gold=False));print(result)
