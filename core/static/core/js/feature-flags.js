/**
 * Feature Flags Client - Check backend feature flags from frontend
 * Integrates with backend feature_flags.py utility
 */

(function (window) {
    'use strict';

    class FeatureFlags {
        constructor() {
            this.flags = {};
            this.loaded = false;
            this.loading = false;
        }

        /**
         * Load feature flags from backend
         */
        async load() {
            if (this.loaded || this.loading) {
                return this.flags;
            }

            this.loading = true;

            try {
                // Use global API client
                const response = await window.api.get('/feature-flags/');
                this.flags = response.flags || {};
                this.loaded = true;
                console.log('[FeatureFlags] Loaded:', this.flags);
                return this.flags;
            } catch (error) {
                console.error('[FeatureFlags] Failed to load:', error);
                // Set safe defaults
                this.flags = {
                    new_sync_api: false,
                    push_notifications: false,
                    advanced_analytics: false,
                    api_v2: false,
                    streaming_export: false
                };
                this.loaded = true;
                return this.flags;
            } finally {
                this.loading = false;
            }
        }

        /**
         * Check if a feature is enabled
         * @param {string} flagName - Name of the feature flag
         * @param {boolean} defaultValue - Default value if flag not found
         */
        isEnabled(flagName, defaultValue = false) {
            if (!this.loaded) {
                console.warn(`[FeatureFlags] Flags not loaded yet, using default for ${flagName}`);
                return defaultValue;
            }

            return this.flags[flagName] !== undefined ? this.flags[flagName] : defaultValue;
        }

        /**
         * Show/hide elements based on feature flag
         * @param {string} flagName - Feature flag name
         * @param {string} selector - CSS selector for elements to toggle
         */
        toggleElements(flagName, selector) {
            const enabled = this.isEnabled(flagName);
            const elements = document.querySelectorAll(selector);

            elements.forEach(el => {
                if (enabled) {
                    el.style.display = '';
                    el.removeAttribute('hidden');
                } else {
                    el.style.display = 'none';
                    el.setAttribute('hidden', '');
                }
            });
        }

        /**
         * Add feature flag class to element
         * @param {string} flagName - Feature flag name
         * @param {string} selector - CSS selector
         * @param {string} className - Class to add if enabled
         */
        addClassIfEnabled(flagName, selector, className) {
            if (this.isEnabled(flagName)) {
                document.querySelectorAll(selector).forEach(el => {
                    el.classList.add(className);
                });
            }
        }

        /**
         * Execute callback if feature is enabled
         * @param {string} flagName - Feature flag name
         * @param {function} callback - Function to execute if enabled
         */
        ifEnabled(flagName, callback) {
            if (this.isEnabled(flagName)) {
                callback();
            }
        }

        /**
         * Get all flags
         */
        getAll() {
            return { ...this.flags };
        }
    }

    // Export to window
    window.FeatureFlags = FeatureFlags;

    // Create global instance and auto-load
    window.featureFlags = new FeatureFlags();

    // Auto-load on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.featureFlags.load();
        });
    } else {
        window.featureFlags.load();
    }

    console.log('[FeatureFlags] Initialized');

})(window);
