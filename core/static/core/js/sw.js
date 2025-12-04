const CACHE_NAME = 'tracker-pro-v2';
const STATIC_ASSETS = [
    '/',
    '/static/core/css/themes.css',
    '/static/core/css/components.css',
    '/static/core/css/spa.css',
    '/static/core/js/app.js',
    '/static/core/js/panels.js',
    '/static/core/js/interactive.js',
    '/static/core/js/analytics.js',
    '/static/core/js/polish.js'
];

// Install
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch - Network first, fallback to cache
self.addEventListener('fetch', (e) => {
    // Skip non-GET requests
    if (e.request.method !== 'GET') return;

    // Skip API requests
    if (e.request.url.includes('/api/')) return;

    e.respondWith(
        fetch(e.request)
            .then(response => {
                // Clone and cache successful responses
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => cache.put(e.request, clone));
                }
                return response;
            })
            .catch(() => {
                // Fallback to cache
                return caches.match(e.request)
                    .then(cached => cached || caches.match('/'));
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', (e) => {
    if (e.tag === 'sync-tasks') {
        e.waitUntil(syncTasks());
    }
});

async function syncTasks() {
    // Get pending actions from IndexedDB and sync
    console.log('Syncing offline actions...');
}
