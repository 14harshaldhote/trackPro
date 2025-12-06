/**
 * Dropdown Manager
 * Handles dropdown menus and popovers
 */

import { dom } from '../utils/dom.js';

export class DropdownManager {
    constructor(app) {
        this.app = app;
        this.activeDropdown = null;
    }

    /**
     * Initialize dropdown manager
     */
    init() {
        // Set up document-wide click handler
        document.addEventListener('click', (e) => this.handleDocumentClick(e));

        // Initialize existing dropdowns
        this.initPanelDropdowns();
    }

    /**
     * Initialize dropdowns in current panel
     */
    initPanelDropdowns() {
        const toggles = dom.$$('.dropdown-toggle, [data-dropdown-toggle]');

        toggles.forEach(toggle => {
            // Remove existing listener to avoid duplicates
            toggle.removeEventListener('click', this.toggleHandler);

            // Add click handler
            toggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggle(toggle);
            });
        });
    }

    /**
     * Toggle dropdown
     */
    toggle(toggle) {
        const dropdown = toggle.closest('.dropdown');

        if (!dropdown) {
            console.error('Dropdown container not found');
            return;
        }

        const menu = dom.$('.dropdown-menu', dropdown);

        if (!menu) {
            console.error('Dropdown menu not found');
            return;
        }

        // Close if already open
        if (this.activeDropdown === dropdown) {
            this.close();
            return;
        }

        // Close any open dropdown
        this.close();

        // Open this dropdown
        this.open(dropdown, menu, toggle);
    }

    /**
     * Open dropdown
     */
    open(dropdown, menu, toggle) {
        // Add active class
        dropdown.classList.add('active');
        menu.classList.add('show');

        // Position menu
        this.position(menu, toggle);

        // Track active dropdown
        this.activeDropdown = dropdown;

        // Add keyboard navigation
        this.setupKeyboardNav(menu);
    }

    /**
     * Close active dropdown
     */
    close() {
        if (!this.activeDropdown) return;

        const menu = dom.$('.dropdown-menu', this.activeDropdown);

        // Remove active class
        this.activeDropdown.classList.remove('active');
        if (menu) {
            menu.classList.remove('show');
        }

        this.activeDropdown = null;
    }

    /**
     * Position dropdown menu
     */
    position(menu, toggle) {
        const toggleRect = toggle.getBoundingClientRect();
        const menuRect = menu.getBoundingClientRect();
        const viewportHeight = window.innerHeight;

        // Default: below toggle
        let placement = 'bottom';

        // Check if menu would overflow viewport
        const spaceBelow = viewportHeight - toggleRect.bottom;
        const spaceAbove = toggleRect.top;

        if (spaceBelow < menuRect.height && spaceAbove > spaceBelow) {
            placement = 'top';
        }

        // Apply placement
        menu.setAttribute('data-placement', placement);

        // Position relative to toggle
        if (placement === 'bottom') {
            menu.style.top = '100%';
            menu.style.bottom = 'auto';
        } else {
            menu.style.top = 'auto';
            menu.style.bottom = '100%';
        }
    }

    /**
     * Handle document clicks
     */
    handleDocumentClick(e) {
        // Close dropdown if clicked outside
        if (this.activeDropdown && !this.activeDropdown.contains(e.target)) {
            this.close();
        }
    }

    /**
     * Setup keyboard navigation
     */
    setupKeyboardNav(menu) {
        const items = dom.$$('.dropdown-item, a, button', menu);

        if (items.length === 0) return;

        let currentIndex = -1;

        menu.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                currentIndex = (currentIndex + 1) % items.length;
                items[currentIndex].focus();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                currentIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
                items[currentIndex].focus();
            } else if (e.key === 'Escape') {
                this.close();
            } else if (e.key === 'Enter' || e.key === ' ') {
                if (document.activeElement && items.includes(document.activeElement)) {
                    e.preventDefault();
                    document.activeElement.click();
                }
            }
        });

        // Focus first item
        items[0].focus();
    }
}
