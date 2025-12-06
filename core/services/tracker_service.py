"""
Tracker Management Service

Centralizes business logic for TrackerDefinition operations.
"""
from typing import Dict, List, Optional
from django.db import transaction
from django.utils import timezone
import uuid

from core.models import TrackerDefinition, TaskTemplate, TrackerInstance
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

