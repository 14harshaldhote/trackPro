/**
 * Tracker Pro - SPA Controller
 * Handles navigation, modals, toasts, and global state
 */

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
            this.loadPanel(e.state.url, false);
        }
    });

    // Load initial panel based on URL
    const panelContent = document.getElementById('panel-content');
    if (panelContent && !panelContent.innerHTML.trim()) {
        this.loadPanel(window.location.pathname, false);
    }

    console.log('🚀 Tracker Pro initialized');
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
        case 'toggle':
            const taskRow = element.closest('[data-task-id]');
            if (taskRow) this.toggleTask(taskRow.dataset.taskId, taskRow);
            break;
        case 'edit':
            const editId = element.closest('[data-task-id]')?.dataset.taskId;
            if (editId) this.loadModal(`/api/task/${editId}/edit/`);
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
        this.renderPanel(cached.html, url, pushState);
        return;
    }

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
            if (response.status === 404) {
                this.renderPanel(await this.fetchPanel('/panel/error_404/'), url, false);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
            return;
        }

        const html = await response.text();

        // Cache the panel
        this.cache.panels.set(url, { html, timestamp: Date.now() });

        this.renderPanel(html, url, pushState);

    } catch (error) {
        console.error('Panel load error:', error);

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

    try {
        console.log('[Modal] 🌐 Fetching modal content from:', url);
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        console.log('[Modal] 📥 Response received:', {
            ok: response.ok,
            status: response.status,
            statusText: response.statusText
        });

        if (!response.ok) throw new Error(`Failed to load modal: ${response.status} ${response.statusText}`);

        const html = await response.text();
        console.log('[Modal] 📄 HTML content received, length:', html.length);

        container.innerHTML = html;
        console.log('[Modal] ✅ Modal content injected into container');

        overlay.setAttribute('aria-hidden', 'false');
        this.state.activeModal = overlay;
        this.trapFocus(overlay);
        document.body.style.overflow = 'hidden';

        this.bindForms(container);
        console.log('[Modal] ✅ Modal fully loaded and ready');

    } catch (error) {
        console.error('[Modal] ❌ Modal load error:', error);
        this.showToast('error', 'Failed to load', error.message);
        this.closeModal();
    }
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
            this.openModal('shortcuts');
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

    try {
        const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
            headers: { 'X-CSRFToken': this.getCsrfToken() }
        });

        if (!response.ok) throw new Error('Search failed');

        const data = await response.json();
        this.renderSearchResults(data);

    } catch (error) {
        // Fallback: show quick links matching query
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
    try {
        const response = await fetch(`${this.config.apiBase}task/${taskId}/toggle/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            }
        });

        if (!response.ok) throw new Error('Toggle failed');

        const data = await response.json();

        rowElement.dataset.status = data.new_status;
        const icon = rowElement.querySelector('.status-icon');
        if (icon) {
            icon.className = `status-icon status-${data.new_status.toLowerCase()}`;
        }

        this.showToast('success', 'Task updated', `Status: ${data.new_status}`);

    } catch (error) {
        console.error('Task toggle error:', error);
        this.showToast('error', 'Failed to update task', error.message);
    }
};

// ============================================================================
// FORM HANDLING
// ============================================================================
App.bindForms = function (container = document) {
    container.querySelectorAll('form[data-ajax]').forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.submitForm(form);
        });
    });
};

App.submitForm = async function (form) {
    const submitBtn = form.querySelector('[type="submit"]');

    try {
        this.setButtonLoading(submitBtn, true);

        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        const response = await fetch(form.action, {
            method: form.method || 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            this.showToast('success', result.message || 'Saved successfully');
            this.closeModal();

            // Invalidate cache and refresh
            if (result.refresh) {
                this.cache.panels.delete(window.location.pathname);
                this.loadPanel(window.location.pathname, false);
            }
        } else {
            this.showFormErrors(form, result.errors || {});
            this.showToast('error', 'Validation failed', 'Please check the form');
        }

    } catch (error) {
        console.error('Form submit error:', error);
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

// Export for debugging
window.App = App;
