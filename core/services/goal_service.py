"""
Goal Progress Service

Provides goal progress calculation, tracking, and recommendations.
Integrates with the behavioral engine for intelligent progress insights.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional
from django.db.models import Sum, Count, Avg, Q

from core.models import Goal, TrackerDefinition, TaskInstance


class GoalProgressService:
    """
    Service for calculating and tracking goal progress.
    
    Provides:
    - Progress calculation based on linked trackers
    - Projection/forecasting
    - Recommendations for at-risk goals
    """
    
    def __init__(self, user):
        """
        Initialize service with user isolation.
        
        Args:
            user: Django User object
        """
        self.user = user
    
    def calculate_goal_progress(self, goal_id: str) -> Dict:
        """
        Calculate current progress for a specific goal.
        
        Args:
            goal_id: Goal UUID
        
        Returns:
            {
                'progress': float (0-100),
                'current_value': float,
                'target_value': float,
                'on_track': bool,
                'days_left': int,
                'projected_completion': date or None
            }
        """
        try:
            goal = Goal.objects.get(goal_id=goal_id, user=self.user)
        except Goal.DoesNotExist:
            return {}
        
        today = date.today()
        
        # Calculate progress based on goal type
        if goal.goal_type == 'habit' and goal.tracker:
            # For habit goals, calculate from linked tracker
            progress = self._calculate_habit_progress(goal)
        elif goal.goal_type == 'milestone':
            # For milestone goals, use current_value vs target_value
            progress = (goal.current_value / goal.target_value * 100) if goal.target_value else 0
        else:
            progress = goal.progress
        
        # Calculate days remaining
        days_left = (goal.target_date - today).days if goal.target_date else None
        
        # Determine if on track
        on_track = True
        behind_by = 0
        if goal.target_date and days_left and days_left > 0:
            expected_progress = self._get_expected_progress(goal)
            on_track = progress >= (expected_progress * 0.9)  # 10% buffer
            if not on_track:
                behind_by = int(expected_progress - progress)
        
        # Project completion date
        projected_completion = self._project_completion(goal, progress)
        
        return {
            'progress': round(progress, 1),
            'current_value': goal.current_value,
            'target_value': goal.target_value,
            'on_track': on_track,
            'behind_by': f"{behind_by}%" if behind_by > 0 else '',
            'days_left': days_left,
            'projected_completion': projected_completion,
            'tracker_name': goal.tracker.name if goal.tracker else 'No tracker'
        }
    
    def _calculate_habit_progress(self, goal: Goal) -> float:
        """Calculate progress for habit-based goals."""
        if not goal.tracker:
            return 0
        
        # Get completion rate from linked tracker
        completed = TaskInstance.objects.filter(
            tracker_instance__tracker=goal.tracker,
            status='DONE'
        ).count()
        
        total = TaskInstance.objects.filter(
            tracker_instance__tracker=goal.tracker
        ).count()
        
        return (completed / total * 100) if total else 0
    
    def _get_expected_progress(self, goal: Goal) -> float:
        """Calculate expected progress based on time elapsed."""
        if not goal.target_date:
            return 0
        
        today = date.today()
        total_days = (goal.target_date - goal.created_at.date()).days
        elapsed_days = (today - goal.created_at.date()).days
        
        if total_days <= 0:
            return 100
        
        return (elapsed_days / total_days) * 100
    
    def _project_completion(self, goal: Goal, current_progress: float) -> Optional[date]:
        """Project when goal will be completed based on current rate."""
        if current_progress >= 100:
            return date.today()
        
        if current_progress <= 0:
            return None
        
        today = date.today()
        days_elapsed = (today - goal.created_at.date()).days
        
        if days_elapsed <= 0:
            return None
        
        # Daily progress rate
        daily_rate = current_progress / days_elapsed
        remaining_progress = 100 - current_progress
        
        if daily_rate <= 0:
            return None
        
        days_needed = int(remaining_progress / daily_rate)
        return today + timedelta(days=days_needed)
    
    def get_all_goals_progress(self) -> List[Dict]:
        """
        Get progress for all user goals.
        
        Returns:
            List of goal progress dicts
        """
        goals = Goal.objects.filter(user=self.user).select_related('tracker')
        
        results = []
        for goal in goals:
            progress_data = self.calculate_goal_progress(goal.goal_id)
            progress_data['goal_id'] = goal.goal_id
            progress_data['title'] = goal.title
            progress_data['icon'] = goal.icon
            progress_data['status'] = goal.status
            progress_data['unit'] = goal.unit or 'tasks'
            progress_data['completed_at'] = goal.updated_at if goal.status == 'achieved' else None
            results.append(progress_data)
        
        return results
    
    def get_at_risk_goals(self) -> List[Dict]:
        """
        Get goals that are behind schedule.
        
        Returns:
            List of at-risk goals with recommendations
        """
        all_progress = self.get_all_goals_progress()
        
        at_risk = []
        for goal in all_progress:
            if goal.get('status') == 'active' and not goal.get('on_track', True):
                goal['recommendation'] = self._get_recommendation(goal)
                at_risk.append(goal)
        
        return at_risk
    
    def _get_recommendation(self, goal_data: Dict) -> str:
        """Generate recommendation for at-risk goal."""
        days_left = goal_data.get('days_left')
        progress = goal_data.get('progress', 0)
        
        if days_left and days_left < 7:
            return "This goal needs immediate attention. Consider focusing on it daily."
        elif progress < 25:
            return "You're in the early stages. Try setting smaller daily milestones."
        elif progress < 50:
            return "You're making progress but falling behind. Increase your daily effort."
        else:
            return "You're more than halfway there! Push a bit harder to finish on time."
    
    def update_goal_progress(self, goal_id: str, new_value: float = None) -> Dict:
        """
        Update a goal's progress.
        
        Args:
            goal_id: Goal UUID
            new_value: New current_value (optional, will recalculate if not provided)
        
        Returns:
            Updated progress data
        """
        try:
            goal = Goal.objects.get(goal_id=goal_id, user=self.user)
        except Goal.DoesNotExist:
            return {'error': 'Goal not found'}
        
        if new_value is not None:
            goal.current_value = new_value
        
        # Recalculate progress
        if goal.target_value:
            goal.progress = min(100, (goal.current_value / goal.target_value) * 100)
        
        # Check if goal is achieved
        if goal.progress >= 100 and goal.status == 'active':
            goal.status = 'achieved'
        
        goal.save()
        
        return self.calculate_goal_progress(goal_id)


# Convenience functions

def calculate_user_goal_progress(user) -> Dict:
    """Get summary of all user's goal progress."""
    service = GoalProgressService(user)
    
    all_progress = service.get_all_goals_progress()
    at_risk = service.get_at_risk_goals()
    
    active_goals = [g for g in all_progress if g.get('status') == 'active']
    avg_progress = sum(g.get('progress', 0) for g in active_goals) / len(active_goals) if active_goals else 0
    
    return {
        'total_goals': len(all_progress),
        'active_goals': len(active_goals),
        'avg_progress': round(avg_progress, 1),
        'at_risk_count': len(at_risk),
        'at_risk_goals': at_risk
    }
