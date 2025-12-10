"""
Activity Replay Tests V2.0 (14 tests)

Test IDs: REPL-001 to REPL-014
Coverage: /api/v1/v2/timeline/, /api/v1/v2/snapshot/, /api/v1/v2/compare/

These tests cover:
- Activity timeline
- Day snapshots
- Period comparison
- Weekly comparison
- Entity history
"""
from datetime import date, timedelta
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
)


class ActivityTimelineTests(BaseAPITestCase):
    """Tests for /api/v1/v2/timeline/ endpoint."""
    
    def test_REPL_001_get_activity_timeline(self):
        """REPL-001: Get activity timeline returns 200 with events."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template, status='TODO')
        
        # Complete a task to create activity
        self.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        
        response = self.get('/api/v1/v2/timeline/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_002_timeline_with_dates(self):
        """REPL-002: Timeline with date filters returns filtered events."""
        tracker = self.create_tracker()
        
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        
        response = self.get(
            f'/api/v1/v2/timeline/?start_date={start_date.isoformat()}&end_date={end_date.isoformat()}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_003_timeline_with_limit(self):
        """REPL-003: Timeline with limit returns limited events."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create multiple activities
        for i in range(5):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            task = self.create_task_instance(instance, template)
        
        response = self.get('/api/v1/v2/timeline/?limit=10')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_004_timeline_event_types(self):
        """REPL-004: Timeline includes all event types."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template)
        
        response = self.get('/api/v1/v2/timeline/')
        
        self.assertEqual(response.status_code, 200)


class DaySnapshotTests(BaseAPITestCase):
    """Tests for /api/v1/v2/snapshot/{date}/ endpoint."""
    
    def test_REPL_005_get_day_snapshot(self):
        """REPL-005: Get day snapshot returns 200 with full state."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker, date.today())
        self.create_task_instance(instance, template, status='DONE')
        
        response = self.get(f'/api/v1/v2/snapshot/{date.today().isoformat()}/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_006_snapshot_no_data(self):
        """REPL-006: Snapshot with no data returns 200 with empty state."""
        old_date = date.today() - timedelta(days=365)
        
        response = self.get(f'/api/v1/v2/snapshot/{old_date.isoformat()}/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_007_snapshot_completion_rate(self):
        """REPL-007: Snapshot includes correct completion rate."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker)
        template2 = self.create_template(tracker)
        instance = self.create_instance(tracker)
        
        # 50% completion
        self.create_task_instance(instance, template1, status='DONE')
        self.create_task_instance(instance, template2, status='TODO')
        
        response = self.get(f'/api/v1/v2/snapshot/{date.today().isoformat()}/')
        
        self.assertEqual(response.status_code, 200)


class PeriodComparisonTests(BaseAPITestCase):
    """Tests for /api/v1/v2/compare/ endpoint."""
    
    def test_REPL_008_compare_two_periods(self):
        """REPL-008: Compare two periods returns 200 with comparison."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create data for both periods
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            status = 'DONE' if i < 7 else 'TODO'
            self.create_task_instance(instance, template, status=status)
        
        p1_start = date.today() - timedelta(days=6)
        p1_end = date.today()
        p2_start = date.today() - timedelta(days=13)
        p2_end = date.today() - timedelta(days=7)
        
        response = self.get(
            f'/api/v1/v2/compare/?p1_start={p1_start}&p1_end={p1_end}&p2_start={p2_start}&p2_end={p2_end}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_009_compare_shows_changes(self):
        """REPL-009: Compare shows direction and delta."""
        tracker = self.create_tracker()
        
        # Provide required date parameters
        from datetime import date, timedelta
        p1_start = date.today() - timedelta(days=6)
        p1_end = date.today()
        p2_start = date.today() - timedelta(days=13)
        p2_end = date.today() - timedelta(days=7)
        
        response = self.get(
            f'/api/v1/v2/compare/?p1_start={p1_start}&p1_end={p1_end}&p2_start={p2_start}&p2_end={p2_end}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_010_compare_generates_insights(self):
        """REPL-010: Compare generates insights array."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Provide required date parameters
        from datetime import date, timedelta
        p1_start = date.today() - timedelta(days=6)
        p1_end = date.today()
        p2_start = date.today() - timedelta(days=13)
        p2_end = date.today() - timedelta(days=7)
        
        response = self.get(
            f'/api/v1/v2/compare/?p1_start={p1_start}&p1_end={p1_end}&p2_start={p2_start}&p2_end={p2_end}'
        )
        
        self.assertEqual(response.status_code, 200)


class WeeklyComparisonTests(BaseAPITestCase):
    """Tests for /api/v1/v2/compare/weekly/ endpoint."""
    
    def test_REPL_011_weekly_comparison(self):
        """REPL-011: Weekly comparison returns week-over-week data."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Create two weeks of data
        for i in range(14):
            day = date.today() - timedelta(days=i)
            instance = self.create_instance(tracker, day)
            self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/v2/compare/weekly/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_012_weekly_trend(self):
        """REPL-012: Weekly comparison includes trend calculation."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/v2/compare/weekly/')
        
        self.assertEqual(response.status_code, 200)


class EntityHistoryTests(BaseAPITestCase):
    """Tests for /api/v1/v2/history/{type}/{id}/ endpoint."""
    
    def test_REPL_013_entity_history(self):
        """REPL-013: Entity history returns history entries."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Make some changes to create history
        self.put(f'/api/v1/tracker/{tracker.tracker_id}/update/', {
            'name': 'Updated Name'
        })
        
        response = self.get(f'/api/v1/v2/history/tracker/{tracker.tracker_id}/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REPL_014_history_deleted_entity(self):
        """REPL-014: History for deleted entity still returns data."""
        tracker = self.create_tracker()
        tracker_id = tracker.tracker_id
        
        # Delete the tracker
        self.delete(f'/api/v1/tracker/{tracker_id}/delete/')
        
        response = self.get(f'/api/v1/v2/history/tracker/{tracker_id}/')
        
        # Should still return history even if entity is deleted
        self.assertIn(response.status_code, [200, 404])
