// Run against the local static server. Uses the bundled Playwright runtime.
const {chromium}=require(process.env.RUNTIME_NODE_MODULES+'/playwright');
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 // The whole data flow must work without the external map provider.
 await page.route('https://**/*',route=>route.abort());
 await page.goto((process.env.DEMO_URL||'http://127.0.0.1:8766')+'/public-notices.html');
 await page.waitForFunction(()=>document.querySelector('#count').textContent.includes('51 / 51'));
 assert.equal(await page.locator('.bid-card').count(),51);
 await page.locator('#review').check();assert.equal(await page.locator('.bid-card').count(),21);
 await page.getByRole('button',{name:'3억 이상',exact:true}).click();
 const payload=JSON.parse(fs.readFileSync(__dirname+'/dist/public-notices.json','utf8'));
 assert.equal(await page.locator('.bid-card').count(),payload.records.filter(r=>r.budget>=3e8&&r.reviewAvailable).length);
 await page.locator('#min').fill('5');await page.locator('#max').fill('1');
 assert((await page.locator('#filter-error').textContent()).includes('커야'));
 assert.equal(await page.locator('.bid-card').count(),0);assert((await page.locator('#detail').textContent()).includes('조회 결과가 없습니다'));
 await page.getByRole('button',{name:'필터 초기화'}).click();await page.waitForFunction(()=>document.querySelectorAll('.bid-card').length===51);assert.equal(await page.locator('.bid-card').count(),51);
 await page.locator('#query').fill('no-such-procurement');assert.equal(await page.locator('.bid-card').count(),0);
 await page.locator('#query').fill('R26BK01577397');assert.equal(await page.locator('.bid-card').count(),1);
 assert((await page.locator('#detail').textContent()).includes('RUDAS'));
 await page.getByRole('button',{name:'필터 초기화'}).click();
 await page.locator('#region').selectOption('미확인');assert((await page.locator('#map-count').textContent()).includes('지역 표시 0건'));
 await page.getByRole('button',{name:'필터 초기화'}).click();
 assert((await page.locator('#map-status').textContent()).includes('불러오지 못했습니다'));
 await page.screenshot({path:path.join(process.env.TEMP,'astra-public-desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:path.join(process.env.TEMP,'astra-public-mobile.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 console.log('PASS: browser filtering, 21 reviewed records, empty/invalid state, reset, selected detail, unknown regions, offline map, mobile width');
 // Online pass: map failures are environmental, but DOM/runtime failures are not.
 await page.unroute('https://**/*');await page.setViewportSize({width:1600,height:1000});
 await page.reload();await page.waitForTimeout(8000);
 console.log('Online map:',await page.locator('#map-status').textContent(),'markers:',await page.locator('.region-marker').count());
 if(await page.locator('.region-marker').count()){
  await page.locator('.region-marker').first().click();
  assert.notEqual(await page.locator('#region').inputValue(),'');
  assert.equal(await page.locator('.region-marker').count(),1);
  await page.getByRole('button',{name:'필터 초기화'}).click();
 }
 await page.screenshot({path:path.join(process.env.TEMP,'astra-public-online.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
