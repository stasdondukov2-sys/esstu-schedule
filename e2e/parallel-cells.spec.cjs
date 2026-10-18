const {test,expect}=require('./fixtures.cjs');
const fs=require('fs');
const routedTest=test.extend({serviceWorkers:'block'});

test('564-2 screenshot case shows two real parallel lessons and opens the second teacher',async({page})=>{
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/147.json','utf8'));
  await page.goto('./?group='+encodeURIComponent(data.group_name)+'&section=bakalavriat');
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  await expect(page.getByRole('heading',{level:1})).toHaveText('564-2');
  await page.getByRole('button',{name:'Ещё',exact:true}).click();await page.locator('#weekControls button').first().click();await page.keyboard.press('Escape');await page.locator('#dayTabs button').first().click();
  const index=data.weeks['1'].monday.pairs.findIndex(pair=>pair.number===3);
  const pair=page.locator(`#pairsContainer>[data-pair-index="${index}"]`);
  await expect(pair.locator('.lesson-detail')).toHaveCount(2);
  await expect(pair.locator('.lesson-warning')).toHaveCount(0);
  await expect(pair.locator('.lesson-subject')).toHaveText(['Операционные системы','Операционные системы']);
  await expect(pair.locator('.lesson-room')).toHaveText(['25-214','25-312']);
  await expect(pair.locator('.lesson-summary').nth(0)).toContainText('Глушкова И.И.');
  await expect(pair.locator('.lesson-summary').nth(1)).toContainText('Гармаев Ч.Б.');
  await pair.locator('.replica-teacher-link').nth(1).click();
  await expect(page.locator('#replicaTeacherPreview')).toContainText('Гармаев Ч.Б.');
  await page.getByRole('button',{name:'Открыть полное расписание →',exact:true}).click();
  await expect(page.getByRole('heading',{level:1})).toContainText('Гармаев Ч.Б.');
});

routedTest('unresolved independent lists show actual course names and keep the source available',async({page})=>{
  const data=JSON.parse(fs.readFileSync('dist/api/schedule/bakalavriat/1.json','utf8'));
  const raw='Иностранный язык (немецкий) Иностранный язык (английский) Иностранный язык (английский) ПЕТРОВ И.И. ИВАНОВ П.П. - а.0105- а.0107';
  const lesson={subject:'Несколько занятий — сверьте с источником',type:'Требуется сверка',type_code:'other',raw,parse_warning:'Не удалось сопоставить преподавателей и аудитории',needs_review:true,teacher:'',room:''};
  data.weeks={'1':{friday:{pairs:[{number:1,start:'09:00',end:'10:35',lessons:[lesson]}]}}};
  await page.route('**/api/schedule/bakalavriat/1.json*',route=>route.fulfill({json:data}));
  await page.goto('./');await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
  const warning=page.locator('#pairsContainer .lesson-warning');
  await expect(warning.locator('.lesson-subject')).toHaveText('Иностранный язык (немецкий) / Иностранный язык (английский)');
  await expect(warning.locator('.whitespace-pre-wrap')).toBeHidden();await warning.locator('.lesson-subject').first().click();
  await expect(page.locator('#replicaNoteContext .replica-source-raw')).toHaveText(raw);
  await expect(warning.getByRole('button',{name:'Преподаватель',exact:true})).toHaveCount(0);
});
