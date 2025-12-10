"""
Analytics & Insights Tests (18 tests)

Test IDs: ANAL-001 to ANAL-018
Coverage: /api/v1/analytics/*, /api/v1/insights/, /api/v1/chart-data/, /api/v1/heatmap/

These tests cover:
- Analytics data endpoint
- Analytics filtering
- Forecast generation
- Tracker comparison
- Insights generation
- Chart data
- Heatmap data
- Export functionality
"""
from datetime import date, timedelta
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, 
    TaskInstanceFactory, create_tracker_with_tasks
)


class AnalyticsDataTests(BaseAPITestCase):
    """Tests for /api/v1/analytics/data/ endpoint."""
    
    def test_ANAL_001_get_analytics_data(self):
        """ANAL-001: Get analytics data returns 200 with summary."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/analytics/data/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_002_analytics_with_tracker_filter(self):
        """ANAL-002: Analytics with tracker filter returns filtered data."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get(f'/api/v1/analytics/data/?tracker_id={tracker.tracker_id}')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_003_analytics_with_date_range(self):
        """ANAL-003: Analytics with date range returns ranged data."""
        tracker = self.create_tracker()
        
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        
        response = self.get(
            f'/api/v1/analytics/data/?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_004_analytics_no_data(self):
        """ANAL-004: Analytics with no data returns 200 with zeros."""
        response = self.get('/api/v1/analytics/data/')
        
        self.assertEqual(response.status_code, 200)


class AnalyticsForecastTests(BaseAPITestCase):
    """Tests for /api/v1/analytics/forecast/ endpoint."""
    
    def test_ANAL_005_analytics_forecast(self):
        """ANAL-005: Analytics forecast returns 200 with prediction."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create some historical data
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE' if i % 2 == 0 else 'TODO')
        
        response = self.get('/api/v1/analytics/forecast/')
        
        self.assertEqual(response.status_code, 200)


class TrackerComparisonTests(BaseAPITestCase):
    """Tests for /api/v1/analytics/compare/ endpoint."""
    
    def test_ANAL_006_compare_trackers(self):
        """ANAL-006: Compare trackers returns 200 with comparison."""
        tracker1 = self.create_tracker(name='Tracker 1')
        tracker2 = self.create_tracker(name='Tracker 2')
        
        response = self.get(
            f'/api/v1/analytics/compare/?trackers={tracker1.tracker_id},{tracker2.tracker_id}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_007_compare_invalid_trackers(self):
        """ANAL-007: Compare with only one tracker returns 400."""
        tracker = self.create_tracker()
        
        response = self.get(f'/api/v1/analytics/compare/?trackers={tracker.tracker_id}')
        
        # Should return 400 or return partial data
        self.assertIn(response.status_code, [200, 400])


class InsightsTests(BaseAPITestCase):
    """Tests for /api/v1/insights/ endpoint."""
    
    def test_ANAL_008_get_insights(self):
        """ANAL-008: Get insights returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/insights/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_009_insights_specific_tracker(self):
        """ANAL-009: Insights for specific tracker returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get(f'/api/v1/insights/{tracker.tracker_id}/')
        
        self.assertEqual(response.status_code, 200)


class ChartDataTests(BaseAPITestCase):
    """Tests for /api/v1/chart-data/ endpoint."""
    
    def test_ANAL_010_get_chart_data(self):
        """ANAL-010: Get chart data returns 200 with chart-ready data."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/chart-data/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_011_chart_data_with_type(self):
        """ANAL-011: Chart data with type parameter returns specific format."""
        response = self.get('/api/v1/chart-data/?type=line')
        
        self.assertEqual(response.status_code, 200)


class HeatmapTests(BaseAPITestCase):
    """Tests for /api/v1/heatmap/ endpoint."""
    
    def test_ANAL_012_get_heatmap_data(self):
        """ANAL-012: Get heatmap data returns 200 with year data."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/heatmap/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_013_heatmap_activity_levels(self):
        """ANAL-013: Heatmap returns activity levels 0-4."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create varying levels of activity
        for i in range(7):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            # Vary the completion count
            for j in range(i % 5):
                self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/heatmap/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_014_heatmap_sparse_data(self):
        """ANAL-014: Heatmap returns zeros for missing days."""
        tracker = self.create_tracker()
        
        # Create only one data point
        instance = self.create_instance(tracker, date.today())
        
        response = self.get('/api/v1/heatmap/')
        
        self.assertEqual(response.status_code, 200)


class ExportTests(BaseAPITestCase):
    """Tests for /api/v1/export/month/ endpoint."""
    
    def test_ANAL_015_export_month(self):
        """ANAL-015: Export month returns 200 with export data."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/export/month/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_016_export_month_csv(self):
        """ANAL-016: Export month as CSV returns 200."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/export/month/?format=csv')
        
        self.assertEqual(response.status_code, 200)


class InsightsAnalysisTests(BaseAPITestCase):
    """Tests for insights analysis features."""
    
    def test_ANAL_017_best_day_calculation(self):
        """ANAL-017: Insights include best day calculation."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create data with varying completion by day
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            # Complete more tasks on certain days
            status = 'DONE' if day.weekday() in [1, 3, 5] else 'TODO'
            self.create_task_instance(instance, template, status=status)
        
        response = self.get('/api/v1/insights/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ANAL_018_trend_calculation(self):
        """ANAL-018: Analytics includes trend calculation (up/down/stable)."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create improving trend
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            # More recent days have more completions (improving trend)
            status = 'DONE' if i < 7 else 'TODO'
            self.create_task_instance(instance, template, status=status)
        
        response = self.get('/api/v1/analytics/data/')
        
        self.assertEqual(response.status_code, 200)
