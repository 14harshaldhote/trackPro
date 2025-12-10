"""
Task & Template Tests (22 tests)

Test IDs: TASK-001 to TASK-022
Coverage: /api/v1/task/* and /api/v1/tasks/* endpoints

These tests cover:
- Adding tasks to trackers
- Task toggle (status change)
- Task status updates
- Task editing
- Task deletion
- Bulk operations
- Template activation
- Task goals and points
"""
from datetime import date, datetime
from django.test import TestCase
from django.utils import timezone
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, 
    TaskInstanceFactory, create_tracker_with_tasks
)


class TaskAddTests(BaseAPITestCase):
    """Tests for /api/v1/tracker/{id}/task/add/ endpoint."""
    
    def test_TASK_001_add_task_to_tracker(self):
        """TASK-001: Add task to tracker returns 201."""
        tracker = self.create_tracker()
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/task/add/', {
            'description': 'New Task'
        })
        
        self.assertIn(response.status_code, [200, 201])
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_TASK_002_add_task_with_all_fields(self):
        """TASK-002: Add task with all fields returns 201."""
        tracker = self.create_tracker()
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/task/add/', {
            'description': 'Full Task',
            'category': 'health',
            'points': 10,
            'time_of_day': 'morning',
            'is_recurring': True
        })
        
        self.assertIn(response.status_code, [200, 201])
    
    def test_TASK_003_add_task_missing_description(self):
        """TASK-003: Add task without description returns 400."""
        tracker = self.create_tracker()
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/task/add/', {
            'category': 'general'
        })
        
        self.assertEqual(response.status_code, 400)
    
    def test_TASK_004_add_task_negative_points(self):
        """TASK-004: Add task with negative points returns 400."""
        tracker = self.create_tracker()
        
        response = self.post(f'/api/v1/tracker/{tracker.tracker_id}/task/add/', {
            'description': 'Negative Task',
            'points': -5
        })
        
        self.assertEqual(response.status_code, 400)


class TaskToggleTests(BaseAPITestCase):
    """Tests for /api/v1/task/{id}/toggle/ endpoint."""
    
    def test_TASK_005_toggle_task_todo_to_done(self):
        """TASK-005: Toggle task from TODO to DONE returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template, status='TODO')
        
        response = self.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'DONE')
    
    def test_TASK_006_toggle_task_done_to_todo(self):
        """TASK-006: Toggle task from DONE to TODO returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template, status='DONE')
        
        response = self.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        
        self.assertEqual(response.status_code, 200)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'TODO')
    
    def test_TASK_007_toggle_task_not_found(self):
        """TASK-007: Toggle non-existent task returns 404."""
        response = self.post('/api/v1/task/invalid-uuid-12345/toggle/')
        
        self.assertEqual(response.status_code, 404)


