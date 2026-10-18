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
    const past=meta.date && !meta.isToday && meta.date<getUlanUdeNow();
    const dayPairs=(week[day.key]?.pairs || []).filter(pair=>filterLessons(pair.lessons).length);
    const countLabel=currentSchedule?.is_incomplete?'нет данных':count?count+' '+pairWord(count):'нет пар';
    const dots=dayPairs.map(pair=>{const types=[...new Set(filterLessons(pair.lessons).map(lesson=>lesson.parse_warning?'review':lesson.type_code || 'other'))];return `<i data-type="${escapeHTML(types.length===1?types[0]:'mixed')}"></i>`;}).join('');
    return `<button onclick="selectDay('${day.key}')" aria-label="${escapeHTML(day.full+', '+meta.shortLabel+' · '+countLabel+(meta.isToday?' · Сегодня':''))}" aria-pressed="${active}" data-past="${!!past}" ${meta.isToday?'aria-current="date"':''} class="calendar-day"><span class="calendar-heading"><span class="calendar-weekday">${day.short}</span><span class="calendar-date">${escapeHTML(meta.date?String(meta.date.getDate()):meta.shortLabel)}</span></span><span class="calendar-dots" aria-hidden="true">${dots || '<i></i>'}</span><span class="calendar-count sr-only ${count>0?'has-lessons':''}">${countLabel}</span></button>`;
  }).join('');
  const day=DAY_NAMES.find(day=>day.key===selectedDayKey),meta=dayDateMeta(week[selectedDayKey],selectedDayKey,dates);
  document.getElementById('selectedDaySummary').textContent=day?`${day.full}, ${meta.shortLabel}${meta.isToday?' · Сегодня':''}`:'';
}
const pairPluralRules=new Intl.PluralRules('ru');
function pairWord(count) {return {one:'пара',few:'пары',many:'пар',other:'пар'}[pairPluralRules.select(count)];}
function durationText(minutes) {
  const whole=Math.max(0,Math.ceil(minutes)),hours=Math.floor(whole/60),rest=whole%60;
  return hours?`${hours} ч${rest?' '+rest+' мин':''}`:`${rest} мин`;
}
function isOnlineLesson(lesson) {
  return !!decodeEsstuRoom(lesson.room)?.online || (!lesson.room && /онлайн[-\s]?курс|online course/i.test(lesson.subject || ''));
}
function displaySubject(lesson) {
  if(lesson.parse_warning && /^(?:Несколько занятий|Не удалось разобрать занятие)/.test(lesson.subject || '') && lesson.raw){
    const raw=String(lesson.raw).replace(/^(?:лек\.|пр\.|лаб\.|сем\.|экз\.|зач\.|конс\.)\s*/i,'');
    const boundary=raw.search(/[А-ЯЁ][А-ЯЁа-яё-]+\s+[А-ЯЁ]\.(?:\s*[А-ЯЁ]\.)?|(?:^|\s)а\.\s*\d/);
    let title=(boundary>=0?raw.slice(0,boundary):raw).trim().replace(/[-–—\s]+$/,'');
    const languages=title.match(/Иностранный язык(?:\s+\d+)?\s*\([^)]*\)/g);
    if(languages && languages.join(' ')===title)title=[...new Set(languages)].join(' / ');
    return title || 'Предмет не указан в источнике';
  }
  return isOnlineLesson(lesson)?String(lesson.subject || '').replace(/\s*\((?:онлайн[-\s]?курс|online course)\)/ig,'').trim() || lesson.subject:lesson.subject;
}
function lessonRoomLabel(lesson) {return isOnlineLesson(lesson)?'Онлайн':lesson.room?'ауд. '+lesson.room:'';}
function groupOnlinePairs(pairs) {
  const groups=[];
  const key=pair=>pair?.lessons?.length===1 && isOnlineLesson(pair.lessons[0]) && !pair.lessons[0].parse_warning && !pair.lessons[0].needs_review
    ? JSON.stringify(['subject','type_code','type','teacher_key','teacher','room','groups','tag','source_file'].map(field=>pair.lessons[0][field] || '')):null;
  for(let index=0;index<pairs.length;index++){
    const previous=groups.at(-1),signature=key(pairs[index]),last=previous && pairs[previous.end];
    const gap=last?timeToMinutes(pairs[index].start)-timeToMinutes(last.end):null;
    if(previous && signature && signature===previous.signature && Number(pairs[index].number)===Number(last.number)+1 && gap>=0 && gap<=30)previous.end=index;
    else groups.push({start:index,end:index,signature});
  }
  return groups;
}
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
  document.getElementById('campusDate').textContent=now.toLocaleDateString('ru-RU',{weekday:'short',day:'numeric',month:'short'}).replace(/\.$/,'')+(simOverride?' · Тест':'');
  document.getElementById('campusDate').title=now.toLocaleDateString('ru-RU',{weekday:'long',day:'numeric',month:'long',year:'numeric'})+' · Улан-Удэ, UTC+8'+(simOverride?' · Тест времени':'');
  document.getElementById('weekBadge').textContent=week===1?'I неделя':'II неделя';
  document.getElementById('clockDisplay').textContent=now.toLocaleString('ru-RU')+' · Улан-Удэ'+(simOverride?' · ТЕСТ':'');
  const stamp=now.toDateString();
  if(stamp!==campusDayStamp){campusDayStamp=stamp;renderCalendarDays();if(currentSchedule && scheduleTab==='session')renderPairsList();}
  if(!currentSchedule || document.getElementById('pairsContainer').getAttribute('aria-busy')==='true')return;
  const state=heroState(currentSchedule,now),pair=state.pair;
  document.getElementById('liveHeroCard').dataset.state=state.kind;
  const label=document.getElementById('heroStatusLabel'),remaining=document.getElementById('heroRemainingTime'),lessons=document.getElementById('heroLessons'),next=document.getElementById('heroNextPairRow');
  document.getElementById('heroProgressWrap').classList.toggle('hidden',state.kind!=='current');
  next.classList.toggle('hidden',!state.next);
  remaining.classList.toggle('hidden',!pair);
  updateCurrentCards(now);
  if(!pair){
    label.textContent=state.kind==='finished'?'Занятия завершены':'Сегодня';remaining.textContent='';
    const upcoming=['finished','empty'].includes(state.kind)?nextStudyDay(currentSchedule,now):null;
    const first=upcoming?.pairs[0],rooms=first?[...new Set(first.lessons.map(lesson=>lesson.room).filter(Boolean))]:[];
    const html=`<p>${state.kind==='finished'?'Все пары на сегодня закончились':currentSchedule.is_incomplete?'Данные неполные — '+escapeHTML(scheduleIssueText(currentSchedule)):state.kind==='dated'?'Занятия по отдельным датам — проверьте расписание ниже':'На сегодня пар нет'}</p>${upcoming?`<button class="hero-upcoming" onclick="openUpcomingStudyDay()"><strong>${upcoming.offset===1?'Завтра':escapeHTML(upcoming.label)}: ${upcoming.pairs.length} ${pairWord(upcoming.pairs.length)}</strong><span>${escapeHTML(first.start)}${rooms.length?' · '+escapeHTML(rooms.map(room=>decodeEsstuRoom(room)?.online?'Онлайн':'ауд. '+room).join(', ')):''} ${uiIcon('arrowUpRight')}</span></button>`:''}`;
    if(lessons.dataset.content!==html){lessons.innerHTML=html;lessons.dataset.content=html;}
    return;
  }
  label.textContent=state.kind==='current'?`Сейчас · ${pair.number}-я пара`:'Следующая пара';
  remaining.textContent=state.kind==='current'?`до конца ${durationText(state.remaining)}`:`Сегодня в ${pair.start} · через ${durationText(state.remaining)}`;
  // Build only when the pair changes, so keyboard focus on room actions survives clock ticks.
  const html=pair.lessons.map((lesson,index)=>{
    const room=decodeEsstuRoom(lesson.room),subtitle=appMode==='student'?lesson.teacher:lesson.groups;
    return `<div class="hero-lesson ${index?'hero-parallel':''}"><p class="hero-lesson-meta">${escapeHTML(pair.start)}–${escapeHTML(pair.end)} · ${escapeHTML(lesson.type || 'Занятие')}${lesson.tag?' · '+escapeHTML(lesson.tag):''}</p><h3 class="hero-subject">${escapeHTML(displaySubject(lesson))}</h3><p class="hero-teacher">${escapeHTML(subtitle || '')}</p>${isOnlineLesson(lesson)?`<span class="online-badge">${uiIcon('link')} Онлайн</span>`:room?`<div class="hero-location"><button onclick="heroRoomAction(${index})" class="hero-room" aria-label="Аудитория ${escapeHTML(room.raw)}"><span>Аудитория</span><strong>${escapeHTML(room.raw)}</strong></button>${room.building?`<span class="hero-building" title="По обозначению аудитории">${escapeHTML(room.building)}<span aria-hidden="true">${uiIcon('arrowUpRight')}</span></span>`:''}</div>`:''}</div>`;
  }).join('');
  if(lessons.dataset.content!==html){lessons.innerHTML=html;lessons.dataset.content=html;}
  if(state.kind==='current'){
    document.getElementById('heroProgress').setAttribute('aria-valuenow',Math.round(state.progress));
    document.getElementById('heroProgressFill').style.transform=`scaleX(${state.progress/100})`;
  }
  if(state.next)next.textContent=`Далее в ${state.next.start} · через ${durationText(timeToMinutes(state.next.start)-now.getHours()*60-now.getMinutes()-now.getSeconds()/60)} · `+state.next.lessons.map(lesson=>`${displaySubject(lesson)}${lessonRoomLabel(lesson)?' · '+lessonRoomLabel(lesson):''}`).join(' / ');
}
function heroRoomAction(index) {const pair=heroState(currentSchedule,getUlanUdeNow()).pair;if(pair?.lessons[index]?.room)openRoomsModal(pair.lessons[index].room);}
function visualPairStates(now) {
  const day=currentSchedule?.weeks?.[selectedWeek]?.[selectedDayKey];
  const pairs=day?.pairs || [],minutes=now.getHours()*60+now.getMinutes()+now.getSeconds()/60;
  const date=day?.session_date?null:getWeekRangeDates(selectedWeek,now)[selectedDayKey]?.date;
  const sameDay=date?.toDateString()===now.toDateString();
  const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
  const next=sameDay?pairs.filter(pair=>filterLessons(pair.lessons).length && timeToMinutes(pair.start)>minutes).sort((a,b)=>timeToMinutes(a.start)-timeToMinutes(b.start))[0]:null;
  return pairs.map(pair=>{
    const start=timeToMinutes(pair.start),end=timeToMinutes(pair.end);
    const current=!!sameDay && minutes>=start && minutes<end;
    const kind=current?'current':pair===next?'next':date && (date<today || sameDay && minutes>=end)?'past':'upcoming';
    return {kind,remaining:current?Math.ceil(end-minutes):Math.ceil(start-minutes),progress:current?Math.min(100,Math.max(0,100*(minutes-start)/(end-start))):0};
  });
}
function applyPairVisualState(card,state) {
  const kind=state?.kind || 'upcoming',active=kind==='current';
  card.dataset.current=String(active);card.dataset.state=kind;
  for(const name of ['current','next','past'])card.classList.toggle('is-'+name,kind===name);
  if(card.dataset.pairIndex===undefined)return;
  card.querySelector('[data-current-label]')?.classList.toggle('hidden',!active);
  const status=card.querySelector('[data-pair-state]');
  if(status){
    status.hidden=!['current','next'].includes(kind);
    card.querySelector('[data-pair-state-name]').textContent=active?'Идёт сейчас':'Следующая пара';
    card.querySelector('[data-pair-countdown]').textContent=active?'ост. '+durationText(state.remaining):'через '+durationText(state.remaining);
  }
  const progress=card.querySelector('[data-pair-progress]');
  if(progress){progress.hidden=!active;progress.setAttribute('aria-valuenow',Math.round(state?.progress || 0));progress.firstElementChild.style.transform=`scaleX(${(state?.progress || 0)/100})`;}
}
function updateCurrentCards(now) {
  if(viewMode!=='day')return;
  const states=visualPairStates(now);
  for(const card of document.querySelectorAll('[data-pair-index]')){
    applyPairVisualState(card,states[Number(card.dataset.pairIndex)]);
  }
  for(const block of document.querySelectorAll('[data-online-pair-indices]')){
    const members=block.dataset.onlinePairIndices.split(',').map(index=>states[Number(index)]);
    const state=members.find(state=>state?.kind==='current') || members.find(state=>state?.kind==='next') || {kind:members.every(state=>state?.kind==='past')?'past':'upcoming'};
    applyPairVisualState(block,state);block.querySelector('[data-merged-current-label]').hidden=state.kind!=='current';
  }
}
function openSimpleDialog(id) { presentDialog(id); }
function closeSimpleDialog(id) { dismissDialog(id); }
function closeSearchModal() { closeSimpleDialog('searchModal'); }
function openSearchModal(mode = appMode) {
  searchMode=mode==='teacher'?'teacher':'student';
  openSimpleDialog('searchModal');
  const slot=document.getElementById('searchInputSlot');
  for(const id of ['groupSearchInput','teacherSearchInput']){const input=document.getElementById(id);slot.append(input);input.hidden=(id==='groupSearchInput')!==(searchMode==='student');}
  renderRecentSchedules();
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
      if(duration>0)gap=`<p class="lesson-break"><span>${escapeHTML(previous.end)}–${escapeHTML(pair.start)} · ${formatBreak(duration)}${before && after && before!==after ? ` · <span class="text-amber-700 dark:text-amber-300">Смена корпуса по расписанию: ${escapeHTML(before)} → ${escapeHTML(after)}</span>`:''}</span></p>`;
    }
    previous={...pair,lessons:visible};
    const lessons=pair.lessons.map((lesson,index)=>{
      if(!visible.includes(lesson))return '';
      const room=decodeEsstuRoom(lesson.room),note=notes[makeNoteKey(lesson.subject,pair.number)];
      const subtitle=appMode==='student'?lesson.teacher:lesson.groups;
      const warning=!!lesson.parse_warning || lesson.type==='Требуется сверка';
      return `<details class="lesson-detail ${warning?'lesson-warning ':''}${index?'lesson-parallel':''}" data-type="${escapeHTML(lesson.type_code)}">
        <summary class="lesson-summary">
          <div class="lesson-title-row"><span class="lesson-subject">${escapeHTML(displaySubject(lesson))}</span><span class="lesson-room">${isOnlineLesson(lesson)?uiIcon('link')+' ':''}${escapeHTML(lessonRoomLabel(lesson))}</span></div>
          <div class="lesson-meta"><span class="lesson-kind">${warning?uiIcon('warning'):lessonTypeIcon(lesson.type_code)}${escapeHTML(lesson.type || 'Занятие')}${lesson.tag ? ' · '+escapeHTML(lesson.tag):''}</span><span class="lesson-person">${escapeHTML(subtitle || (warning?'Откройте для сверки с источником':appMode==='student'?'Преподаватель не указан':'Группы не указаны'))}${note?' · '+uiIcon('note'):''}</span><span aria-hidden="true" class="detail-chevron">${uiIcon('chevron')}</span></div>
        </summary>
        <div class="pt-1 pb-2 space-y-2 text-xs"><p class="text-slate-500">${escapeHTML([lesson.type,lesson.tag].filter(Boolean).join(' · '))}</p>
          ${lesson.parse_warning?`<p class="text-amber-700 dark:text-amber-300">${escapeHTML(lesson.parse_warning)}</p><p class="text-slate-500 dark:text-slate-400 whitespace-pre-wrap">${escapeHTML(lesson.raw)}</p>`:''}
          ${room?`<p class="text-teal-600 dark:text-teal-300">${escapeHTML(room.location)}</p>`:''}
          ${lesson.room_note || lesson.teacher_note?`<p class="text-slate-500 dark:text-slate-400">Пометки источника: ${escapeHTML([lesson.room_note,lesson.teacher_note].filter(Boolean).join('; '))}</p>`:''}
          ${renderLessonMeta(lesson,pair.number)}
          ${note?`<p class="p-2 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-200 whitespace-pre-wrap">${escapeHTML(note)}</p>`:''}
          <div class="flex flex-wrap gap-2">
            ${lesson.room && !isOnlineLesson(lesson)?`<button onclick="compactLessonAction('room',${pairIndex},${index})" class="px-3 rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-300">Аудитория</button>`:''}
            ${appMode==='student' && lesson.teacher_key?`<button onclick="compactLessonAction('teacher',${pairIndex},${index})" class="px-3 rounded-xl bg-slate-100 dark:bg-slate-800">Преподаватель</button>`:''}
            <button onclick="compactLessonAction('note',${pairIndex},${index})" class="px-3 rounded-xl bg-slate-100 dark:bg-slate-800">${note?'Изменить заметку':'Добавить заметку'}</button>
          </div>
        </div></details>`;
    }).join('');
    const types=[...new Set(visible.map(lesson=>lesson.parse_warning?'review':lesson.type_code || 'other'))];
    const cardType=types.length===1?types[0]:'mixed';
    return `${gap}<article data-pair-index="${pairIndex}" data-current="${current}" data-type="${escapeHTML(cardType)}" data-single="${visible.length===1}" class="schedule-pair lesson-card obsidian-card">
      <div class="pair-state" data-pair-state hidden><span class="pair-state-name"><i class="pulse-dot" aria-hidden="true"></i><span data-pair-state-name></span></span><span class="pair-countdown" data-pair-countdown></span></div>
      <div class="pair-time"><div class="pair-start font-semibold text-xs">${escapeHTML(pair.start)}</div><div class="pair-end text-xs">${escapeHTML(pair.end)}</div><div class="pair-number text-xs">${pair.number} пара</div><span data-current-label class="sr-only ${current?'':'hidden'}">СЕЙЧАС</span></div><div class="pair-lessons">${lessons}</div><div class="pair-progress" data-pair-progress hidden role="progressbar" aria-label="Прошло времени пары ${escapeHTML(pair.number)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="progress-bar-fill"></div></div></article>`;
  });
  const pairs=day.pairs || [];
  const grouped=groupOnlinePairs(pairs).map(group=>{
    if(group.start===group.end || !rows[group.start])return rows[group.start];
    const first=pairs[group.start],last=pairs[group.end],lesson=first.lessons[0],count=group.end-group.start+1;
    const gap=rows[group.start].match(/^<p class="lesson-break">[\s\S]*?<\/p>/)?.[0] || '';
    const originals=rows.slice(group.start,group.end+1);originals[0]=originals[0].slice(gap.length);
    const indices=Array.from({length:count},(_,i)=>group.start+i).join(',');
    const active=isToday && pairs.slice(group.start,group.end+1).some(pair=>minutes>=timeToMinutes(pair.start) && minutes<timeToMinutes(pair.end));
    return `${gap}<details class="merged-online-block lesson-card" data-online-pair-indices="${indices}" data-current="${active}"><summary class="lesson-summary"><div class="merged-online-meta">${first.start}–${last.end} · ${count} ${pairWord(count)}<span data-merged-current-label ${active?'':'hidden'}>Сейчас</span></div><div class="lesson-title-row"><span class="lesson-subject">${escapeHTML(displaySubject(lesson))}</span><span class="lesson-room">${uiIcon('link')} Онлайн</span></div><div class="merged-online-bottom"><span>Раскрыть время каждой пары и заметки</span><span class="detail-chevron" aria-hidden="true">${uiIcon('chevron')}</span></div></summary><div class="merged-online-originals">${originals.join('')}</div></details>`;
  });
  container.innerHTML=grouped.join('') || renderEmptyStudyDay();
  updateCurrentCards(now);
}
function updateCompactUI() {
  if(!currentSchedule)return;
  document.getElementById('teacherIdentityWarning').hidden=!(appMode==='teacher' && currentSchedule.identity_ambiguous);
  document.getElementById('currentEntityBtnText').textContent=appMode==='student'?savedState.groupName:(currentSchedule.profile?.short_name || savedState.teacherKey);
  renderDaySource();
  document.querySelector('.campus-agenda').setAttribute('aria-label',viewMode==='week'?'Расписание на неделю':'Расписание на выбранный день');
  if(viewMode==='week')document.getElementById('selectedDaySummary').textContent=`Расписание на ${selectedWeek===1?'I':'II'} неделю`;
  for(const n of [1,2]){const button=document.getElementById('btnWeek'+n),current=getWeekNum(getUlanUdeNow())===n;button.setAttribute('aria-pressed',String(selectedWeek===n));button.dataset.currentWeek=String(current);button.setAttribute('aria-label',`${n===1?'I':'II'} неделя${current?', текущая':''}`);button.title=current?'Текущая календарная неделя':'Выбрать '+(n===1?'I':'II')+' неделю';if(current)button.setAttribute('aria-current','true');else button.removeAttribute('aria-current');}
  const theme=document.getElementById('themeToggleBtn');
  theme.textContent=`Тема: ${{dark:'тёмная',light:'светлая',system:'как на устройстве'}[themeMode]}`;
}
const simpleApplyTheme=applyTheme;
applyTheme=function(){simpleApplyTheme();document.querySelector('meta[name="theme-color"]').content=document.documentElement.classList.contains('dark')?'#000000':'#f3f5f5';const button=document.getElementById('themeToggleBtn');button.textContent=`Тема: ${{dark:'тёмная',light:'светлая',system:'как на устройстве'}[themeMode]}`;};
document.addEventListener('DOMContentLoaded',()=>{
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(themeMode==='system')applyTheme();});
  document.getElementById('debugTools').hidden=new URLSearchParams(location.search).get('debug')!=='1';
  for(const overlay of document.querySelectorAll('.simple-overlay'))overlay.addEventListener('click',event=>{if(event.target===overlay)closeSimpleDialog(overlay.id);});
  for(const id of ['btnViewDay','btnViewWeek'])document.getElementById(id).addEventListener('click',()=>closeSimpleDialog('moreMenuModal'));
});

