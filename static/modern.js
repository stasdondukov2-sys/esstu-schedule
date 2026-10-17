function escapeHTML(value) {
  return String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function initialsAvatar(name) {
  const initials=String(name || '').split(/\s+/).map(word=>word.match(/\p{L}/u)?.[0] || '').filter(Boolean).slice(0,2).join('').toUpperCase() || 'П';
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><rect width="96" height="96" rx="18" fill="#0f2942"/><text x="48" y="58" text-anchor="middle" font-family="sans-serif" font-size="30" fill="#5eead4">${escapeHTML(initials)}</text></svg>`;
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
}
function teacherAvatarURL(profile) {
  const photo=profile?.photo;
  return typeof photo==='string' && /^avatars\/[A-Za-z0-9_-]+\.(png|jpe?g|webp)$/i.test(photo) ? photo : initialsAvatar(profile?.short_name || profile?.full_name);
}
let visibleTeacherChoices=[];
function chooseTeacherByIndex(index) {const teacher=visibleTeacherChoices[index];if(teacher)chooseTeacher(teacher.teacher_key,teacher.caf_id || '');}
function filterCafByIndex(instituteIndex,departmentIndex) {const department=departmentsHierarchy[instituteIndex]?.departments?.[departmentIndex];if(department)filterByCaf(department.caf_id);}
function getFavorites() {
  try { const value = JSON.parse(localStorage.getItem('esstu_favorites_v1') || '[]'); return Array.isArray(value) ? value : []; } catch { return []; }
}
function currentFavorite() {
  return appMode === 'student' ? {type: appMode, section: savedState.section, id: savedState.groupId, label: savedState.groupName} : {type: appMode, teacherKey: savedState.teacherKey, cafId: savedState.teacherCafId, label: currentSchedule?.profile?.short_name || savedState.teacherKey};
}
function favoriteKey(f) { return f.type === 'student' ? `${f.section}:${f.label}` : `teacher:${f.teacherKey}`; }
function toggleCurrentFavorite() {
  const current = currentFavorite(), list = getFavorites(), key = favoriteKey(current);
  const next = list.some(f => favoriteKey(f) === key) ? list.filter(f => favoriteKey(f) !== key) : [...list, current];
  localStorage.setItem('esstu_favorites_v1', JSON.stringify(next)); renderFavoritesBar();
}
function renderFavoritesBar() {
  const bar = document.getElementById('favoritesBar'); bar.replaceChildren();
  getFavorites().forEach(f => {
    const button = document.createElement('button'); button.textContent = `${f.type === 'student' ? '🎓' : '👨‍🏫'} ${f.label}`;
    button.className = 'shrink-0 rounded-xl px-3 py-2 min-h-[44px] bg-teal-600 text-white';
    button.onclick = () => {
      if(typeof closeSearchModal==='function')closeSearchModal();
      return f.type === 'student' ? loadStudentSchedule(f.section, f.id, f.label) : loadTeacherSchedule(f.teacherKey, f.cafId);
    };
    bar.append(button);
  });
  const selected=getFavorites().some(f => favoriteKey(f) === favoriteKey(currentFavorite()));
  const toggle=document.getElementById('favStarBtn');
  toggle.innerHTML=uiIcon('star')+(selected?' В избранном':' Добавить');
  toggle.setAttribute('aria-pressed',String(selected));
  if(!bar.children.length)bar.innerHTML='<p class="search-empty-hint">Добавьте расписание, чтобы быстро открывать его здесь.</p>';
}
function activeSlots(schedule, now = getUlanUdeNow()) {
  const day = (now.getDay() + 6) % 7, minutes = now.getHours()*60 + now.getMinutes();
  if (day === 6) return [];
  return (schedule.weeks?.[getWeekNum(now)]?.[DAY_KEYS[day]]?.pairs || []).filter(p => minutes >= timeToMinutes(p.start) && minutes < timeToMinutes(p.end));
}
function getTeacherLiveStatus(t) {
  const lessons = activeSlots(t).flatMap(p => p.lessons || []);
  return lessons.length ? escapeHTML('🟢 По расписанию: ' + lessons.map(l => l.room || l.subject).join(', ')) : '⚪ Сейчас нет занятий по расписанию';
}
let roomDirectory = null, roomFilter = 'all', roomTimer;
let roomCheck = null;
const ROOM_BELLS = ['09:00','10:45','13:00','14:45','16:25','18:05'];
function roomContext(now = getUlanUdeNow()) {
  if (roomCheck) return roomCheck;
  return {week:getWeekNum(now), day:(now.getDay()+6)%7, pair:null, minutes:now.getHours()*60+now.getMinutes()};
}
function setRoomPreset(preset) {
  roomCheck = null;
  if (preset === 'next') {
    const date = getUlanUdeNow();
    let minutes=date.getHours()*60+date.getMinutes(), index=ROOM_BELLS.findIndex(time=>timeToMinutes(time)>minutes);
    if (index<0 || date.getDay()===0) { date.setDate(date.getDate()+1);index=0; }
    if (date.getDay()===0) date.setDate(date.getDate()+1);
    roomCheck={week:getWeekNum(date),day:(date.getDay()+6)%7,pair:index+1,mode:'next'};
  }
  document.getElementById('roomTimeControls').innerHTML=roomTimeControls();renderRoomsModalList();
}
function setRoomManual() {
  roomCheck={week:Number(document.getElementById('roomWeek').value),day:Number(document.getElementById('roomDay').value),pair:Number(document.getElementById('roomPair').value) || 1,mode:'manual'};
  document.getElementById('roomPair').value=String(roomCheck.pair);
  renderRoomsModalList();
}
function roomTimeControls() {
  const context=roomContext();
  const options=(values,selected)=>values.map(([value,label])=>`<option value="${value}" ${value===selected?'selected':''}>${label}</option>`).join('');
  return `<div class="segmented room-presets" role="group" aria-label="Время проверки"><button data-room-preset="now" aria-pressed="${!roomCheck}" onclick="setRoomPreset('now')">Сейчас</button><button data-room-preset="next" aria-pressed="${context.mode==='next'}" onclick="setRoomPreset('next')">Следующая пара</button></div><div class="room-selects"><select id="roomWeek" aria-label="Неделя проверки" onchange="setRoomManual()">${options([[1,'I неделя'],[2,'II неделя']],context.week)}</select><select id="roomDay" aria-label="День проверки" onchange="setRoomManual()">${options(['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].map((label,i)=>[i,label]),context.day)}</select><select id="roomPair" aria-label="Пара для проверки" onchange="setRoomManual()">${!context.pair?'<option value="0" selected disabled>Текущее время</option>':''}${options(ROOM_BELLS.map((time,i)=>[i+1,`${i+1} пара · ${time}`]),context.pair || 0)}</select></div>`;
}
function roomOccupancy(room, context) {
  const prefix=`${context.week}:${DAY_KEYS[context.day]}:`;
  const lessons=(context.day===6?[]:Object.entries(room.slots).filter(([key])=>key.startsWith(prefix)).flatMap(([,slots])=>Array.isArray(slots)?slots:[slots])).sort((a,b)=>timeToMinutes(a.start)-timeToMinutes(b.start) || timeToMinutes(a.end)-timeToMinutes(b.end) || String(a.subject).localeCompare(String(b.subject),'ru'));
  return {lessons,busy:lessons.filter(l=>context.pair ? Number(l.pair)===Number(context.pair) : context.minutes>=timeToMinutes(l.start) && context.minutes<timeToMinutes(l.end))};
}
function roomLessonLines(lessons) {
  // Several groups and department schedules may describe the same lesson.
  const rows=new Map();
  for(const lesson of lessons){
    const key=JSON.stringify([lesson.start,lesson.end,lesson.subject]);
    if(!rows.has(key))rows.set(key,lesson);
  }
  return [...rows.values()].map(lesson=>`<li><span class="room-lesson-time">${escapeHTML(lesson.start)}–${escapeHTML(lesson.end)}</span> <span>${escapeHTML(lesson.subject || 'Предмет не указан')}</span></li>`).join('');
}
function roomSlotTimeline(lessons,context) {
  const count=Math.max(ROOM_BELLS.length,...lessons.map(lesson=>Number(lesson.pair)||0));
  return `<div class="room-timeline" aria-label="Слоты дня: заполненные — есть занятия">${Array.from({length:count},(_,i)=>{
    const number=i+1,busy=lessons.some(lesson=>Number(lesson.pair)===number),label=`${number} пара${ROOM_BELLS[i]?' · '+ROOM_BELLS[i]:''}: ${busy?'есть занятия':'нет известных занятий'}`;
    return `<span class="room-slot ${busy?'is-busy':''}" data-selected="${Number(context.pair)===number}" title="${label}"><span class="sr-only">${label}</span>${number}</span>`;
  }).join('')}</div>`;
}
function setRoomFilter(filter){roomFilter=filter;renderRoomsModalList();}
async function openRoomsModal(prefill = '') {
  let modal = document.getElementById('roomsModal');
  if (!modal) {
    modal = document.createElement('div'); modal.id = 'roomsModal';
    modal.className = 'simple-overlay hidden';
    modal.innerHTML = `<div class="simple-sheet"><div class="flex justify-between items-center gap-3"><h2 class="font-bold">Радар аудиторий</h2><button onclick="closeRoomsModal()" aria-label="Закрыть" class="w-10">${uiIcon('close')}</button></div><p class="room-hint">Корпуса определены по обозначению аудитории.</p><p class="room-hint">${uiIcon('info')} Занятость по известным расписаниям. Отсутствие пары не гарантирует доступ.</p><input id="roomSearchInput" aria-label="Поиск аудитории" placeholder="Аудитория или корпус" class="w-full rounded-xl p-2" oninput="renderRoomsModalList()"><div class="segmented room-filters" role="group" aria-label="Занятость аудитории"><button data-room-filter="all" onclick="setRoomFilter('all')">Все</button><button data-room-filter="free" onclick="setRoomFilter('free')">Нет пар</button><button data-room-filter="busy" onclick="setRoomFilter('busy')">Есть пары</button></div><div id="roomsListContainer"></div></div>`;
    document.body.append(modal);
  }
  openSimpleDialog('roomsModal'); document.getElementById('roomSearchInput').value = prefill;
  document.getElementById('roomsListContainer').textContent = 'Загрузка индекса аудиторий…';
  try {
    if (!roomDirectory) { const res = await fetch(getApiUrl('/api/rooms')); if (!res.ok) throw Error(); roomDirectory = await res.json(); }
    renderRoomsModalList(); clearInterval(roomTimer); roomTimer = setInterval(renderRoomsModalList, 15000);
  } catch { document.getElementById('roomsListContainer').textContent = 'Не удалось загрузить индекс. Закройте окно и попробуйте снова.'; }
}
function closeRoomsModal() { closeSimpleDialog('roomsModal'); clearInterval(roomTimer); }
function renderRoomsModalList() {
  const context = roomContext();
  let controls=document.getElementById('roomTimeControls');
  if(!controls){controls=document.createElement('div');controls.id='roomTimeControls';document.getElementById('roomSearchInput').before(controls);controls.innerHTML=roomTimeControls();}
  // Keep time presets in sync without replacing the focused manual selectors.
  for(const button of controls.querySelectorAll('[data-room-preset]'))button.setAttribute('aria-pressed',String(button.dataset.roomPreset==='now'?!roomCheck:context.mode==='next'));
  for(const button of document.querySelectorAll('[data-room-filter]'))button.setAttribute('aria-pressed',String(button.dataset.roomFilter===roomFilter));
  if(!roomCheck){document.getElementById('roomWeek').value=String(context.week);document.getElementById('roomDay').value=String(context.day);}
  const query = document.getElementById('roomSearchInput').value.toLowerCase().trim();
  const rows = (roomDirectory?.rooms || []).map(room => {
    const {lessons,busy} = roomOccupancy(room,context);
    const building = decodeEsstuRoom(room.room)?.building || 'Корпус не определён';
    return {...room,building,lessons,busy};
  }).filter(room=>`${room.room} ${room.building}`.toLowerCase().includes(query) && (roomFilter!=='free' || !room.busy.length) && (roomFilter!=='busy' || room.busy.length))
    .sort((a,b)=>Number(!!a.busy.length)-Number(!!b.busy.length) || a.building.localeCompare(b.building,'ru',{numeric:true}) || a.room.localeCompare(b.room,'ru',{numeric:true}));
  let previousGroup='';
  const cards=rows.map(room=>{
    const busy=room.busy.length>0,group=`${busy?'busy':'free'}:${room.building}`;
    const heading=group===previousGroup?'':`<h3 class="room-group-title">${busy?(context.pair?'Занятые в выбранную пару':'Занятые сейчас'):(context.pair?'Свободные в выбранную пару':'Свободные сейчас')} · ${escapeHTML(room.building)}</h3>`;
    previousGroup=group;
    const end=busy?room.busy.map(lesson=>lesson.end).sort().at(-1):'';
    const status=busy?`Занята до ${end}`:'Свободна';
    const busyInfo=[...new Set(room.busy.map(lesson=>[lesson.subject,lesson.teacher,lesson.groups].filter(Boolean).join(' · ')))].map(escapeHTML).join('<br>');
    return `${heading}<article class="room-card" data-room="${escapeHTML(room.room)}"><div class="room-card-heading"><h4>${escapeHTML(room.room)}</h4><span class="chip-status chip-status--${busy?'busy':'free'}">${uiIcon(busy?'clock':'check')}${escapeHTML(status)}</span></div>${busyInfo?`<p class="room-busy-info">${busyInfo}</p>`:''}${roomSlotTimeline(room.lessons,context)}<ul class="room-day-lessons">${roomLessonLines(room.lessons)}</ul></article>`;
  });
  const label=`${context.week===1?'I':'II'} неделя · ${['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][context.day]} · ${context.pair ? context.pair+' пара · '+ROOM_BELLS[context.pair-1] : 'сейчас'}`;
  document.getElementById('roomsListContainer').innerHTML = `<p class="room-context">${label}</p><p class="room-hint">Слоты дня: заполненные — есть занятия.</p>`+(cards.join('') || '<p class="room-hint">Аудитории не найдены</p>');
}
async function shareCurrentScheduleLink() {
  const url = new URL(location.href); url.search = ''; url.hash = '';
  const f = currentFavorite(); url.searchParams.set('mode', f.type);
  if (f.type === 'student') { url.searchParams.set('group', f.label); url.searchParams.set('section', f.section); }
  else { url.searchParams.set('teacher', f.teacherKey); url.searchParams.set('caf', f.cafId); }
  try { await navigator.clipboard.writeText(url.href); alert('Ссылка скопирована'); } catch { prompt('Ссылка на расписание:', url.href); }
}
function icsEscape(value) { return String(value || '').replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;'); }
function exportScheduleToICS() {
  if (!currentSchedule) return;
  if(scheduleTab==='session'){exportSessionICS();return;}
  const monday = getWeekRangeDates(selectedWeek).monday.date;
  const stamp = (d,time) => `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}T${time.replace(':','')}00`;
  const lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//ESSTU//Schedule//RU','CALSCALE:GREGORIAN'];
  DAY_KEYS.forEach((day,index) => {
    const date = new Date(monday); date.setDate(monday.getDate()+index);
    if(currentSchedule.weeks?.[selectedWeek]?.[day]?.session_date)return;
    (currentSchedule.weeks?.[selectedWeek]?.[day]?.pairs || []).forEach(p => filterLessons(p.lessons).forEach((l,idx) => {
      lines.push('BEGIN:VEVENT',`UID:${encodeURIComponent(favoriteKey(currentFavorite()))}-${stamp(date,p.start)}-${idx}@esstu-schedule`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')}`,`DTSTART;TZID=Asia/Irkutsk:${stamp(date,p.start)}`,`DTEND;TZID=Asia/Irkutsk:${stamp(date,p.end)}`,`SUMMARY:${icsEscape(l.subject)}`,`LOCATION:${icsEscape(l.room)}`,`DESCRIPTION:${icsEscape(l.teacher || l.groups)}`,'END:VEVENT');
    }));
  });
  lines.push('END:VCALENDAR');
  const folded = lines.map(line => { let result='', width=0; for (const char of line) { const size=new TextEncoder().encode(char).length; if(width+size>75){result+='\r\n ';width=1;} result+=char;width+=size;} return result; });
  const url = URL.createObjectURL(new Blob([folded.join('\r\n')+'\r\n'], {type:'text/calendar;charset=utf-8'}));
  const a = document.createElement('a'); a.href=url;a.download=`esstu_week${selectedWeek}.ics`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.addEventListener('DOMContentLoaded', () => { setInterval(() => { if (!document.getElementById('teacherModal').classList.contains('hidden')) renderTeacherModalContent(); }, 15000); });
