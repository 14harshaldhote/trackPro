"""
Tests for TaskService layer.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from core.services.task_service import TaskService
from core.models import TrackerDefinition, TaskTemplate, TrackerInstance, TaskInstance
from core.exceptions import TaskNotFoundError, InvalidStatusError

User = get_user_model()


class TaskServiceTests(TestCase):
    """Test TaskService domain logic"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='taskuser', password='pass')
        self.task_service = TaskService()  # TaskService doesn't take user argument
        
        # Setup Tracker
        self.tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Daily Tracker',
            tracker_id='test-tracker-1'
        )
        self.template = TaskTemplate.objects.create(
            tracker=self.tracker,
            template_id='test-template-1',
            description='Test Task',
            weight=1
        )
        
        # Setup Instance and Task
        today = date.today()
        self.tracker_instance = TrackerInstance.objects.create(
            tracker=self.tracker,
            instance_id='test-instance-1',
            tracking_date=today,
            period_start=today,
            period_end=today
        )
        self.task = TaskInstance.objects.create(
            tracker_instance=self.tracker_instance,
            template=self.template,
            task_instance_id='test-task-1',
            status='TODO',
            notes=''  # Required field
        )

    def test_update_task_status_success(self):
        """Test status update and completion time"""
        result = self.task_service.update_task_status('test-task-1', 'DONE')
        
        self.assertEqual(result['status'], 'DONE')
        self.assertIsNotNone(result['completed_at'])
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'DONE')
        self.assertIsNotNone(self.task.completed_at)

    def test_update_task_status_invalid_transition(self):
        """Test invalid status via serializer enforcement"""
        with self.assertRaises(InvalidStatusError):
            self.task_service.update_task_status('test-task-1', 'INVALID_STATUS')

    def test_update_task_not_found(self):
        """Test missing task"""
        with self.assertRaises(TaskNotFoundError):
            self.task_service.update_task_status('missing-id', 'DONE')

    def test_bulk_update_tasks(self):
        """Test bulk status update"""
        # Create second task
        task2 = TaskInstance.objects.create(
            tracker_instance=self.tracker_instance,
            template=self.template,
            task_instance_id='test-task-2',
            status='TODO',
            notes=''
        )
        
        result = self.task_service.bulk_update_tasks(['test-task-1', 'test-task-2'], 'DONE')
        
        self.assertEqual(result['updated'], 2)
        self.assertEqual(result['failed'], 0)
        
        self.task.refresh_from_db()
        task2.refresh_from_db()
        self.assertEqual(self.task.status, 'DONE')
        self.assertEqual(task2.status, 'DONE')

    def test_get_historical_tasks(self):
        """Test historical tasks retrieval"""
        # Create past task
        past_date = date.today() - timedelta(days=5)
        past_instance = TrackerInstance.objects.create(
            tracker=self.tracker,
            instance_id='past-instance',
            tracking_date=past_date,
            period_start=past_date,
            period_end=past_date
        )
        TaskInstance.objects.create(
            tracker_instance=past_instance,
            template=self.template,
            task_instance_id='past-task',
            status='DONE',
            notes=''
        )
        
        history = self.task_service.get_historical_tasks('test-tracker-1', days=7)
        # get_historical_tasks uses end_date as exclusive, so today's task is not included
        self.assertEqual(history.count(), 1)  # Only past task (today excluded)

    def test_mark_overdue_as_missed(self):
        """Test overdue marking"""
        # Create overdue task (TODO)
        past_date = date.today() - timedelta(days=2)
        past_instance = TrackerInstance.objects.create(
            tracker=self.tracker,
            instance_id='overdue-instance',
            tracking_date=past_date,
            period_start=past_date,
            period_end=past_date
        )
        TaskInstance.objects.create(
            tracker_instance=past_instance,
            template=self.template,
            task_instance_id='overdue-task',
            status='TODO',
            notes=''
        )
        
        # Today's task (should stay TODO)
        
        marked = self.task_service.mark_overdue_as_missed('test-tracker-1', date.today())
        
        self.assertEqual(marked, 1)
        
        overdue_task = TaskInstance.objects.get(task_instance_id='overdue-task')
        self.assertEqual(overdue_task.status, 'MISSED')
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'TODO') # Should be untouched
