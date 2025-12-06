/**
 * Notification System
 * Handles toast notifications and notification dropdown
 */

import { dom } from '../utils/dom.js';

export class NotificationSystem {
    constructor(app) {
        this.app = app;
        this.container = null;
        this.toasts = [];
        this.autoDismissDelay = 5000;
    }

    /**
     * Initialize notification system
     */
    init() {
        this.container = dom.$('#toast-container');

        if (!this.container) {
            // Create container if it doesn't exist
            this.container = dom.createElement('div', {
                id: 'toast-container',
                class: 'toast-container',
                role: 'status',
                'aria-live': 'polite'
            });
            document.body.appendChild(this.container);
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = null) {
        const toast = this.createToast(message, type);

        // Add to container
        this.container.appendChild(toast);
        this.toasts.push(toast);

        // Animate in
        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        // Auto dismiss
        const dismissDelay = duration || this.autoDismissDelay;
        setTimeout(() => {
            this.dismissToast(toast);
        }, dismissDelay);

        return toast;
    }

    /**
     * Create toast element
     */
    createToast(message, type) {
        // Icon based on type
        const icons = {
            success: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                      </svg>`,
            error: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                     <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                   </svg>`,
            warning: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                       <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                     </svg>`,
            info: `<svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                  </svg>`
        };

        const toast = dom.createElement('div', {
            class: `toast toast-${type}`,
            role: 'alert'
        });

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" aria-label="Dismiss">
                <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
            </button>
        `;

        // Add click to dismiss
        const closeBtn = dom.$('.toast-close', toast);
        closeBtn.addEventListener('click', () => this.dismissToast(toast));

        // Click anywhere on toast to dismiss
        toast.addEventListener('click', (e) => {
            if (e.target !== closeBtn && !closeBtn.contains(e.target)) {
                this.dismissToast(toast);
            }
        });

        return toast;
    }

    /**
     * Dismiss toast
     */
    dismissToast(toast) {
        toast.classList.remove('show');
        toast.classList.add('hide');

        setTimeout(() => {
            toast.remove();
            this.toasts = this.toasts.filter(t => t !== toast);
        }, 300);
    }

    /**
     * Clear all toasts
     */
    clearAll() {
        this.toasts.forEach(toast => this.dismissToast(toast));
    }
}

// Global helper function
window.showToast = function (message, type = 'info') {
    if (window.app && window.app.notifications) {
        return window.app.notifications.showToast(message, type);
    }
};
