const {test,expect}=require('@playwright/test');
const {default:AxeBuilder}=require('@axe-core/playwright');
const fs=require('fs');

async function ready(page){await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');}
test('dialogs trap focus, close with Escape and return to the launcher',async({page})=>{
  await ready(page);
  const launcher=page.getByRole('button',{name:'Поиск',exact:true});await launcher.click();
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
  await page.getByRole('button',{name:'Поиск',exact:true}).click();
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

test('loading skeleton becomes an explicit unavailable state on failure',async({page})=>{
  let release;const gate=new Promise(resolve=>release=resolve);
  await page.route('**/api/schedule/bakalavriat/1.json*',async route=>{await gate;await route.fulfill({status:503,body:'Unavailable'});});
  await page.goto('./');await expect(page.getByRole('status',{name:'Загрузка расписания'})).toBeVisible();
  release();await expect(page.locator('#pairsContainer')).toContainText('Источник расписания недоступен');
  await expect(page.getByRole('button',{name:'Повторить',exact:true})).toBeVisible();
});
