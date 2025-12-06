"""
View Service

Centralizes presentation logic for the Single Page Application (SPA) views.
Handles data formatting, UI constants, and view-specific data aggregation.
"""
from typing import Dict, List, Any
from django.urls import reverse

# UI Constants
UI_COLORS = {
    'success': '#34C759', # iOS Green
    'warning': '#FF9500', # iOS Orange
    'error': '#FF3B30',   # iOS Red
    'info': '#007AFF',    # iOS Blue
    'neutral': '#8E8E93', # iOS Gray
}

TOUCH_TARGET_MIN_SIZE = 44  # Apple HIG

class ViewService:
    """
    Service for formatting data for views.
    """
    
    @staticmethod
    def format_task_for_list(task, tracker) -> Dict[str, Any]:
        """
        Format a task object for the task list view, including iOS swipe actions.
        
        Args:
            task: TaskInstance object
            tracker: TrackerDefinition object
            
        Returns:
            Dict containing formatted task data
        """
        # Handle attribute access safely (in case it's still a dict, though it shouldn't be)
        if isinstance(task, dict):
            status = task.get('status')
            task_id = task.get('task_instance_id')
            # Assuming template is flattened or we don't have it in dict mode easily
            # This is a fallback
            description = task.get('description', '')
            category = task.get('category', '')
            time_of_day = task.get('time_of_day', 'anytime')
            weight = task.get('weight', 1)
        else:
            status = task.status
            task_id = task.task_instance_id
            description = task.template.description if task.template else ''
            category = task.template.category if task.template and hasattr(task.template, 'category') else ''
            time_of_day = task.template.time_of_day if task.template and hasattr(task.template, 'time_of_day') else 'anytime'
            weight = task.template.weight if task.template and hasattr(task.template, 'weight') else 1
            
        if not status:
            return None
            
        return {
            'task_instance_id': task_id,
            'status': status,
            'description': description,
            'category': category,
            'time_of_day': time_of_day,
            'weight': weight,
            'tracker_name': tracker.name,
            'tracker_id': str(tracker.tracker_id),
            'tracker_color': getattr(tracker, 'color', 'neutral'), # potential future field
            
            # Original object for template compatibility if needed
            '_obj': task,
            
            # iOS swipe actions
            'ios_swipe_actions': ViewService._get_swipe_actions(task_id, status),
            
            # Context menu
            'ios_context_menu': [
                {'title': 'Edit', 'icon': 'pencil', 'action': 'edit'},
                {'title': 'Add Note', 'icon': 'note.text', 'action': 'note'},
                {'title': 'Move to Tomorrow', 'icon': 'arrow.forward', 'action': 'reschedule'},
                {'title': 'Delete', 'icon': 'trash', 'destructive': True, 'action': 'delete'}
            ]
        }
    
    @staticmethod
    def _get_swipe_actions(task_id: str, status: str) -> Dict[str, List[Dict]]:
        """
        Generate iOS swipe actions based on status.
        """
        actions = {
            'leading': [],
            'trailing': []
        }
        
        # Leading Action: Complete (if not done)
        if status != 'DONE':
            actions['leading'].append({
                'id': 'complete',
                'title': '✓',
                'style': 'normal',
                'backgroundColor': UI_COLORS['success'],
                'endpoint': f'/api/task/{task_id}/toggle/',
                'haptic': 'success',
                'minWidth': TOUCH_TARGET_MIN_SIZE
            })
            
        # Trailing Actions: Skip, Delete
        actions['trailing'].append({
            'id': 'skip',
            'title': 'Skip',
            'style': 'normal',
            'backgroundColor': UI_COLORS['warning'],
            'endpoint': f'/api/task/{task_id}/status/',
            'payload': {'status': 'SKIPPED'},
            'haptic': 'warning',
            'minWidth': 60
        })
        
        actions['trailing'].append({
            'id': 'delete',
            'title': 'Delete',
            'style': 'destructive',
            'backgroundColor': UI_COLORS['error'],
            'endpoint': f'/api/task/{task_id}/delete/',
            'confirmRequired': True,
            'haptic': 'error',
            'minWidth': 70
        })
        
        return actions
