const CACHE_NAME = 'esstu-live-v2.4.0';
const SHELL = ['./', './index.html', './modern.js', './experience.js', './simple-ui.js', './manifest.json'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL)));
});
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith('esstu-') && key !== CACHE_NAME).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    try {
      const response = await fetch(request, {cache: 'no-cache', signal: AbortSignal.timeout(12000)});
      if (!response.ok) {
        const saved = await cache.match(request, {ignoreSearch:true});
        if (saved) return cachedResponse(saved);
        return response;
      }
      await cache.put(request, response.clone());
      return response;
    } catch {
      const saved = await cache.match(request, {ignoreSearch:true}) ||
        (request.mode === 'navigate' ? await cache.match(new URL('./', self.registration.scope)) : null);
      return saved ? cachedResponse(saved) : new Response('Нет сохранённой копии. Подключитесь к интернету.', {status:503});
    }
  })());
});
function cachedResponse(saved) {
  const headers = new Headers(saved.headers); headers.set('X-ESSTU-Cache', 'offline');
  return new Response(saved.body, {status:saved.status,statusText:saved.statusText,headers});
}
