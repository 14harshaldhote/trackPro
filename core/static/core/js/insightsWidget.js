/**
 * Insights Widget - Display behavioral insights from backend InsightsEngine
 */

class InsightsWidget {
    constructor(container) {
        this.container = typeof container === 'string' ?
            document.querySelector(container) : container;
        this.insights = [];
        this.trackerId = null;
    }

    // Load insights from backend
    async loadInsights(trackerId = null) {
        this.trackerId = trackerId;

        try {
            const endpoint = trackerId ?
                `/insights/${trackerId}/` :
                '/insights/';

            const data = await window.apiClient.get(endpoint);
            this.insights = data.insights || [];
            this.render();
        } catch (error) {
            console.error('[Insights] Failed to load insights:', error);
            this.renderError();
        }
    }

    // Render insights
    render() {
        if (!this.container) return;

        if (this.insights.length === 0) {
            this.container.innerHTML = this.renderEmpty();
            return;
        }

        const html = `
            <div class="insights-widget">
                <div class="insights-header">
                    <h3 class="insights-title">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <path d="M12 16v-4"></path>
                            <path d="M12 8h.01"></path>
                        </svg>
                        Behavioral Insights
                    </h3>
                    <button class="btn btn-ghost btn-sm" onclick="insightsWidget.refresh()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="23 4 23 10 17 10"></polyline>
                            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
                        </svg>
                    </button>
                </div>
                <div class="insights-list">
                    ${this.insights.slice(0, 3).map(insight => this.renderInsight(insight)).join('')}
                </div>
                ${this.insights.length > 3 ? `
                    <button class="btn btn-ghost btn-sm w-full" onclick="insightsWidget.showAll()">
                        View all ${this.insights.length} insights
                    </button>
                ` : ''}
            </div>
        `;

        this.container.innerHTML = html;
    }

    // Render single insight
    renderInsight(insight) {
        const severityClass = `insight-${insight.severity || 'low'}`;
        const icon = this.getSeverityIcon(insight.severity);

        return `
            <div class="insight-card ${severityClass}">
                <div class="insight-icon">${icon}</div>
                <div class="insight-content">
                    <h4 class="insight-title">${this.escapeHtml(insight.title)}</h4>
                    <p class="insight-description">${this.escapeHtml(insight.description)}</p>
                    ${insight.suggested_action ? `
                        <div class="insight-action">
                            <strong>💡 Suggestion:</strong> ${this.escapeHtml(insight.suggested_action)}
                        </div>
                    ` : ''}
                    ${insight.research_note ? `
                        <details class="insight-research">
                            <summary>Research backing</summary>
                            <p>${this.escapeHtml(insight.research_note)}</p>
                        </details>
                    ` : ''}
                </div>
            </div>
        `;
    }

    // Get icon for severity level
    getSeverityIcon(severity) {
        const icons = {
            high: '🔴',
            medium: '🟡',
            low: '🟢'
        };
        return icons[severity] || '💡';
    }

    // Render empty state
    renderEmpty() {
        return `
            <div class="insights-widget insights-empty">
                <div class="insights-empty-icon">✨</div>
                <p>No insights yet. Keep tracking to unlock behavioral insights!</p>
            </div>
        `;
    }

    // Render error state
    renderError() {
        if (!this.container) return;

        this.container.innerHTML = `
            <div class="insights-widget insights-error">
                <p>Failed to load insights. <button class="btn-link" onclick="insightsWidget.refresh()">Try again</button></p>
            </div>
        `;
    }

    // Escape HTML to prevent XSS
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Refresh insights
    async refresh() {
        await this.loadInsights(this.trackerId);
    }

    // Show all insights in modal
    showAll() {
        if (window.App && window.App.loadModal) {
            const url = this.trackerId ?
                `/modals/insights/?tracker_id=${this.trackerId}` :
                '/modals/insights/';
            window.App.loadModal(url);
        }
    }
}

// Global instance
window.InsightsWidget = InsightsWidget;

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InsightsWidget;
}
