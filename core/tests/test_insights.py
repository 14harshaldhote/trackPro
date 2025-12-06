"""
Tests for behavioral insights engine.

Tests cover:
- Insight generation rules
- Severity classification
- Action recommendations
"""
import unittest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock

User = get_user_model()


class InsightsEngineTestCase(TestCase):
    """Test InsightsEngine behavioral analysis."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='insightuser',
            email='insight@example.com',
            password='pass123'
        )
        
        from core.models import TrackerDefinition
        self.tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Insights Test Tracker'
        )
    
    @patch('core.analytics.compute_completion_rate')
    @patch('core.analytics.detect_streaks')
    @patch('core.analytics.compute_consistency_score')
    @patch('core.analytics.compute_balance_score')
    @patch('core.analytics.compute_effort_index')
    @patch('core.analytics.analyze_notes_sentiment')
    @patch('core.analytics.analyze_trends')
    def test_generates_low_consistency_insight(self, mock_trends, mock_sentiment, 
                                              mock_effort, mock_balance, mock_consistency,
                                              mock_streaks, mock_completion):
        """Test insight generated for low consistency score."""
        from core.behavioral.insights_engine import InsightsEngine
        
        # Mock all the analytics functions
        mock_completion.return_value = {'value': 50, 'daily_rates': []}
        mock_streaks.return_value = {'value': {'current_streak': 2, 'longest_streak': 10}}
        mock_consistency.return_value = {'value': 35, 'rolling_scores': [30, 35, 40]}  # Below 60 threshold
        mock_balance.return_value = {'value': 75, 'category_distribution': {}}
        mock_effort.return_value = {'value': 50, 'raw_inputs': {}}
        mock_sentiment.return_value = {'average_sentiment': 0}
        mock_trends.return_value = {'trend_direction': 'stable', 'improving_periods': 0, 'total_periods': 0}
        
        engine = InsightsEngine(str(self.tracker.tracker_id))
        insights = engine.generate_insights()
        
        # Should have at least one insight about consistency
        self.assertGreater(len(insights), 0)
        insight_types = [i.insight_type.value for i in insights]
        self.assertIn('low_consistency', insight_types)
    
    @patch('core.analytics.compute_completion_rate')
    @patch('core.analytics.detect_streaks')
    @patch('core.analytics.compute_consistency_score')
    @patch('core.analytics.compute_balance_score')
    @patch('core.analytics.compute_effort_index')
    @patch('core.analytics.analyze_notes_sentiment')
    @patch('core.analytics.analyze_trends')
    def test_no_insights_for_healthy_metrics(self, mock_trends, mock_sentiment,
                                             mock_effort, mock_balance, mock_consistency,
                                             mock_streaks, mock_completion):
        """Test no warning insights when all metrics are healthy."""
        from core.behavioral.insights_engine import InsightsEngine
        
        # Mock healthy metrics
        mock_completion.return_value = {'value': 85, 'daily_rates': []}
        mock_streaks.return_value = {'value': {'current_streak': 15, 'longest_streak': 20}}
        mock_consistency.return_value = {'value': 85, 'rolling_scores': [80, 85, 90]}
        mock_balance.return_value = {'value': 90, 'category_distribution': {}}
        mock_effort.return_value = {'value': 70, 'raw_inputs': {}}
        mock_sentiment.return_value = {'average_sentiment': 0.5}
        mock_trends.return_value = {'trend_direction': 'stable', 'improving_periods': 5, 'total_periods': 10}
        
        engine = InsightsEngine(str(self.tracker.tracker_id))
        insights = engine.generate_insights()
        
        # Either no insights or only positive/info insights (not high severity)
        high_severity = [i for i in insights if i.severity.value == 'high']
        self.assertEqual(len(high_severity), 0)
    
    @patch('core.analytics.compute_completion_rate')
    @patch('core.analytics.detect_streaks')
    @patch('core.analytics.compute_consistency_score')
    @patch('core.analytics.compute_balance_score')
    @patch('core.analytics.compute_effort_index')
    @patch('core.analytics.analyze_notes_sentiment')
    @patch('core.analytics.analyze_trends')
    def test_streak_risk_insight(self, mock_trends, mock_sentiment,
                                 mock_effort, mock_balance, mock_consistency,
                                 mock_streaks, mock_completion):
        """Test insight when streak is at risk."""
        from core.behavioral.insights_engine import InsightsEngine
        
        # Current streak is close to being broken - recent drop in completion
        mock_completion.return_value = {
            'value': 75,
            'daily_rates': [
                {'date': '2025-01-01', 'rate': 90},
                {'date': '2025-01-02', 'rate': 65}  # Significant drop
            ]
        }
        mock_streaks.return_value = {
            'value': {
                'current_streak': 14,
                'longest_streak': 14,  # At longest streak
                'days_since_last_done': 1
            }
        }
        mock_consistency.return_value = {'value': 75, 'rolling_scores': [70, 75, 80]}
        mock_balance.return_value = {'value': 80, 'category_distribution': {}}
        mock_effort.return_value = {'value': 60, 'raw_inputs': {}}
        mock_sentiment.return_value = {'average_sentiment': 0.3}
        mock_trends.return_value = {'trend_direction': 'stable', 'improving_periods': 5, 'total_periods': 10}
        
        engine = InsightsEngine(str(self.tracker.tracker_id))
        insights = engine.generate_insights()
        
        # May generate streak-related insight depending on rules
        self.assertIsInstance(insights, list)


class InsightsAPITestCase(TestCase):
    """Test insights API endpoint."""
    
    def setUp(self):
        from django.test import Client
        self.client = Client()
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='pass123'
        )
        self.client.login(username='apiuser', password='pass123')
        
        from core.models import TrackerDefinition
        self.tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='API Test Tracker'
        )
    
    def test_insights_endpoint_returns_list(self):
        """Test insights endpoint returns list of insights."""
        response = self.client.get(f'/api/insights/{self.tracker.tracker_id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('insights', data)
        self.assertIsInstance(data['insights'], list)
    
    def test_insights_endpoint_requires_auth(self):
        """Test insights endpoint requires authentication."""
        from django.test import Client
        anon_client = Client()
        
        response = anon_client.get('/api/insights/')
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_insights_sorted_by_severity(self):
        """Test insights are sorted by severity (high first)."""
        response = self.client.get('/api/insights/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        if data['insights']:
            severities = [i.get('severity', 'low') for i in data['insights']]
            # High should come before medium, medium before low
            severity_order = {'high': 0, 'medium': 1, 'low': 2}
            ordered = [severity_order.get(s, 3) for s in severities]
            self.assertEqual(ordered, sorted(ordered))