function formatBreak(minutes){
  if(minutes<60)return `Перерыв ${minutes} мин`;
  return `Окно ${Math.floor(minutes/60)} ч${minutes%60?' '+minutes%60+' мин':''}`;
}
function lessonTypeIcon(code){
  return uiIcon({lecture:'book',practice:'pen',lab:'flask',sport:'activity',exam:'check',test:'check'}[code] || 'calendar');
}
function nextStudyDay(schedule=currentSchedule,origin=getWeekRangeDates(selectedWeek)[selectedDayKey]?.date){
  if(!schedule || schedule.is_incomplete || hasDatedSchedule(schedule))return null;
  if(!origin)return null;
  for(let offset=1;offset<=14;offset++){
    const date=new Date(origin);date.setDate(date.getDate()+offset);
    const day=DAY_KEYS[(date.getDay()+6)%7];if(!day)continue;
    const week=getWeekNum(date),data=schedule.weeks?.[week]?.[day];
    const pairs=(data?.pairs || []).map(pair=>({...pair,lessons:filterLessons(pair.lessons)})).filter(pair=>pair.lessons.length).sort((a,b)=>timeToMinutes(a.start)-timeToMinutes(b.start));
    if(data && !data.session_date && pairs.length)
      return {day,week,pairs,offset,label:date.toLocaleDateString('ru-RU',{weekday:'short',day:'numeric',month:'short'}).replace(/\.$/,'')};
  }
  return null;
}
function openUpcomingStudyDay(){const next=nextStudyDay(currentSchedule,getUlanUdeNow());if(next){selectedWeek=next.week;selectedDayKey=next.day;setViewMode('day');}}
function renderEmptyStudyDay(){
  const next=nextStudyDay();
  return `<div class="empty-state"><p class="font-semibold">В этот день занятий нет</p>${next?`<button class="next-study-day" onclick="openNextStudyDay()">Ближайший день с парами: ${escapeHTML(next.label)} ${uiIcon('arrowUpRight')}</button>`:'<p class="mt-2 text-sm text-slate-500">Выберите другой день</p>'}</div>`;
}
function openNextStudyDay(){const next=nextStudyDay();if(next){selectedWeek=next.week;selectedDayKey=next.day;setViewMode('day');}}
function moveCalendarDay(direction,keyboard=false){
  if(viewMode!=='day' || hasDatedSchedule(currentSchedule))return;
  const index=DAY_KEYS.indexOf(selectedDayKey),next=index+direction;
  if(index<0 || next<0 || next>=DAY_KEYS.length)return;
  selectDay(DAY_KEYS[next]);
  if(keyboard)document.querySelector('#dayTabs [aria-pressed="true"]')?.focus();
}
document.addEventListener('DOMContentLoaded',()=>{
  const tabs=document.getElementById('dayTabs');let gesture=null,suppressClickUntil=0;
  tabs.addEventListener('pointerdown',event=>{if(event.pointerType==='touch'){gesture={x:event.clientX,y:event.clientY};tabs.setPointerCapture(event.pointerId);}});
  tabs.addEventListener('pointercancel',()=>{gesture=null;});
  tabs.addEventListener('pointerup',event=>{
    if(!gesture)return;const dx=event.clientX-gesture.x,dy=event.clientY-gesture.y;gesture=null;
    if(Math.abs(dx)>55 && Math.abs(dx)>Math.abs(dy)*1.5){event.preventDefault();suppressClickUntil=Date.now()+350;moveCalendarDay(dx<0?1:-1);}
  });
  tabs.addEventListener('click',event=>{if(Date.now()<suppressClickUntil){event.preventDefault();event.stopImmediatePropagation();}},true);
  tabs.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();moveCalendarDay(event.key==='ArrowRight'?1:-1,true);}});
});

