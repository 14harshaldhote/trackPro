/**
 * UI Module
 * Handles tooltips, toasts, dropdowns, and other visual interactions.
 */

export class UIManager {
    constructor() {
        this.init();
        this.toastContainer = document.getElementById('toast-container');
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.className = 'fixed bottom-4 right-4 flex flex-col gap-2 z-50 pointer-events-none'; // Ensure clicks pass through empty area
            document.body.appendChild(this.toastContainer);
        }
    }

    init() {
        // Dropdown Logic
        document.addEventListener('click', (e) => {
            const toggle = e.target.closest('[data-dropdown-toggle]');
            if (toggle) {
                const targetId = toggle.dataset.dropdownToggle;
                const dropdownObj = document.getElementById(`dropdown-${targetId}`);
                if (dropdownObj) {
                    console.log(`[UI] Toggling dropdown: dropdown-${targetId}`);
                    dropdownObj.classList.toggle('show');
                    dropdownObj.classList.toggle('hidden'); // compatibility
                }
            } else {
                // Close all dropdowns if clicking outside
                if (!e.target.closest('.dropdown-menu')) {
                    const visibleDropdowns = document.querySelectorAll('.dropdown-menu.show');
                    if (visibleDropdowns.length > 0) {
                        console.log('[UI] Closing all dropdowns (clicked outside)');
                        visibleDropdowns.forEach(el => {
                            el.classList.remove('show');
                            el.classList.add('hidden');
                        });
                    }
                }
            }
        });

        // Simple Tooltip Logic (HTML title replacement or custom)
        // For now, rely on native title or upgrade later. 
        // Providing a placeholder for advanced tooltip integration.
        console.log('[UI] Initialized');
    }

    showToast(message, type = 'info') {
        console.log(`[UI] 🍞 Toast: [${type}] ${message}`);
        const toast = document.createElement('div');

        const colors = {
            'success': 'bg-surface text-success border-success',
            'error': 'bg-surface text-error border-error',
            'info': 'bg-surface text-primary border-primary'
        };

        toast.className = `p-4 rounded-lg shadow-lg border-l-4 pointer-events-auto flex items-center gap-3 transform transition-all duration-300 translate-y-full opacity-0 ${colors[type] || colors.info}`;
        toast.innerHTML = `
            <span class="font-medium">${message}</span>
        `;

        this.toastContainer.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-y-full', 'opacity-0');
        });

        // Remove after 3s
        setTimeout(() => {
            toast.classList.add('translate-y-full', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    createConfetti(element) {
        // Placeholder for celebration effect
        // Could import a library like canvas-confetti
        console.log('[UI] 🎉 Confetti triggered at', element);
    }
}

export const ui = new UIManager();
