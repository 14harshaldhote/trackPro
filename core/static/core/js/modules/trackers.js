/**
 * Trackers Module
 * Handles tracker-specific AJAX operations: archive, restore, pagination
 */
import { api } from './api.js';
import { ui } from './ui.js';

export class TrackerManager {
    constructor() {
        this.init();
    }

    init() {
        // Expose global functions for template onclick handlers
        window.archiveTracker = this.archiveTracker.bind(this);
        window.restoreTracker = this.restoreTracker.bind(this);
        window.loadMoreTrackers = this.loadMoreTrackers.bind(this);

        console.log('[TrackerManager] Initialized');
    }

    async archiveTracker(trackerId) {
        if (!confirm('Archive this tracker? You can restore it later from the archived section.')) {
            return;
        }

        console.log(`[Trackers] Archiving tracker ${trackerId}`);
        const trackerCard = document.querySelector(`[data-tracker-id="${trackerId}"]`);

        try {
            // Optimistic UI - fade out the card
            if (trackerCard) {
                trackerCard.style.opacity = '0.5';
                trackerCard.style.pointerEvents = 'none';
            }

            await api.post(`/api/tracker/${trackerId}/delete/`);
            console.log(`[Trackers] ✅ Tracker ${trackerId} archived`);

            // Animate removal
            if (trackerCard) {
                trackerCard.style.transform = 'scale(0.9)';
                trackerCard.style.transition = 'all 0.3s ease';

                setTimeout(() => {
                    trackerCard.remove();

                    // Check if no more trackers, show empty state
                    const trackerGrid = document.querySelector('.grid-responsive');
                    if (trackerGrid && trackerGrid.children.length === 0) {
                        window.location.reload(); // Reload to show empty state
                    }
                }, 300);
            }

            ui.showToast('Tracker archived successfully', 'success');
        } catch (error) {
            console.error(`[Trackers] ❌ Failed to archive tracker ${trackerId}:`, error);

            // Revert optimistic UI
            if (trackerCard) {
                trackerCard.style.opacity = '1';
                trackerCard.style.pointerEvents = 'auto';
            }

            ui.showToast('Failed to archive tracker', 'error');
        }
    }

    async restoreTracker(trackerId) {
        console.log(`[Trackers] Restoring tracker ${trackerId}`);
        const archivedCard = document.querySelector(`[data-archived-id="${trackerId}"]`);

        try {
            // Optimistic UI
            if (archivedCard) {
                archivedCard.style.opacity = '0.5';
            }

            // Note: Assuming restore endpoint exists, adjust if different
            await api.post(`/api/tracker/${trackerId}/restore/`);
            console.log(`[Trackers] ✅ Tracker ${trackerId} restored`);

            ui.showToast('Tracker restored successfully', 'success');

            // Reload page to show in active trackers
            setTimeout(() => window.location.reload(), 500);
        } catch (error) {
            console.error(`[Trackers] ❌ Failed to restore tracker ${trackerId}:`, error);

            if (archivedCard) {
                archivedCard.style.opacity = '1';
            }

            ui.showToast('Failed to restore tracker', 'error');
        }
    }

    async loadMoreTrackers(page) {
        console.log(`[Trackers] Loading page ${page}`);
        const loadMoreBtn = event?.target;

        try {
            if (loadMoreBtn) {
                loadMoreBtn.disabled = true;
                loadMoreBtn.textContent = 'Loading...';
            }

            // Fetch next page
            const response = await fetch(`/trackers/?page=${page}`);
            const html = await response.text();

            // Parse HTML and extract tracker cards
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newTrackers = doc.querySelectorAll('.grid-responsive > a');

            // Append to existing grid
            const grid = document.querySelector('.grid-responsive');
            newTrackers.forEach(tracker => {
                grid.appendChild(tracker);
            });

            // Check if there are more pages
            const hasMoreBtn = doc.querySelector('[onclick*="loadMoreTrackers"]');
            if (!hasMoreBtn) {
                loadMoreBtn?.remove();
            } else {
                if (loadMoreBtn) {
                    loadMoreBtn.disabled = false;
                    loadMoreBtn.textContent = 'Load More';
                    // Update onclick with new page number
                    const nextPage = parseInt(page) + 1;
                    loadMoreBtn.setAttribute('onclick', `loadMoreTrackers(${nextPage})`);
                }
            }

            console.log(`[Trackers] ✅ Loaded ${newTrackers.length} more trackers`);
        } catch (error) {
            console.error('[Trackers] ❌ Failed to load more trackers:', error);

            if (loadMoreBtn) {
                loadMoreBtn.disabled = false;
                loadMoreBtn.textContent = 'Load More';
            }

            ui.showToast('Failed to load more trackers', 'error');
        }
    }

    /**
     * Update tracker stats in real-time (called after task toggle)
     */
    updateTrackerStats(trackerId, newStats) {
        console.log(`[Trackers] Updating stats for tracker ${trackerId}`, newStats);

        // Find stat elements on tracker detail page
        const progressValue = document.querySelector('[data-stat="progress-value"]');
        const progressBar = document.querySelector('[data-stat="progress-bar"]');
        const completedCount = document.querySelector('[data-stat="completed-count"]');
        const taskCount = document.querySelector('[data-stat="task-count"]');

        if (progressValue && newStats.progress !== undefined) {
            // Animate number change
            progressValue.classList.add('stat-updating');
            setTimeout(() => {
                progressValue.textContent = `${newStats.progress}%`;
                progressValue.classList.remove('stat-updating');
            }, 150);
        }

        if (progressBar && newStats.progress !== undefined) {
            progressBar.style.width = `${newStats.progress}%`;
        }

        if (completedCount && newStats.completed !== undefined) {
            completedCount.textContent = newStats.completed;
        }

        if (taskCount && newStats.total !== undefined) {
            taskCount.textContent = newStats.total;
        }
    }
}

export const trackers = new TrackerManager();
