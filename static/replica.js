// The approved compact interface reuses the real schedules, ownership and dialog services.
let replicaSelectedTeacher=null,replicaTeacherFilter='',replicaTeacherLimit=40;
const replicaOriginalDay=renderCompactDay;
const replicaOriginalState=applyPairVisualState;
const replicaOriginalCompact=updateCompactUI;
const replicaOriginalHero=updateCampusHero;
const replicaOriginalRooms=renderRoomsModalList;
let replicaSelectedBuilding='';
let replicaRoomLessonChoices=[];
let replicaNoteOrigin=null;
const replicaOriginalSaveNote=saveCurrentNote,replicaOriginalDeleteNote=deleteCurrentNote;
function restoreReplicaNoteFocus(origin){if(origin)document.querySelector(`[data-${origin.empty?'empty':'pair'}-index="${origin.index}"]`)?.focus({preventScroll:true});}
saveCurrentNote=function(){const origin=replicaNoteOrigin;replicaOriginalSaveNote();if(document.getElementById('noteModal').classList.contains('hidden'))restoreReplicaNoteFocus(origin);};
deleteCurrentNote=function(){const origin=replicaNoteOrigin;replicaOriginalDeleteNote();restoreReplicaNoteFocus(origin);};

function replicaTheme(code){return {practice:'practice',lab:'lab',lecture:'lecture',sport:'practice',exam:'lecture',test:'lecture'}[code] || 'neutral';}
function cycleReplicaSubgroup(){
  if(appMode==='teacher'){openReplicaTeachers(savedState.teacherKey);return;}
  const current=activeSubgroup();setSubgroupFilter(current==='all'?'1':current==='1'?'2':'all');
}
function updateReplicaHeader(){
  const subgroup=document.getElementById('replicaSubgroup'),parity=document.getElementById('replicaParity');
  if(!subgroup || !parity)return;
  subgroup.textContent=appMode==='teacher'?'Преп.':activeSubgroup()==='all'?'Все п/г':activeSubgroup()+' п/г';
  subgroup.setAttribute('aria-label',appMode==='teacher'?'Профиль выбранного преподавателя':'Подгруппа: '+subgroup.textContent+'. Переключить');
  parity.textContent=selectedWeek===1?'Нечётная':'Чётная';parity.setAttribute('aria-label',`${selectedWeek===1?'I':'II'} неделя. Переключить неделю`);
  const dated=hasDatedSchedule(currentSchedule) || viewMode==='dates' || scheduleTab==='session';parity.disabled=dated;
  const notice=document.getElementById('replicaViewNotice');
  if((viewMode!=='day' || scheduleTab==='session') && !notice){
    const button=document.createElement('button');button.id='replicaViewNotice';button.className='replica-return';button.textContent='К расписанию дня';button.onclick=()=>{scheduleTab='semester';setViewMode('day');};document.getElementById('dayTabs').before(button);
  }else if(viewMode==='day' && scheduleTab!=='session')notice?.remove();
  let badge=document.getElementById('replicaTestBadge');if(simOverride && !badge){badge=document.createElement('span');badge.id='replicaTestBadge';badge.textContent='Тест времени';document.getElementById('daySourceStatus').append(badge);}if(!simOverride)badge?.remove();
}
updateCompactUI=function(){replicaOriginalCompact();updateReplicaHeader();};
updateCampusHero=function(){replicaOriginalHero();updateReplicaHeader();};
applyPairVisualState=function(card,state){
  replicaOriginalState(card,state);
  const label=card.querySelector('.replica-current');if(label)label.hidden=state?.kind!=='current';
  const check=card.querySelector('.replica-past-check');if(check)check.hidden=state?.kind!=='past';
  const fill=card.querySelector('[data-pair-progress]>.progress-bar-fill');
  if(fill){fill.style.transform='none';fill.style.width=(state?.progress || 0)+'%';}
};
function replicaCardNote(pairIndex,lessonIndex=0){
  const pair=currentSchedule?.weeks?.[selectedWeek]?.[selectedDayKey]?.pairs?.[pairIndex],lesson=pair?.lessons?.[lessonIndex];if(!lesson)return;
  openNoteModal(makeNoteKey(lesson.subject,pair.number),displaySubject(lesson));
  renderReplicaNoteContext(pair,lesson,pairIndex,lessonIndex);
  replicaNoteOrigin={index:pairIndex,empty:false};
}
function renderReplicaNoteContext(pair,lesson,pairIndex,lessonIndex){
  const context=document.getElementById('replicaNoteContext');
  context.innerHTML=lesson?`<div class="replica-note-slot">${pair.number} пара · ${escapeHTML(pair.start)}–${escapeHTML(pair.end)}</div><div class="replica-note-actions">${lesson.room && !isOnlineLesson(lesson)?`<button onclick="compactLessonAction('room',${pairIndex},${lessonIndex})">${escapeHTML(lesson.room)} ${uiIcon('arrowUpRight')}</button>`:''}${lesson.teacher_key?`<button onclick="openReplicaTeachersFromLesson(${pairIndex},${lessonIndex})">${escapeHTML(lesson.teacher || 'Преподаватель')}</button>`:''}</div>${lesson.parse_warning?`<p class="campus-warning">${escapeHTML(lesson.parse_warning)}</p><p class="replica-source-raw">${escapeHTML(lesson.raw)}</p>`:''}${renderLessonMeta(lesson,pair.number)}${lesson.room_note || lesson.teacher_note?`<p class="replica-source-raw">Пометки источника: ${escapeHTML([lesson.room_note,lesson.teacher_note].filter(Boolean).join('; '))}</p>`:''}`:'';
  const tags=lesson?['Сдать лабу','Контрольная работа','Принести отчёт','Взять ноутбук']:['Сходить на обед','Зайти в деканат','Библиотека','Повторить билеты'];
  const box=document.getElementById('replicaNoteTags');box.replaceChildren();
  for(const text of tags){const button=document.createElement('button');button.textContent='+ '+text;button.onclick=()=>{const input=document.getElementById('noteTextarea');input.value=[input.value.trim(),text].filter(Boolean).join(' · ');input.focus();};box.append(button);}
}
function replicaEmptyNote(index){
  const pair=currentSchedule?.weeks?.[selectedWeek]?.[selectedDayKey]?.pairs?.[index];if(!pair)return;
  openNoteModal(makeNoteKey('__empty_slot__',pair.number),`Окно · ${pair.number} пара`);renderReplicaNoteContext(pair,null,index,0);
  document.getElementById('replicaNoteContext').textContent=`${pair.number} пара · ${pair.start}–${pair.end}`;
  replicaNoteOrigin={index,empty:true};
}
function openReplicaTeachersFromLesson(pairIndex,lessonIndex){
  const lesson=currentSchedule?.weeks?.[selectedWeek]?.[selectedDayKey]?.pairs?.[pairIndex]?.lessons?.[lessonIndex];if(lesson?.teacher_key)openReplicaTeachers(lesson.teacher_key,lesson.teacher_caf_id || '');
}
function replicaRoomButton(lesson,pairIndex,lessonIndex){
  const label=isOnlineLesson(lesson)?'Онлайн':lesson.room;if(!label)return null;
  const node=document.createElement(isOnlineLesson(lesson)?'span':'button');node.className='lesson-room replica-room droplet-'+({practice:'indigo',lab:'amber',lecture:'red'}[replicaTheme(lesson.type_code)] || 'frosted');node.textContent=label;
  if(node.tagName==='BUTTON'){node.setAttribute('aria-label','Аудитория '+label);node.onclick=event=>{event.stopPropagation();event.preventDefault();compactLessonAction('room',pairIndex,lessonIndex);};}
  return node;
}
function replicaEmptyHTML(pair,index,day){
  const active=activeSubgroup(),hidden=(pair.lessons || []).filter(lesson=>!matchesSubgroup(lesson,active));
  const other=currentSchedule.weeks?.[selectedWeek===1?2:1]?.[selectedDayKey]?.pairs?.find(item=>item.number===pair.number);
  let reason='Свободно · нет занятий',badge='';
  if(hidden.length){reason=`Свободно у ${active} п/г · у другой подгруппы: `+hidden.map(lesson=>[displaySubject(lesson),lesson.room].filter(Boolean).join(' · ')).join(' / ');if(hidden[0].room)badge=`<button class="replica-window-room" onclick="event.stopPropagation();openRoomsModal(${escapeHTML(JSON.stringify(hidden[0].room))})">${escapeHTML(hidden[0].room)}</button>`;}
  else if(other && filterLessons(other.lessons).length)reason=`Только на ${selectedWeek===1?'II':'I'} неделе: `+filterLessons(other.lessons).map(displaySubject).join(' / ');
  else{
    const before=day.pairs.slice(0,index).filter(item=>filterLessons(item.lessons).length).at(-1),after=day.pairs.slice(index+1).find(item=>filterLessons(item.lessons).length);
    const a=before && singleBuilding({...before,lessons:filterLessons(before.lessons)}),b=after && singleBuilding({...after,lessons:filterLessons(after.lessons)});
    if(a && b && a!==b)badge=`<span class="replica-transition">${escapeHTML(a)} → ${escapeHTML(b)}</span>`;
  }
  const note=getNotesMap()[makeNoteKey('__empty_slot__',pair.number)];
  return `<article class="empty-slot-card" data-empty-index="${index}" tabindex="0" role="group" aria-label="${pair.number} пара: окно, добавить заметку" onclick="if(!event.target.closest('button,a'))replicaEmptyNote(${index})" onkeydown="if(event.target===this && (event.key==='Enter'||event.key===' ')){event.preventDefault();replicaEmptyNote(${index})}"><div class="replica-window-top"><span>${pair.number} пара · ${escapeHTML(pair.start)}–${escapeHTML(pair.end)}</span>${badge}</div><p>${escapeHTML(reason)}</p>${note?`<p class="replica-note-preview">${uiIcon('note')}${escapeHTML(note)}</p>`:''}</article>`;
}
renderCompactDay=function(container){
  replicaOriginalDay(container);
  const day=currentSchedule?.weeks?.[selectedWeek]?.[selectedDayKey];if(!day || day.session_date)return;
  const notes=getNotesMap();
  for(const card of container.querySelectorAll('article.schedule-pair')){
    const index=Number(card.dataset.pairIndex),pair=day.pairs[index];if(!pair)continue;
    const theme=replicaTheme(card.dataset.type);card.classList.add('type-'+theme);
    const time=card.querySelector('.pair-time');
    time?.querySelector('.pair-number')?.classList.add('glass-tag-'+theme);
    card.querySelector('.progress-bar-fill')?.classList.add('neon-progress-bar');
    time?.append(Object.assign(document.createElement('span'),{className:'replica-current',textContent:'ИДЁТ СЕЙЧАС',hidden:true}));
    const past=document.createElement('span');past.className='replica-past-check';past.innerHTML=uiIcon('check');past.hidden=true;past.setAttribute('aria-label','Пара завершена');time?.append(past);
    const visible=filterLessons(pair.lessons);
    for(const oldDetail of card.querySelectorAll('.lesson-detail')){
      // Card actions are separate controls, not buttons nested in a native summary button.
      const detail=document.createElement('section');for(const attribute of oldDetail.attributes)detail.setAttribute(attribute.name,attribute.value);
      const oldSummary=oldDetail.querySelector('summary'),summary=document.createElement('div');summary.className=oldSummary.className;
      while(oldSummary.firstChild)summary.append(oldSummary.firstChild);oldSummary.replaceWith(summary);
      while(oldDetail.firstChild)detail.append(oldDetail.firstChild);for(const child of detail.children)if(child!==summary)child.hidden=true;oldDetail.replaceWith(detail);
      const lesson=visible.shift();if(!lesson)continue;const lessonIndex=pair.lessons.indexOf(lesson);
      const room=replicaRoomButton(lesson,index,lessonIndex);detail.querySelector('.lesson-room')?.remove();
      if(room){if(card.dataset.single==='true')time?.append(room);else detail.querySelector('.lesson-title-row')?.append(room);}
      const person=detail.querySelector('.lesson-person');
      if(person && appMode==='student' && lesson.teacher_key){const button=document.createElement('button');button.className='lesson-person replica-teacher-link';button.textContent=person.textContent;button.onclick=event=>{event.preventDefault();event.stopPropagation();openReplicaTeachers(lesson.teacher_key,lesson.teacher_caf_id || '');};person.replaceWith(button);}
      const type=replicaTheme(lesson.type_code);detail.querySelector('.lesson-kind')?.classList.add('glass-tag-'+type);
      detail.querySelector('.detail-chevron')?.remove();
      summary.onclick=event=>{if(event.target.closest('button,a'))return;event.preventDefault();event.stopPropagation();replicaCardNote(index,lessonIndex);};
      const note=notes[makeNoteKey(lesson.subject,pair.number)];if(note){const preview=document.createElement('p');preview.className='replica-note-preview';preview.textContent=note;summary.append(preview);}
    }
    card.tabIndex=0;card.setAttribute('role','group');card.setAttribute('aria-label',`${pair.number} пара · ${pair.start}. Открыть заметку`);
    card.onclick=event=>{if(!event.target.closest('button,a,.lesson-summary,details'))replicaCardNote(index,pair.lessons.indexOf(filterLessons(pair.lessons)[0]));};
    card.onkeydown=event=>{if(event.target===card && ['Enter',' '].includes(event.key)){event.preventDefault();replicaCardNote(index,pair.lessons.indexOf(filterLessons(pair.lessons)[0]));}};
  }
  // Render each real source slot, including slots hidden by the selected subgroup.
  for(const [index,pair] of (day.pairs || []).entries()){
    if(filterLessons(pair.lessons).length)continue;
    const template=document.createElement('template');template.innerHTML=replicaEmptyHTML(pair,index,day);const empty=template.content.firstElementChild;
    const next=[...container.children].find(node=>Number(node.dataset.pairIndex)>index || node.dataset.onlinePairIndices && Number(node.dataset.onlinePairIndices.split(',')[0])>index);
    if(next)container.insertBefore(empty,next);else container.append(empty);
  }
  bindReplicaGlare(container);updateCurrentCards(getUlanUdeNow());
};
function bindReplicaGlare(root){
  for(const card of root.querySelectorAll('.obsidian-card')){if(card.dataset.glareBound)continue;card.dataset.glareBound='true';card.addEventListener('pointermove',event=>{if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;const rect=card.getBoundingClientRect();card.style.setProperty('--glare-x',(100*(event.clientX-rect.left)/rect.width).toFixed(1)+'%');card.style.setProperty('--glare-y',(100*(event.clientY-rect.top)/rect.height).toFixed(1)+'%');});card.addEventListener('pointerleave',()=>{card.style.removeProperty('--glare-x');card.style.removeProperty('--glare-y');});}
}

