"""
Instance Service (ORM-Based)

Manages TrackerInstance and TaskInstance creation with proper ORM usage.
Includes user isolation and efficient bulk operations.
"""
import uuid
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Q

from core.models import TrackerDefinition, TrackerInstance, TaskInstance, TaskTemplate
from core.utils import time_utils


def ensure_tracker_instance(tracker_id: str, reference_date: date = None, user=None):
    """
    Ensures a TrackerInstance exists for the given tracker and date.
    Uses Django ORM for efficient database operations.
    
    Args:
        tracker_id: The tracker's UUID
        reference_date: Date to create instance for (default: today)
        user: Optional user for access validation
    
    Returns:
        TrackerInstance object or dict for compatibility
    """
    if reference_date is None:
        reference_date = date.today()
    
    # Get tracker definition using ORM
    try:
        tracker_query = TrackerDefinition.objects.filter(tracker_id=tracker_id)
        if user:
            tracker_query = tracker_query.filter(user=user)
        tracker = tracker_query.select_related('user').first()
    except TrackerDefinition.DoesNotExist:
        return None
    
    if not tracker:
        return None
    
    # Calculate period dates
    start_date, end_date = time_utils.get_period_dates(tracker.time_mode, reference_date)
    
    # Check if instance already exists using ORM
    existing_instance = TrackerInstance.objects.filter(
        tracker=tracker,
        period_start=start_date,
        period_end=end_date
    ).first()
    
    if existing_instance:
        return existing_instance
    
    # Create new instance using transaction
    with transaction.atomic():
        new_instance = TrackerInstance.objects.create(
            instance_id=str(uuid.uuid4()),
            tracker=tracker,
            tracking_date=reference_date,
            period_start=start_date,
            period_end=end_date,
            status='active'
        )
        
        # Create tasks from templates using bulk_create for efficiency
        templates = TaskTemplate.objects.filter(
            tracker=tracker
        ).exclude(
            description__startswith='[DELETED]'
        )
        
        tasks_to_create = []
        for template in templates:
            tasks_to_create.append(TaskInstance(
                task_instance_id=str(uuid.uuid4()),
                tracker_instance=new_instance,
                template=template,
                status='TODO'
            ))
        
        if tasks_to_create:
            TaskInstance.objects.bulk_create(tasks_to_create)
    
    return new_instance


def check_all_trackers(reference_date: date = None, user=None):
    """
    Checks all trackers and ensures instances exist for the reference date.
    Uses ORM with user isolation.
    
    Args:
        reference_date: Date to check (default: today)
        user: Optional user to filter trackers
    """
    if reference_date is None:
        reference_date = date.today()
    
    tracker_query = TrackerDefinition.objects.filter(status='active')
    if user:
        tracker_query = tracker_query.filter(user=user)
    
    for tracker in tracker_query:
        ensure_tracker_instance(tracker.tracker_id, reference_date, user)


def get_instance_for_date(tracker_id: str, target_date: date, user=None) -> TrackerInstance:
    """
    Get or create a TrackerInstance for a specific date.
    
    Args:
        tracker_id: The tracker's UUID
        target_date: The target date
        user: Optional user for access validation
    
    Returns:
        TrackerInstance object
    """
    base_query = TrackerInstance.objects.filter(
        tracker__tracker_id=tracker_id,
        period_start__lte=target_date,
        period_end__gte=target_date
    ).select_related('tracker')
    
    if user:
        base_query = base_query.filter(tracker__user=user)
    
    instance = base_query.first()
    
    if not instance:
        ensure_tracker_instance(tracker_id, target_date, user)
        instance = base_query.first()
    
    return instance


def get_tasks_for_instance(instance_id: str, user=None):
    """
    Get all tasks for a tracker instance with prefetching.
    
    Args:
        instance_id: The instance UUID
        user: Optional user for access validation
    
    Returns:
        QuerySet of TaskInstance objects
    """
    query = TaskInstance.objects.filter(
        tracker_instance__instance_id=instance_id
    ).select_related('template', 'tracker_instance__tracker')
    
    if user:
        query = query.filter(tracker_instance__tracker__user=user)
    
    return query.order_by('-template__weight', 'template__time_of_day', 'created_at')
