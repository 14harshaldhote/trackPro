/**
 * Tracker Pro - SPA Controller
 * Handles navigation, modals, toasts, and global state
 * With comprehensive console logging
 */

// Console logging helper for App
const appLog = (module, action, data = {}) => {
    const emoji = data.status === 'SUCCESS' ? '✅' : data.status === 'ERROR' ? '❌' : data.status === 'WARNING' ? '⚠️' : 'ℹ️';
    console.log(`[App/${module}] ${emoji} ${action}`, { timestamp: new Date().toISOString(), module, action, ...data });
};

// ============================================================================
// APP STATE & CONFIG
// ============================================================================
const App = {
    state: {
        currentPanel: 'dashboard',
        currentTracker: null,
        sidebarOpen: true,
        sidebarCollapsed: false,
        activeModal: null,
        isLoading: false,
        isOnline: navigator.onLine,
        keyBuffer: '',
        keyTimeout: null,
        searchSelectedIndex: -1
    },

    // Cache for panels and API responses
    cache: {
        panels: new Map(),
        data: new Map(),
        maxAge: 5 * 60 * 1000 // 5 minutes
    },

    config: window.TrackerPro || {
        csrfToken: '',
        userId: '',
        currentTheme: 'working-hard',
        apiBase: '/api/',
        panelBase: '/'
    }
};

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

App.init = function () {
    appLog('Init', 'START', { status: 'INFO', message: 'Initializing Tracker Pro SPA' });
    this.initTheme();
    this.initSidebarState();
    this.bindEventDelegation();
    this.bindNavigation();
    this.bindSidebar();
    this.bindModals();
    this.bindDropdowns();
    this.bindKeyboardShortcuts();
    this.bindSearch();
    this.bindFAB();
    this.bindNetworkStatus();
    this.markActiveNav();

    // Handle browser back/forward
    window.addEventListener('popstate', (e) => {
        if (e.state?.url) {
            appLog('Navigation', 'POPSTATE', { status: 'INFO', url: e.state.url });
            this.loadPanel(e.state.url, false);
        }
    });

    // Load initial panel based on URL
    const panelContent = document.getElementById('panel-content');
    if (panelContent && !panelContent.innerHTML.trim()) {
        appLog('Init', 'LOAD_INITIAL_PANEL', { status: 'INFO', url: window.location.pathname });
        this.loadPanel(window.location.pathname, false);
    }

    appLog('Init', 'COMPLETE', { status: 'SUCCESS', message: 'Tracker Pro initialized' });
};

// ============================================================================
// EVENT DELEGATION (Single root handler)
// ============================================================================
App.bindEventDelegation = function () {
    const mainContent = document.getElementById('main-content');
    if (!mainContent) return;

    mainContent.addEventListener('click', (e) => {
        const action = e.target.closest('[data-action]');
        if (action) {
            const actionType = action.dataset.action;
            this.handleAction(actionType, action, e);
        }
    });
};

App.handleAction = function (action, element, event) {
    switch (action) {
        // Removed 'toggle' case - now handled by individual panels (dashboard, today, week)
        // to prevent duplicate API calls
        case 'edit':
            const editId = element.closest('[data-task-id]')?.dataset.taskId;
            if (editId) this.loadModal(`/modals/edit_task/?task_id=${editId}`);
            break;
        case 'delete':
            const deleteId = element.closest('[data-task-id]')?.dataset.taskId;
            if (deleteId) this.confirmDelete('task', deleteId);
            break;
        case 'open-modal':
            event.preventDefault();
            const modalId = element.dataset.modal;
            const modalUrl = element.dataset.modalUrl;
            modalUrl ? this.loadModal(modalUrl) : this.openModal(modalId);
            break;
        case 'close-modal':
            this.closeModal();
            break;
        case 'use-template':
            event.preventDefault();
            const templateName = element.dataset.template;
            this.useTemplate(templateName);
            break;
        case 'create-template':
            event.preventDefault();
            this.openModal('add-tracker');
            break;
        default:
            console.log('Unknown action:', action);
    }
};

// ============================================================================
// THEME MANAGEMENT
// ============================================================================
App.initTheme = function () {
    const savedTheme = localStorage.getItem('tracker-theme') || 'working-hard';
    this.setTheme(savedTheme);

    // Sidebar theme switcher
    const sidebarSelect = document.getElementById('theme-switcher-sidebar');
    if (sidebarSelect) {
        sidebarSelect.value = savedTheme;
        sidebarSelect.addEventListener('change', (e) => {
            this.setTheme(e.target.value);
        });
    }

    // Theme dropdown buttons
    document.querySelectorAll('[data-theme]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            this.setTheme(btn.dataset.theme);
            this.closeDropdowns();
        });
    });
};

App.setTheme = function (theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('tracker-theme', theme);
    this.config.currentTheme = theme;

    const sidebarSelect = document.getElementById('theme-switcher-sidebar');
    if (sidebarSelect) sidebarSelect.value = theme;
};

// ============================================================================
// SIDEBAR STATE PERSISTENCE
// ============================================================================
App.initSidebarState = function () {
    const collapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    this.state.sidebarCollapsed = collapsed;

    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');

    if (collapsed && window.innerWidth > 768) {
        sidebar?.classList.add('collapsed');
        mainContent?.classList.add('sidebar-collapsed');
    }
};

App.toggleSidebarCollapse = function () {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');

    this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
    localStorage.setItem('sidebar-collapsed', this.state.sidebarCollapsed);

    sidebar?.classList.toggle('collapsed', this.state.sidebarCollapsed);
    mainContent?.classList.toggle('sidebar-collapsed', this.state.sidebarCollapsed);
};

// ============================================================================
// NAVIGATION WITH CACHING
// ============================================================================
App.bindNavigation = function () {
    document.addEventListener('click', (e) => {
        const navLink = e.target.closest('[data-nav]');
        if (navLink && navLink.href) {
            e.preventDefault();
            const url = new URL(navLink.href).pathname;
            this.loadPanel(url);
        }
    });
};

