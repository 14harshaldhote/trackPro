
import pytest
from django.utils import timezone
from core.tests.base import BaseAPITestCase
from core.models import TrackerDefinition, TaskInstance

@pytest.mark.compliance
@pytest.mark.retention
class DataRetentionTests(BaseAPITestCase):
    """
    Tests for Data Retention and cleanup policies.
    """

    def test_soft_deleted_items_filtering(self):
        """Verify soft deleted items are not returned in standard queries."""
        tracker = self.create_tracker(name="To Delete")
        tracker_id = tracker.tracker_id
        
        # Soft delete
        tracker.soft_delete()
        
        # Verify it's still in DB
        self.assertTrue(TrackerDefinition.objects.filter(tracker_id=tracker_id).exists())
        self.assertIsNotNone(TrackerDefinition.objects.get(tracker_id=tracker_id).deleted_at)
        
        # Verify API doesn't return it
        response = self.client.get('/api/v1/trackers/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        ids = [t['id'] for t in data['trackers']] # Adjust structure if needed
        self.assertNotIn(str(tracker_id), ids)

    def test_related_data_retention(self):
        """Verify tasks associated with deleted trackers are retained (soft deleted) but hidden."""
        tracker = self.create_tracker()
        instance = self.create_instance(tracker)
        task = self.create_task(instance)
        
        # Soft delete tracker
        tracker.soft_delete()
        
        # Task should still exist for history/restore purposes
        self.assertTrue(TaskInstance.objects.filter(task_instance_id=task.task_instance_id).exists())
        
        # But shouldn't appear in lists
        response = self.client.get(f'/api/v1/tracker/{tracker.tracker_id}/')
        self.assertIn(response.status_code, [404, 403])

    def test_restore_functionality(self):
        """Verify data can be restored (retention allows recovery)."""
        tracker = self.create_tracker()
        tracker.soft_delete()
        
        # Restore
        tracker.restore()
        self.assertIsNone(tracker.deleted_at)
        
        # Verify API visibility
        response = self.client.get(f'/api/v1/tracker/{tracker.tracker_id}/')
        self.assertEqual(response.status_code, 200)

    def test_retention_policy_enforcement(self):
        """
        Verify that strictly deleted data (hard delete) is actually gone.
        This might be triggered by a specific cleanup job or 'permanent delete' action.
        """
        # Assuming we have a way to hard delete or a cleanup process
        # If not, this test checks manual hard delete behavior for compliance
        tracker = self.create_tracker(name="Hard Delete")
        tracker.delete() # Hard delete if model allows, or custom hard delete method
        
        # User.delete() usually cascades, but manual model delete might soft delete if overridden
        # Checking default behavior:
        if hasattr(tracker, 'soft_delete'):
            # If standard delete() is NOT overridden to soft delete, it should be gone.
            # If standard delete() IS overridden, we need to check how to force hard delete
            # Standard django delete() on a SoftDeleteModel typically just performs DB delete unless manager overrides it
            # But the model in core/models.py doesn't seem to override delete() method, just adds soft_delete()
            pass
        
        self.assertFalse(TrackerDefinition.objects.filter(tracker_id=tracker.tracker_id).exists())
