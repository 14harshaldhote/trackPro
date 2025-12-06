/**
 * Modals Module
 * Handles opening, closing, and stacking of modals.
 */
import { api } from './api.js';

export class ModalManager {
    constructor() {
        this.overlay = document.getElementById('modal-overlay');
        this.container = document.getElementById('modal-container');
        this.activeModal = null;

        this.bindEvents();

        // Expose global helper for inline HTML calls (onclick="window.openModal(...)")
        window.openModal = this.open.bind(this);
        window.closeModal = this.close.bind(this);
    }

    bindEvents() {
        // Close on backdrop click
        if (this.overlay) {
            this.overlay.addEventListener('click', (e) => {
                if (e.target === this.overlay || e.target.dataset.action === 'close-modal') {
                    this.close();
                }
            });
        }

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activeModal) {
                this.close();
            }
        });

        // Delegate internal close buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-action="close-modal"]')) {
                this.close();
            }
        });
    }

    async open(modalName, context = {}) {
        console.log(`[Modals] 🔓 Opening modal: ${modalName}`, context);
        this.activeModal = modalName;

        // Show overlay with loading state
        this.overlay.classList.add('active');
        this.overlay.style.visibility = 'visible';
        this.overlay.style.opacity = '1';
        this.container.innerHTML = '<div class="p-8 text-center"><div class="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto"></div></div>';

        try {
            // Check if modal exists in DOM (pre-rendered) first
            const existingModal = document.getElementById(`modal-${modalName}`);
            if (existingModal) {
                console.log(`[Modals] Found pre-rendered modal: modal-${modalName}`);
                this.container.innerHTML = '';
                this.container.appendChild(existingModal.content.cloneNode(true));
            } else {
                console.log(`[Modals] Fetching modal content from server...`);
                const html = await api.getPanel(`/modals/${modalName}/`);
                console.log(`[Modals] Content received`);
                this.container.innerHTML = html;

                // Execute script tags in loaded content
                this.executeScripts(this.container);
            }

            // Focus first input
            const input = this.container.querySelector('input, button');
            if (input) input.focus();

        } catch (error) {
            console.error(`[Modals] ❌ Failed to open modal ${modalName}:`, error);
            this.container.innerHTML = `
                <div class="p-6 text-center text-error">
                    <p>Failed to load ${modalName}</p>
                    <button class="btn btn-secondary mt-4" onclick="closeModal()">Close</button>
                </div>
            `;
        }
    }

    /**
     * Execute script tags in dynamically loaded content
     * innerHTML doesn't execute scripts, so we need to do it manually
     */
    executeScripts(container) {
        const scripts = container.querySelectorAll('script');
        scripts.forEach((script) => {
            const newScript = document.createElement('script');

            // Copy attributes
            Array.from(script.attributes).forEach(attr => {
                newScript.setAttribute(attr.name, attr.value);
            });

            // Copy content
            newScript.textContent = script.textContent;

            // Replace old script with new one to execute it
            script.parentNode.replaceChild(newScript, script);
            console.log('[Modals] Executed inline script');
        });
    }

    close() {
        if (!this.activeModal) return;
        console.log(`[Modals] 🔒 Closing modal: ${this.activeModal}`);
        this.overlay.classList.remove('active');
        this.overlay.style.visibility = 'hidden';
        this.overlay.style.opacity = '0';
        setTimeout(() => {
            this.container.innerHTML = '';
            this.activeModal = null;
        }, 300); // Wait for transition
    }
}

export const modals = new ModalManager();