// Map page URLs to panel endpoints
App.getPanelUrl = function (pageUrl) {
    const routes = {
        '/': '/panels/dashboard/',
        '/trackers/': '/panels/trackers/',
        '/today/': '/panels/today/',
        '/week/': '/panels/week/',
        '/month/': '/panels/month/',
        '/analytics/': '/panels/analytics/',
        '/goals/': '/panels/goals/',
        '/insights/': '/panels/insights/',
        '/templates/': '/panels/templates/',
        '/help/': '/panels/help/',
        '/settings/': '/panels/settings/',
    };

    // Check for tracker detail: /tracker/{id}/
    if (pageUrl.match(/^\/tracker\/[\w-]+\/$/)) {
        const trackerId = pageUrl.split('/')[2];
        return `/panels/tracker/${trackerId}/`;
    }

    // Check for settings sections: /settings/{section}/
    if (pageUrl.startsWith('/settings/') && pageUrl !== '/settings/') {
        const section = pageUrl.replace('/settings/', '').replace('/', '');
        return `/panels/settings/${section}/`;
    }

    return routes[pageUrl] || '/panels/dashboard/';
};

App.loadPanel = async function (url, pushState = true) {
    if (this.state.isLoading) return;

    const panelUrl = this.getPanelUrl(url);

    // Check cache first
    const cached = this.cache.panels.get(url);
    if (cached && Date.now() - cached.timestamp < this.cache.maxAge) {
        appLog('Panel', 'CACHE_HIT', { status: 'SUCCESS', url, panelUrl, message: 'Serving from cache' });
        this.renderPanel(cached.html, url, pushState);
        return;
    }

    appLog('Panel', 'LOAD_START', { status: 'INFO', url, panelUrl, method: 'GET' });
    this.state.isLoading = true;
    this.showLoading();

    try {
        const response = await fetch(panelUrl, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'text/html',
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        if (!response.ok) {
            appLog('Panel', 'LOAD_ERROR', { status: 'ERROR', url, panelUrl, responseStatus: response.status });
            if (response.status === 404) {
                this.renderPanel(await this.fetchPanel('/panel/error_404/'), url, false);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
            return;
        }

        const html = await response.text();
        this.cache.panels.set(url, { html, timestamp: Date.now() });
        appLog('Panel', 'LOAD_SUCCESS', { status: 'SUCCESS', url, panelUrl, method: 'GET', responseStatus: response.status, htmlLength: html.length });
        this.renderPanel(html, url, pushState);

    } catch (error) {
        appLog('Panel', 'LOAD_EXCEPTION', { status: 'ERROR', url, panelUrl, error: error.message });
        if (!navigator.onLine) {
            this.showOfflinePanel();
        } else {
            this.showToast('error', 'Failed to load content', error.message);
        }
    } finally {
        this.state.isLoading = false;
        this.hideLoading();
    }
};

App.renderPanel = function (html, url, pushState) {
    const panelContent = document.getElementById('panel-content');

    if (panelContent) {
        panelContent.innerHTML = html;
        this.bindPanelEvents();
        this.executeScripts(panelContent);
    }

    if (pushState) {
        history.pushState({ url }, '', url);
    }

    this.markActiveNav(url);
    this.closeSidebar();
};

App.showOfflinePanel = function () {
    const panelContent = document.getElementById('panel-content');
    if (panelContent) {
        panelContent.innerHTML = `
            <div class="error-panel offline-panel">
                <div class="error-content">
                    <div class="error-icon">📡</div>
                    <h1 class="error-title">You're Offline</h1>
                    <p class="error-message">Check your connection and try again.</p>
                    <button class="btn btn-primary" onclick="location.reload()">Retry</button>
                </div>
            </div>
        `;
    }
};

App.markActiveNav = function (url = window.location.pathname) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        const href = item.getAttribute('href');
        if (href === url || (url === '/' && href === '/')) {
            item.classList.add('active');
        }
    });
};

App.bindPanelEvents = function () {
    this.bindTaskToggles();
    this.bindForms();
    this.initTrackerListFilters();
    this.initTemplateCategoryFilters();
};

// ============================================================================
// SIDEBAR
// ============================================================================
App.bindSidebar = function () {
    const toggle = document.getElementById('sidebar-toggle');
    const overlay = document.getElementById('sidebar-overlay');

    if (toggle) {
        toggle.addEventListener('click', () => this.toggleSidebar());
    }

    if (overlay) {
        overlay.addEventListener('click', () => this.closeSidebar());
    }
};

App.toggleSidebar = function () {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const toggle = document.getElementById('sidebar-toggle');

    this.state.sidebarOpen = !this.state.sidebarOpen;

    if (sidebar) sidebar.classList.toggle('open', this.state.sidebarOpen);
    if (overlay) overlay.classList.toggle('active', this.state.sidebarOpen);
    if (toggle) toggle.setAttribute('aria-expanded', this.state.sidebarOpen);
};

App.closeSidebar = function () {
    if (window.innerWidth <= 768) {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        if (sidebar) sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
        this.state.sidebarOpen = false;
    }
};

// ============================================================================
// NETWORK STATUS
// ============================================================================
App.bindNetworkStatus = function () {
    window.addEventListener('online', () => this.handleNetworkChange(true));
    window.addEventListener('offline', () => this.handleNetworkChange(false));
};

App.handleNetworkChange = function (isOnline) {
    this.state.isOnline = isOnline;

    const indicator = document.getElementById('network-status') || this.createNetworkIndicator();

    indicator.className = `network-status visible ${isOnline ? 'online' : 'offline'}`;
    indicator.querySelector('.network-status-text').textContent =
        isOnline ? 'Back online' : 'You\'re offline';

    // Hide after delay if online
    if (isOnline) {
        setTimeout(() => {
            indicator.classList.remove('visible');
        }, 3000);
    }
};

App.createNetworkIndicator = function () {
    const div = document.createElement('div');
    div.id = 'network-status';
    div.className = 'network-status';
    div.innerHTML = `
        <div class="network-dot"></div>
        <span class="network-status-text"></span>
    `;
    document.body.appendChild(div);
    return div;
};

// ============================================================================
// FLOATING ACTION BUTTON
// ============================================================================
App.bindFAB = function () {
    const fabContainer = document.getElementById('fab-container');
    if (!fabContainer) {
        this.createFAB();
    }

    document.addEventListener('click', (e) => {
        const fab = e.target.closest('.fab');
        if (fab) {
            e.preventDefault();
            const container = fab.closest('.fab-container');
            container?.classList.toggle('open');
        }

        const fabItem = e.target.closest('.fab-menu-item');
        if (fabItem) {
            const action = fabItem.dataset.fabAction;
            this.handleFABAction(action);
            document.querySelector('.fab-container')?.classList.remove('open');
        }

        // Close FAB when clicking outside
        if (!e.target.closest('.fab-container')) {
            document.querySelector('.fab-container')?.classList.remove('open');
        }
    });
};

