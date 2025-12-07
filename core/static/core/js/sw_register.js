/**
 * Service Worker Registration
 * Registers the service worker and handles updates
 */

(function () {
    'use strict';

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            registerServiceWorker();
        });
    } else {
        console.log('[SW] Service Workers are not supported');
    }

    async function registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register('/static/service-worker.js', {
                scope: '/'
            });

            console.log('[SW] Registration successful:', registration.scope);

            // Handle updates
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // New service worker available
                        showUpdateNotification(registration);
                    }
                });
            });

            // Check for updates periodically
            setInterval(() => {
                registration.update();
            }, 60 * 60 * 1000); // Every hour

        } catch (error) {
            console.error('[SW] Registration failed:', error);
        }
    }

    function showUpdateNotification(registration) {
        if (window.App && window.App.showToast) {
            // Create custom toast with action button
            const toast = document.createElement('div');
            toast.className = 'update-toast';
            toast.style.cssText = `
                position: fixed;
                bottom: 24px;
                left: 50%;
                transform: translateX(-50%);
                background: #10B981;
                color: white;
                padding: 16px 24px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10001;
                display: flex;
                align-items: center;
                gap: 16px;
            `;

            toast.innerHTML = `
                <span>🎉 New version available!</span>
                <button class="update-btn" style="
                    background: white;
                    color: #10B981;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: 600;
                    cursor: pointer;
                ">Update Now</button>
                <button class="dismiss-btn" style="
                    background: transparent;
                    color: white;
                    border: none;
                    padding: 8px;
                    cursor: pointer;
                    font-size: 18px;
                ">×</button>
            `;

            document.body.appendChild(toast);

            toast.querySelector('.update-btn').addEventListener('click', () => {
                // Tell service worker to skip waiting
                registration.waiting.postMessage({ type: 'SKIP_WAITING' });

                // Reload page when new SW takes over
                navigator.serviceWorker.addEventListener('controllerchange', () => {
                    window.location.reload();
                });
            });

            toast.querySelector('.dismiss-btn').addEventListener('click', () => {
                toast.remove();
            });
        } else {
            // Fallback to confirm dialog
            if (confirm('A new version is available. Reload to update?')) {
                registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                navigator.serviceWorker.addEventListener('controllerchange', () => {
                    window.location.reload();
                });
            }
        }
    }

    // Network status monitoring
    window.addEventListener('online', () => {
        console.log('[SW] Back online');
        if (window.App && window.App.showToast) {
            window.App.showToast('success', 'Online', 'Connection restored');
        }

        // Trigger background sync if supported
        if ('sync' in registration) {
            registration.sync.register('sync-actions');
        }
    });

    window.addEventListener('offline', () => {
        console.log('[SW] Offline mode');
        if (window.App && window.App.showToast) {
            window.App.showToast('warning', 'Offline', 'Working in offline mode');
        }
    });

    // Expose helper to clear cache
    window.clearServiceWorkerCache = async function () {
        if ('serviceWorker' in navigator) {
            const registration = await navigator.serviceWorker.ready;
            registration.active.postMessage({ type: 'CLEAR_CACHE' });
            console.log('[SW] Cache clear requested');
            return true;
        }
        return false;
    };

})();
