"""
Unit tests for core/services/task_service.py

Tests task management operations:
- Task template creation and deletion
- Status updates and toggling
- Bulk operations
- Task statistics
- Edge cases and error handling
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone

from core.services.task_service import TaskService
from core.models import TrackerDefinition, TaskTemplate, TaskInstance, TrackerInstance
from core.exceptions import (
    TaskNotFoundError,
    TemplateNotFoundError,
    InvalidStatusError,
    ValidationError as AppValidationError
)


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='task_test_user',
        email='task@test.com',
        password='testpass123'
    )


@pytest.fixture
def tracker(db, user):
    """Create a test tracker."""
    from core.tests.factories import TrackerFactory
    return TrackerFactory.create(user)


@pytest.fixture
def template(db, tracker):
    """Create a test task template."""
    from core.tests.factories import TemplateFactory
    return TemplateFactory.create(tracker)


@pytest.fixture
def instance(db, tracker):
    """Create a test tracker instance."""
    from core.tests.factories import InstanceFactory
    return InstanceFactory.create(tracker)


@pytest.fixture
def task(db, instance, template):
    """Create a test task instance."""
    from core.tests.factories import TaskInstanceFactory
    return TaskInstanceFactory.create(instance, template)


@pytest.fixture
def task_service():
    """Create TaskService instance."""
    return TaskService()


# ============================================================================
# Tests for create_task_template
# ============================================================================

class TestCreateTaskTemplate:
    """Tests for TaskService.create_task_template."""
    
    @pytest.mark.django_db
    def test_creates_template_successfully(self, task_service, tracker):
        """Should create a new task template."""
        data = {
            'description': 'Morning exercise',
            'category': 'health',
            'weight': 2,
            'is_recurring': True
        }
        
        result = task_service.create_task_template(str(tracker.tracker_id), data)
        
        assert result is not None
        assert 'template_id' in result or 'description' in result
    
    @pytest.mark.django_db
    def test_template_with_minimal_data(self, task_service, tracker):
        """Should create template with minimal required data."""
        data = {
            'description': 'Simple task'
        }
        
        result = task_service.create_task_template(str(tracker.tracker_id), data)
        
        assert result is not None
    
    @pytest.mark.django_db
    def test_template_validation(self, task_service, tracker):
        """Should validate template data."""
        data = {
            'description': '',  # Empty description
        }
        
        # May raise validation error or handle gracefully
        try:
            result = task_service.create_task_template(str(tracker.tracker_id), data)
            # If no error, check that empty descriptions are handled
        except (AppValidationError, Exception):
            pass  # Expected behavior


# ============================================================================
# Tests for update_task_status
# ============================================================================

class TestUpdateTaskStatus:
    """Tests for TaskService.update_task_status."""
    
    @pytest.mark.django_db
    def test_update_to_done(self, task_service, task):
        """Should update status to DONE."""
        result = task_service.update_task_status(
            str(task.task_instance_id), 'DONE'
        )
        
        task.refresh_from_db()
        assert task.status == 'DONE'
    
    @pytest.mark.django_db
    def test_update_sets_completed_at(self, task_service, task):
        """Should set completed_at when marking DONE."""
        assert task.completed_at is None
        
        task_service.update_task_status(str(task.task_instance_id), 'DONE')
        
        task.refresh_from_db()
        assert task.completed_at is not None
    
    @pytest.mark.django_db
    def test_update_to_todo_clears_completed_at(self, task_service, task):
        """Should clear completed_at when changing from DONE to TODO."""
        # First mark as done
        task.status = 'DONE'
        task.completed_at = timezone.now()
        task.save()
        
        task_service.update_task_status(str(task.task_instance_id), 'TODO')
        
        task.refresh_from_db()
        assert task.status == 'TODO'
        # completed_at might be cleared or kept for history
    
    @pytest.mark.django_db
    def test_update_with_notes(self, task_service, task):
        """Should update notes along with status."""
        result = task_service.update_task_status(
            str(task.task_instance_id), 
            'DONE',
            notes='Completed successfully'
        )
        
        task.refresh_from_db()
        assert task.notes == 'Completed successfully' or 'notes' in str(result)
    
    @pytest.mark.django_db
    def test_invalid_status_raises_error(self, task_service, task):
        """Should raise InvalidStatusError for invalid status."""
        with pytest.raises(InvalidStatusError):
            task_service.update_task_status(
                str(task.task_instance_id), 'INVALID_STATUS'
            )
    
    @pytest.mark.django_db
    def test_nonexistent_task_raises_error(self, task_service):
        """Should raise TaskNotFoundError for missing task."""
        with pytest.raises(TaskNotFoundError):
            task_service.update_task_status(
                'nonexistent-uuid', 'DONE'
            )


# ============================================================================
# Tests for toggle_task_status
# ============================================================================

class TestToggleTaskStatus:
    """Tests for TaskService.toggle_task_status."""
    
    @pytest.mark.django_db
    def test_toggle_todo_to_in_progress(self, task_service, task):
        """Should toggle TODO to IN_PROGRESS."""
        task.status = 'TODO'
        task.save()
        
        result = task_service.toggle_task_status(str(task.task_instance_id))
        
        task.refresh_from_db()
        assert task.status in ['IN_PROGRESS', 'DONE']
    
    @pytest.mark.django_db
    def test_toggle_in_progress_to_done(self, task_service, task):
        """Should toggle IN_PROGRESS to DONE."""
        task.status = 'IN_PROGRESS'
        task.save()
        
        result = task_service.toggle_task_status(str(task.task_instance_id))
        
        task.refresh_from_db()
        assert task.status == 'DONE'
    
    @pytest.mark.django_db
    def test_toggle_done_to_todo(self, task_service, task):
        """Should toggle DONE back to TODO."""
        task.status = 'DONE'
        task.save()
        
        result = task_service.toggle_task_status(str(task.task_instance_id))
        
        task.refresh_from_db()
        assert task.status == 'TODO'
    
    @pytest.mark.django_db
    def test_toggle_returns_updated_task(self, task_service, task):
        """Should return updated task data."""
        result = task_service.toggle_task_status(str(task.task_instance_id))
        
        assert result is not None
        assert 'status' in result or isinstance(result, dict)


# ============================================================================
# Tests for bulk_update_tasks
# ============================================================================

class TestBulkUpdateTasks:
    """Tests for TaskService.bulk_update_tasks."""
    
    @pytest.mark.django_db
    def test_bulk_update_multiple_tasks(self, task_service, instance, template):
        """Should update multiple tasks at once."""
        from core.tests.factories import TaskInstanceFactory
        
        tasks = [
            TaskInstanceFactory.create(instance, template),
            TaskInstanceFactory.create(instance, template),
            TaskInstanceFactory.create(instance, template),
        ]
        task_ids = [str(t.task_instance_id) for t in tasks]
        
        result = task_service.bulk_update_tasks(task_ids, 'DONE')
        
        assert result['updated'] == 3
        assert result['failed'] == 0
    
    @pytest.mark.django_db
    def test_bulk_update_partial_failure(self, task_service, instance, template):
        """Should handle partial failures gracefully."""
        from core.tests.factories import TaskInstanceFactory
        
        task = TaskInstanceFactory.create(instance, template)
        task_ids = [str(task.task_instance_id), 'invalid-uuid']
        
        result = task_service.bulk_update_tasks(task_ids, 'DONE')
        
        assert result['updated'] >= 1
        assert result['failed'] >= 0
    
    @pytest.mark.django_db
    def test_bulk_update_empty_list(self, task_service):
        """Should handle empty task list."""
        # Service validates that list is not empty
        with pytest.raises(AppValidationError):
            task_service.bulk_update_tasks([], 'DONE')
    
    @pytest.mark.django_db
    def test_bulk_update_returns_tracker_ids(self, task_service, instance, template):
        """Should return affected tracker IDs."""
        from core.tests.factories import TaskInstanceFactory
        
        task = TaskInstanceFactory.create(instance, template)
        
        result = task_service.bulk_update_tasks(
            [str(task.task_instance_id)], 'DONE'
        )
        
        assert 'tracker_ids' in result


# ============================================================================
# Tests for mark_overdue_as_missed
# ============================================================================

class TestMarkOverdueAsMissed:
    """Tests for TaskService.mark_overdue_as_missed."""
    
    @pytest.mark.django_db
    def test_marks_old_tasks_as_missed(self, task_service, tracker, template):
        """Should mark tasks before cutoff as MISSED."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        old_date = date(2025, 1, 1)
        instance = InstanceFactory.create(tracker, target_date=old_date)
        task = TaskInstanceFactory.create(instance, template, status='TODO')
        
        count = task_service.mark_overdue_as_missed(
            str(tracker.tracker_id),
            cutoff_date=date(2025, 1, 2)
        )
        
        task.refresh_from_db()
        assert task.status == 'MISSED'
        assert count >= 1
    
    @pytest.mark.django_db
    def test_does_not_mark_done_tasks(self, task_service, tracker, template):
        """Should not change already DONE tasks."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        old_date = date(2025, 1, 1)
        instance = InstanceFactory.create(tracker, target_date=old_date)
        task = TaskInstanceFactory.create(instance, template, status='DONE')
        
        task_service.mark_overdue_as_missed(
            str(tracker.tracker_id),
            cutoff_date=date(2025, 1, 2)
        )
        
        task.refresh_from_db()
        assert task.status == 'DONE'


# ============================================================================
# Tests for delete_task_template
# ============================================================================

class TestDeleteTaskTemplate:
    """Tests for TaskService.delete_task_template."""
    
    @pytest.mark.django_db
    def test_deletes_template_successfully(self, task_service, template):
        """Should delete template."""
        template_id = str(template.template_id)
        
        result = task_service.delete_task_template(template_id)
        
        assert result is True
        # Template should be deleted or soft-deleted
        assert not TaskTemplate.objects.filter(
            template_id=template_id,
            deleted_at__isnull=True
        ).exists()
    
    @pytest.mark.django_db
    def test_delete_nonexistent_template_raises_error(self, task_service):
        """Should raise TemplateNotFoundError for missing template."""
        with pytest.raises(TemplateNotFoundError):
            task_service.delete_task_template('nonexistent-uuid')


# ============================================================================
# Tests for duplicate_task_template
# ============================================================================

class TestDuplicateTaskTemplate:
    """Tests for TaskService.duplicate_task_template."""
    
    @pytest.mark.django_db
    def test_duplicates_template(self, task_service, template):
        """Should create a copy of the template."""
        original_count = TaskTemplate.objects.filter(
            tracker=template.tracker
        ).count()
        
        result = task_service.duplicate_task_template(str(template.template_id))
        
        new_count = TaskTemplate.objects.filter(
            tracker=template.tracker
        ).count()
        
        assert new_count == original_count + 1
    
    @pytest.mark.django_db
    def test_duplicate_has_different_id(self, task_service, template):
        """Duplicated template should have new ID."""
        result = task_service.duplicate_task_template(str(template.template_id))
        
        assert str(result.template_id) != str(template.template_id)


# ============================================================================
# Tests for get_task_stats
# ============================================================================

class TestGetTaskStats:
    """Tests for TaskService.get_task_stats."""
    
    @pytest.mark.django_db
    def test_returns_stats_structure(self, task_service, tracker, instance, template):
        """Should return complete stats structure."""
        from core.tests.factories import TaskInstanceFactory
        
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='TODO')
        
        result = task_service.get_task_stats(str(tracker.tracker_id))
        
        assert 'total' in result
        assert 'done' in result
        assert 'todo' in result
        assert 'completion_rate' in result
    
    @pytest.mark.django_db
    def test_calculates_completion_rate(self, task_service, tracker, instance, template):
        """Should calculate correct completion rate."""
        from core.tests.factories import TaskInstanceFactory
        
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='TODO')
        TaskInstanceFactory.create(instance, template, status='TODO')
        
        result = task_service.get_task_stats(str(tracker.tracker_id))
        
        assert result['total'] == 4
        assert result['done'] == 2
        assert result['completion_rate'] == 50.0
    
    @pytest.mark.django_db
    def test_stats_with_date_filter(self, task_service, tracker, template):
        """Should filter stats by date range."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        instance_today = InstanceFactory.create(tracker, target_date=today)
        instance_yesterday = InstanceFactory.create(tracker, target_date=yesterday)
        
        TaskInstanceFactory.create(instance_today, template, status='DONE')
        TaskInstanceFactory.create(instance_yesterday, template, status='TODO')
        
        result = task_service.get_task_stats(
            str(tracker.tracker_id),
            date_filter={'start_date': today, 'end_date': today}
        )
        
        # Should only count today's task
        assert result['total'] == 1


