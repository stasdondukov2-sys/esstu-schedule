const {test,expect}=require('./fixtures.cjs');
const fs=require('fs'),path=require('path');
const root=process.env.ESSTU_E2E_SITE||'preview/contract-site';
const read=name=>JSON.parse(fs.readFileSync(path.join(root,'api',name),'utf8'));
const groups=read('groups/bakalavriat.json').groups;
const group=groups.find(item=>!read(`schedule/bakalavriat/${item.id}.json`).is_incomplete);
const teachers=read('teachers/all/bakalavriat.json').teachers;
const teacher=teachers.find(item=>!item.is_incomplete);
const teacherName=teacher.profile.full_name||teacher.profile.short_name;
async function ready(page){
  await page.goto('./?group='+encodeURIComponent(group.name));
  await expect(page.getByRole('heading',{level:1})).toHaveText(group.name);
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
}
test('new shell reads a published group and source details',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await ready(page);await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.getByRole('button',{name:'Данные и обновления',exact:true}).click();
  await expect(page.locator('#parseQualityStatus')).toBeVisible();
  expect(errors).toEqual([]);
});
test('new shell can search the published group catalog',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Сменить расписание',exact:true}).click();
  await page.locator('#groupSearchInput').fill(group.name);
  await expect(page.locator('#groupsListContainer')).toContainText(group.name);
});
test('new shell opens a published teacher',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Сменить расписание',exact:true}).click();
  await page.getByRole('button',{name:'Преподаватели',exact:true}).click();
  await page.locator('#teacherSearchInput').fill(teacherName);
  await page.locator('#teacherModalContent button').filter({hasText:teacherName}).first().click();
  await expect(page.getByRole('heading',{level:1})).toContainText(teacherName);
});
test('new shell renders the published room catalog',async({page})=>{
  await ready(page);await page.getByRole('button',{name:'Аудитории',exact:true}).click();
  await expect(page.locator('#roomsModal')).toBeVisible();
  await expect(page.locator('#roomsModal')).not.toContainText('Загрузка…');
  await expect(page.locator('#roomsModal')).not.toContainText('Не удалось загрузить');
});
