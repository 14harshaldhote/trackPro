/**
 * AJAX Utilities
 * Helper functions for making AJAX requests
 */

export const ajax = {
    /**
     * GET request
     */
    async get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    },

    /**
     * POST request
     */
    async post(url, data = {}, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: data instanceof FormData ? data : JSON.stringify(data),
            headers: {
                ...(data instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
                ...options.headers
            }
        });
    },

    /**
     * PUT request
     */
    async put(url, data = {}, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data),
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
    },

    /**
     * DELETE request
     */
    async delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    },

    /**
     * Generic request handler
     */
    async request(url, options = {}) {
        // Add CSRF token for non-GET requests
        if (options.method && options.method !== 'GET') {
            options.headers = {
                ...options.headers,
                'X-CSRFToken': this.getCsrfToken()
            };
        }

        try {
            const response = await fetch(url, options);

            // Handle different response types
            const contentType = response.headers.get('content-type');

            if (!response.ok) {
                throw new HTTPError(response.status, response.statusText, url);
            }

            // Return JSON if content type is JSON
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }

            // Otherwise return text (HTML)
            return await response.text();

        } catch (error) {
            if (error instanceof HTTPError) {
                throw error;
            }
            throw new NetworkError(error.message);
        }
    },

    /**
     * Get CSRF token from DOM or window
     */
    getCsrfToken() {
        return window.TrackerPro?.csrfToken ||
            document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
            document.querySelector('meta[name=csrf-token]')?.content ||
            '';
    }
};

/**
 * HTTP Error class
 */
export class HTTPError extends Error {
    constructor(status, statusText, url) {
        super(`HTTP ${status}: ${statusText} (${url})`);
        this.name = 'HTTPError';
        this.status = status;
        this.statusText = statusText;
        this.url = url;
    }
}

/**
 * Network Error class
 */
export class NetworkError extends Error {
    constructor(message) {
        super(message);
        this.name = 'NetworkError';
    }
}
