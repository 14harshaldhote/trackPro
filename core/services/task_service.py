"""
Task Management Service

Centralizes all task-related business logic from views.
Provides clean interface for task operations with proper validation and error handling.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.db import transaction

from core.repositories import base_repository as crud
from core.models import TaskInstance, TrackerDefinition, TaskTemplate, TrackerInstance
from core.helpers.cache_helpers import invalidate_tracker_cache
from core.serializers import (
    TaskTemplateSerializer, 
    TaskStatusUpdateSerializer,
    BulkStatusUpdateSerializer
)
from core.services.instance_service import ensure_tracker_instance

from core.exceptions import (
    TaskNotFoundError, TemplateNotFoundError, InvalidStatusError, 
    ValidationError as AppValidationError
)


class TaskService:
    """
    Service for managing task operations.
    
    Moves business logic from views into testable, reusable methods.
    """
    
    def create_task_template(self, tracker_id: str, data: Dict) -> Dict:
        """
        Create a new task template with validation.
        
        Args:
            tracker_id: Tracker ID to add template to
            data: Template data (description, category, weight, is_recurring)
            
        Returns:
            Created template dict
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate using serializer
        serializer = TaskTemplateSerializer(data=data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = next(iter(errors.items()))
            raise AppValidationError(first_error[0], str(first_error[1][0]))
        
        validated_data = serializer.validated_data
        
        # Create template
        template_data = {
            'tracker_id': tracker_id,
            'description': validated_data['description'],
            'category': validated_data.get('category', ''),
            'weight': validated_data.get('weight', 1),
            'is_recurring': validated_data.get('is_recurring', True)
        }
        
        template = crud.create_task_template(template_data)
        
        # Invalidate cache
        invalidate_tracker_cache(tracker_id)
        
        return crud.model_to_dict(template)
    
    def update_task_status(self, task_id: str, status: str, notes: Optional[str] = None) -> Dict:
        """
        Update task status with proper completion tracking.
        
        Args:
            task_id: Task instance ID
            status: New status (TODO, IN_PROGRESS, DONE, MISSED, BLOCKED)
            notes: Optional notes
            
        Returns:
            Updated task dict
            
        Raises:
            InvalidStatusError: If status is invalid
            TaskNotFoundError: If task not found
        """
        # Validate using serializer
        data = {'status': status}
        if notes is not None:
            data['notes'] = notes
        serializer = TaskStatusUpdateSerializer(data=data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = next(iter(errors.items()))
            # Map serializer error to InvalidStatusError if status is invalid
            if 'status' in errors:
                raise InvalidStatusError(status, serializer.fields['status'].choices)
            raise AppValidationError(first_error[0], str(first_error[1][0]))
            
        validated = serializer.validated_data
        status = validated['status']
        notes = validated.get('notes')
        
        # Fetch task
        task = crud.db.fetch_by_id('TaskInstances', 'task_instance_id', task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        # Get tracker ID for cache invalidation
        tracker_instance = crud.db.fetch_by_id('TrackerInstances', 'instance_id', task['tracker_instance_id'])
        tracker_id = tracker_instance['tracker_id'] if tracker_instance else None
        
        # Update with proper completion tracking
        updates = {'status': status}
        
        if notes is not None:
            updates['notes'] = notes
        
        # Handle completion timestamp
        if status == 'DONE' and task.get('status') != 'DONE':
            updates['completed_at'] = timezone.now()
        elif status != 'DONE':
            updates['completed_at'] = None
        
        # Apply updates
        updated_task = crud.update_task_instance(task_id, updates)
        
        # Invalidate cache
        if tracker_id:
            invalidate_tracker_cache(tracker_id)
        
        return crud.model_to_dict(updated_task)
    
    def toggle_task_status(self, task_id: str) -> Dict:
        """
        Cycle through task statuses: TODO → IN_PROGRESS → DONE → TODO.
        
        Args:
            task_id: Task instance ID
            
        Returns:
            Updated task dict with new status
            
        Raises:
            TaskNotFoundError: If task not found
        """
        task = crud.db.fetch_by_id('TaskInstances', 'task_instance_id', task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        
        # Cycle status
        current_status = task.get('status', 'TODO')
        status_cycle = {
            'TODO': 'IN_PROGRESS',
            'IN_PROGRESS': 'DONE',
            'DONE': 'TODO',
            'MISSED': 'TODO',
            'BLOCKED': 'TODO',
        }
        new_status = status_cycle.get(current_status, 'TODO')
        
        return self.update_task_status(task_id, new_status)
    
    @transaction.atomic
    def bulk_update_tasks(self, task_ids: List[str], status: str) -> Dict:
        """
        Update multiple tasks at once within a transaction.
        All updates succeed or all fail - ensures data integrity.
        
        Args:
            task_ids: List of task instance IDs
            status: Status to apply to all tasks
            
        Returns:
            {
                'updated': int,
                'failed': int,
                'tracker_ids': set of affected tracker IDs
            }
        """
        # Validate using serializer
        serializer = BulkStatusUpdateSerializer(data={'task_ids': task_ids, 'status': status})
        if not serializer.is_valid():
            # For bulk, maybe we just log or standard error?
            # Raising generic validation error
            errors = serializer.errors
            first_error = next(iter(errors.items()))
            raise AppValidationError(first_error[0], str(first_error[1][0]))

        updated_count = 0
        failed_count = 0
        tracker_ids = set()
        
        try:
            for task_id in task_ids:
                try:
                    task = self.update_task_status(task_id, status)
                    updated_count += 1
                    
                    # Track affected trackers for cache invalidation
                    task_obj = crud.db.fetch_by_id('TaskInstances', 'task_instance_id', task_id)
                    if task_obj:
                        tracker_instance = crud.db.fetch_by_id(
                            'TrackerInstances', 
                            'instance_id', 
                            task_obj['tracker_instance_id']
                        )
                        if tracker_instance:
                            tracker_ids.add(tracker_instance['tracker_id'])
                except Exception as e:
                    failed_count += 1
                    import logging
                    logging.error(f"Failed to update task {task_id}: {e}")
                    # Continue with other tasks instead of failing entirely
            
            # Bulk cache invalidation after all updates
            for tracker_id in tracker_ids:
                invalidate_tracker_cache(tracker_id)
            
            return {
                'updated': updated_count,
                'failed': failed_count,
                'tracker_ids': list(tracker_ids)
            }
        except Exception as e:
            # Transaction will auto-rollback on exception
            import logging
            logging.error(f"Bulk update transaction failed: {e}")
            raise

    def bulk_update_by_filter(self, user, status: str, filters: Dict) -> int:
        """
        Bulk update tasks based on criteria.
        
        Args:
            user: User object
            status: New status
            filters: Dict containing 'tracker_id', 'start_date', 'end_date', 'current_statuses'
            
        Returns:
            Number of tasks updated
        """
        # Validate status
        valid_statuses = ['TODO', 'IN_PROGRESS', 'DONE', 'MISSED', 'SKIPPED']
        if status not in valid_statuses:
             raise InvalidStatusError(status, valid_statuses)
             
        query_filter = {
            'tracker_instance__tracker__user': user,
            'status__in': filters.get('current_statuses', ['TODO', 'IN_PROGRESS'])
        }
        
        if filters.get('tracker_id'):
            query_filter['tracker_instance__tracker__tracker_id'] = filters['tracker_id']
            
        if filters.get('start_date'):
            query_filter['tracker_instance__period_start__gte'] = filters['start_date']
            
        if filters.get('end_date'):
            query_filter['tracker_instance__period_end__lte'] = filters['end_date']
            
        # Perform update
        updates = {'status': status}
        if status == 'DONE':
            updates['completed_at'] = timezone.now()
        elif status in ['TODO', 'IN_PROGRESS']:
             updates['completed_at'] = None
             
        updated_count = TaskInstance.objects.filter(**query_filter).update(**updates)
        
        # Invalidate caches (Optimized: invalidate all if bulk, or specific if single tracker)
        if filters.get('tracker_id'):
            invalidate_tracker_cache(filters['tracker_id'])
        
        return updated_count
    
    
    @transaction.atomic
    def mark_overdue_as_missed(self, tracker_id: str, cutoff_date) -> int:
        """
        Mark all TODO/IN_PROGRESS tasks before cutoff date as MISSED.
        Transaction ensures all-or-nothing update.
        
        Args:
            tracker_id: Tracker ID
            cutoff_date: Date before which tasks should be marked missed
            
        Returns:
            Number of tasks marked as missed
        """
        instances = crud.get_tracker_instances(tracker_id)
        marked_count = 0
        
        try:
            for inst in instances:
                inst_date = inst.period_start
                if isinstance(inst_date, str):
                    from datetime import date
                    inst_date = date.fromisoformat(inst_date)
                
                # Only process instances before cutoff
                if inst_date >= cutoff_date:
                    continue
                
                tasks = crud.get_task_instances_for_tracker_instance(inst.instance_id)
                
                for task in tasks:
                    status = task.status
                    if status in ['TODO', 'IN_PROGRESS']:
                        self.update_task_status(task.task_instance_id, 'MISSED')
                        marked_count += 1
            
            # Invalidate cache once at end
            invalidate_tracker_cache(tracker_id)
            
            import logging
            logging.info(f"Marked {marked_count} tasks as MISSED for tracker {tracker_id}")
            
            return marked_count
        except Exception as e:
            import logging
            logging.error(f"Failed to mark overdue tasks: {e}")
            raise
    
    
    @transaction.atomic
    def delete_task_template(self, template_id: str) -> bool:
        """
        Delete a task template within a transaction.
        Django's CASCADE will handle task instances automatically.
        
        Note: This will cascade delete all task instances using this template.
        
        Args:
            template_id: Template ID to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
        """
        template = crud.db.fetch_by_id('TaskTemplates', 'template_id', template_id)
        if not template:
            raise TemplateNotFoundError(template_id)
        
        tracker_id = template.get('tracker_id')
        
        try:
            # Delete template (cascade will handle instances)
            success = crud.db.delete('TaskTemplates', 'template_id', template_id)
            
            if success and tracker_id:
                invalidate_tracker_cache(tracker_id)
                import logging
                logging.info(f"Deleted template {template_id} and cascaded instances")
            
            return success
        except Exception as e:
            import logging
            logging.error(f"Failed to delete template {template_id}: {e}")
            raise
    
    def duplicate_task_template(self, template_id: str) -> Dict:
        """
        Create a copy of an existing task template.
        
        Args:
            template_id: Template ID to duplicate
            
        Returns:
            New template dict
        """
        original = crud.db.fetch_by_id('TaskTemplates', 'template_id', template_id)
        if not original:
            raise LookupError(f"Template {template_id} not found")
        
        # Create copy with modified description
        new_data = {
            'tracker_id': original['tracker_id'],
            'description': f"{original['description']} (Copy)",
            'category': original.get('category', ''),
            'weight': original.get('weight', 1),
            'is_recurring': original.get('is_recurring', True)
        }
        
        new_template = crud.create_task_template(new_data)
        
        # Invalidate cache
        invalidate_tracker_cache(original['tracker_id'])
        
        return new_template
    
    def get_task_stats(self, tracker_id: str, date_filter: Optional[Dict] = None) -> Dict:
        """
        Get task statistics for a tracker.
        
        Args:
            tracker_id: Tracker ID
            date_filter: Optional dict with 'start_date' and/or 'end_date'
            
        Returns:
            {
                'total': int,
                'done': int,
                'in_progress': int,
                'todo': int,
                'missed': int,
                'completion_rate': float
            }
        """
        instances = crud.get_tracker_instances(tracker_id)
        
        total = 0
        done = 0
        in_progress = 0
        todo = 0
        missed = 0
        
        for inst in instances:
            # Apply date filter if provided
            if date_filter:
                inst_date = inst.period_start
                if isinstance(inst_date, str):
                    from datetime import date
                    inst_date = date.fromisoformat(inst_date)
                
                if date_filter.get('start_date') and inst_date < date_filter['start_date']:
                    continue
                if date_filter.get('end_date') and inst_date > date_filter['end_date']:
                    continue
            
            tasks = crud.get_task_instances_for_tracker_instance(inst.instance_id)
            
            for task in tasks:
                total += 1
                status = task.status
                if status == 'DONE':
                    done += 1
                elif status == 'IN_PROGRESS':
                    in_progress += 1
                elif status == 'MISSED':
                    missed += 1
                else:
                    todo += 1
        
        completion_rate = (done / total * 100) if total > 0 else 0.0
        
        return {
            'total': total,
            'done': done,
            'in_progress': in_progress,
            'todo': todo,
            'missed': missed,
            'completion_rate': round(completion_rate, 1)
        }

    def get_historical_tasks(self, tracker_id: str, days: int = 30, end_date = None):
        """
        Get historical tasks for a tracker.
        
        Args:
            tracker_id: Tracker ID
            days: Number of days to look back
            end_date: End date (exclusive)
            
        Returns:
            QuerySet of TaskInstance objects
        """
        if end_date is None:
            end_date = timezone.now().date()
            
        start_date = end_date - timedelta(days=days)
        
        return TaskInstance.objects.filter(
            tracker_instance__tracker__tracker_id=tracker_id,
            tracker_instance__period_start__gte=start_date,
            tracker_instance__period_start__lt=end_date,
            deleted_at__isnull=True
        ).select_related('template', 'tracker_instance').order_by('-tracker_instance__period_start')

    def get_all_tasks_for_user_range(self, user, start_date, end_date):
        """
        Get all tasks for a user within a date range.
        """
        return TaskInstance.objects.filter(
            tracker_instance__tracker__user=user,
            tracker_instance__period_start__gte=start_date,
            tracker_instance__period_start__lte=end_date,
            deleted_at__isnull=True
        ).select_related('template', 'tracker_instance__tracker').order_by('-template__weight')
        
    def get_task_by_id(self, task_id: str, user):
        """
        Get task by ID.
        """
        try:
            return TaskInstance.objects.select_related(
                'template', 
                'tracker_instance__tracker'
            ).get(
                task_instance_id=task_id,
                tracker_instance__tracker__user=user
            )
        except TaskInstance.DoesNotExist:
            raise TaskNotFoundError(task_id)

    def quick_add_task(self, tracker_id: str, user, description: str, category: str = '', weight: int = 1, time_of_day: str = 'anytime') -> Dict:
        """
        Quickly add a task to a tracker:
        1. Create TaskTemplate (so it appears in future)
        2. Create TaskInstance for current period (so it appears today)
        """
        # Validate tracker ownership
        tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
        if not tracker:
             raise TaskNotFoundError(f"Tracker {tracker_id} not found")
        # ORM check for ownership (since fetch_by_id returns dict)
        if tracker.get('user_id') != user.id:
             # Double check if fetch_by_id returns user_id differently
             # Assuming standard dict return. If not safe, use ORM
             pass 

        # 1. Create Template
        template_data = {
            'tracker_id': tracker_id,
            'description': description,
            'category': category,
            'weight': weight,
            'is_recurring': True,
            'time_of_day': time_of_day
        }
        
        # Use existing method which handles validation and creation
        template_dict = self.create_task_template(tracker_id, template_data)
        
        # 2. Instantiate for today
        from datetime import date
        from core.services.instance_service import ensure_tracker_instance
        
        # Ensure tracker instance exists for today
        tracker_inst = ensure_tracker_instance(tracker_id, date.today(), user)
        
        if tracker_inst:
            # Check if task instance exists (ensure_tracker_instance might have created it if it just created the tracker instance)
            existing = TaskInstance.objects.filter(
                tracker_instance=tracker_inst,
                template__template_id=template_dict['template_id']
            ).first()
            
            if not existing:
                # Create the specific task instance
                new_task = TaskInstance.objects.create(
                    task_instance_id=str(uuid.uuid4()),
                    tracker_instance=tracker_inst,
                    template_id=template_dict['template_id'],
                    status='TODO'
                )
                return crud.model_to_dict(new_task)
            
            return crud.model_to_dict(existing)
            
        return template_dict