App.createFAB = function () {
    const fab = document.createElement('div');
    fab.id = 'fab-container';
    fab.className = 'fab-container';
    fab.innerHTML = `
        <div class="fab-menu">
            <button class="fab-menu-item" data-fab-action="add-task">
                <span class="fab-menu-icon">✓</span>
                Add Task
            </button>
            <button class="fab-menu-item" data-fab-action="add-tracker">
                <span class="fab-menu-icon">📊</span>
                New Tracker
            </button>
            <button class="fab-menu-item" data-fab-action="add-goal">
                <span class="fab-menu-icon">🎯</span>
                Add Goal
            </button>
        </div>
        <button class="fab" aria-label="Quick actions">
            <svg class="fab-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
        </button>
    `;
    document.body.appendChild(fab);
};

App.handleFABAction = function (action) {
    console.log('[FAB] 🔘 handleFABAction called with:', action);
    switch (action) {
        case 'add-task':
            console.log('[FAB] Loading add_task modal');
            this.loadModal('/modals/add_task/');
            break;
        case 'add-tracker':
            console.log('[FAB] Loading add_tracker modal');
            this.loadModal('/modals/add_tracker/');
            break;
        case 'add-goal':
            console.log('[FAB] Loading add_goal modal');
            this.loadModal('/modals/add_goal/');
            break;
        default:
            console.warn('[FAB] Unknown action:', action);
    }
};

// ============================================================================
// MODAL SYSTEM
// ============================================================================
App.bindModals = function () {
    console.log('[Modal] 🔧 bindModals() called');

    document.addEventListener('click', (e) => {
        const trigger = e.target.closest('[data-action="open-modal"]');
        if (trigger) {
            e.preventDefault();
            const modalId = trigger.dataset.modal;
            const modalUrl = trigger.dataset.modalUrl;

            console.log('[Modal] 🖱️ Modal trigger clicked:', { modalId, modalUrl, trigger });

            if (modalUrl) {
                console.log('[Modal] 📡 Loading modal from URL:', modalUrl);
                this.loadModal(modalUrl);
            } else if (modalId) {
                console.log('[Modal] 📂 Opening static modal by ID:', modalId);
                this.openModal(modalId);
            } else {
                console.warn('[Modal] ⚠️ No modalUrl or modalId found on trigger');
            }
        }

        const closeBtn = e.target.closest('[data-action="close-modal"]');
        if (closeBtn) {
            console.log('[Modal] ❌ Close button clicked');
            this.closeModal();
        }
    });

    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', () => {
            console.log('[Modal] 🖱️ Backdrop clicked - closing modal');
            this.closeModal();
        });
    });

    console.log('[Modal] ✅ bindModals() complete');
};

App.openModal = function (modalId) {
    console.log('[Modal] 📂 openModal() called with ID:', modalId);

    const modal = document.getElementById(`${modalId}-modal`) || document.getElementById('modal-overlay');
    console.log('[Modal] 🔍 Looking for modal element:', {
        searchedId: `${modalId}-modal`,
        fallbackId: 'modal-overlay',
        found: !!modal,
        element: modal
    });

    if (modal) {
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        this.state.activeModal = modal;
        this.trapFocus(modal);
        document.body.style.overflow = 'hidden';
        console.log('[Modal] ✅ Modal opened successfully:', modalId);
    } else {
        console.error('[Modal] ❌ Modal element not found for ID:', modalId);
    }
};

App.loadModal = async function (url) {
    console.log('[Modal] 📡 loadModal() called with URL:', url);

    const overlay = document.getElementById('modal-overlay');
    const container = document.getElementById('modal-container');

    console.log('[Modal] 🔍 Modal elements:', {
        overlayFound: !!overlay,
        containerFound: !!container,
        overlay,
        container
    });

    if (!overlay || !container) {
        console.error('[Modal] ❌ Missing modal-overlay or modal-container');
        return;
    }

    // Show loading in modal
    console.log('[Modal] ⏳ Showing loading spinner');
    container.innerHTML = '<div class="modal-dialog"><div class="modal-body" style="text-align:center;padding:3rem"><div class="loading-spinner loading-spinner-lg"></div></div></div>';
    overlay.classList.add('active');

    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    try {
        console.log('[Modal] 🌐 Fetching modal content from:', url);
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCsrfToken()
            },
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        console.log('[Modal] 📥 Response received:', {
            ok: response.ok,
            status: response.status,
            statusText: response.statusText
        });

        if (!response.ok) {
            // Handle specific error codes with user-friendly messages
            let errorMsg = 'Failed to load modal';
            if (response.status === 403) {
                errorMsg = 'Session expired. Please refresh the page.';
            } else if (response.status === 404) {
                errorMsg = 'Modal not found';
            } else if (response.status === 500) {
                errorMsg = 'Server error. Please try again.';
            }
            throw new Error(errorMsg);
        }

        const html = await response.text();
        console.log('[Modal] 📄 HTML content received, length:', html.length);

        container.innerHTML = html;
        console.log('[Modal] ✅ Modal content injected into container');

        overlay.setAttribute('aria-hidden', 'false');
        this.state.activeModal = overlay;
        this.trapFocus(overlay);
        document.body.style.overflow = 'hidden';

        this.bindForms(container);
        this.executeScripts(container);
        console.log('[Modal] ✅ Modal fully loaded and ready');

    } catch (error) {
        clearTimeout(timeoutId);
        console.error('[Modal] ❌ Modal load error:', error);

        // Check if it was a timeout or network error
        let errorTitle = 'Failed to load';
        let errorMessage = error.message;

        if (error.name === 'AbortError') {
            errorTitle = 'Request timed out';
            errorMessage = 'The server took too long to respond.';
        } else if (!navigator.onLine) {
            errorTitle = 'No connection';
            errorMessage = 'Check your internet connection.';
        }

        // Show error in modal with retry button
        container.innerHTML = `
            <div class="modal-dialog" role="document">
                <div class="modal-header">
                    <h3 class="modal-title">${errorTitle}</h3>
                    <button type="button" class="modal-close" data-action="close-modal" aria-label="Close">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
                <div class="modal-body" style="text-align:center;padding:2rem">
                    <p style="color:var(--color-text-secondary);margin-bottom:1.5rem">${errorMessage}</p>
                    <button class="btn btn-primary" onclick="window.App.loadModal('${url}')">Try Again</button>
                </div>
            </div>
        `;

        this.showToast('error', errorTitle, errorMessage);
    }
};

