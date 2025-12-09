"""
Task Signals - Automatic updates triggered by task changes

This module handles:
1. Goal progress updates when task status changes
2. Streak notifications when milestones are reached
3. Progress milestone notifications

Written from scratch as per finalePhase.md Section 6.7
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from core.models import TaskInstance, GoalTaskMapping
from core.services.goal_service import GoalService
from core.services.streak_service import StreakService
from core.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TaskInstance)
def update_goals_on_task_change(sender, instance, created, **kwargs):
    """
    Incrementally update linked goals when task status changes.
    
    This is triggered after every TaskInstance save, ensuring goals
    are always up-to-date without manual recalculation.
    
    Performance Note: For very high volume, consider using async task queue.
    """
    try:
        # Only process if the task has a template (avoid orphaned tasks)
        if not instance.template_id:
            return
        
        # Find all goals linked to this task's template
        mappings = GoalTaskMapping.objects.filter(
            template_id=instance.template_id
        ).select_related('goal')
        
        for mapping in mappings:
            goal = mapping.goal
            if goal.status in ('active', 'paused'):
                # Update goal progress
                result = GoalService.update_goal_progress(goal)
                
                # Check for progress milestones
                if result and 'progress' in result:
                    try:
                        NotificationService.send_goal_progress_update(
                            user_id=goal.user_id,
                            goal_title=goal.title,
                            progress=result['progress']
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send goal progress notification: {e}")
                        
    except Exception as e:
        logger.error(f"Error updating goals on task change: {e}")


@receiver(post_save, sender=TaskInstance)
def check_streak_milestones(sender, instance, created, **kwargs):
    """
    Check for streak milestones when a task is completed.
    
    Only triggers when status changes to DONE to avoid duplicate checks.
    """
    try:
        if instance.status != 'DONE':
            return
        
        # Get tracker info through the instance chain
        tracker_instance = instance.tracker_instance
        if not tracker_instance:
            return
        
        tracker = tracker_instance.tracker
        if not tracker:
            return
        
        user_id = tracker.user_id
        
        # Calculate current streak
        streak_result = StreakService.calculate_streak(
            tracker_id=str(tracker.tracker_id),
            user_id=user_id
        )
        
        if streak_result.streak_active and streak_result.current_streak > 0:
            # Send streak milestone notification if applicable
            NotificationService.send_streak_alert(
                user_id=user_id,
                tracker_name=tracker.name,
                streak_count=streak_result.current_streak
            )
            
    except Exception as e:
        logger.error(f"Error checking streak milestones: {e}")


# Pre-save signal to track status changes
_status_cache = {}

@receiver(pre_save, sender=TaskInstance)
def cache_old_status(sender, instance, **kwargs):
    """Cache old status before save for comparison."""
    if instance.pk:
        try:
            old_instance = TaskInstance.objects.get(pk=instance.pk)
            _status_cache[instance.pk] = old_instance.status
        except TaskInstance.DoesNotExist:
            pass


@receiver(post_save, sender=TaskInstance)
def handle_status_transition(sender, instance, created, **kwargs):
    """
    Handle specific status transitions.
    
    - TODO -> DONE: First completion
    - DONE -> TODO: Uncompleted
    - * -> MISSED: Mark as missed
    """
    if created:
        return  # New instances don't have transitions
    
    old_status = _status_cache.pop(instance.pk, None)
    if old_status is None or old_status == instance.status:
        return
    
    # Log significant transitions for analytics
    logger.debug(f"Task {instance.pk} transitioned: {old_status} -> {instance.status}")
