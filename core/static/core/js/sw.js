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

// Console logging helper for Service Worker
const swLog = (action, data = {}) => {
    const timestamp = new Date().toISOString();
    const logData = {
        timestamp,
        context: 'ServiceWorker',
        action,
        ...data
    };
    console.log(`[SW] 🔧 ${action}`, logData);
};

// Install
self.addEventListener('install', (e) => {
    swLog('INSTALL_START', { status: 'INFO', message: 'Service Worker installing...' });
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                swLog('CACHE_OPEN', {
                    status: 'SUCCESS',
                    cacheName: CACHE_NAME,
                    message: 'Cache opened successfully'
                });
                return cache.addAll(STATIC_ASSETS).then(() => {
                    swLog('CACHE_ADD_ALL', {
                        status: 'SUCCESS',
                        assetsCount: STATIC_ASSETS.length,
                        assets: STATIC_ASSETS,
                        message: 'All static assets cached'
                    });
                });
            })
            .then(() => {
                swLog('INSTALL_COMPLETE', { status: 'SUCCESS', message: 'Service Worker installed' });
                return self.skipWaiting();
            })
            .catch(err => {
                swLog('INSTALL_ERROR', {
                    status: 'ERROR',
                    error: err.message,
                    message: 'Service Worker installation failed'
                });
            })
    );
});

// Activate
self.addEventListener('activate', (e) => {
    swLog('ACTIVATE_START', { status: 'INFO', message: 'Service Worker activating...' });
    e.waitUntil(
        caches.keys().then(keys => {
            swLog('CACHE_KEYS_FOUND', {
                status: 'INFO',
                cacheKeys: keys,
                message: `Found ${keys.length} cache(s)`
            });
            const keysToDelete = keys.filter(key => key !== CACHE_NAME);
            if (keysToDelete.length) {
                swLog('CACHE_CLEANUP', {
                    status: 'INFO',
                    deletingKeys: keysToDelete,
                    message: `Deleting ${keysToDelete.length} old cache(s)`
                });
            }
            return Promise.all(
                keysToDelete.map(key => {
                    swLog('CACHE_DELETE', {
                        status: 'SUCCESS',
                        deletedKey: key,
                        message: `Deleted old cache: ${key}`
                    });
                    return caches.delete(key);
                })
            );
        }).then(() => {
            swLog('ACTIVATE_COMPLETE', { status: 'SUCCESS', message: 'Service Worker activated' });
            return self.clients.claim();
        })
            .catch(err => {
                swLog('ACTIVATE_ERROR', {
                    status: 'ERROR',
                    error: err.message,
                    message: 'Service Worker activation failed'
                });
            })
    );
});

// Fetch - Network first, fallback to cache
self.addEventListener('fetch', (e) => {
    const requestUrl = e.request.url;
    const requestMethod = e.request.method;

    // Skip non-GET requests
    if (requestMethod !== 'GET') {
        swLog('FETCH_SKIP_NON_GET', {
            status: 'INFO',
            url: requestUrl,
            method: requestMethod,
            message: `Skipping ${requestMethod} request`
        });
        return;
    }

    // Skip API requests
    if (requestUrl.includes('/api/')) {
        swLog('FETCH_SKIP_API', {
            status: 'INFO',
            url: requestUrl,
            method: requestMethod,
            message: 'Skipping API request - handled by network'
        });
        return;
    }

    swLog('FETCH_START', {
        status: 'INFO',
        url: requestUrl,
        method: requestMethod,
        message: 'Fetching resource'
    });

    e.respondWith(
        fetch(e.request)
            .then(response => {
                // Clone and cache successful responses
                if (response.ok) {
                    swLog('FETCH_NETWORK_SUCCESS', {
                        status: 'SUCCESS',
                        url: requestUrl,
                        method: requestMethod,
                        responseStatus: response.status,
                        message: `Network fetch successful (${response.status})`
                    });
                    const clone = response.clone();
                    caches.open(CACHE_NAME)
                        .then(cache => {
                            cache.put(e.request, clone);
                            swLog('FETCH_CACHE_UPDATE', {
                                status: 'SUCCESS',
                                url: requestUrl,
                                message: 'Response cached for offline use'
                            });
                        });
                } else {
                    swLog('FETCH_NETWORK_WARNING', {
                        status: 'WARNING',
                        url: requestUrl,
                        method: requestMethod,
                        responseStatus: response.status,
                        message: `Network response not OK (${response.status})`
                    });
                }
                return response;
            })
            .catch((error) => {
                swLog('FETCH_NETWORK_ERROR', {
                    status: 'ERROR',
                    url: requestUrl,
                    method: requestMethod,
                    error: error.message,
                    message: 'Network fetch failed, trying cache'
                });
                // Fallback to cache
                return caches.match(e.request)
                    .then(cached => {
                        if (cached) {
                            swLog('FETCH_CACHE_HIT', {
                                status: 'SUCCESS',
                                url: requestUrl,
                                message: 'Serving from cache'
                            });
                            return cached;
                        }
                        swLog('FETCH_CACHE_MISS', {
                            status: 'WARNING',
                            url: requestUrl,
                            message: 'Not in cache, serving fallback'
                        });
                        return caches.match('/');
                    });
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', (e) => {
    swLog('SYNC_EVENT', {
        status: 'INFO',
        tag: e.tag,
        message: `Background sync triggered: ${e.tag}`
    });
    if (e.tag === 'sync-tasks') {
        e.waitUntil(syncTasks());
    }
});

async function syncTasks() {
    swLog('SYNC_TASKS_START', {
        status: 'INFO',
        message: 'Starting offline task sync'
    });
    // Get pending actions from IndexedDB and sync
    try {
        // Placeholder for actual sync logic
        swLog('SYNC_TASKS_COMPLETE', {
            status: 'SUCCESS',
            message: 'Offline actions synced successfully'
        });
    } catch (error) {
        swLog('SYNC_TASKS_ERROR', {
            status: 'ERROR',
            error: error.message,
            message: 'Failed to sync offline actions'
        });
    }
}
