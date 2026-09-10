// DOM/Map adapter check; not a GPU rendering or tile availability test.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements=new Map();
function el(){return {getBoundingClientRect(){return {right:310,left:1050};},open:false,showModal(){this.open=true;},close(){this.open=false;},focus(){},textContent:'',innerHTML:'',dataset:{},style:{setProperty(){}},classList:{toggle(){},add(){},remove(){}},clientWidth:290,clientHeight:235,events:{},setAttribute(){},addEventListener(k,f){this.events[k]=f;}};}
const document={querySelector(k){if(!elements.has(k))elements.set(k,el());return elements.get(k);},querySelectorAll(){return [];},createElement:el,documentElement:el(),body:el(),addEventListener(){}};
const context={window:{},innerWidth:1440,document,console,matchMedia:()=>({matches:false}),ResizeObserver:class{observe(){}},performance,devicePixelRatio:2};
vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/dist/bids.js','utf8'),context);
let code=fs.readFileSync(__dirname+'/dist/app.js','utf8');
code=code.replace('bind();setupAccess();','bind();window.check={setupAccess,openSource,chunks,select,inspectGate,getActive:()=>active,graph:drawGraph,setRole:r=>{role=r;drawGraph();answer();},setMap:m=>{map=m;ready=true;started=true;cinematic=false;},fly};');
vm.runInContext(code,context);
const a=context.window.check,bids=context.window.ORBIT_BIDS;
assert.equal(bids.length,8);assert.equal(new Set(bids.map(b=>b.id)).size,8);
let destination;const map={resize(){},stop(){},jumpTo(o){destination=o.center;},getPitch:()=>64,getBearing:()=>30,queryTerrainElevation:()=>20};a.setMap(map);
for(const b of bids){a.select(b.id);assert.equal(a.getActive().id,b.id);assert.deepEqual(Array.from(destination),[b.location.lng,b.location.lat]);assert(document.querySelector('#graph').innerHTML.includes(b.city+' 위치'));a.inspectGate(b.id);assert(document.querySelector('#source-title').textContent.includes('참가 자격'));assert(document.querySelector('#graph').innerHTML.includes('제안요청 제8조'));}
a.setRole(1);assert(a.chunks(bids[0]).every(c=>c.level===1));assert(!document.querySelector('#graph').innerHTML.includes('실적증명'));
a.setRole(3);assert.equal(a.chunks(bids[0]).length,5);
console.log('PASS: 8 region bindings, camera destinations, gate evidence, evaluation nodes, L1/L3 fixture filtering. GPU/tiles not tested.');

assert.equal(new Set(bids.map(b=>b.category)).size,4);assert(bids.every(b=>b.documents.length===12));a.openSource(bids[7].id+'-C01');assert(document.querySelector('#source-drawer').open);assert(document.querySelector('#drawer-body').innerHTML.includes('<mark>'));a.setupAccess();document.querySelector('#ops-direct').events.click();assert.equal(document.querySelector('#role').value,'3');document.querySelector('#logout').events.click();assert.equal(document.querySelector('#workspace').inert,true);document.querySelector('#login-card').events.submit({preventDefault(){}});assert.equal(document.querySelector('#role').value,'1');assert.equal(document.querySelector('#workspace').inert,false);console.log('PASS: 4 categories, 12 source fixtures, highlighted drawer, admin entry, logout, normal entry.');
