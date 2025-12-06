/**
 * DOM Utilities
 * Helper functions for DOM manipulation
 */

export const dom = {
    /**
     * Query selector shorthand
     */
    $(selector, context = document) {
        return context.querySelector(selector);
    },

    /**
     * Query selector all shorthand
     */
    $$(selector, context = document) {
        return Array.from(context.querySelectorAll(selector));
    },

    /**
     * Create element with attributes and children
     */
    createElement(tag, attrs = {}, children = []) {
        const el = document.createElement(tag);

        // Set attributes
        Object.entries(attrs).forEach(([key, value]) => {
            if (key === 'class') {
                el.className = value;
            } else if (key === 'style' && typeof value === 'object') {
                Object.assign(el.style, value);
            } else if (key.startsWith('data-')) {
                el.dataset[key.slice(5)] = value;
            } else {
                el.setAttribute(key, value);
            }
        });

        // Append children
        children.forEach(child => {
            if (typeof child === 'string') {
                el.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                el.appendChild(child);
            }
        });

        return el;
    },

    /**
     * Add event listener to multiple elements
     */
    on(selector, event, handler, context = document) {
        this.$$(selector, context).forEach(el => {
            el.addEventListener(event, handler);
        });
    },

    /**
     * Remove event listener from multiple elements
     */
    off(selector, event, handler, context = document) {
        this.$$(selector, context).forEach(el => {
            el.removeEventListener(event, handler);
        });
    },

    /**
     * Toggle class on element(s)
     */
    toggleClass(selector, className, force = undefined) {
        this.$$(selector).forEach(el => {
            el.classList.toggle(className, force);
        });
    },

    /**
     * Add class to element(s)
     */
    addClass(selector, className) {
        this.$$(selector).forEach(el => {
            el.classList.add(className);
        });
    },

    /**
     * Remove class from element(s)
     */
    removeClass(selector, className) {
        this.$$(selector).forEach(el => {
            el.classList.remove(className);
        });
    },

    /**
     * Show element(s)
     */
    show(selector) {
        this.$$(selector).forEach(el => {
            el.style.display = '';
        });
    },

    /**
     * Hide element(s)
     */
    hide(selector) {
        this.$$(selector).forEach(el => {
            el.style.display = 'none';
        });
    },

    /**
     * Get closest parent matching selector
     */
    closest(element, selector) {
        return element.closest(selector);
    },

    /**
     * Serialize form to FormData
     */
    serializeForm(form) {
        return new FormData(form);
    },

    /**
     * Serialize form to JSON object
     */
    serializeFormJSON(form) {
        const formData = new FormData(form);
        const obj = {};
        for (const [key, value] of formData.entries()) {
            if (obj[key]) {
                // Handle multiple values (e.g., checkboxes)
                if (Array.isArray(obj[key])) {
                    obj[key].push(value);
                } else {
                    obj[key] = [obj[key], value];
                }
            } else {
                obj[key] = value;
            }
        }
        return obj;
    },

    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function
     */
    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Animate element
     */
    animate(element, keyframes, options) {
        return element.animate(keyframes, options);
    },

    /**
     * Fade in element
     */
    fadeIn(element, duration = 300) {
        element.style.opacity = '0';
        element.style.display = '';

        return this.animate(element, [
            { opacity: 0 },
            { opacity: 1 }
        ], {
            duration,
            easing: 'ease-in-out',
            fill: 'forwards'
        });
    },

    /**
     * Fade out element
     */
    fadeOut(element, duration = 300) {
        return this.animate(element, [
            { opacity: 1 },
            { opacity: 0 }
        ], {
            duration,
            easing: 'ease-in-out',
            fill: 'forwards'
        }).finished.then(() => {
            element.style.display = 'none';
        });
    }
};

// Export individual functions as well
export const { $, $$, createElement, on, off } = dom;
