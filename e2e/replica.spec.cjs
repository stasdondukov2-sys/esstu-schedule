const {test,expect}=require('./fixtures.cjs');
const {default:AxeBuilder}=require('@axe-core/playwright');
const fs=require('fs');
async function ready(page){await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');}

test('approved compact shell retains real source slots and working subgroup/week controls',async({page})=>{
  await ready(page);
  await expect(page.locator('.campus-nav')).toHaveCount(0);
  await expect(page.locator('#moreMenuModal .campus-overview')).toHaveCount(1);
  const source=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  await expect(page.locator('#pairsContainer>article')).toHaveCount(source.weeks['1'].friday.pairs.length);
  const initial=await page.locator('#replicaParity').getAttribute('aria-label');await page.locator('#replicaParity').click();await expect(page.locator('#replicaParity')).not.toHaveAttribute('aria-label',initial);await page.locator('#replicaParity').click();
  for(const label of ['1 п/г','2 п/г','Все п/г']){await page.locator('#replicaSubgroup').click();await expect(page.locator('#replicaSubgroup')).toHaveText(label);}
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:900});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);const frame=await page.locator('.campus-shell').boundingBox();expect(frame.width).toBeLessThanOrEqual(402);await expect(page.locator('#dayTabs button')).toHaveCount(6);}
});

test('teacher sheet previews a real teacher before explicit navigation and returns keyboard focus',async({page})=>{
  await ready(page);const launcher=page.getByRole('button',{name:'Поиск преподавателя',exact:true});await launcher.focus();await page.keyboard.press('Enter');
  await expect(page.locator('#replicaTeacherQuery')).toBeFocused();
  await page.locator('#replicaTeacherResults .replica-directory-row').first().click();
  await expect(page.getByRole('heading',{level:1})).toHaveText('1146 тпуп');
  await expect(page.locator('#replicaTeacherPreview .replica-preview-timeline>div')).toHaveCount(6);
  await page.keyboard.press('Escape');await expect(launcher).toBeFocused();await launcher.click();
  await page.getByRole('button',{name:'Открыть полное расписание →',exact:true}).click();
  await expect(page.getByRole('heading',{level:1})).not.toHaveText('1146 тпуп');await expect(page.locator('#teacherExplorerModal')).toBeHidden();
});

test('a real empty slot owns an escaped persistent note and restores focus after saving',async({page})=>{
  await ready(page);const empty=page.locator('.empty-slot-card').first();await empty.focus();await page.keyboard.press('Enter');
  await expect(page.locator('#noteModal')).toBeVisible();await page.locator('#noteTextarea').fill('<b>Повторить билеты</b>');
  await page.getByRole('button',{name:'Сохранить',exact:true}).click();await expect(empty).toBeFocused();await expect(empty).toContainText('<b>Повторить билеты</b>');await expect(empty.locator('b')).toHaveCount(0);
  await page.reload();await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');await expect(page.locator('.empty-slot-card').first()).toContainText('<b>Повторить билеты</b>');
});

test('room preview merges equivalent source rows and preserves their real group labels',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Аудитории',exact:true}).click();
  await page.locator('#roomSearchInput').fill('0427');await page.locator('#roomWeek').selectOption('1');await page.locator('#roomDay').selectOption('1');
  const source=JSON.parse(fs.readFileSync('dist/api/rooms.json','utf8')).rooms.find(room=>room.room==='0427').slots['1:tuesday:1'];
  expect(source.length).toBeGreaterThan(1);const first=page.locator('#replicaRoomPreview .replica-preview-timeline>div').first();
  await expect(first.locator('p')).toHaveCount(1);for(const record of source)await expect(first).toContainText(record.groups);
  await expect(first).toContainText('Гармаев В.Д.');
});

test('dedicated teacher and selected-room sheets pass axe in both themes',async({page})=>{
  test.slow();await ready(page);await page.emulateMedia({reducedMotion:'reduce'});
  for(const theme of ['dark','light']){
    await page.evaluate(theme=>{themeMode=theme;applyTheme();},theme);
    await page.getByRole('button',{name:'Поиск преподавателя',exact:true}).click();await page.locator('#replicaTeacherResults .replica-directory-row').first().click();
    expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Аудитории',exact:true}).click();await expect(page.locator('.room-card').first()).toBeVisible();const room=await page.locator('.room-card').first().getAttribute('data-room');await page.locator('#roomSearchInput').fill(room);
    await expect(page.locator('#replicaRoomPreview .replica-preview-timeline>div')).toHaveCount(6);
    await expect(page.locator('#replicaRoomPreview .replica-map-link')).toHaveAttribute('href',/https:\/\/2gis.ru\/ulanude\/search\//);
    expect((await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()).violations).toEqual([]);await page.keyboard.press('Escape');
  }
});
