"""
Activity Replay Service - V2.0 Feature

Enables users to view historical states of their trackers using the audit trail.
Supports timeline visualization and "what changed when" queries.

Written from scratch for Version 2.0
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from core.models import (
    TrackerDefinition, TrackerInstance, TaskInstance, TaskTemplate,
    DayNote, Goal
)
import logging

logger = logging.getLogger(__name__)


class ActivityReplayService:
    """
    Service for viewing historical states and activity timeline.
    
    Uses the HistoricalRecords from django-simple-history to
    reconstruct past states of entities.
    """
    
    @staticmethod
    def get_activity_timeline(
        user_id: int,
        start_date: date = None,
        end_date: date = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get a chronological timeline of all user activity.
        
        Args:
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum events to return
            
        Returns:
            List of activity events in reverse chronological order
        """
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        events = []
        
        # 1. Task status changes
        task_changes = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            updated_at__date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).select_related(
            'template', 'tracker_instance', 'tracker_instance__tracker'
        ).order_by('-updated_at')[:limit]
        
        for task in task_changes:
            events.append({
                'type': 'task_update',
                'timestamp': task.updated_at.isoformat(),
                'entity_type': 'task',
                'entity_id': str(task.task_instance_id),
                'description': f"Task '{task.template.description}' marked as {task.status}",
                'data': {
                    'task_id': str(task.task_instance_id),
                    'tracker_name': task.tracker_instance.tracker.name,
                    'status': task.status,
                    'date': task.tracker_instance.tracking_date.isoformat()
                }
            })
        
        # 2. Tracker creations/updates
        trackers = TrackerDefinition.objects.filter(
            user_id=user_id,
            updated_at__date__range=(start_date, end_date)
        ).order_by('-updated_at')[:limit]
        
        for tracker in trackers:
            event_type = 'tracker_created' if tracker.created_at == tracker.updated_at else 'tracker_updated'
            events.append({
                'type': event_type,
                'timestamp': tracker.updated_at.isoformat(),
                'entity_type': 'tracker',
                'entity_id': str(tracker.tracker_id),
                'description': f"Tracker '{tracker.name}' {'created' if event_type == 'tracker_created' else 'updated'}",
                'data': {
                    'tracker_id': str(tracker.tracker_id),
                    'name': tracker.name,
                    'status': tracker.status
                }
            })
        
        # 3. Notes added
        notes = DayNote.objects.filter(
            tracker__user_id=user_id,
            updated_at__date__range=(start_date, end_date)
        ).select_related('tracker').order_by('-updated_at')[:limit]
        
        for note in notes:
            events.append({
                'type': 'note_added',
                'timestamp': note.updated_at.isoformat(),
                'entity_type': 'note',
                'entity_id': str(note.note_id),
                'description': f"Note added to '{note.tracker.name}' for {note.date}",
                'data': {
                    'tracker_name': note.tracker.name,
                    'date': note.date.isoformat(),
                    'preview': note.content[:100] if note.content else ''
                }
            })
        
        # 4. Goal updates
        goals = Goal.objects.filter(
            user_id=user_id,
            updated_at__date__range=(start_date, end_date)
        ).order_by('-updated_at')[:limit]
        
        for goal in goals:
            events.append({
                'type': 'goal_progress',
                'timestamp': goal.updated_at.isoformat(),
                'entity_type': 'goal',
                'entity_id': str(goal.goal_id),
                'description': f"Goal '{goal.title}' progress: {goal.progress}%",
                'data': {
                    'goal_id': str(goal.goal_id),
                    'title': goal.title,
                    'progress': goal.progress,
                    'status': goal.status
                }
            })
        
        # Sort all events by timestamp
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return events[:limit]
    
    @staticmethod
    def get_day_snapshot(user_id: int, target_date: date) -> Dict:
        """
        Get a complete snapshot of user's state on a specific date.
        
        Args:
            user_id: User ID
            target_date: Date to snapshot
            
        Returns:
            Dict with all tracker/task states for that date
        """
        snapshot = {
            'date': target_date.isoformat(),
            'trackers': [],
            'totals': {
                'total_tasks': 0,
                'done': 0,
                'missed': 0,
                'in_progress': 0,
                'todo': 0
            },
            'notes': [],
            'goals': []
        }
        
        # Get all instances for this date
        instances = TrackerInstance.objects.filter(
            tracker__user_id=user_id,
            tracking_date=target_date,
            deleted_at__isnull=True
        ).select_related('tracker').prefetch_related('tasks__template')
        
        for instance in instances:
            tasks_data = []
            for task in instance.tasks.filter(deleted_at__isnull=True):
                tasks_data.append({
                    'task_id': str(task.task_instance_id),
                    'description': task.template.description,
                    'status': task.status,
                    'completed_at': task.first_completed_at.isoformat() if task.first_completed_at else None,
                    'notes': task.notes
                })
                
                snapshot['totals']['total_tasks'] += 1
                status_key = task.status.lower()
                if status_key in snapshot['totals']:
                    snapshot['totals'][status_key] += 1
            
            snapshot['trackers'].append({
                'tracker_id': str(instance.tracker.tracker_id),
                'name': instance.tracker.name,
                'instance_id': str(instance.instance_id),
                'status': instance.status,
                'tasks': tasks_data,
                'completion_rate': (
                    len([t for t in tasks_data if t['status'] == 'DONE']) / len(tasks_data) * 100
                ) if tasks_data else 0
            })
        
        # Get notes for this date
        notes = DayNote.objects.filter(
            tracker__user_id=user_id,
            date=target_date
        ).select_related('tracker')
        
        for note in notes:
            snapshot['notes'].append({
                'tracker_name': note.tracker.name,
                'content': note.content,
                'sentiment': note.sentiment_score
            })
        
        # Get active goals on this date
        goals = Goal.objects.filter(
            user_id=user_id,
            status__in=['active', 'achieved'],
            deleted_at__isnull=True
        ).filter(
            Q(target_date__isnull=True) | Q(target_date__gte=target_date)
        )
        
        for goal in goals:
            snapshot['goals'].append({
                'goal_id': str(goal.goal_id),
                'title': goal.title,
                'progress': goal.progress,
                'status': goal.status
            })
        
        # Calculate overall completion rate
        total = snapshot['totals']['total_tasks']
        done = snapshot['totals']['done']
        snapshot['totals']['completion_rate'] = round((done / total * 100), 1) if total > 0 else 0
        
        return snapshot
    
    @staticmethod
    def compare_periods(
        user_id: int,
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date
    ) -> Dict:
        """
        Compare user performance between two periods.
        
        Args:
            user_id: User ID
            period1_*: First period dates
            period2_*: Second period dates
            
        Returns:
            Comparison analysis
        """
        def get_period_stats(start: date, end: date) -> Dict:
            tasks = TaskInstance.objects.filter(
                tracker_instance__tracker__user_id=user_id,
                tracker_instance__tracking_date__range=(start, end),
                deleted_at__isnull=True
            )
            
            total = tasks.count()
            done = tasks.filter(status='DONE').count()
            missed = tasks.filter(status='MISSED').count()
            
            return {
                'start': start.isoformat(),
                'end': end.isoformat(),
                'days': (end - start).days + 1,
                'total_tasks': total,
                'completed': done,
                'missed': missed,
                'completion_rate': round((done / total * 100), 1) if total > 0 else 0,
                'miss_rate': round((missed / total * 100), 1) if total > 0 else 0
            }
        
        period1 = get_period_stats(period1_start, period1_end)
        period2 = get_period_stats(period2_start, period2_end)
        
        # Calculate changes
        rate_change = period2['completion_rate'] - period1['completion_rate']
        
        return {
            'period1': period1,
            'period2': period2,
            'changes': {
                'completion_rate_change': round(rate_change, 1),
                'direction': 'improved' if rate_change > 0 else 'declined' if rate_change < 0 else 'stable',
                'tasks_change': period2['total_tasks'] - period1['total_tasks']
            },
            'insights': ActivityReplayService._generate_comparison_insights(period1, period2, rate_change)
        }
    
    @staticmethod
    def _generate_comparison_insights(period1: Dict, period2: Dict, rate_change: float) -> List[str]:
        """Generate insights from period comparison."""
        insights = []
        
        if rate_change > 10:
            insights.append(f"Great improvement! Your completion rate increased by {rate_change:.1f}%")
        elif rate_change < -10:
            insights.append(f"Your completion rate dropped by {abs(rate_change):.1f}%. Consider reviewing your schedule.")
        
        if period2['miss_rate'] < period1['miss_rate']:
            drop = period1['miss_rate'] - period2['miss_rate']
            insights.append(f"You reduced missed tasks by {drop:.1f}%")
        
        if period2['total_tasks'] > period1['total_tasks'] * 1.2:
            insights.append("You tracked significantly more tasks. Be mindful of burnout.")
        
        return insights
    
    @staticmethod
    def get_weekly_comparison(user_id: int, weeks_back: int = 4) -> List[Dict]:
        """
        Get week-over-week comparison for recent weeks.
        
        Args:
            user_id: User ID
            weeks_back: Number of weeks to compare
            
        Returns:
            List of weekly summaries for comparison
        """
        today = date.today()
        weeks = []
        
        for i in range(weeks_back):
            week_end = today - timedelta(days=today.weekday() + (i * 7))
            week_start = week_end - timedelta(days=6)
            
            tasks = TaskInstance.objects.filter(
                tracker_instance__tracker__user_id=user_id,
                tracker_instance__tracking_date__range=(week_start, week_end),
                deleted_at__isnull=True
            )
            
            total = tasks.count()
            done = tasks.filter(status='DONE').count()
            
            weeks.append({
                'week_number': i + 1,
                'week_label': f"Week of {week_start.strftime('%b %d')}",
                'start': week_start.isoformat(),
                'end': week_end.isoformat(),
                'total_tasks': total,
                'completed': done,
                'completion_rate': round((done / total * 100), 1) if total > 0 else 0
            })
        
        # Calculate trend
        if len(weeks) >= 2:
            recent_rate = weeks[0]['completion_rate']
            older_rate = weeks[-1]['completion_rate']
            
            trend = 'improving' if recent_rate > older_rate else 'declining' if recent_rate < older_rate else 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'weeks': weeks,
            'trend': trend,
            'trend_percentage': weeks[0]['completion_rate'] - weeks[-1]['completion_rate'] if len(weeks) >= 2 else 0
        }
    
    @staticmethod
    def get_historical_record(entity_type: str, entity_id: str) -> List[Dict]:
        """
        Get the full history of changes for an entity.
        
        Uses django-simple-history HistoricalRecords if available.
        
        Args:
            entity_type: Type of entity (tracker, task, goal)
            entity_id: Entity ID
            
        Returns:
            List of historical changes
        """
        history = []
        
        try:
            if entity_type == 'tracker':
                tracker = TrackerDefinition.objects.get(tracker_id=entity_id)
                if hasattr(tracker, 'history'):
                    for record in tracker.history.all()[:20]:
                        history.append({
                            'timestamp': record.history_date.isoformat(),
                            'change_type': record.history_type,
                            'changed_by': str(record.history_user_id) if record.history_user_id else None,
                            'data': {
                                'name': record.name,
                                'status': record.status,
                                'time_mode': record.time_mode
                            }
                        })
            
            elif entity_type == 'goal':
                goal = Goal.objects.get(goal_id=entity_id)
                if hasattr(goal, 'history'):
                    for record in goal.history.all()[:20]:
                        history.append({
                            'timestamp': record.history_date.isoformat(),
                            'change_type': record.history_type,
                            'data': {
                                'title': record.title,
                                'progress': record.progress,
                                'status': record.status,
                                'current_value': record.current_value,
                                'target_value': record.target_value
                            }
                        })
        
        except Exception as e:
            logger.warning(f"Could not fetch history for {entity_type}:{entity_id}: {e}")
        
        return history
