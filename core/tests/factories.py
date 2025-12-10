"""
Test factories for creating test data.

Usage:
    from core.tests.factories import TrackerFactory, TemplateFactory
    
    tracker = TrackerFactory.create(user)
    template = TemplateFactory.create(tracker)
"""
import uuid
from datetime import date, timedelta
from django.contrib.auth import get_user_model


class UserFactory:
    """Factory for creating test users."""
    
    counter = 0
    
    @classmethod
    def create(cls, **kwargs):
        cls.counter += 1
        defaults = {
            'username': f'testuser_{cls.counter}',
            'email': f'testuser_{cls.counter}@example.com',
            'password': 'testpass123'
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        User = get_user_model()
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        return user


class TrackerFactory:
    """Factory for creating test trackers."""
    
    @staticmethod
    def create(user, **kwargs):
        from core.models import TrackerDefinition
        
        defaults = {
            'tracker_id': str(uuid.uuid4()),
            'name': f'Test Tracker {uuid.uuid4().hex[:6]}',
            'description': 'A test tracker',
            'time_mode': 'daily',
            'status': 'active'
        }
        defaults.update(kwargs)
        return TrackerDefinition.objects.create(user=user, **defaults)


class TemplateFactory:
    """Factory for creating test task templates."""
    
    @staticmethod
    def create(tracker, **kwargs):
        from core.models import TaskTemplate
        
        defaults = {
            'template_id': str(uuid.uuid4()),
            'description': f'Test Task {uuid.uuid4().hex[:6]}',
            'category': 'general',
            'points': 1,
            'weight': 1.0,
            'is_recurring': True,
            'time_of_day': 'anytime'
        }
        defaults.update(kwargs)
        return TaskTemplate.objects.create(tracker=tracker, **defaults)


class InstanceFactory:
    """Factory for creating test tracker instances."""
    
    @staticmethod
    def create(tracker, target_date=None, **kwargs):
        from core.models import TrackerInstance
        
        if target_date is None:
            target_date = date.today()
        
        defaults = {
            'instance_id': str(uuid.uuid4()),
            'tracking_date': target_date,
            'period_start': target_date,
            'period_end': target_date,
            'status': 'active'
        }
        defaults.update(kwargs)
        return TrackerInstance.objects.create(tracker=tracker, **defaults)


class TaskInstanceFactory:
    """Factory for creating test task instances."""
    
    @staticmethod
    def create(instance, template, **kwargs):
        from core.models import TaskInstance
        
        defaults = {
            'task_instance_id': str(uuid.uuid4()),
            'status': 'TODO'
        }
        defaults.update(kwargs)
        return TaskInstance.objects.create(
            tracker_instance=instance,
            template=template,
            **defaults
        )


class GoalFactory:
    """Factory for creating test goals."""
    
    @staticmethod
    def create(user, tracker=None, **kwargs):
        from core.models import Goal
        
        defaults = {
            'goal_id': str(uuid.uuid4()),
            'title': f'Test Goal {uuid.uuid4().hex[:6]}',
            'target_value': 21,
            'current_value': 0,
            'progress': 0,
            'unit': 'days',
            'status': 'active'
        }
        defaults.update(kwargs)
        return Goal.objects.create(user=user, tracker=tracker, **defaults)


class TagFactory:
    """Factory for creating test tags."""
    
    @staticmethod
    def create(user, **kwargs):
        from core.models import Tag
        
        defaults = {
            'tag_id': str(uuid.uuid4()),
            'name': f'Tag {uuid.uuid4().hex[:6]}',
            'color': '#3B82F6',
            'icon': 'tag'
        }
        defaults.update(kwargs)
        return Tag.objects.create(user=user, **defaults)


class ShareLinkFactory:
    """Factory for creating test share links."""
    
    @staticmethod
    def create(tracker, user, **kwargs):
        from core.models import ShareLink
        import secrets
        
        # Map permission_level to permission if provided
        if 'permission_level' in kwargs:
            kwargs['permission'] = kwargs.pop('permission_level')
        
        defaults = {
            'token': secrets.token_urlsafe(32),
            'permission': 'view',
            'is_active': True
        }
        defaults.update(kwargs)
        return ShareLink.objects.create(
            tracker=tracker,
            created_by=user,
            **defaults
        )


class DayNoteFactory:
    """Factory for creating test day notes."""
    
    @staticmethod
    def create(tracker, target_date=None, **kwargs):
        from core.models import DayNote
        
        if target_date is None:
            target_date = date.today()
        
        defaults = {
            'date': target_date,
            'content': 'Test note content'
        }
        defaults.update(kwargs)
        return DayNote.objects.create(tracker=tracker, **defaults)


# Helper functions for complex test scenarios

def create_tracker_with_tasks(user, task_count=3, **tracker_kwargs):
    """Create a tracker with multiple task templates."""
    tracker = TrackerFactory.create(user, **tracker_kwargs)
    templates = [
        TemplateFactory.create(tracker, description=f'Task {i+1}')
        for i in range(task_count)
    ]
    return tracker, templates


def create_completed_day(user, target_date=None, completion_rate=1.0):
    """Create a tracker instance with tasks at specified completion rate."""
    if target_date is None:
        target_date = date.today()
    
    tracker, templates = create_tracker_with_tasks(user, task_count=4)
    instance = InstanceFactory.create(tracker, target_date)
    
    tasks = []
    completed_count = int(len(templates) * completion_rate)
    
    for i, template in enumerate(templates):
        status = 'DONE' if i < completed_count else 'TODO'
        task = TaskInstanceFactory.create(instance, template, status=status)
        tasks.append(task)
    
    return tracker, instance, tasks


def create_streak_data(user, streak_days=7, completion_rate=1.0):
    """Create data for streak testing."""
    tracker, templates = create_tracker_with_tasks(user, task_count=2)
    
    today = date.today()
    instances = []
    
    for i in range(streak_days):
        day = today - timedelta(days=i)
        instance = InstanceFactory.create(tracker, day)
        
        for template in templates:
            status = 'DONE' if i == 0 or completion_rate >= 1.0 else 'TODO'
            TaskInstanceFactory.create(instance, template, status=status)
        
        instances.append(instance)
    
    return tracker, instances
