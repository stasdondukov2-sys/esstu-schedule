const {test:base,expect}=require('./fixtures.cjs');
const fs=require('fs');
const test=base.extend({serviceWorkers:'block'});
async function ready(page){
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  const lesson={subject:'Разработка клиентских интерфейсов',type:'Лабораторная',type_code:'lab',teacher:'Преподаватель И.О.',room:'0427'};
  const pairs=[{number:0,start:'07:00',end:'08:35',lessons:[{...lesson,subject:'Прошедшее занятие'}]},
    {number:1,start:'09:00',end:'10:35',lessons:[lesson]},
    {number:2,start:'10:45',end:'12:20',lessons:[{...lesson,subject:'Следующее занятие'}]}];
  data.is_incomplete=false;data.weeks={'1':{friday:{pairs},saturday:{pairs}},'2':{friday:{pairs}}};
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:data}));
  await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
}
test('lesson states and progress follow the clock, including the break boundary',async({page})=>{
  await ready(page);
  const cards=page.locator('#pairsContainer>.lesson-card');
  await expect(cards.nth(0)).toHaveClass(/is-past/);
  await expect(cards.nth(1)).toHaveClass(/is-current/);
  await expect(cards.nth(2)).toHaveClass(/is-next/);
  await expect(cards.nth(1).locator('[data-pair-countdown]')).toHaveText('ост. 1 ч 5 мин');
  await expect(cards.nth(1).getByRole('progressbar')).toHaveAttribute('aria-valuenow','32');
  await page.clock.fastForward(65*60000);
  await expect(page.locator('#pairsContainer>.is-current')).toHaveCount(0);
  await expect(cards.nth(1)).toHaveClass(/is-past/);
  await expect(cards.nth(2)).toHaveClass(/is-next/);
  await expect(cards.nth(2).locator('[data-pair-countdown]')).toHaveText('через 10 мин');
  await page.clock.fastForward(10*60000);
  await expect(cards.nth(2)).toHaveClass(/is-current/);
});
test('past lesson notes remain usable and another day is not marked current or next',async({page})=>{
  await ready(page);
  const past=page.locator('#pairsContainer>.is-past');
  await past.locator('.lesson-subject').first().click();
  await expect(page.locator('#noteModal')).toBeVisible();
  await page.getByRole('button',{name:'Закрыть заметку'}).click();
  await page.locator('#dayTabs button').last().click();
  await expect(page.locator('#pairsContainer>.is-current,#pairsContainer>.is-next')).toHaveCount(0);
});
test('compact header fits 320px with one heading and distinct search controls',async({page})=>{
  await ready(page);await page.setViewportSize({width:320,height:900});
  await expect(page.getByRole('heading',{level:1})).toHaveText('1146 тпуп');
  await expect(page.getByRole('button',{name:'Сменить расписание',exact:true})).toHaveCount(1);
  await expect(page.getByRole('button',{name:'Поиск преподавателя',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  for(const button of await page.locator('.header-actions button').all()){
    const box=await button.boundingBox();expect(box.width).toBeGreaterThanOrEqual(32);expect(box.height).toBeGreaterThanOrEqual(32);
  }
  const h=await page.locator('.campus-header').boundingBox();expect(h.height).toBeLessThanOrEqual(80);
});

test('type colours preserve mixed parallel lessons and accessible day counts',async({page})=>{
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  const lesson=code=>({subject:'Предмет '+code,type:{practice:'Практика',lab:'Лабораторная',lecture:'Лекция'}[code],type_code:code,teacher:'Преподаватель И.О.',room:'0427'});
  const types=['practice','lab','lecture','mixed'];
  const pairs=types.map((type,i)=>({number:i+1,start:['09:00','10:45','13:00','14:45'][i],end:['10:35','12:20','14:35','16:20'][i],lessons:type==='mixed'?[lesson('lab'),lesson('lecture')]:[lesson(type)]}));
  data.is_incomplete=false;data.weeks={'1':{saturday:{pairs}},'2':{}};
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:data}));
  await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  await page.getByRole('button',{name:/Суббота,.*4 пары/}).click();
  const cards=page.locator('#pairsContainer>.lesson-card');await expect(cards).toHaveCount(4);
  for(const [i,type] of types.entries())await expect(cards.nth(i)).toHaveAttribute('data-type',type);
  await expect(cards.last().locator('.lesson-detail[data-type="lab"]')).toHaveCount(1);
  await expect(cards.last().locator('.lesson-detail[data-type="lecture"]')).toHaveCount(1);
  for(const theme of ['dark','light']){
    await page.evaluate(theme=>{themeMode=theme;applyTheme();},theme);
    const backgrounds=await cards.evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).backgroundImage));
    expect(new Set(backgrounds).size).toBe(4);
  }
  await expect(page.locator('#dayTabs [aria-pressed="true"] .calendar-dots i')).toHaveCount(4);
  await cards.last().locator('.lesson-subject').last().click();
  await expect(page.locator('#noteModal')).toBeVisible();
});
