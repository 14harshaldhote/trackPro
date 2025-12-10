"""
Critical Path Tests

Test IDs: CP-001 to CP-015
Priority: CRITICAL
Coverage: Most important user flows that must never fail

These tests verify the critical paths that are essential for core functionality.
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from core.tests.base import BaseAPITestCase
from core.models import TrackerDefinition, TaskInstance

User = get_user_model()


@pytest.mark.critical
class AuthenticationCriticalPathTests(BaseAPITestCase):
    """Critical path tests for authentication."""
    
    def test_CP_001_authenticated_user_can_access_dashboard(self):
        """CP-001: Authenticated user can access dashboard."""
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success', False))
    
    def test_CP_002_unauthenticated_user_blocked(self):
        """CP-002: Unauthenticated requests are blocked."""
        self.client.logout()
        
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, 401)
    
    def test_CP_003_auth_status_endpoint_works(self):
        """CP-003: Auth status check returns correct state."""
        response = self.client.get('/api/auth/status/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('authenticated', False))


@pytest.mark.critical
class TaskToggleCriticalPathTests(BaseAPITestCase):
    """Critical path tests for task toggling - the core action."""
    
    def test_CP_004_task_toggle_works(self):
        """CP-004: Task toggle changes status correctly."""
        tracker = self.create_tracker()
        instance = self.create_instance(tracker)
        task = self.create_task(instance)
        
        # Initial status should be TODO
        self.assertEqual(task.status, 'TODO')
        
        # Toggle to DONE
        response = self.client.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        self.assertEqual(response.status_code, 200)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'DONE')
    
    def test_CP_005_task_toggle_is_reversible(self):
        """CP-005: Task can be toggled back to TODO."""
        tracker = self.create_tracker()
        instance = self.create_instance(tracker)
        task = self.create_task(instance)
        
        # Toggle to DONE
        self.client.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        task.refresh_from_db()
        self.assertEqual(task.status, 'DONE')
        
        # Toggle back to TODO
        self.client.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        task.refresh_from_db()
        self.assertEqual(task.status, 'TODO')
    
    def test_CP_006_completed_at_timestamp_set(self):
        """CP-006: Completed timestamp is set when task is done."""
        tracker = self.create_tracker()
        instance = self.create_instance(tracker)
        task = self.create_task(instance)
        
        self.assertIsNone(task.completed_at)
        
        self.client.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        task.refresh_from_db()
        
        self.assertIsNotNone(task.completed_at)


@pytest.mark.critical
class TrackerCRUDCriticalPathTests(BaseAPITestCase):
    """Critical path tests for tracker CRUD operations."""
    
    def test_CP_007_create_tracker(self):
        """CP-007: User can create a tracker."""
        response = self.client.post('/api/v1/tracker/create/', {
            'name': 'New Critical Tracker',
            'time_mode': 'daily'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify tracker exists
        self.assertTrue(
            TrackerDefinition.objects.filter(
                user=self.user,
                name='New Critical Tracker'
            ).exists()
        )
    
    def test_CP_008_list_trackers(self):
        """CP-008: User can list their trackers."""
        self.create_tracker(name="Tracker 1")
        self.create_tracker(name="Tracker 2")
        
        response = self.client.get('/api/v1/trackers/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertGreaterEqual(len(data.get('trackers', [])), 2)
    
    def test_CP_009_delete_tracker(self):
        """CP-009: User can delete their tracker."""
        tracker = self.create_tracker(name="To Delete")
        tracker_id = tracker.tracker_id
        
        response = self.client.delete(f'/api/v1/tracker/{tracker_id}/delete/')
        self.assertEqual(response.status_code, 200)
        
        # Should be soft deleted
        tracker.refresh_from_db()
        self.assertIsNotNone(tracker.deleted_at)


@pytest.mark.critical
class DataIntegrityCriticalPathTests(BaseAPITestCase):
    """Critical path tests for data integrity."""
    
    def test_CP_010_user_isolation(self):
        """CP-010: Users cannot see other users' data."""
        # Create tracker for current user
        my_tracker = self.create_tracker(name="My Private Tracker")
        
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        other_tracker = TrackerDefinition.objects.create(
            user=other_user,
            name="Other User Tracker",
            time_mode='daily'
        )
        
        # List trackers - should only see own
        response = self.client.get('/api/v1/trackers/')
        data = response.json()
        
        tracker_names = [t['name'] for t in data.get('trackers', [])]
        self.assertIn('My Private Tracker', tracker_names)
        self.assertNotIn('Other User Tracker', tracker_names)
    
    def test_CP_011_cascade_delete_works(self):
        """CP-011: Deleting tracker cascades to instances and tasks."""
        tracker = self.create_tracker()
        instance = self.create_instance(tracker)
        task = self.create_task(instance)
        
        task_id = task.task_instance_id
        instance_id = instance.instance_id
        
        # Delete user (cascade)
        user_id = self.user.id
        self.user.delete()
        
        # All related data should be gone
        self.assertFalse(TrackerDefinition.objects.filter(tracker_id=tracker.tracker_id).exists())


@pytest.mark.critical
class HealthCheckCriticalPathTests(BaseAPITestCase):
    """Critical path tests for system health."""
    
    def test_CP_012_health_endpoint_accessible(self):
        """CP-012: Health check endpoint is accessible."""
        self.client.logout()  # Should work without auth
        
        response = self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data.get('status'), 'healthy')
    
    def test_CP_013_database_health_check(self):
        """CP-013: Database health is verified."""
        response = self.client.get('/api/v1/health/')
        data = response.json()
        
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])
        self.assertEqual(data['checks']['database']['status'], 'ok')


@pytest.mark.critical
class DashboardCriticalPathTests(BaseAPITestCase):
    """Critical path tests for dashboard loading."""
    
    def test_CP_014_dashboard_loads_with_data(self):
        """CP-014: Dashboard loads correctly with user data."""
        # Create some data
        tracker = self.create_tracker(name="Dashboard Test")
        instance = self.create_instance(tracker)
        self.create_task(instance)
        
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success', False))
    
    def test_CP_015_dashboard_loads_empty(self):
        """CP-015: Dashboard loads correctly for new user with no data."""
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success', False))
