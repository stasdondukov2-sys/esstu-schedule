const {test,expect}=require('./fixtures.cjs');
const {default:AxeBuilder}=require('@axe-core/playwright');
const fs=require('fs');
test.use({serviceWorkers:'block'});
const lesson=(pair,start,end,subject)=>({pair,start,end,subject,teacher:'Иванов И.И.',groups:'А'});
const rooms={rooms:[
  {room:'0105',slots:{'1:friday:3':[lesson(3,'13:00','14:35','Физика'),lesson(3,'13:00','14:35','Физика')],'1:friday:1':[lesson('1','09:00','10:35','Математика')],'1:friday:2':[lesson(2,'10:45','12:20','История')]}},
  {room:'0107',slots:{}},
  {room:'0302',slots:{'1:friday:1':[lesson(1,'09:00','10:35','Химия')]}},
]};
async function ready(page){
  await page.clock.setFixedTime(new Date('2026-10-16T20:00:00+08:00'));
  await page.route('**/api/rooms.json',route=>route.fulfill({json:rooms}));
  await page.goto('./');
  await expect(page.locator('#pairsContainer')).toHaveAttribute('aria-busy','false');
}

test('room manual slot determines status, sorted deduplicated rows and active filters',async({page})=>{
  await ready(page);
  await page.getByRole('button',{name:'Аудитории',exact:true}).click();
  await expect(page.locator('#roomPair')).toHaveValue('0');
  await expect(page.locator('[data-room-preset="now"]')).toHaveAttribute('aria-pressed','true');
  await page.locator('#roomPair').selectOption('1');
  await expect(page.locator('.room-context')).toHaveText('I неделя · Пт · 1 пара · 09:00');
  await expect(page.locator('[data-room="0105"] .chip-status')).toHaveText('Занята до 10:35');
  await expect(page.locator('[data-room="0107"] .chip-status')).toHaveText('Свободна');
  await expect(page.locator('[data-room="0105"] .room-lesson-time')).toHaveText(['09:00–10:35','10:45–12:20','13:00–14:35']);
  await expect(page.locator('[data-room="0105"] .room-slot.is-busy')).toHaveCount(3);
  await page.locator('[data-room-filter="busy"]').click();
  await expect(page.locator('[data-room-filter="busy"]')).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.room-card')).toHaveCount(2);
  await page.locator('[data-room-filter="free"]').click();
  await expect(page.locator('.room-card')).toHaveCount(1);
  await page.locator('[data-room-preset="next"]').click();
  await expect(page.locator('[data-room-preset="next"]')).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.room-context')).not.toContainText('сейчас');
  await page.locator('[data-room-preset="now"]').click();
  await expect(page.locator('#roomPair')).toHaveValue('0');
  await expect(page.locator('.room-context')).toContainText('сейчас');
});

test('single saved source chip keeps age and warning visible after reload failure and recovery',async({page})=>{
  await ready(page);
  await page.evaluate(()=>{
    currentSchedule.source_checked_at='2026-10-16T15:00:00+08:00';
    currentSchedule.is_stale_fallback=true;renderAll();
  });
  await expect(page.locator('#compactFreshnessText')).toContainText('Сохранённая копия · 5 ч назад');
  await expect(page.locator('#daySourceStatus button')).toHaveCount(1);
  await expect(page.locator('.campus-overview .campus-freshness')).toHaveCount(0);
  await page.evaluate(()=>{scheduleUnavailable('Проверка недоступности');renderAll();});
  await expect(page.locator('#compactFreshnessText')).toContainText('Сохранённая копия');
  await page.locator('#compactFreshnessText').click();
  await expect(page.locator('#freshnessModal')).toBeVisible();
  await page.locator('#refreshSchedule').click();
  await expect(page.locator('#refreshSchedule')).toBeEnabled();
  await page.keyboard.press('Escape');
  await expect(page.locator('#heroStatusLabel')).toHaveText('Занятия завершены');
  await expect(page.locator('#heroLessons .hero-skeleton')).toHaveCount(0);
  await expect(page.locator('#heroLessons')).toContainText('Все пары на сегодня закончились');
});

