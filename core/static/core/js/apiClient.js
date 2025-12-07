/**
 * API Client - Centralized API request handler
 * Features: API v1 versioning, Request ID correlation, Feature flags, Retry logic
 */

// Generate unique request ID for correlation
function generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Feature flags (sync with backend)
const FeatureFlags = {
    cache: {},

    async check(flagName) {
        if (this.cache[flagName] !== undefined) {
            return this.cache[flagName];
        }

        try {
            const response = await fetch(`/api/v1/feature-flags/${flagName}/`, {
                headers: {
                    'X-Request-ID': generateRequestId(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.cache[flagName] = data.enabled;
                return data.enabled;
            }
        } catch (error) {
            console.warn('[FeatureFlags] Check failed for', flagName, error);
        }

        return false; // Default to disabled
    },

    isEnabled(flagName) {
        return this.cache[flagName] === true;
    }
};

// API Client class
class APIClient {
    constructor(baseUrl = '/api/v1') {
        this.baseUrl = baseUrl;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
        this.maxRetries = 2;
        this.retryDelay = 1000;
    }

    // Get CSRF token
    getCsrfToken() {
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    // Build request headers with Request ID
    buildHeaders(customHeaders = {}) {
        return {
            ...this.defaultHeaders,
            'X-CSRFToken': this.getCsrfToken(),
            'X-Request-ID': generateRequestId(),
            ...customHeaders
        };
    }

    // Retry logic for failed requests
    async retryRequest(fn, retries = this.maxRetries) {
        try {
            return await fn();
        } catch (error) {
            if (retries > 0 && this.isRetryable(error)) {
                console.warn(`[APIClient] Retrying request (${retries} attempts left)`, error);
                await this.delay(this.retryDelay);
                return this.retryRequest(fn, retries - 1);
            }
            throw error;
        }
    }

    // Check if error is retryable
    isRetryable(error) {
        return error.name === 'TypeError' || // Network error
            (error.status && error.status >= 500); // Server error
    }

    // Delay helper for retry
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Generic request method
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
        const headers = this.buildHeaders(options.headers);

        return this.retryRequest(async () => {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (!response.ok) {
                const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
                error.status = response.status;
                error.response = response;
                throw error;
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.text();
        });
    }

    // Convenience methods
    async get(endpoint, params = {}) {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${endpoint}?${query}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async patch(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

// Global instance
window.apiClient = new APIClient();
window.FeatureFlags = FeatureFlags;

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { APIClient, FeatureFlags, generateRequestId };
}
