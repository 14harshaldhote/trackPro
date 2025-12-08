"""
Dashboard Service

Central service for dashboard data aggregation.
Provides all data needed for the main dashboard view including:
- Today's trackers with progress
- Active goals summary
- Streaks and achievements
- Recent activity
- Quick stats
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.db.models import Sum, Count, Avg, Q, F
from django.utils import timezone
from django.contrib.auth.models import User
import pytz

from core.models import (
    TrackerDefinition, TaskTemplate, TaskInstance, 
    TrackerInstance, UserPreferences, Goal, Notification,
    DayNote
)


class DashboardService:
    """
    Service for aggregating dashboard data.
    
    Provides a single entry point for fetching all dashboard data
    efficiently with proper caching considerations.
    """
    
    def __init__(self, user: User, target_date: date = None):
        """
        Initialize dashboard service.
        
        Args:
            user: Django User object
            target_date: Date to show dashboard for (defaults to today)
        """
        self.user = user
        self._user_timezone = self._get_user_timezone()
        self.target_date = target_date or self._get_today_in_user_tz()
    
    def _get_user_timezone(self) -> pytz.timezone:
        """Get user's timezone from preferences."""
        try:
            prefs = UserPreferences.objects.get(user=self.user)
            return pytz.timezone(prefs.timezone)
        except (UserPreferences.DoesNotExist, pytz.UnknownTimeZoneError):
            return pytz.UTC
    
    def _get_today_in_user_tz(self) -> date:
        """Get today's date in user's timezone."""
        now_utc = timezone.now()
        now_local = now_utc.astimezone(self._user_timezone)
        return now_local.date()
    
    def get_full_dashboard(self) -> Dict:
        """
        Get complete dashboard data in one call.
        
        Returns comprehensive dashboard data structure.
        """
        return {
            'date': self.target_date.isoformat(),
            'greeting': self._get_greeting(),
            'trackers': self.get_trackers_summary(),
            'today_stats': self.get_today_stats(),
            'goals_progress': self.get_goals_progress(),
            'streaks': self.get_streaks(),
            'recent_activity': self.get_recent_activity(),
            'notifications_count': self.get_unread_notifications_count(),
            'quick_actions': self.get_quick_actions(),
        }
    
    def _get_greeting(self) -> str:
        """Get time-appropriate greeting."""
        now = datetime.now(self._user_timezone)
        hour = now.hour
        
        if hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        elif hour < 21:
            return "Good evening"
        else:
            return "Good night"
    
    def get_trackers_summary(self) -> List[Dict]:
        """
        Get summary of all active trackers for today.
        
        Returns list of tracker summaries with tasks and progress.
        """
        trackers = TrackerDefinition.objects.filter(
            user=self.user,
            status='active',
            deleted_at__isnull=True
        ).prefetch_related('templates').order_by('-created_at')
        
        summaries = []
        for tracker in trackers:
            # Get today's tracker instance if exists
            try:
                tracker_instance = TrackerInstance.objects.get(
                    tracker=tracker,
                    period_start__lte=self.target_date,
                    period_end__gte=self.target_date
                )
                
                # Get tasks for this instance
                tasks = TaskInstance.objects.filter(
                    tracker_instance=tracker_instance,
                    deleted_at__isnull=True
                ).select_related('template').order_by('-template__weight')
                
                total_tasks = tasks.count()
                completed_tasks = tasks.filter(status='DONE').count()
                
                # Calculate points
                total_points = 0
                earned_points = 0
                for task in tasks:
                    if hasattr(task.template, 'points'):
                        if getattr(task.template, 'include_in_goal', True):
                            total_points += task.template.points
                            if task.status == 'DONE':
                                earned_points += task.template.points
                
                task_list = [{
                    'task_id': str(task.task_instance_id),
                    'template_id': str(task.template.template_id),
                    'description': task.template.description,
                    'status': task.status,
                    'is_completed': task.status == 'DONE',
                    'points': getattr(task.template, 'points', 1),
                    'include_in_goal': getattr(task.template, 'include_in_goal', True),
                    'time_of_day': task.template.time_of_day,
                    'notes': task.notes or '',
                } for task in tasks]
                
            except TrackerInstance.DoesNotExist:
                total_tasks = 0
                completed_tasks = 0
                total_points = 0
                earned_points = 0
                task_list = []
            
            # Calculate completion percentage
            completion_pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Calculate points progress
            target_points = getattr(tracker, 'target_points', 0)
            points_progress = (earned_points / target_points * 100) if target_points > 0 else 0
            
            summaries.append({
                'tracker_id': str(tracker.tracker_id),
                'name': tracker.name,
                'description': tracker.description,
                'time_mode': tracker.time_mode,
                'status': tracker.status,
                
                # Task stats
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_percentage': round(completion_pct, 1),
                
                # Point-based goal
                'target_points': target_points,
                'current_points': earned_points,
                'total_possible_points': total_points,
                'points_progress': round(points_progress, 1),
                'goal_period': getattr(tracker, 'goal_period', 'daily'),
                'goal_met': earned_points >= target_points if target_points > 0 else False,
                
                # Tasks
                'tasks': task_list,
            })
        
        return summaries
    
    def get_today_stats(self) -> Dict:
        """
        Get aggregated stats for today.
        """
        # Get all task instances for today
        tasks_today = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__period_start__lte=self.target_date,
            tracker_instance__period_end__gte=self.target_date,
            deleted_at__isnull=True
        ).select_related('template')
        
        total = tasks_today.count()
        done = tasks_today.filter(status='DONE').count()
        in_progress = tasks_today.filter(status='IN_PROGRESS').count()
        todo = tasks_today.filter(status='TODO').count()
        missed = tasks_today.filter(status='MISSED').count()
        
        # Points calculation
        total_points = 0
        earned_points = 0
        for task in tasks_today:
            points = getattr(task.template, 'points', 1)
            include = getattr(task.template, 'include_in_goal', True)
            if include:
                total_points += points
                if task.status == 'DONE':
                    earned_points += points
        
        completion_rate = (done / total * 100) if total > 0 else 0
        
        return {
            'date': self.target_date.isoformat(),
            'total_tasks': total,
            'completed': done,
            'in_progress': in_progress,
            'todo': todo,
            'missed': missed,
            'completion_rate': round(completion_rate, 1),
            'total_points': total_points,
            'earned_points': earned_points,
            'points_percentage': round((earned_points / total_points * 100) if total_points > 0 else 0, 1),
        }
    
    def get_goals_progress(self) -> List[Dict]:
        """
        Get progress for all active goals.
        """
        goals = Goal.objects.filter(
            user=self.user,
            status='active',
            deleted_at__isnull=True
        ).select_related('tracker').order_by('-priority', '-created_at')[:5]
        
        goal_list = []
        for goal in goals:
            # Calculate days remaining
            if goal.target_date:
                days_left = (goal.target_date - self.target_date).days
            else:
                days_left = None
            
            goal_list.append({
                'goal_id': str(goal.goal_id),
                'title': goal.title,
                'icon': goal.icon,
                'goal_type': goal.goal_type,
                'target_value': goal.target_value,
                'current_value': goal.current_value,
                'progress': round(goal.progress, 1),
                'status': goal.status,
                'priority': goal.priority,
                'days_left': days_left,
                'target_date': goal.target_date.isoformat() if goal.target_date else None,
                'tracker_name': goal.tracker.name if goal.tracker else None,
            })
        
        return goal_list
    
    def get_streaks(self) -> Dict:
        """
        Calculate current streaks.
        """
        # Get last 30 days of task completion data
        end_date = self.target_date
        start_date = end_date - timedelta(days=30)
        
        daily_completions = {}
        
        task_instances = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__period_start__gte=start_date,
            tracker_instance__period_end__lte=end_date,
            deleted_at__isnull=True
        ).values(
            'tracker_instance__period_start'
        ).annotate(
            total=Count('task_instance_id'),
            completed=Count('task_instance_id', filter=Q(status='DONE'))
        )
        
        for entry in task_instances:
            day = entry['tracker_instance__period_start']
            if day:
                total = entry['total']
                completed = entry['completed']
                if total > 0:
                    rate = completed / total
                    daily_completions[day] = rate >= 0.8  # 80% threshold
        
        # Calculate current streak
        current_streak = 0
        check_date = self.target_date
        
        while check_date >= start_date:
            if daily_completions.get(check_date, False):
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        # Calculate longest streak (in the 30 day window)
        longest_streak = 0
        temp_streak = 0
        
        for i in range(31):
            day = start_date + timedelta(days=i)
            if daily_completions.get(day, False):
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 0
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'streak_threshold': 80,  # Percentage needed for streak day
            'last_30_days': sum(1 for v in daily_completions.values() if v),
        }
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """
        Get recent task completions and changes.
        """
        recent_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            status='DONE',
            completed_at__isnull=False,
            deleted_at__isnull=True
        ).select_related(
            'template', 
            'tracker_instance__tracker'
        ).order_by('-completed_at')[:limit]
        
        activities = []
        for task in recent_tasks:
            activities.append({
                'type': 'task_completed',
                'task_id': str(task.task_instance_id),
                'description': task.template.description,
                'tracker_name': task.tracker_instance.tracker.name,
                'tracker_id': str(task.tracker_instance.tracker.tracker_id),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'points': getattr(task.template, 'points', 1),
            })
        
        return activities
    
    def get_unread_notifications_count(self) -> int:
        """Get count of unread notifications."""
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
    
    def get_quick_actions(self) -> List[Dict]:
        """
        Get suggested quick actions for the user.
        """
        actions = []
        
        # Check for incomplete high-priority tasks
        pending_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__period_start__lte=self.target_date,
            tracker_instance__period_end__gte=self.target_date,
            status__in=['TODO', 'IN_PROGRESS'],
            deleted_at__isnull=True
        ).select_related('template', 'tracker_instance__tracker').order_by(
            '-template__weight'
        )[:3]
        
        for task in pending_tasks:
            actions.append({
                'type': 'complete_task',
                'label': f"Complete: {task.template.description}",
                'task_id': str(task.task_instance_id),
                'tracker_name': task.tracker_instance.tracker.name,
                'points': getattr(task.template, 'points', 1),
            })
        
        # Check if day note exists for today
        has_note = DayNote.objects.filter(
            tracker__user=self.user,
            date=self.target_date
        ).exists()
        
        if not has_note:
            actions.append({
                'type': 'add_note',
                'label': "Add a note for today",
            })
        
        return actions
    
    def get_week_overview(self) -> Dict:
        """
        Get overview for the current week.
        """
        # Calculate week boundaries
        today = self.target_date
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        # Get day-by-day data
        days = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            
            tasks = TaskInstance.objects.filter(
                tracker_instance__tracker__user=self.user,
                tracker_instance__period_start__lte=day,
                tracker_instance__period_end__gte=day,
                deleted_at__isnull=True
            )
            
            total = tasks.count()
            done = tasks.filter(status='DONE').count()
            rate = (done / total * 100) if total > 0 else 0
            
            days.append({
                'date': day.isoformat(),
                'day_name': day.strftime('%a'),
                'total_tasks': total,
                'completed_tasks': done,
                'completion_rate': round(rate, 1),
                'is_today': day == today,
                'is_future': day > today,
            })
        
        # Week totals
        week_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__period_start__gte=week_start,
            tracker_instance__period_end__lte=week_end,
            deleted_at__isnull=True
        )
        
        total_week = week_tasks.count()
        done_week = week_tasks.filter(status='DONE').count()
        
        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'days': days,
            'week_total': total_week,
            'week_completed': done_week,
            'week_rate': round((done_week / total_week * 100) if total_week > 0 else 0, 1),
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def get_dashboard_data(user, target_date: date = None) -> Dict:
    """
    Get full dashboard data for a user.
    """
    service = DashboardService(user, target_date)
    return service.get_full_dashboard()


def get_today_summary(user) -> Dict:
    """
    Get just today's summary stats.
    """
    service = DashboardService(user)
    return service.get_today_stats()


def get_trackers_with_tasks(user, target_date: date = None) -> List[Dict]:
    """
    Get trackers with their tasks for a specific date.
    """
    service = DashboardService(user, target_date)
    return service.get_trackers_summary()
