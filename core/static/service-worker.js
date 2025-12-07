/**
 * Tracker Pro - Service Worker
 * Provides offline support and caching
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `tracker-static-${CACHE_VERSION}`;
const DATA_CACHE = `tracker-data-${CACHE_VERSION}`;
const OFFLINE_URL = '/offline/';

// Static assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/core/css/base.css',
    '/static/core/css/panels.css',
    '/static/core/js/api Client.js',
    '/static/core/js/app.js',
    '/static/core/js/analytics.js',
    '/static/core/js/goals_pagination.js',
    '/static/core/js/undo_manager.js',
    '/offline/',
    '/manifest.json'
];

// API endpoints to cache with network-first strategy
const API_ENDPOINTS = [
    '/api/v1/dashboard/',
    '/api/v1/tasks/',
    '/api/v1/goals/',
    '/api/v1/trackers/',
    '/api/v1/analytics/data/'
];

// =============================================================================
// INSTALL - Cache static assets
// =============================================================================
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Installing...');

    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            console.log('[ServiceWorker] Caching static assets');
            return cache.addAll(STATIC_ASSETS.map(url => new Request(url, { credentials: 'same-origin' })));
        }).catch((error) => {
            console.error('[ServiceWorker] Install failed:', error);
        })
    );

    // Activate immediately
    self.skipWaiting();
});

// =============================================================================
// ACTIVATE - Clean up old caches
// =============================================================================
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activating...');

    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== STATIC_CACHE && cacheName !== DATA_CACHE) {
                        console.log('[ServiceWorker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );

    // Take control immediately
    return self.clients.claim();
});

// =============================================================================
// FETCH - Handle requests with appropriate caching strategy
// =============================================================================
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip chrome extensions and external
    if (!url.origin.includes(self.location.origin)) {
        return;
    }

    // Strategy selection based on request type
    if (isAPIRequest(url)) {
        // API: Network-first with cache fallback
        event.respondWith(networkFirstStrategy(request));
    } else if (isStaticAsset(url)) {
        // Static assets: Cache-first
        event.respondWith(cacheFirstStrategy(request));
    } else {
        // HTML pages: Network-first with offline fallback
        event.respondWith(networkFirstWithOfflineStrategy(request));
    }
});

// =============================================================================
// CACHING STRATEGIES
// =============================================================================

/**
 * Network-first: Try network, fall back to cache
 * Best for API requests (fresh data preferred)
 */
async function networkFirstStrategy(request) {
    try {
        const response = await fetch(request);

        // Cache successful responses
        if (response && response.status === 200) {
            const cache = await caches.open(DATA_CACHE);
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        // Network failed, try cache
        const cached = await caches.match(request);
        if (cached) {
            console.log('[ServiceWorker] Serving from cache (offline):', request.url);
            return cached;
        }

        // No cache, return offline response
        return new Response(JSON.stringify({
            success: false,
            error: 'Offline - no cached data available',
            offline: true
        }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

/**
 * Cache-first: Try cache, fall back to network
 * Best for static assets (rarely change)
 */
async function cacheFirstStrategy(request) {
    const cached = await caches.match(request);

    if (cached) {
        return cached;
    }

    try {
        const response = await fetch(request);

        if (response && response.status === 200) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, response.clone());
        }

        return response;
    } catch (error) {
        console.error('[ServiceWorker] Fetch failed:', error);
        return new Response('Offline', { status: 503 });
    }
}

/**
 * Network-first with offline page fallback
 * Best for HTML pages
 */
async function networkFirstWithOfflineStrategy(request) {
    try {
        return await fetch(request);
    } catch (error) {
        // Serve offline page
        const cached = await caches.match(OFFLINE_URL);
        if (cached) {
            return cached;
        }

        return new Response('Offline', {
            status: 503,
            headers: { 'Content-Type': 'text/html' }
        });
    }
}

// =============================================================================
// HELPERS
// =============================================================================

function isAPIRequest(url) {
    return url.pathname.startsWith('/api/');
}

function isStaticAsset(url) {
    const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.svg', '.woff', '.woff2', '.ttf'];
    return staticExtensions.some(ext => url.pathname.endsWith(ext)) ||
        url.pathname.startsWith('/static/');
}

// =============================================================================
// BACKGROUND SYNC (for offline actions)
// =============================================================================

self.addEventListener('sync', (event) => {
    console.log('[ServiceWorker] Background sync:', event.tag);

    if (event.tag === 'sync-actions') {
        event.waitUntil(syncPendingActions());
    }
});

async function syncPendingActions() {
    // Get pending actions from IndexedDB or localStorage
    // This would sync task completions, creates, updates made while offline

    console.log('[ServiceWorker] Syncing pending actions...');

    // Implementation would:
    // 1. Read pending actions from local storage
    // 2. POST each to server
    // 3. Remove successful ones
    // 4. Keep failed ones for retry

    // For now, just log (full implementation requires IndexedDB setup)
    return Promise.resolve();
}

// =============================================================================
// MESSAGE HANDLER
// =============================================================================

self.addEventListener('message', (event) => {
    console.log('[ServiceWorker] Message received:', event.data);

    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => caches.delete(cacheName))
                );
            })
        );
    }
});

console.log('[ServiceWorker] Loaded');
