/**
 * Theme System
 * Handles theme switching and persistence
 */

import { storage } from '../utils/storage.js';

export class ThemeSystem {
    constructor(app) {
        this.app = app;
        this.currentTheme = null;
        this.storageKey = 'tracker-theme';
        this.defaultTheme = 'working-hard';
    }

    /**
     * Initialize theme system
     */
    init() {
        // Load saved theme or use default
        const savedTheme = storage.get(this.storageKey, this.defaultTheme);
        this.apply(savedTheme);
    }

    /**
     * Apply theme
     */
    apply(themeName) {
        // Set data attribute on html element
        document.documentElement.setAttribute('data-theme', themeName);

        // Update current theme
        this.currentTheme = themeName;

        // Save to localStorage
        storage.set(this.storageKey, themeName);

        // Update theme selector if exists
        this.updateThemeSelector(themeName);

        // Dispatch event
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName }
        }));
    }

    /**
     * Get current theme
     */
    get() {
        return this.currentTheme;
    }

    /**
     * Update theme selector UI
     */
    updateThemeSelector(themeName) {
        // Update radio buttons
        const radio = document.querySelector(`input[name="theme"][value="${themeName}"]`);
        if (radio) {
            radio.checked = true;
        }

        // Update theme preview selections
        document.querySelectorAll('.theme-option, .theme-preview').forEach(el => {
            if (el.dataset.theme === themeName) {
                el.classList.add('theme-selected', 'active');
            } else {
                el.classList.remove('theme-selected', 'active');
            }
        });
    }

    /**
     * Toggle between light and dark
     */
    toggleDarkMode() {
        const isDark = this.currentTheme.includes('dark');
        const newTheme = isDark ? 'bloom' : 'total-dark';
        this.apply(newTheme);
    }
}
