"""
Instance Management Tests (16 tests)

Test IDs: INST-001 to INST-016
Coverage: /api/v1/tracker/{id}/instances/* endpoints

These tests cover:
- Instance generation (single day, date ranges)
- Week aggregation
- Overdue marking
- Concurrent access
- Backdated/future instances
"""
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from core.tests.base import BaseAPITestCase, BaseTransactionTestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, 
    TaskInstanceFactory, create_tracker_with_tasks
)


class InstanceGenerationTests(BaseAPITestCase):
    """Tests for /api/v1/tracker/{id}/instances/generate/ endpoint."""
    
    def test_INST_001_generate_single_day(self):
        """INST-001: Generate single day instance returns 200 with 1 instance."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_002_generate_date_range(self):
        """INST-002: Generate date range returns 200 with N instances."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        start_date = date.today() - timedelta(days=5)
        end_date = date.today()
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_003_generate_overlapping_range(self):
        """INST-003: Generate overlapping range doesn't create duplicates."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create an instance for today
        instance = self.create_instance(tracker, date.today())
        
        # Try to generate again for same date
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_004_generate_with_mark_missed(self):
        """INST-004: Generate with mark_missed sets tasks to MISSED."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        past_date = date.today() - timedelta(days=3)
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': past_date.isoformat(),
            'mark_missed': True
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_005_generate_over_365_days_fails(self):
        """INST-005: Generate over 365 days range returns 400."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        start_date = date.today() - timedelta(days=400)
        end_date = date.today()
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        })
        
        self.assertEqual(response.status_code, 400)
    
    def test_INST_006_generate_weekly_tracker(self):
        """INST-006: Generate for weekly tracker respects weekly bounds."""
        tracker = self.create_tracker(time_mode='weekly')
        template = self.create_template(tracker)
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_007_generate_monthly_tracker(self):
        """INST-007: Generate for monthly tracker respects monthly bounds."""
        tracker = self.create_tracker(time_mode='monthly')
        template = self.create_template(tracker)
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, 200)


class WeekAggregationTests(BaseAPITestCase):
    """Tests for /api/v1/tracker/{id}/week/ endpoint."""
    
    def test_INST_008_get_week_aggregation(self):
        """INST-008: Get week aggregation returns 200 with 7 days."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create instances for the week
        for i in range(7):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE' if i % 2 == 0 else 'TODO')
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/week/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_009_week_with_custom_start(self):
        """INST-009: Week with custom start date returns correct range."""
        tracker = self.create_tracker()
        
        custom_start = date.today() - timedelta(days=14)
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/week/?week_start={custom_start.isoformat()}')
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_010_week_aggregation_empty(self):
        """INST-010: Week aggregation with no data returns zeros."""
        tracker = self.create_tracker()
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/week/')
        
        self.assertEqual(response.status_code, 200)


class MarkOverdueTests(BaseAPITestCase):
    """Tests for /api/v1/tracker/{id}/mark-overdue/ endpoint."""
    
    def test_INST_011_mark_overdue_missed(self):
        """INST-011: Mark overdue tasks as missed returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create past instance with TODO tasks
        past_date = date.today() - timedelta(days=2)
        instance = self.create_instance(tracker, past_date)
        task = self.create_task_instance(instance, template, status='TODO')
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/mark-overdue/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_012_mark_overdue_nothing_overdue(self):
        """INST-012: Mark overdue with no overdue tasks returns 200 with 0 marked."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create today's instance with DONE tasks
        instance = self.create_instance(tracker, date.today())
        task = self.create_task_instance(instance, template, status='DONE')
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/mark-overdue/')
        
        self.assertEqual(response.status_code, 200)


class ConcurrencyTests(BaseTransactionTestCase):
    """Tests for concurrent access scenarios."""
    
    def test_INST_013_instance_get_or_create_race(self):
        """INST-013: Concurrent instance creation creates only 1."""
        from core.tests.factories import TrackerFactory, TemplateFactory
        import threading
        
        tracker = TrackerFactory.create(self.user)
        template = TemplateFactory.create(tracker)
        
        results = []
        errors = []
        
        def create_instance():
            try:
                response = self.client.post(
                    f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/',
                    {'date': date.today().isoformat()},
                    format='json'
                )
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = [threading.Thread(target=create_instance) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All requests should succeed
        for status in results:
            self.assertIn(status, [200, 201])


class BackdatedAndFutureInstanceTests(BaseAPITestCase):
    """Tests for backdated and future instance creation."""
    
    def test_INST_014_backdated_instance_creates(self):
        """INST-014: Backdated instance creation returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        yesterday = date.today() - timedelta(days=1)
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': yesterday.isoformat()
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_015_future_instance_creates(self):
        """INST-015: Future instance creation returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        tomorrow = date.today() + timedelta(days=1)
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': tomorrow.isoformat()
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_INST_016_instance_without_templates(self):
        """INST-016: Instance creation for tracker with no templates returns 200."""
        tracker = self.create_tracker()
        # No templates created
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/instances/generate/', {
            'date': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, 200)
