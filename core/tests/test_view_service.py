
import pytest
from unittest.mock import Mock, MagicMock
from core.services.view_service import ViewService, UI_COLORS, TOUCH_TARGET_MIN_SIZE

class TestViewService:
    def test_constants(self):
        """Test that UI constants are correct."""
        assert UI_COLORS['success'] == '#34C759'
        assert UI_COLORS['warning'] == '#FF9500'
        assert UI_COLORS['error'] == '#FF3B30'
        assert TOUCH_TARGET_MIN_SIZE == 44

    def test_format_task_for_list_with_object(self):
        """Test formatting a task object."""
        # Setup mock objects
        tracker = Mock()
        tracker.name = "Test Tracker"
        tracker.tracker_id = "tracker-123"
        tracker.color = "blue"

        template = Mock()
        template.description = "Task Description"
        template.category = "Health"
        template.time_of_day = "morning"
        template.weight = 5

        task = Mock()
        task.task_instance_id = "task-123"
        task.status = "PENDING"
        task.template = template

        # Execute
        result = ViewService.format_task_for_list(task, tracker)

        # Verify
        assert result['task_instance_id'] == "task-123"
        assert result['status'] == "PENDING"
        assert result['description'] == "Task Description"
        assert result['category'] == "Health"
        assert result['time_of_day'] == "morning"
        assert result['weight'] == 5
        assert result['tracker_name'] == "Test Tracker"
        assert result['tracker_id'] == "tracker-123"
        assert result['tracker_color'] == "blue"
        assert result['_obj'] == task
        assert 'ios_swipe_actions' in result
        assert 'ios_context_menu' in result

    def test_format_task_for_list_with_dict(self):
        """Test formatting a task dictionary."""
        # Setup
        tracker = Mock()
        tracker.name = "Test Tracker"
        tracker.tracker_id = "tracker-123"
        
        task_dict = {
            'task_instance_id': "task-123",
            'status': "DONE",
            'description': "Dict Description",
            'category': "Work",
            'time_of_day': "afternoon",
            'weight': 3
        }

        # Execute
        result = ViewService.format_task_for_list(task_dict, tracker)

        # Verify
        assert result['task_instance_id'] == "task-123"
        assert result['status'] == "DONE"
        assert result['description'] == "Dict Description"
        assert result['category'] == "Work"
        assert result['ios_swipe_actions']['leading'] == [] # Completed tasks have no leading action (complete)

    def test_format_task_for_list_missing_status(self):
        """Test formatting returns None if status is missing."""
        tracker = Mock()
        task = Mock()
        task.status = None
        
        assert ViewService.format_task_for_list(task, tracker) is None

    def test_get_swipe_actions_pending(self):
        """Test swipe actions for pending task."""
        actions = ViewService._get_swipe_actions("task-123", "PENDING")
        
        # Should have complete action
        leading = actions['leading']
        assert len(leading) == 1
        assert leading[0]['id'] == 'complete'
        assert leading[0]['endpoint'] == '/api/task/task-123/toggle/'
        
        # Should have skip and delete actions
        trailing = actions['trailing']
        assert len(trailing) == 2
        assert trailing[0]['id'] == 'skip'
        assert trailing[1]['id'] == 'delete'

    def test_get_swipe_actions_done(self):
        """Test swipe actions for completed task."""
        actions = ViewService._get_swipe_actions("task-123", "DONE")
        
        # Should NOT have complete action
        assert len(actions['leading']) == 0
        
        # Should still have skip and delete
        assert len(actions['trailing']) == 2
