const {test,expect}=require('./fixtures.cjs');
const fs=require('fs');

test('real source room annotation renders a subject, teacher and room without a parse warning',async({page})=>{
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/spezialitet/1.json','utf8'));
  await page.goto('./?group='+encodeURIComponent(data.group_name)+'&section=spezialitet');
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  await expect(page.getByRole('heading',{level:1})).toHaveText(data.group_name);
  await page.locator('#weekControls button').first().click();
  await page.locator('#dayTabs button').nth(3).click();
  const rows=page.locator('#pairsContainer .lesson-detail').filter({hasText:'Основы безопасности и защиты Родины'});
  await expect(rows).toHaveCount(2);
  for(const row of await rows.all()){
    await expect(row).not.toHaveClass(/lesson-warning/);
    await expect(row.locator('.lesson-room')).toHaveText('ауд. 8236 и/д');
    await expect(row.locator('summary')).toContainText('Ринчинова С.Б.');
    await row.locator('summary').click();
    await expect(row).toContainText('Пометки источника: экол');
    await expect(row.getByRole('button',{name:'Преподаватель',exact:true})).toBeVisible();
    await row.locator('summary').click();
  }
});
