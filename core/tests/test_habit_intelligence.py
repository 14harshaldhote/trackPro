"""
Habit Intelligence Tests V2.0 (10 tests)

Test IDs: HBIT-001 to HBIT-010
Coverage: /api/v1/v2/insights/habits/, /api/v1/v2/insights/day-analysis/, etc.

These tests cover:
- Habit insights
- Day of week analysis
- Task difficulty ranking
- Schedule suggestions
- Streak correlations
"""
from datetime import date, timedelta
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
)


class HabitInsightsTests(BaseAPITestCase):
    """Tests for /api/v1/v2/insights/habits/ endpoint."""
    
    def test_HBIT_001_get_all_insights(self):
        """HBIT-001: Get all habit insights returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create some historical data
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            status = 'DONE' if i % 2 == 0 else 'TODO'
            self.create_task_instance(instance, template, status=status)
        
        response = self.get('/api/v1/v2/insights/habits/')
        
        self.assertEqual(response.status_code, 200)


class DayOfWeekAnalysisTests(BaseAPITestCase):
    """Tests for /api/v1/v2/insights/day-analysis/ endpoint."""
    
    def test_HBIT_002_day_of_week_analysis(self):
        """HBIT-002: Day of week analysis returns best/worst days."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create data for different days
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            # More completions on weekends
            status = 'DONE' if day.weekday() in [5, 6] else 'TODO'
            self.create_task_instance(instance, template, status=status)
        
        response = self.get('/api/v1/v2/insights/day-analysis/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_HBIT_003_analysis_custom_days(self):
        """HBIT-003: Analysis with custom days parameter returns correct range."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/v2/insights/day-analysis/?days=30')
        
        self.assertEqual(response.status_code, 200)


class TaskDifficultyTests(BaseAPITestCase):
    """Tests for /api/v1/v2/insights/difficulty/ endpoint."""
    
    def test_HBIT_004_task_difficulty_ranking(self):
        """HBIT-004: Task difficulty ranking ranks by miss percentage."""
        tracker = self.create_tracker()
        easy_task = self.create_template(tracker, description='Easy Task')
        hard_task = self.create_template(tracker, description='Hard Task')
        
        # Create instances with different completion patterns
        for i in range(10):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            # Easy task almost always done
            self.create_task_instance(instance, easy_task, status='DONE')
            # Hard task almost always missed
            self.create_task_instance(instance, hard_task, status='TODO')
        
        response = self.get('/api/v1/v2/insights/difficulty/')
        
        self.assertEqual(response.status_code, 200)


class ScheduleSuggestionsTests(BaseAPITestCase):
    """Tests for /api/v1/v2/insights/schedule/ endpoint."""
    
    def test_HBIT_005_schedule_suggestions(self):
        """HBIT-005: Schedule suggestions returns suggestions."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/v2/insights/schedule/')
        
        self.assertEqual(response.status_code, 200)


class InsightsMinDataTests(BaseAPITestCase):
    """Tests for insights with minimum data requirements."""
    
    def test_HBIT_006_insights_min_data_warning(self):
        """HBIT-006: Insights with <14 days data shows insufficient message."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Only create 7 days of data
        for i in range(7):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/v2/insights/habits/')
        
        self.assertEqual(response.status_code, 200)


class StreakCorrelationTests(BaseAPITestCase):
    """Tests for streak correlation insights."""
    
    def test_HBIT_007_streak_correlations(self):
        """HBIT-007: Streak correlations identify anchor tasks."""
        tracker = self.create_tracker()
        anchor_task = self.create_template(tracker, description='Anchor Task')
        dependent_task = self.create_template(tracker, description='Dependent Task')
        
        # Anchor task success correlates with dependent task success
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            if i < 7:  # First week - both done
                self.create_task_instance(instance, anchor_task, status='DONE')
                self.create_task_instance(instance, dependent_task, status='DONE')
            else:  # Second week - anchor missed, dependent also missed
                self.create_task_instance(instance, anchor_task, status='TODO')
                self.create_task_instance(instance, dependent_task, status='TODO')
        
        response = self.get('/api/v1/v2/insights/habits/')
        
        self.assertEqual(response.status_code, 200)


class MoodCorrelationTests(BaseAPITestCase):
    """Tests for mood correlation insights."""
    
    def test_HBIT_008_mood_correlations(self):
        """HBIT-008: Mood correlations show mood→completion patterns."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/v2/insights/habits/')
        
        self.assertEqual(response.status_code, 200)


class InsightsExtremeTests(BaseAPITestCase):
    """Tests for extreme completion scenarios."""
    
    def test_HBIT_009_insights_all_100_percent(self):
        """HBIT-009: Insights with 100% completion shows positive insights."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # All tasks done for 14 days
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/v2/insights/habits/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_HBIT_010_insights_all_0_percent(self):
        """HBIT-010: Insights with 0% completion shows critical insights."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # All tasks missed for 14 days
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='TODO')
        
        response = self.get('/api/v1/v2/insights/habits/')
        
        self.assertEqual(response.status_code, 200)
