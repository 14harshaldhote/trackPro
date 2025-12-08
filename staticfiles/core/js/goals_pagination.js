/**
 * Goals Pagination & Infinite Scroll
 * Loads goals progressively with infinite scroll and "Load More" fallback
 */

class GoalsPagination {
    constructor(options = {}) {
        this.container = options.container || document.querySelector('.goals-list');
        this.sentinel = null;
        this.loadMoreBtn = null;
        this.currentPage = 1;
        this.perPage = options.perPage || 20;
        this.status = options.status || 'all';
        this.sort = options.sort || '-created_at';
        this.hasMore = true;
        this.loading = false;
        this.observer = null;

        // Cache
        this.cache = new Map();
        this.cacheExpiry = 5 * 60 * 1000; // 5 minutes

        this.init();
    }

    init() {
        if (!this.container) {
            console.warn('[GoalsPagination] Container not found');
            return;
        }

        // Create UI elements
        this.createSentinel();
        this.createLoadMoreButton();

        // Setup infinite scroll observer
        if ('IntersectionObserver' in window) {
            this.setupIntersectionObserver();
        } else {
            // Fallback to Load More button only
            console.log('[GoalsPagination] IntersectionObserver not supported, using Load More only');
        }

        // Load first page
        this.loadPage(1);
    }

    createSentinel() {
        this.sentinel = document.createElement('div');
        this.sentinel.className = 'scroll-sentinel';
        this.sentinel.style.height = '1px';
        this.container.appendChild(this.sentinel);
    }

    createLoadMoreButton() {
        this.loadMoreBtn = document.createElement('button');
        this.loadMoreBtn.className = 'btn btn-secondary load-more-btn';
        this.loadMoreBtn.textContent = 'Load More Goals';
        this.loadMoreBtn.style.display = 'none';
        this.loadMoreBtn.addEventListener('click', () => this.loadMore());
        this.container.appendChild(this.loadMoreBtn);
    }

    setupIntersectionObserver() {
        this.observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && !this.loading && this.hasMore) {
                    this.loadMore();
                }
            },
            { threshold: 0.1, rootMargin: '100px' }
        );

        this.observer.observe(this.sentinel);
    }

    async loadPage(page, options = {}) {
        if (this.loading) return;

        this.loading = true;
        this.showLoading();

        try {
            // Check cache
            const cacheKey = this.getCacheKey(page);
            const cached = this.getFromCache(cacheKey);

            if (cached && !options.force) {
                this.renderGoals(cached.goals, page === 1);
                this.updatePaginationState(cached.pagination);
                this.loading = false;
                this.hideLoading();
                return;
            }

            // Fetch from API
            const url = `/api/v1/goals/?page=${page}&per_page=${this.perPage}&status=${this.status}&sort=${this.sort}`;

            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Failed to load goals');
            }

            // Cache result
            this.addToCache(cacheKey, result);

            // Render
            this.renderGoals(result.goals, page === 1);
            this.updatePaginationState(result.pagination);

        } catch (error) {
            console.error('[GoalsPagination] Error loading page:', error);
            this.showError('Failed to load goals. Please try again.');
        } finally {
            this.loading = false;
            this.hideLoading();
        }
    }

    loadMore() {
        if (!this.hasMore || this.loading) return;

        this.currentPage++;
        this.loadPage(this.currentPage);
    }

    renderGoals(goals, clearFirst = false) {
        if (clearFirst) {
            // Clear existing goals (keep sentinel and button)
            const goalCards = this.container.querySelectorAll('.goal-card');
            goalCards.forEach(card => card.remove());
        }

        if (goals.length === 0 && clearFirst) {
            this.showEmptyState();
            return;
        }

        // Insert goals before sentinel
        goals.forEach(goal => {
            const card = this.createGoalCard(goal);
            this.container.insertBefore(card, this.sentinel);
        });
    }

    createGoalCard(goal) {
        const card = document.createElement('div');
        card.className = `goal-card goal-${goal.status}`;
        card.dataset.goalId = goal.goal_id;

        const progressPercent = goal.progress || 0;
        const statusBadge = goal.status === 'completed' ? '✅' : goal.status === 'archived' ? '📦' : '🎯';

        card.innerHTML = `
            <div class="goal-header">
                <div class="goal-icon">${goal.icon || '🎯'}</div>
                <div class="goal-info">
                    <h3 class="goal-title">${this.escapeHtml(goal.title)}</h3>
                    <p class="goal-description">${this.escapeHtml(goal.description || '')}</p>
                </div>
                <div class="goal-status-badge">${statusBadge}</div>
            </div>
            <div class="goal-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progressPercent}%"></div>
                </div>
                <div class="progress-text">${progressPercent}%</div>
            </div>
            <div class="goal-footer">
                <span class="goal-type">${goal.goal_type}</span>
                ${goal.target_date ? `<span class="goal-date">📅 ${new Date(goal.target_date).toLocaleDateString()}</span>` : ''}
                ${goal.target_value ? `<span class="goal-target">${goal.current_value || 0} / ${goal.target_value} ${goal.unit}</span>` : ''}
            </div>
        `;

        return card;
    }

    updatePaginationState(pagination) {
        this.hasMore = pagination.has_next;
        this.currentPage = pagination.current_page;

        // Update Load More button
        if (this.hasMore) {
            this.loadMoreBtn.style.display = 'block';
            this.loadMoreBtn.textContent = `Load More (${pagination.total_count - (pagination.current_page * pagination.per_page)} remaining)`;
        } else {
            this.loadMoreBtn.style.display = 'none';
        }
    }

    showLoading() {
        if (!this.loadingIndicator) {
            this.loadingIndicator = document.createElement('div');
            this.loadingIndicator.className = 'goals-loading';
            this.loadingIndicator.innerHTML = '<div class="spinner"></div><p>Loading goals...</p>';
        }

        this.container.insertBefore(this.loadingIndicator, this.sentinel);
    }

    hideLoading() {
        if (this.loadingIndicator && this.loadingIndicator.parentNode) {
            this.loadingIndicator.remove();
        }
    }

    showEmptyState() {
        const empty = document.createElement('div');
        empty.className = 'goals-empty-state';
        empty.innerHTML = `
            <div class="empty-icon">🎯</div>
            <h3>No Goals Yet</h3>
            <p>Create your first goal to get started!</p>
            <button class="btn btn-primary create-goal-btn">Create Goal</button>
        `;
        this.container.insertBefore(empty, this.sentinel);
    }

    showError(message) {
        if (window.App && window.App.showToast) {
            window.App.showToast('error', 'Error', message);
        } else {
            alert(message);
        }
    }

    // Cache methods
    getCacheKey(page) {
        return `goals_${this.status}_${this.sort}_${page}`;
    }

    getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;

        if (Date.now() - cached.timestamp > this.cacheExpiry) {
            this.cache.delete(key);
            return null;
        }

        return cached.data;
    }

    addToCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    clearCache() {
        this.cache.clear();
    }

    // Helpers
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Public methods
    refresh() {
        this.clearCache();
        this.currentPage = 1;
        this.loadPage(1, { force: true });
    }

    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }

        if (this.sentinel) {
            this.sentinel.remove();
        }

        if (this.loadMoreBtn) {
            this.loadMoreBtn.remove();
        }

        this.cache.clear();
    }
}

// Export for use
window.GoalsPagination = GoalsPagination;

// Auto-initialize if goals panel exists
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('.goals-panel .goals-list')) {
        window.goalsPagination = new GoalsPagination({
            perPage: 20,
            status: 'all',
            sort: '-created_at'
        });
    }
});
