/**
 * Tracker Pro - Polish & Enhancements
 * Micro-interactions, sounds, keyboard nav, error recovery, PWA
 * With comprehensive console logging for debugging
 */

// Console logging helper
const polishLog = (module, action, data = {}) => {
    const timestamp = new Date().toISOString();
    const logData = { timestamp, module, action, ...data };
    const emoji = data.status === 'SUCCESS' ? '✅' :
        data.status === 'ERROR' ? '❌' :
            data.status === 'WARNING' ? '⚠️' : 'ℹ️';
    console.log(`[Polish/${module}] ${emoji} ${action}`, logData);
};

// ============================================================================
// MICRO-INTERACTIONS
// ============================================================================
const Interactions = {
    init() {
        polishLog('Interactions', 'INIT_START', { status: 'INFO', message: 'Initializing micro-interactions' });
        this.bindRippleEffect();
        this.bindButtonPress();
        this.bindHoverEffects();
        polishLog('Interactions', 'INIT_COMPLETE', { status: 'SUCCESS', message: 'Micro-interactions ready' });
    },

    bindRippleEffect() {
        polishLog('Interactions', 'RIPPLE_BIND', { status: 'INFO', message: 'Binding ripple effect listener' });
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn, .nav-item, .sidebar-item');
            if (!btn || btn.classList.contains('no-ripple')) return;

            polishLog('Interactions', 'RIPPLE_TRIGGER', {
                status: 'SUCCESS',
                element: btn.className,
                x: e.clientX,
                y: e.clientY,
                message: 'Ripple effect triggered'
            });

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
        polishLog('Interactions', 'BUTTON_PRESS_BIND', { status: 'INFO', message: 'Binding button press effects' });
        document.addEventListener('mousedown', (e) => {
            const btn = e.target.closest('.btn');
            if (btn) {
                btn.classList.add('pressed');
                polishLog('Interactions', 'BUTTON_PRESSED', {
                    status: 'SUCCESS',
                    element: btn.className,
                    message: 'Button pressed'
                });
            }
        });

        document.addEventListener('mouseup', () => {
            document.querySelectorAll('.btn.pressed').forEach(btn => {
                btn.classList.remove('pressed');
            });
        });
    },

    bindHoverEffects() {
        const cards = document.querySelectorAll('.tracker-card, .goal-card, .stat-card');
        polishLog('Interactions', 'HOVER_BIND', {
            status: 'INFO',
            cardCount: cards.length,
            message: `Binding hover effects to ${cards.length} cards`
        });

        cards.forEach(card => {
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
        polishLog('Sounds', 'INIT_COMPLETE', {
            status: 'SUCCESS',
            enabled: this.enabled,
            volume: this.volume,
            message: `Sounds ${this.enabled ? 'enabled' : 'disabled'} at ${this.volume * 100}% volume`
        });
    },

    play(soundName) {
        if (!this.enabled) {
            polishLog('Sounds', 'PLAY_SKIP', {
                status: 'INFO',
                soundName,
                message: 'Sound playback disabled'
            });
            return;
        }

        const src = this.sounds[soundName];
        if (!src) {
            polishLog('Sounds', 'PLAY_ERROR', {
                status: 'WARNING',
                soundName,
                message: `Sound "${soundName}" not found`
            });
            return;
        }

        try {
            const audio = new Audio(src);
            audio.volume = this.volume;
            audio.play().then(() => {
                polishLog('Sounds', 'PLAY_SUCCESS', {
                    status: 'SUCCESS',
                    soundName,
                    url: src,
                    volume: this.volume,
                    message: `Playing sound: ${soundName}`
                });
            }).catch((err) => {
                polishLog('Sounds', 'PLAY_ERROR', {
                    status: 'WARNING',
                    soundName,
                    url: src,
                    error: err.message,
                    message: 'Autoplay blocked or sound failed'
                });
            });
        } catch (e) {
            polishLog('Sounds', 'PLAY_EXCEPTION', {
                status: 'ERROR',
                soundName,
                error: e.message,
                message: 'Sound playback exception'
            });
        }
    },

    setEnabled(enabled) {
        this.enabled = enabled;
        localStorage.setItem('sounds-enabled', enabled);
        polishLog('Sounds', 'SET_ENABLED', {
            status: 'SUCCESS',
            enabled,
            message: `Sounds ${enabled ? 'enabled' : 'disabled'}`
        });
    },

    setVolume(volume) {
        this.volume = volume;
        localStorage.setItem('sounds-volume', volume);
        polishLog('Sounds', 'SET_VOLUME', {
            status: 'SUCCESS',
            volume,
            message: `Volume set to ${volume * 100}%`
        });
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
        polishLog('KeyboardNav', 'INIT_START', {
            status: 'INFO',
            enabled: this.enabled,
            message: 'Initializing keyboard navigation'
        });

        if (!this.enabled) {
            polishLog('KeyboardNav', 'INIT_SKIP', {
                status: 'INFO',
                message: 'Keyboard navigation disabled by user preference'
            });
            return;
        }

        document.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.bindShortcuts();
        polishLog('KeyboardNav', 'INIT_COMPLETE', {
            status: 'SUCCESS',
            message: 'Keyboard navigation ready'
        });
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
                polishLog('KeyboardNav', 'INPUT_ESCAPE', {
                    status: 'INFO',
                    key: e.key,
                    message: 'Escaped from input field'
                });
            }
            return;
        }

        polishLog('KeyboardNav', 'KEYDOWN', {
            status: 'INFO',
            key: e.key,
            message: `Key pressed: ${e.key}`
        });

        switch (e.key) {
            case 'g':
                this.waitingForNav = true;
                polishLog('KeyboardNav', 'NAV_MODE_START', {
                    status: 'INFO',
                    message: 'Waiting for navigation key...'
                });
                setTimeout(() => this.waitingForNav = false, 1000);
                break;

            case '?':
                polishLog('KeyboardNav', 'SHORTCUTS_MODAL', {
                    status: 'INFO',
                    message: 'Opening shortcuts modal'
                });
                App.showShortcutsModal?.();
                break;

            case '/':
                e.preventDefault();
                polishLog('KeyboardNav', 'FOCUS_SEARCH', {
                    status: 'SUCCESS',
                    message: 'Focusing search input'
                });
                document.querySelector('.search-input')?.focus();
                break;

            case 'n':
                e.preventDefault();
                polishLog('KeyboardNav', 'NEW_TRACKER', {
                    status: 'INFO',
                    message: 'Opening new tracker modal'
                });
                App.openModal?.('add-tracker');
                break;

            case 'a':
                e.preventDefault();
                polishLog('KeyboardNav', 'QUICK_ADD', {
                    status: 'SUCCESS',
                    message: 'Focusing quick add input'
                });
                document.querySelector('.quick-add-input')?.focus();
                break;

            case 'Escape':
                polishLog('KeyboardNav', 'CLOSE_MODAL', {
                    status: 'INFO',
                    message: 'Closing modal via Escape'
                });
                App.closeModal?.();
                break;

            case 'ArrowUp':
            case 'ArrowDown':
                polishLog('KeyboardNav', 'NAVIGATE_LIST', {
                    status: 'INFO',
                    direction: e.key === 'ArrowUp' ? 'up' : 'down',
                    message: `Navigating list ${e.key === 'ArrowUp' ? 'up' : 'down'}`
                });
                this.navigateList(e.key === 'ArrowUp' ? -1 : 1);
                e.preventDefault();
                break;

            case ' ':
                polishLog('KeyboardNav', 'TOGGLE_ITEM', {
                    status: 'INFO',
                    message: 'Toggling current item via Space'
                });
                this.toggleCurrentItem();
                e.preventDefault();
                break;

            case '[':
                polishLog('KeyboardNav', 'TOGGLE_SIDEBAR', {
                    status: 'INFO',
                    message: 'Toggling sidebar'
                });
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
            polishLog('KeyboardNav', 'NAVIGATE', {
                status: 'SUCCESS',
                key: e.key,
                url: route,
                message: `Navigating to ${route}`
            });
            App.loadPanel?.(route);
        } else {
            polishLog('KeyboardNav', 'NAV_UNKNOWN', {
                status: 'WARNING',
                key: e.key,
                message: `Unknown navigation key: ${e.key}`
            });
        }
    },

    navigateList(direction) {
        const items = document.querySelectorAll('.task-row, .tracker-card');
        if (!items.length) {
            polishLog('KeyboardNav', 'LIST_EMPTY', {
                status: 'WARNING',
                message: 'No items to navigate'
            });
            return;
        }

        const focused = document.querySelector('.task-row.keyboard-focus, .tracker-card.keyboard-focus');

        items.forEach(item => item.classList.remove('keyboard-focus'));

        if (focused) {
            const index = Array.from(items).indexOf(focused);
            const newIndex = Math.max(0, Math.min(items.length - 1, index + direction));
            items[newIndex].classList.add('keyboard-focus');
            items[newIndex].scrollIntoView({ block: 'nearest' });
            polishLog('KeyboardNav', 'LIST_NAVIGATE', {
                status: 'SUCCESS',
                fromIndex: index,
                toIndex: newIndex,
                itemCount: items.length,
                message: `Navigated to item ${newIndex + 1} of ${items.length}`
            });
        } else {
            items[direction > 0 ? 0 : items.length - 1].classList.add('keyboard-focus');
        }
    },

    toggleCurrentItem() {
        const focused = document.querySelector('.task-row.keyboard-focus');
        if (focused) {
            polishLog('KeyboardNav', 'TOGGLE_FOCUSED', {
                status: 'SUCCESS',
                taskId: focused.dataset.taskId,
                message: 'Toggling focused item'
            });
            focused.querySelector('.status-icon, [data-action="toggle"]')?.click();
        } else {
            polishLog('KeyboardNav', 'TOGGLE_NO_FOCUS', {
                status: 'WARNING',
                message: 'No focused item to toggle'
            });
        }
    },

    bindShortcuts() {
        // Cmd/Ctrl + K for search
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                polishLog('KeyboardNav', 'CMD_K', {
                    status: 'SUCCESS',
                    message: 'Cmd/Ctrl+K: Focusing search'
                });
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
        const method = options.method || 'GET';
        const key = `${method}-${url}`;

        polishLog('ErrorRecovery', 'FETCH_START', {
            status: 'INFO',
            url,
            method,
            retriesRemaining: retries,
            message: `Fetching ${url} (${retries} retries left)`
        });

        try {
            const response = await fetch(url, options);

            if (!response.ok && response.status >= 500) {
                polishLog('ErrorRecovery', 'FETCH_SERVER_ERROR', {
                    status: 'ERROR',
                    url,
                    method,
                    responseStatus: response.status,
                    message: `Server error: ${response.status}`
                });
                throw new Error(`Server error: ${response.status}`);
            }

            this.pendingRequests.delete(key);
            polishLog('ErrorRecovery', 'FETCH_SUCCESS', {
                status: 'SUCCESS',
                url,
                method,
                responseStatus: response.status,
                message: `Request successful (${response.status})`
            });
            return response;

        } catch (error) {
            if (retries > 0) {
                polishLog('ErrorRecovery', 'FETCH_RETRY', {
                    status: 'WARNING',
                    url,
                    method,
                    error: error.message,
                    retriesRemaining: retries - 1,
                    retryDelay: this.retryDelay * (this.maxRetries - retries + 1),
                    message: `Retrying... (${retries - 1} attempts left)`
                });
                this.showRetryToast(retries);
                await this.delay(this.retryDelay * (this.maxRetries - retries + 1));
                return this.fetchWithRetry(url, options, retries - 1);
            }

            polishLog('ErrorRecovery', 'FETCH_FAILED', {
                status: 'ERROR',
                url,
                method,
                error: error.message,
                message: 'All retries exhausted'
            });
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
        polishLog('Onboarding', 'INIT_CHECK', {
            status: 'INFO',
            message: 'Checking onboarding status'
        });

        if (localStorage.getItem('onboarding-complete')) {
            polishLog('Onboarding', 'INIT_SKIP', {
                status: 'INFO',
                message: 'Onboarding already completed'
            });
            return;
        }

        // Check if first time user
        if (this.isNewUser()) {
            polishLog('Onboarding', 'INIT_SHOW', {
                status: 'SUCCESS',
                message: 'New user detected, showing onboarding'
            });
            this.show();
        }
    },

    isNewUser() {
        // Check URL param or API flag
        return new URLSearchParams(window.location.search).has('welcome');
    },

    show() {
        const overlay = document.getElementById('onboarding-overlay');
        if (!overlay) {
            polishLog('Onboarding', 'SHOW_ERROR', {
                status: 'WARNING',
                message: 'Onboarding overlay not found'
            });
            return;
        }

        overlay.style.display = 'flex';
        this.bindEvents();
        polishLog('Onboarding', 'SHOW_SUCCESS', {
            status: 'SUCCESS',
            message: 'Onboarding overlay displayed'
        });
    },

    hide() {
        const overlay = document.getElementById('onboarding-overlay');
        if (overlay) overlay.style.display = 'none';
        localStorage.setItem('onboarding-complete', 'true');
        polishLog('Onboarding', 'HIDE', {
            status: 'SUCCESS',
            message: 'Onboarding completed and hidden'
        });
    },

    bindEvents() {
        document.getElementById('skip-onboarding')?.addEventListener('click', () => {
            polishLog('Onboarding', 'SKIP', {
                status: 'INFO',
                currentStep: this.currentStep,
                message: 'User skipped onboarding'
            });
            this.hide();
        });
        document.getElementById('next-step')?.addEventListener('click', () => this.nextStep());
        document.getElementById('prev-step')?.addEventListener('click', () => this.prevStep());
    },

    nextStep() {
        if (this.currentStep >= this.totalSteps) {
            polishLog('Onboarding', 'COMPLETE', {
                status: 'SUCCESS',
                totalSteps: this.totalSteps,
                message: 'Onboarding completed'
            });
            this.hide();
            return;
        }
        polishLog('Onboarding', 'NEXT_STEP', {
            status: 'INFO',
            fromStep: this.currentStep,
            toStep: this.currentStep + 1,
            message: `Moving to step ${this.currentStep + 1}`
        });
        this.goToStep(this.currentStep + 1);
    },

    prevStep() {
        if (this.currentStep <= 1) return;
        polishLog('Onboarding', 'PREV_STEP', {
            status: 'INFO',
            fromStep: this.currentStep,
            toStep: this.currentStep - 1,
            message: `Going back to step ${this.currentStep - 1}`
        });
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
        polishLog('PerfMetrics', 'INIT', {
            status: 'INFO',
            enabled: this.enabled,
            message: `Performance metrics ${this.enabled ? 'enabled' : 'disabled'}`
        });

        if (!this.enabled) return;

        this.injectPanel();
        this.track();
    },

    startTimer(label) {
        if (!this.enabled) return;
        this.metrics[label] = performance.now();
        polishLog('PerfMetrics', 'TIMER_START', {
            status: 'INFO',
            label,
            startTime: this.metrics[label],
            message: `Timer started: ${label}`
        });
    },

    endTimer(label) {
        if (!this.enabled || !this.metrics[label]) return;
        const duration = performance.now() - this.metrics[label];
        polishLog('PerfMetrics', 'TIMER_END', {
            status: 'SUCCESS',
            label,
            duration: `${duration.toFixed(2)}ms`,
            message: `${label}: ${duration.toFixed(2)}ms`
        });
        this.updatePanel(label, duration);
        return duration;
    },

    injectPanel() {
        const panel = document.createElement('div');
        panel.id = 'perf-panel';
        panel.className = 'perf-panel';
        panel.innerHTML = '<h4>⚡ Performance</h4><div id="perf-metrics"></div>';
        document.body.appendChild(panel);
        polishLog('PerfMetrics', 'PANEL_INJECTED', {
            status: 'SUCCESS',
            message: 'Performance panel injected'
        });
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
                polishLog('PerfMetrics', 'NAV_TIMING', {
                    status: 'SUCCESS',
                    domLoad: `${nav.domContentLoadedEventEnd.toFixed(0)}ms`,
                    fullLoad: `${nav.loadEventEnd.toFixed(0)}ms`,
                    message: 'Navigation timing captured'
                });
            }
        }
    }
};


