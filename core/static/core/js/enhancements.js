/**
 * Keyboard Shortcuts & UX Enhancements
 * Global JavaScript for improved user experience
 */

// ===== KEYBOARD SHORTCUTS =====
class KeyboardShortcuts {
    constructor() {
        this.shortcuts = {
            '?': () => this.showShortcutsModal(),
            'n': () => this.navigateTo('/trackers/create/'),
            'h': () => this.navigateTo('/'),
            't': () => this.navigateTo('/templates/'),
            'Escape': () => this.closeModals(),
        };

        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger if typing in input
            if (e.target.matches('input, textarea')) return;

            const key = e.key;
            const action = this.shortcuts[key];

            if (action) {
                e.preventDefault();
                action();
            }
        });
    }

    navigateTo(url) {
        window.location.href = url;
    }

    closeModals() {
        document.querySelectorAll('.modal, .tour-overlay').forEach(modal => {
            modal.style.display = 'none';
            modal.classList.remove('active');
        });
    }

    showShortcutsModal() {
        const modal = document.getElementById('shortcutsModal');
        if (modal) {
            modal.style.display = 'flex';
        } else {
            this.createShortcutsModal();
        }
    }

    createShortcutsModal() {
        const modal = document.createElement('div');
        modal.id = 'shortcutsModal';
        modal.className = 'modal';
        modal.style.cssText = 'display: flex; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; z-index: 10000;';

        modal.innerHTML = `
            <div class="card" style="max-width: 500px; margin: 2rem;">
                <h2 style="margin-bottom: 1.5rem;">⌨️ Keyboard Shortcuts</h2>
                
                <div class="shortcut-list">
                    <div class="shortcut-item">
                        <span>Show this help</span>
                        <kbd class="kbd">?</kbd>
                    </div>
                    <div class="shortcut-item">
                        <span>Go to Home</span>
                        <kbd class="kbd">H</kbd>
                    </div>
                    <div class="shortcut-item">
                        <span>New Tracker</span>
                        <kbd class="kbd">N</kbd>
                    </div>
                    <div class="shortcut-item">
                        <span>Templates</span>
                        <kbd class="kbd">T</kbd>
                    </div>
                    <div class="shortcut-item">
                        <span>Close Modal</span>
                        <kbd class="kbd">Esc</kbd>
                    </div>
                </div>
                
                <button onclick="document.getElementById('shortcutsModal').style.display='none'" class="btn btn-primary" style="margin-top: 1.5rem; width: 100%;">
                    Got it!
                </button>
            </div>
        `;

        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
}

// ===== DRAG AND DROP FOR TASK REORDERING =====
class DragDropManager {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        if (!this.container) return;

        this.init();
    }

    init() {
        const items = this.container.querySelectorAll('.draggable');

        items.forEach((item, index) => {
            item.setAttribute('draggable', 'true');
            item.dataset.index = index;

            item.addEventListener('dragstart', this.handleDragStart.bind(this));
            item.addEventListener('dragover', this.handleDragOver.bind(this));
            item.addEventListener('drop', this.handleDrop.bind(this));
            item.addEventListener('dragend', this.handleDragEnd.bind(this));
        });
    }

    handleDragStart(e) {
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', e.target.innerHTML);
        e.dataTransfer.setData('index', e.target.dataset.index);
    }

    handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault();
        }
        e.dataTransfer.dropEffect = 'move';

        const dragging = document.querySelector('.dragging');
        if (e.target.classList.contains('draggable') && e.target !== dragging) {
            e.target.classList.add('drag-over');
        }

        return false;
    }

    handleDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation();
        }

        e.target.classList.remove('drag-over');

        const dragging = document.querySelector('.dragging');
        if (e.target.classList.contains('draggable') && e.target !== dragging) {
            // Swap elements
            const fromIndex = parseInt(dragging.dataset.index);
            const toIndex = parseInt(e.target.dataset.index);

            this.reorderItems(fromIndex, toIndex);
            this.saveOrder();
        }

        return false;
    }

    handleDragEnd(e) {
        e.target.classList.remove('dragging');
        document.querySelectorAll('.drag-over').forEach(item => {
            item.classList.remove('drag-over');
        });
    }

    reorderItems(fromIndex, toIndex) {
        const items = Array.from(this.container.querySelectorAll('.draggable'));
        const [movedItem] = items.splice(fromIndex, 1);
        items.splice(toIndex, 0, movedItem);

        // Re-render
        items.forEach((item, index) => {
            item.dataset.index = index;
            this.container.appendChild(item);
        });
    }

    saveOrder() {
        // Send to backend
        const items = this.container.querySelectorAll('.draggable');
        const order = Array.from(items).map(item => item.dataset.id);

        fetch('/api/tasks/reorder/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ order: order })
        });

        showToast('Order saved!', 'success');
    }
}

// ===== ONBOARDING TOUR =====
class OnboardingTour {
    constructor(steps) {
        this.steps = steps;
        this.currentStep = 0;
        this.overlay = null;
        this.init();
    }

