/**
 * Tracker Pro - Traditional Django Multi-Page App
 * Main Entry Point
 */

import { api } from './modules/api.js';
import { tasks } from './modules/tasks.js';
import { modals } from './modules/modals.js';
import { keyboard } from './modules/keyboard.js';
import { ui } from './modules/ui.js';
import { trackers } from './modules/trackers.js';

class App {
    constructor() {
        this.init();
    }

    async init() {
        console.log('Tracker Pro initialized');

        // Modules map (for debugging/access)
        this.modules = {
            api,
            tasks,
            modals,
            keyboard,
            ui,
            trackers
        };

        // Perform an initial health check if needed
        try {
            // await api.get('/api/health/'); // Optional
        } catch (e) {
            console.warn('API connection check failed', e);
        }
    }
}

// Start app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
