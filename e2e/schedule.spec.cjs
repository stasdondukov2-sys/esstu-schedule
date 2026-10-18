const {test,expect}=require('./fixtures.cjs');
// Mocked network responses must not be bypassed by service-worker fetches.
const routedTest=test.extend({serviceWorkers:'block'});

test('schedule, source status and teacher navigation work under the Pages prefix',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('./');
  await expect(page.getByRole('heading',{level:1})).toHaveText('1146 тпуп');
  await expect(page.locator('#pairsContainer')).not.toContainText('Загрузка');
  await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.getByRole('button',{name:'Данные и обновления',exact:true}).click();
  await expect(page.locator('#parseQualityStatus')).toContainText('Ошибок разбора:');
  await page.getByRole('button',{name:'Закрыть сведения',exact:true}).click();
  await page.getByRole('button',{name:'Сменить расписание',exact:true}).click();
  await page.getByRole('button',{name:'Преподаватели',exact:true}).click();
  await page.locator('#teacherSearchInput').fill('Дарибазарон');
  const teacher=page.locator('#teacherModalContent button').filter({hasText:'Дарибазарон'});
  await expect(teacher).toHaveCount(1);
  await teacher.click();
  await expect(page.getByRole('heading',{level:1})).toContainText('Дарибазарон');
  expect(errors).toEqual([]);
});

routedTest('unreadable data is marked incomplete, not as a free day',async({page})=>{
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:{
    mode:'student',group_name:'1146 тпуп',group_id:'1',section:'bakalavriat',
    weeks:{1:{},2:{}},is_incomplete:true,parse_errors:['Unexpected table structure']
  }}));
  await page.goto('./');
  await expect(page.locator('#incompleteWarning')).toBeVisible();
  await expect(page.locator('#pairsContainer')).toContainText('Данные неполные');
  await expect(page.locator('#pairsContainer')).not.toContainText('занятий нет');
  await expect(page.locator('#dayTabs')).not.toContainText('нет пар');
  await expect(page.locator('#heroLessons')).toContainText('Данные неполные');
});

for(const reason of ['Источник портала содержит расписание другой группы (ЗУ-395-1).','Расписание на портале не заполнено.'])routedTest('source defect is explained: '+reason,async({page})=>{
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:{
    mode:'student',group_name:'1146 тпуп',group_id:'1',section:'bakalavriat',weeks:{1:{},2:{}},is_incomplete:true,incomplete_reason:reason,parse_errors:[reason]
  }}));
  await page.goto('./');
  await expect(page.locator('#incompleteWarning')).toContainText(reason);
  await expect(page.locator('#pairsContainer')).toContainText(reason);
  await expect(page.locator('#heroLessons')).toContainText(reason);
  await expect(page.locator('#pairsContainer')).not.toContainText('занятий нет');
});

test('installation URLs stay inside the repository and the cached shell opens offline',async({page,context,request})=>{
  const manifest=await (await request.get('manifest.json')).json();
  for(const relative of [manifest.start_url,manifest.scope,...manifest.shortcuts.map(shortcut=>shortcut.url)])
    expect(new URL(relative,'https://example.test/esstu-schedule/manifest.json').pathname).toMatch(/^\/esstu-schedule\//);
  await page.goto('./');
  await expect(page.getByRole('heading',{level:1})).toHaveText('1146 тпуп');
  await page.evaluate(async()=>{await navigator.serviceWorker.ready;});
  await page.reload();
  await expect.poll(()=>page.evaluate(()=>!!navigator.serviceWorker.controller)).toBe(true);
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  await expect(page.locator('#pairsContainer article').first()).toBeVisible();
  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole('heading',{level:1})).toHaveText('1146 тпуп');
  await expect(page.locator('#compactFreshnessText')).toContainText('Офлайн');
});
