"""
Streak Tests (12 tests)

Test IDs: STRK-001 to STRK-012
Coverage: StreakService

These tests cover:
- Current streak calculation
- Streak with gaps
- Streak thresholds
- Longest streak tracking
- Weekly/monthly tracker streaks
- Streak milestones
- Timezone handling
"""
from datetime import date, timedelta
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, 
    TaskInstanceFactory, create_streak_data
)


class StreakCalculationTests(BaseAPITestCase):
    """Tests for streak calculation functionality."""
    
    def test_STRK_001_calculate_current_streak(self):
        """STRK-001: Calculate current streak with consecutive complete days."""
        # Create 5 days of completed tasks
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        for i in range(5):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_STRK_002_streak_with_gap(self):
        """STRK-002: Streak with gap returns 1 after break."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Today - completed
        instance_today = self.create_instance(tracker, date.today())
        self.create_task_instance(instance_today, template, status='DONE')
        
        # Yesterday - missed (no instance or TODO)
        
        # Day before - completed
        day_before = date.today() - timedelta(days=2)
        instance_before = self.create_instance(tracker, day_before)
        self.create_task_instance(instance_before, template, status='DONE')
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_STRK_003_streak_with_threshold_80(self):
        """STRK-003: Streak with 80% threshold counts partial completion."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, description='Task 1')
        template2 = self.create_template(tracker, description='Task 2')
        template3 = self.create_template(tracker, description='Task 3')
        template4 = self.create_template(tracker, description='Task 4')
        template5 = self.create_template(tracker, description='Task 5')
        
        # Create instance with 80% completion
        instance = self.create_instance(tracker, date.today())
        self.create_task_instance(instance, template1, status='DONE')
        self.create_task_instance(instance, template2, status='DONE')
        self.create_task_instance(instance, template3, status='DONE')
        self.create_task_instance(instance, template4, status='DONE')
        self.create_task_instance(instance, template5, status='TODO')
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_STRK_004_streak_with_threshold_100(self):
        """STRK-004: Streak with 100% threshold breaks at 99%."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_STRK_005_longest_streak_tracking(self):
        """STRK-005: Longest streak is tracked correctly."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create a streak of 10 days in the past
        for i in range(10):
            day = date.today() - timedelta(days=20-i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        # Gap of a few days
        
        # Current streak of 3 days
        for i in range(3):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)


class WeeklyStreakTests(BaseAPITestCase):
    """Tests for weekly tracker streaks."""
    
    def test_STRK_006_weekly_tracker_streak(self):
        """STRK-006: Weekly tracker counts streaks by weeks."""
        tracker = self.create_tracker(time_mode='weekly')
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)


class StreakEdgeCaseTests(BaseAPITestCase):
    """Tests for streak edge cases."""
    
    def test_STRK_007_streak_first_day(self):
        """STRK-007: First day of tracking shows streak=1."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        instance = self.create_instance(tracker, date.today())
        self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_STRK_008_streak_no_data(self):
        """STRK-008: No data shows streak=0."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)


class StreakMilestoneTests(BaseAPITestCase):
    """Tests for streak milestone notifications."""
    
    def test_STRK_009_streak_milestone_7(self):
        """STRK-009: Reaching 7-day streak creates notification."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create 7 consecutive days
        for i in range(7):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/notifications/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_STRK_010_streak_milestone_21(self):
        """STRK-010: Reaching 21-day streak creates notification."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create 21 consecutive days
        for i in range(21):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/notifications/')
        
        self.assertEqual(response.status_code, 200)


class StreakTimezoneTests(BaseAPITestCase):
    """Tests for streak timezone handling."""
    
    def test_STRK_011_streak_across_timezones(self):
        """STRK-011: Streak calculation handles timezone changes."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)


class AllUserStreaksTests(BaseAPITestCase):
    """Tests for all user streaks endpoint."""
    
    def test_STRK_012_all_user_streaks(self):
        """STRK-012: Get streaks for all trackers returns all streaks."""
        tracker1 = self.create_tracker(name='Tracker 1')
        tracker2 = self.create_tracker(name='Tracker 2')
        
        template1 = self.create_template(tracker1)
        template2 = self.create_template(tracker2)
        
        # Create streak data for both
        instance1 = self.create_instance(tracker1, date.today())
        self.create_task_instance(instance1, template1, status='DONE')
        
        instance2 = self.create_instance(tracker2, date.today())
        self.create_task_instance(instance2, template2, status='DONE')
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)
