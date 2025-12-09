"""
Tracker Management Service

Centralizes business logic for TrackerDefinition operations.
"""
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
import uuid

from core.models import TrackerDefinition, TaskTemplate, TrackerInstance, TaskInstance
from core.helpers.cache_helpers import invalidate_tracker_cache
from core.exceptions import TrackerNotFoundError, ValidationError as AppValidationError
from core.serializers import TrackerCreateSerializer

class TrackerService:
    """
    Service for managing TrackerDefinition operations.
    """

    def create_tracker(self, user, data: Dict) -> Dict:
        """
        Create a new tracker with initial templates.
        
        Args:
            user: User object
            data: Request data (name, description, time_mode, tasks)
            
        Returns:
            Created tracker dict
        """
        # Validate using serializer
        serializer = TrackerCreateSerializer(data=data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = next(iter(errors.items()))
            raise AppValidationError(first_error[0], str(first_error[1][0]))
            
        validated_data = serializer.validated_data
        
        name = validated_data['name']
        description = validated_data.get('description', '')
        time_mode = validated_data.get('time_mode', 'daily')
        
        with transaction.atomic():
            tracker = TrackerDefinition.objects.create(
                user=user,
                tracker_id=str(uuid.uuid4()),
                name=name,
                description=description,
                time_mode=time_mode,
                status='active'
            )
            
            # Create initial templates
            tasks = data.get('tasks', [])
            for i, task_desc in enumerate(tasks):
                if task_desc.strip():
                    TaskTemplate.objects.create(
                        template_id=str(uuid.uuid4()),
                        tracker=tracker,
                        description=task_desc,
                        is_recurring=True,
                        weight=len(tasks) - i,
                        time_of_day='anytime'
                    )
        
        return {
            'id': str(tracker.tracker_id),
            'name': tracker.name,
            'tracker_id': str(tracker.tracker_id) # API consistency
        }

    def update_tracker(self, tracker_id: str, user, data: Dict) -> Dict:
        """
        Update tracker details.
        
        Args:
            tracker_id: Tracker ID
            user: User object
            data: Updates (name, description, time_mode, status)
            
        Returns:
            Updated tracker dict
        """
        try:
            tracker = TrackerDefinition.objects.get(tracker_id=tracker_id, user=user)
        except TrackerDefinition.DoesNotExist:
            raise TrackerNotFoundError(tracker_id)
            
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                raise AppValidationError('name', 'Name is required')
            tracker.name = name
            
        if 'description' in data:
            tracker.description = data['description']
            
        if 'time_mode' in data:
            tracker.time_mode = data['time_mode']
            
        if 'status' in data:
            tracker.status = data['status']
            
        tracker.save()
        invalidate_tracker_cache(tracker_id)
        
        return {
            'id': str(tracker.tracker_id),
            'name': tracker.name,
            'status': tracker.status
        }
        
    def delete_tracker(self, tracker_id: str, user) -> Dict:
        """
        Soft delete a tracker.
        
        Args:
            tracker_id: Tracker ID
            user: User object
        """
        try:
            tracker = TrackerDefinition.objects.get(tracker_id=tracker_id, user=user)
        except TrackerDefinition.DoesNotExist:
            raise TrackerNotFoundError(tracker_id)
            
        name = tracker.name
        # SoftDeleteModel method
        tracker.soft_delete()
        invalidate_tracker_cache(tracker_id)
        
        return {'tracker_id': tracker_id, 'name': name}

    def reorder_tasks(self, tracker_id: str, user, task_order: List[str]) -> bool:
        """
        Update task order.
        Currently a placeholder as TaskTemplate doesn't have explicit order field exposed this way,
        but implementation would go here.
        """
        # Checks existence
        if not TrackerDefinition.objects.filter(tracker_id=tracker_id, user=user).exists():
            raise TrackerNotFoundError(tracker_id)
            
        # Implementation depends on data model supporting arbitrary ordering
        return True

    def get_active_trackers(self, user, order_by='created_at'):
        """
        Get all active, non-deleted trackers for a user.
        
        Args:
            user: User object
            order_by: Field to order by
            
        Returns:
            QuerySet of TrackerDefinition objects
        """
        return TrackerDefinition.objects.filter(
            user=user, 
            deleted_at__isnull=True
        ).exclude(
            status='archived'
        ).order_by(order_by)

    def get_archived_trackers(self, user):
        """
        Get archived trackers for a user.
        """
        return TrackerDefinition.objects.filter(
            user=user, 
            status='archived'
        ).order_by('-updated_at')

    def get_tracker_by_id(self, tracker_id: str, user):
        """
        Get a specific tracker by ID for a user.
        Raises TrackerDefinition.DoesNotExist if not found.
        """
        try:
            return TrackerDefinition.objects.get(
                tracker_id=tracker_id, 
                user=user, 
                deleted_at__isnull=True
            )
        except TrackerDefinition.DoesNotExist:
            raise TrackerNotFoundError(tracker_id)

    def change_time_mode(self, tracker: TrackerDefinition, new_mode: str) -> Dict:
        """
        Safely change tracker's time mode.
        
        Strategy:
        1. Mark existing instances as 'legacy' (don't delete)
        2. Change time_mode
        3. Future instances will use new mode
        """
        from datetime import date
        
        with transaction.atomic():
            # Mark all future instances as legacy
            future_instances = TrackerInstance.objects.filter(
                tracker=tracker,
                tracking_date__gt=date.today()
            )
            future_instances.update(status='legacy')
            
            # Store mode change in metadata for history (if supported) or just change it
            old_mode = tracker.time_mode
            tracker.time_mode = new_mode
            tracker.save()
            
            invalidate_tracker_cache(str(tracker.tracker_id))
            
            return {
                'success': True,
                'old_mode': old_mode,
                'new_mode': new_mode,
                'legacy_instances': future_instances.count()
            }

    def restore_tracker(self, tracker_id: str, user) -> Dict:
        """
        Restore soft-deleted tracker with conflict handling.
        """
        try:
            tracker = TrackerDefinition.objects.get(
                tracker_id=tracker_id,
                user=user
            )
        except TrackerDefinition.DoesNotExist:
            raise TrackerNotFoundError(tracker_id)
            
        if tracker.deleted_at is None:
            return {'error': 'Tracker is not deleted'}
        
        # Check for name conflict
        conflict = TrackerDefinition.objects.filter(
            user=user,
            name=tracker.name,
            deleted_at__isnull=True
        ).exists()
        
        if conflict:
            tracker.name = f"{tracker.name} (Restored)"
        
        tracker.restore()
        
        # Also restore children (cascading restore logic if needed)
        # Assuming simple restore for now, or we define restore logic on models
        TrackerInstance.objects.filter(tracker=tracker).update(deleted_at=None)
        TaskInstance.objects.filter(tracker_instance__tracker=tracker).update(deleted_at=None)
        
        invalidate_tracker_cache(tracker_id)
        
        return {'success': True, 'renamed': conflict, 'new_name': tracker.name}

    def clone_tracker(self, tracker_id: str, user, new_name: str = None) -> Dict:
        """
        Clone/duplicate a tracker with all its templates.
        
        Useful for creating variations of existing trackers.
        
        Args:
            tracker_id: Source tracker ID
            user: User object
            new_name: Optional name for clone (default: "{original} (Copy)")
            
        Returns:
            Dict with clone details
        """
        try:
            source = TrackerDefinition.objects.get(
                tracker_id=tracker_id,
                user=user,
                deleted_at__isnull=True
            )
        except TrackerDefinition.DoesNotExist:
            raise TrackerNotFoundError(tracker_id)
        
        with transaction.atomic():
            # Create clone
            clone_name = new_name or f"{source.name} (Copy)"
            
            clone = TrackerDefinition.objects.create(
                tracker_id=str(uuid.uuid4()),
                user=user,
                name=clone_name,
                description=source.description,
                time_mode=source.time_mode,
                status='active',
                icon=source.icon if hasattr(source, 'icon') else None,
                color=source.color if hasattr(source, 'color') else None
            )
            
            # Clone templates
            templates = TaskTemplate.objects.filter(
                tracker=source,
                deleted_at__isnull=True
            )
            
            cloned_templates = []
            for template in templates:
                cloned_template = TaskTemplate.objects.create(
                    template_id=str(uuid.uuid4()),
                    tracker=clone,
                    description=template.description,
                    category=template.category,
                    time_of_day=template.time_of_day,
                    is_recurring=template.is_recurring,
                    points=template.points,
                    weight=template.weight,
                    include_in_goal=template.include_in_goal
                )
                cloned_templates.append(str(cloned_template.template_id))
        
        return {
            'success': True,
            'source_id': tracker_id,
            'clone_id': str(clone.tracker_id),
            'clone_name': clone.name,
            'templates_cloned': len(cloned_templates)
        }

    @staticmethod
    def get_week_aggregation(tracker_id: str, week_start: 'date') -> Dict:
        """
        Aggregate daily instances into weekly view.
        Does NOT create new instances - just aggregates.
        
        This solves the overlapping periods edge case from finalePhase.md.
        
        Args:
            tracker_id: Tracker to aggregate
            week_start: Start of the week (usually Monday)
            
        Returns:
            Dict with weekly aggregated stats
        """
        from datetime import timedelta
        
        week_end = week_start + timedelta(days=6)
        
        daily_instances = TrackerInstance.objects.filter(
            tracker_id=tracker_id,
            tracking_date__range=(week_start, week_end),
            deleted_at__isnull=True
        ).prefetch_related('tasks')
        
        total = 0
        done = 0
        days_with_data = 0
        daily_breakdown = []
        
        for instance in daily_instances:
            tasks = instance.tasks.filter(deleted_at__isnull=True)
            day_total = tasks.count()
            day_done = tasks.filter(status='DONE').count()
            
            total += day_total
            done += day_done
            if tasks.exists():
                days_with_data += 1
            
            daily_breakdown.append({
                'date': instance.tracking_date.isoformat(),
                'total': day_total,
                'done': day_done,
                'rate': (day_done / day_total * 100) if day_total > 0 else 0
            })
        
        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'total_tasks': total,
            'completed_tasks': done,
            'completion_rate': (done / total * 100) if total > 0 else 0,
            'days_tracked': days_with_data,
            'daily_breakdown': daily_breakdown
        }
