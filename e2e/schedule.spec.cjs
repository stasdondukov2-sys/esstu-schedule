const {test,expect}=require('@playwright/test');

test('schedule, source status and teacher navigation work under the Pages prefix',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('./');
  await expect(page.getByRole('heading',{level:1})).toHaveText('1146 тпуп');
  await expect(page.locator('#pairsContainer')).not.toContainText('Загрузка');
  await page.locator('#compactFreshnessText').click();
  await expect(page.locator('#parseQualityStatus')).toContainText('Ошибок разбора:');
  await page.getByRole('button',{name:'Закрыть сведения',exact:true}).click();
  await page.getByRole('button',{name:'Поиск',exact:true}).click();
  await page.getByRole('button',{name:'Преподаватели',exact:true}).click();
  await page.locator('#teacherSearchInput').fill('Дарибазарон');
  const teacher=page.locator('#teacherModalContent button').filter({hasText:'Дарибазарон'});
  await expect(teacher).toHaveCount(1);
  await teacher.click();
  await expect(page.getByRole('heading',{level:1})).toContainText('Дарибазарон');
  expect(errors).toEqual([]);
});

test('unreadable data is marked incomplete, not as a free day',async({page})=>{
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
