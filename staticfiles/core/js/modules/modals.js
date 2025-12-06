/**
 * Modal System
 * Handles modal loading, display, and interactions
 */

import { ajax } from '../utils/ajax.js';
import { dom } from '../utils/dom.js';

export class ModalSystem {
    constructor(app) {
        this.app = app;
        this.overlay = null;
        this.container = null;
        this.backdrop = null;
        this.activeModal = null;
        this.modalStack = [];
    }

    /**
     * Initialize modal system
     */
    init() {
        this.overlay = dom.$('#modal-overlay');
        this.container = dom.$('#modal-container');
        this.backdrop = dom.$('.modal-backdrop');

        if (!this.overlay || !this.container) {
            console.error('Modal elements not found');
            return;
        }

        // Close on backdrop click
        if (this.backdrop) {
            this.backdrop.addEventListener('click', () => this.close());
        }

        // Close on escape key (handled by keyboard module)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activeModal) {
                this.close();
            }
        });
    }

    /**
     * Open a modal
     */
    async open(modalName, params = {}) {
        try {
            // Build URL with params
            const url = `/modals/${modalName}/`;
            const queryString = new URLSearchParams(params).toString();
            const fullUrl = queryString ? `${url}?${queryString}` : url;

            // Fetch modal content
            const html = await ajax.get(fullUrl);

            // Render modal
            this.render(html, modalName);

        } catch (error) {
            console.error('Failed to load modal:', error);
            this.app.notifications.showToast('Failed to open modal', 'error');
        }
    }

    /**
     * Render modal HTML
     */
    render(html, modalName) {
        // Set content
        this.container.innerHTML = html;

        // Show overlay
        this.overlay.classList.add('active');
        this.overlay.setAttribute('aria-hidden', 'false');

        // Animate in
        dom.fadeIn(this.overlay, 200);

        // Track modal
        this.activeModal = modalName;
        this.modalStack.push(modalName);

        // Trap focus
        this.trapFocus();

        // Initialize modal elements
        this.initModalElements();

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close active modal
     */
    close() {
        if (!this.activeModal) return;

        // Animate out
        dom.fadeOut(this.overlay, 200).then(() => {
            // Clear content
            this.container.innerHTML = '';

            // Hide overlay
            this.overlay.classList.remove('active');
            this.overlay.setAttribute('aria-hidden', 'true');

            // Remove from stack
            this.modalStack.pop();
            this.activeModal = this.modalStack[this.modalStack.length - 1] || null;

            // Restore body scroll
            document.body.style.overflow = '';

            // Restore focus
            this.restoreFocus();
        });
    }

    /**
     * Initialize modal interactive elements
     */
    initModalElements() {
        // Close buttons
        dom.$$('[data-action="close-modal"]', this.container).forEach(btn => {
            btn.addEventListener('click', () => this.close());
        });

        // Forms in modal
        const forms = dom.$$('form', this.container);
        forms.forEach(form => {
            this.app.forms.initForm(form);
        });

        // Focus first input
        const firstInput = dom.$('input:not([type="hidden"]), textarea, select', this.container);
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }

    /**
     * Trap focus within modal
     */
    trapFocus() {
        const focusableElements = dom.$$([
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])'
        ].join(','), this.container);

        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        this.container.addEventListener('keydown', (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        });
    }

    /**
     * Restore focus to trigger element
     */
    restoreFocus() {
        // Focus management for accessibility
        const mainContent = dom.$('#main-content');
        if (mainContent) {
            mainContent.focus();
        }
    }
}

// Global helper function
window.openModal = function (modalName, params = {}) {
    if (window.app && window.app.modals) {
        window.app.modals.open(modalName, params);
    }
};

window.closeModal = function () {
    if (window.app && window.app.modals) {
        window.app.modals.close();
    }
};
