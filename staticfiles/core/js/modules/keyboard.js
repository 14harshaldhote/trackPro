/**
 * Keyboard Shortcuts
 * Global keyboard shortcut handler
 */

import { dom } from '../utils/dom.js';

export class KeyboardShortcuts {
    constructor(app) {
        this.app = app;
        this.shortcuts = new Map();
        this.enabled = true;
    }

    /**
     * Initialize keyboard shortcuts
     */
    init() {
        // Register all shortcuts
        this.registerShortcuts();

        // Set up global key handler
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
    }

    /**
     * Register all keyboard shortcuts
     */
    registerShortcuts() {
        // Global shortcuts
        this.register('ctrl+k', () => this.openSearch(), 'Open search');
        this.register('cmd+k', () => this.openSearch(), 'Open search');
        this.register('ctrl+n', () => window.openModal('add-tracker'), 'New tracker');
        this.register('cmd+n', () => window.openModal('add-tracker'), 'New tracker');
        this.register('ctrl+t', () => window.openModal('quick-add'), 'Quick add task');
        this.register('cmd+t', () => window.openModal('quick-add'), 'Quick add task');
        this.register('?', () => this.showShortcutsModal(), 'Show shortcuts');
        this.register('escape', () => this.handleEscape(), 'Close modal/dropdown');

        // Navigation shortcuts
        this.register('d', () => this.app.router.navigate('/'), 'Dashboard');
        this.register('t', () => this.app.router.navigate('/today/'), 'Today');
        this.register('w', () => this.app.router.navigate('/week/'), 'Week');
        this.register('m', () => this.app.router.navigate('/month/'), 'Month');
        this.register('a', () => this.app.router.navigate('/analytics/'), 'Analytics');
        this.register('g', () => this.app.router.navigate('/goals/'), 'Goals');
        this.register('h', () => this.app.router.navigate('/help/'), 'Help');
        this.register('s', () => this.app.router.navigate('/settings/'), 'Settings');

        // Dashboard filter shortcuts
        this.register('1', () => this.setFilter('daily'), 'Daily view');
        this.register('2', () => this.setFilter('weekly'), 'Weekly view');
        this.register('3', () => this.setFilter('monthly'), 'Monthly view');
        this.register('4', () => this.setFilter('all'), 'All view');

        // Date navigation
        this.register('arrowleft', () => this.navigateDate('prev'), 'Previous day/week/month');
        this.register('arrowright', () => this.navigateDate('next'), 'Next day/week/month');
        this.register('.', () => this.navigateDate('today'), 'Jump to today');

        // Task actions (when task focused)
        this.register('space', () => this.toggleTask(), 'Toggle task');
        this.register('e', () => this.editTask(), 'Edit task');
        this.register('delete', () => this.deleteTask(), 'Delete task');
        this.register('backspace', () => this.deleteTask(), 'Delete task');
    }

    /**
     * Register a keyboard shortcut
     */
    register(key, handler, description = '') {
        this.shortcuts.set(key.toLowerCase(), { handler, description });
    }

    /**
     * Handle key press
     */
    handleKeyPress(e) {
        if (!this.enabled) return;

        // Skip if typing in input field
        if (this.isTyping(e.target)) {
            // Allow Escape and Ctrl+shortcuts even when typing
            if (e.key !== 'Escape' && !e.ctrlKey && !e.metaKey) {
                return;
            }
        }

        // Build key combo
        const key = this.buildKeyCombo(e);

        // Find and execute handler
        const shortcut = this.shortcuts.get(key);
        if (shortcut) {
            e.preventDefault();
            shortcut.handler(e);
        }
    }

    /**
     * Build key combination string
     */
    buildKeyCombo(e) {
        const parts = [];

        if (e.ctrlKey) parts.push('ctrl');
        if (e.metaKey) parts.push('cmd');
        if (e.altKey) parts.push('alt');
        if (e.shiftKey && e.key.length > 1) parts.push('shift');

        parts.push(e.key.toLowerCase());

        return parts.join('+');
    }

    /**
     * Check if user is typing
     */
    isTyping(element) {
        const tagName = element.tagName.toLowerCase();
        return tagName === 'input' ||
            tagName === 'textarea' ||
            element.isContentEditable;
    }

    /**
     * Open search
     */
    openSearch() {
        const searchInput = dom.$('#global-search, input[type="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    /**
     * Show shortcuts modal
     */
    showShortcutsModal() {
        const modal = dom.$('#shortcuts-modal');
        if (modal) {
            modal.classList.add('active');
            modal.setAttribute('aria-hidden', 'false');
        }
    }

    /**
     * Handle Escape key
     */
    handleEscape() {
        // Close modal first
        if (this.app.modals && this.app.modals.activeModal) {
            this.app.modals.close();
            return;
        }

        // Close dropdown
        if (this.app.dropdowns && this.app.dropdowns.activeDropdown) {
            this.app.dropdowns.close();
            return;
        }

        // Close shortcuts modal
        const shortcutsModal = dom.$('#shortcuts-modal.active');
        if (shortcutsModal) {
            shortcutsModal.classList.remove('active');
            shortcutsModal.setAttribute('aria-hidden', 'true');
        }
    }

    /**
     * Set dashboard filter
     */
    setFilter(period) {
        const filterBtn = dom.$(`[data-filter="${period}"]`);
        if (filterBtn) {
            filterBtn.click();
        }
    }

    /**
     * Navigate date (prev/next/today)
     */
    navigateDate(direction) {
        const navBtn = dom.$(`[data-nav="${direction}"]`);
        if (navBtn) {
            navBtn.click();
        }
    }

    /**
     * Toggle selected task
     */
    toggleTask() {
        const focusedTask = document.activeElement.closest('.task-item');
        if (focusedTask) {
            const checkbox = dom.$('input[type="checkbox"]', focusedTask);
            if (checkbox) {
                checkbox.click();
            }
        }
    }

    /**
     * Edit selected task
     */
    editTask() {
        const focusedTask = document.activeElement.closest('.task-item');
        if (focusedTask) {
            const editBtn = dom.$('[data-action="edit-task"]', focusedTask);
            if (editBtn) {
                editBtn.click();
            }
        }
    }

    /**
     * Delete selected task
     */
    deleteTask() {
        const focusedTask = document.activeElement.closest('.task-item');
        if (focusedTask) {
            const deleteBtn = dom.$('[data-action="delete-task"]', focusedTask);
            if (deleteBtn) {
                deleteBtn.click();
            }
        }
    }

    /**
     * Enable shortcuts
     */
    enable() {
        this.enabled = true;
    }

    /**
     * Disable shortcuts
     */
    disable() {
        this.enabled = false;
    }
}
