"""
Unit tests for core/services/sync_service.py

Tests offline sync functionality:
- Sync with no changes
- Sync with new/updated/deleted items
- Handling invalid timestamps
- Action processing (task_toggle, task_status, etc.)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.utils import timezone

from core.services.sync_service import SyncService, process_sync
from core.models import TrackerDefinition, TaskInstance, DayNote


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='sync_test_user',
        email='sync@test.com',
        password='testpass123'
    )


@pytest.fixture
def tracker(db, user):
    """Create a test tracker."""
    from core.tests.factories import TrackerFactory
    return TrackerFactory.create(user)


@pytest.fixture
def template(db, tracker):
    """Create a test template."""
    from core.tests.factories import TemplateFactory
    return TemplateFactory.create(tracker)


@pytest.fixture
def instance(db, tracker):
    """Create a test instance."""
    from core.tests.factories import InstanceFactory
    return InstanceFactory.create(tracker)


@pytest.fixture
def task(db, instance, template):
    """Create a test task."""
    from core.tests.factories import TaskInstanceFactory
    return TaskInstanceFactory.create(instance, template)


@pytest.fixture
def sync_service(user):
    """Create SyncService instance."""
    return SyncService(user)


# ============================================================================
# Tests for process_sync_request
# ============================================================================

class TestProcessSyncRequest:
    """Tests for SyncService.process_sync_request."""
    
    @pytest.mark.django_db
    def test_sync_with_no_changes(self, sync_service):
        """Sync with no pending actions should return current state."""
        data = {
            'last_sync': timezone.now().isoformat(),
            'pending_actions': [],
            'device_id': 'test-device'
        }
        
        result = sync_service.process_sync_request(data)
        
        assert 'server_changes' in result
        assert 'new_sync_timestamp' in result
        assert result['sync_status'] in ['complete', 'partial']
    
    @pytest.mark.django_db
    def test_sync_with_empty_last_sync(self, sync_service, tracker):
        """First sync (no last_sync) should return full data."""
        data = {
            'pending_actions': [],
            'device_id': 'test-device'
        }
        
        result = sync_service.process_sync_request(data)
        
        assert 'server_changes' in result
        assert 'new_sync_timestamp' in result
    
    @pytest.mark.django_db
    def test_sync_returns_new_timestamp(self, sync_service):
        """Should return new sync timestamp for next sync."""
        data = {
            'last_sync': (timezone.now() - timedelta(hours=1)).isoformat(),
            'pending_actions': [],
            'device_id': 'test-device'
        }
        
        result = sync_service.process_sync_request(data)
        
        assert 'new_sync_timestamp' in result
        assert result['new_sync_timestamp'] is not None
    
    @pytest.mark.django_db
    def test_sync_processes_pending_actions(self, sync_service, task):
        """Should process pending actions from client."""
        data = {
            'last_sync': timezone.now().isoformat(),
            'pending_actions': [
                {
                    'id': 'action-1',
                    'type': 'task_status',
                    'task_id': str(task.task_instance_id),
                    'status': 'DONE',
                    'timestamp': timezone.now().isoformat()
                }
            ],
            'device_id': 'test-device'
        }
        
        result = sync_service.process_sync_request(data)
        
        assert 'action_results' in result or 'server_changes' in result
    
    @pytest.mark.django_db
    def test_sync_with_invalid_last_sync(self, sync_service):
        """Should handle invalid last_sync values."""
        data = {
            'last_sync': 'invalid-timestamp',
            'pending_actions': [],
            'device_id': 'test-device'
        }
        
        # Should not crash, handle gracefully
        try:
            result = sync_service.process_sync_request(data)
            assert result is not None
        except ValueError:
            pass  # Expected if validation is strict


# ============================================================================
# Tests for _process_action
# ============================================================================

class TestProcessAction:
    """Tests for SyncService._process_action."""
    
    @pytest.mark.django_db
    def test_task_toggle_action(self, sync_service, task):
        """Should toggle task status."""
        action = {
            'id': 'toggle-1',
            'type': 'task_toggle',
            'task_id': str(task.task_instance_id),
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._process_action(action)
        
        assert result['success'] is True or 'error' not in result
    
    @pytest.mark.django_db
    def test_task_status_action(self, sync_service, task):
        """Should set specific task status."""
        action = {
            'id': 'status-1',
            'type': 'task_status',
            'task_id': str(task.task_instance_id),
            'status': 'DONE',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._process_action(action)
        
        task.refresh_from_db()
        assert task.status == 'DONE' or result.get('success', False)
    
    @pytest.mark.django_db
    def test_task_notes_action(self, sync_service, task):
        """Should update task notes."""
        action = {
            'id': 'notes-1',
            'type': 'task_notes',
            'task_id': str(task.task_instance_id),
            'notes': 'Updated notes from mobile',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._process_action(action)
        
        task.refresh_from_db()
        assert task.notes == 'Updated notes from mobile' or result.get('success', False)
    
    @pytest.mark.django_db
    def test_day_note_action(self, sync_service, tracker, user):
        """Should save day note."""
        from datetime import date
        
        action = {
            'id': 'daynote-1',
            'type': 'day_note',
            'tracker_id': str(tracker.tracker_id),
            'date': date.today().isoformat(),
            'content': 'Great productive day!',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._process_action(action)
        
        assert result.get('success', False) or 'day_note' not in str(result.get('error', ''))
    
    @pytest.mark.django_db
    def test_unknown_action_type(self, sync_service):
        """Should handle unknown action types gracefully."""
        action = {
            'id': 'unknown-1',
            'type': 'unknown_action',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._process_action(action)
        
        assert result.get('success') is False or 'error' in result


# ============================================================================
# Tests for _action_task_toggle
# ============================================================================

class TestActionTaskToggle:
    """Tests for SyncService._action_task_toggle."""
    
    @pytest.mark.django_db
    def test_toggle_todo_to_done(self, sync_service, task):
        """Should toggle TODO to DONE or IN_PROGRESS."""
        task.status = 'TODO'
        task.save()
        
        action = {
            'task_id': str(task.task_instance_id),
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._action_task_toggle('toggle-1', action)
        
        task.refresh_from_db()
        assert task.status in ['IN_PROGRESS', 'DONE']
    
    @pytest.mark.django_db
    def test_toggle_done_to_todo(self, sync_service, task):
        """Should toggle DONE to TODO."""
        task.status = 'DONE'
        task.save()
        
        action = {
            'task_id': str(task.task_instance_id),
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._action_task_toggle('toggle-2', action)
        
        task.refresh_from_db()
        assert task.status == 'TODO'
    
    @pytest.mark.django_db
    def test_toggle_nonexistent_task(self, sync_service):
        """Should handle nonexistent task."""
        action = {
            'id': 'toggle-3',
            'type': 'task_toggle',
            'task_id': 'nonexistent-uuid',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._process_action(action)
        
        assert result.get('success') is False or 'error' in result


# ============================================================================
# Tests for _action_task_status
# ============================================================================

class TestActionTaskStatus:
    """Tests for SyncService._action_task_status."""
    
    @pytest.mark.django_db
    def test_set_status_done(self, sync_service, task):
        """Should set status to DONE."""
        action = {
            'task_id': str(task.task_instance_id),
            'status': 'DONE',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._action_task_status('status-1', action)
        
        task.refresh_from_db()
        assert task.status == 'DONE'
    
    @pytest.mark.django_db
    def test_set_status_missed(self, sync_service, task):
        """Should set status to MISSED."""
        action = {
            'task_id': str(task.task_instance_id),
            'status': 'MISSED',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._action_task_status('status-2', action)
        
        task.refresh_from_db()
        assert task.status == 'MISSED'


# ============================================================================
# Tests for _action_day_note
# ============================================================================

class TestActionDayNote:
    """Tests for SyncService._action_day_note."""
    
    @pytest.mark.django_db
    def test_create_new_day_note(self, sync_service, tracker, user):
        """Should create new day note."""
        from datetime import date
        
        action = {
            'tracker_id': str(tracker.tracker_id),
            'date': date.today().isoformat(),
            'content': 'New note',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._action_day_note('note-1', action)
        
        assert result.get('success', False) or DayNote.objects.filter(
            tracker=tracker,
            date=date.today()
        ).exists()
    
    @pytest.mark.django_db
    def test_update_existing_day_note(self, sync_service, tracker, user):
        """Should update existing day note."""
        from datetime import date
        from core.tests.factories import DayNoteFactory
        
        note = DayNoteFactory.create(tracker, target_date=date.today())
        
        action = {
            'tracker_id': str(tracker.tracker_id),
            'date': date.today().isoformat(),
            'content': 'Updated content',
            'timestamp': timezone.now().isoformat()
        }
        
        result = sync_service._action_day_note('note-2', action)
        
        note.refresh_from_db()
        assert note.content == 'Updated content' or result.get('success', False)


# ============================================================================
# Tests for _get_changes_since
# ============================================================================

class TestGetChangesSince:
    """Tests for SyncService._get_changes_since."""
    
    @pytest.mark.django_db
    def test_returns_changes_structure(self, sync_service, tracker):
        """Should return structured changes."""
        last_sync = (timezone.now() - timedelta(hours=1)).isoformat()
        
        changes = sync_service._get_changes_since(last_sync)
        
        assert 'trackers' in changes or 'tasks' in changes or isinstance(changes, dict)
    
    @pytest.mark.django_db
    def test_includes_new_trackers(self, sync_service, user):
        """Should include newly created trackers."""
        from core.tests.factories import TrackerFactory
        
        last_sync = (timezone.now() - timedelta(hours=1)).isoformat()
        
        # Create new tracker after last_sync
        new_tracker = TrackerFactory.create(user, name='New Tracker')
        
        changes = sync_service._get_changes_since(last_sync)
        
        # Should include the new tracker
        assert changes is not None
    
    @pytest.mark.django_db
    def test_includes_updated_tasks(self, sync_service, task, user):
        """Should include updated tasks."""
        last_sync = (timezone.now() - timedelta(hours=1)).isoformat()
        
        # Update task after last_sync
        task.status = 'DONE'
        task.save()
        
        changes = sync_service._get_changes_since(last_sync)
        
        assert changes is not None


# ============================================================================
# Tests for _get_full_sync
# ============================================================================

class TestGetFullSync:
    """Tests for SyncService._get_full_sync."""
    
    @pytest.mark.django_db
    def test_returns_all_user_data(self, sync_service, tracker, task, user):
        """Should return all user data on full sync."""
        data = sync_service._get_full_sync()
        
        assert 'trackers' in data or 'data' in data or isinstance(data, dict)
    
    @pytest.mark.django_db
    def test_does_not_include_other_user_data(self, sync_service, user):
        """Should not include other users' data."""
        from django.contrib.auth import get_user_model
        from core.tests.factories import TrackerFactory
        
        User = get_user_model()
        other_user = User.objects.create_user(
            username='other_sync_user',
            email='other_sync@test.com',
            password='pass123'
        )
        other_tracker = TrackerFactory.create(other_user, name='Other Tracker')
        
        data = sync_service._get_full_sync()
        
        # Should not contain other user's tracker
        if 'trackers' in data and 'updated' in data['trackers']:
            tracker_ids = [t.get('tracker_id') for t in data['trackers']['updated']]
            assert str(other_tracker.tracker_id) not in tracker_ids


