/**
 * Settings Manager - Unified JavaScript for all settings pages
 * Handles: General, Preferences, Keyboard, Data, About, Sidebar
 * 
 * Features:
 * - API v1 integration via apiClient
 * - Loading states and error handling
 * - Accessibility improvements
 * - Works for both web and iOS app (same backend APIs)
 */

class SettingsManager {
    constructor() {
        this.api = window.apiClient || this.createFallbackClient();
        this.currentPage = this.getActivePage();
        this.debounceTimers = {};

        this.init();
    }

    // Fallback API client if not loaded
    createFallbackClient() {
        console.warn('[Settings] apiClient not found, using fallback');
        return {
            get: (url) => fetch(url).then(r => r.json()),
            post: (url, data) => fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(r => r.json()),
            put: (url, data) => fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            }).then(r => r.json()),
            delete: (url) => fetch(url, { method: 'DELETE' }).then(r => r.json())
        };
    }

    init() {
        console.log('[Settings] Initializing for page:', this.currentPage);

        // Initialize sidebar navigation
        this.initSidebar();

        // Initialize page-specific features
        switch (this.currentPage) {
            case 'general':
                this.initGeneral();
                break;
            case 'preferences':
                this.initPreferences();
                break;
            case 'keyboard':
                this.initKeyboard();
                break;
            case 'data':
                this.initData();
                break;
            case 'about':
                this.initAbout();
                break;
        }
    }

    getActivePage() {
        // Determine active page from URL or DOM
        const path = window.location.pathname;
        if (path.includes('/settings/general') || path === '/settings/') return 'general';
        if (path.includes('/settings/preferences')) return 'preferences';
        if (path.includes('/settings/keyboard')) return 'keyboard';
        if (path.includes('/settings/data')) return 'data';
        if (path.includes('/settings/about')) return 'about';

        // Fallback: check for active class
        const activeNav = document.querySelector('.settings-nav-item.active');
        if (activeNav) {
            const href = activeNav.getAttribute('href');
            if (href.includes('preferences')) return 'preferences';
            if (href.includes('keyboard')) return 'keyboard';
            if (href.includes('data')) return 'data';
            if (href.includes('about')) return 'about';
        }

        return 'general'; // default
    }

    // =========================================================================
    // SIDEBAR NAVIGATION
    // =========================================================================

    initSidebar() {
        const nav = document.querySelector('.settings-nav');
        if (!nav) return;

        // Add ARIA attributes
        nav.setAttribute('role', 'navigation');
        nav.setAttribute('aria-label', 'Settings navigation');

        // Mark active item
        const items = nav.querySelectorAll('.settings-nav-item');
        items.forEach(item => {
            const href = item.getAttribute('href');
            const isActive = item.classList.contains('active');

            if (isActive) {
                item.setAttribute('aria-current', 'page');
            }

            // Ensure touch-friendly size (already handled by CSS but add padding if needed)
            const rect = item.getBoundingClientRect();
            if (rect.height < 44) {
                item.style.paddingTop = '12px';
                item.style.paddingBottom = '12px';
            }
        });

        // Keyboard navigation
        nav.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                const current = document.activeElement;
                const items = Array.from(nav.querySelectorAll('.settings-nav-item'));
                const currentIndex = items.indexOf(current);

                if (currentIndex >= 0) {
                    const nextIndex = e.key === 'ArrowDown'
                        ? (currentIndex + 1) % items.length
                        : (currentIndex - 1 + items.length) % items.length;
                    items[nextIndex].focus();
                }
            }
        });
    }

    // =========================================================================
    // GENERAL SETTINGS
    // =========================================================================

    initGeneral() {
        const form = document.getElementById('general-settings-form');
        if (!form) return;

        console.log('[Settings] Initializing general settings');

        // Avatar upload
        this.initAvatarUpload();

        // Form submission
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveGeneralSettings(form);
        });

        // Autosave (if data-autosave attribute exists)
        if (form.hasAttribute('data-autosave')) {
            this.initAutosave(form);
        }
    }

    initAvatarUpload() {
        const uploadBtn = document.getElementById('upload-avatar');
        const removeBtn = document.getElementById('remove-avatar');
        const avatarInput = document.getElementById('avatar-input');
        const avatarPreview = document.querySelector('.avatar-preview img');

        if (!uploadBtn || !avatarInput) return;

        uploadBtn.addEventListener('click', () => {
            avatarInput.click();
        });

        avatarInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Validate file size (5MB max)
            if (file.size > 5 * 1024 * 1024) {
                this.showToast('error', 'File too large', 'Maximum size is 5MB');
                return;
            }

            // Preview image
            const reader = new FileReader();
            reader.onload = (e) => {
                if (avatarPreview) {
                    avatarPreview.src = e.target.result;
                }
            };
            reader.readAsDataURL(file);

            // Upload to server
            await this.uploadAvatar(file);
        });

        if (removeBtn) {
            removeBtn.addEventListener('click', async () => {
                await this.removeAvatar();
            });
        }
    }

    async uploadAvatar(file) {
        const formData = new FormData();
        formData.append('avatar', file);

        try {
            this.showLoading('Uploading avatar...');

            const response = await fetch('/api/v1/user/avatar/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.api.getCsrfToken ? this.api.getCsrfToken() : this.getCsrfToken(),
                    'X-Request-ID': this.generateRequestId(),
                },
                body: formData
            });

            const result = await response.json();

            this.hideLoading();

            if (result.success) {
                this.showToast('success', 'Success', 'Avatar updated successfully');
                // Update preview
                const avatarPreview = document.querySelector('.avatar-preview img');
                if (avatarPreview) {
                    avatarPreview.src = result.avatar_url;
                }
            } else {
                this.showToast('error', 'Upload failed', result.error);
            }
        } catch (error) {
            this.hideLoading();
            console.error('[Settings] Avatar upload error:', error);
            this.showToast('error', 'Upload failed', 'Network error. Please try again.');
        }
    }

    async removeAvatar() {
        try {
            this.showLoading('Removing avatar...');

            const result = await this.api.delete('/user/avatar/');

            this.hideLoading();

            if (result.success) {
                this.showToast('success', 'Success', 'Avatar removed');
                // Update preview to default
                const avatarPreview = document.querySelector('.avatar-preview img');
                if (avatarPreview) {
                    avatarPreview.src = result.avatar_url;
                }
            } else {
                this.showToast('error', 'Error', result.error);
            }
        } catch (error) {
            this.hideLoading();
            console.error('[Settings] Avatar remove error:', error);
            this.showToast('error', 'Error', 'Failed to remove avatar');
        }
    }

    async saveGeneralSettings(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : 'Save Changes';

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="loading-spinner" style="width:16px;height:16px;border-width:2px;"></span> Saving...';
            }

            const formData = new FormData(form);
            const data = {
                first_name: formData.get('first_name'),
                last_name: formData.get('last_name'),
                email: formData.get('email'),
                timezone: formData.get('timezone'),
                date_format: formData.get('date_format'),
                week_start: parseInt(formData.get('week_start'))
            };

            const result = await this.api.put('/user/profile/', data);

            if (result.success) {
                this.showToast('success', 'Saved', 'Profile updated successfully');
                this.showAutosaveIndicator('Saved');
            } else {
                this.showToast('error', 'Error', result.error);
            }
        } catch (error) {
            console.error('[Settings] Save error:', error);
            this.showToast('error', 'Error', 'Failed to save settings');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        }
    }

    initAutosave(form) {
        const inputs = form.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            input.addEventListener('input', () => {
                this.debounce('autosave', () => {
                    this.saveGeneralSettings(form);
                }, 2000); // 2 second delay
            });
        });
    }

    showAutosaveIndicator(message) {
        const indicator = document.getElementById('autosave-status');
        if (!indicator) return;

        indicator.textContent = message;
        indicator.style.opacity = '1';

        setTimeout(() => {
            indicator.style.opacity = '0';
        }, 2000);
    }

    // =========================================================================
    // PREFERENCES SETTINGS
    // =========================================================================

    initPreferences() {
        const form = document.getElementById('preferences-form');
        if (!form) return;

        console.log('[Settings] Initializing preferences');

        // Theme selection with immediate preview
        const themeInputs = document.querySelectorAll('input[name="theme"]');
        themeInputs.forEach(input => {
            input.addEventListener('change', () => {
                if (window.App && window.App.setTheme) {
                    window.App.setTheme(input.value);
                } else {
                    // Fallback theme application
                    document.documentElement.setAttribute('data-theme', input.value);
                    localStorage.setItem('tracker-theme', input.value);
                }
            });
        });

        // Form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.savePreferences(form);
        });

        // Push notification permission request
        const pushToggle = document.getElementById('push-toggle');
        if (pushToggle) {
            pushToggle.addEventListener('change', async (e) => {
                if (e.target.checked) {
                    await this.requestPushPermission();
                }
            });
        }
    }

    async savePreferences(form) {
        const saveBtn = document.getElementById('save-prefs-btn');
        const originalText = saveBtn ? saveBtn.textContent : 'Save Preferences';

        try {
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<span class="loading-spinner" style="width:16px;height:16px;border-width:2px;"></span> Saving...';
            }

            const formData = new FormData(form);
            const data = {
                theme: formData.get('theme'),
                sound_complete: formData.has('sound_complete'),
                sound_notify: formData.has('sound_notify'),
                sound_volume: parseInt(formData.get('sound_volume')) || 70,
                push_enabled: formData.has('push_enabled'),
                daily_reminder_enabled: formData.has('daily_reminder_enabled'),
                compact_mode: formData.has('compact_mode'),
                animations: formData.has('animations')
            };

            // Use versioned API endpoint
            const result = await this.api.put('/preferences/', data);

            if (result.success) {
                this.showToast('success', 'Saved', 'Preferences updated successfully');
            } else {
                this.showToast('error', 'Error', result.error);
            }
        } catch (error) {
            console.error('[Settings] Save preferences error:', error);
            this.showToast('error', 'Error', error.message || 'Failed to save preferences');
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = originalText;
            }
        }
    }

    async requestPushPermission() {
        if (!('Notification' in window)) {
            this.showToast('warning', 'Not supported', 'Push notifications are not supported in this browser');
            return false;
        }

        try {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                this.showToast('success', 'Enabled', 'Push notifications enabled');
                return true;
            } else {
                this.showToast('info', 'Permission denied', 'You can enable notifications in browser settings');
                const pushToggle = document.getElementById('push-toggle');
                if (pushToggle) pushToggle.checked = false;
                return false;
            }
        } catch (error) {
            console.error('[Settings] Push permission error:', error);
            return false;
        }
    }

    // =========================================================================
    // KEYBOARD SETTINGS
    // =========================================================================

    initKeyboard() {
        const toggle = document.querySelector('input[name="keyboard_enabled"]');
        if (!toggle) return;

        console.log('[Settings] Initializing keyboard settings');

        toggle.addEventListener('change', async () => {
            await this.saveKeyboardPreference(toggle.checked);
        });
    }

    async saveKeyboardPreference(enabled) {
        try {
            const result = await this.api.put('/preferences/', {
                keyboard_enabled: enabled
            });

            if (result.success) {
                this.showToast('success', 'Saved', `Keyboard shortcuts ${enabled ? 'enabled' : 'disabled'}`);

                // Update global keyboard handler if exists
                if (window.App && window.App.toggleKeyboard) {
                    window.App.toggleKeyboard(enabled);
                }
            } else {
                this.showToast('error', 'Error', result.error);
            }
        } catch (error) {
            console.error('[Settings] Keyboard pref error:', error);
            this.showToast('error', 'Error', 'Failed to save preference');
        }
    }

    // =========================================================================
    // DATA SETTINGS
    // =========================================================================

    initData() {
        console.log('[Settings] Initializing data settings');

        // Export buttons
        const exportBtns = document.querySelectorAll('[data-export]');
        exportBtns.forEach(btn => {
            btn.addEventListener('click', async () => {
                const format = btn.getAttribute('data-export');
                await this.exportData(format);
            });
        });

        // Import
        const importZone = document.getElementById('import-zone');
        const importInput = document.getElementById('import-input');
        const browseBtn = importZone?.querySelector('.btn-link');

        if (browseBtn && importInput) {
            browseBtn.addEventListener('click', () => {
                importInput.click();
            });
        }

        if (importInput) {
            importInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (file) {
                    await this.importData(file);
                }
            });
        }

        // Drag and drop import
        if (importZone) {
            importZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                importZone.classList.add('drag-over');
            });

            importZone.addEventListener('dragleave', () => {
                importZone.classList.remove('drag-over');
            });

            importZone.addEventListener('drop', async (e) => {
                e.preventDefault();
                importZone.classList.remove('drag-over');

                const file = e.dataTransfer.files[0];
                if (file) {
                    await this.importData(file);
                }
            });
        }

        // Danger zone actions
        const clearBtn = document.querySelector('[data-action="clear-data"]');
        const deleteBtn = document.querySelector('[data-action="delete-account"]');

        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.confirmClearData());
        }

        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.confirmDeleteAccount());
        }
    }

    async exportData(format) {
        try {
            this.showLoading(`Exporting ${format.toUpperCase()}...`);

            const response = await fetch('/api/v1/data/export/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Request-ID': this.generateRequestId(),
                },
                body: JSON.stringify({ format })
            });

            this.hideLoading();

            if (response.ok) {
                // Trigger file download
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `tracker_export_${new Date().toISOString().split('T')[0]}.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                this.showToast('success', 'Exported', `Data exported as ${format.toUpperCase()}`);
            } else {
                const result = await response.json();
                this.showToast('error', 'Export failed', result.error || 'Unknown error');
            }
        } catch (error) {
            this.hideLoading();
            console.error('[Settings] Export error:', error);
            this.showToast('error', 'Export failed', 'Network error. Please try again.');
        }
    }

    async importData(file) {
        try {
            this.showLoading('Importing data...');

            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/v1/data/import/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Request-ID': this.generateRequestId(),
                },
                body: formData
            });

            const result = await response.json();

            this.hideLoading();

            if (result.success) {
                this.showToast('success', 'Import successful', result.message);

                // Prompt to reload page
                if (confirm('Data imported successfully. Reload page to see changes?')) {
                    window.location.reload();
                }
            } else {
                this.showToast('error', 'Import failed', result.error);
            }
        } catch (error) {
            this.hideLoading();
            console.error('[Settings] Import error:', error);
            this.showToast('error', 'Import failed', 'Network error. Please try again.');
        }
    }

    confirmClearData() {
        if (!confirm('⚠️ This will delete ALL your trackers and tasks. This cannot be undone.\n\nDo you want to export your data first?')) {
            return;
        }

        const confirmation = prompt('Type "DELETE ALL DATA" to confirm:');
        if (confirmation === 'DELETE ALL DATA') {
            this.clearAllData();
        } else {
            this.showToast('info', 'Cancelled', 'Clear data cancelled');
        }
    }

    async clearAllData() {
        try {
            this.showLoading('Clearing all data...');

            const result = await this.api.post('/data/clear/', {
                confirmation: 'DELETE ALL DATA'
            });

            this.hideLoading();

            if (result.success) {
                this.showToast('success', 'Data cleared', result.message);

                // Redirect to dashboard after 2 seconds
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } else {
                this.showToast('error', 'Error', result.error);
            }
        } catch (error) {
            this.hideLoading();
            console.error('[Settings] Clear data error:', error);
            this.showToast('error', 'Error', 'Failed to clear data');
        }
    }

    confirmDeleteAccount() {
        if (!confirm('⚠️ DANGER: This will PERMANENTLY delete your account and ALL data.\n\nThis action is IRREVERSIBLE.\n\nDo you want to export your data first?')) {
            return;
        }

        const confirmation = prompt('Type "DELETE MY ACCOUNT" to confirm:');
        if (confirmation !== 'DELETE MY ACCOUNT') {
            this.showToast('info', 'Cancelled', 'Account deletion cancelled');
            return;
        }

        const password = prompt('Enter your password to confirm:');
        if (!password) {
            this.showToast('info', 'Cancelled', 'Account deletion cancelled');
            return;
        }

        this.deleteAccount(password);
    }

    async deleteAccount(password) {
        try {
            this.showLoading('Deleting account...');

            const result = await this.api.delete('/user/delete/', {
                confirmation: 'DELETE MY ACCOUNT',
                password: password
            });

            this.hideLoading();

            if (result.success) {
                this.showToast('success', 'Account deleted', result.message);

                // Redirect to logout
                setTimeout(() => {
                    window.location.href = result.redirect || '/logout/';
                }, 2000);
            } else {
                this.showToast('error', 'Error', result.error);
            }
        } catch (error) {
            this.hideLoading();
            console.error('[Settings] Delete account error:', error);
            this.showToast('error', 'Error', 'Failed to delete account');
        }
    }

    // =========================================================================
    // ABOUT SETTINGS
    // =========================================================================

    initAbout() {
        console.log('[Settings] Initializing about page');
        // No backend integration needed for now
        // Future: version check API, changelog updates
    }

    // =========================================================================
    // UTILITY FUNCTIONS
    // =========================================================================

    showToast(type, title, message) {
        if (window.App && window.App.showToast) {
            window.App.showToast(type, title, message);
        } else {
            // Fallback alert
            alert(`${title}: ${message}`);
        }
    }

    showLoading(message = 'Loading...') {
        if (window.App && window.App.showLoading) {
            window.App.showLoading(message);
        } else {
            console.log('[Settings] Loading:', message);
        }
    }

    hideLoading() {
        if (window.App && window.App.hideLoading) {
            window.App.hideLoading();
        }
    }

    getCsrfToken() {
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    generateRequestId() {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    debounce(key, func, delay) {
        clearTimeout(this.debounceTimers[key]);
        this.debounceTimers[key] = setTimeout(func, delay);
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.settingsManager = new SettingsManager();
    });
} else {
    window.settingsManager = new SettingsManager();
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsManager;
}
