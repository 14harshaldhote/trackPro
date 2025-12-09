"""
Goal Service

Manage goal progress calculations, status updates, and insights.
"""
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Count, Q, F
from core.models import Goal, GoalTaskMapping, TaskInstance, Notification

class GoalService:
    """Manage goal progress calculations and updates."""
    
    @staticmethod
    def update_goal_progress(goal: Goal) -> dict:
        """
        Recalculate and update goal progress.
        
        Returns:
            Dict with progress details
        """
        # Filter out deleted templates
        mappings = goal.task_mappings.filter(
            template__deleted_at__isnull=True
        ).select_related('template')
        
        if not mappings.exists():
            # If no mappings, check if it's a simple manual goal or has no tasks
            # For now return 0 progress if no mappings and no manual override logic
            return {'progress': 0, 'current_value': 0, 'target_value': goal.target_value}
        
        total_weight = 0
        weighted_completion = 0
        total_completions = 0
        
        for mapping in mappings:
            template = mapping.template
            weight = mapping.contribution_weight
            
            # Get instance counts
            # Note: We might want to filter by date range if goal has start/end date
            # Current plan doesn't specify strict date filtering for all goals yet, 
            # but usually goals apply to tasks created after goal start.
            # For simplicity matching the plan:
            instances = template.instances.filter(deleted_at__isnull=True)
            if goal.target_date:
                 instances = instances.filter(completed_at__lte=goal.target_date) # Cap at target date?
            # Or usually within goal window. Let's stick to plan's simple count for now or add basic date filter
            
            total = instances.count()
            done = instances.filter(status='DONE').count()
            
            total_completions += done
            
            if total > 0:
                completion_rate = done / total
                weighted_completion += completion_rate * weight
                total_weight += weight
        
        # Calculate progress percentage
        if total_weight > 0:
            progress = (weighted_completion / total_weight) * 100
        else:
            progress = 0
        
        # Update goal
        with transaction.atomic():
            goal.progress = progress
            goal.current_value = total_completions
            
            # Check if goal achieved
            if goal.target_value and goal.current_value >= goal.target_value:
                if goal.status != 'achieved':
                    goal.status = 'achieved'
                    GoalService._send_achievement_notification(goal)
            
            goal.save(update_fields=['progress', 'current_value', 'status', 'updated_at'])
        
        return {
            'progress': progress,
            'current_value': goal.current_value,
            'target_value': goal.target_value,
            'status': goal.status
        }
    
    @staticmethod
    def _send_achievement_notification(goal: Goal):
        """Send notification when goal is achieved."""
        # Check if notification service is available/imported or create directly
        # Plan says create directly here
        Notification.objects.create(
            user=goal.user,
            type='achievement',
            title='🎉 Goal Achieved!',
            message=f'Congratulations! You completed "{goal.title}"',
            link=f'/goals/{str(goal.goal_id)}'
        )
    
    @staticmethod
    def get_goal_insights(goal: Goal) -> dict:
        """Get detailed insights for a goal."""
        mappings = goal.task_mappings.select_related('template')
        
        task_breakdowns = []
        for mapping in mappings:
            template = mapping.template
            instances = template.instances.filter(deleted_at__isnull=True)
            
            total = instances.count()
            done = instances.filter(status='DONE').count()
            missed = instances.filter(status='MISSED').count()
            
            task_breakdowns.append({
                'template_id': str(template.template_id),
                'description': template.description,
                'weight': mapping.contribution_weight,
                'total': total,
                'done': done,
                'missed': missed,
                'completion_rate': (done / total * 100) if total > 0 else 0
            })
        
        # Calculate days remaining
        days_remaining = None
        if goal.target_date:
            days_remaining = (goal.target_date - date.today()).days
        
        # Forecast completion
        avg_daily_progress = GoalService._calculate_velocity(goal)
        
        return {
            'goal_id': str(goal.goal_id),
            'title': goal.title,
            'progress': goal.progress,
            'current_value': goal.current_value,
            'target_value': goal.target_value,
            'days_remaining': days_remaining,
            'avg_daily_progress': avg_daily_progress,
            'on_track': GoalService._is_on_track(goal, avg_daily_progress, days_remaining),
            'task_breakdowns': task_breakdowns
        }
    
    @staticmethod
    def _calculate_velocity(goal: Goal) -> float:
        """Calculate average daily progress rate."""
        days_elapsed = (date.today() - goal.created_at.date()).days or 1
        return goal.current_value / days_elapsed
    
    @staticmethod
    def _is_on_track(goal: Goal, velocity: float, days_remaining: int | None) -> bool:
        """Determine if goal is on track for completion."""
        if not goal.target_value or not days_remaining or days_remaining <= 0:
            return goal.status == 'achieved'
        
        projected_value = goal.current_value + (velocity * days_remaining)
        return projected_value >= goal.target_value

    @staticmethod
    def update_target(goal: Goal, new_target: float) -> dict:
        """
        Update goal target with history preservation.
        """
        old_target = goal.target_value
        was_achieved = goal.status == 'achieved'
        
        goal.target_value = new_target
        
        # Recalculate status
        if goal.current_value >= new_target:
            goal.status = 'achieved'
        elif was_achieved:
            # Was achieved, now not - reopen
            goal.status = 'active'
            # Could add notification here: "Goal target increased!"
        
        goal.save()
        GoalService.update_goal_progress(goal)
        
        return {
            'old_target': old_target,
            'new_target': new_target,
            'status_changed': was_achieved and goal.status != 'achieved'
        }

    @staticmethod
    def get_count_based_progress(
        goal: Goal,
        start_date: date = None,
        end_date: date = None
    ) -> dict:
        """
        Calculate progress for frequency-based goals.
        """
        # Get all task mappings for this goal
        template_ids = goal.task_mappings.values_list('template_id', flat=True)
        
        # Build query for completed tasks
        query = TaskInstance.objects.filter(
            template_id__in=template_ids,
            status='DONE',
            deleted_at__isnull=True
        )
        
        # Apply date filters if provided
        if start_date:
            query = query.filter(completed_at__date__gte=start_date)
        if end_date:
            query = query.filter(completed_at__date__lte=end_date)
        
        current_count = query.count()
        target = goal.target_value or 1
        
        return {
            'current_count': current_count,
            'target': target,
            'progress_percent': min(100, (current_count / target) * 100),
            'remaining': max(0, target - current_count)
        }
