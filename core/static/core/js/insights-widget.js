/**
 * Insights Widget - Display behavioral insights from InsightsEngine
 * Integrates with backend behavioral/insights_engine.py
 */

(function (window) {
    'use strict';

    class InsightsWidget {
        constructor(containerId, trackerId = null) {
            this.container = document.getElementById(containerId);
            this.trackerId = trackerId;
            this.insights = [];
        }

        /**
         * Load insights from backend
         * @param {string} trackerId - Optional tracker ID, if null loads user-level insights
         */
        async load(trackerId = null) {
            const id = trackerId || this.trackerId;
            const endpoint = id ? `/insights/${id}/` : '/insights/';

            try {
                const response = await window.api.get(endpoint);
                this.insights = response.insights || [];
                this.render();
                return this.insights;
            } catch (error) {
                console.error('[InsightsWidget] Failed to load insights:', error);
                this.renderError();
                return [];
            }
        }

        /**
         * Render insights in container
         */
        render() {
            if (!this.container) {
                console.warn('[InsightsWidget] Container not found');
                return;
            }

            if (this.insights.length === 0) {
                this.container.innerHTML = `
                    <div class="empty-state-sm">
                        <p>No insights available yet. Keep tracking!</p>
                    </div>
                `;
                return;
            }

            const html = this.insights.map(insight => this.renderInsight(insight)).join('');
            this.container.innerHTML = html;
        }

        /**
         * Render single insight card
         */
        renderInsight(insight) {
            const severityColors = {
                high: 'danger',
                medium: 'warning',
                low: 'info'
            };

            const severityIcons = {
                high: '⚠️',
                medium: '💡',
                low: 'ℹ️'
            };

            const color = severityColors[insight.severity] || 'info';
            const icon = severityIcons[insight.severity] || 'ℹ️';

            return `
                <div class="insight-card insight-${color}" data-insight-type="${insight.type}">
                    <div class="insight-header">
                        <span class="insight-icon">${icon}</span>
                        <h4 class="insight-title">${this.escapeHtml(insight.title)}</h4>
                    </div>
                    <p class="insight-description">${this.escapeHtml(insight.description)}</p>
                    ${insight.suggested_action ? `
                        <div class="insight-action">
                            <strong>💪 Action:</strong> ${this.escapeHtml(insight.suggested_action)}
                        </div>
                    ` : ''}
                    ${insight.research_note && insight.confidence > 0.7 ? `
                        <details class="insight-research">
                            <summary>Research backing</summary>
                            <p class="text-muted">${this.escapeHtml(insight.research_note)}</p>
                        </details>
                    ` : ''}
                    <div class="insight-meta">
                        <span class="confidence-badge">Confidence: ${Math.round(insight.confidence * 100)}%</span>
                    </div>
                </div>
            `;
        }

        /**
         * Render error state
         */
        renderError() {
            if (!this.container) return;

            this.container.innerHTML = `
                <div class="alert alert-warning">
                    <p>Unable to load insights. Please try again later.</p>
                </div>
            `;
        }

        /**
         * Escape HTML to prevent XSS
         */
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        /**
         * Get top insight (highest severity)
         */
        getTopInsight() {
            if (this.insights.length === 0) return null;

            const severityOrder = { high: 0, medium: 1, low: 2 };
            return this.insights.sort((a, b) =>
                severityOrder[a.severity] - severityOrder[b.severity]
            )[0];
        }

        /**
         * Filter insights by severity
         */
        filterBySeverity(severity) {
            return this.insights.filter(i => i.severity === severity);
        }
    }

    // Export to window
    window.InsightsWidget = InsightsWidget;

    console.log('[InsightsWidget] Initialized');

})(window);
