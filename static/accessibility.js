// One focus stack for all modal dialogs, including nested dialogs and notes.
const modalStack=[];
function visibleControls(dialog){return [...dialog.querySelectorAll('button,a[href],input,textarea,select,summary,[tabindex]:not([tabindex="-1"])')].filter(node=>!node.disabled && !node.closest('[inert]') && node.getClientRects().length);}
function updateModalBackground(){
  const top=modalStack.at(-1)?.dialog;
  for(const child of document.body.children){
    if(child.tagName==='SCRIPT')continue;
    child.inert=!!top && child!==top && !child.contains(top);
  }
  document.body.style.overflow=top?'hidden':'';
}
function presentDialog(id){
  const dialog=document.getElementById(id);if(!dialog)return;
  if(!modalStack.some(entry=>entry.dialog===dialog))modalStack.push({dialog,launcher:document.activeElement});
  const inner=dialog.querySelector('[role="dialog"]');if(inner){inner.removeAttribute('role');inner.removeAttribute('aria-modal');}
  const title=dialog.querySelector('h2,h3');if(title){title.id ||=id+'Title';dialog.setAttribute('aria-labelledby',title.id);}
  dialog.tabIndex=-1;
  for(const button of dialog.querySelectorAll('button'))if(/^[×✕]$/.test(button.textContent.trim())){button.setAttribute('aria-label',button.getAttribute('aria-label') || 'Закрыть окно');button.innerHTML=uiIcon('close');}
  dialog.classList.remove('hidden');dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');
  updateModalBackground();
  (visibleControls(dialog)[0] || dialog).focus();
}
function dismissDialog(id){
  const index=modalStack.findIndex(entry=>entry.dialog.id===id);
  const entry=index>=0?modalStack.splice(index,1)[0]:null;
  document.getElementById(id)?.classList.add('hidden');updateModalBackground();
  const top=modalStack.at(-1)?.dialog;
  if(entry?.launcher?.isConnected && entry.launcher.getClientRects().length && !entry.launcher.closest('[inert]'))entry.launcher.focus();
  else if(top)(visibleControls(top)[0] || top).focus();
  const command=entry?.launcher?.getAttribute('onclick');
  if(command)queueMicrotask(()=>{if(!entry.launcher.isConnected && document.activeElement===document.body){const replacement=[...document.querySelectorAll('button[onclick]')].find(button=>button.getAttribute('onclick')===command && !button.closest('[inert]'));replacement?.focus();}});
}
document.addEventListener('keydown',event=>{
  const dialog=modalStack.at(-1)?.dialog;if(!dialog)return;
  if(event.key==='Escape'){
    event.preventDefault();event.stopImmediatePropagation();
    if(dialog.id==='noteModal')closeNoteModal();else closeSimpleDialog(dialog.id);
  }else if(event.key==='Tab'){
    const controls=visibleControls(dialog),first=controls[0],last=controls.at(-1);
    if(!first){event.preventDefault();dialog.focus();return;}
    if(event.shiftKey && (document.activeElement===first || !dialog.contains(document.activeElement))){event.preventDefault();last.focus();}
    else if(!event.shiftKey && (document.activeElement===last || !dialog.contains(document.activeElement))){event.preventDefault();first.focus();}
  }
},true);

function scheduleSkeleton(){return `<div class="schedule-skeleton" role="status" aria-label="Загрузка расписания"><span class="sr-only">Загрузка расписания…</span>${Array.from({length:3},()=>'<div class="skeleton-card" aria-hidden="true"><i></i><i></i><i></i></div>').join('')}</div>`;}
let scheduleLoadVersion=0;
let startupLinkFailed=false;
function beginScheduleLoad(){
  startupLinkFailed=false;
  const version=++scheduleLoadVersion;
  const container=document.getElementById('pairsContainer');container.setAttribute('aria-busy','true');container.innerHTML=scheduleSkeleton();
  document.getElementById('heroLessons').textContent='Загрузка расписания…';
  return version;
}
function finishScheduleLoad(version){if(version===scheduleLoadVersion)document.getElementById('pairsContainer').setAttribute('aria-busy','false');}
function scheduleUnavailable(message){
  document.getElementById('dayTabs').replaceChildren();
  document.getElementById('selectedDaySummary').textContent='';
  document.getElementById('daySourceStatus').textContent='Источник недоступен';
  document.getElementById('heroNextPairRow').classList.add('hidden');
  document.getElementById('heroProgressWrap').classList.add('hidden');
  document.getElementById('heroLessons').textContent=message;
  document.getElementById('pairsContainer').innerHTML=`<div class="empty-state" role="status"><p class="font-semibold">${escapeHTML(message)}</p><p class="mt-2 text-sm text-slate-500">Проверьте соединение или выберите другое расписание.</p><button class="mt-3 px-4 rounded-xl bg-teal-600 text-white" onclick="retryScheduleLoad()">Повторить</button><button class="mt-3 px-4 rounded-xl" onclick="openSearchModal()">Выбрать расписание</button></div>`;
}
function retryScheduleLoad(){if(startupLinkFailed){location.reload();return;}return appMode==='teacher'?loadTeacherSchedule(savedState.teacherKey,savedState.teacherCafId,true):loadStudentSchedule(savedState.section,savedState.groupId,savedState.groupName,true);}
function relativeChecked(value,now=Date.now()){
  const stamp=Date.parse(value);if(!Number.isFinite(stamp))return 'Дата проверки неизвестна';
  const minutes=Math.floor((now-stamp)/60000);
  if(minutes<0)return 'Проверено '+displayDate(value);
  if(minutes<60)return minutes<1?'Проверено только что':`Проверено ${minutes} мин назад`;
  return `Проверено ${Math.floor(minutes/60)} ч назад`;
}
function daySourceText(schedule,delivery,online=true){
  const offline=!online || delivery?.cached;
  const source=schedule.partial?'Расписания групп':'Портал ВСГУТУ';
  return `${offline?'Офлайн-копия · ':''}${source} · ${relativeChecked(schedule.source_checked_at)}`;
}
function renderDaySource(){
  const target=document.getElementById('daySourceStatus');if(!target || !currentSchedule)return;
  target.textContent=daySourceText(currentSchedule,lastDelivery,navigator.onLine);
}

