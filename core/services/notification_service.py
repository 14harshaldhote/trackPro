"""
Notification Service

Handle all notification logic including daily reminders, summaries, and achievements.
"""
from datetime import datetime, time, timedelta, date
from django.utils import timezone
from django.db.models import Count, Q
from core.models import (
    Notification, UserPreferences, TrackerDefinition, 
    TrackerInstance, TaskInstance
)

class NotificationService:
    """Handle all notification logic."""
    
    DEFAULT_REMINDER_TIME = time(8, 0)  # 8 AM
    
    @staticmethod
    def get_reminder_time(user_id: int) -> time:
        try:
            prefs = UserPreferences.objects.get(user_id=user_id)
            return prefs.daily_reminder_time or NotificationService.DEFAULT_REMINDER_TIME
        except UserPreferences.DoesNotExist:
            return NotificationService.DEFAULT_REMINDER_TIME

    @staticmethod
    def send_daily_reminder(user_id: int) -> Notification | None:
        """
        Send morning reminder with today's tasks summary.
        Called by scheduled task at user's preferred time.
        """
        try:
            prefs = UserPreferences.objects.get(user_id=user_id)
            if not prefs.daily_reminder_enabled:
                return None
        except UserPreferences.DoesNotExist:
            pass # Continue with defaults or return None? Plan says defaults.
            # actually code says return None if prefs not exist in line 801 of plan, 
            # but line 340 says defaults. I will use safer approach: defaults if no prefs logic is fuzzy, 
            # but usually if user has no prefs we assume defaults enabled? 
            # Let's align with plan code which checked DoesNotExist.
            # But wait, plan code block 800: returns None if DoesNotExist.
            # I will follow that for now, assuming users must have prefs created.
            return None
        
        today = timezone.now().date()
        
        # Count today's tasks across all active trackers
        task_count = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracker__status='active',
            tracker_instance__tracking_date=today,
            status='TODO',
            deleted_at__isnull=True
        ).count()
        
        if task_count == 0:
            return None
        
        return Notification.objects.create(
            user_id=user_id,
            type='reminder',
            title='🌅 Good Morning!',
            message=f'You have {task_count} tasks scheduled for today.',
            link='/today'
        )
    
    @staticmethod
    def send_evening_summary(user_id: int) -> Notification | None:
        """Send evening progress summary."""
        today = timezone.now().date()
        
        # Get today's stats
        stats = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date=today,
            deleted_at__isnull=True
        ).aggregate(
            total=Count('task_instance_id'),
            done=Count('task_instance_id', filter=Q(status='DONE')),
            remaining=Count('task_instance_id', filter=Q(status='TODO'))
        )
        
        if stats['total'] == 0:
            return None
        
        completion_pct = int((stats['done'] / stats['total']) * 100)
        
        if stats['remaining'] > 0:
            message = f"You're {stats['remaining']} tasks away from completing today! ({completion_pct}% done)"
        else:
            message = f"🎉 Amazing! You completed all {stats['total']} tasks today!"
        
        return Notification.objects.create(
            user_id=user_id,
            type='info',
            title='📊 Daily Progress',
            message=message,
            link='/today'
        )
    
    @staticmethod
    def send_streak_alert(user_id: int, tracker_name: str, streak_count: int):
        """Notify user about streak milestones."""
        milestones = [7, 14, 21, 30, 60, 90, 100, 180, 365]
        
        if streak_count in milestones:
            return Notification.objects.create(
                user_id=user_id,
                type='achievement',
                title='🔥 Streak Milestone!',
                message=f'You\'ve maintained {tracker_name} for {streak_count} days!',
                link='/streaks'
            )
        return None
    
    @staticmethod
    def send_goal_progress_update(user_id: int, goal_title: str, progress: float):
        """Notify at progress milestones (25%, 50%, 75%, 100%)."""
        milestones = [25, 50, 75, 100]
        
        # Find which milestone was just crossed
        for milestone in milestones:
            if abs(progress - milestone) < 1:  # Within 1% of milestone
                emoji_map = {25: '🚀', 50: '🎯', 75: '💪', 100: '🎉'}
                return Notification.objects.create(
                    user_id=user_id,
                    type='success' if milestone == 100 else 'info',
                    title=f'{emoji_map.get(milestone, "📈")} Goal Progress!',
                    message=f'You\'re {milestone}% through "{goal_title}"!',
                    link='/goals'
                )
        return None
    
    @staticmethod
    def mark_all_read(user_id: int) -> int:
        """Mark all user notifications as read. Returns count updated."""
        return Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).update(is_read=True)
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Get count of unread notifications."""
        return Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).count()
