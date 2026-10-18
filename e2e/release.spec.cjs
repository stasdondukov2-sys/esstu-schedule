const {test,expect}=require('./fixtures.cjs');
const fs=require('fs'),path=require('path'),http=require('http');
const routedTest=test.extend({serviceWorkers:'block'});
async function ready(page,url='./'){await page.goto(url);await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');}

routedTest('an empty day links to the next known teaching day',async({page})=>{
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  data.is_incomplete=false;data.weeks={'1':{},'2':{}};
  for(const week of Object.values(data.weeks)){
    week.monday={pairs:[]};week.tuesday={pairs:[{number:1,start:'09:00',end:'10:35',lessons:[{subject:'Тестовое занятие',type:'Практика',room:'0410'}]}]};
  }
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:data}));
  await ready(page);
  await page.evaluate(()=>{simOverride={dayIndex:0,hours:9,minutes:0};selectedWeek=getWeekNum(getUlanUdeNow());selectedDayKey='monday';renderAll();});
  await page.getByRole('button',{name:/Ближайший день с парами/}).click();
  await expect(page.locator('#selectedDaySummary')).toContainText('Вторник');
  await expect(page.locator('#pairsContainer')).toContainText('Тестовое занятие');
});

routedTest('recent schedules are local and search precedes filters',async({page})=>{
  const groups=JSON.parse(fs.readFileSync('dist/api/groups/bakalavriat.json','utf8')).groups;
  const target=groups.find(group=>{try{return group.id!=='1'&&!JSON.parse(fs.readFileSync(`dist/api/schedule/bakalavriat/${group.id}.json`,'utf8')).is_incomplete;}catch{return false;}});
  expect(target).toBeTruthy();await ready(page);await ready(page,'./?group='+encodeURIComponent(target.name));
  await page.getByRole('button',{name:'Сменить расписание',exact:true}).click();
  await expect(page.locator('#searchInputSlot #groupSearchInput')).toBeVisible();
  const input=await page.locator('#groupSearchInput').boundingBox(),filters=await page.locator('#sectionTabs').boundingBox();expect(input.y).toBeLessThan(filters.y);
  await expect(page.locator('#recentSection')).toBeVisible();await expect(page.locator('#recentSchedules')).toContainText(target.name);
  await page.locator('#recentSchedules').getByRole('button',{name:groups[0].name,exact:true}).click();
  await expect(page.getByRole('heading',{level:1})).toHaveText(groups[0].name);
});

routedTest('mobile swipes move days and dismiss a sheet without losing focus',async({page,context,isMobile})=>{
  test.skip(!isMobile,'Native touch gestures are checked in the mobile project');await ready(page);
  await page.evaluate(()=>{selectedDayKey='tuesday';renderAll();});
  const cdp=await context.newCDPSession(page);
  async function swipe(x,y,endX,endY){
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
    for(let step=1;step<=5;step++)await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+(endX-x)*step/5,y:y+(endY-y)*step/5}]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  }
  await page.locator('#dayTabs').evaluate(node=>node.scrollIntoView({block:'center',behavior:'instant'}));const tabs=await page.locator('#dayTabs').boundingBox();
  await swipe(tabs.x+tabs.width*.8,tabs.y+tabs.height/2,tabs.x+tabs.width*.2,tabs.y+tabs.height/2);
  await expect(page.locator('#dayTabs [aria-pressed="true"]')).toHaveAttribute('onclick',"selectDay('wednesday')");
  const launcher=page.getByRole('button',{name:'Ещё',exact:true});await launcher.click();
  const handle=page.locator('#moreMenuModal .sheet-handle');await expect(handle).toBeVisible();
  const grip=await handle.boundingBox();await swipe(grip.x+grip.width/2,grip.y+grip.height/2,grip.x+grip.width/2,grip.y+grip.height/2+130);
  await expect(page.locator('#moreMenuModal')).toBeHidden();await expect(launcher).toBeFocused();
});

