/**
 * API Client Utility - Unified client for backend API with v1 versioning
 * Features:
 * - Automatic request ID generation for structured logging correlation
 * - API versioning support
 * - Retry logic
 * - Error handling with toast notifications
 */

(function (window) {
    'use strict';

    class APIClient {
        constructor() {
            this.baseURL = '/api/v1';
            this.retryAttempts = 3;
            this.retryDelay = 1000; // ms
        }

        /**
         * Generate unique request ID for logging correlation
         */
        generateRequestID() {
            return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }

        /**
         * Make HTTP request with automatic request ID and retry logic
         * @param {string} endpoint - API endpoint (without /api/v1 prefix)
         * @param {object} options - Fetch options
         * @param {number} attempt - Current retry attempt
         */
        async request(endpoint, options = {}, attempt = 1) {
            const requestID = this.generateRequestID();

            // Build full URL
            const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;

            // Add request ID header
            const headers = {
                'X-Request-ID': requestID,
                'Content-Type': 'application/json',
                ...options.headers
            };

            // Add CSRF token if present
            const csrfToken = this.getCSRFToken();
            if (csrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase())) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const fetchOptions = {
                ...options,
                headers,
                credentials: 'same-origin' // Include cookies
            };

            try {
                console.log(`[APIClient] ${options.method || 'GET'} ${endpoint} (${requestID})`);

                const response = await fetch(url, fetchOptions);

                // Store request ID from response if available
                const responseRequestID = response.headers.get('X-Request-ID');
                if (responseRequestID) {
                    console.log(`[APIClient] Response Request-ID: ${responseRequestID}`);
                }

                // Handle error responses
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));

                    // Check if we should retry
                    if (attempt < this.retryAttempts && this.shouldRetry(response.status)) {
                        console.warn(`[APIClient] Retrying ${endpoint} (attempt ${attempt + 1}/${this.retryAttempts})`);
                        await this.delay(this.retryDelay * attempt);
                        return this.request(endpoint, options, attempt + 1);
                    }

                    throw new APIError(
                        errorData.message || `Request failed with status ${response.status}`,
                        response.status,
                        errorData,
                        requestID
                    );
                }

                // Parse response
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                }

                return await response.text();

            } catch (error) {
                if (error instanceof APIError) {
                    throw error;
                }

                // Network error - retry if applicable
                if (attempt < this.retryAttempts) {
                    console.warn(`[APIClient] Network error, retrying ${endpoint} (attempt ${attempt + 1}/${this.retryAttempts})`);
                    await this.delay(this.retryDelay * attempt);
                    return this.request(endpoint, options, attempt + 1);
                }

                throw new APIError(
                    error.message || 'Network error',
                    0,
                    { originalError: error },
                    requestID
                );
            }
        }

        /**
         * Check if error status should be retried
         */
        shouldRetry(status) {
            return status === 429 || // Rate limit
                status === 503 || // Service unavailable
                status === 504;   // Gateway timeout
        }

        /**
         * Delay helper for retry logic
         */
        delay(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }

        /**
         * Get CSRF token from cookie
         */
        getCSRFToken() {
            const name = 'csrftoken';
            const cookie = document.cookie.split(';').find(c => c.trim().startsWith(name + '='));
            return cookie ? cookie.split('=')[1] : null;
        }

        // Convenience methods
        get(endpoint, options = {}) {
            return this.request(endpoint, { ...options, method: 'GET' });
        }

        post(endpoint, data, options = {}) {
            return this.request(endpoint, {
                ...options,
                method: 'POST',
                body: JSON.stringify(data)
            });
        }

        put(endpoint, data, options = {}) {
            return this.request(endpoint, {
                ...options,
                method: 'PUT',
                body: JSON.stringify(data)
            });
        }

        patch(endpoint, data, options = {}) {
            return this.request(endpoint, {
                ...options,
                method: 'PATCH',
                body: JSON.stringify(data)
            });
        }

        delete(endpoint, options = {}) {
            return this.request(endpoint, { ...options, method: 'DELETE' });
        }
    }

    /**
     * Custom API Error class
     */
    class APIError extends Error {
        constructor(message, status, data = {}, requestID = null) {
            super(message);
            this.name = 'APIError';
            this.status = status;
            this.data = data;
            this.requestID = requestID;
        }

        toString() {
            return `APIError: ${this.message} (Status: ${this.status}, Request ID: ${this.requestID})`;
        }

        /**
         * Show error as toast notification
         */
        showToast() {
            if (window.App && window.App.showToast) {
                let message = this.message;

                // Add user-friendly messages for common errors
                if (this.status === 429) {
                    message = 'Too many requests. Please wait a moment.';
                } else if (this.status === 503) {
                    message = 'Service temporarily unavailable. Retrying...';
                } else if (this.status === 401) {
                    message = 'Please log in to continue.';
                } else if (this.status === 403) {
                    message = 'Access denied.';
                }

                window.App.showToast('error', message);
            } else {
                console.error(this.toString());
            }
        }
    }

    // Export to window
    window.APIClient = APIClient;
    window.APIError = APIError;

    // Create global instance
    window.api = new APIClient();

    console.log('[APIClient] Initialized with API v1 support and request ID tracking');

})(window);
