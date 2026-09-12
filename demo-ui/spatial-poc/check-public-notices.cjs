const assert=require('node:assert/strict'),fs=require('node:fs');
const core=require('./dist/public-notices-core.js');
const rows=JSON.parse(fs.readFileSync(__dirname+'/dist/public-notices.json','utf8')).records.map(r=>({...r,region:core.locate(r.agency)}));
assert.equal(rows.length,51);assert.equal(new Set(rows.map(r=>r.id)).size,51);
assert.equal(rows.filter(r=>r.reviewAvailable).length,21);
assert(rows.every(r=>r.reviewAvailable?r.requirements.length===10:r.requirements.length===0));
assert.equal(core.locate('세종대학교'),null);assert.equal(core.locate('한국과학기술정보연구원'),null);
assert.equal(core.locate('대구광역시').name,'대구');
const boundary=[0,49999999,50000000,99999999,100000000,299999999,300000000].map((budget,i)=>({budget,id:String(i),title:'',agency:''}));
const presets=[['','.5'],['.5','1'],['1','3'],['3','']];
assert.deepEqual(presets.map(p=>core.filter(boundary,core.parseRange(...p)).map(r=>r.budget)),[[0,49999999],[50000000,99999999],[100000000,299999999],[300000000]]);
for(const p of [['-1',''],['3','1'],['1','1'],['bad',''],['','Infinity']])assert(core.parseRange(...p).error);
assert.equal(core.filter(rows,{query:'not-a-bid'}).length,0);
const joined=core.filter(rows,{min:1e8,max:3e8,review:true,month:'2026-05'});
assert(joined.length);assert(joined.every(r=>r.reviewAvailable&&r.budget>=1e8&&r.budget<3e8&&r.month==='2026-05'));
for(const f of [{},{min:3e8},{review:true},{region:'미확인'},{query:'한국과학기술정보연구원'}]){
 const visible=core.filter(rows,f);assert.equal(core.group(visible).reduce((n,g)=>n+g.records.length,0),visible.filter(r=>r.region).length);
}
console.log('PASS: 51 IDs, 21 sheets; budget boundaries, invalid ranges, combined filters, unknown locations and map counts');