App.executeScripts = function (container) {
    const scripts = container.querySelectorAll('script');
    console.log('[App] 📜 Executing', scripts.length, 'scripts from container');

    scripts.forEach(oldScript => {
        const newScript = document.createElement('script');
        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
        oldScript.parentNode.replaceChild(newScript, oldScript);
    });
};

App.confirmAction = function (options) {
    const { title, message, confirmText, confirmType, onConfirm } = options;

    // Load generic confirm modal
    // Fix: Pass only the URL to loadModal, then handle binding in a callback/after-await
    this.loadModal('/modals/confirm_delete/').then(() => {
        setTimeout(() => {
            const titleEl = document.getElementById('confirm-title');
            const messageEl = document.getElementById('confirm-message');
            const confirmBtn = document.getElementById('confirm-action-btn');

            if (titleEl) titleEl.textContent = title || 'Confirm Action';
            if (messageEl) messageEl.innerHTML = message || 'Are you sure?';

            if (confirmBtn) {
                confirmBtn.textContent = confirmText || 'Confirm';
                confirmBtn.className = `btn btn-${confirmType || 'primary'}`;

                // Remove old listeners to prevent multiple firings by cloning
                const newBtn = confirmBtn.cloneNode(true);
                confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

                newBtn.onclick = async () => {
                    newBtn.disabled = true;
                    newBtn.innerHTML = '<span class="loading-spinner"></span> Processing...';

                    try {
                        await onConfirm();
                        this.closeModal();
                    } catch (error) {
                        console.error('Action failed:', error);
                        this.showToast('error', 'Action Failed', error.message);
                        newBtn.disabled = false;
                        newBtn.textContent = confirmText || 'Confirm';
                    }
                };
            }
        }, 100);
    });
};

App.closeModal = function () {
    console.log('[Modal] ❌ closeModal() called');
    console.log('[Modal] 🔍 Current activeModal:', this.state.activeModal);

    if (this.state.activeModal) {
        this.state.activeModal.classList.remove('active');
        this.state.activeModal.setAttribute('aria-hidden', 'true');
        this.state.activeModal = null;
        document.body.style.overflow = '';
        console.log('[Modal] ✅ Active modal closed');
    }

    document.querySelectorAll('.modal-overlay.active').forEach(modal => {
        console.log('[Modal] 🧹 Cleaning up additional active modal:', modal.id);
        modal.classList.remove('active');
        modal.setAttribute('aria-hidden', 'true');
    });

    console.log('[Modal] ✅ closeModal() complete');
};

App.trapFocus = function (element) {
    const focusableElements = element.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    if (focusableElements.length === 0) return;

    const firstEl = focusableElements[0];
    const lastEl = focusableElements[focusableElements.length - 1];

    firstEl.focus();

    element.addEventListener('keydown', (e) => {
        if (e.key !== 'Tab') return;

        if (e.shiftKey) {
            if (document.activeElement === firstEl) {
                e.preventDefault();
                lastEl.focus();
            }
        } else {
            if (document.activeElement === lastEl) {
                e.preventDefault();
                firstEl.focus();
            }
        }
    });
};

App.confirmDelete = function (type, id) {
    console.log('[Modal] 🗑️ confirmDelete called:', { type, id });
    window.deleteConfig = {
        url: `/api/${type}/${id}/delete/`,
        type: type,
        id: id,
        onSuccess: () => {
            this.loadPanel(window.location.pathname, false);
        }
    };
    this.loadModal('/modals/confirm_delete/');
};

// ============================================================================
// DROPDOWNS
// ============================================================================
App.bindDropdowns = function () {
    document.addEventListener('click', (e) => {
        const toggle = e.target.closest('.dropdown-toggle');

        if (toggle) {
            e.preventDefault();
            e.stopPropagation();
            const dropdown = toggle.closest('.dropdown');
            const isOpen = dropdown.classList.contains('open');

            this.closeDropdowns();

            if (!isOpen) {
                dropdown.classList.add('open');
                toggle.setAttribute('aria-expanded', 'true');
            }
        } else {
            this.closeDropdowns();
        }
    });
};

App.closeDropdowns = function () {
    document.querySelectorAll('.dropdown.open').forEach(dropdown => {
        dropdown.classList.remove('open');
        dropdown.querySelector('.dropdown-toggle')?.setAttribute('aria-expanded', 'false');
    });
};

// ============================================================================
// TOAST NOTIFICATIONS
// ============================================================================
App.showToast = function (type, title, message = '', duration = 5000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const template = document.getElementById('toast-template');
    const iconTemplate = document.getElementById(`toast-icon-${type}`);

    const toast = template?.content.cloneNode(true).querySelector('.toast') || this.createToastElement();

    toast.classList.add(type);
    toast.querySelector('.toast-title').textContent = title;
    toast.querySelector('.toast-message').textContent = message;

    if (iconTemplate) {
        toast.querySelector('.toast-icon').innerHTML = iconTemplate.innerHTML;
    }

    toast.querySelector('.toast-close')?.addEventListener('click', () => {
        this.dismissToast(toast);
    });

    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => this.dismissToast(toast), duration);
    }

    return toast;
};

