const CACHE_NAME = 'esstu-live-__BUILD_ID__';
const CACHE_PREFIX = `esstu-pwa:${self.registration.scope}:`;
const SHELL_CACHE = `${CACHE_PREFIX}${CACHE_NAME}`;
const DATA_CACHE = `${CACHE_PREFIX}data-v2`;
const MAX_DATA_ENTRIES = 200;
const PIN_CACHE = `${CACHE_PREFIX}preferences-v1`;
const PIN_URL = new URL('offline-pins',self.registration.scope).href;
let protectedURLs = null;
async function loadPins(){if(!protectedURLs){const saved=await (await caches.open(PIN_CACHE)).match(PIN_URL);protectedURLs=new Set(saved?await saved.json():[]);}return protectedURLs;}
const SHELL = ['./', './index.html', './app.css', './shortcut-now.svg', './modern.js', './experience.js', './simple-ui.js', './study-tools.js', './accessibility.js', './manifest.json', './icons/app-icon.svg', './icons/app-icon-192.png', './icons/app-icon-512.png', './shortcut-now.png', './shortcut-rooms.png', './shortcut-session.png', './shortcut-campus.png'];
const SHELL_URLS = new Set(SHELL.map(path => new URL(path, self.registration.scope).href));
const API_URL = new URL('api/', self.registration.scope).href;
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(
    SHELL.map(path => new Request(new URL(path, self.registration.scope), {cache:'reload'}))
  )));
});
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') event.waitUntil(self.skipWaiting());
  if(event.data?.type==='PROTECT_DATA')event.waitUntil((async()=>{
    const urls=(event.data.urls || []).filter(url=>typeof url==='string' && url.startsWith(API_URL)).slice(0,64);
    protectedURLs=new Set(urls);await (await caches.open(PIN_CACHE)).put(PIN_URL,new Response(JSON.stringify(urls)));
  })());
});
async function trimData(cache) {
  const requests = await cache.keys();
  const pins=await loadPins();
  const victims=requests.filter(request=>!pins.has(request.url));
  // FIFO among unprotected responses; current/favourite endpoints are retained.
  await Promise.all(victims.slice(0,Math.max(0,requests.length-MAX_DATA_ENTRIES)).map(request=>cache.delete(request)));
}
// Serialize writes so simultaneous downloads cannot race the entry limit.
let dataWrite = Promise.resolve();
function saveData(cache, request, response) {
  dataWrite = dataWrite.catch(() => {}).then(async () => {
    const headers = new Headers(response.headers); headers.set('X-ESSTU-Schema', '2');
    await cache.put(request, new Response(response.body, {status:response.status,statusText:response.statusText,headers}));
    await trimData(cache);
  });
  return dataWrite;
}
async function fingerprint(response) {
  const etag=response.headers.get('ETag');
  if(etag)return 'etag:'+etag;
  const stored=response.headers.get('X-ESSTU-Content-Hash');
  if(stored)return stored;
  const digest=await crypto.subtle.digest('SHA-256',await response.clone().arrayBuffer());
  return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');
}
async function migrateData(response) {
  const payload = await response.json();
  if (!payload || typeof payload !== 'object') throw Error('Unsupported saved data');
  const markSchedule = schedule => {
    if (!schedule?.weeks) return;
    schedule.is_stale_fallback = true;
    schedule.source_mode = 'saved_snapshot';
    // Old data cannot establish that a teacher identity was checked.
    if (schedule.mode === 'teacher' && schedule.identity_ambiguous === undefined) schedule.identity_ambiguous = true;
  };
  markSchedule(payload);
  if (Array.isArray(payload.teachers)) payload.teachers.forEach(markSchedule);
  payload.schema_version = 2;
  const headers = new Headers(response.headers);
  headers.set('Content-Type','application/json; charset=utf-8');
  headers.delete('Content-Length'); headers.delete('Content-Encoding'); headers.delete('ETag');
  return new Response(JSON.stringify(payload), {status:response.status,headers});
}
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    const data = await caches.open(DATA_CACHE);
    const legacyKeys = keys.filter(key => key.startsWith('esstu-live-') || key === `${CACHE_PREFIX}data-v1`);
    for (const key of legacyKeys.reverse()) {
      const legacy = await caches.open(key); let migrated = true, shared = false;
      for (const request of await legacy.keys()) {
        if (!request.url.startsWith(self.registration.scope)) { shared = true; continue; }
        if (!request.url.startsWith(API_URL) || await data.match(request)) continue;
        try { await saveData(data, request, await migrateData(await legacy.match(request))); }
        catch (error) { migrated = false; console.warn('ESSTU cache migration failed', error); }
      }
      if (migrated && !shared) await caches.delete(key);
    }
    await trimData(data);
    // Keep failed migrations and caches containing another application's entries.
    await Promise.all(keys.filter(key => key.startsWith(CACHE_PREFIX) && key !== SHELL_CACHE && key !== DATA_CACHE && key !== PIN_CACHE && !legacyKeys.includes(key)).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || !url.href.startsWith(self.registration.scope)) return;
  const isData = url.href.startsWith(API_URL);
  const assetURL = new URL(url); assetURL.search = ''; assetURL.hash = '';
  const isShell = SHELL_URLS.has(assetURL.href);
  // Other assets follow normal HTTP caching, never shell cache-first.
  if (!isData && !isShell) return;
  const background=[];
  const result=(async () => {
    const cache=await caches.open(isData?DATA_CACHE:SHELL_CACHE);
    const shellURL=request.mode==='navigate'?new URL('./',self.registration.scope).href:assetURL.href;
    if(!isData){const shell=await cache.match(shellURL);if(shell)return shell;}
    const saved=isData?await cache.match(request):null;
    if(saved && request.headers.get('X-ESSTU-Cache-Only')==='1')return saved;
    const fetching=fetch(request,{cache:'reload',signal:AbortSignal.timeout(saved?60000:12000)}).then(async response=>{
      if(response.ok){
        try{
          let changed=false;
          if(isData){
            const hash=await fingerprint(response);
            changed=saved && await fingerprint(saved)!==hash;
            const headers=new Headers(response.headers);headers.set('X-ESSTU-Content-Hash',hash);
            await saveData(cache,request,new Response(response.clone().body,{status:response.status,statusText:response.statusText,headers}));
          }else await cache.put(shellURL,response.clone());
          if(changed)for(const client of await self.clients.matchAll({type:'window'}))client.postMessage({type:'DATA_UPDATED',url:request.url});
        }catch(error){console.warn('ESSTU cache write failed',error);}
      }
      return response;
    });
    // Keep a slow transfer alive after serving a saved response.
    background.push(fetching.catch(()=>{}));
    try{
      let response;
      if(saved){
        let timer;
        try{response=await Promise.race([fetching,new Promise(resolve=>{timer=setTimeout(()=>resolve(null),3500);})]);}
        finally{clearTimeout(timer);}
        if(!response)return cachedResponse(saved,'refreshing');
      }else response=await fetching;
      return saved && response.status>=500?cachedResponse(saved,'server-error'):response;
    }catch{return saved?cachedResponse(saved,'offline'):new Response('Нет сохранённой копии. Подключитесь к интернету.',{status:503});}
  })();
  event.respondWith(result);
  event.waitUntil(result.then(()=>Promise.all(background)).catch(()=>{}));
});

function cachedResponse(saved, reason) {
  const headers = new Headers(saved.headers); headers.set('X-ESSTU-Cache', reason);
  return new Response(saved.clone().body, {status:saved.status,statusText:saved.statusText,headers});
}
