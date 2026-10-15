let searchMode = 'student';
function getTypeBorderClass(code) {
  return {lecture:'border-l-purple-500',practice:'border-l-emerald-500',lab:'border-l-amber-500',sport:'border-l-sky-500',exam:'border-l-rose-500',test:'border-l-rose-500'}[code] || 'border-l-slate-400';
}
function singleBuilding(pair) {
  const buildings=(pair.lessons || []).map(lesson=>decodeEsstuRoom(lesson.room)?.building);
  return buildings.length && buildings.every(building=>building && building===buildings[0]) ? buildings[0] : null;
}
function getWeekRangeDates(weekNumber, now=getUlanUdeNow()) {
  const monday=new Date(now.getFullYear(),now.getMonth(),now.getDate()-(now.getDay()+6)%7);
  // I/II select the current week or its neighbour, matching the existing week selector.
  const current=getWeekNum(now),shift=Number(weekNumber)===current?0:(Number(weekNumber)>current?7:-7);
  monday.setDate(monday.getDate()+shift);
  return Object.fromEntries(DAY_KEYS.map((key,index)=>{
    const date=new Date(monday);date.setDate(monday.getDate()+index);
    return [key,{date,shortLabel:date.toLocaleDateString('ru-RU',{day:'numeric',month:'short'}).replace(/\.$/,''),isToday:date.toDateString()===now.toDateString()}];
  }));
}
function dayDateMeta(day,key,dates) {
  // Session dates are explicit source data, not a recurring weekday template.
  if(day?.session_date)return {shortLabel:day.session_date,isToday:false};
  return dates[key];
}
function renderCalendarDays() {
  const dates=getWeekRangeDates(selectedWeek),week=currentSchedule?.weeks?.[selectedWeek] || {};
  document.getElementById('dayTabs').innerHTML=DAY_NAMES.map(day=>{
    const meta=dayDateMeta(week[day.key],day.key,dates),active=day.key===selectedDayKey;
    const count=(week[day.key]?.pairs || []).filter(pair=>filterLessons(pair.lessons).length).length;
    return `<button onclick="selectDay('${day.key}')" aria-pressed="${active}" ${meta.isToday?'aria-current="date"':''} class="flex-1 min-w-[58px] px-1 py-2 rounded-xl border text-center ${active?'bg-teal-600 border-teal-600 text-white':'bg-white dark:bg-[#101c2e] border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300'}"><div class="text-xs font-bold">${day.short}${meta.isToday?' <span class="text-amber-400" aria-label="Сегодня">•</span>':''}${hasDayChanges(selectedWeek,day.key)?' ⚡':''}</div><div class="text-[10px] mt-1 whitespace-nowrap">${escapeHTML(meta.shortLabel)}</div><div class="text-[9px] mt-1 ${active?'text-teal-100':'text-slate-400'}">${currentSchedule?.is_incomplete?'нет данных':count?count+' '+pairWord(count):'нет пар'}</div></button>`;
  }).join('');
  const day=DAY_NAMES.find(day=>day.key===selectedDayKey),meta=dayDateMeta(week[selectedDayKey],selectedDayKey,dates);
  document.getElementById('selectedDaySummary').textContent=day?`${day.full}, ${meta.shortLabel}${meta.isToday?' · Сегодня':''}`:'';
}
function pairWord(count) {return count%100>=11 && count%100<=14?'пар':count%10===1?'пара':count%10>=2 && count%10<=4?'пары':'пар';}
function heroState(schedule,now) {
  if(schedule?.is_incomplete)return {kind:'incomplete'};
  if(hasDatedSchedule(schedule))return {kind:'dated'};
  const dayIndex=(now.getDay()+6)%7,minutes=now.getHours()*60+now.getMinutes()+now.getSeconds()/60;
  if(dayIndex===6)return {kind:'empty'};
  const day=schedule.weeks?.[getWeekNum(now)]?.[DAY_KEYS[dayIndex]];
  if(day?.session_date)return {kind:'dated'}; // A weekday alone cannot prove a session is today.
  const pairs=(day?.pairs || []).map(pair=>({...pair,lessons:filterLessons(pair.lessons)})).filter(pair=>pair.lessons.length).sort((a,b)=>timeToMinutes(a.start)-timeToMinutes(b.start));
  const current=pairs.find(pair=>minutes>=timeToMinutes(pair.start) && minutes<timeToMinutes(pair.end));
  const next=pairs.find(pair=>minutes<timeToMinutes(pair.start));
  if(current)return {kind:'current',pair:current,next,remaining:Math.ceil(timeToMinutes(current.end)-minutes),progress:Math.min(100,Math.max(0,100*(minutes-timeToMinutes(current.start))/(timeToMinutes(current.end)-timeToMinutes(current.start))))};
  if(next)return {kind:'next',pair:next,remaining:Math.ceil(timeToMinutes(next.start)-minutes)};
  return {kind:pairs.length?'finished':'empty'};
}
let campusDayStamp='';
function updateCampusHero() {
  const now=getUlanUdeNow(),week=getWeekNum(now);
  document.getElementById('weekBadge').textContent=week===1?'I неделя':'II неделя';
  document.getElementById('clockDisplay').textContent=now.toLocaleString('ru-RU')+' · Улан-Удэ'+(simOverride?' · ТЕСТ':'');
  const stamp=now.toDateString();
  if(stamp!==campusDayStamp){campusDayStamp=stamp;renderCalendarDays();if(currentSchedule && scheduleTab==='session')renderPairsList();}
  if(!currentSchedule)return;
  const state=heroState(currentSchedule,now),pair=state.pair;
  const label=document.getElementById('heroStatusLabel'),remaining=document.getElementById('heroRemainingTime'),lessons=document.getElementById('heroLessons'),next=document.getElementById('heroNextPairRow');
  document.getElementById('heroProgressWrap').classList.toggle('hidden',state.kind!=='current');
  next.classList.toggle('hidden',!state.next);
  remaining.classList.toggle('hidden',!pair);
  updateCurrentCards(now);
  if(!pair){
    label.textContent=state.kind==='finished'?'Занятия завершены':'Сегодня';remaining.textContent='';
    lessons.innerHTML=`<p class="font-semibold text-sm">${state.kind==='finished'?'Все пары на сегодня закончились':currentSchedule.is_incomplete?'Данные неполные — проверьте источник':state.kind==='dated'?'Занятия по отдельным датам — проверьте расписание ниже':'На сегодня пар нет'}</p>`;
    delete lessons.dataset.content;
    return;
  }
  label.textContent=state.kind==='current'?`Сейчас · ${pair.number}-я пара`:'Следующая пара';
  remaining.textContent=state.kind==='current'?`до конца ${state.remaining} мин`:`через ${state.remaining} мин`;
  // Build only when the pair changes, so keyboard focus on room actions survives clock ticks.
  const html=pair.lessons.map((lesson,index)=>{
    const room=decodeEsstuRoom(lesson.room),subtitle=appMode==='student'?lesson.teacher:lesson.groups;
    return `<div class="flex items-start justify-between gap-3 ${index?'pt-3 border-t border-slate-100 dark:border-slate-800':''}"><div class="min-w-0 flex-1"><div class="text-[11px] text-slate-500 dark:text-slate-400">${escapeHTML(pair.start)}–${escapeHTML(pair.end)} · ${escapeHTML(lesson.type || 'Занятие')}${lesson.tag?' · '+escapeHTML(lesson.tag):''}</div><div class="text-base font-bold leading-snug mt-1">${escapeHTML(lesson.subject)}</div><div class="text-xs text-slate-500 dark:text-slate-400 mt-1">${escapeHTML(subtitle || '')}</div></div>${room?`<div class="shrink-0 text-right"><button onclick="heroRoomAction(${index})" class="px-2.5 rounded-xl bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 text-xs font-bold">${escapeHTML(room.badge)}</button>${room.building?`<p class="text-[10px] text-slate-500 dark:text-slate-400 mt-1" title="По обозначению аудитории">${escapeHTML(room.building)}</p>`:''}</div>`:''}</div>`;
  }).join('');
  if(lessons.dataset.content!==html){lessons.innerHTML=html;lessons.dataset.content=html;}
  if(state.kind==='current'){
    document.getElementById('heroProgress').setAttribute('aria-valuenow',Math.round(state.progress));
    document.getElementById('heroProgressFill').style.width=state.progress+'%';
  }
  if(state.next)next.textContent=`Далее: ${state.next.start} · `+state.next.lessons.map(lesson=>`${lesson.subject}${lesson.room?' · ауд. '+lesson.room:''}`).join(' / ');
}
function heroRoomAction(index) {const pair=heroState(currentSchedule,getUlanUdeNow()).pair;if(pair?.lessons[index]?.room)openRoomsModal(pair.lessons[index].room);}
function updateCurrentCards(now) {
  if(viewMode!=='day')return;
  const day=DAY_KEYS[(now.getDay()+6)%7],minutes=now.getHours()*60+now.getMinutes();
  const pairs=currentSchedule?.weeks?.[selectedWeek]?.[selectedDayKey]?.pairs || [];
  for(const card of document.querySelectorAll('[data-pair-index]')){
    const pair=pairs[Number(card.dataset.pairIndex)];
    const active=pair && !currentSchedule.weeks[selectedWeek][selectedDayKey].session_date && day===selectedDayKey && getWeekNum(now)===selectedWeek && minutes>=timeToMinutes(pair.start) && minutes<timeToMinutes(pair.end);
    card.classList.toggle('border-teal-500',active);card.classList.toggle('border-slate-200',!active);card.classList.toggle('dark:border-slate-800',!active);
    card.querySelector('[data-current-label]')?.classList.toggle('hidden',!active);
  }
}
const dialogFocus = new Map();
function openSimpleDialog(id) {
  const dialog=document.getElementById(id);
  if(dialog.classList.contains('hidden'))dialogFocus.set(id,document.activeElement);
  dialog.classList.remove('hidden');
  document.body.style.overflow='hidden';
  dialog.querySelector('button')?.focus();
}
function closeSimpleDialog(id) {
  document.getElementById(id)?.classList.add('hidden');
  if (!document.querySelector('.simple-overlay:not(.hidden)')) document.body.style.overflow='';
  dialogFocus.get(id)?.focus();
}
function closeSearchModal() { closeSimpleDialog('searchModal'); }
function openSearchModal(mode = appMode) {
  searchMode=mode==='teacher'?'teacher':'student';
  openSimpleDialog('searchModal');
  document.getElementById('groupModal').classList.toggle('hidden',searchMode!=='student');
  document.getElementById('teacherModal').classList.toggle('hidden',searchMode!=='teacher');
  for (const [id,value] of [['searchStudentTab','student'],['searchTeacherTab','teacher']]) {
    const button=document.getElementById(id),active=searchMode===value;
    button.className=`px-4 rounded-xl text-sm ${active?'bg-teal-600 text-white':'text-slate-500'}`;
    button.setAttribute('aria-pressed',String(active));
  }
  renderFavoritesBar();
  if(searchMode==='student') {
    renderGroupsModalList();document.getElementById('groupSearchInput').focus();
    if(!allGroups.length) loadGroups(savedState.section);
  } else {
    renderTeacherModalContent();document.getElementById('teacherSearchInput').focus();
    if(!allTeachersDirectory.length) loadDepartmentsAndTeachers();
  }
}
function compactLessonAction(action,pairIndex,lessonIndex) {
  const pair=currentSchedule?.weeks?.[selectedWeek]?.[selectedDayKey]?.pairs?.[pairIndex];
  const lesson=pair?.lessons?.[lessonIndex];
  if(!lesson)return;
  if(action==='note')openNoteModal(makeNoteKey(lesson.subject,pair.number),lesson.subject);
  if(action==='teacher')openTeacherFromLesson(lesson.teacher_key,lesson.teacher_caf_id || '');
  if(action==='room')openRoomsModal(lesson.room);
}
function renderCompactDay(container) {
  const day=currentSchedule.weeks?.[selectedWeek]?.[selectedDayKey];
  if(!day){container.innerHTML='<p class="text-sm text-slate-500 py-8 text-center">Нет данных на этот день</p>';return;}
  const now=getUlanUdeNow(),today=DAY_KEYS[(now.getDay()+6)%7];
  const isToday=!day.session_date && today===selectedDayKey && getWeekNum(now)===selectedWeek;
  const minutes=now.getHours()*60+now.getMinutes(),notes=getNotesMap();
  let previous=null;
  const rows=(day.pairs || []).map((pair,pairIndex)=>{
    const visible=filterLessons(pair.lessons);
    if(!visible.length)return '';
    const current=isToday && minutes>=timeToMinutes(pair.start) && minutes<timeToMinutes(pair.end);
    let gap='';
    if(previous){
      const duration=timeToMinutes(pair.start)-timeToMinutes(previous.end);
      const before=singleBuilding(previous),after=singleBuilding({...pair,lessons:visible});
      if(duration>0)gap=`<p class="pl-3 py-1 text-[11px] text-slate-500 dark:text-slate-400">Перерыв ${duration} мин${before && after && before!==after ? ` · <span class="text-amber-700 dark:text-amber-300">Смена корпуса по расписанию: ${escapeHTML(before)} → ${escapeHTML(after)}</span>`:''}</p>`;
    }
    previous={...pair,lessons:visible};
    const lessons=pair.lessons.map((lesson,index)=>{
      if(!visible.includes(lesson))return '';
      const room=decodeEsstuRoom(lesson.room),note=notes[makeNoteKey(lesson.subject,pair.number)];
      const subtitle=appMode==='student'?lesson.teacher:lesson.groups;
      return `<details class="lesson-detail group py-1 pl-3 border-l-[3px] ${getTypeBorderClass(lesson.type_code)} ${index?'mt-3':''}">
        <summary class="min-h-[60px] rounded-lg focus-visible:outline focus-visible:outline-teal-500">
          <div class="text-[10px] font-semibold text-slate-500 dark:text-slate-400 mb-1">${escapeHTML(lesson.type || 'Занятие')}${lesson.tag ? ' · '+escapeHTML(lesson.tag):''}</div>
          <div class="flex justify-between items-start gap-2"><span class="font-bold text-sm leading-snug">${escapeHTML(lesson.subject)}</span><span class="shrink-0 text-xs font-semibold text-teal-600 dark:text-teal-300">${lesson.room?'ауд. '+escapeHTML(lesson.room):''}</span></div>
          <div class="flex justify-between items-center gap-2 mt-1"><span class="text-xs text-slate-500 dark:text-slate-400">${escapeHTML(subtitle || (appMode==='student'?'Преподаватель не указан':'Группы не указаны'))}${note?' · 📝':''}</span><span aria-hidden="true" class="detail-chevron text-slate-400 text-xs">⌄</span></div>
        </summary>
        <div class="pt-1 pb-2 space-y-2 text-xs"><p class="text-slate-500">${escapeHTML([lesson.type,lesson.tag].filter(Boolean).join(' · '))}</p>
          ${lesson.parse_warning?`<p class="text-amber-700 dark:text-amber-300">${escapeHTML(lesson.parse_warning)}</p><p class="text-slate-500 dark:text-slate-400 whitespace-pre-wrap">${escapeHTML(lesson.raw)}</p>`:''}
          ${room?`<p class="text-teal-600 dark:text-teal-300">${escapeHTML(room.location)}</p>`:''}
          ${renderLessonMeta(lesson,pair.number)}
          ${note?`<p class="p-2 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-200 whitespace-pre-wrap">${escapeHTML(note)}</p>`:''}
          <div class="flex flex-wrap gap-2">
            ${lesson.room?`<button onclick="compactLessonAction('room',${pairIndex},${index})" class="px-3 rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-300">Аудитория</button>`:''}
            ${appMode==='student' && lesson.teacher_key?`<button onclick="compactLessonAction('teacher',${pairIndex},${index})" class="px-3 rounded-xl bg-slate-100 dark:bg-slate-800">Преподаватель</button>`:''}
            <button onclick="compactLessonAction('note',${pairIndex},${index})" class="px-3 rounded-xl bg-slate-100 dark:bg-slate-800">${note?'Изменить заметку':'Добавить заметку'}</button>
          </div>
        </div></details>`;
    }).join('');
    return `${gap}<article data-pair-index="${pairIndex}" class="rounded-2xl p-3.5 bg-white dark:bg-[#101c2e] border ${current?'border-teal-500':'border-slate-200 dark:border-slate-800'} flex gap-3">
      <div class="w-12 shrink-0 text-center pt-1"><div class="font-semibold text-xs">${escapeHTML(pair.start)}</div><div class="text-[11px] text-slate-400 mt-1">${escapeHTML(pair.end)}</div><div class="text-[10px] text-slate-400 mt-2">${pair.number} пара</div><span data-current-label class="${current?'':'hidden'} text-[9px] text-teal-500 font-bold">СЕЙЧАС</span></div><div class="min-w-0 flex-1">${lessons}</div></article>`;
  }).filter(Boolean);
  container.innerHTML=rows.join('') || '<div class="text-center py-10"><p class="font-semibold">В этот день занятий нет</p><p class="text-xs text-slate-500 mt-2">Выберите другой день</p></div>';
}
function updateCompactUI() {
  if(!currentSchedule)return;
  document.getElementById('currentEntityBtnText').textContent=appMode==='student'?savedState.groupName:(currentSchedule.profile?.short_name || savedState.teacherKey);
  const checked=currentSchedule.source_checked_at,offline=lastDelivery?.cached || !navigator.onLine;
  const fallback=currentSchedule.is_stale_fallback || ['local_fallback','saved_snapshot'].includes(currentSchedule.source_mode);
  const text=checked?`Проверено ${displayDate(checked)}`:`Сборка ${displayDate(currentSchedule.generated_at)}`;
  document.getElementById('compactFreshnessText').textContent=(currentSchedule.is_incomplete?'Данные неполные · ':offline?'Офлайн · ':fallback?'Сохранённая копия · ':'')+text+' ⓘ';
  const theme=document.getElementById('themeToggleBtn');
  theme.textContent=`Тема: ${{dark:'тёмная',light:'светлая',system:'как на устройстве'}[themeMode]}`;
}
const simpleApplyTheme=applyTheme;
applyTheme=function(){simpleApplyTheme();const button=document.getElementById('themeToggleBtn');button.textContent=`Тема: ${{dark:'тёмная',light:'светлая',system:'как на устройстве'}[themeMode]}`;};
document.addEventListener('DOMContentLoaded',()=>{
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(themeMode==='system')applyTheme();});
  document.getElementById('debugTools').hidden=new URLSearchParams(location.search).get('debug')!=='1';
  for(const overlay of document.querySelectorAll('.simple-overlay'))overlay.addEventListener('click',event=>{if(event.target===overlay)closeSimpleDialog(overlay.id);});
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape')document.querySelectorAll('.simple-overlay:not(.hidden)').forEach(dialog=>closeSimpleDialog(dialog.id));
    if(event.key==='Tab'){
      const dialog=document.querySelector('.simple-overlay:not(.hidden)');
      if(!dialog)return;
      const items=[...dialog.querySelectorAll('button,input,select,textarea,a[href],summary')].filter(item=>!item.disabled && item.getClientRects().length);
      const first=items[0],last=items.at(-1);
      if(event.shiftKey && document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey && document.activeElement===last){event.preventDefault();first?.focus();}
    }
  });
  for(const id of ['btnViewDay','btnViewWeek'])document.getElementById(id).addEventListener('click',()=>closeSimpleDialog('moreMenuModal'));
});
