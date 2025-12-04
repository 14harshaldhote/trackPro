/**
 * Tracker Pro - Polish & Enhancements
 * Micro-interactions, sounds, keyboard nav, error recovery, PWA
 */

// ============================================================================
// MICRO-INTERACTIONS
// ============================================================================
const Interactions = {
    init() {
        this.bindRippleEffect();
        this.bindButtonPress();
        this.bindHoverEffects();
    },

    bindRippleEffect() {
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn, .nav-item, .sidebar-item');
            if (!btn || btn.classList.contains('no-ripple')) return;

            const ripple = document.createElement('span');
            ripple.className = 'ripple';

            const rect = btn.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);

            ripple.style.width = ripple.style.height = `${size}px`;
            ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
            ripple.style.top = `${e.clientY - rect.top - size / 2}px`;

            btn.appendChild(ripple);

            ripple.addEventListener('animationend', () => ripple.remove());
        });
    },

    bindButtonPress() {
        document.addEventListener('mousedown', (e) => {
            const btn = e.target.closest('.btn');
            if (btn) btn.classList.add('pressed');
        });

        document.addEventListener('mouseup', () => {
            document.querySelectorAll('.btn.pressed').forEach(btn => {
                btn.classList.remove('pressed');
            });
        });
    },

    bindHoverEffects() {
        // Card lift on hover
        document.querySelectorAll('.tracker-card, .goal-card, .stat-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-2px)';
            });
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }
};


// ============================================================================
// SOUND EFFECTS
// ============================================================================
const Sounds = {
    enabled: true,
    volume: 0.5,

    sounds: {
        complete: '/static/core/sounds/complete.mp3',
        notify: '/static/core/sounds/notify.mp3',
        error: '/static/core/sounds/error.mp3',
        click: '/static/core/sounds/click.mp3'
    },

    init() {
        this.enabled = localStorage.getItem('sounds-enabled') !== 'false';
        this.volume = parseFloat(localStorage.getItem('sounds-volume') || '0.5');
    },

    play(soundName) {
        if (!this.enabled) return;

        const src = this.sounds[soundName];
        if (!src) return;

        try {
            const audio = new Audio(src);
            audio.volume = this.volume;
            audio.play().catch(() => { }); // Ignore autoplay errors
        } catch (e) {
            // Sounds not critical
        }
    },

    setEnabled(enabled) {
        this.enabled = enabled;
        localStorage.setItem('sounds-enabled', enabled);
    },

    setVolume(volume) {
        this.volume = volume;
        localStorage.setItem('sounds-volume', volume);
    }
};


