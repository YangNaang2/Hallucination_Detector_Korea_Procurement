const fs=require('fs'),vm=require('vm'),assert=require('assert');
const changes=[];const map={getStyle:()=>({layers:[{id:'bg',type:'background'},{id:'park',type:'fill'},{id:'road-primary',type:'line'},{id:'label',type:'symbol',layout:{'text-field':'x'}}]}),setPaintProperty:(...a)=>changes.push(a),getLayer:()=>true,setLight:l=>changes.push(['light',l]),setSky:s=>changes.push(['sky',s])};
const ctx={window:{},document:{body:{dataset:{}}}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(__dirname+'/dist/reality-style.js','utf8'),ctx);
ctx.window.paintReality(map,'dusk');assert.equal(ctx.document.body.dataset.mapLight,'dusk');const dusk=changes.find(a=>a[0]==='bg')[2];changes.length=0;ctx.window.paintReality(map,'night');assert.equal(ctx.document.body.dataset.mapLight,'night');assert.notEqual(changes.find(a=>a[0]==='bg')[2],dusk);
const app=fs.readFileSync(__dirname+'/dist/app.js','utf8');assert(!app.includes('api.mapbox.com'));assert(!app.includes('runtime-config.json'));assert(app.includes('makeRealityStyle'));
console.log('PASS: dusk/night paint updates; active map has no Mapbox/config requests.');
