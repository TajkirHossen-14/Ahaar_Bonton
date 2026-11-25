const CACHE_NAME = 'ahaarbonton-v9';
const OFFLINE_PATH = '/offline/';
const STATIC_ASSETS = ['/static/css/style.css', '/static/js/main.js', OFFLINE_PATH];

self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)));
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    )));
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    if (request.method !== 'GET' || url.origin !== self.location.origin) return;

    if (url.pathname.startsWith('/static/')) {
        event.respondWith(caches.match(request).then(cached => {
            const network = fetch(request).then(response => {
                if (response.ok && response.type !== 'opaque') {
                    const clone = response.clone();
                    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.put(request, clone)));
                }
                return response;
            }).catch(() => cached || Response.error());
            if (cached) event.waitUntil(network);
            return cached || network;
        }));
        return;
    }

    // Application HTML can contain account details, so it is never stored.
    if (request.mode === 'navigate') {
        event.respondWith(fetch(request).catch(async () => (
            (await caches.match(OFFLINE_PATH)) || Response.error()
        )));
    }
});