function replicaTeacherName(teacher){return teacher.profile?.full_name || teacher.profile?.short_name || teacher.teacher_key;}
async function openReplicaTeachers(key='',caf=''){
  let modal=document.getElementById('teacherExplorerModal');
  if(!modal){modal=document.createElement('div');modal.id='teacherExplorerModal';modal.className='simple-overlay hidden';modal.innerHTML=`<div class="simple-sheet"><div class="replica-sheet-heading"><h2>Поиск преподавателя</h2><button aria-label="Закрыть преподавателей" onclick="closeSimpleDialog('teacherExplorerModal')">${uiIcon('close')}</button></div><input id="replicaTeacherQuery" type="search" aria-label="Поиск преподавателей" placeholder="Фамилия, предмет или кафедра" oninput="replicaTeacherLimit=40;renderReplicaTeachers()"><div id="replicaTeacherCafs" class="replica-chips"></div><div class="replica-sheet-scroll"><section id="replicaTeacherPreview"></section><div id="replicaTeacherResults"></div></div></div>`;document.body.append(modal);}
  if(key){replicaSelectedTeacher=key;replicaTeacherFilter=caf;}
  openSimpleDialog('teacherExplorerModal');document.getElementById('replicaTeacherQuery').value='';document.getElementById('replicaTeacherQuery').focus();
  document.getElementById('replicaTeacherResults').textContent='Загрузка преподавателей…';
  if(!allTeachersDirectory.length)await loadDepartmentsAndTeachers();renderReplicaTeachers();
}
function replicaPreviewTeacher(index){replicaSelectedTeacher=allTeachersDirectory[index]?.teacher_key || '';renderReplicaTeachers();document.getElementById('replicaTeacherPreview').scrollIntoView({block:'nearest'});}
function replicaCafFilter(value){replicaTeacherFilter=value;replicaTeacherLimit=40;renderReplicaTeachers();}
function replicaTeacherFull(){
  const teacher=allTeachersDirectory.find(item=>item.teacher_key===replicaSelectedTeacher);if(!teacher)return;
  closeSimpleDialog('teacherExplorerModal');closeSearchModal();loadTeacherSchedule(teacher.teacher_key,teacher.caf_id || '');
}
function replicaTeacherRoom(pairIndex,lessonIndex){const teacher=allTeachersDirectory.find(item=>item.teacher_key===replicaSelectedTeacher),lesson=teacher?.weeks?.[selectedWeek]?.[selectedDayKey]?.pairs?.[pairIndex]?.lessons?.[lessonIndex];if(lesson?.room)openRoomsModal(lesson.room);}
function renderReplicaTeachers(){
  if(!document.getElementById('replicaTeacherResults'))return;
  const query=document.getElementById('replicaTeacherQuery').value;
  const selected=allTeachersDirectory.find(item=>item.teacher_key===replicaSelectedTeacher);
  const cafs=[...new Set(allTeachersDirectory.flatMap(item=>item.caf_ids || [item.caf_id]).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'ru',{numeric:true}));
  const chips=document.getElementById('replicaTeacherCafs'),focusedCaf=chips.contains(document.activeElement)?document.activeElement.dataset.caf:null;chips.replaceChildren();
  const departments=departmentsHierarchy.flatMap(institute=>institute.departments || []);
  for(const caf of ['',...cafs]){const button=document.createElement('button');button.dataset.caf=caf;button.textContent=caf?(departments.find(department=>department.caf_id===caf)?.name || `Кафедра ${caf.replace(/^Caf/i,'')}`):'Все кафедры';button.setAttribute('aria-pressed',String(replicaTeacherFilter===caf));button.onclick=()=>replicaCafFilter(caf);chips.append(button);if(focusedCaf===caf)button.focus();}
  const rows=allTeachersDirectory.filter(item=>teacherMatches(item,query,replicaTeacherFilter));
  const box=document.getElementById('replicaTeacherResults');box.replaceChildren();
  for(const teacher of rows.slice(0,replicaTeacherLimit)){const button=document.createElement('button');button.className='replica-directory-row';button.setAttribute('aria-pressed',String(teacher===selected));const title=document.createElement('strong'),department=document.createElement('span');title.textContent=teacher.profile?.short_name || teacher.teacher_key;department.textContent=teacher.profile?.department || (teacher.caf_ids || [teacher.caf_id]).filter(Boolean).join(' · ');button.append(title,department);button.onclick=()=>replicaPreviewTeacher(allTeachersDirectory.indexOf(teacher));box.append(button);}
  if(!rows.length){const p=document.createElement('p');p.textContent=teacherDirectoryError || 'Преподаватели не найдены. Измените поиск или кафедру.';box.append(p);}
  if(rows.length>replicaTeacherLimit){const more=document.createElement('button');more.className='replica-more-results';more.textContent=`Показать ещё · всего ${rows.length}`;more.onclick=()=>{replicaTeacherLimit+=40;renderReplicaTeachers();};box.append(more);}
  renderReplicaTeacherPreview(selected);
}
function renderReplicaTeacherPreview(selected=allTeachersDirectory.find(item=>item.teacher_key===replicaSelectedTeacher)){
  const preview=document.getElementById('replicaTeacherPreview');if(!preview)return;if(!selected){preview.replaceChildren();return;}
  const pairs=selected.weeks?.[selectedWeek]?.[selectedDayKey]?.pairs || [],now=getUlanUdeNow(),today=DAY_KEYS[(now.getDay()+6)%7],minutes=now.getHours()*60+now.getMinutes();
  const current=selectedWeek===getWeekNum(now) && selectedDayKey===today?pairs.find(pair=>minutes>=timeToMinutes(pair.start) && minutes<timeToMinutes(pair.end) && pair.lessons?.length):null;
  const title=replicaTeacherName(selected),profile=selected.profile || {};
  preview.innerHTML=`<div class="replica-preview-card obsidian-card"><h3>${escapeHTML(title)}</h3>${profile.short_name && profile.short_name!==title?`<p>${escapeHTML(profile.short_name)}</p>`:''}<p>${escapeHTML([profile.degree,profile.department].filter(Boolean).join(' · '))}</p>${selected.identity_ambiguous?'<p class="campus-warning">Возможны данные нескольких преподавателей. Сверьте кафедру с источником.</p>':''}<p class="replica-preview-status">${current?'Ведёт пару сейчас · до '+escapeHTML(current.end):selectedDayKey===today && selectedWeek===getWeekNum(now)?'Сейчас нет известных занятий':'Расписание на выбранный день'}</p><div class="replica-preview-timeline">${pairs.map((pair,pairIndex)=>`<div><span>${pair.number} пара · ${escapeHTML(pair.start)}</span>${(pair.lessons || []).map((lesson,lessonIndex)=>`<p><span class="glass-tag-${replicaTheme(lesson.type_code)}">${escapeHTML(lesson.type || 'Занятие')}</span> ${escapeHTML(displaySubject(lesson))}${lesson.groups?' · '+escapeHTML(lesson.groups):''}${lesson.room?`<button class="replica-mini-room" onclick="replicaTeacherRoom(${pairIndex},${lessonIndex})">${escapeHTML(lesson.room)}</button>`:''}</p>`).join('') || '<p>Нет занятий</p>'}</div>`).join('')}</div><button class="replica-full-schedule" onclick="replicaTeacherFull()">Открыть полное расписание →</button></div>`;
  bindReplicaGlare(preview);
}

