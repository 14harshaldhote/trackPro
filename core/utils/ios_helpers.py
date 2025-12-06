"""
iOS-Specific Helper Functions
Formats data for iOS Widgets and Siri Shortcuts
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any


def format_widget_timeline_entry(
    tasks: List[Dict],
    date: datetime,
    relevance_score: float = 1.0
) -> Dict:
    """
    Format widget timeline entry for iOS WidgetKit.
    
    Timeline entries tell iOS when to refresh the widget.
    
    Args:
        tasks: List of task dictionaries
        date: Date for this timeline entry
        relevance_score: Relevance score for widget intelligence (0-1)
    
    Returns:
        Widget timeline entry dict
    """
    completed = sum(1 for t in tasks if t.get('status') == 'DONE')
    total = len(tasks)
    
    return {
        'date': date.isoformat(),
        'relevance': relevance_score,
        'content': {
            'total_tasks': total,
            'completed_tasks': completed,
            'pending_tasks': total - completed,
            'completion_rate': int(completed / total * 100) if total > 0 else 0,
            'tasks': tasks[:5],  # Widget shows max 5 tasks
            'display_date': date.strftime('%A, %b %d'),
        }
    }


def format_siri_response(
    spoken_text: str,
    display_title: str = None,
    display_subtitle: str = None,
    success: bool = True
) -> Dict:
    """
    Format response for Siri Shortcuts.
    
    Args:
        spoken_text: Text Siri will speak
        display_title: Title shown on screen
        display_subtitle: Subtitle shown on screen
        success: Whether operation succeeded
    
    Returns:
        Siri-compatible response dict
    """
    return {
        'success': success,
        'spoken_response': spoken_text,
        'display': {
            'title': display_title or spoken_text,
            'subtitle': display_subtitle or ''
        },
        'timestamp': datetime.now().isoformat()
    }


def create_widget_snapshot(user, widget_type: str = 'small') -> Dict:
    """
    Create widget snapshot data for different widget sizes.
    
    Args:
        user: Django User instance
        widget_type: 'small', 'medium', or 'large'
    
    Returns:
        Widget snapshot data
    """
    from core.models import TaskInstance
    from datetime import date
    
    today = date.today()
    
    # Get today's tasks
    tasks = TaskInstance.objects.filter(
        tracker_instance__tracker__user=user,
        tracker_instance__period_start__lte=today,
        tracker_instance__period_end__gte=today
    ).select_related('template', 'tracker_instance__tracker')[:10]
    
    task_data = [{
        'id': str(t.task_instance_id),
        'description': t.template.description,
        'status': t.status,
        'tracker': t.tracker_instance.tracker.name,
        'category': t.template.category or '',
        'completed': t.status == 'DONE'
    } for t in tasks]
    
    completed = sum(1 for t in task_data if t['completed'])
    total = len(task_data)
    
    # Base data for all widget sizes
    snapshot = {
        'widget_type': widget_type,
        'total_tasks': total,
        'completed_tasks': completed,
        'completion_percentage': int(completed / total * 100) if total > 0 else 0,
        'generated_at': datetime.now().isoformat()
    }
    
    # Size-specific data
    if widget_type == 'small':
        # Small widget: Just progress ring
        snapshot['display'] = 'progress_ring'
        snapshot['tasks'] = []
        
    elif widget_type == 'medium':
        # Medium widget: Progress + 3 tasks
        snapshot['display'] = 'progress_and_tasks'
        snapshot['tasks'] = task_data[:3]
        
    else:  # large
        # Large widget: Progress + 6 tasks + streak
        snapshot['display'] = 'full'
        snapshot['tasks'] = task_data[:6]
        
        # Add streak data for large widget
        from core.services.analytics_service import compute_user_streak
        snapshot['streak_days'] = compute_user_streak(user)
    
    return snapshot


def format_siri_task_list(tasks: List[Dict]) -> str:
    """
    Format task list for Siri spoken response.
    
    Args:
        tasks: List of task dictionaries
    
    Returns:
        Natural language task list
    """
    if not tasks:
        return "You have no tasks to complete today."
    
    pending = [t for t in tasks if t.get('status') != 'DONE']
    completed = [t for t in tasks if t.get('status') == 'DONE']
    
    response_parts = []
    
    if completed:
        response_parts.append(f"You've completed {len(completed)} task{'s' if len(completed) != 1 else ''}.")
    
    if pending:
        if len(pending) <= 3:
            # List specific tasks
            task_names = [t.get('description', 'unnamed task') for t in pending[:3]]
            tasks_str = ', '.join(task_names[:-1]) + (', and ' if len(task_names) > 2 else ' and ') + task_names[-1] if len(task_names) > 1 else task_names[0]
            response_parts.append(f"You have {len(pending)} pending task{'s' if len(pending) != 1 else ''}: {tasks_str}.")
        else:
            # Just give count
            response_parts.append(f"You have {len(pending)} pending tasks.")
    else:
        response_parts.append("All tasks are complete! Great work!")
    
    return ' '.join(response_parts)