App.createToastElement = function () {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <div class="toast-icon"></div>
        <div class="toast-content">
            <div class="toast-title"></div>
            <div class="toast-message"></div>
        </div>
        <button type="button" class="toast-close" aria-label="Close">×</button>
        <div class="toast-progress"></div>
    `;
    return toast;
};

App.dismissToast = function (toast) {
    toast.style.animation = 'slideOutRight 0.3s ease-out forwards';
    setTimeout(() => toast.remove(), 300);
};

// ============================================================================
// LOADING STATE
// ============================================================================
App.showLoading = function () {
    const skeleton = document.getElementById('loading-skeleton');
    const content = document.getElementById('panel-content');
    const overlay = document.getElementById('content-loading-overlay');

    if (skeleton) skeleton.style.display = 'block';
    if (content) content.style.opacity = '0.5';
    if (overlay) overlay.style.display = 'flex';
};

App.hideLoading = function () {
    const skeleton = document.getElementById('loading-skeleton');
    const content = document.getElementById('panel-content');
    const overlay = document.getElementById('content-loading-overlay');

    if (skeleton) skeleton.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
    if (content) {
        content.style.opacity = '1';
        content.classList.add('fade-in');
    }
};

App.setButtonLoading = function (btn, loading) {
    if (loading) {
        btn.dataset.originalText = btn.textContent;
        btn.innerHTML = '<span class="spinner-inline"></span> Loading...';
        btn.disabled = true;
        btn.classList.add('loading');
    } else {
        btn.textContent = btn.dataset.originalText || 'Submit';
        btn.disabled = false;
        btn.classList.remove('loading');
    }
};

// ============================================================================
// KEYBOARD SHORTCUTS
// ============================================================================
App.bindKeyboardShortcuts = function () {
    document.addEventListener('keydown', (e) => {
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            if (e.key === 'Escape') {
                document.activeElement.blur();
                this.closeSearchResults();
            }
            return;
        }

        if (e.key === 'Escape') {
            this.closeModal();
            this.closeDropdowns();
            this.closeSearchResults();
            return;
        }

        if (e.key === '?' || (e.shiftKey && e.key === '/')) {
            e.preventDefault();
            this.showShortcutsModal();
            return;
        }

        if (e.key === '/') {
            e.preventDefault();
            document.getElementById('global-search')?.focus();
            return;
        }

        if (e.key === '[') {
            e.preventDefault();
            window.innerWidth > 768 ? this.toggleSidebarCollapse() : this.toggleSidebar();
            return;
        }

        if (e.key === 'n') {
            e.preventDefault();
            console.log('[Keyboard] "n" pressed - loading add_tracker modal');
            this.loadModal('/modals/add_tracker/');
            return;
        }

        if (e.key === 't' && this.state.currentTracker) {
            e.preventDefault();
            console.log('[Keyboard] "t" pressed - loading add_task modal');
            this.loadModal('/modals/add_task/');
            return;
        }

        this.handleKeySequence(e.key);
    });

    // Bind shortcuts button in header
    document.getElementById('shortcuts-btn')?.addEventListener('click', () => {
        appLog('Keyboard', 'SHORTCUTS_BTN_CLICK', { status: 'INFO', message: 'Opening shortcuts modal' });
        this.showShortcutsModal();
    });
};

// Show shortcuts modal
App.showShortcutsModal = function () {
    const modal = document.getElementById('shortcuts-modal');
    if (modal) {
        appLog('Modal', 'SHORTCUTS_OPEN', { status: 'SUCCESS', message: 'Showing keyboard shortcuts modal' });
        modal.classList.add('active');
        modal.setAttribute('aria-hidden', 'false');
        this.state.activeModal = modal;
        document.body.style.overflow = 'hidden';
    } else {
        appLog('Modal', 'SHORTCUTS_NOT_FOUND', { status: 'ERROR', message: 'Shortcuts modal element not found' });
    }
};

App.handleKeySequence = function (key) {
    clearTimeout(this.state.keyTimeout);
    this.state.keyBuffer += key;

    this.state.keyTimeout = setTimeout(() => {
        this.state.keyBuffer = '';
    }, 500);

    if (this.state.keyBuffer === 'gd') {
        this.loadPanel('/');
        this.state.keyBuffer = '';
    }
    else if (this.state.keyBuffer === 'gt') {
        this.loadPanel('/trackers/');
        this.state.keyBuffer = '';
    }
    else if (this.state.keyBuffer === 'gg') {
        this.loadPanel('/goals/');
        this.state.keyBuffer = '';
    }
    else if (this.state.keyBuffer === 'gs') {
        this.loadPanel('/settings/');
        this.state.keyBuffer = '';
    }
};

// ============================================================================
// SEARCH WITH RESULTS
// ============================================================================
App.bindSearch = function () {
    const searchInput = document.getElementById('global-search');
    if (!searchInput) return;

    let debounceTimer;

    // Create results dropdown if not exists
    if (!document.getElementById('search-results')) {
        const results = document.createElement('div');
        results.id = 'search-results';
        results.className = 'search-results';
        searchInput.parentNode.appendChild(results);
    }

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            this.handleSearch(e.target.value);
        }, 300);
    });

    searchInput.addEventListener('focus', () => {
        if (searchInput.value.length >= 2) {
            document.getElementById('search-results')?.classList.add('active');
        }
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            searchInput.blur();
            searchInput.value = '';
            this.closeSearchResults();
        }
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();
            this.navigateSearchResults(e.key === 'ArrowDown' ? 1 : -1);
        }
        if (e.key === 'Enter') {
            this.selectSearchResult();
        }
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-box')) {
            this.closeSearchResults();
        }
    });
};

App.handleSearch = async function (query) {
    const resultsContainer = document.getElementById('search-results');

    if (query.length < 2) {
        this.closeSearchResults();
        return;
    }

    const url = `/api/search/?q=${encodeURIComponent(query)}`;
    appLog('Search', 'QUERY_START', { status: 'INFO', url, method: 'GET', query });

    try {
        const response = await fetch(url, {
            headers: { 'X-CSRFToken': this.getCsrfToken() }
        });

        if (!response.ok) throw new Error('Search failed');

        const data = await response.json();
        appLog('Search', 'QUERY_SUCCESS', { status: 'SUCCESS', url, method: 'GET', resultCount: (data.trackers?.length || 0) + (data.tasks?.length || 0), responseStatus: response.status });
        this.renderSearchResults(data);

    } catch (error) {
        appLog('Search', 'QUERY_ERROR', { status: 'WARNING', url, method: 'GET', error: error.message, message: 'Using fallback search' });
        this.renderSearchFallback(query);
    }
};

App.renderSearchResults = function (data) {
    const container = document.getElementById('search-results');
    if (!container) return;

    let html = '';

    if (data.trackers?.length) {
        html += `<div class="search-section">
            <div class="search-section-title">Trackers</div>
            ${data.trackers.map(t => `
                <div class="search-result-item" data-url="/tracker/${t.id}/">
                    <div class="search-result-icon">📊</div>
                    <div class="search-result-text">
                        <div class="search-result-title">${t.name}</div>
                        <div class="search-result-meta">${t.task_count || 0} tasks</div>
                    </div>
                </div>
            `).join('')}
        </div>`;
    }

    if (data.tasks?.length) {
        html += `<div class="search-section">
            <div class="search-section-title">Tasks</div>
            ${data.tasks.map(t => `
                <div class="search-result-item" data-url="/tracker/${t.tracker_id}/">
                    <div class="search-result-icon">✓</div>
                    <div class="search-result-text">
                        <div class="search-result-title">${t.description}</div>
                        <div class="search-result-meta">${t.category || 'No category'}</div>
                    </div>
                </div>
            `).join('')}
        </div>`;
    }

    if (!html) {
        html = '<div class="notifications-empty">No results found</div>';
    }

    html += `<div class="search-hint">
        <span>Navigate with ↑↓</span>
        <span>Select with Enter</span>
        <span>Close with Esc</span>
    </div>`;

    container.innerHTML = html;
    container.classList.add('active');
    this.state.searchSelectedIndex = -1;

    // Bind click events
    container.querySelectorAll('.search-result-item').forEach(item => {
        item.addEventListener('click', () => {
            this.loadPanel(item.dataset.url);
            this.closeSearchResults();
            document.getElementById('global-search').value = '';
        });
    });
};

App.renderSearchFallback = function (query) {
    const container = document.getElementById('search-results');
    if (!container) return;

    const lowerQuery = query.toLowerCase();
    const quickLinks = [
        { name: 'Dashboard', url: '/', icon: '🏠' },
        { name: 'My Trackers', url: '/trackers/', icon: '📊' },
        { name: 'Goals', url: '/goals/', icon: '🎯' },
        { name: 'Analytics', url: '/analytics/', icon: '📈' },
        { name: 'Settings', url: '/settings/', icon: '⚙️' }
    ].filter(l => l.name.toLowerCase().includes(lowerQuery));

    if (quickLinks.length) {
        container.innerHTML = `
            <div class="search-section">
                <div class="search-section-title">Quick Links</div>
                ${quickLinks.map(l => `
                    <div class="search-result-item" data-url="${l.url}">
                        <div class="search-result-icon">${l.icon}</div>
                        <div class="search-result-text">
                            <div class="search-result-title">${l.name}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        container.classList.add('active');
    }
};

App.navigateSearchResults = function (direction) {
    const items = document.querySelectorAll('.search-result-item');
    if (!items.length) return;

    items[this.state.searchSelectedIndex]?.classList.remove('selected');
    this.state.searchSelectedIndex += direction;

    if (this.state.searchSelectedIndex < 0) this.state.searchSelectedIndex = items.length - 1;
    if (this.state.searchSelectedIndex >= items.length) this.state.searchSelectedIndex = 0;

    items[this.state.searchSelectedIndex]?.classList.add('selected');
};

App.selectSearchResult = function () {
    const selected = document.querySelector('.search-result-item.selected');
    if (selected) {
        this.loadPanel(selected.dataset.url);
        this.closeSearchResults();
        document.getElementById('global-search').value = '';
    }
};

App.closeSearchResults = function () {
    document.getElementById('search-results')?.classList.remove('active');
    this.state.searchSelectedIndex = -1;
};

// ============================================================================
// TASK INTERACTIONS
// ============================================================================
App.bindTaskToggles = function () {
    // Now handled by event delegation
};

App.toggleTask = async function (taskId, rowElement) {
    const url = `${this.config.apiBase}task/${taskId}/toggle/`;
    appLog('Task', 'TOGGLE_START', { status: 'INFO', url, method: 'POST', taskId });
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        if (!response.ok) throw new Error('Toggle failed');

        const data = await response.json();
        appLog('Task', 'TOGGLE_SUCCESS', { status: 'SUCCESS', url, method: 'POST', taskId, newStatus: data.new_status, responseStatus: response.status });

        rowElement.dataset.status = data.new_status;
        const icon = rowElement.querySelector('.status-icon');
        if (icon) {
            icon.className = `status-icon status-${data.new_status.toLowerCase()}`;
        }

        this.showToast('success', 'Task updated', `Status: ${data.new_status}`);

    } catch (error) {
        appLog('Task', 'TOGGLE_ERROR', { status: 'ERROR', url, method: 'POST', taskId, error: error.message });
        this.showToast('error', 'Failed to update task', error.message);
    }
};

// ============================================================================
// FORM HANDLING
// ============================================================================
App.bindForms = function (container = document) {
    console.log('[Forms] 🔧 bindForms() called on container:', container.id || 'document');

    const forms = container.querySelectorAll('form[data-ajax]');
    console.log('[Forms] Found', forms.length, 'forms with data-ajax attribute');

    forms.forEach(form => {
        console.log('[Forms] Binding form:', form.id || 'unnamed form', 'action:', form.action);

        // Remove any existing listeners by cloning
        const newForm = form.cloneNode(true);
        form.parentNode.replaceChild(newForm, form);

        newForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log('[Forms] 📤 Form submit event triggered:', newForm.id || 'unnamed form');
            await this.submitForm(newForm);
        });

        // Also bind click handler on submit button as backup
        const submitBtn = newForm.querySelector('[type="submit"]');
        if (submitBtn) {
            console.log('[Forms] Found submit button:', submitBtn.id || submitBtn.textContent.trim());
            submitBtn.addEventListener('click', (e) => {
                console.log('[Forms] 🖱️ Submit button clicked');
                // Form's submit event should handle it, but click confirms binding
            });
        }
    });
};

App.submitForm = async function (form) {
    const submitBtn = form.querySelector('[type="submit"]');
    console.log('[Forms] 🚀 submitForm() called');
    console.log('[Forms] Form action:', form.action);
    console.log('[Forms] Form method:', form.method);

    try {
        this.setButtonLoading(submitBtn, true);

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        console.log('[Forms] 📦 Form data:', data);

        const response = await fetch(form.action, {
            method: form.method || 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        console.log('[Forms] 📥 Response status:', response.status, response.statusText);
        const result = await response.json();
        console.log('[Forms] 📥 Response data:', result);

        if (response.ok && result.success) {
            this.showToast('success', result.message || 'Saved successfully');
            this.closeModal();

            // Invalidate cache and refresh
            if (result.refresh) {
                console.log('[Forms] 🔄 Refreshing panel:', window.location.pathname);
                this.cache.panels.delete(window.location.pathname);
                this.loadPanel(window.location.pathname, false);
            }
        } else {
            console.log('[Forms] ❌ Validation errors:', result.errors);
            this.showFormErrors(form, result.errors || {});
            this.showToast('error', 'Validation failed', result.error || 'Please check the form');
        }

    } catch (error) {
        console.error('[Forms] ❌ Form submit error:', error);
        this.showToast('error', 'Failed to save', error.message);
    } finally {
        this.setButtonLoading(submitBtn, false);
    }
};

App.showFormErrors = function (form, errors) {
    form.querySelectorAll('.field-error').forEach(el => el.textContent = '');
    form.querySelectorAll('.form-input.error').forEach(el => el.classList.remove('error'));

    Object.entries(errors).forEach(([field, messages]) => {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.classList.add('error');
            const errorEl = input.parentNode.querySelector('.field-error') || document.createElement('div');
            errorEl.className = 'field-error';
            errorEl.textContent = Array.isArray(messages) ? messages[0] : messages;
            if (!input.parentNode.querySelector('.field-error')) {
                input.parentNode.appendChild(errorEl);
            }
        }
    });
};

// ============================================================================
// LOGOUT
// ============================================================================
document.addEventListener('click', (e) => {
    if (e.target.closest('[data-action="logout"]')) {
        e.preventDefault();
        App.handleLogout();
    }
});

App.handleLogout = async function () {
    try {
        const response = await fetch('/api/auth/logout/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        const data = await response.json();
        if (data.success) {
            window.location.href = data.redirect || '/accounts/login/';
        }
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/logout/';
    }
};

// ============================================================================
// UTILITY
// ============================================================================
App.getCsrfToken = function () {
    return this.config.csrfToken ||
        document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        this.getCookie('csrftoken');
};

App.getCookie = function (name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
};

App.debounce = function (func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

App.invalidateCache = function (url) {
    if (url) {
        this.cache.panels.delete(url);
    } else {
        this.cache.panels.clear();
    }
};

// ============================================================================
// TEMPLATE FUNCTIONS
// ============================================================================
App.useTemplate = function (templateName) {
    console.log('[Templates] Using template:', templateName);

    // Template definitions with tasks
    const templates = {
        'morning': {
            name: 'Morning Routine',
            tasks: ['Wake up early', 'Meditate 10 min', 'Exercise 30 min', 'Healthy breakfast', 'Plan day', 'Review goals', 'Personal growth reading', 'Journal']
        },
        'fitness': {
            name: 'Fitness Tracker',
            tasks: ['Warm up', 'Main workout', 'Cool down', 'Track nutrition', 'Hydration check', 'Recovery stretches']
        },
        'study': {
            name: 'Study Plan',
            tasks: ['Review previous notes', 'Read new material', 'Practice exercises', 'Take notes', 'Self-quiz']
        },
        'work': {
            name: 'Work Productivity',
            tasks: ['Check emails', 'Priority task 1', 'Priority task 2', 'Priority task 3', 'Deep work block', 'Team sync', 'End of day review']
        },
        'mindfulness': {
            name: 'Mindfulness',
            tasks: ['Morning meditation', 'Gratitude journal', 'Mindful break', 'Evening reflection']
        },
        'evening': {
            name: 'Evening Wind Down',
            tasks: ['Review day', 'Prepare tomorrow', 'Light stretching', 'No screens', 'Relaxation time']
        },
        'weekly-review': {
            name: 'Weekly Review',
            tasks: ['Review goals', 'Celebrate wins', 'Identify challenges', 'Plan next week', 'Clear inbox', 'Update trackers']
        },
        'language': {
            name: 'Language Learning',
            tasks: ['Vocabulary practice', 'Grammar exercise', 'Speaking practice', 'Listening practice', 'Immersion activity']
        }
    };

    const template = templates[templateName];
    if (!template) {
        this.showToast('error', 'Template not found');
        return;
    }

    // Show confirmation and create tracker
    this.showToast('info', `Creating "${template.name}" tracker...`);

    // Create the tracker via API
    fetch('/api/tracker/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken()
        },
        body: JSON.stringify({
            name: template.name,
            description: `Created from ${template.name} template`,
            time_period: templateName === 'weekly-review' ? 'weekly' : 'daily',
            tasks: template.tasks  // Backend will create task templates
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                this.showToast('success', `${template.name} tracker created!`);
                // Navigate to the new tracker
                if (data.redirect) {
                    this.loadPanel(data.redirect, true);
                } else {
                    this.loadPanel('/trackers/', true);
                }
            } else {
                this.showToast('error', data.error || 'Failed to create tracker');
            }
        })
        .catch(err => {
            console.error('[Templates] Error:', err);
            this.showToast('error', 'Failed to create tracker');
        });
};

// ============================================================================
// CRUD ACTIONS & CONFIRMATION
// ============================================================================

// App.confirmAction is defined in the MODAL SYSTEM section above
// Reusing that implementation to ensure consistency


App.handleTrackerAction = function (action, trackerId) {
    if (!trackerId) return;

    if (action === 'archive') {
        this.confirmAction({
            title: 'Archive Tracker',
            message: 'Are you sure you want to archive this tracker? It will be hidden from your active list.',
            confirmText: 'Archive',
            confirmType: 'warning',
            onConfirm: async () => {
                const response = await fetch(`/api/tracker/${trackerId}/update/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({ status: 'archived' })
                });

                const result = await response.json();
                if (result.success) {
                    this.showToast('success', 'Tracker Archived');
                    // Refresh current panel
                    this.cache.panels.clear();
                    this.loadPanel(window.location.pathname, false);
                } else {
                    throw new Error(result.error);
                }
            }
        });
    } else if (action === 'delete') {
        this.confirmAction({
            title: 'Delete Tracker',
            message: 'Are you sure you want to delete this tracker? <strong>This action cannot be undone</strong> and will delete all associated tasks and history.',
            confirmText: 'Delete Forever',
            confirmType: 'danger',
            onConfirm: async () => {
                const response = await fetch(`/api/tracker/${trackerId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                const result = await response.json();
                if (result.success) {
                    this.showToast('success', 'Tracker Deleted');
                    this.cache.panels.clear();

                    // If we are on the tracker detail page, go back to list
                    if (window.location.pathname.includes(`/tracker/${trackerId}`)) {
                        window.history.pushState({}, '', '/trackers/');
                        this.loadPanel('/trackers/', true);
                    } else {
                        this.loadPanel(window.location.pathname, false);
                    }
                } else {
                    throw new Error(result.error);
                }
            }
        });
    } else if (action === 'unarchive') {
        // Unarchive: set status back to active
        this.confirmAction({
            title: 'Unarchive Tracker',
            message: 'Restore this tracker to your active list?',
            confirmText: 'Unarchive',
            confirmType: 'primary',
            onConfirm: async () => {
                const response = await fetch(`/api/tracker/${trackerId}/update/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    },
                    body: JSON.stringify({ status: 'active' })
                });

                const result = await response.json();
                if (result.success) {
                    this.showToast('success', 'Tracker Restored');
                    this.cache.panels.clear();
                    this.loadPanel(window.location.pathname, false);
                } else {
                    throw new Error(result.error);
                }
            }
        });
    } else if (action === 'duplicate') {
        // Implement duplicate if needed, or show toast
        this.showToast('info', 'Duplicate', 'Feature coming soon!');
    }
};

