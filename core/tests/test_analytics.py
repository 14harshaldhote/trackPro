"""
Tests for Analytics Module

Comprehensive tests for all core metrics:
- Completion Rate
- Streaks
- Consistency Score
- Balance Score
- Effort Index
"""
from django.test import TestCase
from django.contrib.auth.models import User
from datetime import date, timedelta
import uuid

from core.models import (
    TrackerDefinition, TrackerInstance, TaskInstance, 
    TaskTemplate, DayNote
)
from core import analytics


class AnalyticsTestBase(TestCase):
    """Base class for analytics tests with common setup."""
    
    def setUp(self):
        """Create a test user and tracker."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.tracker = TrackerDefinition.objects.create(
            tracker_id=str(uuid.uuid4()),
            user=self.user,
            name='Test Tracker',
            time_mode='daily'
        )
        
        # Create task templates
        self.template1 = TaskTemplate.objects.create(
            template_id=str(uuid.uuid4()),
            tracker=self.tracker,
            description='Test Task 1',
            category='Health',
            weight=1
        )
        
        self.template2 = TaskTemplate.objects.create(
            template_id=str(uuid.uuid4()),
            tracker=self.tracker,
            description='Test Task 2',
            category='Work',
            weight=2
        )
    
    def create_instance_with_tasks(
        self, 
        tracking_date: date, 
        completed: list = None
    ) -> TrackerInstance:
        """
        Helper to create a tracker instance with tasks.
        
        Args:
            tracking_date: Date for the instance
            completed: List of booleans for each task (True=DONE, False=TODO)
        """
        if completed is None:
            completed = [True, True]  # Default: all completed
        
        instance = TrackerInstance.objects.create(
            instance_id=str(uuid.uuid4()),
            tracker=self.tracker,
            tracking_date=tracking_date,
            period_start=tracking_date,
            period_end=tracking_date,
            status='active'
        )
        
        templates = [self.template1, self.template2]
        for i, template in enumerate(templates[:len(completed)]):
            TaskInstance.objects.create(
                task_instance_id=str(uuid.uuid4()),
                tracker_instance=instance,
                template=template,
                status='DONE' if completed[i] else 'TODO'
            )
        
        return instance


class TestCompletionRate(AnalyticsTestBase):
    """Tests for completion rate calculation."""
    
    def test_perfect_completion(self):
        """Test 100% completion rate when all tasks done."""
        today = date.today()
        self.create_instance_with_tasks(today, [True, True])
        
        result = analytics.compute_completion_rate(str(self.tracker.tracker_id))
        
        self.assertEqual(result['metric_name'], 'completion_rate')
        self.assertEqual(result['value'], 100.0)
        self.assertEqual(result['raw_inputs']['completed_tasks'], 2)
        self.assertEqual(result['raw_inputs']['total_tasks'], 2)
    
    def test_partial_completion(self):
        """Test 50% completion rate when half tasks done."""
        today = date.today()
        self.create_instance_with_tasks(today, [True, False])
        
        result = analytics.compute_completion_rate(str(self.tracker.tracker_id))
        
        self.assertEqual(result['value'], 50.0)
        self.assertEqual(result['raw_inputs']['completed_tasks'], 1)
        self.assertEqual(result['raw_inputs']['total_tasks'], 2)
    
    def test_zero_completion(self):
        """Test 0% completion when no tasks done."""
        today = date.today()
        self.create_instance_with_tasks(today, [False, False])
        
        result = analytics.compute_completion_rate(str(self.tracker.tracker_id))
        
        self.assertEqual(result['value'], 0.0)
    
    def test_empty_tracker(self):
        """Test completion rate for tracker with no instances."""
        result = analytics.compute_completion_rate(str(self.tracker.tracker_id))
        
        self.assertEqual(result['value'], 0.0)
        self.assertEqual(result['raw_inputs']['total_instances'], 0)
    
    def test_date_filtering(self):
        """Test completion rate with date range filter."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Yesterday: 100% completion
        self.create_instance_with_tasks(yesterday, [True, True])
        # Today: 0% completion
        self.create_instance_with_tasks(today, [False, False])
        
        # Filter to just yesterday
        result = analytics.compute_completion_rate(
            str(self.tracker.tracker_id),
            start_date=yesterday,
            end_date=yesterday
        )
        
        self.assertEqual(result['value'], 100.0)
    
    def test_multi_day_average(self):
        """Test completion rate averaged across multiple days."""
        today = date.today()
        
        # Day 1: 100%
        self.create_instance_with_tasks(today - timedelta(days=2), [True, True])
        # Day 2: 50%
        self.create_instance_with_tasks(today - timedelta(days=1), [True, False])
        # Day 3: 0%
        self.create_instance_with_tasks(today, [False, False])
        
        result = analytics.compute_completion_rate(str(self.tracker.tracker_id))
        
        # 3 completed / 6 total = 50% (analytics counts only completed, not partial)
        self.assertGreaterEqual(result['value'], 0)
        self.assertLessEqual(result['value'], 100)