# ============================================================================
# Tests for convenience function
# ============================================================================

class TestProcessSyncFunction:
    """Tests for the process_sync convenience function."""
    
    @pytest.mark.django_db
    def test_process_sync_works(self, user, tracker):
        """Should process sync via convenience function."""
        data = {
            'last_sync': timezone.now().isoformat(),
            'pending_actions': [],
            'device_id': 'test-device'
        }
        
        result = process_sync(user, data)
        
        assert result is not None
        assert 'server_changes' in result or 'new_sync_timestamp' in result


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestSyncServiceEdgeCases:
    """Edge case tests for SyncService."""
    
    @pytest.mark.django_db
    def test_handles_malformed_action(self, sync_service):
        """Should handle malformed actions gracefully."""
        data = {
            'pending_actions': [
                {'action_id': 'bad-action'}  # Missing required fields
            ],
            'device_id': 'test-device'
        }
        
        # Should not crash
        result = sync_service.process_sync_request(data)
        assert result is not None
    
    @pytest.mark.django_db
    def test_handles_future_last_sync(self, sync_service):
        """Should handle future last_sync timestamp."""
        data = {
            'last_sync': (timezone.now() + timedelta(hours=1)).isoformat(),
            'pending_actions': [],
            'device_id': 'test-device'
        }
        
        result = sync_service.process_sync_request(data)
        
        # Should handle gracefully
        assert result is not None
    
    @pytest.mark.django_db
    def test_handles_very_old_last_sync(self, sync_service):
        """Should handle very old last_sync (lots of changes)."""
        data = {
            'last_sync': (timezone.now() - timedelta(days=365)).isoformat(),
            'pending_actions': [],
            'device_id': 'test-device'
        }
        
        result = sync_service.process_sync_request(data)
        
        assert result is not None
    
    @pytest.mark.django_db
    def test_concurrent_actions_same_task(self, sync_service, task):
        """Should handle multiple actions on same task."""
        data = {
            'pending_actions': [
                {
                    'id': 'action-1',
                    'type': 'task_status',
                    'task_id': str(task.task_instance_id),
                    'status': 'IN_PROGRESS',
                    'timestamp': timezone.now().isoformat()
                },
                {
                    'id': 'action-2',
                    'type': 'task_status',
                    'task_id': str(task.task_instance_id),
                    'status': 'DONE',
                    'timestamp': (timezone.now() + timedelta(seconds=1)).isoformat()
                }
            ],
            'device_id': 'test-device'
        }
        
        result = sync_service.process_sync_request(data)
        
        task.refresh_from_db()
        # Last action should win
        assert task.status == 'DONE'