App.handleTaskAction = function (action, taskId) {
    if (!taskId) return;

    if (action === 'delete') {
        this.confirmAction({
            title: 'Delete Task',
            message: 'Are you sure you want to permanently delete this task?',
            confirmText: 'Delete',
            confirmType: 'danger',
            onConfirm: async () => {
                const response = await fetch(`/api/task/${taskId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                const result = await response.json();
                if (result.success) {
                    this.showToast('success', 'Task Deleted');
                    // Remove element from DOM immediately for better UX
                    const taskEl = document.querySelector(`[data-task-id="${taskId}"]`);
                    if (taskEl) taskEl.remove();

                    // Refresh stats if needed (optional, or rely on full reload)
                    // For now, simple removal is enough
                } else {
                    throw new Error(result.error);
                }
            }
        });
    }
};

// Global Listener for Delete Task
document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action="delete-task"]');
    if (btn) {
        e.preventDefault();
        e.stopPropagation();
        const taskRow = btn.closest('[data-task-id]');
        if (taskRow) {
            App.handleTaskAction('delete', taskRow.dataset.taskId);
        }
    }
});


// ============================================================================
// TRACKER LIST FILTERING 
// ============================================================================
App.initTrackerListFilters = function () {
    const container = document.getElementById('trackers-container');
    if (!container) return;

    console.log('[Filters] Initializing tracker list filters');

    // View toggle
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            document.querySelectorAll('.view-toggle-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-pressed', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-pressed', 'true');
            container.dataset.view = view;
        });
    });

    // Filter checkboxes
    document.querySelectorAll('.filter-option input').forEach(checkbox => {
        checkbox.addEventListener('change', () => this.applyTrackerFilters());
    });

    // Clear filters
    const clearBtn = document.getElementById('clear-filters');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            document.querySelectorAll('.filter-option input').forEach(cb => cb.checked = true);
            this.applyTrackerFilters();
        });
    }

    // Sort buttons
    document.querySelectorAll('[data-sort]').forEach(btn => {
        btn.addEventListener('click', () => {
            const sortType = btn.dataset.sort;
            document.getElementById('current-sort').textContent = btn.textContent.trim();
            this.sortTrackers(sortType);
        });
    });

    // Search
    const searchInput = document.getElementById('tracker-search');
    if (searchInput) {
        searchInput.addEventListener('input', this.debounce(() => {
            this.filterTrackersBySearch(searchInput.value.toLowerCase().trim());
        }, 300));
    }
};

App.applyTrackerFilters = function () {
    const statusFilters = Array.from(document.querySelectorAll('input[name="filter-status"]:checked')).map(cb => cb.value);
    const periodFilters = Array.from(document.querySelectorAll('input[name="filter-period"]:checked')).map(cb => cb.value);

    // Update filter count badge
    const totalFilters = 6; // 3 statuses + 3 periods
    const activeFilters = totalFilters - (statusFilters.length + periodFilters.length);
    const filterCount = document.getElementById('filter-count');
    if (filterCount) {
        if (activeFilters > 0) {
            filterCount.textContent = activeFilters;
            filterCount.style.display = 'inline';
        } else {
            filterCount.style.display = 'none';
        }
    }

    // Apply filters
    document.querySelectorAll('.tracker-item').forEach(item => {
        const status = item.dataset.status || 'active';
        const period = item.querySelector('.tracker-period-badge')?.textContent?.toLowerCase() || 'daily';

        const statusMatch = statusFilters.length === 0 || statusFilters.includes(status);
        const periodMatch = periodFilters.length === 0 || periodFilters.includes(period);

        item.style.display = (statusMatch && periodMatch) ? '' : 'none';
    });
};

App.sortTrackers = function (sortType) {
    const container = document.getElementById('trackers-container');
    if (!container) return;

    const items = Array.from(container.querySelectorAll('.tracker-item'));

    items.sort((a, b) => {
        switch (sortType) {
            case 'name':
                const nameA = a.querySelector('.tracker-name')?.textContent || '';
                const nameB = b.querySelector('.tracker-name')?.textContent || '';
                return nameA.localeCompare(nameB);
            case 'progress':
                const progressA = parseInt(a.querySelector('.progress-fill')?.style.width) || 0;
                const progressB = parseInt(b.querySelector('.progress-fill')?.style.width) || 0;
                return progressB - progressA;
            case 'tasks':
                const tasksA = parseInt(a.querySelector('.tracker-task-count')?.textContent) || 0;
                const tasksB = parseInt(b.querySelector('.tracker-task-count')?.textContent) || 0;
                return tasksB - tasksA;
            case 'recent':
            default:
                // Keep original order (by updated_at from server)
                return 0;
        }
    });

    // Re-append sorted items
    items.forEach(item => container.appendChild(item));
};

App.filterTrackersBySearch = function (query) {
    document.querySelectorAll('.tracker-item').forEach(item => {
        const name = item.querySelector('.tracker-name')?.textContent?.toLowerCase() || '';
        const desc = item.querySelector('.tracker-description')?.textContent?.toLowerCase() || '';

        const matches = !query || name.includes(query) || desc.includes(query);
        item.style.display = matches ? '' : 'none';
    });
};

// ============================================================================
// TEMPLATE CATEGORY FILTERING
// ============================================================================
App.initTemplateCategoryFilters = function () {
    const categoryBtns = document.querySelectorAll('.category-btn');
    if (!categoryBtns.length) return;

    console.log('[Templates] Initializing category filters');

    categoryBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            categoryBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Filter cards
            const category = btn.dataset.category;
            document.querySelectorAll('.template-card').forEach(card => {
                if (category === 'all' || card.dataset.category === category) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
};

// Export for debugging
window.App = App;