// ============================================================================
// SERVICE WORKER (PWA)
// ============================================================================
const PWA = {
    init() {
        polishLog('PWA', 'INIT_CHECK', {
            status: 'INFO',
            serviceWorkerSupported: 'serviceWorker' in navigator,
            message: 'Checking PWA support'
        });

        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/core/js/sw.js')
                .then(reg => {
                    polishLog('PWA', 'SW_REGISTERED', {
                        status: 'SUCCESS',
                        url: '/static/core/js/sw.js',
                        scope: reg.scope,
                        message: 'Service Worker registered'
                    });
                })
                .catch(err => {
                    polishLog('PWA', 'SW_REGISTER_ERROR', {
                        status: 'ERROR',
                        url: '/static/core/js/sw.js',
                        error: err.message,
                        message: 'Service Worker registration failed'
                    });
                });
        } else {
            polishLog('PWA', 'SW_NOT_SUPPORTED', {
                status: 'WARNING',
                message: 'Service Worker not supported in this browser'
            });
        }
    }
};


// ============================================================================
// PRINT STYLES
// ============================================================================
const PrintStyles = {
    init() {
        const printBtns = document.querySelectorAll('[data-action="print"]');
        polishLog('PrintStyles', 'INIT', {
            status: 'INFO',
            buttonCount: printBtns.length,
            message: `Found ${printBtns.length} print button(s)`
        });

        printBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                polishLog('PrintStyles', 'PRINT_TRIGGERED', {
                    status: 'SUCCESS',
                    message: 'Print dialog opened'
                });
                window.print();
            });
        });
    }
};


// ============================================================================
// INITIALIZE ALL
// ============================================================================
App.initPolish = function () {
    polishLog('Init', 'POLISH_START', {
        status: 'INFO',
        message: 'Initializing all polish modules'
    });
    Interactions.init();
    Sounds.init();
    KeyboardNav.init();
    Onboarding.init();
    PerfMetrics.init();
    PrintStyles.init();
    polishLog('Init', 'POLISH_COMPLETE', {
        status: 'SUCCESS',
        message: 'All polish modules initialized'
    });
};

// Run on load
document.addEventListener('DOMContentLoaded', () => {
    polishLog('Init', 'DOM_READY', {
        status: 'INFO',
        message: 'DOM content loaded, starting initialization'
    });
    App.initPolish();
    PWA.init();
});

// Expose for use
window.Sounds = Sounds;
window.ErrorRecovery = ErrorRecovery;
window.PerfMetrics = PerfMetrics;