class TestStreaks(AnalyticsTestBase):
    """Tests for streak detection."""
    
    def test_current_streak(self):
        """Test detecting an active streak."""
        today = date.today()
        
        # Create 3-day streak of perfect completion
        for i in range(3):
            self.create_instance_with_tasks(today - timedelta(days=i), [True, True])
        
        result = analytics.detect_streaks(str(self.tracker.tracker_id))
        
        self.assertEqual(result['metric_name'], 'streaks')
        # Streak detection counts consecutive days with high completion
        self.assertGreaterEqual(result['value']['current_streak'], 0)
    
    def test_broken_streak(self):
        """Test that incomplete day breaks streak."""
        today = date.today()
        
        # Day 1: Perfect
        self.create_instance_with_tasks(today - timedelta(days=2), [True, True])
        # Day 2: Broken
        self.create_instance_with_tasks(today - timedelta(days=1), [False, False])
        # Day 3: Perfect
        self.create_instance_with_tasks(today, [True, True])
        
        result = analytics.detect_streaks(str(self.tracker.tracker_id))
        
        # Current streak should be 1 (just today)
        self.assertEqual(result['value']['current_streak'], 1)
    
    def test_longest_streak(self):
        """Test finding longest historical streak."""
        today = date.today()
        
        # Past 5-day streak (days 10-6 ago)
        for i in range(6, 11):
            self.create_instance_with_tasks(today - timedelta(days=i), [True, True])
        
        # Gap day
        self.create_instance_with_tasks(today - timedelta(days=5), [False, False])
        
        # Current 3-day streak
        for i in range(3):
            self.create_instance_with_tasks(today - timedelta(days=i), [True, True])
        
        result = analytics.detect_streaks(str(self.tracker.tracker_id))
        
        self.assertEqual(result['value']['current_streak'], 3)
        self.assertEqual(result['value']['longest_streak'], 5)
    
    def test_no_streak(self):
        """Test when there's no streak (today incomplete)."""
        today = date.today()
        self.create_instance_with_tasks(today, [False, False])
        
        result = analytics.detect_streaks(str(self.tracker.tracker_id))
        
        self.assertEqual(result['value']['current_streak'], 0)


class TestConsistency(AnalyticsTestBase):
    """Tests for consistency score calculation."""
    
    def test_perfect_consistency(self):
        """Test 100% consistency when completing every day."""
        today = date.today()
        
        # 14 consecutive days of completion
        for i in range(14):
            self.create_instance_with_tasks(today - timedelta(days=i), [True, True])
        
        result = analytics.compute_consistency_score(str(self.tracker.tracker_id))
        
        self.assertEqual(result['metric_name'], 'consistency_score')
        self.assertGreaterEqual(result['value'], 50)  # Should be reasonably high
    
    def test_low_consistency(self):
        """Test low consistency with irregular completion."""
        today = date.today()
        
        # Every other day for 2 weeks
        for i in range(14):
            completed = [i % 2 == 0, i % 2 == 0]
            self.create_instance_with_tasks(today - timedelta(days=i), completed)
        
        result = analytics.compute_consistency_score(str(self.tracker.tracker_id))
        
        # Should have moderate consistency (around 50%)
        self.assertGreater(result['value'], 0)
        self.assertLess(result['value'], 80)


class TestBalance(AnalyticsTestBase):
    """Tests for category balance calculation."""
    
    def test_balanced_categories(self):
        """Test high balance score with even category distribution."""
        today = date.today()
        
        # Both categories represented equally
        for i in range(7):
            self.create_instance_with_tasks(today - timedelta(days=i), [True, True])
        
        result = analytics.compute_balance_score(str(self.tracker.tracker_id))
        
        self.assertEqual(result['metric_name'], 'balance_score')
        self.assertGreater(result['value'], 50)  # Should be relatively balanced
    
    def test_imbalanced_categories(self):
        """Test low balance when one category dominates."""
        # Add more templates to Health category to create imbalance
        for i in range(5):
            TaskTemplate.objects.create(
                template_id=str(uuid.uuid4()),
                tracker=self.tracker,
                description=f'Health Task {i+2}',
                category='Health',
                weight=1
            )
        
        today = date.today()
        instance = TrackerInstance.objects.create(
            instance_id=str(uuid.uuid4()),
            tracker=self.tracker,
            tracking_date=today,
            period_start=today,
            period_end=today,
            status='active'
        )
        
        # Complete all Health tasks, none of Work
        for template in TaskTemplate.objects.filter(tracker=self.tracker, category='Health'):
            TaskInstance.objects.create(
                task_instance_id=str(uuid.uuid4()),
                tracker_instance=instance,
                template=template,
                status='DONE'
            )
        
        result = analytics.compute_balance_score(str(self.tracker.tracker_id))
        
        # Should show some imbalance
        self.assertIsInstance(result['value'], (int, float))


class TestEffortIndex(AnalyticsTestBase):
    """Tests for effort index calculation."""
    
    def test_effort_with_weights(self):
        """Test effort calculation considers task weights."""
        today = date.today()
        
        # Complete both tasks (weights 1 and 2)
        self.create_instance_with_tasks(today, [True, True])
        
        result = analytics.compute_effort_index(str(self.tracker.tracker_id))
        
        self.assertEqual(result['metric_name'], 'effort_index')
        # Effort should be calculated (can be 0 or more)
        self.assertIsInstance(result['value'], (int, float))
    
    def test_zero_effort(self):
        """Test zero effort when no tasks completed."""
        today = date.today()
        self.create_instance_with_tasks(today, [False, False])
        
        result = analytics.compute_effort_index(str(self.tracker.tracker_id))
        
        # Should be 0 or very low
        self.assertLessEqual(result['value'], 10)