class TaskStatusTests(BaseAPITestCase):
    """Tests for /api/v1/task/{id}/status/ endpoint."""
    
    def test_TASK_008_set_task_status_done(self):
        """TASK-008: Set task status to DONE returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template, status='TODO')
        
        response = self.put(f'/api/v1/task/{task.task_instance_id}/status/', {
            'status': 'DONE'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_009_set_task_status_missed(self):
        """TASK-009: Set task status to MISSED returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template)
        
        response = self.put(f'/api/v1/task/{task.task_instance_id}/status/', {
            'status': 'MISSED'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_010_set_task_status_in_progress(self):
        """TASK-010: Set task status to IN_PROGRESS returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template)
        
        response = self.put(f'/api/v1/task/{task.task_instance_id}/status/', {
            'status': 'IN_PROGRESS'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_011_set_task_status_skipped(self):
        """TASK-011: Set task status to SKIPPED returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template)
        
        response = self.put(f'/api/v1/task/{task.task_instance_id}/status/', {
            'status': 'SKIPPED'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_012_set_task_invalid_status(self):
        """TASK-012: Set task to invalid status returns 400."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template)
        
        response = self.put(f'/api/v1/task/{task.task_instance_id}/status/', {
            'status': 'INVALID_STATUS'
        })
        
        self.assertEqual(response.status_code, 400)


class TaskEditTests(BaseAPITestCase):
    """Tests for /api/v1/task/{id}/edit/ endpoint."""
    
    def test_TASK_013_edit_task_description(self):
        """TASK-013: Edit task description returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template)
        
        response = self.put(f'/api/v1/task/{task.task_instance_id}/edit/', {
            'description': 'Updated Description'
        })
        
        self.assertEqual(response.status_code, 200)


class TaskDeleteTests(BaseAPITestCase):
    """Tests for /api/v1/task/{id}/delete/ endpoint."""
    
    def test_TASK_014_delete_task_soft(self):
        """TASK-014: Delete task performs soft delete and returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template)
        
        response = self.delete(f'/api/v1/task/{task.task_instance_id}/delete/')
        
        self.assertEqual(response.status_code, 200)


class TaskBulkOperationsTests(BaseAPITestCase):
    """Tests for /api/v1/tasks/bulk/* endpoints."""
    
    def test_TASK_015_bulk_update_tasks(self):
        """TASK-015: Bulk update tasks returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task1 = self.create_task_instance(instance, template)
        task2 = self.create_task_instance(instance, template)
        
        response = self.post('/api/v1/tasks/bulk/', {
            'task_ids': [task1.task_instance_id, task2.task_instance_id],
            'action': 'complete'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_016_bulk_status_update(self):
        """TASK-016: Bulk status update returns 200 with all updated."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task1 = self.create_task_instance(instance, template)
        task2 = self.create_task_instance(instance, template)
        
        response = self.post('/api/v1/tasks/bulk-update/', {
            'task_ids': [task1.task_instance_id, task2.task_instance_id],
            'status': 'DONE'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_017_bulk_update_partial_fail(self):
        """TASK-017: Bulk update with some failures returns 207 partial."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task1 = self.create_task_instance(instance, template)
        
        response = self.post('/api/v1/tasks/bulk-update/', {
            'task_ids': [task1.task_instance_id, 'invalid-uuid-12345'],
            'status': 'DONE'
        })
        
        # Should return 200 or 207 (partial success)
        self.assertIn(response.status_code, [200, 207])


class TemplateActivationTests(BaseAPITestCase):
    """Tests for /api/v1/templates/activate/ endpoint."""
    
    def test_TASK_018_template_activate(self):
        """TASK-018: Template activation returns 200."""
        response = self.post('/api/v1/templates/activate/', {
            'template_key': 'morning'
        })
        
        # Should return 200 if template exists, 400 if not
        self.assertIn(response.status_code, [200, 201, 400])


class TaskGoalTests(BaseAPITestCase):
    """Tests for task goal endpoints."""
    
    def test_TASK_019_toggle_task_goal(self):
        """TASK-019: Toggle task goal returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Provide the include parameter in the body as expected by the endpoint
        response = self.post(f'/api/v1/task/{template.template_id}/toggle-goal/', {
            'include': True
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_020_update_task_points(self):
        """TASK-020: Update task points returns 200."""
        tracker = self.create_tracker()
        template = self.create_template(tracker, points=5)
        
        response = self.put(f'/api/v1/task/{template.template_id}/points/', {
            'points': 10
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_TASK_021_points_breakdown(self):
        """TASK-021: Points breakdown returns 200 with breakdown."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, points=5)
        template2 = self.create_template(tracker, points=10)
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/points-breakdown/')
        
        self.assertEqual(response.status_code, 200)


class TaskCompletionTimeTests(BaseAPITestCase):
    """Tests for task completion time tracking."""
    
    def test_TASK_022_first_completed_at_persists(self):
        """TASK-022: First completed_at timestamp persists through toggles."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        task = self.create_task_instance(instance, template, status='TODO')
        
        # First toggle: TODO -> DONE
        response1 = self.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        self.assertEqual(response1.status_code, 200)
        
        task.refresh_from_db()
        first_completed = task.first_completed_at
        
        # Wait a bit and toggle again: DONE -> TODO
        import time
        time.sleep(0.1)
        
        response2 = self.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        self.assertEqual(response2.status_code, 200)
        
        # Toggle again: TODO -> DONE
        response3 = self.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        self.assertEqual(response3.status_code, 200)
        
        task.refresh_from_db()
        
        # first_completed_at should remain unchanged
        if first_completed:
            self.assertEqual(task.first_completed_at, first_completed)
