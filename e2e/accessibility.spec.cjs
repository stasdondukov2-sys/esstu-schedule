const {test,expect}=require('./fixtures.cjs');
const {default:AxeBuilder}=require('@axe-core/playwright');
const fs=require('fs');
const routedTest=test.extend({serviceWorkers:'block'});

async function ready(page){await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');}
test('dialogs trap focus, close with Escape and return to the launcher',async({page})=>{
  await ready(page);
  const launcher=page.getByRole('button',{name:'Сменить расписание',exact:true});await launcher.click();
  await expect(page.getByRole('textbox',{name:'Поиск учебной группы'})).toBeFocused();
  const dialog=page.getByRole('dialog',{name:'Выбрать расписание'});
  const close=page.getByRole('button',{name:'Закрыть поиск'});await close.focus();await page.keyboard.press('Shift+Tab');
  expect(await dialog.evaluate(node=>node.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Escape');await expect(dialog).toBeHidden();await expect(launcher).toBeFocused();
  await page.getByRole('button',{name:'Аудитории',exact:true}).click();
  await expect(page.getByRole('dialog',{name:'Радар аудиторий'})).toBeVisible();
  await page.keyboard.press('Escape');await expect(page.getByRole('button',{name:'Аудитории',exact:true})).toBeFocused();
});

test('dark and light views and the search dialog pass accessibility checks',async({page},testInfo)=>{
  await ready(page);
  for(const theme of ['dark','light']){
    await page.getByRole('button',{name:'Сменить расписание',exact:true}).hover();
    const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    expect(result.violations).toEqual([]);
    if(process.env.CAPTURE_SCREENSHOTS && theme==='dark'){
      fs.mkdirSync('docs/screenshots',{recursive:true});
      await page.screenshot({path:`docs/screenshots/schedule-${testInfo.project.name}.png`,fullPage:true});
    }
    if(theme==='dark'){
      await page.getByRole('button',{name:'Ещё',exact:true}).click();
      await page.getByRole('button',{name:'Сменить тему'}).click();await page.keyboard.press('Escape');
    }
  }
  await page.getByRole('button',{name:'Сменить расписание',exact:true}).click();
  const modal=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  expect(modal.violations).toEqual([]);
});

test('last successful group is restored and a deep-link overrides it',async({page})=>{
  const groups=JSON.parse(fs.readFileSync('dist/api/groups/bakalavriat.json','utf8')).groups;
  const target=groups[1];await page.goto('./?group='+encodeURIComponent(target.name));
  await expect(page.getByRole('heading',{level:1})).toHaveText(target.name);
  await page.goto('./');await expect(page.getByRole('heading',{level:1})).toHaveText(target.name);
  await page.goto('./?group='+encodeURIComponent(groups[0].name));
  await expect(page.getByRole('heading',{level:1})).toHaveText(groups[0].name);
});

test('an unknown group link never silently opens the saved group',async({page})=>{
  const requests=[];page.on('request',request=>{if(request.url().includes('/api/schedule/'))requests.push(request.url());});
  await page.goto('./?group=not-a-real-group');
  await expect(page.locator('#pairsContainer')).toContainText('Группа из ссылки не найдена');
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  expect(requests).toEqual([]);
});

routedTest('loading skeleton becomes an explicit unavailable state on failure',async({page})=>{
  let release;const gate=new Promise(resolve=>release=resolve);
  await page.route('**/api/schedule/bakalavriat/1.json*',async route=>{await gate;await route.fulfill({status:503,body:'Unavailable'});});
  await page.goto('./');await expect(page.getByRole('status',{name:'Загрузка расписания'})).toBeVisible();
  release();await expect(page.locator('#pairsContainer')).toContainText('Источник расписания недоступен');
  await expect(page.getByRole('button',{name:'Повторить',exact:true})).toBeVisible();
});


test('restoring a saved group resolves its name when the file number changes',async({page})=>{
  const groups=JSON.parse(fs.readFileSync('dist/api/groups/bakalavriat.json','utf8')).groups;
  const target=groups[1];
  await page.addInitScript(({target,oldId})=>{
    localStorage.setItem('esstu_mode','student');localStorage.setItem('esstu_section','bakalavriat');
    localStorage.setItem('esstu_group_id',oldId);localStorage.setItem('esstu_group_name',target.name);
  },{target,oldId:groups[0].id});
  await page.goto('./');await expect(page.getByRole('heading',{level:1})).toHaveText(target.name);
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
});

routedTest('server fallback remains visible after a manual refresh',async({page})=>{
  const schedule=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  Object.assign(schedule,{is_stale_fallback:true,source_mode:'saved_snapshot',source_checked_at:'2026-10-12T01:00:00Z'});
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:schedule}));
  await ready(page);
  await expect(page.locator('#compactFreshnessText')).toContainText('Сохранённая копия');
  await expect(page.locator('#daySourceStatus')).toContainText('Сохранённая копия');
  await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.getByRole('button',{name:'Данные и обновления',exact:true}).click();
  await page.locator('#refreshSchedule').click();
  await expect(page.locator('#refreshSchedule')).toBeEnabled();
  await expect(page.locator('#freshnessBadge')).toContainText('Сохранённая копия');
  await expect(page.locator('#freshnessBadge')).not.toContainText('версия проверена');
});