function replicaRoomRecords(lessons){
  const records=new Map();
  for(const lesson of lessons){
    const key=JSON.stringify(Object.keys(lesson).filter(key=>key!=='groups').sort().map(key=>[key,lesson[key]]));
    if(!records.has(key))records.set(key,{...lesson,groupLabels:new Set()});
    const labels=Array.isArray(lesson.groups)?lesson.groups:[lesson.groups];
    for(const label of labels)if(label)records.get(key).groupLabels.add(String(label));
  }
  return [...records.values()].map(({groupLabels,...lesson})=>({...lesson,groups:[...groupLabels].join(', ')}));
}

renderRoomsModalList=function(){
  replicaOriginalRooms();
  const modal=document.getElementById('roomsModal');if(!modal || !roomDirectory)return;
  let chips=document.getElementById('replicaRoomBuildings');if(!chips){chips=document.createElement('div');chips.id='replicaRoomBuildings';chips.className='replica-chips';document.getElementById('roomSearchInput').after(chips);}
  const buildings=[...new Set(roomDirectory.rooms.map(room=>decodeEsstuRoom(room.room)?.building).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'ru',{numeric:true}));chips.replaceChildren();
  for(const building of ['',...buildings]){const button=document.createElement('button');button.textContent=building || 'Все корпуса';button.setAttribute('aria-pressed',String(replicaSelectedBuilding===building));button.onclick=()=>{replicaSelectedBuilding=building;renderRoomsModalList();};chips.append(button);}
  for(const card of modal.querySelectorAll('.room-card'))card.hidden=!!replicaSelectedBuilding && decodeEsstuRoom(card.dataset.room)?.building!==replicaSelectedBuilding;
  for(const heading of modal.querySelectorAll('.room-group-title'))heading.hidden=!!replicaSelectedBuilding && !heading.textContent.includes(replicaSelectedBuilding);
  let selected=document.getElementById('replicaRoomPreview');if(!selected){selected=document.createElement('section');selected.id='replicaRoomPreview';document.getElementById('roomsListContainer').before(selected);}
  const query=normSearch(document.getElementById('roomSearchInput').value),room=roomDirectory.rooms.find(item=>normSearch(item.room)===query);
  if(!room){selected.replaceChildren();replicaRoomLessonChoices=[];return;}
  const context=roomContext(),data=roomOccupancy(room,context),building=decodeEsstuRoom(room.room)?.building;
  replicaRoomLessonChoices=replicaRoomRecords(data.lessons);
  selected.innerHTML=`<div class="replica-preview-card obsidian-card"><h3>${escapeHTML(room.room)}${building?' · '+escapeHTML(building):''}</h3><p>Корпус по обозначению аудитории. Занятость — только по известным расписаниям.</p><div class="replica-preview-timeline">${ROOM_BELLS.map((start,index)=>{const rows=replicaRoomLessonChoices.map((lesson,choice)=>({lesson,choice})).filter(({lesson})=>Number(lesson.pair)===index+1);return `<div><span>${index+1} пара · ${start}</span>${rows.map(({lesson,choice})=>`<p>${escapeHTML(lesson.subject || 'Предмет не указан')}${lesson.teacher?` · <button class="replica-inline-link" onclick="replicaRoomTeacher(${choice})">${escapeHTML(lesson.teacher)}</button>`:''}${lesson.type?' · '+escapeHTML(lesson.type):''}${lesson.groups?'<br><span class="replica-room-groups">Группы: '+escapeHTML(lesson.groups)+'</span>':''}</p>`).join('') || '<p>Нет известных занятий</p>'}</div>`;}).join('')}</div>${building?`<a class="replica-map-link" href="https://2gis.ru/ulanude/search/${encodeURIComponent('ВСГУТУ '+building)}" target="_blank" rel="noopener">Найти корпус в 2ГИС ${uiIcon('arrowUpRight')}</a>`:''}</div>`;
  bindReplicaGlare(selected);
};
async function replicaRoomTeacher(index){const name=replicaRoomLessonChoices[index]?.teacher;if(!name)return;if(!allTeachersDirectory.length)await loadDepartmentsAndTeachers();const teacher=allTeachersDirectory.find(item=>normSearch(item.teacher_key)===normSearch(name) || normSearch(item.profile?.short_name)===normSearch(name));if(teacher)openReplicaTeachers(teacher.teacher_key,teacher.caf_id || '');else{await openReplicaTeachers();document.getElementById('replicaTeacherQuery').value=name;renderReplicaTeachers();}}

