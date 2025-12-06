/**
 * Form Manager
 * Handles form validation and submission
 */

import { ajax } from '../utils/ajax.js';
import { dom } from '../utils/dom.js';

export class FormManager {
    constructor(app) {
        this.app = app;
        this.forms = new Map();
    }

    /**
     * Initialize form manager
     */
    init() {
        // Initialize all forms on page
        this.initPanelForms();
    }

    /**
     * Initialize forms in current panel
     */
    initPanelForms() {
        const forms = dom.$$('form');
        forms.forEach(form => this.initForm(form));
    }

    /**
     * Initialize single form
     */
    initForm(form) {
        if (this.forms.has(form)) return;

        // Mark as initialized
        this.forms.set(form, true);

        // Add submit handler
        form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Add real-time validation
        const inputs = dom.$$('input, textarea, select', form);
        inputs.forEach(input => {
            input.addEventListener('blur', () => this.validateField(input));
            input.addEventListener('input', () => this.clearFieldError(input));
        });
    }

    /**
     * Handle form submission
     */
    async handleSubmit(e) {
        e.preventDefault();

        const form = e.target;

        // Validate form
        if (!this.validateForm(form)) {
            return;
        }

        // Get form action and method
        const action = form.getAttribute('action');
        const method = form.getAttribute('method')?.toUpperCase() || 'POST';

        if (!action) {
            console.error('Form has no action attribute');
            return;
        }

        // Show loading state
        this.setFormLoading(form, true);

        try {
            // Get form data
            const formData = new FormData(form);

            // Submit form
            let result;
            if (method === 'POST') {
                result = await ajax.post(action, formData);
            } else if (method === 'PUT') {
                result = await ajax.put(action, dom.serializeFormJSON(form));
            } else if (method === 'DELETE') {
                result = await ajax.delete(action);
            } else {
                result = await ajax.get(action);
            }

            // Handle response
            this.handleResponse(result, form);

        } catch (error) {
            console.error('Form submission error:', error);
            this.handleError(error, form);
        } finally {
            this.setFormLoading(form, false);
        }
    }

    /**
     * Validate entire form
     */
    validateForm(form) {
        let isValid = true;

        // Clear previous errors
        this.clearFormErrors(form);

        // Validate required fields
        const requiredFields = dom.$$('[required]', form);
        requiredFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });

        // Validate email fields
        const emailFields = dom.$$('input[type="email"]', form);
        emailFields.forEach(field => {
            if (field.value && !this.isValidEmail(field.value)) {
                this.showFieldError(field, 'Please enter a valid email address');
                isValid = false;
            }
        });

        // Validate password confirmation
        const password = dom.$('input[name="password"], input[name="new_password"]', form);
        const confirm = dom.$('input[name="password2"], input[name="confirm_password"]', form);

        if (password && confirm && password.value !== confirm.value) {
            this.showFieldError(confirm, 'Passwords do not match');
            isValid = false;
        }

        return isValid;
    }

    /**
     * Validate single field
     */
    validateField(field) {
        // Required validation
        if (field.hasAttribute('required') && !field.value.trim()) {
            this.showFieldError(field, 'This field is required');
            return false;
        }

        // Min length validation
        const minLength = field.getAttribute('minlength');
        if (minLength && field.value.length < parseInt(minLength)) {
            this.showFieldError(field, `Minimum ${minLength} characters required`);
            return false;
        }

        // Max length validation
        const maxLength = field.getAttribute('maxlength');
        if (maxLength && field.value.length > parseInt(maxLength)) {
            this.showFieldError(field, `Maximum ${maxLength} characters allowed`);
            return false;
        }

        // Pattern validation
        const pattern = field.getAttribute('pattern');
        if (pattern && field.value && !new RegExp(pattern).test(field.value)) {
            this.showFieldError(field, 'Please match the requested format');
            return false;
        }

        return true;
    }

    /**
     * Show field error
     */
    showFieldError(field, message) {
        // Add error class
        field.classList.add('error');

        // Create error message element
        const errorEl = dom.createElement('small', {
            class: 'field-error',
            style: { color: 'var(--color-error)', fontSize: '0.875rem', marginTop: '0.25rem', display: 'block' }
        }, [message]);

        // Insert after field
        field.parentNode.appendChild(errorEl);
    }

    /**
     * Clear field error
     */
    clearFieldError(field) {
        field.classList.remove('error');
        const errorEl = field.parentNode.querySelector('.field-error');
        if (errorEl) {
            errorEl.remove();
        }
    }

    /**
     * Clear all form errors
     */
    clearFormErrors(form) {
        dom.$$('.error', form).forEach(el => el.classList.remove('error'));
        dom.$$('.field-error', form).forEach(el => el.remove());
    }

    /**
     * Set form loading state
     */
    setFormLoading(form, loading) {
        const submitBtn = dom.$('button[type="submit"]', form);

        if (submitBtn) {
            submitBtn.disabled = loading;

            // Toggle loading spinner
            const btnText = dom.$('.btn-text', submitBtn);
            const btnLoader = dom.$('.btn-loader', submitBtn);

            if (btnText && btnLoader) {
                btnText.style.display = loading ? 'none' : 'inline';
                btnLoader.style.display = loading ? 'inline-block' : 'none';
            } else {
                submitBtn.textContent = loading ? 'Loading...' : 'Submit';
            }
        }
    }

    /**
     * Handle successful response
     */
    handleResponse(result, form) {
        // JSON response
        if (typeof result === 'object') {
            if (result.success) {
                // Show success message
                this.app.notifications.showToast(
                    result.message || 'Success!',
                    'success'
                );

                // Reset form
                form.reset();

                // Handle redirect
                if (result.redirect) {
                    if (result.redirect.startsWith('http')) {
                        window.location.href = result.redirect;
                    } else {
                        this.app.router.navigate(result.redirect);
                    }
                }

                // Close modal if in modal
                const modal = form.closest('.modal-dialog');
                if (modal) {
                    this.app.modals.close();
                }

                // Reload panel if needed
                if (result.reload || form.dataset.reloadOnSuccess) {
                    this.app.router.reload();
                }
            } else {
                // Show error message
                this.app.notifications.showToast(
                    result.error || 'An error occurred',
                    'error'
                );

                // Show field errors if provided
                if (result.errors) {
                    Object.entries(result.errors).forEach(([field, messages]) => {
                        const fieldEl = dom.$(`[name="${field}"]`, form);
                        if (fieldEl) {
                            this.showFieldError(fieldEl, messages[0]);
                        }
                    });
                }
            }
        }
    }

    /**
     * Handle error
     */
    handleError(error, form) {
        let message = 'An error occurred. Please try again.';

        if (error.status === 400) {
            message = 'Invalid form data. Please check your input.';
        } else if (error.status === 403) {
            message = 'You do not have permission to perform this action.';
        } else if (error.status === 404) {
            message = 'The requested resource was not found.';
        } else if (error.status === 500) {
            message = 'Server error. Please try again later.';
        }

        this.app.notifications.showToast(message, 'error');
    }

    /**
     * Validate email format
     */
    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
}
