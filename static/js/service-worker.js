const CACHE_NAME = 'ahaarbonton-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/login/',
    '/transparency/',
];

// Install: cache static assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate: clear old caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

// Fetch: serve from cache if offline
self.addEventListener('fetch', event => {
    // Only handle GET requests
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then(response => {
                // Cache successful responses
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(
                        event.request, responseClone
                    );
                });
                return response;
            })
            .catch(() => {
                // Offline: serve from cache
                return caches.match(event.request)
                    .then(cached => {
                        if (cached) return cached;
                        // Show offline page
                        return caches.match('/offline/');
                    });
            })
    );
});
