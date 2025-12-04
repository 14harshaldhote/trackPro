/**
 * AJAX Utilities
 * 
 * CSRF-safe fetch wrapper and utilities for AJAX requests.
 */

// Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

/**
 * CSRF-safe fetch wrapper
 * 
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, body, headers, etc.)
 * @returns {Promise} - Fetch promise
 */
export async function fetchJSON(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
        },
        credentials: 'same-origin',
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };

    try {
        const response = await fetch(url, mergedOptions);
        const data = await response.json();

        if (!response.ok) {
            throw {
                status: response.status,
                data: data,
            };
        }

        return data;
    } catch (error) {
        // Re-throw for caller to handle
        throw error;
    }
}

/**
 * Show toast notification
 * 
 * @param {string} message - Message to display
 * @param {string} type - success, error, info, warning
 * @param {number} duration - Duration in ms (default 3000)
 */
export function showToast(message, type = 'info', duration = 3000) {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast-notification');
    existingToasts.forEach(toast => toast.remove());

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.textContent = message;

    // Add styles
    Object.assign(toast.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '1rem 1.5rem',
        borderRadius: '8px',
        backgroundColor: type === 'success' ? '#10b981' :
            type === 'error' ? '#ef4444' :
                type === 'warning' ? '#f59e0b' : '#3b82f6',
        color: 'white',
        fontWeight: '500',
        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
        zIndex: '9999',
        animation: 'slideInRight 0.3s ease-out',
    });

    document.body.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * Display form errors
 * 
 * @param {HTMLFormElement} form - Form element
 * @param {object} errors - Error object from API response
 */
export function displayFormErrors(form, errors) {
    // Clear existing errors
    const existingErrors = form.querySelectorAll('.field-error');
    existingErrors.forEach(error => error.remove());

    // Clear error states
    const fields = form.querySelectorAll('.form-input, .form-select');
    fields.forEach(field => field.classList.remove('error'));

    // Display new errors
    for (const [field, messages] of Object.entries(errors)) {
        let fieldElement;

        if (field === 'non_field_errors') {
            // Display at top of form
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error non-field-error';
            errorDiv.style.cssText = 'color: #ef4444; margin-bottom: 1rem; padding: 0.5rem; background: rgba(239, 68, 68, 0.1); border-radius: 4px;';
            errorDiv.textContent = Array.isArray(messages) ? messages[0] : messages;
            form.insertBefore(errorDiv, form.firstChild);
        } else {
            // Find the input field
            fieldElement = form.querySelector(`[name="${field}"]`);

            if (fieldElement) {
                // Add error class
                fieldElement.classList.add('error');

                // Create error message element
                const errorDiv = document.createElement('div');
                errorDiv.className = 'field-error';
                errorDiv.style.cssText = 'color: #ef4444; font-size: 0.875rem; margin-top: 0.25rem;';
                errorDiv.textContent = Array.isArray(messages) ? messages[0] : messages;

                // Insert after the input
                fieldElement.parentNode.appendChild(errorDiv);
            }
        }
    }
}

/**
 * Set loading state on button
 * 
 * @param {HTMLButtonElement} button - Button element
 * @param {boolean} loading - Whether loading or not
 */
export function setButtonLoading(button, loading) {
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.textContent;
        button.innerHTML = '<span class="spinner"></span> Loading...';
        button.classList.add('loading');
    } else {
        button.disabled = false;
        button.textContent = button.dataset.originalText || button.textContent;
        button.classList.remove('loading');
    }
}

/**
 * Validate email format
 * 
 * @param {string} email - Email to validate
 * @returns {boolean} - Valid or not
 */
export function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Check password strength
 * 
 * @param {string} password - Password to check
 * @returns {object} - {strength: 'weak'|'medium'|'strong', score: 0-100}
 */
export function checkPasswordStrength(password) {
    let score = 0;

    if (!password) return { strength: 'weak', score: 0 };

    // Length
    if (password.length >= 8) score += 25;
    if (password.length >= 12) score += 15;

    // Complexity
    if (/[a-z]/.test(password)) score += 15;
    if (/[A-Z]/.test(password)) score += 15;
    if (/[0-9]/.test(password)) score += 15;
    if (/[^a-zA-Z0-9]/.test(password)) score += 15;

    let strength = 'weak';
    if (score >= 70) strength = 'strong';
    else if (score >= 40) strength = 'medium';

    return { strength, score };
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .spinner {
        display: inline-block;
        width: 14px;
        height: 14px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-top-color: white;
        border-radius: 50%;
        animation: spin 0.6s linear infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .form-input.error,
    .form-select.error {
        border-color: #ef4444 !important;
    }
`;
document.head.appendChild(style);