// ============================================================================
// KEYBOARD NAVIGATION
// ============================================================================
const KeyboardNav = {
    enabled: true,
    focusableSelector: 'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])',
    currentFocusIndex: 0,

    init() {
        this.enabled = localStorage.getItem('keyboard-enabled') !== 'false';
        if (!this.enabled) return;

        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.bindShortcuts();
    },

    handleKeydown(e) {
        // Navigation shortcuts (G + key)
        if (this.waitingForNav) {
            this.handleNavKey(e);
            return;
        }

        // Don't handle if in input
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            if (e.key === 'Escape') {
                document.activeElement.blur();
            }
            return;
        }

        switch (e.key) {
            case 'g':
                this.waitingForNav = true;
                setTimeout(() => this.waitingForNav = false, 1000);
                break;

            case '?':
                App.showShortcutsModal?.();
                break;

            case '/':
                e.preventDefault();
                document.querySelector('.search-input')?.focus();
                break;

            case 'n':
                e.preventDefault();
                App.openModal?.('add-tracker');
                break;

            case 'a':
                e.preventDefault();
                document.querySelector('.quick-add-input')?.focus();
                break;

            case 'Escape':
                App.closeModal?.();
                break;

            case 'ArrowUp':
            case 'ArrowDown':
                this.navigateList(e.key === 'ArrowUp' ? -1 : 1);
                e.preventDefault();
                break;

            case ' ':
                this.toggleCurrentItem();
                e.preventDefault();
                break;

            case '[':
                App.toggleSidebar?.();
                break;
        }
    },

    handleNavKey(e) {
        this.waitingForNav = false;

        const routes = {
            'd': '/',
            't': '/today/',
            'l': '/trackers/',
            's': '/settings/',
            'a': '/analytics/',
            'g': '/goals/',
            'i': '/insights/',
            'h': '/help/'
        };

        const route = routes[e.key.toLowerCase()];
        if (route) {
            e.preventDefault();
            App.loadPanel?.(route);
        }
    },

    navigateList(direction) {
        const items = document.querySelectorAll('.task-row, .tracker-card');
        if (!items.length) return;

        const focused = document.querySelector('.task-row.keyboard-focus, .tracker-card.keyboard-focus');

        items.forEach(item => item.classList.remove('keyboard-focus'));

        if (focused) {
            const index = Array.from(items).indexOf(focused);
            const newIndex = Math.max(0, Math.min(items.length - 1, index + direction));
            items[newIndex].classList.add('keyboard-focus');
            items[newIndex].scrollIntoView({ block: 'nearest' });
        } else {
            items[direction > 0 ? 0 : items.length - 1].classList.add('keyboard-focus');
        }
    },

    toggleCurrentItem() {
        const focused = document.querySelector('.task-row.keyboard-focus');
        if (focused) {
            focused.querySelector('.status-icon, [data-action="toggle"]')?.click();
        }
    },

    bindShortcuts() {
        // Cmd/Ctrl + K for search
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                document.querySelector('.search-input')?.focus();
            }
        });
    }
};


// ============================================================================
// ERROR RECOVERY
// ============================================================================
const ErrorRecovery = {
    maxRetries: 3,
    retryDelay: 1000,
    pendingRequests: new Map(),

    async fetchWithRetry(url, options = {}, retries = this.maxRetries) {
        const key = `${options.method || 'GET'}-${url}`;

        try {
            const response = await fetch(url, options);

            if (!response.ok && response.status >= 500) {
                throw new Error(`Server error: ${response.status}`);
            }

            this.pendingRequests.delete(key);
            return response;

        } catch (error) {
            if (retries > 0) {
                this.showRetryToast(retries);
                await this.delay(this.retryDelay * (this.maxRetries - retries + 1));
                return this.fetchWithRetry(url, options, retries - 1);
            }

            this.showErrorToast(error);
            throw error;
        }
    },

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    showRetryToast(retriesLeft) {
        App.showToast?.('warning', `Retrying... (${retriesLeft} attempts left)`);
    },

    showErrorToast(error) {
        App.showToast?.('error', 'Request failed', 'Please check your connection and try again.');
    }
};


// ============================================================================
// ONBOARDING
// ============================================================================
const Onboarding = {
    currentStep: 1,
    totalSteps: 4,

    init() {
        if (localStorage.getItem('onboarding-complete')) return;

        // Check if first time user
        if (this.isNewUser()) {
            this.show();
        }
    },

    isNewUser() {
        // Check URL param or API flag
        return new URLSearchParams(window.location.search).has('welcome');
    },

    show() {
        const overlay = document.getElementById('onboarding-overlay');
        if (!overlay) return;

        overlay.style.display = 'flex';
        this.bindEvents();
    },

    hide() {
        const overlay = document.getElementById('onboarding-overlay');
        if (overlay) overlay.style.display = 'none';
        localStorage.setItem('onboarding-complete', 'true');
    },

    bindEvents() {
        document.getElementById('skip-onboarding')?.addEventListener('click', () => this.hide());
        document.getElementById('next-step')?.addEventListener('click', () => this.nextStep());
        document.getElementById('prev-step')?.addEventListener('click', () => this.prevStep());
    },

    nextStep() {
        if (this.currentStep >= this.totalSteps) {
            this.hide();
            return;
        }
        this.goToStep(this.currentStep + 1);
    },

    prevStep() {
        if (this.currentStep <= 1) return;
        this.goToStep(this.currentStep - 1);
    },

    goToStep(step) {
        this.currentStep = step;

        // Update dots
        document.querySelectorAll('.progress-dots .dot').forEach((dot, i) => {
            dot.classList.toggle('active', i + 1 <= step);
        });

        // Update steps
        document.querySelectorAll('.onboarding-step').forEach((stepEl, i) => {
            stepEl.classList.toggle('active', i + 1 === step);
        });

        // Update buttons
        const prevBtn = document.getElementById('prev-step');
        const nextBtn = document.getElementById('next-step');

        if (prevBtn) prevBtn.style.visibility = step > 1 ? 'visible' : 'hidden';
        if (nextBtn) nextBtn.textContent = step >= this.totalSteps ? 'Get Started' : 'Next';
    }
};


