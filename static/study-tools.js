let scheduleTab='semester';
function storedJSON(key,fallback) {try{return JSON.parse(localStorage.getItem(key)) ?? fallback;}catch{return fallback;}}
function studyOwner() {return appMode==='student'?`group:${savedState.section}:${savedState.groupName}`:`teacher:${savedState.teacherKey}`;}
function activeSubgroup() {
  if(appMode!=='student')return 'all';
  const value=localStorage.getItem('esstu_subgroup_v2:'+studyOwner());
  return ['1','2'].includes(value)?value:'all';
}
function matchesSubgroup(lesson,value) {
  if(!value || value==='all')return true;
  const text=[lesson.tag,...(Array.isArray(lesson.tags)?lesson.tags:[]),lesson.raw,lesson.subject].filter(Boolean).join(' ').toLowerCase();
  if(/(?:^|[^\d])(?:1\s*(?:[,/]|и)\s*2|2\s*(?:[,/]|и)\s*1)\s*(?:п\s*\/?\s*г|подгр)/u.test(text))return true;
  const marks=[...text.matchAll(/(?:^|[^\d])(1|2)\s*(?:[-–]\s*[яй]\s*)?(?:п\s*\/?\s*г(?:р)?\.?|подгрупп[а-яё]*|подгр\.?)(?=$|[^а-яё\d])/gu)].map(match=>match[1]);
  // Unknown/ambiguous notation stays visible. No bare '1' in subject names is a subgroup.
  return !marks.length || marks.includes(value);
}
function setSubgroupFilter(value) {
  if(!['all','1','2'].includes(value))return;
  localStorage.setItem('esstu_subgroup_v2:'+studyOwner(),value);renderAll();
}
function setScheduleTab(tab) {
  scheduleTab=tab==='session'?'session':'semester';
  closeSimpleDialog('moreMenuModal');renderAll();
}
function updateStudyUI() {
  const session=scheduleTab==='session';
  const dated=hasDatedSchedule(currentSchedule) || viewMode==='dates';
  document.getElementById('datedViewBtn').classList.toggle('hidden',!hasDatedRows(currentSchedule));
  document.getElementById('weekControls').classList.toggle('hidden',session || dated);
  document.getElementById('dayTabs').classList.toggle('hidden',session || dated || viewMode==='week');
  document.getElementById('selectedDaySummary').classList.toggle('hidden',session || dated);
  const subgroup=activeSubgroup(),wrap=document.getElementById('subgroupFilterWrap');
  wrap.classList.toggle('hidden',appMode!=='student');
  for(const value of ['all','1','2']){
    const button=document.getElementById('subgroupBtn_'+value),active=value===subgroup;
    button.setAttribute('aria-pressed',String(active));
    button.className='px-3 rounded-xl text-xs font-semibold '+(active?'bg-teal-600 text-white':'bg-slate-100 dark:bg-slate-800');
  }
  const chip=document.getElementById('activeSubgroupChip');
  chip.classList.toggle('hidden',subgroup==='all');chip.textContent=`${subgroup} подгруппа · изменить`;
}
function hasDatedRows(schedule) {return Object.values(schedule?.weeks || {}).some(days=>Object.values(days).some(day=>day.session_date));}
function hasDatedSchedule(schedule) {
  const days=Object.values(schedule?.weeks || {}).flatMap(week=>Object.values(week));
  return days.some(day=>day.session_date) && !days.some(day=>!day.session_date && (day.pairs || []).some(pair=>pair.lessons?.length));
}
let datedLessons=[];
function renderDatedTimetable(container) {
  datedLessons=[];
  const seen=new Set(),days=[];
  for(const [week,entries] of Object.entries(currentSchedule.weeks || {}))for(const [key,day] of Object.entries(entries)){
    const signature=JSON.stringify([day.session_date || `${week}:${key}`,day.pairs]);if(seen.has(signature))continue;seen.add(signature);
    days.push({week,key,day});
  }
  container.innerHTML='<h2 class="font-bold">Занятия по датам</h2><p class="text-xs text-slate-500 dark:text-slate-400">Даты сохранены из источника. Без указанного года день недели не определяется.</p>'+days.map(({week,key,day})=>`<section class="rounded-2xl bg-white dark:bg-[#101c2e] border border-slate-200 dark:border-slate-800 p-4"><h3 class="font-bold text-sm">${escapeHTML(day.session_date || `${day.day_title || key} · ${week==='1'?'I':'II'} неделя`)}</h3>${(day.pairs || []).map(pair=>filterLessons(pair.lessons).map(lesson=>{
    const index=datedLessons.push({week,key,pair,lesson})-1;
    return `<div class="border-l-[3px] ${getTypeBorderClass(lesson.type_code)} pl-3 mt-3"><p class="text-xs text-slate-500 dark:text-slate-400">${escapeHTML(pair.start)}–${escapeHTML(pair.end)} · ${escapeHTML(lesson.type)}</p><p class="text-sm font-semibold mt-1">${escapeHTML(lesson.subject)}</p><p class="text-xs text-slate-500 mt-1">${escapeHTML(appMode==='teacher'?lesson.groups:lesson.teacher)}</p><div class="flex gap-2 text-xs mt-1">${lesson.room?`<button class="px-2 text-teal-600 dark:text-teal-300" onclick="datedLessonAction(${index},'room')">ауд. ${escapeHTML(lesson.room)}</button>`:''}<button class="px-2 text-teal-600 dark:text-teal-300" onclick="datedLessonAction(${index},'note')">Заметка</button></div></div>`;
  }).join('')).join('') || '<p class="text-xs text-slate-500 mt-2">Занятия не указаны</p>'}</section>`).join('');
}
function datedLessonAction(index,action) {
  const item=datedLessons[index];if(!item)return;
  if(action==='room')openRoomsModal(item.lesson.room);
  if(action==='note'){
    const owner=appMode==='student'?savedState.groupName:savedState.teacherKey;
    openNoteModal(`${owner}::${item.week}::${item.key}::${item.pair.number}::${item.lesson.subject}`,item.lesson.subject);
  }
}
function examKind(lesson) {
  if(['exam','test','consultation'].includes(lesson.type_code))return lesson.type_code;
  const type=String(lesson.type || '').toLowerCase(),raw=String(lesson.raw || '').trim().toLowerCase();
  if(/экзамен/.test(type) || /^экз(?:\.|амен)/u.test(raw))return 'exam';
  if(/зач[её]т/.test(type) || /^зач(?:\.|[её]т)/u.test(raw))return 'test';
  if(/консультац/.test(type) || /^конс(?:\.|ультац)/u.test(raw))return 'consultation';
  return null;
}
function explicitISODate(value) {
  const raw=String(value || ''),iso=raw.match(/^(\d{4})-(\d{2})-(\d{2})$/),ru=raw.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if(!iso && !ru)return null;
  const year=Number(iso?iso[1]:ru[3]),month=Number(iso?iso[2]:ru[2]),day=Number(iso?iso[3]:ru[1]);
  const date=new Date(Date.UTC(year,month-1,day));
  return date.getUTCFullYear()===year && date.getUTCMonth()===month-1 && date.getUTCDate()===day?`${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`:null;
}
function getCustomExams() {
  const rows=storedJSON('esstu_exams_v1:'+studyOwner(),[]);
  return Array.isArray(rows)?rows.filter(row=>row && typeof row.id==='string' && typeof row.subject==='string' && explicitISODate(row.date)):[];
}
function saveCustomExams(rows) {localStorage.setItem('esstu_exams_v1:'+studyOwner(),JSON.stringify(rows));}
function collectSessionEvents(schedule=currentSchedule) {
  const events=[],seen=new Set();
  for(const [week,days] of Object.entries(schedule?.weeks || {}))for(const [dayKey,day] of Object.entries(days || {}))for(const pair of day.pairs || [])for(const lesson of filterLessons(pair.lessons)){
    const kind=examKind(lesson);if(!kind)continue;
    const date=explicitISODate(day.session_date || lesson.date),rawDate=day.session_date || '';
    const key=JSON.stringify([date || rawDate || week,date || rawDate?'':dayKey,pair.start,pair.end,lesson.subject,kind,lesson.room,lesson.teacher,lesson.groups,lesson.tag]);
    if(seen.has(key))continue;seen.add(key);
    events.push({id:'official:'+key,subject:lesson.subject,kind,date,rawDate,time:pair.start,end:pair.end,room:lesson.room,teacher:appMode==='teacher'?lesson.groups:lesson.teacher,tag:lesson.tag,source:'official',source_file:lesson.source_file,week,dayKey});
  }
  return [...events,...getCustomExams().map(row=>({...row,source:'custom'}))].sort((a,b)=>(a.date || '9999').localeCompare(b.date || '9999') || String(a.time || '').localeCompare(String(b.time || '')));
}
function countdownText(event,now=getUlanUdeNow()) {
  if(event.done)return 'Отмечено как сданное';
  if(!event.date)return event.rawDate?'Год не указан в источнике':'Дата не указана';
  const days=Math.round((Date.parse(event.date+'T00:00:00Z')-Date.UTC(now.getFullYear(),now.getMonth(),now.getDate()))/86400000);
  return days===0?'Сегодня':days===1?'Завтра':days>1?`Через ${days} дн.`:'Дата прошла';
}
const EXAM_LABELS={exam:'Экзамен',test:'Зачёт',consultation:'Консультация'};
let sessionEvents=[];
function renderSessionTimeline(container) {
  sessionEvents=collectSessionEvents();
  const card=(event,index)=>`<article class="rounded-2xl p-4 bg-white dark:bg-[#101c2e] border border-slate-200 dark:border-slate-800 space-y-2"><div class="flex justify-between gap-2 text-xs"><b class="text-purple-700 dark:text-purple-300">${EXAM_LABELS[event.kind] || 'Аттестация'}</b><span class="text-slate-500 dark:text-slate-400">${escapeHTML(countdownText(event))}</span></div><p class="font-bold">${escapeHTML(event.subject)}</p><p class="text-xs text-slate-600 dark:text-slate-300">${escapeHTML(event.date || event.rawDate || `Неделя ${event.week}, ${DAY_NAMES.find(day=>day.key===event.dayKey)?.full || ''}`)}${event.time?' · '+escapeHTML(event.time):''}${event.room?' · ауд. '+escapeHTML(event.room):''}</p>${event.teacher?`<p class="text-xs text-slate-500 dark:text-slate-400">${escapeHTML(event.teacher)}</p>`:''}${event.tag?`<p class="text-xs text-slate-500">${escapeHTML(event.tag)}</p>`:''}<div class="flex flex-wrap gap-2 text-xs">${event.source==='custom'?`<span class="text-slate-500">Личная запись · только на этом устройстве</span><button onclick="editExam(${index})" class="px-3 bg-slate-100 dark:bg-slate-800 rounded-xl">Изменить</button>`:event.source_file?`<a href="https://portal.esstu.ru/${event.source_file.split('/').map(encodeURIComponent).join('/')}" target="_blank" rel="noopener" class="text-teal-600 dark:text-teal-300 underline">Источник вуза</a>`:'<span class="text-slate-500">Из загруженного расписания</span>'}${event.room?`<button class="px-3 bg-teal-500/10 text-teal-700 dark:text-teal-300 rounded-xl" onclick="sessionRoom(${index})">Аудитория</button>`:''}</div></article>`;
  container.innerHTML=`<div class="flex items-center justify-between gap-2"><h2 class="font-bold">Сессия и зачёты</h2><button class="text-xs text-teal-600 dark:text-teal-300 px-3" onclick="setScheduleTab('semester')">К расписанию</button></div><p class="text-xs text-slate-500 dark:text-slate-400">Аттестации из загруженного расписания и ваши записи. Даты без года требуют уточнения.</p><button class="w-full rounded-xl bg-teal-600 text-white text-sm font-semibold" onclick="openAddExamModal()">+ Добавить личную запись</button>${sessionEvents.length?sessionEvents.map(card).join(''):'<p class="py-6 text-center text-sm text-slate-500">В загруженном расписании экзамены не найдены. Можно добавить личную запись.</p>'}`;
}
function sessionRoom(index) {const room=sessionEvents[index]?.room;if(room)openRoomsModal(room);}
let editingExamId=null,editingExamOwner=null;
function openAddExamModal(event=null) {
  editingExamId=event?.id || null;editingExamOwner=studyOwner();
  document.getElementById('examForm').reset();
  for(const key of ['subject','date','time','room','teacher','kind'])document.getElementById('exam_'+key).value=event?.[key] || (key==='kind'?'exam':'');
  document.getElementById('exam_done').checked=Boolean(event?.done);
  document.getElementById('deleteExamBtn').classList.toggle('hidden',!event);
  document.getElementById('examFormError').textContent='';openSimpleDialog('examModal');document.getElementById('exam_subject').focus();
}
function editExam(index) {const event=sessionEvents[index];if(event?.source==='custom')openAddExamModal(event);}
function saveExam(event) {
  event.preventDefault();const form=document.getElementById('examForm');if(!form.reportValidity())return;
  const subject=document.getElementById('exam_subject').value.trim(),date=explicitISODate(document.getElementById('exam_date').value);
  if(!subject || !date || editingExamOwner!==studyOwner()){document.getElementById('examFormError').textContent='Проверьте предмет и дату; расписание должно оставаться тем же.';return;}
  const row={id:editingExamId || crypto.randomUUID(),subject,date,done:document.getElementById('exam_done').checked};
  for(const key of ['time','room','teacher','kind'])row[key]=document.getElementById('exam_'+key).value.trim();
  const rows=getCustomExams().filter(item=>item.id!==editingExamId);rows.push(row);
  try{saveCustomExams(rows);}catch{document.getElementById('examFormError').textContent='Не удалось сохранить на устройстве.';return;}
  closeSimpleDialog('examModal');renderPairsList();
}
function deleteExam() {if(editingExamId && editingExamOwner===studyOwner()){saveCustomExams(getCustomExams().filter(row=>row.id!==editingExamId));closeSimpleDialog('examModal');renderPairsList();}}
function exportSessionICS() {
  const rows=collectSessionEvents().filter(row=>row.date);
  if(!rows.length){alert('Нет записей с полной датой. Уточните год в источнике или добавьте личную запись.');return;}
  const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//ESSTU//Session//RU','CALSCALE:GREGORIAN'];
  const stamp=new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
  for(const row of rows){
    const day=row.date.replace(/-/g,'');lines.push('BEGIN:VEVENT',`UID:${encodeURIComponent(studyOwner()+row.id)}@esstu-session`,`DTSTAMP:${stamp}`,`SUMMARY:${icsEscape((EXAM_LABELS[row.kind] || '')+' '+row.subject)}`,`LOCATION:${icsEscape(row.room)}`,`DESCRIPTION:${icsEscape((row.source==='custom'?'Личная запись. ':'Из расписания вуза. ')+(row.teacher || ''))}`);
    if(row.time){lines.push(`DTSTART;TZID=Asia/Irkutsk:${day}T${row.time.replace(':','')}00`);if(row.end)lines.push(`DTEND;TZID=Asia/Irkutsk:${day}T${row.end.replace(':','')}00`);}
    else lines.push(`DTSTART;VALUE=DATE:${day}`);
    lines.push('END:VEVENT');
  }
  lines.push('END:VCALENDAR');downloadICS(lines,'esstu_session.ics');
}
function downloadICS(lines,name) {
  const folded=lines.map(line=>{let text='',width=0;for(const char of line){const length=new TextEncoder().encode(char).length;if(width+length>75){text+='\r\n ';width=1;}text+=char;width+=length;}return text;});
  const url=URL.createObjectURL(new Blob([folded.join('\r\n')+'\r\n'],{type:'text/calendar;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
let campusBuildings=[],campusSelection=null;
function buildCampusDirectory(rooms) {
  const buildings=new Map();
  for(const room of rooms){const label=decodeEsstuRoom(room.room)?.building;if(!label)continue;if(!buildings.has(label))buildings.set(label,[]);buildings.get(label).push(room.room);}
  return [...buildings].sort(([a],[b])=>a.localeCompare(b,'ru',{numeric:true})).map(([label,rooms])=>({label,rooms:[...new Set(rooms)].sort((a,b)=>a.localeCompare(b,'ru',{numeric:true}))}));
}
async function openCampusMapModal(building=null) {
  closeSimpleDialog('moreMenuModal');openSimpleDialog('campusMapModal');
  const status=document.getElementById('campusStatus');status.textContent='Загрузка аудиторий…';
  try{
    if(!roomDirectory){const response=await fetch(getApiUrl('/api/rooms'));if(!response.ok)throw Error();roomDirectory=await response.json();}
    campusBuildings=buildCampusDirectory(roomDirectory.rooms || []);campusSelection=building;
    renderCampusMap();status.textContent=campusBuildings.length?'Выберите корпус, чтобы найти его аудитории.':'В загруженных данных нет обозначений корпусов.';
  }catch{status.textContent='Не удалось загрузить аудитории. Повторите при подключении к сети.';}
}
function renderCampusMap() {
  const height=Math.max(100,Math.ceil(campusBuildings.length/3)*70+10);
  document.getElementById('campusDiagram').innerHTML=`<svg viewBox="0 0 420 ${height}" class="w-full h-auto" role="group" aria-label="Условная схема корпусов">${campusBuildings.map((building,index)=>{const x=10+(index%3)*138,y=10+Math.floor(index/3)*70,active=campusSelection===building.label;return `<g role="button" tabindex="0" aria-label="${escapeHTML(building.label)}" aria-pressed="${active}" onclick="selectCampusBuilding(${index})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectCampusBuilding(${index});}"><rect x="${x}" y="${y}" width="124" height="56" rx="10" fill="${active?'#0d9488':'currentColor'}" fill-opacity="${active?'1':'.06'}" stroke="${active?'#0d9488':'#64748b'}"/><text x="${x+62}" y="${y+24}" text-anchor="middle" fill="${active?'white':'currentColor'}" font-size="12" font-weight="600">${escapeHTML(building.label)}</text><text x="${x+62}" y="${y+43}" text-anchor="middle" fill="${active?'white':'currentColor'}" font-size="10">${building.rooms.length} ауд.</text></g>`;}).join('')}</svg>`;
  const selected=campusBuildings.find(building=>building.label===campusSelection);
  document.getElementById('campusBldCard').innerHTML=selected?`<h3 class="font-bold text-sm">${escapeHTML(selected.label)}</h3><p class="text-xs text-slate-500 mt-1">Корпус определён по обозначению аудитории в расписании.</p><div class="flex flex-wrap gap-2 mt-3">${selected.rooms.map((room,index)=>`<button class="px-3 rounded-xl bg-teal-500/10 text-teal-700 dark:text-teal-300 text-xs" onclick="campusRoom(${index})">${escapeHTML(room)}</button>`).join('')}</div>`:'';
}
function selectCampusBuilding(index){campusSelection=campusBuildings[index]?.label;renderCampusMap();document.querySelector('#campusDiagram [aria-pressed="true"]')?.focus();}
function campusRoom(index){const room=campusBuildings.find(building=>building.label===campusSelection)?.rooms[index];if(room){closeSimpleDialog('campusMapModal');openRoomsModal(room);}}
async function handleUrlShortcuts() {
  const action=new URLSearchParams(location.search).get('action');
  if(action==='rooms')await openRoomsModal();
  if(action==='session')setScheduleTab('session');
  if(action==='campus')await openCampusMapModal();
  if(action==='now'){bottomNavToday();document.getElementById('liveHeroCard').scrollIntoView({behavior:'smooth',block:'center'});}
}
