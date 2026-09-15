"""Fixed ablations: operating point versus training; no new selection."""
import klue_fp_select as s
k=s.k
if __name__=='__main__':
 chosen=k.load(k.OUT/'fp_selection.json')['selected'];configs={'v3_original':dict(model='mil3',aggregation='min2',threshold=.5),'threshold_only':dict(model='mil3',aggregation='min2',threshold=chosen['threshold']),'threshold_and_aggregation':dict(model='mil3',aggregation=chosen['aggregation'],threshold=chosen['threshold']),'with_negative_training':chosen}
 results={name:s.evaluate(k.selected_ids('evaluation'),config)[0] for name,config in configs.items()};k.save(k.OUT/'ablations.json',results);print({name:r['answer_presence'] for name,r in results.items()})
