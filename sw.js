const CACHE = 'newsroom-shell-a6ef0e3779719313';
const ASSETS = ['./', './index.html', './style.css', './i18n.js', './learning.js', './app.js', './pwa.js', './manifest.webmanifest', './icon.svg', './icon-192.png', './icon-512.png'];
const allowed = new Set(ASSETS.map(path => new URL(path, self.registration.scope).href));
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('newsroom-shell-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
async function cachedResponse(cache, request) {
  const cached = await cache.match(request);
  if (!cached) return null;
  const headers = new Headers(cached.headers); headers.set('X-Newsroom-Offline', '1');
  return new Response(cached.body, { status: cached.status, headers });
}
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || !allowed.has(event.request.url)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(event.request);
      if (response.ok) { await cache.put(event.request, response.clone()); return response; }
      return await cachedResponse(cache, event.request) || response;
    } catch {
      return await cachedResponse(cache, event.request) || new Response('Offline. Reconnect to load this page.', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
    }
  })());
});
