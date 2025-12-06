from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
from core.services.task_service import TaskService
from core.services.tracker_service import TrackerService
from core.models import TrackerDefinition, TaskInstance, TrackerInstance, TaskTemplate
from core.exceptions import InvalidStatusError, TaskNotFoundError, ValidationError as AppValidationError

User = get_user_model()

class TaskServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.task_service = TaskService()
        self.tracker_service = TrackerService()
        
        # Setup Tracker and Template
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
        self.tracker_instance = TrackerInstance.objects.create(
            tracker=self.tracker,
            instance_id='test-instance-1',
            period_start=date.today(),
            period_end=date.today()
        )
        self.task = TaskInstance.objects.create(
            tracker_instance=self.tracker_instance,
            template=self.template,
            task_instance_id='test-task-1',
            status='TODO'
        )

    def test_update_task_status_success(self):
        """Test status update and completion time"""
        result = self.task_service.update_task_status('test-task-1', 'DONE')
        
        self.assertEqual(result['status'], 'DONE')
        self.assertIsNotNone(result['completed_at'])
        
        # Verify DB
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'DONE')
        self.assertIsNotNone(self.task.completed_at)
        
        # Revert to TODO
        result = self.task_service.update_task_status('test-task-1', 'TODO')
        self.assertEqual(result['status'], 'TODO')
        self.assertIsNone(result['completed_at'])

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
            status='TODO'
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
            period_start=past_date,
            period_end=past_date
        )
        TaskInstance.objects.create(
            tracker_instance=past_instance,
            template=self.template,
            task_instance_id='past-task',
            status='DONE'
        )
        
        history = self.task_service.get_historical_tasks('test-tracker-1', days=7)
        self.assertEqual(history.count(), 2) # Today's + Past

    def test_mark_overdue_as_missed(self):
        """Test overdue marking"""
        # Create overdue task (TODO)
        past_date = date.today() - timedelta(days=2)
        past_instance = TrackerInstance.objects.create(
            tracker=self.tracker,
            instance_id='overdue-instance',
            period_start=past_date,
            period_end=past_date
        )
        TaskInstance.objects.create(
            tracker_instance=past_instance,
            template=self.template,
            task_instance_id='overdue-task',
            status='TODO'
        )
        
        # Today's task (should stay TODO)
        
        marked = self.task_service.mark_overdue_as_missed('test-tracker-1', date.today())
        
        self.assertEqual(marked, 1)
        
        overdue_task = TaskInstance.objects.get(task_instance_id='overdue-task')
        self.assertEqual(overdue_task.status, 'MISSED')
        
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'TODO') # Should be untouched
