/**
 * Tracker Pro - Analytics & Charts
 * Chart.js integration with interactive features
 */

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
        this.loadChartJS().then(() => {
            this.initAllCharts();
            this.bindTimeRangeSelector();
            this.bindChartTypeToggle();
            this.bindComparison();
            this.bindExport();
        });
    },

    async loadChartJS() {
        if (window.Chart) return;

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    },

    initAllCharts() {
        // Line/Bar chart
        this.initCompletionChart();

        // Pie chart
        this.initCategoryChart();

        // Time of day bar chart
        this.initTimeChart();

        // Heatmap (custom, not Chart.js)
        this.initHeatmap();

        // Comparison chart
        this.initComparisonChart();
    },

    // =========================================================================
    // COMPLETION TREND CHART
    // =========================================================================
    initCompletionChart() {
        const canvas = document.getElementById('completion-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Generate sample data (replace with real data from API)
        const labels = this.getLast30Days();
        const data = this.generateSampleData(30, 0, 100);

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
                    if (elements.length) {
                        const index = elements[0].index;
                        const date = labels[index];
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
    initCategoryChart() {
        const canvas = document.getElementById('category-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        const data = {
            labels: ['Work', 'Health', 'Learning', 'Personal', 'Other'],
            datasets: [{
                data: [35, 25, 20, 15, 5],
                backgroundColor: [
                    ChartConfig.colors.primary,
                    ChartConfig.colors.success,
                    ChartConfig.colors.warning,
                    '#8B5CF6',
                    ChartConfig.colors.gray
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
    initTimeChart() {
        const canvas = document.getElementById('time-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        this.charts.time = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Morning', 'Afternoon', 'Evening', 'Night'],
                datasets: [{
                    data: [45, 65, 40, 15],
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
    initHeatmap() {
        const grid = document.getElementById('heatmap-grid');
        if (!grid) return;

        // Generate 365 days of data
        const today = new Date();
        const oneYearAgo = new Date(today);
        oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);

        // Align to Sunday
        const startDay = oneYearAgo.getDay();
        oneYearAgo.setDate(oneYearAgo.getDate() - startDay);

        const cells = [];
        const currentDate = new Date(oneYearAgo);

        while (currentDate <= today) {
            const dateStr = currentDate.toISOString().split('T')[0];
            // Generate random level 0-4 (replace with real data)
            const level = Math.floor(Math.random() * 5);
            const count = level * 3;

            cells.push(`
                <span 
                    class="heatmap-cell" 
                    data-level="${level}" 
                    data-date="${dateStr}"
                    data-count="${count}"
                    title="${count} tasks on ${dateStr}"
                ></span>
            `);

            currentDate.setDate(currentDate.getDate() + 1);
        }

        grid.innerHTML = cells.join('');

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
        const labels = this.getLastNDays(days);
        const data = this.generateSampleData(days, 0, 100);

        if (this.charts.completion) {
            this.charts.completion.data.labels = labels;
            this.charts.completion.data.datasets[0].data = data;
            this.charts.completion.update('active');
        }
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
    // DRILL DOWN
    // =========================================================================
    drillDown(date) {
        // Navigate to day view
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

    generateSampleData(length, min, max) {
        // Replace with actual API call
        return Array.from({ length }, () =>
            Math.floor(Math.random() * (max - min + 1)) + min
        );
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
    }
};

// ============================================================================
// INITIALIZE
// ============================================================================
App.initAnalytics = function () {
    if (document.querySelector('.analytics-panel')) {
        ChartManager.init();
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
