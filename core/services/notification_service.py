"""
Notification Service
Unified notification system for push, in-app, and badge notifications.

Following OpusSuggestion.md Part 5.1: Notification System Backend
"""
from typing import Optional, Dict
from django.utils import timezone
from core.models import Notification, UserPreferences


class NotificationService:
    """Unified notification service for push and in-app notifications."""
    
    def __init__(self, user):
        """
        Initialize notification service for a user.
        
        Args:
            user: Django User instance
        """
        self.user = user
        self.prefs, _ = UserPreferences.objects.get_or_create(user=user)
    
    def create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = 'info',
        link: str = '',
        send_push: bool = True
    ) -> Notification:
        """
        Create notification with optional push.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error, reminder, achievement)
            link: Optional link to related content
            send_push: Whether to send push notification
        
        Returns:
            Created Notification instance
        """
        notif = Notification.objects.create(
            user=self.user,
            type=notification_type,
            title=title,
            message=message,
            link=link
        )
        
        if send_push and self.prefs.push_enabled:
            self._send_push(notif)
        
        return notif
    
    def _send_push(self, notification: Notification) -> Dict:
        """
        Send iOS APNS / Web Push notification.
        
        Args:
            notification: Notification instance
        
        Returns:
            Push payload (for logging/debugging)
        """
        badge_count = self.get_badge_count()
        
        # iOS APNS payload format
        payload = {
            'aps': {
                'alert': {
                    'title': notification.title,
                    'body': notification.message
                },
                'badge': badge_count,
                'sound': self._get_sound(notification.type),
                'category': notification.type,
                'thread-id': 'tracker-app'
            },
            'notification_id': notification.notification_id,
            'link': notification.link,
            'type': notification.type
        }
        
        # TODO: Integrate with APNS/FCM service
        # For now, just return payload for debugging
        return payload
    
    def _get_sound(self, notification_type: str) -> str:
        """
        Get sound effect for notification type.
        
        Args:
            notification_type: Type of notification
        
        Returns:
            Sound file name
        """
        sounds = {
            'achievement': 'celebration.aiff',
            'reminder': 'reminder.aiff',
            'warning': 'alert.aiff',
            'error': 'error.aiff',
            'success': 'complete.aiff'
        }
        return sounds.get(notification_type, 'default')
    
    def get_badge_count(self) -> int:
        """
        Get unread notification count for badge.
        
        Returns:
            Number of unread notifications
        """
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
    
    def mark_as_read(self, notification_ids: Optional[list] = None) -> int:
        """
        Mark notifications as read.
        
        Args:
            notification_ids: List of notification IDs to mark as read,
                            or None to mark all as read
        
        Returns:
            Number of notifications marked as read
        """
        if notification_ids:
            count = Notification.objects.filter(
                user=self.user,
                notification_id__in=notification_ids
            ).update(is_read=True)
        else:
            count = Notification.objects.filter(
                user=self.user,
                is_read=False
            ).update(is_read=True)
        
        return count
    
    def get_recent_notifications(self, limit: int = 50) -> list:
        """
        Get recent notifications with metadata.
        
        Args:
            limit: Maximum number of notifications to return
        
        Returns:
            List of notification dicts
        """
        notifications = Notification.objects.filter(
            user=self.user
        ).order_by('-created_at')[:limit]
        
        return [
            {
                'id': n.notification_id,
                'title': n.title,
                'message': n.message,
                'type': n.type,
                'is_read': n.is_read,
                'link': n.link,
                'created_at': n.created_at.isoformat(),
                'time_ago': self._time_ago(n.created_at)
            }
            for n in notifications
        ]
    
    def _time_ago(self, dt) -> str:
        """
        Get human-readable time ago string.
        
        Args:
            dt: Datetime to compare
        
        Returns:
            Human-readable time string
        """
        now = timezone.now()
        diff = now - dt
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f'{minutes}m ago'
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f'{hours}h ago'
        elif seconds < 604800:
            days = int(seconds / 86400)
            return f'{days}d ago'
        else:
            weeks = int(seconds / 604800)
            return f'{weeks}w ago'


# ============================================================================
# Convenience Functions for Common Notifications
# ============================================================================

def notify_streak_at_risk(user, streak_count: int):
    """
    Send streak at risk notification.
    
    Args:
        user: Django User instance
        streak_count: Current streak count
    """
    NotificationService(user).create_notification(
        title=f"⚠️ {streak_count}-Day Streak at Risk!",
        message="Complete at least one task today to maintain your streak.",
        notification_type='warning',
        link='/today/'
    )


def notify_streak_milestone(user, streak_count: int):
    """
    Send streak milestone notification.
    
    Args:
        user: Django User instance
        streak_count: Milestone streak count
    """
    NotificationService(user).create_notification(
        title=f"🎉 {streak_count}-Day Streak!",
        message=f"Amazing! You've maintained your streak for {streak_count} days.",
        notification_type='achievement',
        link='/analytics/'
    )


def notify_daily_reminder(user):
    """
    Send daily reminder notification.
    
    Args:
        user: Django User instance
    """
    NotificationService(user).create_notification(
        title="📋 Daily Reminder",
        message="Don't forget to check your tasks for today!",
        notification_type='reminder',
        link='/today/'
    )


def notify_goal_progress(user, goal_title: str, progress: float):
    """
    Send goal progress notification.
    
    Args:
        user: Django User instance
        goal_title: Title of the goal
        progress: Progress percentage
    """
    NotificationService(user).create_notification(
        title=f"🎯 Goal Progress: {goal_title}",
        message=f"You're {int(progress)}% of the way there!",
        notification_type='info',
        link='/goals/'
    )


def notify_weekly_review(user):
    """
    Send weekly review notification.
    
    Args:
        user: Django User instance
    """
    NotificationService(user).create_notification(
        title="📊 Weekly Review Available",
        message="Check out your weekly progress and insights!",
        notification_type='info',
        link='/analytics/week/'
    )
