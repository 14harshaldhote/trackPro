/**
 * Tracker Pro - Main Application
 * Core SPA controller that initializes and coordinates all modules
 */

// Import modules (will be loaded in order in base.html)
import { Router } from './modules/router.js';
import { ModalSystem } from './modules/modals.js';
import { FormManager } from './modules/forms.js';
import { KeyboardShortcuts } from './modules/keyboard.js';
import { ThemeSystem } from './modules/theme.js';
import { NotificationSystem } from './modules/notifications.js';
import { DropdownManager } from './modules/dropdowns.js';
import { SwipeGestures } from './modules/swipe.js';

class TrackerProApp {
    constructor() {
        this.router = null;
        this.modals = null;
        this.forms = null;
        this.keyboard = null;
        this.theme = null;
        this.notifications = null;
        this.dropdowns = null;
        this.swipe = null;

        this.state = {
            currentPanel: null,
            user: null,
            loading: false
        };

        this.config = window.TrackerPro || {};
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('🚀 Initializing Tracker Pro...');

        try {
            // Initialize core modules
            this.router = new Router(this);
            this.modals = new ModalSystem(this);
            this.forms = new FormManager(this);
            this.keyboard = new KeyboardShortcuts(this);
            this.theme = new ThemeSystem(this);
            this.notifications = new NotificationSystem(this);
            this.dropdowns = new DropdownManager(this);
            this.swipe = new SwipeGestures(this);

            // Set up global error handler
            this.setupErrorHandling();

            // Initialize theme from localStorage or default
            this.theme.init();

            // Set up keyboard shortcuts
            this.keyboard.init();

            // Set up dropdowns
            this.dropdowns.init();

            // Set up modals
            this.modals.init();

            // Set up forms
            this.forms.init();

            // Initialize swipe gestures (iOS)
            if (this.isIOS()) {
                this.swipe.init();
            }

            // Initialize router and load initial panel
            await this.router.init();

            // Set up navigation event listeners
            this.setupNavigation();

            // Mark app as ready
            document.body.classList.add('app-ready');

            console.log('✅ Tracker Pro initialized successfully');

        } catch (error) {
            console.error('❌ Failed to initialize Tracker Pro:', error);
            this.notifications.showToast('Failed to initialize app. Please refresh.', 'error');
        }
    }

    /**
     * Set up navigation event listeners
     */
    setupNavigation() {
        // Sidebar navigation links
        document.querySelectorAll('.sidebar .nav-item, .sidebar-nav a').forEach(link => {
            link.addEventListener('click', (e) => {
                const panel = link.dataset.panel;
                if (panel) {
                    e.preventDefault();
                    this.router.navigate(link.getAttribute('href') || `/${panel}/`);
                }
            });
        });

        // Browser back/forward
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.panel) {
                this.router.loadPanel(e.state.url, false);
            }
        });

        // Handle clicks on tracker links
        document.addEventListener('click', (e) => {
            const trackerLink = e.target.closest('.tracker-item');
            if (trackerLink) {
                e.preventDefault();
                const href = trackerLink.getAttribute('href');
                if (href) {
                    this.router.navigate(href);
                }
            }
        });
    }

    /**
     * Global error handling
     */
    setupErrorHandling() {
        window.addEventListener('error', (e) => {
            console.error('Global error:', e.error);
            this.notifications.showToast('An unexpected error occurred', 'error');
        });

        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            this.notifications.showToast('An unexpected error occurred', 'error');
        });
    }

    /**
     * Utility: Check if running on iOS
     */
    isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }

    /**
     * Get CSRF token
     */
    getCsrfToken() {
        return this.config.csrfToken ||
            document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
            '';
    }

    /**
     * Show loading state
     */
    showLoading() {
        this.state.loading = true;
        const skeleton = document.getElementById('loading-skeleton');
        if (skeleton) {
            skeleton.style.display = 'block';
        }
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        this.state.loading = false;
        const skeleton = document.getElementById('loading-skeleton');
        if (skeleton) {
            skeleton.style.display = 'none';
        }
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new TrackerProApp();
        window.app.init();
    });
} else {
    window.app = new TrackerProApp();
    window.app.init();
}

// Export for use in other modules
export default TrackerProApp;
