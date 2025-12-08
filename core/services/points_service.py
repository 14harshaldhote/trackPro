"""
Points Calculation Service

Central service for all points and goal progress calculations.
Ensures consistent calculation logic across the entire application.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.db.models import Sum, Count, Q
from django.utils import timezone
import pytz

from core.models import (
    TrackerDefinition, TaskTemplate, TaskInstance, 
    TrackerInstance, UserPreferences
)


class PointsCalculationService:
    """
    Service for calculating tracker progress based on points.
    
    Responsibilities:
    - Calculate current points based on completed tasks with include_in_goal=True
    - Handle daily/weekly goal periods with proper timezone support
    - Provide progress percentage and goal status
    - Refresh progress after task completion or toggle changes
    """
    
    def __init__(self, tracker_id: str, user, target_date: date = None):
        """
        Initialize the points calculation service.
        
        Args:
            tracker_id: UUID of the tracker
            user: Django User object
            target_date: Date to calculate for (defaults to today in user's timezone)
        """
        self.tracker_id = tracker_id
        self.user = user
        self._tracker = None
        self._user_timezone = None
        
        # Get user timezone
        self._user_timezone = self._get_user_timezone()
        
        # Set target date in user's timezone
        if target_date is None:
            self.target_date = self._get_today_in_user_tz()
        else:
            self.target_date = target_date
    
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
    
    @property
    def tracker(self) -> TrackerDefinition:
        """Lazy load the tracker."""
        if self._tracker is None:
            self._tracker = TrackerDefinition.objects.get(
                tracker_id=self.tracker_id,
                user=self.user
            )
        return self._tracker
    
    def get_period_date_range(self, period: str = None) -> Tuple[date, date]:
        """
        Get the date range for the goal period.
        
        Args:
            period: 'daily', 'weekly', or 'custom' (uses tracker's goal_period if None)
        
        Returns:
            Tuple of (start_date, end_date) inclusive
        """
        if period is None:
            period = self.tracker.goal_period
        
        if period == 'daily':
            return (self.target_date, self.target_date)
        
        elif period == 'weekly':
            # Calculate week start based on tracker's goal_start_day
            start_day = self.tracker.goal_start_day  # 0=Monday, 6=Sunday
            current_weekday = self.target_date.weekday()
            
            # Calculate days since week start
            days_since_start = (current_weekday - start_day) % 7
            week_start = self.target_date - timedelta(days=days_since_start)
            week_end = week_start + timedelta(days=6)
            
            return (week_start, week_end)
        
        else:  # 'custom' or unknown - default to daily
            return (self.target_date, self.target_date)
    
    def get_applicable_tasks(self, include_only_completed: bool = True) -> List[TaskInstance]:
        """
        Get tasks that are applicable for goal calculation.
        
        Filters:
        1. Belongs to this tracker
        2. Within current period (daily/weekly)
        3. include_in_goal = True on the template
        4. status = DONE (if include_only_completed is True)
        
        Returns:
            List of TaskInstance objects
        """
        start_date, end_date = self.get_period_date_range()
        
        # Build query
        query = TaskInstance.objects.filter(
            tracker_instance__tracker=self.tracker,
            tracker_instance__period_start__lte=end_date,
            tracker_instance__period_end__gte=start_date,
            template__include_in_goal=True,
            deleted_at__isnull=True
        ).select_related('template', 'tracker_instance')
        
        if include_only_completed:
            query = query.filter(status='DONE')
        
        return list(query)
    
    def calculate_current_points(self) -> Dict:
        """
        Calculate current points for the tracker's goal.
        
        Returns:
            {
                'current_points': int,
                'target_points': int,
                'progress_percentage': float (0-100+),
                'goal_met': bool,
                'period': str,
                'period_start': str (ISO date),
                'period_end': str (ISO date),
                'task_breakdown': {
                    'total_tasks': int,
                    'completed_tasks': int,
                    'included_tasks': int,
                    'excluded_tasks': int,
                    'completed_included': int
                }
            }
        """
        target_points = self.tracker.target_points
        period = self.tracker.goal_period
        start_date, end_date = self.get_period_date_range()
        
        # Get all task instances in period for this tracker
        all_tasks_in_period = TaskInstance.objects.filter(
            tracker_instance__tracker=self.tracker,
            tracker_instance__period_start__lte=end_date,
            tracker_instance__period_end__gte=start_date,
            deleted_at__isnull=True
        ).select_related('template')
        
        # Calculate task breakdown
        total_tasks = all_tasks_in_period.count()
        completed_tasks = all_tasks_in_period.filter(status='DONE').count()
        
        # Filter for included tasks
        included_tasks_query = all_tasks_in_period.filter(template__include_in_goal=True)
        included_tasks = included_tasks_query.count()
        excluded_tasks = total_tasks - included_tasks
        
        # Calculate points from completed included tasks
        completed_included = included_tasks_query.filter(status='DONE')
        completed_included_count = completed_included.count()
        
        # Sum points from completed included tasks
        current_points = 0
        for task in completed_included.select_related('template'):
            current_points += task.template.points
        
        # Calculate progress percentage
        if target_points > 0:
            progress_percentage = (current_points / target_points) * 100
        else:
            # No target set - show 0% or could show based on task completion
            progress_percentage = 0.0
        
        # Determine if goal is met
        goal_met = current_points >= target_points if target_points > 0 else False
        
        return {
            'current_points': current_points,
            'target_points': target_points,
            'progress_percentage': round(progress_percentage, 1),
            'goal_met': goal_met,
            'period': period,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'task_breakdown': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'included_tasks': included_tasks,
                'excluded_tasks': excluded_tasks,
                'completed_included': completed_included_count
            }
        }
    
    def get_task_points_breakdown(self) -> List[Dict]:
        """
        Get detailed breakdown of each task's contribution to points.
        
        Returns list of dicts with task info and points status.
        """
        start_date, end_date = self.get_period_date_range()
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker=self.tracker,
            tracker_instance__period_start__lte=end_date,
            tracker_instance__period_end__gte=start_date,
            deleted_at__isnull=True
        ).select_related('template').order_by('-template__weight')
        
        breakdown = []
        for task in tasks:
            points_earned = task.template.points if (
                task.status == 'DONE' and task.template.include_in_goal
            ) else 0
            
            breakdown.append({
                'task_id': task.task_instance_id,
                'description': task.template.description,
                'points_possible': task.template.points,
                'points_earned': points_earned,
                'include_in_goal': task.template.include_in_goal,
                'status': task.status,
                'is_completed': task.status == 'DONE'
            })
        
        return breakdown


# =============================================================================
# Convenience Functions
# =============================================================================

def calculate_tracker_progress(tracker_id: str, user) -> Dict:
    """
    Calculate progress for a tracker.
    
    Args:
        tracker_id: Tracker UUID
        user: Django User object
        
    Returns:
        Progress dict from PointsCalculationService.calculate_current_points()
    """
    service = PointsCalculationService(tracker_id, user)
    return service.calculate_current_points()


def toggle_task_goal_inclusion(template_id: str, user, include: bool) -> Dict:
    """
    Toggle whether a task template's points count towards the goal.
    
    Args:
        template_id: TaskTemplate UUID
        user: Django User object
        include: True to include, False to exclude
        
    Returns:
        {
            'template_id': str,
            'include_in_goal': bool,
            'tracker_progress': dict (updated progress)
        }
    """
    try:
        template = TaskTemplate.objects.select_related('tracker').get(
            template_id=template_id,
            tracker__user=user
        )
    except TaskTemplate.DoesNotExist:
        raise ValueError(f"TaskTemplate {template_id} not found")
    
    # Update the template
    template.include_in_goal = include
    template.save(update_fields=['include_in_goal'])
    
    # Recalculate tracker progress
    service = PointsCalculationService(str(template.tracker.tracker_id), user)
    new_progress = service.calculate_current_points()
    
    return {
        'template_id': template_id,
        'include_in_goal': include,
        'tracker_progress': new_progress
    }


def update_task_points(template_id: str, user, points: int) -> Dict:
    """
    Update the points value for a task template.
    
    Args:
        template_id: TaskTemplate UUID
        user: Django User object
        points: New points value (must be >= 0)
        
    Returns:
        {
            'template_id': str,
            'points': int,
            'tracker_progress': dict (updated progress)
        }
    """
    if points < 0:
        raise ValueError("Points must be 0 or greater")
    
    try:
        template = TaskTemplate.objects.select_related('tracker').get(
            template_id=template_id,
            tracker__user=user
        )
    except TaskTemplate.DoesNotExist:
        raise ValueError(f"TaskTemplate {template_id} not found")
    
    # Update points
    template.points = points
    template.save(update_fields=['points'])
    
    # Recalculate tracker progress
    service = PointsCalculationService(str(template.tracker.tracker_id), user)
    new_progress = service.calculate_current_points()
    
    return {
        'template_id': template_id,
        'points': points,
        'tracker_progress': new_progress
    }


def set_tracker_goal(tracker_id: str, user, target_points: int, goal_period: str = None) -> Dict:
    """
    Set or update the goal for a tracker.
    
    Args:
        tracker_id: Tracker UUID
        user: Django User object
        target_points: Target points (0 to clear goal)
        goal_period: 'daily', 'weekly', or 'custom' (optional)
        
    Returns:
        {
            'tracker_id': str,
            'target_points': int,
            'goal_period': str,
            'progress': dict (current progress)
        }
    """
    if target_points < 0:
        raise ValueError("Target points must be 0 or greater")
    
    try:
        tracker = TrackerDefinition.objects.get(tracker_id=tracker_id, user=user)
    except TrackerDefinition.DoesNotExist:
        raise ValueError(f"Tracker {tracker_id} not found")
    
    # Update goal settings
    tracker.target_points = target_points
    if goal_period and goal_period in ['daily', 'weekly', 'custom']:
        tracker.goal_period = goal_period
    
    tracker.save(update_fields=['target_points', 'goal_period', 'updated_at'])
    
    # Calculate current progress
    service = PointsCalculationService(tracker_id, user)
    progress = service.calculate_current_points()
    
    return {
        'tracker_id': tracker_id,
        'target_points': tracker.target_points,
        'goal_period': tracker.goal_period,
        'progress': progress
    }
