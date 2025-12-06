/**
 * Keyboard Module
 * Handles global keyboard shortcuts.
 * Uses window.location.href for traditional page navigation.
 */
import { modals } from './modals.js';

export class KeyboardManager {
    constructor() {
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            // Ignore if typing in input/textarea
            if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
            if (e.target.isContentEditable) return;

            // Normalize key
            const key = e.key.toLowerCase();
            const ctrl = e.ctrlKey || e.metaKey; // Cmd on Mac

            // Shortcuts from Sidebar - full page navigation
            if (!ctrl && !e.altKey && !e.shiftKey) {
                switch (key) {
                    case 'd':
                        console.log('[Keyboard] Shortcut matched: D (Dashboard)');
                        e.preventDefault();
                        window.location.href = '/';
                        break;
                    case 't':
                        console.log('[Keyboard] Shortcut matched: T (Today)');
                        e.preventDefault();
                        window.location.href = '/today/';
                        break;
                    case 'w':
                        console.log('[Keyboard] Shortcut matched: W (Week)');
                        e.preventDefault();
                        window.location.href = '/week/';
                        break;
                    case 'm':
                        console.log('[Keyboard] Shortcut matched: M (Month)');
                        e.preventDefault();
                        window.location.href = '/month/';
                        break;
                    case 'a':
                        console.log('[Keyboard] Shortcut matched: A (Analytics)');
                        e.preventDefault();
                        window.location.href = '/analytics/';
                        break;
                    case 'g':
                        console.log('[Keyboard] Shortcut matched: G (Goals)');
                        e.preventDefault();
                        window.location.href = '/goals/';
                        break;
                    case ',':
                        console.log('[Keyboard] Shortcut matched: , (Settings)');
                        e.preventDefault();
                        window.location.href = '/settings/';
                        break;
                    case '?':
                        console.log('[Keyboard] Shortcut matched: ? (Help)');
                        e.preventDefault();
                        window.location.href = '/help/';
                        break;
                }
            }

            // Command Shortcuts
            if (ctrl) {
                if (key === 'k') {
                    console.log('[Keyboard] Shortcut matched: Ctrl+K (Quick Search)');
                    e.preventDefault();
                    modals.open('quick_add');
                }
                if (key === 'n') {
                    console.log('[Keyboard] Shortcut matched: Ctrl+N (New Task)');
                    e.preventDefault();
                    modals.open('add_task');
                }
            }
        });

        console.log('[Keyboard] Shortcuts listener attached');
    }
}

export const keyboard = new KeyboardManager();