// Decorative SVG replaces emoji without changing source data or button names.
const ICON_PATHS={
  calendar:'M5 4h14v16H5z M8 2v4m8-4v4M5 9h14',
  person:'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-2a8 8 0 0 1 16 0v2',
  pin:'M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 14 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  star:'m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z',
  clock:'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM12 6v6l4 2',
  note:'M5 3h14v18H5z M8 8h8m-8 4h8m-8 4h5',
  door:'M4 21h16M7 21V3l10 2v16M13 12h1',
  link:'m9 15 6-6M8 17H6a4 4 0 0 1-3-7l4-4a4 4 0 0 1 6 0m-2 12a4 4 0 0 0 6 0l4-4a4 4 0 0 0-3-7h-2',
  refresh:'M20 7v5h-5M4 17v-5h5M5 8a8 8 0 0 1 13-3l2 3M4 16l2 3a8 8 0 0 0 13-3',
  building:'M3 21h18M5 21V8h14v13M3 8l9-5 9 5M9 11v7m6-7v7',
  check:'m4 12 5 5L20 6', warning:'m12 3 10 18H2ZM12 9v5m0 3v1',
  info:'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0ZM12 11v6m0-10v1',chevron:'m7 10 5 5 5-5',
  dot:'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z', close:'m6 6 12 12M6 18 18 6', more:'M4 12h1m6 0h1m6 0h1'
};
function uiIcon(name){return `<svg class="ui-icon" aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="${ICON_PATHS[name] || ICON_PATHS.dot}"/></svg>`;}
const EMOJI_ICONS={'ⓘ':'info','⌄':'chevron','🎓':'building','👨‍🏫':'person','👥':'person','📍':'pin','🏛':'building','⭐':'star','☆':'star','🌙':'dot','☀️':'dot','💻':'dot','📅':'calendar','🗂':'calendar','🚪':'door','📆':'calendar','🔗':'link','⏱':'clock','📝':'note','✏️':'note','📌':'note','⚡':'dot','🔄':'refresh','💾':'note','🌐':'link','🚀':'dot','🎉':'check','✅':'check','⚠️':'warning','☕':'clock','🍽':'clock','⏳':'clock','🏃':'pin','🟢':'dot','🔴':'dot','⚪':'dot','⏭':'clock','⏰':'clock','🌴':'dot'};
const emojiPattern=new RegExp(Object.keys(EMOJI_ICONS).sort((a,b)=>b.length-a.length).join('|'),'gu');
function replaceDecorativeIcons(root){
  if(root.nodeType===1 && (root.closest('script,style,svg,textarea,option,title,.whitespace-pre-wrap') || root.matches('script,style,svg,textarea,option,title,.whitespace-pre-wrap')))return;
  const nodes=root.nodeType===3?[root]:[...function*(){const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);while(walker.nextNode())yield walker.currentNode;}()];
  for(const node of nodes){
    if(!node.parentElement || node.parentElement.closest('script,style,svg,textarea,option,title,.whitespace-pre-wrap'))continue;
    const matches=[...node.data.matchAll(emojiPattern)];if(!matches.length)continue;
    const fragment=document.createDocumentFragment();let offset=0;
    for(const match of matches){fragment.append(document.createTextNode(node.data.slice(offset,match.index)));const span=document.createElement('span');span.innerHTML=uiIcon(EMOJI_ICONS[match[0]]);fragment.append(span.firstChild);offset=match.index+match[0].length;}
    fragment.append(document.createTextNode(node.data.slice(offset)));node.replaceWith(fragment);
  }
}
document.addEventListener('DOMContentLoaded',()=>{
  for(const dialog of document.querySelectorAll('[role="dialog"],#noteModal,#roomsModal')){
    dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.tabIndex=-1;
    const title=dialog.querySelector('h2,h3');if(title){title.id ||=dialog.id+'Title';dialog.setAttribute('aria-labelledby',title.id);}
    for(const button of dialog.querySelectorAll('button'))if(/^[×✕]$/.test(button.textContent.trim())){button.setAttribute('aria-label',button.getAttribute('aria-label') || 'Закрыть окно');button.innerHTML=uiIcon('close');}
  }
  document.querySelector('button[aria-label="Ещё"]').innerHTML=uiIcon('more');
  document.getElementById('groupSearchInput').setAttribute('aria-label','Поиск учебной группы');
  document.getElementById('teacherSearchInput').setAttribute('aria-label','Поиск преподавателя');
  document.getElementById('noteTextarea').setAttribute('aria-label','Текст заметки');
  document.getElementById('dayTabs').setAttribute('aria-label','Дни недели');
  document.querySelector('body > nav')?.setAttribute('aria-label','Основная навигация');
  replaceDecorativeIcons(document.body);
  new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes)replaceDecorativeIcons(node);}).observe(document.body,{childList:true,subtree:true});
  setInterval(renderDaySource,60000);window.addEventListener('online',renderDaySource);window.addEventListener('offline',renderDaySource);
});