    init() {
        // Check if user has seen tour
        if (localStorage.getItem('tourCompleted')) return;

        // Show tour after short delay
        setTimeout(() => this.start(), 1000);
    }

    start() {
        this.createOverlay();
        this.showStep(0);
    }

    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay active';
        document.body.appendChild(this.overlay);
    }

    showStep(index) {
        if (index >= this.steps.length) {
            this.complete();
            return;
        }

        this.currentStep = index;
        const step = this.steps[index];

        // Create spotlight
        const element = document.querySelector(step.element);
        if (!element) {
            this.next();
            return;
        }

        const rect = element.getBoundingClientRect();

        // Remove old spotlight
        const oldSpotlight = document.querySelector('.tour-spotlight');
        if (oldSpotlight) oldSpotlight.remove();

        const spotlight = document.createElement('div');
        spotlight.className = 'tour-spotlight';
        spotlight.style.top = rect.top + 'px';
        spotlight.style.left = rect.left + 'px';
        spotlight.style.width = rect.width + 'px';
        spotlight.style.height = rect.height + 'px';
        document.body.appendChild(spotlight);

        // Show tooltip
        this.showTooltip(step, rect);
    }

    showTooltip(step, rect) {
        const oldTooltip = document.querySelector('.tour-tooltip');
        if (oldTooltip) oldTooltip.remove();

        const tooltip = document.createElement('div');
        tooltip.className = 'tour-tooltip fade-in-up';
        tooltip.innerHTML = `
            <h3>${step.title}</h3>
            <p>${step.content}</p>
            <div class="tour-controls">
                <span class="tour-progress">${this.currentStep + 1} / ${this.steps.length}</span>
                <div style="display: flex; gap: 0.5rem;">
                    ${this.currentStep > 0 ? '<button onclick="tour.previous()" class="btn btn-ghost btn-sm">Previous</button>' : ''}
                    <button onclick="tour.skip()" class="btn btn-ghost btn-sm">Skip Tour</button>
                    <button onclick="tour.next()" class="btn btn-primary btn-sm">
                        ${this.currentStep === this.steps.length - 1 ? 'Finish' : 'Next'}
                    </button>
                </div>
            </div>
        `;

        // Position tooltip
        tooltip.style.top = (rect.bottom + 20) + 'px';
        tooltip.style.left = Math.max(20, rect.left) + 'px';

        document.body.appendChild(tooltip);
    }

    next() {
        this.showStep(this.currentStep + 1);
    }

    previous() {
        this.showStep(this.currentStep - 1);
    }

    skip() {
        this.complete();
    }

    complete() {
        localStorage.setItem('tourCompleted', 'true');
        this.cleanup();
        showToast('Tour completed! Press ? anytime for keyboard shortcuts.', 'success');
    }

    cleanup() {
        if (this.overlay) this.overlay.remove();
        document.querySelectorAll('.tour-spotlight, .tour-tooltip').forEach(el => el.remove());
    }
}

// ===== TOAST NOTIFICATIONS =====
function showToast(message, type = 'info', duration = 3000) {
    const container = document.querySelector('.toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            ${type === 'success' ? '✓' : type === 'error' ? '✗' : type === 'warning' ? '⚠' : 'ℹ'}
        </div>
        <div class="toast-content">
            <div class="toast-message">${message}</div>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// ===== UTILITY FUNCTIONS =====
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function showLoadingOverlay() {
    let overlay = document.querySelector('.loading-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = '<div class="loading-spinner loading-spinner-lg"></div>';
        document.body.appendChild(overlay);
    }
    overlay.classList.add('active');
}

function hideLoadingOverlay() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    // Initialize keyboard shortcuts
    new KeyboardShortcuts();

    // Initialize drag-drop if on manage tasks page
    if (document.querySelector('.task-list-container')) {
        new DragDropManager('.task-list-container');
    }

    // Initialize tour for first-time users
    if (document.querySelector('.dashboard') && !localStorage.getItem('tourCompleted')) {
        window.tour = new OnboardingTour([
            {
                element: '.sidebar a[href="/"]',
                title: 'Welcome to Tracker Pro!',
                content: 'This is your dashboard. Let\'s take a quick tour of the key features.'
            },
            {
                element: '.sidebar a[href="/trackers/create/"]',
                title: 'Create a Tracker',
                content: 'Click here to create a new habit tracker. Choose from templates or start from scratch.'
            },
            {
                element: '.card:first-child',
                title: 'Your Trackers',
                content: 'All your trackers appear here. Click on any tracker to view details and track your progress.'
            },
            {
                element: '.sidebar a[href="/help/"]',
                title: 'Need Help?',
                content: 'Visit the Help Center anytime for guides and FAQs. Press ? for keyboard shortcuts!'
            }
        ]);
    }
});

// Make tour globally accessible
window.showToast = showToast;
window.showLoadingOverlay = showLoadingOverlay;
window.hideLoadingOverlay = hideLoadingOverlay;
