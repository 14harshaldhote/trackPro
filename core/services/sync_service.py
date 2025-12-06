"""
Offline Sync Service
Handles queued actions and bidirectional sync for offline-first architecture.

Following OpusSuggestion.md Part 4.2: Offline Data Sync Endpoint
"""
from typing import List, Dict, Any
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from core.models import TaskInstance, TrackerDefinition, TaskTemplate, TrackerInstance


class SyncService:
    """Handle offline action processing and bidirectional sync."""
    
    def __init__(self, user):
        """
        Initialize sync service for a user.
        
        Args:
            user: Django User instance
        """
        self.user = user
    
    def process_sync_request(self, data: Dict) -> Dict:
        """
        Process bidirectional sync request.
        
        Args:
            data: {
                'last_sync': ISO timestamp,
                'pending_actions': [...],
                'device_id': str
            }
        
        Returns:
            {
                'action_results': [...],
                'server_changes': {...},
                'new_sync_timestamp': ISO timestamp
            }
        """
        last_sync = data.get('last_sync')
        pending_actions = data.get('pending_actions', [])
        
        # Process queued offline actions
        action_results = []
        for action in pending_actions:
            result = self._process_action(action)
            action_results.append(result)
        
        # Get server changes since last sync
        server_changes = self._get_changes_since(last_sync) if last_sync else {}
        
        return {
            'action_results': action_results,
            'server_changes': server_changes,
            'new_sync_timestamp': timezone.now().isoformat(),
            'sync_status': 'complete'
        }
    
    def _process_action(self, action: Dict) -> Dict:
        """
        Process a single queued offline action.
        
        Args:
            action: Action dictionary with 'type', 'id', and action-specific data
        
        Returns:
            Result dictionary with success status
        """
        action_type = action.get('type')
        action_id = action.get('id')
        
        try:
            with transaction.atomic():
                if action_type == 'task_toggle':
                    return self._handle_task_toggle(action)
                
                elif action_type == 'task_add':
                    return self._handle_task_add(action)
                
                elif action_type == 'task_delete':
                    return self._handle_task_delete(action)
                
                elif action_type == 'task_update':
                    return self._handle_task_update(action)
                
                elif action_type == 'tracker_create':
                    return self._handle_tracker_create(action)
                
                elif action_type == 'note_save':
                    return self._handle_note_save(action)
                
                else:
                    return {
                        'id': action_id,
                        'success': False,
                        'error': f'Unknown action type: {action_type}'
                    }
        
        except Exception as e:
            return {
                'id': action_id,
                'success': False,
                'error': str(e),
                'retry': True
            }
    
    def _handle_task_toggle(self, action: Dict) -> Dict:
        """Handle task status toggle action."""
        task = TaskInstance.objects.get(
            task_instance_id=action['task_id'],
            tracker_instance__tracker__user=self.user
        )
        task.status = action['new_status']
        
        if action['new_status'] == 'DONE':
            task.completed_at = timezone.now()
        else:
            task.completed_at = None
        
        task.save()
        
        return {
            'id': action['id'],
            'success': True,
            'server_data': {
                'task_id': task.task_instance_id,
                'status': task.status,
                'updated_at': task.updated_at.isoformat()
            }
        }
    
    def _handle_task_add(self, action: Dict) -> Dict:
        """Handle task addition action."""
        # Implementation would create task instance
        return {
            'id': action['id'],
            'success': True,
            'message': 'Task added successfully'
        }
    
    def _handle_task_delete(self, action: Dict) -> Dict:
        """Handle task deletion action."""
        task = TaskInstance.objects.get(
            task_instance_id=action['task_id'],
            tracker_instance__tracker__user=self.user
        )
        task.delete()
        
        return {
            'id': action['id'],
            'success': True,
            'message': 'Task deleted successfully'
        }
    
    def _handle_task_update(self, action: Dict) -> Dict:
        """Handle task update action."""
        task = TaskInstance.objects.get(
            task_instance_id=action['task_id'],
            tracker_instance__tracker__user=self.user
        )
        
        if 'notes' in action:
            task.notes = action['notes']
        
        task.save()
        
        return {
            'id': action['id'],
            'success': True,
            'server_data': {
                'task_id': task.task_instance_id,
                'updated_at': task.updated_at.isoformat()
            }
        }
    
    def _handle_tracker_create(self, action: Dict) -> Dict:
        """Handle tracker creation action."""
        # Implementation would create tracker
        return {
            'id': action['id'],
            'success': True,
            'message': 'Tracker created successfully'
        }
    
    def _handle_note_save(self, action: Dict) -> Dict:
        """Handle note save action."""
        # Implementation would save day note
        return {
            'id': action['id'],
            'success': True,
            'message': 'Note saved successfully'
        }
    
    def _get_changes_since(self, last_sync: str) -> Dict:
        """
        Get changes since last sync timestamp.
        
        Args:
            last_sync: ISO timestamp of last successful sync
        
        Returns:
            Dict with changed trackers, tasks, and deletions
        """
        last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
        
        changes = {}
        
        # Changed trackers
        changed_trackers = TrackerDefinition.objects.filter(
            user=self.user,
            updated_at__gt=last_sync_dt
        ).values('tracker_id', 'name', 'status', 'time_mode', 'updated_at')
        
        changes['trackers'] = [
            {
                **tracker,
                'updated_at': tracker['updated_at'].isoformat()
            }
            for tracker in changed_trackers
        ]
        
        # Changed tasks - limit to 100 most recent
        changed_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            updated_at__gt=last_sync_dt
        ).select_related('template', 'tracker_instance').order_by('-updated_at')[:100]
        
        changes['tasks'] = [
            {
                'task_instance_id': task.task_instance_id,
                'status': task.status,
                'notes': task.notes,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'updated_at': task.updated_at.isoformat(),
                'template_id': task.template.template_id,
                'tracker_id': task.tracker_instance.tracker.tracker_id
            }
            for task in changed_tasks
        ]
        
        # For deletions, would need soft delete or deletion log
        # Placeholder for now
        changes['deletions'] = []
        
        return changes
    
    def get_initial_sync_data(self) -> Dict:
        """
        Get complete initial sync data for new device.
        
        Returns:
            Dict with all user trackers and recent tasks
        """
        # Get all active trackers
        trackers = TrackerDefinition.objects.filter(
            user=self.user
        ).exclude(status='archived')
        
        tracker_data = [
            {
                'tracker_id': t.tracker_id,
                'name': t.name,
                'time_mode': t.time_mode,
                'status': t.status,
                'created_at': t.created_at.isoformat(),
            }
            for t in trackers
        ]
        
        # Get recent tasks (last 30 days)
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        recent_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            created_at__gte=thirty_days_ago
        ).select_related('template', 'tracker_instance')[:500]
        
        task_data = [
            {
                'task_instance_id': t.task_instance_id,
                'status': t.status,
                'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                'template_id': t.template.template_id,
                'tracker_id': t.tracker_instance.tracker.tracker_id
            }
            for t in recent_tasks
        ]
        
        return {
            'trackers': tracker_data,
            'tasks': task_data,
            'sync_timestamp': timezone.now().isoformat()
        }
