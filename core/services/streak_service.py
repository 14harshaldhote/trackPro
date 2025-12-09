from datetime import date, timedelta
from typing import NamedTuple
from django.db.models import Count, Q
from core.models import TrackerInstance, TaskInstance, UserPreferences, TrackerDefinition

class StreakResult(NamedTuple):
    current_streak: int
    longest_streak: int
    streak_active: bool
    last_completed_date: date | None

class StreakService:
    """Calculate and manage user streaks."""
    
    @staticmethod
    def calculate_streak(
        tracker_id: str,
        user_id: int,
        as_of_date: date = None,
        threshold_percent: int = None
    ) -> StreakResult:
        """
        Calculate current and longest streak for a tracker.
        
        Args:
            tracker_id: The tracker to calculate for
            user_id: User ID for getting preferences
            as_of_date: Calculate as of this date (default: today)
            threshold_percent: Override user's streak threshold
            
        Returns:
            StreakResult with current, longest, and status
        """
        as_of_date = as_of_date or date.today()
        
        # Get user's streak threshold
        try:
            prefs = UserPreferences.objects.get(user_id=user_id)
            threshold = threshold_percent or prefs.streak_threshold
        except UserPreferences.DoesNotExist:
            threshold = threshold_percent or 80
        
        # Get all instances ordered by date
        instances = TrackerInstance.objects.filter(
            tracker__tracker_id=tracker_id,
            deleted_at__isnull=True,
            tracking_date__lte=as_of_date
        ).order_by('-tracking_date')
        
        current_streak = 0
        longest_streak = 0
        temp_streak = 0
        last_completed_date = None
        streak_active = False
        
        prev_date = None
        
        for instance in instances:
            # Calculate completion percentage for this instance
            total_tasks = instance.tasks.filter(deleted_at__isnull=True).count()
            done_tasks = instance.tasks.filter(status='DONE', deleted_at__isnull=True).count()
            
            if total_tasks == 0:
                continue
            
            completion_pct = (done_tasks / total_tasks) * 100
            meets_threshold = completion_pct >= threshold
            
            if meets_threshold:
                if last_completed_date is None:
                    last_completed_date = instance.tracking_date
                
                # Check continuity
                if prev_date is None:
                    temp_streak = 1
                    # Check if streak is still active (today or yesterday)
                    days_gap = (as_of_date - instance.tracking_date).days
                    streak_active = days_gap <= 1
                elif (prev_date - instance.tracking_date).days == 1:
                    temp_streak += 1
                else:
                    # Streak broken
                    longest_streak = max(longest_streak, temp_streak)
                    if current_streak == 0:
                        current_streak = temp_streak
                    temp_streak = 1
                
                prev_date = instance.tracking_date
            else:
                # Missed day - streak broken
                if temp_streak > 0:
                    longest_streak = max(longest_streak, temp_streak)
                    if current_streak == 0:
                        current_streak = temp_streak
                temp_streak = 0
                prev_date = None
        
        # Handle final streak
        longest_streak = max(longest_streak, temp_streak)
        if current_streak == 0:
            current_streak = temp_streak
        
        return StreakResult(
            current_streak=current_streak if streak_active else 0,
            longest_streak=longest_streak,
            streak_active=streak_active,
            last_completed_date=last_completed_date
        )
    
    @staticmethod
    def get_all_user_streaks(user_id: int) -> list[dict]:
        """Get streak summary for all user's active trackers."""
        
        trackers = TrackerDefinition.objects.filter(
            user_id=user_id,
            status='active',
            deleted_at__isnull=True
        )
        
        return [
            {
                'tracker_id': str(tracker.tracker_id),
                'tracker_name': tracker.name,
                **StreakService.calculate_streak(tracker.tracker_id, user_id)._asdict()
            }
            for tracker in trackers
        ]
