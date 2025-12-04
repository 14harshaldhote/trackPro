/**
 * Authentication JavaScript
 * 
 * Handles login, signup, and logout with AJAX.
 */

import {
    fetchJSON,
    showToast,
    displayFormErrors,
    setButtonLoading,
    isValidEmail,
    checkPasswordStrength
} from './ajax-utils.js';

// ============================================================================
// LOGIN
// ============================================================================

export function initLogin() {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = loginForm.querySelector('button[type="submit"]');
        const email = loginForm.querySelector('[name="email"]').value;
        const password = loginForm.querySelector('[name="password"]').value;
        const remember = loginForm.querySelector('[name="remember"]')?.checked || false;

        // Client-side validation
        if (!isValidEmail(email)) {
            displayFormErrors(loginForm, { email: ['Please enter a valid email.'] });
            return;
        }

        if (password.length < 8) {
            displayFormErrors(loginForm, { password: ['Password must be at least 8 characters.'] });
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            const data = await fetchJSON('/api/auth/login/', {
                method: 'POST',
                body: JSON.stringify({ email, password, remember }),
            });

            if (data.success) {
                showToast('Login successful! Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = data.redirect || '/';
                }, 500);
            }
        } catch (error) {
            setButtonLoading(submitBtn, false);

            if (error.data && error.data.errors) {
                displayFormErrors(loginForm, error.data.errors);
            } else {
                showToast('An error occurred. Please try again.', 'error');
            }
        }
    });
}

// ============================================================================
// SIGNUP
// ============================================================================

export function initSignup() {
    const signupForm = document.getElementById('signup-form');
    if (!signupForm) return;

    const emailInput = signupForm.querySelector('[name="email"]');
    const password1Input = signupForm.querySelector('[name="password1"]');
    const password2Input = signupForm.querySelector('[name="password2"]');

    // Real-time email validation
    let emailTimeout;
    emailInput?.addEventListener('input', (e) => {
        clearTimeout(emailTimeout);
        const email = e.target.value;

        if (!isValidEmail(email)) return;

        emailTimeout = setTimeout(async () => {
            try {
                const data = await fetchJSON('/api/auth/validate-email/', {
                    method: 'POST',
                    body: JSON.stringify({ email }),
                });

                const indicator = signupForm.querySelector('.email-availability');
                if (indicator) {
                    indicator.textContent = data.message;
                    indicator.style.color = data.available ? '#10b981' : '#ef4444';
                }
            } catch (error) {
                console.error('Email validation error:', error);
            }
        }, 500);
    });

    // Password strength indicator
    password1Input?.addEventListener('input', (e) => {
        const password = e.target.value;
        const { strength, score } = checkPasswordStrength(password);

        const strengthIndicator = signupForm.querySelector('.password-strength');
        if (strengthIndicator) {
            strengthIndicator.textContent = `Strength: ${strength.toUpperCase()}`;
            strengthIndicator.style.color =
                strength === 'strong' ? '#10b981' :
                    strength === 'medium' ? '#f59e0b' : '#ef4444';

            // Update strength bar
            const strengthBar = signupForm.querySelector('.password-strength-bar');
            if (strengthBar) {
                strengthBar.style.width = `${score}%`;
                strengthBar.style.backgroundColor =
                    strength === 'strong' ? '#10b981' :
                        strength === 'medium' ? '#f59e0b' : '#ef4444';
            }
        }
    });

    // Form submission
    signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = signupForm.querySelector('button[type="submit"]');
        const email = emailInput.value;
        const password1 = password1Input.value;
        const password2 = password2Input.value;

        // Client-side validation
        if (!isValidEmail(email)) {
            displayFormErrors(signupForm, { email: ['Please enter a valid email.'] });
            return;
        }

        if (password1.length < 8) {
            displayFormErrors(signupForm, { password1: ['Password must be at least 8 characters.'] });
            return;
        }

        if (password1 !== password2) {
            displayFormErrors(signupForm, { password2: ['Passwords do not match.'] });
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            const data = await fetchJSON('/api/auth/signup/', {
                method: 'POST',
                body: JSON.stringify({ email, password1, password2 }),
            });

            if (data.success) {
                showToast('Account created successfully! Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = data.redirect || '/';
                }, 500);
            }
        } catch (error) {
            setButtonLoading(submitBtn, false);

            if (error.data && error.data.errors) {
                displayFormErrors(signupForm, error.data.errors);
            } else {
                showToast('An error occurred. Please try again.', 'error');
            }
        }
    });
}

// ============================================================================
// LOGOUT
// ============================================================================

// ============================================================================
// LOGOUT
// ============================================================================

export function initLogout() {
    // Logout is now handled via direct link to /logout/
    // This function is kept empty to prevent import errors if called elsewhere
}

// ============================================================================
// INIT
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initLogin();
    initSignup();
    initLogout();
});
