const APP_VERSION = '2.4.0';
let scheduleChanges = [], highlightChanges = true, lastDelivery = null;
function flattenSchedule(schedule) {
  const rows = [];
  for (const [week, days] of Object.entries(schedule.weeks || {})) {
    for (const [day, data] of Object.entries(days)) for (const pair of data.pairs || []) {
      for (const lesson of pair.lessons || []) rows.push({week, day, pair:pair.number, start:pair.start, end:pair.end,
        subject:lesson.subject || '', room:lesson.room || '', teacher:lesson.teacher || '',
        groups:lesson.groups || '', tag:lesson.tag || '', type:lesson.type || ''});
    }
  }
  return rows.sort((a,b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
}
function compareSchedules(previous, current) {
  if (!previous) return [];
  const before = [...previous], changes = [];
  for (const row of current) {
    const exact = before.findIndex(old => JSON.stringify(old) === JSON.stringify(row));
    if (exact >= 0) { before.splice(exact,1); continue; }
    let index = before.findIndex(old => old.week === row.week && old.day === row.day && old.pair === row.pair && old.subject === row.subject && old.tag === row.tag && old.groups === row.groups);
    // Call something a move only when the remaining subject has one unambiguous match.
    if (index < 0) {
      const matches = before.map((old,i)=>({old,i})).filter(({old}) => old.week === row.week && old.subject === row.subject && old.tag === row.tag && old.groups === row.groups);
      if (matches.length === 1 && current.filter(item => item.week === row.week && item.subject === row.subject && item.tag === row.tag && item.groups === row.groups).length === 1) index = matches[0].i;
    }
    if (index < 0) changes.push({kind:'added',label:'Добавлено занятие',current:row});
    else {
      const old = before.splice(index,1)[0], labels = [];
      if (old.day !== row.day || old.pair !== row.pair || old.start !== row.start || old.end !== row.end) labels.push(`Время: ${old.day}, ${old.start} → ${row.day}, ${row.start}`);
      if (old.room !== row.room) labels.push(`Аудитория: ${old.room || '—'} → ${row.room || '—'}`);
      if (old.teacher !== row.teacher) labels.push(`Преподаватель: ${old.teacher || '—'} → ${row.teacher || '—'}`);
      if (old.type !== row.type) labels.push(`Вид занятия: ${old.type} → ${row.type}`);
      changes.push({kind:'changed',label:labels.join(' • ') || 'Изменены данные занятия',previous:old,current:row});
    }
  }
  return [...changes,...before.map(previous=>({kind:'removed',label:'Занятие удалено из выгрузки',previous}))];
}
function trackSchedule(schedule) {
  lastDelivery = schedule._delivery || null;
  const owner = schedule.mode === 'teacher' ? `teacher:${schedule.teacher_key}` : `${schedule.section}:${schedule.group_name || schedule.group_id}`;
  const key = `esstu_snapshot_v2:${owner}`, rows = flattenSchedule(schedule), signature = JSON.stringify(rows);
  try {
    const previous = JSON.parse(localStorage.getItem(key) || 'null');
    if (previous && JSON.stringify(previous.rows) === signature) scheduleChanges = previous.changes || [];
    else {
      scheduleChanges = compareSchedules(previous?.rows, rows);
      localStorage.setItem(key,JSON.stringify({rows,changes:scheduleChanges}));
    }
  } catch { scheduleChanges = []; }
}
function hasDayChanges(week,day) {
  return highlightChanges && scheduleChanges.some(change => [change.current,change.previous].some(row=>row && String(row.week)===String(week) && row.day===day));
}
function renderLessonMeta(lesson,pair) {
  const file = lesson.source_file;
  const label = lesson.source_type === 'official_caf' ? '🏛 Расписание кафедры' : '📄 Расписание группы';
  const source = file ? `<a class="text-teal-600 dark:text-teal-400 text-[11px] underline" target="_blank" rel="noopener" href="https://portal.esstu.ru/${file.split('/').map(encodeURIComponent).join('/')}">${label}: ${escapeHTML(file)}</a>` : '<span class="text-[11px] text-slate-400">Источник не указан</span>';
  const changes = highlightChanges ? scheduleChanges.filter(c => c.current && String(c.current.week)===String(selectedWeek) && c.current.day===selectedDayKey && c.current.pair===pair && c.current.subject===lesson.subject) : [];
  return `<div class="mt-2">${source}${changes.map(c=>`<div class="text-xs text-amber-600 dark:text-amber-300 mt-1">⚡ ${escapeHTML(c.label)}</div>`).join('')}</div>`;
}
function displayDate(value) {
  if (!value || Number.isNaN(Date.parse(value))) return 'дата неизвестна';
  return new Intl.DateTimeFormat('ru-RU',{timeZone:'Asia/Irkutsk',dateStyle:'short',timeStyle:'short'}).format(new Date(value));
}
function updateExperienceUI() {
  if (!currentSchedule) return;
  const cached = lastDelivery?.cached || !navigator.onLine || currentSchedule.is_stale_fallback;
  document.getElementById('freshnessBadge').textContent = cached ? '💾 Сохранённая копия' : '🌐 Загружено с сайта';
  const checked = currentSchedule.source_checked_at;
  document.getElementById('freshnessTimestamp').textContent = `${currentSchedule.source_file || (currentSchedule.partial ? 'Расписания групп' : 'Сводный каталог')} • Проверка источника: ${displayDate(checked)} • Сборка: ${displayDate(currentSchedule.generated_at)}${lastDelivery ? ' • Получено: '+displayDate(lastDelivery.at) : ''}`;
  document.getElementById('btnToggleDiff').textContent = `⚡ Изменения (${scheduleChanges.length})${highlightChanges ? '' : ' · скрыты'}`;
  const panel = document.getElementById('scheduleChanges');
  panel.classList.toggle('hidden',!highlightChanges || !scheduleChanges.length);
  panel.innerHTML = '<b>Изменения относительно предыдущей загруженной версии</b>' + scheduleChanges.map(c=>{
    const row = c.current || c.previous;
    return `<p class="mt-2">${escapeHTML(row.subject)} • ${escapeHTML(row.day)}, ${row.pair} пара: ${escapeHTML(c.label)}</p>`;
  }).join('');
}
async function scheduleJSON(response) {
  if (!response.ok) throw Error(`HTTP ${response.status}`);
  const data = await response.json();
  data._delivery = {cached:response.headers.get('X-ESSTU-Cache')==='offline', at:new Date().toISOString()};
  return data;
}
function toggleDiffHighlightMode() { highlightChanges=!highlightChanges;renderAll(); }
async function forceRefreshSchedule() {
  const button = document.getElementById('refreshSchedule'); button.disabled=true;button.textContent='Проверка…';
  try {
    const ok = appMode==='student' ? await loadStudentSchedule(savedState.section,savedState.groupId,savedState.groupName,true) : await loadTeacherSchedule(savedState.teacherKey,savedState.teacherCafId,true);
    if (!ok) throw Error();
    document.getElementById('freshnessBadge').textContent = lastDelivery?.cached ? '💾 Сеть недоступна — сохранённая копия' : '✓ Доступная версия проверена';
  } catch { document.getElementById('freshnessBadge').textContent='Не удалось обновить. Попробуйте позже.'; }
  finally { button.disabled=false;button.textContent='🔄 Обновить'; }
}
function renderProminentNext() {
  const target = document.getElementById('prominentNext');
  if (!currentSchedule || !target) return;
  const now=getUlanUdeNow(),day=(now.getDay()+6)%7,minutes=now.getHours()*60+now.getMinutes();
  const pairs=day===6?[]:currentSchedule.weeks?.[getWeekNum(now)]?.[DAY_KEYS[day]]?.pairs || [];
  const next=pairs.filter(p=>p.lessons?.length && timeToMinutes(p.start)>minutes).sort((a,b)=>timeToMinutes(a.start)-timeToMinutes(b.start))[0];
  target.classList.toggle('hidden',!next);
  if (!next) return;
  target.replaceChildren();
  const title=document.createElement('b');title.textContent=`⏭ Следующая пара · ${next.start}–${next.end}`;target.append(title);
  for (const lesson of next.lessons) {
    const text=document.createElement('p');text.className='mt-2 font-semibold';text.textContent=lesson.subject;target.append(text);
    if (lesson.room) { const button=document.createElement('button');button.className='mt-2 px-3 py-2 rounded-xl bg-teal-600 text-white';button.textContent=`📍 ${lesson.room}`;button.onclick=()=>openRoomsModal(lesson.room);target.append(button); }
  }
}
const originalLiveHero = updateLiveHero;
updateLiveHero = function() { originalLiveHero();renderProminentNext(); };
let pendingWorker = null;
function showUpdateBanner(worker) { pendingWorker=worker;document.getElementById('appUpdateBanner').classList.remove('hidden'); }
async function applyAppUpdate() {
  if (pendingWorker) pendingWorker.postMessage({type:'SKIP_WAITING'});
  else location.reload();
}
async function initAppUpdates() {
  if (!('serviceWorker' in navigator)) return;
  let reloading=false;
  navigator.serviceWorker.addEventListener('controllerchange',()=>{
    if (!reloading && pendingWorker) { reloading=true;location.reload(); }
  });
  try {
    const registration=await navigator.serviceWorker.register('sw.js',{updateViaCache:'none'});
    if (registration.waiting) showUpdateBanner(registration.waiting);
    registration.addEventListener('updatefound',()=>{
      const worker=registration.installing;
      worker?.addEventListener('statechange',()=>{ if(worker.state==='installed' && navigator.serviceWorker.controller) showUpdateBanner(worker); });
    });
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible') registration.update().catch(()=>{});});
    setInterval(()=>registration.update().catch(()=>{}),180000);
  } catch (error) { console.error('Не удалось включить офлайн-режим',error); }
}
document.addEventListener('DOMContentLoaded',()=>{
  initAppUpdates();
  window.addEventListener('online',updateExperienceUI);window.addEventListener('offline',updateExperienceUI);
});
