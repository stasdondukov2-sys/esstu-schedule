function escapeHTML(value) {
  return String(value || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
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
    button.className = 'shrink-0 rounded-xl px-3 py-2 bg-teal-600 text-white';
    button.onclick = () => f.type === 'student' ? loadStudentSchedule(f.section, f.id, f.label) : loadTeacherSchedule(f.teacherKey, f.cafId);
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
async function openRoomsModal(prefill = '') {
  let modal = document.getElementById('roomsModal');
  if (!modal) {
    modal = document.createElement('div'); modal.id = 'roomsModal';
    modal.className = 'fixed inset-0 z-50 bg-slate-950/80 flex items-center justify-center p-4';
    modal.innerHTML = `<div role="dialog" aria-modal="true" aria-label="Радар аудиторий" class="w-full max-w-lg rounded-3xl p-4 bg-white dark:bg-[#101c2e] max-h-[88vh] overflow-auto"><button onclick="closeRoomsModal()" class="float-right" aria-label="Закрыть">✕</button><h2 class="font-bold">🚪 Радар аудиторий</h2><p class="text-xs my-2">Занятость по известным расписаниям. Отсутствие пары не гарантирует доступ в аудиторию.</p><input id="roomSearchInput" aria-label="Поиск аудитории" placeholder="Аудитория или корпус" class="w-full rounded-xl p-2 bg-slate-100 dark:bg-slate-800" oninput="renderRoomsModalList()"><div class="flex gap-3 my-3 text-xs"><button onclick="roomFilter='all';renderRoomsModalList()">Все</button><button onclick="roomFilter='free';renderRoomsModalList()">🟢 Нет пар сейчас</button><button onclick="roomFilter='busy';renderRoomsModalList()">🔴 Заняты сейчас</button></div><div id="roomsListContainer"></div></div>`;
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
  const now = getUlanUdeNow(), day = (now.getDay()+6)%7, minutes = now.getHours()*60+now.getMinutes();
  const prefix = `${getWeekNum(now)}:${DAY_KEYS[day]}:`;
  const query = document.getElementById('roomSearchInput').value.toLowerCase().trim();
  const rows = (roomDirectory?.rooms || []).map(room => {
    const lessons = day === 6 ? [] : Object.entries(room.slots).filter(([key]) => key.startsWith(prefix)).flatMap(([,slots]) => Array.isArray(slots) ? slots : [slots]);
    const busy = lessons.filter(l => minutes >= timeToMinutes(l.start) && minutes < timeToMinutes(l.end));
    const location = decodeEsstuRoom(room.room)?.location || '';
    if (!`${room.room} ${location}`.toLowerCase().includes(query) || (roomFilter==='free' && busy.length) || (roomFilter==='busy' && !busy.length)) return '';
    return `<div class="rounded-2xl p-3 border border-slate-500/30 my-2"><b>${escapeHTML(room.room)}</b> • ${escapeHTML(location)}<div class="text-xs mt-2">${busy.length ? '🔴 По расписанию: ' + busy.map(l => escapeHTML(`${l.subject} • ${l.teacher} • ${l.groups}`)).join('<br>') : '🟢 Сейчас занятий по известным расписаниям нет'}</div><div class="text-xs mt-2 text-slate-400">${lessons.map(l => escapeHTML(`${l.start}–${l.end}: ${l.subject}`)).join('<br>')}</div></div>`;
  }).filter(Boolean);
  document.getElementById('roomsListContainer').innerHTML = rows.join('') || 'Аудитории не найдены';
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
  const now = getUlanUdeNow(), monday = new Date(now);
  monday.setDate(now.getDate() - (now.getDay()+6)%7);
  if (getWeekNum(monday) !== selectedWeek) monday.setDate(monday.getDate()+7);
  const stamp = (d,time) => `${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}T${time.replace(':','')}00`;
  const lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//ESSTU//Schedule//RU','CALSCALE:GREGORIAN'];
  DAY_KEYS.forEach((day,index) => {
    const date = new Date(monday); date.setDate(monday.getDate()+index);
    (currentSchedule.weeks?.[selectedWeek]?.[day]?.pairs || []).forEach(p => (p.lessons || []).forEach((l,idx) => {
      lines.push('BEGIN:VEVENT',`UID:${encodeURIComponent(favoriteKey(currentFavorite()))}-${stamp(date,p.start)}-${idx}@esstu-schedule`, `DTSTAMP:${new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'')}`,`DTSTART;TZID=Asia/Irkutsk:${stamp(date,p.start)}`,`DTEND;TZID=Asia/Irkutsk:${stamp(date,p.end)}`,`SUMMARY:${icsEscape(l.subject)}`,`LOCATION:${icsEscape(l.room)}`,`DESCRIPTION:${icsEscape(l.teacher || l.groups)}`,'END:VEVENT');
    }));
  });
  lines.push('END:VCALENDAR');
  const folded = lines.map(line => { let result='', width=0; for (const char of line) { const size=new TextEncoder().encode(char).length; if(width+size>75){result+='\r\n ';width=1;} result+=char;width+=size;} return result; });
  const url = URL.createObjectURL(new Blob([folded.join('\r\n')+'\r\n'], {type:'text/calendar;charset=utf-8'}));
  const a = document.createElement('a'); a.href=url;a.download=`esstu_week${selectedWeek}.ics`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.addEventListener('DOMContentLoaded', () => { setInterval(() => { if (!document.getElementById('teacherModal').classList.contains('hidden')) renderTeacherModalContent(); }, 15000); });
