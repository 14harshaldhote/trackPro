/**
 * Tracker Pro - Analytics & Charts
 * Chart.js integration with interactive features
 * With comprehensive console logging
 */

// Console logging helper
const analyticsLog = (module, action, data = {}) => {
    const emoji = data.status === 'SUCCESS' ? '✅' : data.status === 'ERROR' ? '❌' : data.status === 'WARNING' ? '⚠️' : 'ℹ️';
    console.log(`[Analytics/${module}] ${emoji} ${action}`, { timestamp: new Date().toISOString(), module, action, ...data });
};

// ============================================================================
// CHART.JS CONFIGURATION
// ============================================================================
const ChartConfig = {
    colors: {
        primary: getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#0277BD',
        primaryRgb: '2, 119, 189',
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444',
        gray: '#6B7280',
        gridColor: 'rgba(0, 0, 0, 0.05)'
    },

    fonts: {
        family: getComputedStyle(document.body).fontFamily || 'system-ui, sans-serif'
    },

    defaultOptions: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 750,
            easing: 'easeOutQuart'
        },
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                titleColor: '#fff',
                bodyColor: '#fff',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1,
                padding: 12,
                cornerRadius: 8,
                displayColors: false
            }
        }
    }
};

// ============================================================================
// CHART MANAGER
// ============================================================================
const ChartManager = {
    charts: {},

    init() {
        analyticsLog('ChartManager', 'INIT_START', { status: 'INFO', message: 'Loading Chart.js and initializing charts' });
        this.loadChartJS().then(() => {
            analyticsLog('ChartManager', 'CHARTJS_LOADED', { status: 'SUCCESS', message: 'Chart.js loaded' });
            this.initAllCharts();
            this.bindTimeRangeSelector();
            this.bindChartTypeToggle();
            this.bindComparison();
            this.bindExport();
            analyticsLog('ChartManager', 'INIT_COMPLETE', { status: 'SUCCESS', message: 'All charts initialized' });
        }).catch(err => {
            analyticsLog('ChartManager', 'INIT_ERROR', { status: 'ERROR', error: err.message });
        });
    },

    async loadChartJS() {
        if (window.Chart) {
            analyticsLog('ChartManager', 'CHARTJS_CACHED', { status: 'INFO', message: 'Chart.js already loaded' });
            return;
        }

        const cdnUrl = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
        analyticsLog('ChartManager', 'CHARTJS_LOADING', { status: 'INFO', url: cdnUrl, method: 'GET' });
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = cdnUrl;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    },

    initAllCharts() {
        analyticsLog('ChartManager', 'LOADING_DATA', { status: 'INFO', message: 'Fetching analytics data from API' });

        // Fetch real data from API
        this.loadAnalyticsData().then(data => {
            analyticsLog('ChartManager', 'DATA_LOADED', { status: 'SUCCESS', message: 'Analytics data received', dataKeys: Object.keys(data) });

            // Initialize charts with real data
            this.initCompletionChart(data.completion_trend);
            this.initCategoryChart(data.category_distribution);
            this.initTimeChart(data.time_of_day);
            this.initHeatmap(data.heatmap);
            this.initComparisonChart();

            // Render insights
            if (data.insights && data.insights.length > 0) {
                this.renderInsights(data.insights);
            }

        }).catch(err => {
            analyticsLog('ChartManager', 'DATA_ERROR', { status: 'ERROR', error: err.message });
            this.showErrorState(err.message);
        });
    },

    showErrorState(message) {
        document.querySelectorAll('.chart-wrapper canvas').forEach(canvas => {
            const wrapper = canvas.closest('.chart-wrapper');
            if (wrapper) {
                // Remove loading
                const loading = wrapper.querySelector('.chart-loading');
                if (loading) loading.style.display = 'none';

                // Add error message
                let errorMsg = wrapper.querySelector('.chart-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'chart-error';
                    errorMsg.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: var(--color-danger);';
                    wrapper.appendChild(errorMsg);
                }
                errorMsg.innerHTML = `<p>⚠️ Failed to load data</p><small>${message}</small>`;
                canvas.style.opacity = '0.3';
            }
        });

        const heatmapGrid = document.getElementById('heatmap-grid');
        if (heatmapGrid) {
            heatmapGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--color-text-muted);">Unable to load activity heatmap</div>`;
        }
    },

    async loadAnalyticsData(days = 30) {
        const url = `/api/v1/analytics/data/?days=${days}`;

        analyticsLog('ChartManager', 'API_REQUEST', { status: 'INFO', url, method: 'GET' });

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Failed to load analytics data');
        }

        return result.data;
    },

    // =========================================================================
    // COMPLETION TREND CHART
    // =========================================================================
    initCompletionChart(chartData) {
        const canvas = document.getElementById('completion-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Use real data if provided, otherwise fall back to sample
        // Use real data if provided
        const labels = chartData?.labels || [];
        const data = chartData?.data || [];

        if (labels.length === 0) {
            this.showNoDataState(canvas, 'No completion data available');
            return;
        }

        this.charts.completion = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Completion Rate',
                    data,
                    borderColor: ChartConfig.colors.primary,
                    backgroundColor: `rgba(${ChartConfig.colors.primaryRgb}, 0.1)`,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: ChartConfig.colors.primary,
                    pointHoverBorderColor: '#fff',
                    pointHoverBorderWidth: 2
                }]
            },
            options: {
                ...ChartConfig.defaultOptions,
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 7 }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: ChartConfig.colors.gridColor },
                        ticks: {
                            callback: value => `${value}%`
                        }
                    }
                },
                onClick: (e, elements) => {
                    if (elements.length && chartData?.dates) {
                        const index = elements[0].index;
                        const date = chartData.dates[index];
                        this.drillDown(date);
                    }
                }
            }
        });

        canvas.closest('.chart-wrapper').querySelector('.chart-loading').style.display = 'none';
    },

    // =========================================================================
    // CATEGORY PIE CHART
    // =========================================================================
    initCategoryChart(chartData) {
        const canvas = document.getElementById('category-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (!chartData || !chartData.data || chartData.data.length === 0) {
            this.showNoDataState(canvas, 'No category data available');
            return;
        }

        const data = {
            labels: chartData.labels,
            datasets: [{
                data: chartData.data,
                backgroundColor: [
                    ChartConfig.colors.primary,
                    ChartConfig.colors.success,
                    ChartConfig.colors.warning,
                    '#8B5CF6',
                    ChartConfig.colors.gray,
                    '#EC4899'
                ],
                borderWidth: 0,
                hoverOffset: 8
            }]
        };

        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data,
            options: {
                ...ChartConfig.defaultOptions,
                cutout: '65%',
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        // Generate custom legend
        this.generatePieLegend('category-chart-legend', data);

        canvas.closest('.chart-wrapper').querySelector('.chart-loading').style.display = 'none';
    },

    generatePieLegend(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const html = data.labels.map((label, i) => `
            <div class="legend-item">
                <span class="legend-color" style="background: ${data.datasets[0].backgroundColor[i]}"></span>
                <span class="legend-label">${label}</span>
                <span class="legend-value">${data.datasets[0].data[i]}%</span>
            </div>
        `).join('');

        container.innerHTML = html;
    },

    // =========================================================================
    // TIME OF DAY BAR CHART
    // =========================================================================
    initTimeChart(chartData) {
        const canvas = document.getElementById('time-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        if (!chartData || !chartData.data || chartData.data.length === 0) {
            this.showNoDataState(canvas, 'No time data available');
            return;
        }

        this.charts.time = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    data: chartData.data,
                    backgroundColor: [
                        `rgba(${ChartConfig.colors.primaryRgb}, 0.6)`,
                        ChartConfig.colors.primary,
                        `rgba(${ChartConfig.colors.primaryRgb}, 0.6)`,
                        `rgba(${ChartConfig.colors.primaryRgb}, 0.3)`
                    ],
                    borderRadius: 6,
                    barThickness: 40
                }]
            },
            options: {
                ...ChartConfig.defaultOptions,
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        grid: { color: ChartConfig.colors.gridColor },
                        ticks: { callback: value => `${value}%` }
                    }
                }
            }
        });

        canvas.closest('.chart-wrapper').querySelector('.chart-loading').style.display = 'none';
    },

    // =========================================================================
    // HEATMAP (Custom Implementation)
    // =========================================================================
    initHeatmap(heatmapData) {
        const grid = document.getElementById('heatmap-grid');
        if (!grid) return;

        // Use real data if provided
        const cells = [];

        if (heatmapData && heatmapData.length > 0) {
            // Use API data
            heatmapData.forEach(day => {
                cells.push(`
                    <span 
                        class="heatmap-cell" 
                        data-level="${day.level}" 
                        data-date="${day.date}"
                        data-count="${day.count}"
                        title="${day.count} tasks on ${day.date}"
                        role="gridcell"
                        tabindex="0"
                        aria-label="${day.count} tasks on ${day.date}"
                    ></span>
                `);
            });
            grid.innerHTML = cells.join('');

            // Add responsiveness
            const wrapper = grid.closest('.heatmap-wrapper');
            if (wrapper) {
                wrapper.style.overflowX = 'auto';
                wrapper.style.paddingBottom = '10px';
            }
            grid.style.minWidth = 'max-content'; // Ensure horizontal scroll triggers
            grid.setAttribute('role', 'grid');

        } else {
            // No data state
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--color-text-muted);">No activity data recorded yet</div>`;
        }

        // Tooltip handling
        grid.addEventListener('mouseover', (e) => {
            const cell = e.target.closest('.heatmap-cell');
            if (!cell) return;

            const tooltip = document.getElementById('heatmap-tooltip');
            const count = cell.dataset.count;
            const date = cell.dataset.date;

            tooltip.querySelector('.tooltip-count').textContent = `${count} tasks`;
            tooltip.querySelector('.tooltip-date').textContent = new Date(date).toLocaleDateString('en-US', {
                weekday: 'long', month: 'short', day: 'numeric'
            });

            const rect = cell.getBoundingClientRect();
            tooltip.style.display = 'block';
            tooltip.style.left = `${rect.left + rect.width / 2}px`;
            tooltip.style.top = `${rect.top - 50}px`;
        });

        grid.addEventListener('mouseout', () => {
            document.getElementById('heatmap-tooltip').style.display = 'none';
        });

        // Click to drill down
        grid.addEventListener('click', (e) => {
            const cell = e.target.closest('.heatmap-cell');
            if (cell) {
                this.drillDown(cell.dataset.date);
            }
        });
    },

    // =========================================================================
    // INSIGHTS RENDERER
    // =========================================================================
    renderInsights(insights) {
        const container = document.getElementById('insights-container');
        if (!container) return;

        const html = insights.map(insight => `
            <div class="insight-card insight-${insight.type}">
                <div class="insight-icon">${insight.icon}</div>
                <div class="insight-content">
                    <h3 class="insight-title">${insight.title}</h3>
                    <p class="insight-message">${insight.message}</p>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
        analyticsLog('Charts', 'INSIGHTS_RENDERED', { status: 'SUCCESS', count: insights.length });
    },

    // =========================================================================
    // COMPARISON CHART
    // =========================================================================
    initComparisonChart() {
        const canvas = document.getElementById('comparison-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const labels = this.getLast30Days();

        this.charts.comparison = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: []
            },
            options: {
                ...ChartConfig.defaultOptions,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: ChartConfig.colors.gridColor }
                    }
                }
            }
        });

        canvas.closest('.chart-wrapper').querySelector('.chart-loading').style.display = 'none';
    },

    // =========================================================================
    // TIME RANGE SELECTOR
    // =========================================================================
    bindTimeRangeSelector() {
        document.querySelectorAll('.range-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const days = parseInt(btn.dataset.range);
                this.updateChartsRange(days);
            });
        });
    },

    updateChartsRange(days) {
        // Since we removed fake data generation, this needs to fetch new data
        // For now, we can just reload the full analytics data or implement range fetching
        // But given the scope, reloading is safest to ensure consistency

        if (window.App && window.App.showLoading) {
            window.App.showLoading('Updating charts...');
        }

        this.loadAnalyticsData(days).then(data => {
            if (this.charts.completion) {
                this.charts.completion.data.labels = data.completion_trend.labels;
                this.charts.completion.data.datasets[0].data = data.completion_trend.data;
                this.charts.completion.update();
            }
            if (window.App && window.App.hideLoading) {
                window.App.hideLoading();
            }
        }).catch(err => {
            if (window.App && window.App.hideLoading) {
                window.App.hideLoading();
            }
            console.error('Failed to update chart range', err);
        });
    },

    // =========================================================================
    // CHART TYPE TOGGLE
    // =========================================================================
    bindChartTypeToggle() {
        document.querySelectorAll('.chart-type-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.dataset.type;

                document.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                if (this.charts.completion) {
                    this.charts.completion.config.type = type;
                    this.charts.completion.update('active');
                }
            });
        });
    },

    // =========================================================================
    // COMPARISON MODE
    // =========================================================================
    bindComparison() {
        const select1 = document.getElementById('compare-tracker-1');
        const select2 = document.getElementById('compare-tracker-2');

        const updateComparison = () => {
            const tracker1 = select1?.value;
            const tracker2 = select2?.value;

            if (!tracker1) return;

            const labels = this.getLast30Days();
            const datasets = [{
                label: select1?.options[select1.selectedIndex]?.text || 'Tracker 1',
                data: this.generateSampleData(30, 0, 100),
                borderColor: ChartConfig.colors.primary,
                backgroundColor: 'transparent',
                tension: 0.4
            }];

            if (tracker2) {
                datasets.push({
                    label: select2?.options[select2.selectedIndex]?.text || 'Tracker 2',
                    data: this.generateSampleData(30, 0, 100),
                    borderColor: ChartConfig.colors.success,
                    backgroundColor: 'transparent',
                    tension: 0.4
                });
            }

            if (this.charts.comparison) {
                this.charts.comparison.data.labels = labels;
                this.charts.comparison.data.datasets = datasets;
                this.charts.comparison.update('active');
            }
        };

        select1?.addEventListener('change', updateComparison);
        select2?.addEventListener('change', updateComparison);

        // Initial load
        updateComparison();
    },

    // =========================================================================
    // EXPORT CHARTS
    // =========================================================================
    bindExport() {
        document.getElementById('export-charts')?.addEventListener('click', () => {
            this.exportAllCharts();
        });
    },

    exportAllCharts() {
        Object.entries(this.charts).forEach(([name, chart]) => {
            const link = document.createElement('a');
            link.download = `${name}-chart.png`;
            link.href = chart.toBase64Image();
            link.click();
        });

        App.showToast('success', 'Charts exported');
    },

    exportChart(chartId) {
        const chart = this.charts[chartId];
        if (!chart) return;

        const link = document.createElement('a');
        link.download = `${chartId}-chart.png`;
        link.href = chart.toBase64Image();
        link.click();
    },

    // =========================================================================
    // MONTH EXPORT
    // =========================================================================
    async exportMonth(year, month, format = 'json') {
        analyticsLog('Export', 'EXPORT_START', { status: 'INFO', year, month, format });

        try {
            if (window.App && window.App.showLoading) {
                window.App.showLoading('Exporting data...');
            }

            const response = await fetch('/api/v1/export/month/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.apiClient?.getCsrfToken() || this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin',
                body: JSON.stringify({ year, month, format })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `HTTP ${response.status}`);
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;

            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `export_${year}_${month}.${format}`;
            if (contentDisposition) {
                const matches = /filename="?([^"]+)"?/.exec(contentDisposition);
                if (matches) filename = matches[1];
            }

            link.download = filename;
            link.click();

            // Cleanup
            window.URL.revokeObjectURL(url);

            if (window.App && window.App.hideLoading) {
                window.App.hideLoading();
            }

            if (window.App && window.App.showToast) {
                window.App.showToast('success', 'Export complete', `Downloaded ${filename}`);
            }

            analyticsLog('Export', 'EXPORT_SUCCESS', { status: 'SUCCESS', filename });

        } catch (error) {
            analyticsLog('Export', 'EXPORT_ERROR', { status: 'ERROR', error: error.message });

            if (window.App && window.App.hideLoading) {
                window.App.hideLoading();
            }

            if (window.App && window.App.showToast) {
                window.App.showToast('error', 'Export failed', error.message);
            }
        }
    },

    getCsrfToken() {
        const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    },

    // =========================================================================
    // DRILL DOWN
    // =========================================================================
    drillDown(date) {
        analyticsLog('Charts', 'DRILL_DOWN', { status: 'INFO', date, url: `/today/?date=${date}` });
        App.loadPanel(`/today/?date=${date}`);
    },

    // =========================================================================
    // HELPERS
    // =========================================================================
    getLast30Days() {
        return this.getLastNDays(30);
    },

    getLastNDays(n) {
        const dates = [];
        for (let i = n - 1; i >= 0; i--) {
            const d = new Date();
            d.setDate(d.getDate() - i);
            dates.push(d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        }
        return dates;
    },

    showNoDataState(canvas, message) {
        const wrapper = canvas.closest('.chart-wrapper');
        if (wrapper) {
            // Remove loading
            const loading = wrapper.querySelector('.chart-loading');
            if (loading) loading.style.display = 'none';

            // Add no data message
            let msgEl = wrapper.querySelector('.chart-no-data');
            if (!msgEl) {
                msgEl = document.createElement('div');
                msgEl.className = 'chart-no-data';
                msgEl.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; color: var(--color-text-muted);';
                wrapper.appendChild(msgEl);
            }
            msgEl.innerHTML = `<p>${message}</p>`;
            canvas.style.opacity = '0.1';
        }
    }
};

// ============================================================================
// GOAL ANIMATIONS
// ============================================================================
const GoalAnimations = {
    init() {
        this.animateProgressRings();
        this.bindGoalCompletion();
    },

    animateProgressRings() {
        document.querySelectorAll('.goal-progress-ring').forEach(ring => {
            const progress = parseFloat(ring.dataset.progress) || 0;
            const circle = ring.querySelector('.progress-fill');

            // Calculate stroke offset
            const circumference = 2 * Math.PI * 42; // radius = 42
            const offset = circumference - (progress / 100) * circumference;

            // Animate
            setTimeout(() => {
                circle.style.strokeDashoffset = offset;
            }, 100);
        });
    },

    bindGoalCompletion() {
        document.querySelectorAll('.goal-card.completed').forEach(card => {
            if (!card.dataset.celebrated) {
                card.dataset.celebrated = 'true';
                this.celebrate();
            }
        });
    },

    celebrate() {
        this.confetti();
    },

    confetti() {
        const canvas = document.getElementById('confetti-canvas');
        if (!canvas) return;

        canvas.style.display = 'block';
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles = [];
        const colors = ['#F59E0B', '#10B981', '#3B82F6', '#EF4444', '#8B5CF6'];

        for (let i = 0; i < 150; i++) {
            particles.push({
                x: canvas.width / 2,
                y: canvas.height / 2,
                vx: (Math.random() - 0.5) * 20,
                vy: (Math.random() - 0.5) * 20 - 10,
                color: colors[Math.floor(Math.random() * colors.length)],
                size: Math.random() * 8 + 4,
                rotation: Math.random() * 360,
                rotationSpeed: (Math.random() - 0.5) * 10
            });
        }

        let frame = 0;
        const animate = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.5; // gravity
                p.rotation += p.rotationSpeed;

                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate(p.rotation * Math.PI / 180);
                ctx.fillStyle = p.color;
                ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                ctx.restore();
            });

            frame++;
            if (frame < 120) {
                requestAnimationFrame(animate);
            } else {
                canvas.style.display = 'none';
            }
        };

        animate();
    }
};

// ============================================================================
// INSIGHTS ENGINE
// ============================================================================
const InsightsEngine = {
    generateInsights(data) {
        const insights = [];

        // Best day analysis
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const bestDayIndex = data.dayStats?.indexOf(Math.max(...(data.dayStats || []))) || 2;
        insights.push({
            type: 'pattern',
            icon: '📅',
            title: 'Best Day',
            message: `You're most productive on ${days[bestDayIndex]}s`
        });

        // Streak insight
        if (data.currentStreak >= 7) {
            insights.push({
                type: 'achievement',
                icon: '🔥',
                title: 'Hot Streak!',
                message: `You've maintained a ${data.currentStreak}-day streak. Keep it up!`
            });
        }

        // Consistency insight
        if (data.consistency >= 80) {
            insights.push({
                type: 'success',
                icon: '⭐',
                title: 'Highly Consistent',
                message: 'You complete tasks reliably. Your consistency is in the top 20%!'
            });
        }

        return insights;
    },

    getForecast(data) {
        const rate = data.avgCompletionRate || 0;
        const remaining = data.goalRemaining || 0;

        if (rate === 0) {
            return { message: 'Complete some tasks to see your forecast!', days_analyzed: 0 };
        }

        const daysToComplete = Math.ceil(remaining / rate);

        return {
            message: `At your current pace, you'll reach your goal in ${daysToComplete} days`,
            days_analyzed: 30
        };
    },

    async loadForecast(days = 7) {
        /**
         * Load forecast from API
         */
        try {
            const url = `/api/v1/analytics/forecast/?days=${days}`;

            analyticsLog('Forecast', 'LOADING', { status: 'INFO', url });

            const response = await fetch(url, {
                method: 'GET',
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
                throw new Error(result.error || 'Forecast failed');
            }

            analyticsLog('Forecast', 'LOADED', { status: 'SUCCESS', confidence: result.forecast.confidence });

            return result;

        } catch (error) {
            analyticsLog('Forecast', 'ERROR', { status: 'ERROR', error: error.message });
            return null;
        }
    },

    renderForecast(forecastData) {
        /**
         * Render forecast visualization and summary
         */
        const container = document.getElementById('forecast-container');
        if (!container) return;

        if (!forecastData) {
            container.innerHTML = '<p class="forecast-error">Unable to load forecast</p>';
            return;
        }

        const { forecast, summary } = forecastData;

        // Get trend icon
        const trendIcons = {
            'increasing': '📈',
            'decreasing': '📉',
            'stable': '➡️'
        };

        const trendIcon = trendIcons[forecast.trend] || '📊';

        // Render summary
        const html = `
            <div class="forecast-summary">
                <div class="forecast-header">
                    <span class="forecast-icon">${trendIcon}</span>
                    <h3>7-Day Forecast</h3>
                    <span class="forecast-confidence">${Math.round(forecast.confidence * 100)}% confidence</span>
                </div>
                <p class="forecast-message">${summary.message}</p>
                <p class="forecast-recommendation">${summary.recommendation}</p>
                <div class="forecast-stats">
                    <div class="forecast-stat">
                        <span class="stat-label">Current Rate</span>
                        <span class="stat-value">${forecast.current_rate}%</span>
                    </div>
                    <div class="forecast-stat">
                        <span class="stat-label">Predicted</span>
                        <span class="stat-value">${forecast.predictions[forecast.predictions.length - 1]}%</span>
                    </div>
                    <div class="forecast-stat">
                        <span class="stat-label">Change</span>
                        <span class="stat-value stat-${summary.predicted_change >= 0 ? 'positive' : 'negative'}">
                            ${summary.predicted_change >= 0 ? '+' : ''}${summary.predicted_change}%
                        </span>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // If there's a forecast chart canvas, render it
        this.renderForecastChart(forecast);
    },

    renderForecastChart(forecast) {
        /**
         * Render forecast as a line chart with confidence intervals
         */
        const canvas = document.getElementById('forecast-chart');
        if (!canvas || !window.Chart) return;

        const ctx = canvas.getContext('2d');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: forecast.labels,
                datasets: [
                    {
                        label: 'Predicted',
                        data: forecast.predictions,
                        borderColor: ChartConfig.colors.primary,
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'Upper Bound',
                        data: forecast.upper_bound,
                        borderColor: `rgba(${ChartConfig.colors.primaryRgb}, 0.3)`,
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointRadius: 0
                    },
                    {
                        label: 'Lower Bound',
                        data: forecast.lower_bound,
                        borderColor: `rgba(${ChartConfig.colors.primaryRgb}, 0.3)`,
                        backgroundColor: 'transparent',
                        borderWidth: 1,
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                ...ChartConfig.defaultOptions,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        grid: { display: false }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: ChartConfig.colors.gridColor },
                        ticks: {
                            callback: value => `${value}%`
                        }
                    }
                }
            }
        });
    }
};

// ============================================================================
// INITIALIZE
// ============================================================================
App.initAnalytics = function () {
    if (document.querySelector('.analytics-panel')) {
        ChartManager.init();

        // Load forecast if container exists
        if (document.getElementById('forecast-container')) {
            InsightsEngine.loadForecast(7).then(forecastData => {
                if (forecastData) {
                    InsightsEngine.renderForecast(forecastData);
                }
            });
        }
    }
    if (document.querySelector('.goals-panel')) {
        GoalAnimations.init();
    }
};

// Auto-run on panel load
const originalBindPanelEvents3 = App.bindPanelEvents.bind(App);
App.bindPanelEvents = function () {
    originalBindPanelEvents3();
    this.initAnalytics();
};

// Expose exportMonth globally for button clicks
window.exportMonth = function (format = 'json') {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;

    ChartManager.exportMonth(year, month, format);
};