test('a real worker update preserves saved data and the new shell opens offline',async({page,context})=>{
  const root=path.resolve('dist');let release=1;
  const server=http.createServer((req,res)=>{
    const url=new URL(req.url,'http://test');let name=decodeURIComponent(url.pathname).replace(/^\/esstu-schedule\//,'')||'index.html';
    const file=path.resolve(root,name);
    if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}
    let content=fs.readFileSync(file);
    if(name==='sw.js')content=Buffer.from(content.toString().replace(/const CACHE_NAME = '[^']+';/,`const CACHE_NAME = 'esstu-live-browser-test-${release}';`));
    if(name==='index.html')content=Buffer.from(content.toString().replace(/content="[^"]+" name="app-version"/,`content="browser-test-${release}" name="app-version"`));
    if(name==='app.css')content=Buffer.from(content.toString()+`\n:root{--test-release:${release}}`);
    const mime={'.html':'text/html','.js':'application/javascript','.json':'application/json','.css':'text/css','.svg':'image/svg+xml','.png':'image/png'}[path.extname(file)]||'application/octet-stream';
    res.writeHead(200,{'Content-Type':mime,'Cache-Control':name==='sw.js'?'no-cache':'public, max-age=600'});res.end(content);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin=`http://127.0.0.1:${server.address().port}/esstu-schedule/`;
  try{
    await ready(page,origin);await page.evaluate(()=>navigator.serviceWorker.ready);await ready(page,origin);
    await expect.poll(()=>page.evaluate(()=>!!navigator.serviceWorker.controller)).toBe(true);
    const peer=await context.newPage();await ready(peer,origin);
    await expect.poll(()=>peer.evaluate(()=>!!navigator.serviceWorker.controller)).toBe(true);
    await page.evaluate(()=>fetch('api/groups/bakalavriat.json').then(response=>response.json()));
    release=2;await page.evaluate(async()=>{const registration=await navigator.serviceWorker.getRegistration();await registration.update();});
    await expect(page.locator('#appUpdateBanner')).toBeVisible();
    const banner=await page.locator('#appUpdateBanner').boundingBox();expect(banner.y+banner.height).toBeLessThanOrEqual(page.viewportSize().height);await expect(page.locator('.campus-nav')).toHaveCount(0);
    await Promise.all([page.waitForEvent('load'),peer.waitForEvent('load'),page.locator('#appUpdateBanner button').click()]);
    await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
    await expect(page.locator('meta[name="app-version"]')).toHaveAttribute('content','browser-test-2');
    await expect(peer.locator('meta[name="app-version"]')).toHaveAttribute('content','browser-test-2');
    expect(await peer.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--test-release').trim())).toBe('2');
    expect(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--test-release').trim())).toBe('2');
    const keys=await page.evaluate(()=>caches.keys());expect(keys.some(key=>key.endsWith('browser-test-2'))).toBe(true);expect(keys.some(key=>key.endsWith('browser-test-1'))).toBe(false);expect(keys.some(key=>key.endsWith('data-v2'))).toBe(true);
    await context.setOffline(true);await page.reload();
    await expect(page.getByRole('heading',{level:1})).toHaveText('1146 тпуп');
    await expect(page.locator('#compactFreshnessText')).toContainText('Офлайн');
    await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});

routedTest('a room search highlights its building on the conditional campus diagram',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.getByRole('button',{name:'Корпуса кампуса',exact:true}).click();
  await expect(page.locator('#campusStatus')).toContainText('Выберите корпус');
  await page.getByRole('searchbox',{name:'Найти аудиторию'}).fill('0427');
  await expect(page.locator('#campusDiagram [aria-pressed="true"]')).toHaveAttribute('aria-label','Корпус 4');
  await expect(page.locator('#campusBldCard [data-found="true"]')).toContainText('0427');
  await expect(page.locator('#campusMapModal')).toContainText('не отражает географию');
  await page.locator('#campusBldCard').getByRole('button',{name:'0427',exact:true}).click();
  await expect(page.locator('#roomsModal')).toBeVisible();await expect(page.locator('#roomSearchInput')).toHaveValue('0427');
});

routedTest('online pairs stay compact with readable time and preserved original entries',async({page},testInfo)=>{
  await page.clock.setFixedTime(new Date('2026-10-17T01:57:00+08:00'));
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  data.is_incomplete=false;data.weeks={'1':{},'2':{}};
  const lesson={subject:'Основы проектной деятельности (онлайн-курс)',room:'онлайн',type:'Практика',type_code:'practice'};
  for(const week of Object.values(data.weeks))week.saturday={pairs:[{number:5,start:'16:25',end:'18:00',lessons:[lesson]},{number:6,start:'18:05',end:'19:40',lessons:[lesson]}]};
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:data}));await ready(page);
  await expect(page.locator('#heroRemainingTime')).toContainText('Сегодня в 16:25 · через 14 ч 28 мин');
  await expect(page.locator('.hero-lesson .online-badge')).toHaveText('Онлайн');await expect(page.locator('.hero-room')).toHaveCount(0);
  const block=page.locator('.merged-online-block');await expect(block).toHaveCount(1);await expect(block.locator(':scope > summary')).toContainText('16:25–19:40 · 2 пары');
  await page.screenshot({path:`preview/online-${testInfo.project.name}.png`,fullPage:true});
  await expect(block.locator(':scope > summary')).not.toContainText('(онлайн-курс)');await block.locator(':scope > summary').click();
  await expect(block.locator('article')).toHaveCount(2);await expect(block.locator('article').last()).toContainText('18:05');
  await block.locator('article').last().locator('.lesson-subject').first().click();await expect(page.locator('#noteModal')).toBeVisible();await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.locator('#btnViewWeek').click();
  await expect(page.locator('#moreMenuModal')).toBeHidden();
  await expect(page.locator('#pairsContainer')).toContainText('2 пары');await expect(page.locator('#pairsContainer')).not.toContainText(/2 пар(?:\s|$)/);
  await page.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));
  const content=await page.locator('#pairsContainer').boundingBox(),footer=await page.locator('.replica-footer').boundingBox();expect(content.y+content.height).toBeLessThanOrEqual(footer.y);await expect(page.locator('.campus-nav')).toHaveCount(0);
  await page.screenshot({path:`preview/online-week-bottom-${testInfo.project.name}.png`});
});

test('a slow API response refreshes the visible schedule in the background and remains offline',async({page,context})=>{
  const root=path.resolve('dist');let slow=false;
  const server=http.createServer((req,res)=>{
    const name=decodeURIComponent(new URL(req.url,'http://test').pathname).replace(/^\/esstu-schedule\//,'')||'index.html',file=path.resolve(root,name);
    if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}
    let content=fs.readFileSync(file);const changed=slow && name==='api/schedule/bakalavriat/1.json';
    if(changed){const data=JSON.parse(content);data.weeks['1'].friday.pairs.find(pair=>pair.lessons.length).lessons[0].subject='Фоновое обновление расписания';content=Buffer.from(JSON.stringify(data));}
    const send=()=>{const mime={'.html':'text/html','.js':'application/javascript','.json':'application/json','.css':'text/css','.svg':'image/svg+xml','.png':'image/png'}[path.extname(file)]||'application/octet-stream';res.writeHead(200,{'Content-Type':mime,'Cache-Control':'no-cache'});res.end(content);};
    if(changed)setTimeout(send,4800);else send();
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const origin=`http://127.0.0.1:${server.address().port}/esstu-schedule/`;
  try{
    await ready(page,origin);await page.evaluate(()=>navigator.serviceWorker.ready);await ready(page,origin);slow=true;
    const reason=await page.evaluate(async()=>{const response=await fetch('api/schedule/bakalavriat/1.json');await response.json();return response.headers.get('X-ESSTU-Cache');});
    expect(reason).toBe('refreshing');await expect(page.locator('#pairsContainer')).toContainText('Фоновое обновление расписания');
    await context.setOffline(true);await page.reload();await expect(page.locator('#pairsContainer')).toContainText('Фоновое обновление расписания');
  }finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
});
