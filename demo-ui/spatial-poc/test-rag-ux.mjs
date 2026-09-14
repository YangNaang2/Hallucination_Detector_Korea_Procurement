import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createSavedSource,createDisconnectedSource,validateEvent,canApplyResult} from './dist/rag-source.mjs';
import {renderAnswer} from './dist/rag-render.mjs';
const data=JSON.parse(readFileSync(new URL('./dist/rag-observatory.json',import.meta.url)));
const source=createSavedSource(data),c=data.cases[0];
assert.equal((await source.ask({bid:c.bid,question:c.question})).answer,c.answer);
await assert.rejects(source.ask({bid:'wrong',question:c.question}),/미연결/);
await assert.rejects(source.ask({bid:c.bid,question:'arbitrary'}),/미연결/);
const ac=new AbortController();ac.abort();await assert.rejects(source.ask({bid:c.bid,question:c.question},ac.signal),{name:'AbortError'});
assert.equal(canApplyResult(1,2,c.bid,c.bid),false);
assert.equal(canApplyResult(1,1,c.bid,'other'),false);
assert.equal(source.status().connected,false);
await assert.rejects(async()=>{for await(const e of createDisconnectedSource().stream()){}},/서버 계약/);
const context={requestId:'r',snapshotId:'s',lastSeq:1};
assert.equal(validateEvent({request_id:'r',snapshot_id:'s',seq:2,type:'delta',text:'ok'},context),2);
for(const bad of [{request_id:'wrong'},{snapshot_id:'wrong'},{seq:1},{type:'unknown'},{text:null}])
 assert.throws(()=>validateEvent({request_id:'r',snapshot_id:'s',seq:2,type:'delta',text:'ok',...bad},context));
const hostile=renderAnswer('<img src=x onerror=alert(1)> **안전** [x](javascript:alert(1)) [999]',[]);
assert(!hostile.includes('<img'));assert(!hostile.includes('<a '));assert(hostile.includes('<strong>안전</strong>'));assert(!hostile.includes('data-citation="999"'));
assert(renderAnswer('[1]',[{citation:1}]).includes('data-citation="1"'));
assert.equal(renderAnswer('😀가나다',[],[{start:1,end:3,label:'DRAFT',reason:'test'}],true).match(/<mark /g).length,2);
for(const c of data.cases){const before=JSON.stringify(c);for(const on of [false,true]){const html=renderAnswer(c.answer,c.contexts,c.spans,on);assert(!/<script|<img|<iframe/.test(html));}assert.equal(JSON.stringify(c),before);}
console.log('PASS saved matching/cancel/stale responses, event guards, XSS, citations, Unicode spans, all 4 canonical cases');
