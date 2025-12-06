/**
 * Swipe Gestures (iOS)
 * Handles swipe actions for task completion
 */

import { ajax } from '../utils/ajax.js';
import { dom } from '../utils/dom.js';

export class SwipeGestures {
    constructor(app) {
        this.app = app;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.minSwipeDistance = 60;
        this.currentSwipeElement = null;
    }

    /**
     * Initialize swipe gestures
     */
    init() {
        this.initPanelSwipes();
    }

    /**
     * Initialize swipes in current panel
     */
    initPanelSwipes() {
        const swipeableElements = dom.$$('.task-item, [data-swipe-enabled]');

        swipeableElements.forEach(el => {
            this.initSwipe(el);
        });
    }

    /**
     * Initialize swipe on element
     */
    initSwipe(element) {
        element.addEventListener('touchstart', (e) => this.handleTouchStart(e, element), { passive: true });
        element.addEventListener('touchmove', (e) => this.handleTouchMove(e, element), { passive: false });
        element.addEventListener('touchend', (e) => this.handleTouchEnd(e, element), { passive: true });
    }

    /**
     * Handle touch start
     */
    handleTouchStart(e, element) {
        this.touchStartX = e.touches[0].clientX;
        this.touchStartY = e.touches[0].clientY;
        this.currentSwipeElement = element;
    }

    /**
     * Handle touch move
     */
    handleTouchMove(e, element) {
        if (!this.currentSwipeElement) return;

        const touch = e.touches[0];
        const deltaX = touch.clientX - this.touchStartX;
        const deltaY = touch.clientY - this.touchStartY;

        // Only swipe horizontally if horizontal movement > vertical
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            e.preventDefault(); // Prevent scroll

            // Show swipe action preview
            this.showSwipePreview(element, deltaX);
        }
    }

    /**
     * Handle touch end
     */
    handleTouchEnd(e, element) {
        if (!this.currentSwipeElement) return;

        this.touchEndX = e.changedTouches[0].clientX;
        this.touchEndY = e.changedTouches[0].clientY;

        const deltaX = this.touchEndX - this.touchStartX;
        const deltaY = this.touchEndY - this.touchStartY;

        // Check if swipe was horizontal
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > this.minSwipeDistance) {
            if (deltaX > 0) {
                // Swipe right (leading) - Complete
                this.handleSwipeAction(element, 'complete');
            } else {
                // Swipe left (trailing) - Skip/Delete
                this.handleSwipeAction(element, 'skip');
            }
        }

        // Reset swipe preview
        this.clearSwipePreview(element);
        this.currentSwipeElement = null;
    }

    /**
     * Show swipe action preview
     */
    showSwipePreview(element, deltaX) {
        // Limit translation
        const maxTranslate = 100;
        const translate = Math.max(-maxTranslate, Math.min(maxTranslate, deltaX));

        // Apply transform
        element.style.transform = `translateX(${translate}px)`;
        element.style.transition = 'none';

        // Show action indicator
        if (deltaX > 0) {
            element.classList.add('swipe-right');
            element.classList.remove('swipe-left');
        } else {
            element.classList.add('swipe-left');
            element.classList.remove('swipe-right');
        }
    }

    /**
     * Clear swipe preview
     */
    clearSwipePreview(element) {
        element.style.transform = '';
        element.style.transition = '';
        element.classList.remove('swipe-left', 'swipe-right');
    }

    /**
     * Handle swipe action
     */
    async handleSwipeAction(element, action) {
        const taskId = element.dataset.taskId;

        if (!taskId) {
            console.error('Task ID not found');
            return;
        }

        // Trigger haptic feedback
        this.triggerHaptic(action);

        // Animate out
        element.style.transform = action === 'complete' ? 'translateX(100%)' : 'translateX(-100%)';
        element.style.transition = 'transform 0.3s ease';
        element.style.opacity = '0.5';

        try {
            let endpoint;
            if (action === 'complete') {
                endpoint = `/api/task/${taskId}/toggle/`;
            } else if (action === 'skip') {
                endpoint = `/api/task/${taskId}/skip/`;
            }

            const result = await ajax.post(endpoint);

            if (result.success) {
                // Remove element
                setTimeout(() => {
                    element.remove();
                }, 300);

                // Show success feedback
                this.app.notifications.showToast(
                    result.message || `Task ${action}d`,
                    'success'
                );

                // Show celebration if all complete
                if (result.stats_delta?.all_complete) {
                    this.showCelebration();
                }
            } else {
                // Revert on error
                this.clearSwipePreview(element);
                element.style.opacity = '';
                this.app.notifications.showToast(result.error || 'Action failed', 'error');
            }
        } catch (error) {
            console.error('Swipe action error:', error);
            this.clearSwipePreview(element);
            element.style.opacity = '';
            this.app.notifications.showToast('Action failed', 'error');
        }
    }

    /**
     * Trigger haptic feedback
     */
    triggerHaptic(type) {
        if (!navigator.vibrate) return;

        const patterns = {
            complete: [10, 20, 10],
            skip: [20],
            delete: [30, 10, 30]
        };

        navigator.vibrate(patterns[type] || [10]);
    }

    /**
     * Show celebration animation
     */
    showCelebration() {
        // Simple confetti animation or message
        this.app.notifications.showToast('🎉 All tasks complete!', 'success', 3000);
    }
}
