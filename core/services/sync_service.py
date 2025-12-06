"""
Sync Service - Bidirectional sync for offline-first mobile apps.

Handles queued actions from offline app and returns server changes.
Enables seamless offline/online transitions for iOS and web.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from core.models import (
    TrackerDefinition, 
    TrackerInstance, 
    TaskInstance, 
    TaskTemplate,
    DayNote
)


class SyncService:
    """
    Handle offline action processing and bidirectional sync.
    
    Design:
    - Client sends pending actions from offline queue
    - Server processes actions and returns results
    - Server sends changes since last sync timestamp
    - Conflict resolution: Last-write-wins with timestamps
    
    Usage:
        sync_service = SyncService(request.user)
        result = sync_service.process_sync_request({
            'last_sync': '2025-12-06T10:00:00Z',
            'pending_actions': [...],
            'device_id': 'ios-abc123'
        })
    """
    
    def __init__(self, user):
        self.user = user
    
    def process_sync_request(self, data: Dict) -> Dict:
        """
        Process bidirectional sync request.
        
        Args:
            data: {
                'last_sync': ISO timestamp (optional),
                'pending_actions': List of offline actions,
                'device_id': Device identifier
            }
        
        Returns:
            {
                'action_results': Results for each pending action,
                'server_changes': Changes since last sync,
                'new_sync_timestamp': Timestamp for next sync,
                'sync_status': 'complete' or 'partial'
            }
        """
        last_sync = data.get('last_sync')
        pending_actions = data.get('pending_actions', [])
        device_id = data.get('device_id', 'unknown')
        
        # Process queued actions
        action_results = []
        for action in pending_actions:
            result = self._process_action(action)
            action_results.append(result)
        
        # Get server changes since last sync
        changes = self._get_changes_since(last_sync) if last_sync else self._get_full_sync()
        
        return {
            'action_results': action_results,
            'server_changes': changes,
            'new_sync_timestamp': timezone.now().isoformat(),
            'sync_status': 'complete',
            'device_id': device_id
        }
    
    def _process_action(self, action: Dict) -> Dict:
        """
        Process a single queued action from the client.
        
        Supported action types:
        - task_toggle: Toggle task status
        - task_status: Set specific status
        - task_notes: Update task notes
        - day_note: Save day note
        """
        action_type = action.get('type')
        action_id = action.get('id', 'unknown')
        client_timestamp = action.get('timestamp')
        
        try:
            with transaction.atomic():
                if action_type == 'task_toggle':
                    return self._action_task_toggle(action_id, action)
                
                elif action_type == 'task_status':
                    return self._action_task_status(action_id, action)
                
                elif action_type == 'task_notes':
                    return self._action_task_notes(action_id, action)
                
                elif action_type == 'day_note':
                    return self._action_day_note(action_id, action)
                
                else:
                    return {
                        'id': action_id,
                        'success': False,
                        'error': f'Unknown action type: {action_type}',
                        'retry': False
                    }
                
        except Exception as e:
            return {
                'id': action_id,
                'success': False,
                'error': str(e),
                'retry': True
            }
    
    def _action_task_toggle(self, action_id: str, action: Dict) -> Dict:
        """Toggle task status"""
        task_id = action.get('task_id')
        expected_old = action.get('old_status')
        new_status = action.get('new_status')
        
        task = TaskInstance.objects.get(
            task_instance_id=task_id,
            tracker_instance__tracker__user=self.user
        )
        
        # Conflict check: If server status differs from expected old status
        if expected_old and task.status != expected_old:
            return {
                'id': action_id,
                'success': False,
                'conflict': True,
                'server_status': task.status,
                'client_expected': expected_old,
                'error': 'Conflict: Status was changed on server',
                'retry': False
            }
        
        task.status = new_status
        task.completed_at = timezone.now() if new_status == 'DONE' else None
        task.save()
        
        return {
            'id': action_id,
            'success': True,
            'task_id': task_id,
            'new_status': new_status,
            'server_timestamp': task.updated_at.isoformat()
        }
    
    def _action_task_status(self, action_id: str, action: Dict) -> Dict:
        """Set specific task status"""
        task_id = action.get('task_id')
        status = action.get('status')
        notes = action.get('notes', '')
        
        task = TaskInstance.objects.get(
            task_instance_id=task_id,
            tracker_instance__tracker__user=self.user
        )
        
        task.status = status
        task.notes = notes or task.notes
        task.completed_at = timezone.now() if status == 'DONE' else None
        task.save()
        
        return {
            'id': action_id,
            'success': True,
            'task_id': task_id,
            'server_timestamp': task.updated_at.isoformat()
        }
    
    def _action_task_notes(self, action_id: str, action: Dict) -> Dict:
        """Update task notes"""
        task_id = action.get('task_id')
        notes = action.get('notes', '')
        
        task = TaskInstance.objects.get(
            task_instance_id=task_id,
            tracker_instance__tracker__user=self.user
        )
        
        task.notes = notes
        task.save()
        
        return {
            'id': action_id,
            'success': True,
            'task_id': task_id,
            'server_timestamp': task.updated_at.isoformat()
        }
    
    def _action_day_note(self, action_id: str, action: Dict) -> Dict:
        """Save day note"""
        from core.models import DayNote
        
        note_date_str = action.get('date')
        content = action.get('content', '')
        
        note_date = datetime.fromisoformat(note_date_str).date()
        
        note, created = DayNote.objects.update_or_create(
            user=self.user,
            date=note_date,
            defaults={'content': content}
        )
        
        return {
            'id': action_id,
            'success': True,
            'note_id': str(note.pk),
            'created': created
        }
    
    def _get_changes_since(self, last_sync: str) -> Dict:
        """
        Get all changes since last sync timestamp.
        Returns lightweight data for efficient sync.
        """
        try:
            last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
        except ValueError:
            # Fallback: try without timezone
            last_sync_dt = datetime.fromisoformat(last_sync)
        
        # Get updated trackers (not deleted)
        updated_trackers = TrackerDefinition.objects.filter(
            user=self.user,
            updated_at__gt=last_sync_dt,
            deleted_at__isnull=True
        ).values(
            'tracker_id', 'name', 'status', 'time_mode', 'updated_at'
        )[:50]
        
        # Get deleted trackers
        deleted_trackers = TrackerDefinition.objects.filter(
            user=self.user,
            deleted_at__gt=last_sync_dt
        ).values('tracker_id', 'deleted_at')
        
        # Get updated tasks (not deleted)
        updated_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            updated_at__gt=last_sync_dt,
            deleted_at__isnull=True
        ).select_related(
            'template', 'tracker_instance__tracker'
        ).values(
            'task_instance_id', 
            'status', 
            'notes',
            'completed_at',
            'updated_at',
            'tracker_instance__tracker__tracker_id'
        )[:100]
        
        # Get deleted tasks
        deleted_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            deleted_at__gt=last_sync_dt
        ).values('task_instance_id', 'deleted_at')
        
        # Get updated day notes
        updated_notes = DayNote.objects.filter(
            user=self.user,
            updated_at__gt=last_sync_dt,
            deleted_at__isnull=True
        ).values(
            'date', 'content', 'updated_at'
        )[:30]
        
        return {
            'trackers': {
                'updated': list(updated_trackers),
                'deleted': list(deleted_trackers)
            },
            'tasks': {
                'updated': list(updated_tasks),
                'deleted': list(deleted_tasks)
            },
            'day_notes': {
                'updated': list(updated_notes)
            },
            'has_more': False
        }
    
    def _get_full_sync(self) -> Dict:
        """
        Get full data for initial sync (no last_sync timestamp).
        Returns minimal data to bootstrap the client.
        """
        # Get all active trackers (exclude deleted)
        trackers = TrackerDefinition.objects.filter(
            user=self.user,
            deleted_at__isnull=True
        ).exclude(
            status='archived'
        ).values(
            'tracker_id', 'name', 'description', 'status', 'time_mode', 'updated_at'
        )
        
        # Get recent tasks (last 14 days, exclude deleted)
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=14)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__period_start__gte=cutoff,
            deleted_at__isnull=True
        ).select_related(
            'template', 'tracker_instance__tracker'
        ).values(
            'task_instance_id',
            'status',
            'notes',
            'completed_at',
            'updated_at',
            'tracker_instance__tracker__tracker_id',
            'template__description',
            'template__category',
            'template__time_of_day',
            'template__weight'
        )[:500]
        
        return {
            'trackers': {
                'updated': list(trackers),
                'deleted': []
            },
            'tasks': {
                'updated': list(tasks),
                'deleted': []
            },
            'day_notes': {
                'updated': []
            },
            'is_full_sync': True,
            'has_more': False
        }


# Convenience function for API use
def process_sync(user, data: Dict) -> Dict:
    """Process sync request for given user"""
    return SyncService(user).process_sync_request(data)