// ============================================================================
// PERFORMANCE METRICS (Dev Mode)
// ============================================================================
const PerfMetrics = {
    enabled: false,
    metrics: {},

    init() {
        this.enabled = localStorage.getItem('dev-mode') === 'true';
        if (!this.enabled) return;

        this.injectPanel();
        this.track();
    },

    startTimer(label) {
        if (!this.enabled) return;
        this.metrics[label] = performance.now();
    },

    endTimer(label) {
        if (!this.enabled || !this.metrics[label]) return;
        const duration = performance.now() - this.metrics[label];
        console.log(`[Perf] ${label}: ${duration.toFixed(2)}ms`);
        this.updatePanel(label, duration);
        return duration;
    },

    injectPanel() {
        const panel = document.createElement('div');
        panel.id = 'perf-panel';
        panel.className = 'perf-panel';
        panel.innerHTML = '<h4>⚡ Performance</h4><div id="perf-metrics"></div>';
        document.body.appendChild(panel);
    },

    updatePanel(label, duration) {
        const container = document.getElementById('perf-metrics');
        if (!container) return;

        let metric = container.querySelector(`[data-metric="${label}"]`);
        if (!metric) {
            metric = document.createElement('div');
            metric.dataset.metric = label;
            container.appendChild(metric);
        }

        const status = duration < 100 ? 'good' : duration < 300 ? 'warn' : 'bad';
        metric.innerHTML = `<span>${label}</span><span class="${status}">${duration.toFixed(0)}ms</span>`;
    },

    track() {
        // Track navigation timing
        if (performance.getEntriesByType) {
            const nav = performance.getEntriesByType('navigation')[0];
            if (nav) {
                this.updatePanel('DOM Load', nav.domContentLoadedEventEnd);
                this.updatePanel('Full Load', nav.loadEventEnd);
            }
        }
    }
};


// ============================================================================
// SERVICE WORKER (PWA)
// ============================================================================
const PWA = {
    init() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/core/js/sw.js')
                .then(reg => console.log('SW registered'))
                .catch(err => console.log('SW registration failed:', err));
        }
    }
};


// ============================================================================
// PRINT STYLES
// ============================================================================
const PrintStyles = {
    init() {
        // Add print button handler
        document.querySelectorAll('[data-action="print"]').forEach(btn => {
            btn.addEventListener('click', () => window.print());
        });
    }
};


// ============================================================================
// INITIALIZE ALL
// ============================================================================
App.initPolish = function () {
    Interactions.init();
    Sounds.init();
    KeyboardNav.init();
    Onboarding.init();
    PerfMetrics.init();
    PrintStyles.init();
};

// Run on load
document.addEventListener('DOMContentLoaded', () => {
    App.initPolish();
    PWA.init();
});

// Expose for use
window.Sounds = Sounds;
window.ErrorRecovery = ErrorRecovery;
window.PerfMetrics = PerfMetrics;