function recentSchedules(){try{const rows=JSON.parse(localStorage.getItem('esstu_recent_v1') || '[]');return Array.isArray(rows)?rows.filter(row=>row && ['student','teacher'].includes(row.type) && typeof row.label==='string').slice(0,6):[];}catch{return [];}}
function rememberRecentSchedule(){
  if(!currentSchedule || currentSchedule.is_incomplete)return;
  const entry=currentFavorite(),key=favoriteKey(entry);
  try{localStorage.setItem('esstu_recent_v1',JSON.stringify([entry,...recentSchedules().filter(row=>favoriteKey(row)!==key)].slice(0,6)));}catch(error){console.warn('Не удалось сохранить недавние расписания',error);}
}
function renderRecentSchedules(){
  const box=document.getElementById('recentSchedules');box.replaceChildren();
  for(const row of recentSchedules().filter(row=>row.type===searchMode)){
    const button=document.createElement('button');button.className='recent-schedule';button.textContent=row.label;
    button.onclick=()=>{closeSearchModal();if(row.type==='student')loadStudentSchedule(row.section,row.id,row.label);else loadTeacherSchedule(row.teacherKey,row.cafId);};box.append(button);
  }
  document.getElementById('recentSection').hidden=!box.children.length;
}

function scheduleIssueText(schedule){return schedule?.incomplete_reason || schedule?.parse_errors?.[0] || 'Расписание не удалось надёжно прочитать. Сверьте источник.';}
