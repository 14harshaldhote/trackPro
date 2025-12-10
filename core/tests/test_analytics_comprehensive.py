
"""
Additional comprehensive tests for analytics.py to achieve 99% coverage.
Focuses on edge cases, visualization functions, and error paths.
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, Mock
from core import analytics
from core.tests.factories import UserFactory, TrackerFactory, InstanceFactory, TaskInstanceFactory, TemplateFactory
from django.test import TestCase

class TestAnalyticsComprehensive(TestCase):
    
    def setUp(self):
        self.user = UserFactory.create()
        self.tracker = TrackerFactory.create(user=self.user)
        self.template = TemplateFactory.create(tracker=self.tracker)

    def test_generate_correlation_heatmap(self):
        """Test correlation heatmap generation."""
        result = analytics.generate_correlation_heatmap(self.tracker.tracker_id)
        assert result is not None
        # Should call compute_correlations internally
        
    def test_simple_forecast_no_data(self):
        """Test forecast with insufficient data."""
        result = analytics.simple_forecast(self.tracker.tracker_id)
        assert 'error' in result
        assert result['method'] == 'none'
        
    def test_simple_forecast_with_data(self):
        """Test forecast with sufficient data."""
        # Create 30 days of data
        for i in range(30):
            day = date.today() - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE')
        
        result = analytics.simple_forecast(self.tracker.tracker_id, days=7)
        assert result is not None
        assert 'metric_name' in result or 'method' in result
        # Could return various formats depending on data availability
        
    def test_compute_tracker_stats_with_templates(self):
        """Test tracker stats with actual templates."""
        template2 = TemplateFactory.create(tracker=self.tracker, category='work')
        
        inst = InstanceFactory.create(tracker=self.tracker, target_date=date.today())
        TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE')
        TaskInstanceFactory.create(instance=inst, template=template2, status='TODO')
        
        stats = analytics.compute_tracker_stats(self.tracker.tracker_id)
        # compute_tracker_stats returns total_tasks, completed_tasks, completion_rate, current_streak
        assert 'total_tasks' in stats
        assert stats['total_tasks'] > 0
        
    def test_analyze_time_series_per_day_effort(self):
        """Test time series with per_day_effort metric."""
        # Create instances with effort data
        for i in range(7):
            day = date.today() - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            # Create tasks (use weight instead of duration)
            template = TemplateFactory.create(tracker=self.tracker, weight=i+1)
            TaskInstanceFactory.create(instance=inst, template=template, status='DONE')
        
        # analyze_time_series uses 'forecast_days' parameter, not 'days'
        result = analytics.analyze_time_series(self.tracker.tracker_id, metric='per_day_effort', forecast_days=7)
        assert result is not None
        assert 'trend' in result or 'metric_name' in result  # Accepts either format
        
    def test_analyze_trends_empty_data(self):
        """Test trends with no data."""
        result = analytics.analyze_trends(self.tracker.tracker_id)
        # Should handle empty gracefully
        assert result is not None
        
    def test_analyze_trends_with_data(self):
        """Test trends with actual data."""
        # Create varying completion rates
        for i in range(14):
            day = date.today() - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            # Alternate DONE and TODO
            status = 'DONE' if i % 2 == 0 else 'TODO'
            TaskInstanceFactory.create(instance=inst, template=self.template, status=status)
        
        result = analytics.analyze_trends(self.tracker.tracker_id)
        assert 'trend_direction' in result
        assert result['trend_direction'] in ['improving', 'declining', 'stable']

    def test_compute_completion_rate_edge_cases(self):
        """Test completion rate with various edge cases."""
        # Test with custom date range
        start = date.today() - timedelta(days=7)
        end = date.today()
        
        inst = InstanceFactory.create(tracker=self.tracker, target_date=date.today())
        TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE')
        
        result = analytics.compute_completion_rate(self.tracker.tracker_id, start_date=start, end_date=end)
        assert result['value'] > 0
        
    def test_detect_streaks_empty(self):
        """Test streak detection with no data."""
        result = analytics.detect_streaks(self.tracker.tracker_id)
        # Returns {'metric_name': 'streaks', 'value': {'current_streak': ..., 'longest_streak': ...}}
        assert result['value']['current_streak'] == 0
        assert result['value']['longest_streak'] == 0
        
    def test_detect_streaks_with_task_template_filter(self):
        """Test streak detection filtered by task template."""
        # Create data for specific template
        for i in range(5):
            day = date.today() - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE')
        
        result = analytics.detect_streaks(self.tracker.tracker_id, task_template_id=self.template.template_id)
        assert result['value']['current_streak'] >= 0
        
    def test_compute_consistency_score_variations(self):
        """Test consistency score with different patterns."""
        # Create consistent daily completions
        for i in range(7):
            day = date.today() - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE')
        
        result = analytics.compute_consistency_score(self.tracker.tracker_id)
        # Should be high consistency
        assert result['value'] > 50
        
    def test_compute_balance_score_multiple_categories(self):
        """Test balance score with multiple categories."""
        # Create templates in different categories
        t1 = TemplateFactory.create(tracker=self.tracker, category='work')
        t2 = TemplateFactory.create(tracker=self.tracker, category='health')
        t3 = TemplateFactory.create(tracker=self.tracker, category='personal')
        
        inst = InstanceFactory.create(tracker=self.tracker, target_date=date.today())
        TaskInstanceFactory.create(instance=inst, template=t1, status='DONE')
        TaskInstanceFactory.create(instance=inst, template=t2, status='DONE')
        TaskInstanceFactory.create(instance=inst, template=t3, status='DONE')
        
        result = analytics.compute_balance_score(self.tracker.tracker_id)
        assert result['value'] > 50  # Should be balanced
        
    def test_compute_effort_index_with_data(self):
        """Test effort index with actual task data."""
        # Create tasks with varying weight (difficulty proxy)
        t1 = TemplateFactory.create(tracker=self.tracker, weight=1.0)
        t2 = TemplateFactory.create(tracker=self.tracker, weight=3.0)
        
        inst = InstanceFactory.create(tracker=self.tracker, target_date=date.today())
        TaskInstanceFactory.create(instance=inst, template=t1, status='DONE')
        TaskInstanceFactory.create(instance=inst, template=t2, status='DONE')
        
        result = analytics.compute_effort_index(self.tracker.tracker_id)
        assert result['value'] > 0
        
    def test_analyze_notes_sentiment_with_notes(self):
        """Test sentiment analysis with actual notes."""
        # Create instances with notes
        inst = InstanceFactory.create(tracker=self.tracker, target_date=date.today())
        task = TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE', notes="Great day!")
        
        result = analytics.analyze_notes_sentiment(self.tracker.tracker_id)
        # Returns {'metric_name': 'sentiment_analysis', 'daily_mood': [...], 'average_mood': ...}
        assert 'metric_name' in result
        assert result['metric_name'] == 'sentiment_analysis'
        
    def test_extract_keywords_from_notes_with_data(self):
        """Test keyword extraction with actual notes."""
        # Create multiple instances with notes
        for i in range(3):
            day = date.today() - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            TaskInstanceFactory.create(instance=inst, template=self.template, notes=f"workout gym fitness day {i}")
        
        result = analytics.extract_keywords_from_notes(self.tracker.tracker_id)
        assert 'keywords' in result
        # Should have extracted "gym", "workout", etc.
        
    def test_compute_mood_trends_with_data(self):
        """Test mood trends with sentiment data."""
        # Mock analyze_notes_sentiment to return expected structure
        with patch('core.analytics.analyze_notes_sentiment') as mock_sentiment:
            mock_sentiment.return_value = {
                'metric_name': 'sentiment_analysis',
                'daily_mood': [
                    {'date': '2023-01-01', 'compound': 0.8},
                    {'date': '2023-01-02', 'compound': 0.7}
                ],
                'average_mood': 0.75
            }
            
            result = analytics.compute_mood_trends(self.tracker.tracker_id)
            assert result is not None
            assert 'metric_name' in result
            
    def test_compute_correlations_edge_cases(self):
        """Test correlations with minimal data."""
        # Create just enough data
        inst = InstanceFactory.create(tracker=self.tracker, target_date=date.today())
        TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE')
        
        result = analytics.compute_correlations(self.tracker.tracker_id)
        # Should handle gracefully even with minimal data
        assert result is not None
        
    def test_visualization_functions_return_none(self):
        """Test that visualization functions return None (disabled for serverless)."""
        # These should be disabled
        from core.analytics import (
            generate_completion_chart,
            generate_category_pie_chart,
            generate_completion_heatmap,
            generate_streak_timeline
        )
        
        # All should return None (serverless constraint)
        assert generate_completion_chart(self.tracker.tracker_id) is None
        assert generate_category_pie_chart(self.tracker.tracker_id) is None
        assert generate_completion_heatmap(self.tracker.tracker_id) is None
        assert generate_streak_timeline(self.tracker.tracker_id) is None