routedTest('possible teacher identity collision is visible and clears for a group',async({page})=>{
  const payload=JSON.parse(fs.readFileSync('dist/api/teachers/all/bakalavriat.json','utf8'));
  const teacher=payload.teachers[0];
  teacher.identity_ambiguous=true;
  await page.route('**/api/teachers/all/bakalavriat.json*',route=>route.fulfill({json:payload}));
  await ready(page);
  await page.getByRole('button',{name:'Сменить расписание',exact:true}).click();
  await page.getByRole('button',{name:'Преподаватели',exact:true}).click();
  await page.locator('#teacherSearchInput').fill(teacher.profile.short_name);
  await page.locator('#teacherModalContent button').filter({hasText:teacher.profile.short_name}).first().click();
  await expect(page.locator('#teacherIdentityWarning')).toBeVisible();
  await expect(page.locator('#teacherIdentityWarning')).toContainText('Возможны данные нескольких преподавателей');
  await page.getByRole('button',{name:'Сменить расписание',exact:true}).click();
  await page.getByRole('button',{name:'Группы',exact:true}).click();
  await page.locator('#groupSearchInput').fill('1146 тпуп');
  await page.locator('#groupsListContainer button').filter({hasText:'1146 тпуп'}).click();
  await expect(page.locator('#teacherIdentityWarning')).toBeHidden();
});

test('secondary dialogs pass axe in dark and light themes',async({page})=>{
  test.slow();
  await ready(page);
  const scan=async()=>expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
  for(const theme of ['dark','light']){
    await page.emulateMedia({reducedMotion:'reduce'});
    await page.evaluate(theme=>{themeMode=theme;applyTheme();},theme);
    await page.getByRole('button',{name:'Аудитории',exact:true}).click();
    await expect(page.locator('#roomTimeControls')).toBeVisible();await scan();await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Ещё',exact:true}).click();await scan();await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.getByRole('button',{name:'Данные и обновления',exact:true}).click();await scan();await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Ещё',exact:true}).click();
    await page.getByRole('button',{name:'Корпуса кампуса',exact:true}).click();
    await expect(page.locator('#campusDiagram').getByRole('button').first()).toBeVisible();await scan();await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Ещё',exact:true}).click();
    await page.getByRole('button',{name:'Сессия и зачёты',exact:true}).click();
    await page.getByRole('button',{name:'+ Добавить личную запись',exact:true}).click();
    await expect(page.locator('#examModal')).toBeVisible();await scan();await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'К расписанию',exact:true}).click();
  }
});

routedTest('server-error cached response is not labeled offline',async({page})=>{
  const schedule=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:schedule,headers:{'X-ESSTU-Cache':'server-error'}}));
  await ready(page);
  await expect(page.locator('#compactFreshnessText')).toContainText('Ошибка сервера · Сохранённая копия');
  await expect(page.locator('#compactFreshnessText')).not.toContainText('Офлайн');
});

routedTest('stale publication warns without relying on the GitHub scheduler',async({page})=>{
  const status=JSON.parse(fs.readFileSync('dist/api/status.json','utf8'));
  let stale=true;
  await page.route('**/api/status.json',route=>route.fulfill({json:{...status,generated_at:stale?'2026-10-15T00:00:00Z':'2026-10-16T01:00:00Z'}}));
  await ready(page);
  await expect(page.locator('#publicationFreshnessWarning')).toContainText('более 12 часов');
  stale=false;await ready(page);
  await expect(page.locator('#publicationFreshnessWarning')).toBeHidden();
});
