const CACHE_NAME = 'ahaarbonton-v12';
const OFFLINE_PATH = '/offline/';
const OFFLINE_CACHE_PREFIX = 'ahaarbonton-offline-v12-';
const SUPPORTED_LANGUAGES = ['bn', 'en'];
const FONT_ASSETS = [];
const STATIC_ASSETS = ['/static/css/style.css', '/static/js/main.js', ...FONT_ASSETS];

function offlineCacheKey(language) {
    return OFFLINE_CACHE_PREFIX + language;
}

function fetchOffline(language) {
    return fetch(OFFLINE_PATH, {
        credentials: 'omit',
        headers: { 'Accept-Language': language }
    }).then(response => {
        if (!response.ok) throw new Error('Could not cache the offline page.');
        return response;
    });
}

function cacheOffline(cache, language) {
    return fetchOffline(language).then(response => cache.put(offlineCacheKey(language), response));
}

function preferredLanguage(request) {
    const cookie = request.headers.get('cookie') || '';
    const languageCookie = cookie.match(/(?:^|;\s*)django_language=(bn|en)(?:;|$)/);
    if (languageCookie) return languageCookie[1];
    const accepted = (request.headers.get('accept-language') || '').split(',')[0].split('-')[0].toLowerCase();
    return SUPPORTED_LANGUAGES.includes(accepted) ? accepted : 'bn';
}

self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => (
        cache.addAll(STATIC_ASSETS).then(() => Promise.all(
            SUPPORTED_LANGUAGES.map(language => cacheOffline(cache, language))
        ))
    )));
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(caches.keys().then(keys => Promise.all(
        keys.filter(key => key !== CACHE_NAME && !key.startsWith(OFFLINE_CACHE_PREFIX))
            .map(key => caches.delete(key))
    )));
    self.clients.claim();
});

self.addEventListener('message', event => {
    if (!event.data || event.data.type !== 'CACHE_OFFLINE') return;
    const language = SUPPORTED_LANGUAGES.includes(event.data.language) ? event.data.language : 'bn';
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cacheOffline(cache, language)));
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
        event.respondWith(fetch(request).catch(async () => {
            const language = preferredLanguage(request);
            return (await caches.match(offlineCacheKey(language)))
                || (await caches.match(offlineCacheKey('bn')))
                || Response.error();
        }));
    }
});
