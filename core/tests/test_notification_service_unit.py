
from datetime import date
from django.test import TestCase
from unittest.mock import Mock, patch
from core.services.notification_service import NotificationService
from core.models import UserPreferences, Notification, TaskInstance
from core.tests.factories import UserFactory, TrackerFactory, InstanceFactory, TaskInstanceFactory, TemplateFactory

class TestNotificationService(TestCase):

    def setUp(self):
        self.user = UserFactory.create(username="notif_user")
        self.prefs = UserPreferences.objects.create(
            user=self.user,
            daily_reminder_enabled=True,
            daily_reminder_time='09:00:00'
        )
        # Create a default tracker and template for reuse or create inside tests
        self.tracker = TrackerFactory.create(user=self.user)
        self.template = TemplateFactory.create(tracker=self.tracker)

    def test_get_reminder_time(self):
        # With active prefs
        time_val = NotificationService.get_reminder_time(self.user.pk)
        assert time_val.hour == 9
        
        # User not found / default
        with patch('core.models.UserPreferences.objects.get', side_effect=UserPreferences.DoesNotExist):
            time_val = NotificationService.get_reminder_time(self.user.pk)
            assert time_val == NotificationService.DEFAULT_REMINDER_TIME

    def test_send_daily_reminder(self):
        # 1. Prefs disabled
        self.prefs.daily_reminder_enabled = False
        self.prefs.save()
        assert NotificationService.send_daily_reminder(self.user.pk) is None
        
        # 2. Prefs enabled, no tasks
        self.prefs.daily_reminder_enabled = True
        self.prefs.save()
        assert NotificationService.send_daily_reminder(self.user.pk) is None
        
        # 3. With tasks
        tracker = TrackerFactory.create(user=self.user, status='active')
        template = TemplateFactory.create(tracker=tracker)
        instance = InstanceFactory.create(tracker=tracker, target_date=date.today())
        TaskInstanceFactory.create(instance=instance, template=template, status='TODO')
        
        notif = NotificationService.send_daily_reminder(self.user.pk)
        assert notif is not None
        assert notif.type == 'reminder'
        assert '1 tasks' in notif.message
        
        # 4. Prefs DoesNotExist
        with patch('core.models.UserPreferences.objects.get', side_effect=UserPreferences.DoesNotExist):
            assert NotificationService.send_daily_reminder(self.user.pk) is None

    def test_send_evening_summary(self):
        # No stats
        res = NotificationService.send_evening_summary(self.user.pk)
        assert res is None
        
        # With stats
        tracker = TrackerFactory.create(user=self.user)
        template = TemplateFactory.create(tracker=tracker)
        instance = InstanceFactory.create(tracker=tracker, target_date=date.today())
        TaskInstanceFactory.create(instance=instance, template=template, status='DONE')
        TaskInstanceFactory.create(instance=instance, template=template, status='TODO')
        
        notif = NotificationService.send_evening_summary(self.user.pk)
        assert notif is not None
        assert '50% done' in notif.message
        
        # All done
        TaskInstance.objects.update(status='DONE')
        notif = NotificationService.send_evening_summary(self.user.pk)
        assert 'Amazing' in notif.message

    def test_send_streak_alert(self):
        # Not a milestone
        assert NotificationService.send_streak_alert(self.user.pk, "Gym", 5) is None
        
        # Milestone
        notif = NotificationService.send_streak_alert(self.user.pk, "Gym", 7)
        assert notif is not None
        assert notif.type == 'achievement'
        assert '7 days' in notif.message

    def test_send_goal_progress_update(self):
        # Not a milestone
        assert NotificationService.send_goal_progress_update(self.user.pk, "Goal", 10.0) is None
        
        # Milestone 50%
        notif = NotificationService.send_goal_progress_update(self.user.pk, "Goal", 50.0)
        assert notif is not None
        assert '50%' in notif.message
        
        # Milestone 100%
        notif = NotificationService.send_goal_progress_update(self.user.pk, "Goal", 100.0)
        assert notif.type == 'success'

    def test_mark_all_read(self):
        # Create unread notifs
        Notification.objects.create(user=self.user, title="Test 1")
        Notification.objects.create(user=self.user, title="Test 2")
        
        assert Notification.objects.filter(is_read=False).count() == 2
        
        count = NotificationService.mark_all_read(self.user.pk)
        assert count == 2
        assert Notification.objects.filter(is_read=False).count() == 0

    def test_get_unread_count(self):
        assert NotificationService.get_unread_count(self.user.pk) == 0
        Notification.objects.create(user=self.user, title="Test 1")
        assert NotificationService.get_unread_count(self.user.pk) == 1