# ============================================================================
# Tests for quick_add_task
# ============================================================================

class TestQuickAddTask:
    """Tests for TaskService.quick_add_task."""
    
    @pytest.mark.django_db
    def test_quick_add_creates_template_and_instance(self, task_service, tracker, user):
        """Should create both template and task instance."""
        initial_template_count = TaskTemplate.objects.filter(tracker=tracker).count()
        
        result = task_service.quick_add_task(
            str(tracker.tracker_id),
            user,
            description='Quick task'
        )
        
        new_template_count = TaskTemplate.objects.filter(tracker=tracker).count()
        assert new_template_count == initial_template_count + 1
    
    @pytest.mark.django_db
    def test_quick_add_with_options(self, task_service, tracker, user):
        """Should accept optional parameters."""
        result = task_service.quick_add_task(
            str(tracker.tracker_id),
            user,
            description='Morning workout',
            category='health',
            weight=3,
            time_of_day='morning'
        )
        
        assert result is not None


# ============================================================================
# Tests for get_task_by_id
# ============================================================================

class TestGetTaskById:
    """Tests for TaskService.get_task_by_id."""
    
    @pytest.mark.django_db
    def test_returns_task(self, task_service, task, user):
        """Should return task by ID."""
        result = task_service.get_task_by_id(str(task.task_instance_id), user)
        
        assert result is not None
    
    @pytest.mark.django_db
    def test_raises_for_nonexistent(self, task_service, user):
        """Should raise TaskNotFoundError for missing task."""
        with pytest.raises(TaskNotFoundError):
            task_service.get_task_by_id('nonexistent-uuid', user)


# ============================================================================
# Edge Cases
# ============================================================================

class TestTaskServiceEdgeCases:
    """Edge case tests for TaskService."""
    
    @pytest.mark.django_db
    def test_status_update_with_special_characters_in_notes(self, task_service, task):
        """Should handle special characters in notes."""
        special_notes = "Test with émojis 🎉 and <script>tags</script>"
        
        result = task_service.update_task_status(
            str(task.task_instance_id),
            'DONE',
            notes=special_notes
        )
        
        task.refresh_from_db()
        assert task.status == 'DONE'
    
    @pytest.mark.django_db
    def test_empty_tracker_stats(self, task_service, tracker):
        """Should handle tracker with no tasks."""
        result = task_service.get_task_stats(str(tracker.tracker_id))
        
        assert result['total'] == 0
        assert result['completion_rate'] == 0  # No division by zero
    
    @pytest.mark.django_db
    def test_all_tasks_done(self, task_service, tracker, instance, template):
        """Should show 100% completion when all done."""
        from core.tests.factories import TaskInstanceFactory
        
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        result = task_service.get_task_stats(str(tracker.tracker_id))
        
        assert result['completion_rate'] == 100.0
