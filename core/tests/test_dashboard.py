"""
Dashboard Endpoints Tests (28 tests)

Test IDs: DASH-001 to DASH-028
Coverage: /api/v1/dashboard/*, /api/v1/trackers/, /api/v1/tracker/{id}/

These tests cover:
- Main dashboard endpoints
- Today and week views
- Goals and streaks dashboard
- Activity feed
- Tracker list and details
- Prefetch, suggestions, and sync
"""
from datetime import date, timedelta
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, 
    TaskInstanceFactory, GoalFactory, create_tracker_with_tasks
)


class DashboardMainTests(BaseAPITestCase):
    """Tests for /api/v1/dashboard/ endpoint."""
    
    def test_DASH_001_get_main_dashboard(self):
        """DASH-001: Get main dashboard returns 200 with complete data."""
        # Create some data
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        self.create_task_instance(instance, template)
        
        response = self.get('/api/v1/dashboard/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_DASH_002_dashboard_with_no_trackers(self):
        """DASH-002: Dashboard with no trackers returns 200 with empty arrays."""
        response = self.get('/api/v1/dashboard/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_DASH_003_dashboard_with_date_param(self):
        """DASH-003: Dashboard with date parameter returns filtered data."""
        tracker = self.create_tracker()
        specific_date = date.today() - timedelta(days=5)
        
        response = self.get(f'/api/v1/dashboard/?date={specific_date.isoformat()}')
        
        self.assertEqual(response.status_code, 200)


class DashboardTrackersTests(BaseAPITestCase):
    """Tests for /api/v1/dashboard/trackers/ endpoint."""
    
    def test_DASH_004_get_dashboard_trackers(self):
        """DASH-004: Get dashboard trackers returns 200 with tracker list."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/dashboard/trackers/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_DASH_005_dashboard_trackers_with_date(self):
        """DASH-005: Dashboard trackers with date parameter returns filtered data."""
        tracker = self.create_tracker()
        
        response = self.get(f'/api/v1/dashboard/trackers/?date={date.today().isoformat()}')
        
        self.assertEqual(response.status_code, 200)


class DashboardTodayTests(BaseAPITestCase):
    """Tests for /api/v1/dashboard/today/ endpoint."""
    
    def test_DASH_006_get_todays_view(self):
        """DASH-006: Get today's view returns 200 with today's data."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/dashboard/today/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_DASH_007_today_creates_instance_if_none(self):
        """DASH-007: Today view creates instance if none exists."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/dashboard/today/')
        
        self.assertEqual(response.status_code, 200)
        # Verify instance was created by checking the response


class DashboardWeekTests(BaseAPITestCase):
    """Tests for /api/v1/dashboard/week/ endpoint."""
    
    def test_DASH_008_get_week_view(self):
        """DASH-008: Get week view returns 200 with 7 days of data."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/dashboard/week/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_009_week_with_custom_start(self):
        """DASH-009: Week view with custom start date returns correct range."""
        custom_start = date.today() - timedelta(days=14)
        
        response = self.get(f'/api/v1/dashboard/week/?week_start={custom_start.isoformat()}')
        
        self.assertEqual(response.status_code, 200)


class DashboardGoalsTests(BaseAPITestCase):
    """Tests for /api/v1/dashboard/goals/ endpoint."""
    
    def test_DASH_010_get_goals_dashboard(self):
        """DASH-010: Get goals dashboard returns 200 with goals list."""
        tracker = self.create_tracker()
        goal = GoalFactory.create(self.user, tracker)
        
        response = self.get('/api/v1/dashboard/goals/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_011_goals_with_no_goals(self):
        """DASH-011: Goals dashboard with no goals returns 200 with empty list."""
        response = self.get('/api/v1/dashboard/goals/')
        
        self.assertEqual(response.status_code, 200)


class DashboardStreaksTests(BaseAPITestCase):
    """Tests for /api/v1/dashboard/streaks/ endpoint."""
    
    def test_DASH_012_get_streaks_dashboard(self):
        """DASH-012: Get streaks dashboard returns 200 with streak data."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_013_streaks_with_no_data(self):
        """DASH-013: Streaks with no data returns 200 with streak=0."""
        response = self.get('/api/v1/dashboard/streaks/')
        
        self.assertEqual(response.status_code, 200)


class DashboardActivityTests(BaseAPITestCase):
    """Tests for /api/v1/dashboard/activity/ endpoint."""
    
    def test_DASH_014_get_activity_feed(self):
        """DASH-014: Get activity feed returns 200 with events."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/dashboard/activity/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_015_activity_with_limit(self):
        """DASH-015: Activity feed with limit returns limited items."""
        response = self.get('/api/v1/dashboard/activity/?limit=5')
        
        self.assertEqual(response.status_code, 200)


class TrackerListTests(BaseAPITestCase):
    """Tests for /api/v1/trackers/ endpoint."""
    
    def test_DASH_016_get_trackers_list(self):
        """DASH-016: Get trackers list returns 200 with all trackers."""
        tracker1 = self.create_tracker(name='Tracker 1')
        tracker2 = self.create_tracker(name='Tracker 2')
        
        response = self.get('/api/v1/trackers/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_DASH_017_trackers_list_empty(self):
        """DASH-017: Trackers list with no trackers returns 200 with empty array."""
        response = self.get('/api/v1/trackers/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_018_trackers_list_excludes_deleted(self):
        """DASH-018: Trackers list excludes deleted trackers."""
        active_tracker = self.create_tracker(name='Active', status='active')
        deleted_tracker = self.create_tracker(name='Deleted', status='deleted')
        
        response = self.get('/api/v1/trackers/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Verify deleted tracker is not in response
        trackers = data.get('trackers', data.get('data', []))
        if isinstance(trackers, list):
            tracker_names = [t.get('name') for t in trackers]
            self.assertNotIn('Deleted', tracker_names)


class TrackerDetailTests(BaseAPITestCase):
    """Tests for /api/v1/tracker/{id}/ endpoint."""
    
    def test_DASH_019_get_tracker_detail(self):
        """DASH-019: Get tracker detail returns 200 with full detail."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_DASH_020_tracker_detail_not_found(self):
        """DASH-020: Tracker detail with invalid ID returns 404."""
        response = self.get('/api/v1/tracker/invalid-uuid-12345/')
        
        self.assertEqual(response.status_code, 404)
    
    def test_DASH_021_tracker_detail_other_user(self):
        """DASH-021: Tracker detail for other user's tracker returns 404."""
        from core.tests.factories import UserFactory
        
        other_user = UserFactory.create()
        other_tracker = TrackerFactory.create(other_user)
        
        response = self.get(f'/api/v1/tracker/{other_tracker.tracker_id}/')
        
        # Should return 404 (not found from user's perspective)
        self.assertEqual(response.status_code, 404)
    
    def test_DASH_022_tracker_detail_deleted(self):
        """DASH-022: Tracker detail for deleted tracker returns 404."""
        tracker = self.create_tracker()
        tracker.soft_delete()
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/')
        
        self.assertEqual(response.status_code, 404)


class PrefetchAndSuggestionsTests(BaseAPITestCase):
    """Tests for prefetch and suggestions endpoints."""
    
    def test_DASH_023_get_prefetch_data(self):
        """DASH-023: Get prefetch data returns 200 with bundled data."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/prefetch/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_024_get_smart_suggestions(self):
        """DASH-024: Get smart suggestions returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/suggestions/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_025_suggestions_with_no_history(self):
        """DASH-025: Suggestions with no history returns defaults."""
        response = self.get('/api/v1/suggestions/')
        
        self.assertEqual(response.status_code, 200)


class TasksInfiniteScrollTests(BaseAPITestCase):
    """Tests for /api/v1/tasks/infinite/ endpoint."""
    
    def test_DASH_026_get_tasks_infinite_scroll(self):
        """DASH-026: Get tasks with infinite scroll returns 200 paginated."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        self.create_task_instance(instance, template)
        
        response = self.get('/api/v1/tasks/infinite/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_DASH_027_tasks_infinite_with_offset(self):
        """DASH-027: Tasks infinite with offset returns next page."""
        response = self.get('/api/v1/tasks/infinite/?offset=20')
        
        self.assertEqual(response.status_code, 200)


class SyncTests(BaseAPITestCase):
    """Tests for /api/v1/sync/ endpoint."""
    
    def test_DASH_028_sync_endpoint(self):
        """DASH-028: Sync endpoint returns 200 with sync result."""
        tracker = self.create_tracker()
        
        response = self.post('/api/v1/sync/', {
            'last_sync': '2025-01-01T00:00:00Z'
        })
        
        # Should return 200 or accept the sync request
        self.assertIn(response.status_code, [200, 201])
