const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={window:{}};vm.createContext(c);for(const f of ['bids.js','twin-data.js'])vm.runInContext(fs.readFileSync(__dirname+'/dist/'+f,'utf8'),c);
const w=c.window;assert.equal(w.TWIN_SECTORS.length,4);const ids=new Set();
for(const s of w.TWIN_SECTORS){assert.equal(s.docs.length,12);assert(s.equipment[0].count>0);assert(s.docs[8].text.includes(s.requirement));for(const d of s.docs){assert(!ids.has(d.id));ids.add(d.id);}assert.equal(w.twinAudit(s.required,s.actual).pass,s.actual>=s.required);assert(fs.existsSync(__dirname+'/dist/twin-pdfs/'+s.id+'.pdf'));}
assert.equal(w.twinAudit(10,10).pass,true);assert.equal(w.twinAudit(10,9).gap,1);assert(w.TWIN_SECTORS.some(s=>w.twinAudit(s.required,s.actual).pass));assert(w.TWIN_SECTORS.some(s=>!w.twinAudit(s.required,s.actual).pass));
console.log('PASS: four sectors, 48 unique documents, equipment IDs/counts, audit boundary/pass/fail, four PDF assets.');
