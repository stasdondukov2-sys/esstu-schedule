let searchMode = 'student';
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
  const isToday=today===selectedDayKey && getWeekNum(now)===selectedWeek;
  const minutes=now.getHours()*60+now.getMinutes(),notes=getNotesMap();
  let previous=null;
  const rows=(day.pairs || []).map((pair,pairIndex)=>{
    if(!pair.lessons?.length)return '';
    const current=isToday && minutes>=timeToMinutes(pair.start) && minutes<timeToMinutes(pair.end);
    let gap='';
    if(previous){
      const duration=timeToMinutes(pair.start)-timeToMinutes(previous.end);
      const before=decodeEsstuRoom(previous.lessons[0]?.room)?.building,after=decodeEsstuRoom(pair.lessons[0]?.room)?.building;
      if(duration>0)gap=`<p class="pl-16 py-1 text-[11px] text-slate-400">Перерыв ${duration} мин${before && after && before!==after ? ` · ${escapeHTML(before)} → ${escapeHTML(after)}`:''}</p>`;
    }
    previous=pair;
    const lessons=pair.lessons.map((lesson,index)=>{
      const room=decodeEsstuRoom(lesson.room),note=notes[makeNoteKey(lesson.subject,pair.number)];
      const subtitle=appMode==='student'?lesson.teacher:lesson.groups;
      return `<details class="lesson-detail group py-1 ${index?'border-t border-slate-200 dark:border-slate-800 mt-2 pt-3':''}">
        <summary class="min-h-[60px] rounded-lg focus-visible:outline focus-visible:outline-teal-500">
          <div class="flex justify-between items-start gap-2"><span class="font-bold text-sm leading-snug">${escapeHTML(lesson.subject)}</span><span class="shrink-0 text-xs font-semibold text-teal-600 dark:text-teal-300">${escapeHTML(lesson.room || '')}</span></div>
          <div class="flex justify-between items-center gap-2 mt-1"><span class="text-xs text-slate-500 dark:text-slate-400">${escapeHTML(subtitle || (appMode==='student'?'Преподаватель не указан':'Группы не указаны'))}${note?' · 📝':''}</span><span aria-hidden="true" class="detail-chevron text-slate-400 text-xs">⌄</span></div>
        </summary>
        <div class="pt-1 pb-2 space-y-2 text-xs"><p class="text-slate-500">${escapeHTML([lesson.type,lesson.tag].filter(Boolean).join(' · '))}</p>
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
    return `${gap}<article class="rounded-2xl p-3.5 bg-white dark:bg-[#101c2e] border ${current?'border-teal-500':'border-slate-200 dark:border-slate-800'} flex gap-3">
      <div class="w-12 shrink-0 text-center pt-1"><div class="font-semibold text-xs">${escapeHTML(pair.start)}</div><div class="text-[11px] text-slate-400 mt-1">${escapeHTML(pair.end)}</div><div class="text-[10px] text-slate-400 mt-2">${pair.number} пара</div>${current?'<span class="text-[9px] text-teal-500 font-bold">СЕЙЧАС</span>':''}</div><div class="min-w-0 flex-1">${lessons}</div></article>`;
  }).filter(Boolean);
  container.innerHTML=rows.join('') || '<div class="text-center py-10"><p class="font-semibold">В этот день занятий нет</p><p class="text-xs text-slate-500 mt-2">Выберите другой день</p></div>';
}
function updateCompactUI() {
  if(!currentSchedule)return;
  document.getElementById('currentEntityBtnText').textContent=appMode==='student'?savedState.groupName:(currentSchedule.profile?.short_name || savedState.teacherKey);
  const checked=currentSchedule.source_checked_at,offline=lastDelivery?.cached || !navigator.onLine;
  const text=checked?`Проверено ${displayDate(checked)}`:`Сборка ${displayDate(currentSchedule.generated_at)}`;
  document.getElementById('compactFreshnessText').textContent=(offline?'Офлайн · ':'')+text+' ⓘ';
  const theme=document.getElementById('themeToggleBtn');
  theme.textContent=`Тема: ${{dark:'тёмная',light:'светлая',system:'как на устройстве'}[themeMode]}`;
}
const simpleApplyTheme=applyTheme;
applyTheme=function(){simpleApplyTheme();const button=document.getElementById('themeToggleBtn');button.textContent=`Тема: ${{dark:'тёмная',light:'светлая',system:'как на устройстве'}[themeMode]}`;};
document.addEventListener('DOMContentLoaded',()=>{
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
