
from django.test import TestCase
from datetime import date, timedelta
from django.utils import timezone
from core.services import points_service
from core.models import UserPreferences
from core.tests.factories import UserFactory, TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory

class TestPointsServiceUnit(TestCase):

    def setUp(self):
        self.user = UserFactory.create(username="points_user")
        self.tracker = TrackerFactory.create(user=self.user, target_points=10, goal_period='daily', goal_start_day=0) # 0=Monday
        self.template = TemplateFactory.create(
            tracker=self.tracker, 
            points=5, 
            include_in_goal=True
        )
        self.today = date.today()
        self.instance = InstanceFactory.create(tracker=self.tracker, target_date=self.today)
        self.task = TaskInstanceFactory.create(instance=self.instance, template=self.template, status='DONE')

    def test_init_default_timezone(self):
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user)
        # Default is UTC if no preferences
        assert service._user_timezone.zone == 'UTC'
        assert service.target_date == timezone.now().date()

    def test_init_with_user_timezone(self):
        UserPreferences.objects.create(user=self.user, timezone='Asia/Kolkata')
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user)
        assert service._user_timezone.zone == 'Asia/Kolkata'

    def test_get_period_date_range_daily(self):
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user, target_date=self.today)
        start, end = service.get_period_date_range('daily')
        assert start == self.today
        assert end == self.today

    def test_get_period_date_range_weekly(self):
        # Determine week dates manually
        # Monday=0. If today is Wed (2). start = today - 2.
        weekday = self.today.weekday()
        week_start = self.today - timedelta(days=weekday)
        week_end = week_start + timedelta(days=6)
        
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user, target_date=self.today)
        start, end = service.get_period_date_range('weekly')
        assert start == week_start
        assert end == week_end

    def test_get_applicable_tasks(self):
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user, target_date=self.today)
        tasks = service.get_applicable_tasks()
        assert len(tasks) == 1
        assert tasks[0].task_instance_id == self.task.task_instance_id

        # Non-completed filter
        tasks_all = service.get_applicable_tasks(include_only_completed=False)
        assert len(tasks_all) == 1

        # Exclude task
        self.template.include_in_goal = False
        self.template.save()
        tasks = service.get_applicable_tasks()
        assert len(tasks) == 0

    def test_calculate_current_points(self):
        # 1 task worth 5 points. Target 10.
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user, target_date=self.today)
        res = service.calculate_current_points()
        
        assert res['current_points'] == 5
        assert res['target_points'] == 10
        assert res['progress_percentage'] == 50.0
        assert res['goal_met'] == False
        
        # Add another task to meet goal
        t2 = TemplateFactory.create(tracker=self.tracker, points=5, include_in_goal=True)
        TaskInstanceFactory.create(instance=self.instance, template=t2, status='DONE')
        
        res = service.calculate_current_points()
        assert res['current_points'] == 10
        assert res['progress_percentage'] == 100.0
        assert res['goal_met'] == True

    def test_calculate_current_points_zero_target(self):
        self.tracker.target_points = 0
        self.tracker.save()
        
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user, target_date=self.today)
        res = service.calculate_current_points()
        assert res['target_points'] == 0
        assert res['progress_percentage'] == 0.0 # Division by zero handled
        assert res['goal_met'] == False

    def test_get_task_points_breakdown(self):
        service = points_service.PointsCalculationService(self.tracker.tracker_id, self.user, target_date=self.today)
        breakdown = service.get_task_points_breakdown()
        assert len(breakdown) == 1
        assert breakdown[0]['points_earned'] == 5
        assert breakdown[0]['is_completed'] == True

    def test_calculate_tracker_progress(self):
        res = points_service.calculate_tracker_progress(self.tracker.tracker_id, self.user)
        assert res['current_points'] == 5

    def test_toggle_task_goal_inclusion(self):
        # Set to false
        res = points_service.toggle_task_goal_inclusion(self.template.template_id, self.user, False)
        assert res['include_in_goal'] == False
        assert res['tracker_progress']['current_points'] == 0 # Excluded now
        
        self.template.refresh_from_db()
        assert self.template.include_in_goal == False
        
        # Error case
        try:
            points_service.toggle_task_goal_inclusion("fake-id", self.user, True)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_update_task_points(self):
        res = points_service.update_task_points(self.template.template_id, self.user, 10)
        assert res['points'] == 10
        assert res['tracker_progress']['current_points'] == 10
        
        self.template.refresh_from_db()
        assert self.template.points == 10
        
        # Negative error
        try:
            points_service.update_task_points(self.template.template_id, self.user, -5)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
        
        # does not exist
        try:
            points_service.update_task_points("fake-id", self.user, 10)
            assert False
        except ValueError:
            pass

    def test_set_tracker_goal(self):
        res = points_service.set_tracker_goal(self.tracker.tracker_id, self.user, 20, 'weekly')
        assert res['target_points'] == 20
        assert res['goal_period'] == 'weekly'
        
        self.tracker.refresh_from_db()
        assert self.tracker.target_points == 20
        assert self.tracker.goal_period == 'weekly' # updated
        
        # Negative target error
        try:
            points_service.set_tracker_goal(self.tracker.tracker_id, self.user, -1)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
            
        # Tracker not found
        try:
            points_service.set_tracker_goal("fake-id", self.user, 10)
            assert False
        except ValueError:
            pass
