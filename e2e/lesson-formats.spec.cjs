const {test,expect}=require('./fixtures.cjs');
const fs=require('fs');

test('real source room annotation renders a subject, teacher and room without a parse warning',async({page})=>{
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/spezialitet/1.json','utf8'));
  await page.goto('./?group='+encodeURIComponent(data.group_name)+'&section=spezialitet');
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  await expect(page.getByRole('heading',{level:1})).toHaveText(data.group_name);
  await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.locator('#weekControls button').first().click();await page.keyboard.press('Escape');
  await page.locator('#dayTabs button').nth(3).click();
  const rows=page.locator('#pairsContainer .lesson-detail').filter({hasText:'Основы безопасности и защиты Родины'});
  await expect(rows).toHaveCount(2);
  for(const row of await rows.all()){
    await expect(row).not.toHaveClass(/lesson-warning/);
    await expect(row.locator('xpath=ancestor::article[1]').locator('.lesson-room')).toHaveText('8236 и/д');
    await expect(row.locator('.lesson-summary')).toContainText('Ринчинова С.Б.');
    await row.locator('.lesson-subject').first().click();
    await expect(page.locator('#replicaNoteContext')).toContainText('Пометки источника: экол');
    await expect(page.locator('#replicaNoteContext').getByRole('button',{name:'Ринчинова С.Б.'})).toBeVisible();
    await page.keyboard.press('Escape');
  }
});
