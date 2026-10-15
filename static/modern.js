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
  document.getElementById('favStarBtn').textContent = getFavorites().some(f => favoriteKey(f) === favoriteKey(currentFavorite())) ? '⭐ Избранное' : '☆ Избранное';
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
    roomCheck={week:getWeekNum(date),day:(date.getDay()+6)%7,pair:index+1};
  }
  document.getElementById('roomTimeControls').innerHTML=roomTimeControls();renderRoomsModalList();
}
function setRoomManual() {
  roomCheck={week:Number(document.getElementById('roomWeek').value),day:Number(document.getElementById('roomDay').value),pair:Number(document.getElementById('roomPair').value)};
  renderRoomsModalList();
}
function roomTimeControls() {
  const context=roomContext();
  const options=(values,selected)=>values.map(([value,label])=>`<option value="${value}" ${value===selected?'selected':''}>${label}</option>`).join('');
  return `<div class="flex gap-2 text-xs my-2"><button onclick="setRoomPreset('now')">⚡ Сейчас</button><button onclick="setRoomPreset('next')">⏭ Следующая пара</button></div><div class="flex gap-2 text-xs mb-3"><select id="roomWeek" aria-label="Неделя проверки" onchange="setRoomManual()" class="rounded-lg p-2 bg-slate-100 dark:bg-slate-800">${options([[1,'I неделя'],[2,'II неделя']],context.week)}</select><select id="roomDay" aria-label="День проверки" onchange="setRoomManual()" class="rounded-lg p-2 bg-slate-100 dark:bg-slate-800">${options(['Пн','Вт','Ср','Чт','Пт','Сб','Вс'].map((label,i)=>[i,label]),context.day)}</select><select id="roomPair" aria-label="Пара для проверки" onchange="setRoomManual()" class="rounded-lg p-2 bg-slate-100 dark:bg-slate-800">${options(ROOM_BELLS.map((time,i)=>[i+1,`${i+1} · ${time}`]),context.pair || 1)}</select></div>`;
}
function roomOccupancy(room, context) {
  const prefix=`${context.week}:${DAY_KEYS[context.day]}:`;
  const lessons=context.day===6?[]:Object.entries(room.slots).filter(([key])=>key.startsWith(prefix)).flatMap(([,slots])=>Array.isArray(slots)?slots:[slots]);
  return {lessons,busy:lessons.filter(l=>context.pair ? l.pair===context.pair : context.minutes>=timeToMinutes(l.start) && context.minutes<timeToMinutes(l.end))};
}
async function openRoomsModal(prefill = '') {
  let modal = document.getElementById('roomsModal');
  if (!modal) {
    modal = document.createElement('div'); modal.id = 'roomsModal';
    modal.className = 'fixed inset-0 z-50 bg-slate-950/80 flex items-center justify-center p-4';
    modal.innerHTML = `<div role="dialog" aria-modal="true" aria-label="Радар аудиторий" class="w-full max-w-lg rounded-3xl p-4 bg-white dark:bg-[#101c2e] max-h-[88vh] overflow-auto"><button onclick="closeRoomsModal()" class="float-right" aria-label="Закрыть">✕</button><h2 class="font-bold">🚪 Радар аудиторий</h2><p class="text-xs my-2">Занятость по известным расписаниям. Отсутствие пары не гарантирует доступ в аудиторию.</p><input id="roomSearchInput" aria-label="Поиск аудитории" placeholder="Аудитория или корпус" class="w-full rounded-xl p-2 bg-slate-100 dark:bg-slate-800" oninput="renderRoomsModalList()"><div class="flex gap-3 my-3 text-xs"><button onclick="roomFilter='all';renderRoomsModalList()">Все</button><button onclick="roomFilter='free';renderRoomsModalList()">🟢 Нет пар</button><button onclick="roomFilter='busy';renderRoomsModalList()">🔴 Есть пары</button></div><div id="roomsListContainer"></div></div>`;
    document.body.append(modal);
  }
  modal.classList.remove('hidden'); document.getElementById('roomSearchInput').value = prefill;
  document.getElementById('roomsListContainer').textContent = 'Загрузка индекса аудиторий…';
  try {
    if (!roomDirectory) { const res = await fetch(getApiUrl('/api/rooms')); if (!res.ok) throw Error(); roomDirectory = await res.json(); }
    renderRoomsModalList(); clearInterval(roomTimer); roomTimer = setInterval(renderRoomsModalList, 15000);
  } catch { document.getElementById('roomsListContainer').textContent = 'Не удалось загрузить индекс. Закройте окно и попробуйте снова.'; }
}
function closeRoomsModal() { document.getElementById('roomsModal').classList.add('hidden'); clearInterval(roomTimer); }
function renderRoomsModalList() {
  const context = roomContext();
  let controls=document.getElementById('roomTimeControls');
  if(!controls){controls=document.createElement('div');controls.id='roomTimeControls';document.getElementById('roomSearchInput').before(controls);controls.innerHTML=roomTimeControls();}
  const query = document.getElementById('roomSearchInput').value.toLowerCase().trim();
  const rows = (roomDirectory?.rooms || []).map(room => {
    const {lessons,busy} = roomOccupancy(room,context);
    const location = decodeEsstuRoom(room.room)?.location || '';
    if (!`${room.room} ${location}`.toLowerCase().includes(query) || (roomFilter==='free' && busy.length) || (roomFilter==='busy' && !busy.length)) return '';
    return `<div class="rounded-2xl p-3 border border-slate-500/30 my-2"><b>${escapeHTML(room.room)}</b> • ${escapeHTML(location)}<div class="text-xs mt-2">${busy.length ? '🔴 По расписанию: ' + [...new Set(busy.map(l => escapeHTML(`${l.subject} • ${l.teacher} • ${l.groups}`)))].join('<br>') : `🟢 ${context.pair ? 'В выбранную пару' : 'Сейчас'} занятий по известным расписаниям нет`}</div><div class="text-xs mt-2 text-slate-400">${[...new Set(lessons.map(l => escapeHTML(`${l.start}–${l.end}: ${l.subject}`)))].join('<br>')}</div></div>`;
  }).filter(Boolean);
  const label=`${context.week===1?'I':'II'} неделя • ${['Пн','Вт','Ср','Чт','Пт','Сб','Вс'][context.day]} • ${context.pair ? context.pair+' пара' : 'сейчас'}`;
  document.getElementById('roomsListContainer').innerHTML = `<p class="text-xs text-teal-600">${label}</p>`+(rows.join('') || 'Аудитории не найдены');
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
