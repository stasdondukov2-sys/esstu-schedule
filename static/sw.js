const CACHE_NAME = 'esstu-live-v2.4.0';
const CACHE_PREFIX = `esstu-pwa:${self.registration.scope}:`;
const SHELL_CACHE = `${CACHE_PREFIX}${CACHE_NAME}`;
const DATA_CACHE = `${CACHE_PREFIX}data-v1`;
const SHELL = ['./', './index.html', './app.css', './shortcut-now.svg', './modern.js', './experience.js', './simple-ui.js', './study-tools.js', './accessibility.js', './manifest.json', './shortcut-now.png', './shortcut-rooms.png', './shortcut-session.png', './shortcut-campus.png'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL)));
});
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') event.waitUntil(self.skipWaiting());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    const data = await caches.open(DATA_CACHE);
    const apiURL = new URL('api/', self.registration.scope).href;
    // Migrate this scope's data from the previous, combined shell/data caches.
    for (const key of keys.filter(key => key.startsWith('esstu-live-')).reverse()) {
      const legacy = await caches.open(key);
      for (const request of await legacy.keys()) {
        if (request.url.startsWith(apiURL) && !(await data.match(request))) {
          try { await data.put(request, await legacy.match(request)); }
          catch (error) { console.warn('ESSTU cache migration failed', error); }
        }
      }
    }
    // Retain data across shell updates. Never delete another application's caches.
    await Promise.all(keys.filter(key => key.startsWith(CACHE_PREFIX) && key !== SHELL_CACHE && key !== DATA_CACHE).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || !url.href.startsWith(self.registration.scope)) return;
  event.respondWith((async () => {
    const isData = url.pathname.startsWith(new URL('api/', self.registration.scope).pathname);
    const cache = await caches.open(isData ? DATA_CACHE : SHELL_CACHE);
    // A controlled page uses one installed shell until the user accepts its update.
    // Search parameters select schedules, but do not change the HTML shell.
    const shellURL = request.mode === 'navigate' ? new URL('./', self.registration.scope).href : url.href;
    if (!isData) {
      const shell = await cache.match(shellURL, {ignoreSearch: true});
      if (shell) return shell;
    }
    try {
      const response = await fetch(request, {cache: 'no-cache', signal: AbortSignal.timeout(12000)});
      if (!response.ok) {
        const saved = response.status >= 500 ? await cache.match(request) : null;
        if (saved) return cachedResponse(saved);
        return response;
      }
      // Storage quota failures must not hide a successful network response.
      try { await cache.put(request, response.clone()); } catch (error) { console.warn('ESSTU cache write failed', error); }
      return response;
    } catch {
      const saved = await cache.match(request) ||
        (request.mode === 'navigate' ? await cache.match(new URL('./', self.registration.scope)) : null);
      return saved ? cachedResponse(saved) : new Response('Нет сохранённой копии. Подключитесь к интернету.', {status:503});
    }
  })());
});
function cachedResponse(saved) {
  const headers = new Headers(saved.headers); headers.set('X-ESSTU-Cache', 'offline');
  return new Response(saved.body, {status:saved.status,statusText:saved.statusText,headers});
}
