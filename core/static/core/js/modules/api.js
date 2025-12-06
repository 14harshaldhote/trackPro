/**
 * API Module
 * Centralized fetch wrapper for backend communication.
 * Handles CSRF tokens and error parsing globally.
 */

export class API {
    constructor() {
        this.csrfToken = window.TrackerPro?.csrfToken;
        this.apiBase = window.TrackerPro?.apiBase || '/api/';
        this.panelBase = window.TrackerPro?.panelBase || '/panel/';
    }

    async request(url, options = {}) {
        const method = options.method || 'GET';
        console.log(`[API] 🚀 ${method} ${url}`);

        const headers = {
            'X-CSRFToken': this.csrfToken,
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            ...options.headers
        };

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);

            // Clone response before reading, in case we need to read it multiple times
            const responseClone = response.clone();

            // Handle HTTP errors
            if (!response.ok) {
                console.warn(`[API] ⚠️ Request failed: ${response.status} ${url}`);

                // Try to parse error message from JSON
                let errorMessage = `Request failed: ${response.status}`;
                try {
                    const errorData = await responseClone.json();
                    errorMessage = errorData.message || errorData.error || errorMessage;
                } catch (e) {
                    // Fallback to text if not JSON
                    try {
                        const text = await response.text();
                        if (text) errorMessage = text.substring(0, 100);
                    } catch (textErr) {
                        // Body already read, use default message
                    }
                }
                throw new Error(errorMessage);
            }

            console.log(`[API] ✅ Success: ${method} ${url}`);

            // Return JSON if content-type is json, else text
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.text();

        } catch (error) {
            console.error(`[API] ❌ Error in ${method} ${url}:`, error);
            throw error; // Re-throw for caller to handle
        }
    }

    async get(endpoint) {
        return this.request(endpoint);
    }

    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getPanel(panelUrl) {
        // Panels return HTML fragments
        return this.request(panelUrl, {
            headers: {
                'Accept': 'text/html'
            }
        });
    }
}

export const api = new API();
