/**
 * Router Module
 * Handles client-side routing with AJAX panel loading
 */

import { ajax } from '../utils/ajax.js';

export class Router {
    constructor(app) {
        this.app = app;
        this.currentPanel = null;
        this.panelCache = new Map();
        this.cacheEnabled = true;
        this.maxCacheSize = 10;
    }

    /**
     * Initialize router
     */
    async init() {
        // Load initial panel based on current URL
        const path = window.location.pathname;
        await this.loadPanel(path, false);
    }

    /**
     * Navigate to a URL
     */
    async navigate(url, pushState = true) {
        // Update browser history
        if (pushState) {
            window.history.pushState(
                { panel: this.getPanelName(url), url },
                '',
                url
            );
        }

        // Load the panel
        await this.loadPanel(url, pushState);
    }

    /**
     * Load panel content via AJAX
     */
    async loadPanel(url, updateHistory = true) {
        try {
            // Convert URL to panel URL if needed
            const panelUrl = this.toPanelUrl(url);

            // Check cache first
            if (this.cacheEnabled && this.panelCache.has(panelUrl)) {
                this.renderPanel(this.panelCache.get(panelUrl), panelUrl);
                return;
            }

            // Show loading state
            this.app.showLoading();

            // Load skeleton first for perceived performance
            const skeletonUrl = `${panelUrl}${panelUrl.includes('?') ? '&' : '?'}skeleton=true`;
            const skeletonHtml = await ajax.get(skeletonUrl).catch(() => null);

            if (skeletonHtml) {
                this.renderPanel(skeletonHtml, panelUrl, true);
            }

            // Load actual content
            const html = await ajax.get(panelUrl);

            // Cache the result
            if (this.cacheEnabled) {
                this.addToCache(panelUrl, html);
            }

            // Render the panel
            this.renderPanel(html, panelUrl);

            // Hide loading state
            this.app.hideLoading();

        } catch (error) {
            console.error('Failed to load panel:', error);
            this.app.hideLoading();

            // Load error panel
            this.loadErrorPanel(error.status || 500);
        }
    }

    /**
     * Render panel HTML into main content area
     */
    renderPanel(html, url, isSkeleton = false) {
        const container = document.getElementById('panel-content') ||
            document.getElementById('main-content');

        if (!container) {
            console.error('Panel container not found');
            return;
        }

        // Update content
        container.innerHTML = html;

        // Update active nav item
        this.updateActiveNav(url);

        // Scroll to top
        container.scrollTop = 0;
        window.scrollTo(0, 0);

        // Announce to screen readers
        if (!isSkeleton) {
            this.announcePageChange(this.getPanelName(url));
        }

        // Re-initialize interactive elements
        if (!isSkeleton) {
            this.initializePanelElements();
        }

        // Update current panel
        this.currentPanel = url;
    }

    /**
     * Initialize interactive elements in loaded panel
     */
    initializePanelElements() {
        // Re-init dropdowns
        this.app.dropdowns?.initPanelDropdowns();

        // Re-init swipe gestures
        if (this.app.isIOS()) {
            this.app.swipe?.initPanelSwipes();
        }

        // Re-init forms
        this.app.forms?.initPanelForms();

        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('panelLoaded', {
            detail: { url: this.currentPanel }
        }));
    }

    /**
     * Update active navigation item
     */
    updateActiveNav(url) {
        // Remove all active classes
        document.querySelectorAll('.nav-item, .sidebar-nav a').forEach(item => {
            item.classList.remove('active');
        });

        // Add active to matching item
        const panelName = this.getPanelName(url);
        const activeItem = document.querySelector(
            `.nav-item[data-panel="${panelName}"], .sidebar-nav a[data-panel="${panelName}"]`
        );

        if (activeItem) {
            activeItem.classList.add('active');
        }
    }

    /**
     * Load error panel
     */
    async loadErrorPanel(status) {
        const errorUrl = `/panels/error/${status}/`;
        try {
            const html = await ajax.get(errorUrl);
            this.renderPanel(html, errorUrl);
        } catch (err) {
            // Fallback error display
            const container = document.getElementById('panel-content');
            if (container) {
                container.innerHTML = `
                    <div class="empty-state">
                        <h2>Error ${status}</h2>
                        <p>Something went wrong. Please try again.</p>
                        <button class="btn btn-primary" onclick="window.location.reload()">Reload</button>
                    </div>
                `;
            }
        }
    }

    /**
     * Convert regular URL to panel URL
     */
    toPanelUrl(url) {
        // Already a panel URL
        if (url.startsWith('/panels/')) {
            return url;
        }

        // Map URLs to panel endpoints
        const urlMap = {
            '/': '/panels/dashboard/',
            '/today/': '/panels/today/',
            '/week/': '/panels/week/',
            '/month/': '/panels/month/',
            '/trackers/': '/panels/trackers/',
            '/analytics/': '/panels/analytics/',
            '/goals/': '/panels/goals/',
            '/insights/': '/panels/insights/',
            '/templates/': '/panels/templates/',
            '/help/': '/panels/help/',
            '/settings/': '/panels/settings/'
        };

        // Check direct mapping
        if (urlMap[url]) {
            return urlMap[url];
        }

        // Handle tracker detail URLs
        if (url.match(/^\/tracker\/[\w-]+\/$/)) {
            return url.replace('/tracker/', '/panels/tracker/');
        }

        // Default: prepend /panels/
        return `/panels${url}`;
    }

    /**
     * Get panel name from URL
     */
    getPanelName(url) {
        const match = url.match(/\/panels?\/([\w-]+)/);
        return match ? match[1] : 'dashboard';
    }

    /**
     * Add to cache with LRU eviction
     */
    addToCache(url, html) {
        if (this.panelCache.size >= this.maxCacheSize) {
            // Remove oldest entry
            const firstKey = this.panelCache.keys().next().value;
            this.panelCache.delete(firstKey);
        }
        this.panelCache.set(url, html);
    }

    /**
     * Clear cache
     */
    clearCache() {
        this.panelCache.clear();
    }

    /**
     * Reload current panel
     */
    async reload() {
        if (this.currentPanel) {
            this.panelCache.delete(this.currentPanel);
            await this.loadPanel(this.currentPanel, false);
        }
    }

    /**
     * Announce page change to screen readers
     */
    announcePageChange(panelName) {
        const announcement = document.getElementById('aria-announcer') ||
            this.createAnnouncer();
        announcement.textContent = `Navigated to ${panelName} panel`;
    }

    /**
     * Create ARIA live region for announcements
     */
    createAnnouncer() {
        const announcer = document.createElement('div');
        announcer.id = 'aria-announcer';
        announcer.setAttribute('role', 'status');
        announcer.setAttribute('aria-live', 'polite');
        announcer.style.position = 'absolute';
        announcer.style.left = '-10000px';
        announcer.style.width = '1px';
        announcer.style.height = '1px';
        announcer.style.overflow = 'hidden';
        document.body.appendChild(announcer);
        return announcer;
    }
}