test('finished hero uses tomorrow from actual date, independent of selected agenda day',async({page})=>{
  await ready(page);
  await page.evaluate(()=>{
    const pair={number:1,start:'09:00',end:'10:35',lessons:[{subject:'Математика',type:'Лекция',type_code:'lecture',room:'0105'}]};
    currentSchedule={...currentSchedule,weeks:{1:{friday:{pairs:[pair]},saturday:{pairs:[pair]}}}};
    selectedWeek=1;selectedDayKey='monday';renderAll();
  });
  await expect(page.locator('#heroStatusLabel')).toHaveText('Занятия завершены');
  await expect(page.locator('.hero-upcoming')).toContainText('Завтра: 1 пара');
  await expect(page.locator('.hero-upcoming')).toContainText('09:00 · ауд. 0105');
  await page.locator('.hero-upcoming').click();
  await expect(page.locator('#selectedDaySummary')).toContainText('Суббота');
});

test('warning source stays collapsed and break identifies both adjacent times',async({page})=>{
  await ready(page);
  await page.evaluate(()=>{
    const lesson={subject:'Предмет не указан',type:'Требуется сверка',type_code:'other',tag:'англ, нем',parse_warning:'Название отсутствует — сверьте источник',raw:'ДАНЗАНОВА С.В. -',teacher:'Данзанова С.В.'};
    currentSchedule.weeks[1].friday={pairs:[{number:1,start:'09:00',end:'10:35',lessons:[lesson]},{number:2,start:'10:45',end:'12:20',lessons:[{subject:'Физика',type:'Лекция',type_code:'lecture'}]}]};
    selectedWeek=1;selectedDayKey='friday';renderAll();
  });
  const warning=page.locator('.lesson-warning');
  await expect(warning.locator('summary')).toContainText('Требуется сверка');
  await expect(warning.locator('summary')).not.toContainText('ДАНЗАНОВА');
  await expect(warning.locator('.whitespace-pre-wrap')).toBeHidden();
  await warning.locator('summary').click();
  await expect(warning.locator('.whitespace-pre-wrap')).toHaveText('ДАНЗАНОВА С.В. -');
  await expect(page.locator('.lesson-break')).toHaveText('10:35–10:45 · Перерыв 10 мин');
});

test('picker sorts courses and names, exposes favorites and marks current group',async({page})=>{
  await ready(page);
  await page.getByRole('button',{name:'Поиск',exact:true}).click();
  await page.evaluate(()=>{
    allGroups=[{name:'1146 тпуп',id:'1',section:'bakalavriat',course:2},{name:'245',id:'2',section:'bakalavriat',course:1},{name:'244',id:'3',section:'bakalavriat',course:1}];
    savedState.groupName='1146 тпуп';savedState.section='bakalavriat';setCourseFilter(0);
  });
  await expect(page.locator('#groupsListContainer .group-name')).toHaveText(['244','245','1146 тпупВыбрана']);
  await expect(page.locator('#groupsListContainer button[aria-pressed="true"] .group-current')).toBeVisible();
  await expect(page.locator('#favoritesSection')).toBeVisible();
  await expect(page.locator('#recentSection')).toBeVisible();
  const focus=await page.locator('#groupSearchInput').evaluate(node=>{
    node.focus();const css=getComputedStyle(node);return {shadow:css.boxShadow,offset:css.outlineOffset};
  });
  expect(focus).toEqual({shadow:'none',offset:'0px'});
});

test('radar accessibility, readable labels and responsive views in both themes',async({page},testInfo)=>{
  await ready(page);
  for(const theme of ['dark','light']){
    await page.evaluate(theme=>{themeMode=theme;applyTheme();},theme);
    await page.getByRole('button',{name:'Аудитории',exact:true}).click();
    await page.locator('#roomPair').selectOption('1');
    const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    expect(result.violations).toEqual([]);
    for(const width of [320,390,768,1440]){
      await page.setViewportSize({width,height:900});
      expect(await page.locator('#roomsModal .simple-sheet').evaluate(node=>node.scrollWidth<=node.clientWidth)).toBe(true);
    }
    await page.keyboard.press('Escape');
  }
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.evaluate(()=>{themeMode='dark';applyTheme();});
  await page.setViewportSize({width:testInfo.project.name==='mobile'?390:1440,height:1000});
  fs.mkdirSync('preview/design-review',{recursive:true});
  await page.screenshot({path:`preview/design-review/day-${testInfo.project.name}.png`,fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'Поиск',exact:true}).click();
  await page.screenshot({path:`preview/design-review/search-${testInfo.project.name}.png`,animations:'disabled'});
  await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Аудитории',exact:true}).click();
  await page.screenshot({path:`preview/design-review/rooms-${testInfo.project.name}.png`,animations:'disabled'});
});
