const APP_VERSION = '2.5.0';
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
  const label = lesson.source_type === 'official_caf' ? 'Расписание кафедры' : 'Расписание группы';
  const source = file ? `<a class="text-teal-600 dark:text-teal-400 text-[11px] underline" target="_blank" rel="noopener" href="https://portal.esstu.ru/${file.split('/').map(encodeURIComponent).join('/')}">${label}: ${escapeHTML(file)}</a>` : '<span class="text-[11px] text-slate-400">Источник не указан</span>';
  const changes = highlightChanges ? scheduleChanges.filter(c => c.current && String(c.current.week)===String(selectedWeek) && c.current.day===selectedDayKey && c.current.pair===pair && c.current.subject===lesson.subject) : [];
  return `<div class="mt-2">${source}${changes.map(c=>`<div class="text-xs text-amber-600 dark:text-amber-300 mt-1">${escapeHTML(c.label)}</div>`).join('')}</div>`;
}
function displayDate(value) {
  if (!value || Number.isNaN(Date.parse(value))) return 'дата неизвестна';
  return new Intl.DateTimeFormat('ru-RU',{timeZone:'Asia/Irkutsk',dateStyle:'short',timeStyle:'short'}).format(new Date(value));
}
function updateExperienceUI() {
  if (!currentSchedule) return;
  renderDataQuality();
  protectOfflineSchedules();
  const cached = lastDelivery?.cached || !navigator.onLine || currentSchedule.is_stale_fallback;
  document.getElementById('freshnessBadge').textContent = cached ? '💾 Сохранённая копия' : '🌐 Загружено с сайта';
  const checked = currentSchedule.source_checked_at;
  document.getElementById('freshnessTimestamp').textContent = `${currentSchedule.source_file || (currentSchedule.partial ? 'Расписания групп' : 'Сводный каталог')} • Проверка источника: ${displayDate(checked)} • Сборка: ${displayDate(currentSchedule.generated_at)}${lastDelivery ? ' • Получено: '+displayDate(lastDelivery.at) : ''}`;
  document.getElementById('btnToggleDiff').textContent = `Изменения (${scheduleChanges.length})${highlightChanges ? '' : ' · скрыты'}`;
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
  const reason=response.headers.get('X-ESSTU-Cache');
  data._delivery = {cached:['offline','server-error','refreshing'].includes(reason), reason, at:new Date().toISOString()};
  return data;
}
function toggleDiffHighlightMode() { highlightChanges=!highlightChanges;renderAll(); }
async function forceRefreshSchedule() {
  const button = document.getElementById('refreshSchedule'); button.disabled=true;button.textContent='Проверка…';
  try {
    const ok = appMode==='student' ? await loadStudentSchedule(savedState.section,savedState.groupId,savedState.groupName,true) : await loadTeacherSchedule(savedState.teacherKey,savedState.teacherCafId,true);
    if (!ok) throw Error();
    updateExperienceUI();
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
let pendingWorker = null, appReloading = false, updateFallbackTimer;
function reloadAppOnce() {
  if(appReloading)return;
  appReloading=true;clearTimeout(updateFallbackTimer);location.reload();
}
function showUpdateBanner(worker) {
  pendingWorker=worker;
  document.getElementById('appUpdateBanner').classList.remove('hidden');
}
async function applyAppUpdate(event) {
  const button=event?.currentTarget || document.getElementById('applyAppUpdateButton');
  button.disabled=true;button.textContent='Обновление…';
  if(!pendingWorker){reloadAppOnce();return;}
  updateFallbackTimer=setTimeout(reloadAppOnce,4000);
  try{pendingWorker.postMessage({type:'SKIP_WAITING'});}
  catch(error){console.warn('Не удалось активировать обновление',error);reloadAppOnce();}
}
async function initAppUpdates() {
  if (!('serviceWorker' in navigator)) return;
  let hadController=!!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener('controllerchange',()=>{
    if(hadController)reloadAppOnce();
    hadController=true;
  });
  try {
    const registration=await navigator.serviceWorker.register('sw.js',{updateViaCache:'none'});
    if (registration.waiting) showUpdateBanner(registration.waiting);
    registration.addEventListener('updatefound',()=>{
      const worker=registration.installing;
      worker?.addEventListener('statechange',()=>{ if(worker.state==='installed' && navigator.serviceWorker.controller) showUpdateBanner(worker); });
    });
    const check=()=>{if(document.visibilityState==='visible')registration.update().catch(()=>{});};
    document.addEventListener('visibilitychange',check);
    setInterval(check,15*60000);
  } catch (error) { console.error('Не удалось включить офлайн-режим',error); }
}
document.addEventListener('DOMContentLoaded',()=>{
  document.getElementById('applyAppUpdateButton').addEventListener('click',applyAppUpdate);
  initAppUpdates();
  window.addEventListener('online',updateExperienceUI);window.addEventListener('offline',updateExperienceUI);
});

let catalogQuality = null;
function renderDataQuality() {
  const ageWarning=document.getElementById('publicationFreshnessWarning');
  const generated=Date.parse(catalogQuality?.generated_at);
  if(ageWarning){
    const stale=Number.isFinite(generated) && Date.now()-generated>12*3600000;
    ageWarning.hidden=!stale;
    ageWarning.textContent=stale?'Выгрузка не обновлялась более 12 часов. Проверьте занятия на портале ВСГУТУ.':'';
  }
  const warning=document.getElementById('incompleteWarning');
  if(warning){warning.classList.toggle('hidden',!currentSchedule?.is_incomplete && !currentSchedule?.incomplete_reason);warning.textContent=currentSchedule?.is_incomplete?'Данные неполные: '+scheduleIssueText(currentSchedule):'Показана сохранённая копия: '+scheduleIssueText(currentSchedule);}
  const status=document.getElementById('parseQualityStatus');
  if(status)status.textContent=catalogQuality ? `Ошибок разбора: ${catalogQuality.parse_error_count ?? 0} · Неполных расписаний: ${catalogQuality.incomplete_schedule_count ?? '—'} · Ячеек для сверки: ${catalogQuality.review_cell_count ?? catalogQuality.unparsed_cell_count ?? '—'}` : 'Статистика качества пока недоступна';
}
document.addEventListener('DOMContentLoaded',async()=>{
  try { const response=await fetch(getApiUrl('/api/status')); if(!response.ok)throw Error(response.status); catalogQuality=await response.json(); }
  catch(error){console.warn('Статистика разбора недоступна',error);}
  renderDataQuality();
  setInterval(renderDataQuality,60000);
});


function protectOfflineSchedules(){
  if(!navigator.serviceWorker?.controller)return;
  const choices=[currentFavorite(),...getFavorites()].slice(0,30);
  const urls=choices.flatMap(choice=>choice.type==='student'?
    [getApiUrl(`/api/schedule/${choice.section}/${encodeURIComponent(choice.id)}`),getApiUrl(`/api/groups?section=${choice.section}`)]:
    [getApiUrl('/api/teachers/all?section=bakalavriat')]);
  navigator.serviceWorker.controller.postMessage({type:'PROTECT_DATA',urls:[...new Set(urls.map(url=>new URL(url,location.href).href))]});
}
async function receiveBackgroundData(event){
  const message=event.data;
  if(message?.type!=='DATA_UPDATED')return;
  const url=new URL(message.url,location.href);
  if(url.origin!==location.origin || !url.href.startsWith(new URL('api/',location.href).href))return;
  try{
    const data=await scheduleJSON(await fetch(url,{headers:{'X-ESSTU-Cache-Only':'1'}}));
    if(url.pathname.endsWith('/rooms.json')){roomDirectory=data;if(!document.getElementById('roomsModal')?.classList.contains('hidden'))renderRoomsModalList();}
    else if(data.mode==='student' && appMode==='student' && data.section===savedState.section && String(data.group_id)===String(savedState.groupId)){
      currentSchedule=data;trackSchedule(data);renderAll();
    }else if(Array.isArray(data.teachers)){
      allTeachersDirectory=data.teachers.map(teacher=>({...teacher,_delivery:data._delivery}));
      if(appMode==='teacher'){const current=allTeachersDirectory.find(teacher=>normSearch(teacher.teacher_key)===normSearch(savedState.teacherKey));if(current){currentSchedule=current;trackSchedule(current);renderAll();}}
    }
  }catch(error){console.warn('Не удалось показать фоновое обновление',error);}
}
if('serviceWorker' in navigator)navigator.serviceWorker.addEventListener('message',receiveBackgroundData);