document.addEventListener('DOMContentLoaded',()=>{
  // Tools and optional week controls remain available without occupying the first screen.
  const tools=document.querySelector('#moreMenuModal .simple-sheet');
  const week=document.getElementById('weekControls');tools?.append(week);
  const overview=document.querySelector('.campus-overview');if(overview)tools?.append(overview);
  const note=document.querySelector('#noteModal .simple-sheet'),input=document.getElementById('noteTextarea');
  const context=document.createElement('div');context.id='replicaNoteContext';input.before(context);
  const tags=document.createElement('div');tags.id='replicaNoteTags';tags.className='replica-chips';input.after(tags);
  // A direct notes launcher outside the compact day can still use the existing editor.
  const originalNote=openNoteModal;openNoteModal=function(key,title){replicaNoteOrigin=null;originalNote(key,title);renderReplicaNoteContext(null,null,0,0);};
  updateReplicaHeader();
  setInterval(()=>{if(document.getElementById('teacherExplorerModal') && !document.getElementById('teacherExplorerModal').classList.contains('hidden'))renderReplicaTeacherPreview();},15000);
});
document.addEventListener('keydown',event=>{
  if(event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey || event.target.closest('input,textarea,select,[contenteditable="true"]') || modalStack.length)return;
  if(event.key==='/'){event.preventDefault();openRoomsModal();}
  if(['t','T','е','Е'].includes(event.key)){event.preventDefault();openReplicaTeachers();}
});
