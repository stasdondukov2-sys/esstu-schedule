const {test,expect}=require('@playwright/test');
const {default:AxeBuilder}=require('@axe-core/playwright');
async function ready(page){await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');}

test('day controls fit small screens and future lessons never get a current label',async({page})=>{
  await ready(page);
  await page.evaluate(()=>{simOverride={dayIndex:3,hours:9,minutes:20};selectedWeek=getWeekNum(getUlanUdeNow());selectedDayKey='thursday';renderAll();});
  await expect(page.locator('#heroStatusLabel')).toHaveText('Следующая пара');
  await expect(page.locator('[data-current-label]:visible')).toHaveCount(0);
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await expect(page.locator('#dayTabs button')).toHaveCount(6);
    for(const button of await page.locator('#dayTabs button').all())await expect(button).toBeInViewport();
  }
});

test('glass search remains accessible in dark mode and keyboard motion is immediate',async({page})=>{
  await ready(page);
  const search=page.getByRole('button',{name:'Поиск',exact:true});
  await search.focus();await page.keyboard.press('Enter');
  await expect(page.locator('#searchModal .simple-sheet')).not.toHaveClass(/motion-enter/);
  expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);
  await page.keyboard.press('Escape');
  await page.emulateMedia({reducedMotion:'reduce'});await search.click();
  await expect(page.locator('#searchModal .simple-sheet')).not.toHaveClass(/motion-enter/);
});

test('glass note dialog saves and deletes a lesson note',async({page})=>{
  await ready(page);
  await page.evaluate(()=>{selectedWeek=1;selectedDayKey='thursday';renderAll();});
  const lesson=page.locator('.lesson-detail').first();
  await lesson.locator('summary').click();
  await lesson.getByRole('button',{name:'Добавить заметку',exact:true}).click();
  await page.locator('#noteTextarea').fill('Проверка заметки в новом интерфейсе');
  await page.getByRole('button',{name:'Сохранить',exact:true}).click();
  await expect(page.locator('#noteModal')).toBeHidden();
  await lesson.locator('summary').click();
  await expect(lesson).toContainText('Проверка заметки в новом интерфейсе');
  await lesson.getByRole('button',{name:'Изменить заметку',exact:true}).click();
  await expect(page.locator('#noteTextarea')).toHaveValue('Проверка заметки в новом интерфейсе');
  await page.getByRole('button',{name:'Удалить',exact:true}).click();
  await lesson.locator('summary').click();
  await expect(lesson).not.toContainText('Проверка заметки в новом интерфейсе');
});
