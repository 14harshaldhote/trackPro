# TrackPro Backend - Final Implementation Plan

> **Version**: 1.0 | **Last Updated**: 2025-12-09  
> **Status**: Comprehensive Implementation Blueprint

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Feature Checklist (Now / Next / Later)](#3-feature-checklist)
4. [Time Logic Implementation](#4-time-logic-implementation)
5. [Core Services Implementation](#5-core-services-implementation)
6. [Edge Cases & Solutions](#6-edge-cases--solutions)
7. [API Endpoints Specification](#7-api-endpoints-specification)
8. [Testing Strategy](#8-testing-strategy)
9. [Migration Plan](#9-migration-plan)

---

## 1. Executive Summary

### Vision
Build a **dynamic, time-flexible, goal-driven tracker system** that works seamlessly for:
- Single days → Custom multi-day challenges (21-day detox)
- Weekly → Multi-week programs (8-week gym plan)  
- Monthly → Multi-month → Yearly tracking
- Count-based goals not tied to specific dates

### Current Model Foundation
Your existing `core/models.py` provides:
- ✅ `TrackerDefinition` - Container with time_mode (daily/weekly/monthly)
- ✅ `TaskTemplate` - Reusable task blueprints with points
- ✅ `TrackerInstance` - Date/period snapshots
- ✅ `TaskInstance` - Actual completion records
- ✅ `Goal` + `GoalTaskMapping` - Goal engine
- ✅ `DayNote` - Journaling
- ✅ `UserPreferences` - Personalization
- ✅ `Notification` - Alerts system
- ✅ `EntityRelation` - Knowledge graph
- ✅ `ShareLink` - Sharing capability
- ✅ `Tag` + `TaskTemplateTag` - Categorization
- ✅ `SearchHistory` - Search intelligence
- ✅ `SoftDeleteModel` - Safe deletions
- ✅ `HistoricalRecords` - Full audit trail

---

## 2. Architecture Overview

### Service Layer Structure

```
core/
├── models.py                    # Data models (DONE)
├── services/
│   ├── __init__.py
│   ├── instance_service.py      # Instance generation & management
│   ├── streak_service.py        # Streak calculations
│   ├── goal_service.py          # Goal progress engine
│   ├── notification_service.py  # Push/in-app notifications
│   ├── analytics_service.py     # Stats & insights
│   ├── sync_service.py          # Conflict resolution
│   └── share_service.py         # Sharing logic
├── managers/
│   ├── __init__.py
│   ├── tracker_manager.py       # Custom QuerySet managers
│   └── task_manager.py
├── signals/
│   ├── __init__.py
│   └── task_signals.py          # Auto-updates on task changes
├── tasks/
│   ├── __init__.py
│   └── scheduled_tasks.py       # Celery/background jobs
└── utils/
    ├── __init__.py
    ├── date_utils.py            # Timezone-aware date helpers
    └── validators.py            # Input validation
```

---

## 3. Feature Checklist

### ✅ NOW (v1.0 - Core MVP)

| Feature | Model Ready | Service Needed | API Needed | Priority |
|---------|-------------|----------------|------------|----------|
| Tracker CRUD | ✅ | ✅ Basic | ✅ | P0 |
| Task Template CRUD | ✅ | ✅ Basic | ✅ | P0 |
| Instance Generation | ✅ | 🔲 **BUILD** | ✅ | P0 |
| Task Instance Status | ✅ | ✅ Basic | ✅ | P0 |
| Simple Progress (%) | ✅ | 🔲 **BUILD** | ✅ | P0 |
| DayNote (basic) | ✅ | ✅ Basic | ✅ | P0 |
| Streak Engine | ✅ | 🔲 **BUILD** | ✅ | P0 |
| Goal + Mapping | ✅ | 🔲 **BUILD** | ✅ | P0 |
| UserPreferences | ✅ | ✅ Basic | ✅ | P0 |
| Notifications (basic) | ✅ | 🔲 **BUILD** | ✅ | P0 |
| Soft Delete | ✅ | ✅ Done | ✅ | P0 |

### 🔶 NEXT (v1.5 - Enhanced)

| Feature | Model Ready | Service Needed | API Needed | Priority |
|---------|-------------|----------------|------------|----------|
| Tags Filtering | ✅ | 🔲 Build | 🔲 | P1 |
| SearchHistory Features | ✅ | 🔲 Build | 🔲 | P1 |
| EntityRelation (depends_on) | ✅ | 🔲 Build | 🔲 | P1 |
| Multi-tracker Analytics | ✅ | 🔲 Build | 🔲 | P1 |
| Batch Operations | ✅ | 🔲 Build | 🔲 | P1 |

### 🔵 LATER (v2.0 - Power Features)

| Feature | Model Ready | Service Needed | Priority |
|---------|-------------|----------------|----------|
| Knowledge Graph Viz | ✅ | 🔲 | P2 |
| Habit Intelligence | ✅ | 🔲 | P2 |
| Activity Replay | ✅ | 🔲 | P2 |
| ShareLink Collab | ✅ | 🔲 | P2 |
| Calendar Integration | 🔲 | 🔲 | P3 |
| Export/Import | 🔲 | 🔲 | P2 |

---

## 4. Time Logic Implementation

### 4.1 Single Day Tracker

**Use Case**: "Deep Work Sunday", "Exam Day Routine"

```python
# core/services/instance_service.py

from datetime import date, timedelta
from django.db import transaction
from core.models import TrackerDefinition, TrackerInstance, TaskInstance, TaskTemplate

class InstanceService:
    """
    Core service for generating and managing tracker instances.
    Handles all time modes: daily, weekly, monthly.
    """
    
    @staticmethod
    def create_daily_instance(tracker: TrackerDefinition, target_date: date) -> TrackerInstance:
        """
        Create a single day instance with all task instances.
        
        Args:
            tracker: The tracker definition
            target_date: The specific date for the instance
            
        Returns:
            TrackerInstance with populated TaskInstances
        """
        with transaction.atomic():
            # Get or create to prevent duplicates
            instance, created = TrackerInstance.objects.get_or_create(
                tracker=tracker,
                tracking_date=target_date,
                defaults={
                    'period_start': target_date,
                    'period_end': target_date,
                    'status': 'active'
                }
            )
            
            if created:
                # Create task instances from active templates
                templates = TaskTemplate.objects.filter(
                    tracker=tracker,
                    deleted_at__isnull=True,
                    is_recurring=True
                )
                
                task_instances = [
                    TaskInstance(
                        tracker_instance=instance,
                        template=template,
                        status='TODO'
                    )
                    for template in templates
                ]
                TaskInstance.objects.bulk_create(task_instances)
            
            return instance
```

### 4.2 Multi-Day Challenge (21-Day Detox, 10-Day Reading)

**Use Case**: Custom duration challenges

```python
    @staticmethod
    def create_challenge(
        tracker: TrackerDefinition,
        start_date: date,
        duration_days: int,
        goal_title: str = None
    ) -> list[TrackerInstance]:
        """
        Create a multi-day challenge with optional goal tracking.
        
        Args:
            tracker: The tracker definition
            start_date: Challenge start date
            duration_days: Number of days (e.g., 21, 30)
            goal_title: Optional goal to create and link
            
        Returns:
            List of created TrackerInstances
        """
        from core.models import Goal, GoalTaskMapping
        
        instances = []
        end_date = start_date + timedelta(days=duration_days - 1)
        
        with transaction.atomic():
            # Create daily instances for the challenge
            for day_offset in range(duration_days):
                current_date = start_date + timedelta(days=day_offset)
                instance = InstanceService.create_daily_instance(tracker, current_date)
                instances.append(instance)
            
            # Optionally create a goal for the challenge
            if goal_title:
                goal = Goal.objects.create(
                    user=tracker.user,
                    tracker=tracker,
                    title=goal_title,
                    target_value=duration_days,
                    unit='days',
                    target_date=end_date,
                    goal_type='achievement'
                )
                
                # Link all templates to the goal
                templates = tracker.templates.filter(deleted_at__isnull=True)
                for template in templates:
                    GoalTaskMapping.objects.create(
                        goal=goal,
                        template=template,
                        contribution_weight=1.0
                    )
        
        return instances
```

### 4.3 Weekly / Multi-Week Tracker

**Use Case**: "8-Week Gym Program", "4-Week Sprint"

```python
    @staticmethod
    def get_week_boundaries(target_date: date, week_start: int = 0) -> tuple[date, date]:
        """
        Get Monday-Sunday boundaries for a given date.
        
        Args:
            target_date: Any date within the week
            week_start: 0=Monday, 6=Sunday
            
        Returns:
            Tuple of (period_start, period_end)
        """
        days_since_start = (target_date.weekday() - week_start) % 7
        period_start = target_date - timedelta(days=days_since_start)
        period_end = period_start + timedelta(days=6)
        return period_start, period_end
    
    @staticmethod
    def create_weekly_instance(
        tracker: TrackerDefinition,
        target_date: date,
        week_start: int = 0
    ) -> TrackerInstance:
        """
        Create a weekly instance.
        
        Args:
            tracker: The tracker definition (time_mode='weekly')
            target_date: Any date within the target week
            week_start: User's preferred week start (0=Mon, 6=Sun)
            
        Returns:
            TrackerInstance for the week
        """
        period_start, period_end = InstanceService.get_week_boundaries(target_date, week_start)
        
        with transaction.atomic():
            instance, created = TrackerInstance.objects.get_or_create(
                tracker=tracker,
                tracking_date=period_start,  # Anchor to week start
                defaults={
                    'period_start': period_start,
                    'period_end': period_end,
                    'status': 'active'
                }
            )
            
            if created:
                templates = TaskTemplate.objects.filter(
                    tracker=tracker,
                    deleted_at__isnull=True
                )
                
                TaskInstance.objects.bulk_create([
                    TaskInstance(
                        tracker_instance=instance,
                        template=template,
                        status='TODO'
                    )
                    for template in templates
                ])
            
            return instance
    
    @staticmethod
    def create_multi_week_program(
        tracker: TrackerDefinition,
        start_date: date,
        num_weeks: int,
        goal_title: str = None
    ) -> list[TrackerInstance]:
        """
        Create an N-week program (e.g., 8-week fitness plan).
        """
        from core.models import Goal, GoalTaskMapping
        
        instances = []
        
        with transaction.atomic():
            for week_num in range(num_weeks):
                week_date = start_date + timedelta(weeks=week_num)
                instance = InstanceService.create_weekly_instance(tracker, week_date)
                instances.append(instance)
            
            if goal_title:
                goal = Goal.objects.create(
                    user=tracker.user,
                    tracker=tracker,
                    title=goal_title,
                    target_value=num_weeks,
                    unit='weeks',
                    target_date=start_date + timedelta(weeks=num_weeks),
                    goal_type='project'
                )
                
                for template in tracker.templates.filter(deleted_at__isnull=True):
                    GoalTaskMapping.objects.create(
                        goal=goal,
                        template=template
                    )
        
        return instances
```

### 4.4 Monthly / Multi-Month / Yearly

**Use Case**: "12-Month Reading Goal", "3-Month Cutting Phase"

```python
    @staticmethod
    def get_month_boundaries(target_date: date) -> tuple[date, date]:
        """Get first and last day of the month."""
        from calendar import monthrange
        
        period_start = target_date.replace(day=1)
        _, last_day = monthrange(target_date.year, target_date.month)
        period_end = target_date.replace(day=last_day)
        return period_start, period_end
    
    @staticmethod
    def create_monthly_instance(tracker: TrackerDefinition, target_date: date) -> TrackerInstance:
        """Create a monthly tracker instance."""
        period_start, period_end = InstanceService.get_month_boundaries(target_date)
        
        with transaction.atomic():
            instance, created = TrackerInstance.objects.get_or_create(
                tracker=tracker,
                tracking_date=period_start,
                defaults={
                    'period_start': period_start,
                    'period_end': period_end,
                    'status': 'active'
                }
            )
            
            if created:
                TaskInstance.objects.bulk_create([
                    TaskInstance(tracker_instance=instance, template=t, status='TODO')
                    for t in tracker.templates.filter(deleted_at__isnull=True)
                ])
            
            return instance
    
    @staticmethod
    def create_yearly_plan(
        tracker: TrackerDefinition,
        year: int,
        goal_title: str,
        target_value: float,
        unit: str = 'completions'
    ) -> tuple[list[TrackerInstance], 'Goal']:
        """
        Create a year-long tracking plan.
        
        Example: "Read 24 books in 2025"
        - Creates 12 monthly instances
        - Creates goal with target_value=24, unit='books'
        """
        from core.models import Goal, GoalTaskMapping
        
        instances = []
        
        with transaction.atomic():
            for month in range(1, 13):
                month_date = date(year, month, 1)
                instance = InstanceService.create_monthly_instance(tracker, month_date)
                instances.append(instance)
            
            goal = Goal.objects.create(
                user=tracker.user,
                tracker=tracker,
                title=goal_title,
                target_value=target_value,
                unit=unit,
                target_date=date(year, 12, 31),
                goal_type='achievement'
            )
            
            for template in tracker.templates.filter(deleted_at__isnull=True):
                GoalTaskMapping.objects.create(goal=goal, template=template)
        
        return instances, goal
```

### 4.5 Count-Based Goals (Not Date-Tied)

**Use Case**: "Go to gym 10 times this month (any day)"

```python
    @staticmethod
    def get_count_based_progress(
        goal: 'Goal',
        start_date: date = None,
        end_date: date = None
    ) -> dict:
        """
        Calculate progress for frequency-based goals.
        
        Args:
            goal: Goal with target_value as count
            start_date: Optional filter start
            end_date: Optional filter end
            
        Returns:
            Dict with current_count, target, progress_percent
        """
        from core.models import TaskInstance
        
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
```

---

## 5. Core Services Implementation

### 5.1 Streak Service

```python
# core/services/streak_service.py

from datetime import date, timedelta
from typing import NamedTuple
from django.db.models import Count, Q
from core.models import TrackerInstance, TaskInstance, UserPreferences

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
            tracker_id=tracker_id,
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
        from core.models import TrackerDefinition
        
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
```

### 5.2 Goal Progress Service

```python
# core/services/goal_service.py

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
        mappings = goal.task_mappings.select_related('template')
        
        if not mappings.exists():
            return {'progress': 0, 'current_value': 0, 'target_value': goal.target_value}
        
        total_weight = 0
        weighted_completion = 0
        total_completions = 0
        
        for mapping in mappings:
            template = mapping.template
            weight = mapping.contribution_weight
            
            # Get instance counts
            total = template.instances.filter(deleted_at__isnull=True).count()
            done = template.instances.filter(
                status='DONE',
                deleted_at__isnull=True
            ).count()
            
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
        Notification.objects.create(
            user=goal.user,
            type='achievement',
            title='🎉 Goal Achieved!',
            message=f'Congratulations! You completed "{goal.title}"',
            link=f'/goals/{goal.goal_id}'
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
```

---

### 5.3 Notification Service

```python
# core/services/notification_service.py

from datetime import datetime, time, timedelta
from django.utils import timezone
from django.db.models import Count, Q
from core.models import (
    Notification, UserPreferences, TrackerDefinition, 
    TrackerInstance, TaskInstance
)

class NotificationService:
    """Handle all notification logic."""
    
    @staticmethod
    def send_daily_reminder(user_id: int) -> Notification | None:
        """
        Send morning reminder with today's tasks summary.
        Called by scheduled task at user's preferred time.
        """
        try:
            prefs = UserPreferences.objects.get(user_id=user_id)
            if not prefs.daily_reminder_enabled:
                return None
        except UserPreferences.DoesNotExist:
            return None
        
        today = timezone.now().date()
        
        # Count today's tasks across all active trackers
        task_count = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracker__status='active',
            tracker_instance__tracking_date=today,
            status='TODO',
            deleted_at__isnull=True
        ).count()
        
        if task_count == 0:
            return None
        
        return Notification.objects.create(
            user_id=user_id,
            type='reminder',
            title='🌅 Good Morning!',
            message=f'You have {task_count} tasks scheduled for today.',
            link='/today'
        )
    
    @staticmethod
    def send_evening_summary(user_id: int) -> Notification | None:
        """Send evening progress summary."""
        today = timezone.now().date()
        
        # Get today's stats
        stats = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date=today,
            deleted_at__isnull=True
        ).aggregate(
            total=Count('task_instance_id'),
            done=Count('task_instance_id', filter=Q(status='DONE')),
            remaining=Count('task_instance_id', filter=Q(status='TODO'))
        )
        
        if stats['total'] == 0:
            return None
        
        completion_pct = int((stats['done'] / stats['total']) * 100)
        
        if stats['remaining'] > 0:
            message = f"You're {stats['remaining']} tasks away from completing today! ({completion_pct}% done)"
        else:
            message = f"🎉 Amazing! You completed all {stats['total']} tasks today!"
        
        return Notification.objects.create(
            user_id=user_id,
            type='info',
            title='📊 Daily Progress',
            message=message,
            link='/today'
        )
    
    @staticmethod
    def send_streak_alert(user_id: int, tracker_name: str, streak_count: int):
        """Notify user about streak milestones."""
        milestones = [7, 14, 21, 30, 60, 90, 100, 180, 365]
        
        if streak_count in milestones:
            return Notification.objects.create(
                user_id=user_id,
                type='achievement',
                title='🔥 Streak Milestone!',
                message=f'You\'ve maintained {tracker_name} for {streak_count} days!',
                link='/streaks'
            )
        return None
    
    @staticmethod
    def send_goal_progress_update(user_id: int, goal_title: str, progress: float):
        """Notify at progress milestones (25%, 50%, 75%, 100%)."""
        milestones = [25, 50, 75, 100]
        
        # Find which milestone was just crossed
        for milestone in milestones:
            if abs(progress - milestone) < 1:  # Within 1% of milestone
                emoji_map = {25: '🚀', 50: '🎯', 75: '💪', 100: '🎉'}
                return Notification.objects.create(
                    user_id=user_id,
                    type='success' if milestone == 100 else 'info',
                    title=f'{emoji_map.get(milestone, "📈")} Goal Progress!',
                    message=f'You\'re {milestone}% through "{goal_title}"!',
                    link='/goals'
                )
        return None
    
    @staticmethod
    def mark_all_read(user_id: int) -> int:
        """Mark all user notifications as read. Returns count updated."""
        return Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).update(is_read=True)
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Get count of unread notifications."""
        return Notification.objects.filter(
            user_id=user_id,
            is_read=False
        ).count()
```

### 5.4 Analytics Service

```python
# core/services/analytics_service.py

from datetime import date, timedelta
from collections import defaultdict
from django.db.models import Count, Q, Avg, F
from core.models import (
    TrackerDefinition, TrackerInstance, TaskInstance,
    TaskTemplate, Goal
)

class AnalyticsService:
    """Generate analytics and insights."""
    
    @staticmethod
    def get_daily_summary(user_id: int, target_date: date = None) -> dict:
        """Get summary stats for a specific day."""
        target_date = target_date or date.today()
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date=target_date,
            deleted_at__isnull=True
        )
        
        stats = tasks.aggregate(
            total=Count('task_instance_id'),
            done=Count('task_instance_id', filter=Q(status='DONE')),
            in_progress=Count('task_instance_id', filter=Q(status='IN_PROGRESS')),
            missed=Count('task_instance_id', filter=Q(status='MISSED')),
            skipped=Count('task_instance_id', filter=Q(status='SKIPPED')),
            blocked=Count('task_instance_id', filter=Q(status='BLOCKED'))
        )
        
        stats['todo'] = stats['total'] - stats['done'] - stats['in_progress'] - stats['missed'] - stats['skipped'] - stats['blocked']
        stats['completion_rate'] = (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
        stats['date'] = target_date.isoformat()
        
        return stats
    
    @staticmethod
    def get_weekly_summary(user_id: int, week_start: date = None) -> dict:
        """Get summary for an entire week."""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date__range=(week_start, week_end),
            deleted_at__isnull=True
        )
        
        daily_stats = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            daily_stats.append(AnalyticsService.get_daily_summary(user_id, day))
        
        total = tasks.count()
        done = tasks.filter(status='DONE').count()
        
        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'total_tasks': total,
            'completed_tasks': done,
            'completion_rate': (done / total * 100) if total > 0 else 0,
            'daily_breakdown': daily_stats,
            'best_day': max(daily_stats, key=lambda x: x['completion_rate'])['date'] if daily_stats else None
        }
    
    @staticmethod
    def get_tracker_analytics(tracker_id: str, days: int = 30) -> dict:
        """Get analytics for a specific tracker."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        instances = TrackerInstance.objects.filter(
            tracker_id=tracker_id,
            tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).prefetch_related('tasks')
        
        daily_data = []
        total_tasks = 0
        total_done = 0
        
        for instance in instances:
            tasks = instance.tasks.filter(deleted_at__isnull=True)
            day_total = tasks.count()
            day_done = tasks.filter(status='DONE').count()
            
            total_tasks += day_total
            total_done += day_done
            
            daily_data.append({
                'date': instance.tracking_date.isoformat(),
                'total': day_total,
                'done': day_done,
                'rate': (day_done / day_total * 100) if day_total > 0 else 0
            })
        
        return {
            'tracker_id': tracker_id,
            'period_days': days,
            'total_tasks': total_tasks,
            'completed_tasks': total_done,
            'overall_rate': (total_done / total_tasks * 100) if total_tasks > 0 else 0,
            'daily_data': daily_data,
            'trend': AnalyticsService._calculate_trend(daily_data)
        }
    
    @staticmethod
    def _calculate_trend(daily_data: list) -> str:
        """Calculate if performance is improving, declining, or stable."""
        if len(daily_data) < 7:
            return 'insufficient_data'
        
        # Compare first half vs second half
        mid = len(daily_data) // 2
        first_half_avg = sum(d['rate'] for d in daily_data[:mid]) / mid
        second_half_avg = sum(d['rate'] for d in daily_data[mid:]) / (len(daily_data) - mid)
        
        diff = second_half_avg - first_half_avg
        
        if diff > 5:
            return 'improving'
        elif diff < -5:
            return 'declining'
        else:
            return 'stable'
    
    @staticmethod
    def get_heatmap_data(user_id: int, year: int = None) -> list[dict]:
        """Get completion heatmap data for calendar visualization."""
        year = year or date.today().year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        instances = TrackerInstance.objects.filter(
            tracker__user_id=user_id,
            tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).prefetch_related('tasks')
        
        # Aggregate by date
        date_stats = defaultdict(lambda: {'total': 0, 'done': 0})
        
        for instance in instances:
            tasks = instance.tasks.filter(deleted_at__isnull=True)
            date_key = instance.tracking_date.isoformat()
            date_stats[date_key]['total'] += tasks.count()
            date_stats[date_key]['done'] += tasks.filter(status='DONE').count()
        
        return [
            {
                'date': d,
                'count': stats['done'],
                'level': AnalyticsService._get_activity_level(stats['done'], stats['total'])
            }
            for d, stats in sorted(date_stats.items())
        ]
    
    @staticmethod
    def _get_activity_level(done: int, total: int) -> int:
        """Get 0-4 activity level for heatmap."""
        if total == 0:
            return 0
        rate = done / total
        if rate >= 0.9:
            return 4
        elif rate >= 0.7:
            return 3
        elif rate >= 0.5:
            return 2
        elif rate > 0:
            return 1
        return 0
    
    @staticmethod
    def get_most_missed_tasks(user_id: int, limit: int = 5) -> list[dict]:
        """Get tasks with highest miss rate."""
        templates = TaskTemplate.objects.filter(
            tracker__user_id=user_id,
            deleted_at__isnull=True
        ).annotate(
            total_instances=Count('instances', filter=Q(instances__deleted_at__isnull=True)),
            missed_count=Count('instances', filter=Q(instances__status='MISSED', instances__deleted_at__isnull=True))
        ).filter(
            total_instances__gt=5  # Only include with enough data
        ).order_by('-missed_count')[:limit]
        
        return [
            {
                'template_id': str(t.template_id),
                'description': t.description,
                'tracker_name': t.tracker.name,
                'missed_count': t.missed_count,
                'total': t.total_instances,
                'miss_rate': (t.missed_count / t.total_instances * 100) if t.total_instances > 0 else 0
            }
            for t in templates
        ]
    
    @staticmethod
    def get_best_days(user_id: int) -> dict:
        """Analyze which days of week user performs best."""
        # Get last 90 days of data
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).select_related('tracker_instance')
        
        day_stats = defaultdict(lambda: {'total': 0, 'done': 0})
        
        for task in tasks:
            weekday = task.tracker_instance.tracking_date.weekday()
            day_stats[weekday]['total'] += 1
            if task.status == 'DONE':
                day_stats[weekday]['done'] += 1
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        results = [
            {
                'day': day_names[i],
                'day_num': i,
                'total': stats['total'],
                'done': stats['done'],
                'rate': (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
            }
            for i, stats in sorted(day_stats.items())
        ]
        
        best_day = max(results, key=lambda x: x['rate']) if results else None
        worst_day = min(results, key=lambda x: x['rate']) if results else None
        
        return {
            'breakdown': results,
            'best_day': best_day['day'] if best_day else None,
            'worst_day': worst_day['day'] if worst_day else None
        }
```

---

## 6. Edge Cases & Solutions

### 6.1 Time & Period Edge Cases

#### Changing time_mode Mid-Life

**Problem**: User switches tracker from daily → weekly → monthly.

**Solution**:
```python
# core/services/tracker_service.py

class TrackerService:
    @staticmethod
    def change_time_mode(tracker: TrackerDefinition, new_mode: str) -> dict:
        """
        Safely change tracker's time mode.
        
        Strategy:
        1. Mark existing instances as 'legacy' (don't delete)
        2. Change time_mode
        3. Future instances will use new mode
        """
        from django.db import transaction
        
        with transaction.atomic():
            # Mark all future instances as legacy
            future_instances = TrackerInstance.objects.filter(
                tracker=tracker,
                tracking_date__gt=date.today()
            )
            future_instances.update(status='legacy')
            
            # Store mode change in metadata for history
            old_mode = tracker.time_mode
            tracker.time_mode = new_mode
            tracker.save()
            
            return {
                'success': True,
                'old_mode': old_mode,
                'new_mode': new_mode,
                'legacy_instances': future_instances.count()
            }
```

#### Overlapping Periods (Daily + Weekly Views)

**Problem**: Daily instances exist but user also wants weekly summaries.

**Solution**: Don't create overlapping TrackerInstances. Use aggregation queries instead.

```python
    @staticmethod
    def get_week_aggregation(tracker_id: str, week_start: date) -> dict:
        """
        Aggregate daily instances into weekly view.
        Does NOT create new instances - just aggregates.
        """
        week_end = week_start + timedelta(days=6)
        
        daily_instances = TrackerInstance.objects.filter(
            tracker_id=tracker_id,
            tracking_date__range=(week_start, week_end),
            deleted_at__isnull=True
        ).prefetch_related('tasks')
        
        total = 0
        done = 0
        days_with_data = 0
        
        for instance in daily_instances:
            tasks = instance.tasks.filter(deleted_at__isnull=True)
            total += tasks.count()
            done += tasks.filter(status='DONE').count()
            if tasks.exists():
                days_with_data += 1
        
        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'total_tasks': total,
            'completed_tasks': done,
            'completion_rate': (done / total * 100) if total > 0 else 0,
            'days_tracked': days_with_data
        }
```

#### Timezone Shifts

**Problem**: User changes timezone, day boundaries shift.

**Solution**: Store in UTC, convert for display.

```python
# core/utils/date_utils.py

from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from django.utils import timezone

def get_user_today(user_timezone: str) -> date:
    """Get 'today' in user's timezone."""
    tz = ZoneInfo(user_timezone)
    return datetime.now(tz).date()

def to_user_datetime(dt: datetime, user_timezone: str) -> datetime:
    """Convert UTC datetime to user's timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('UTC'))
    return dt.astimezone(ZoneInfo(user_timezone))

def get_day_boundaries(target_date: date, user_timezone: str) -> tuple[datetime, datetime]:
    """Get midnight-to-midnight in user's timezone as UTC."""
    tz = ZoneInfo(user_timezone)
    start = datetime.combine(target_date, time.min).replace(tzinfo=tz)
    end = datetime.combine(target_date, time.max).replace(tzinfo=tz)
    return start.astimezone(ZoneInfo('UTC')), end.astimezone(ZoneInfo('UTC'))
```

#### Backdating & Future-Dating

**Problem**: User creates/edits instances in the past or future.

**Solution**:
```python
class InstanceService:
    @staticmethod
    def create_or_update_instance(
        tracker: TrackerDefinition,
        target_date: date,
        allow_backdate: bool = True,
        allow_future: bool = True
    ) -> tuple[TrackerInstance, bool, list[str]]:
        """
        Create instance with validation.
        
        Returns:
            Tuple of (instance, created, warnings)
        """
        warnings = []
        today = date.today()
        
        if target_date < today and not allow_backdate:
            raise ValueError("Backdating not allowed")
        
        if target_date > today:
            if not allow_future:
                raise ValueError("Future dating not allowed")
            warnings.append("This is a future date - reminders will not trigger")
        
        if target_date < today:
            warnings.append("Backdated entry - will not affect current streak")
        
        instance = InstanceService.create_daily_instance(tracker, target_date)
        created = instance._state.adding
        
        return instance, created, warnings
```

### 6.2 Tracker & Task Instance Edge Cases

#### Instance Generation Gaps

**Problem**: User doesn't open app for 10 days.

**Solution**: On-demand generation with gap filling option.

```python
    @staticmethod
    def fill_missing_instances(
        tracker: TrackerDefinition,
        start_date: date,
        end_date: date,
        mark_missed: bool = True
    ) -> list[TrackerInstance]:
        """
        Fill in missing instances for a date range.
        Optionally mark all tasks as MISSED.
        """
        from django.db import transaction
        
        existing_dates = set(
            TrackerInstance.objects.filter(
                tracker=tracker,
                tracking_date__range=(start_date, end_date)
            ).values_list('tracking_date', flat=True)
        )
        
        instances = []
        current = start_date
        
        with transaction.atomic():
            while current <= end_date:
                if current not in existing_dates:
                    instance = InstanceService.create_daily_instance(tracker, current)
                    instances.append(instance)
                    
                    if mark_missed and current < date.today():
                        instance.tasks.update(status='MISSED')
                
                current += timedelta(days=1)
        
        return instances
```

#### Editing Templates After Instances Exist

**Problem**: Change task description/points after instances created.

**Solution**: Instances snapshot template at creation time.

```python
# Add to TaskInstance model
class TaskInstance(SoftDeleteModel):
    # ... existing fields ...
    
    # Snapshot fields (copied from template at creation)
    snapshot_description = models.CharField(max_length=500, blank=True)
    snapshot_points = models.IntegerField(default=0)
    snapshot_weight = models.IntegerField(default=1)
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            self.snapshot_description = self.template.description
            self.snapshot_points = self.template.points
            self.snapshot_weight = self.template.weight
        super().save(*args, **kwargs)
```

#### Task Status Oscillation

**Problem**: User toggles DONE → TODO → DONE repeatedly.

**Solution**: Track first and last completion times.

```python
# Add to TaskInstance
class TaskInstance(SoftDeleteModel):
    # ... existing fields ...
    first_completed_at = models.DateTimeField(null=True, blank=True)
    last_status_change = models.DateTimeField(auto_now=True)
    
    def set_status(self, new_status: str):
        """Properly handle status changes."""
        old_status = self.status
        self.status = new_status
        
        if new_status == 'DONE':
            now = timezone.now()
            if self.first_completed_at is None:
                self.first_completed_at = now
            self.completed_at = now
        elif old_status == 'DONE':
            # Was done, now not - keep completed_at for history
            pass
        
        self.save()
```

### 6.3 Goals & Progress Edge Cases

#### Goal Target Changed Mid-Way

**Problem**: Target goes from 21 → 30 days.

**Solution**:
```python
class GoalService:
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
        
        GoalService.update_goal_progress(goal)
        
        return {
            'old_target': old_target,
            'new_target': new_target,
            'status_changed': was_achieved and goal.status != 'achieved'
        }
```

#### Goal Linked to Deleted Items

**Problem**: Soft-delete template that's in GoalTaskMapping.

**Solution**: Filter deleted items in progress calculation.

```python
    @staticmethod
    def update_goal_progress(goal: Goal) -> dict:
        # Filter out deleted templates
        mappings = goal.task_mappings.filter(
            template__deleted_at__isnull=True
        ).select_related('template')
        
        # ... rest of calculation excludes deleted items
```

#### Multiple Goals Sharing Same Tasks

**Problem**: One template mapped to two goals.

**Solution**: Each completion counts fully for each goal (additive model).

```python
# This is the default behavior - no change needed.
# In update_goal_progress, each goal calculates independently.
# Alternative: Use contribution_weight to split (e.g., 0.5 each)
```

### 6.4 Soft Delete & Restore Edge Cases

#### Restore with Conflicts

**Problem**: Restore tracker whose name now conflicts.

**Solution**:
```python
class TrackerService:
    @staticmethod
    def restore_tracker(tracker_id: str, user_id: int) -> dict:
        """Restore with conflict handling."""
        tracker = TrackerDefinition.objects.get(
            tracker_id=tracker_id,
            user_id=user_id
        )
        
        if tracker.deleted_at is None:
            return {'error': 'Tracker is not deleted'}
        
        # Check for name conflict
        conflict = TrackerDefinition.objects.filter(
            user_id=user_id,
            name=tracker.name,
            deleted_at__isnull=True
        ).exists()
        
        if conflict:
            tracker.name = f"{tracker.name} (Restored)"
        
        tracker.restore()
        
        # Also restore children
        TrackerInstance.objects.filter(tracker=tracker).update(deleted_at=None)
        TaskInstance.objects.filter(tracker_instance__tracker=tracker).update(deleted_at=None)
        
        return {'success': True, 'renamed': conflict}
```

#### Soft Delete Chain

**Problem**: Parent deleted but children orphaned.

**Solution**: Cascade soft-delete.

```python
class TrackerDefinition(SoftDeleteModel):
    def soft_delete(self):
        """Cascade soft delete to all children."""
        super().soft_delete()
        
        # Soft delete all instances and their tasks
        self.instances.update(deleted_at=timezone.now())
        TaskInstance.objects.filter(
            tracker_instance__tracker=self
        ).update(deleted_at=timezone.now())
        
        # Soft delete notes
        self.notes.update(deleted_at=timezone.now())
```

### 6.5 Preferences & Notifications Edge Cases

#### Reminder Time Null

**Problem**: `daily_reminder_enabled=True` but `daily_reminder_time=None`.

**Solution**: Default fallback in notification service.

```python
class NotificationService:
    DEFAULT_REMINDER_TIME = time(8, 0)  # 8 AM
    
    @staticmethod
    def get_reminder_time(user_id: int) -> time:
        try:
            prefs = UserPreferences.objects.get(user_id=user_id)
            return prefs.daily_reminder_time or NotificationService.DEFAULT_REMINDER_TIME
        except UserPreferences.DoesNotExist:
            return NotificationService.DEFAULT_REMINDER_TIME
```

#### Over-Notification

**Problem**: 5 trackers = 5 notifications at 8 AM.

**Solution**: Aggregate notifications.

```python
    @staticmethod
    def send_daily_reminder(user_id: int) -> Notification | None:
        """Send ONE aggregated morning reminder."""
        # Instead of per-tracker, aggregate all
        today = date.today()
        
        tracker_summaries = []
        total_tasks = 0
        
        trackers = TrackerDefinition.objects.filter(
            user_id=user_id,
            status='active',
            deleted_at__isnull=True
        )
        
        for tracker in trackers:
            task_count = TaskInstance.objects.filter(
                tracker_instance__tracker=tracker,
                tracker_instance__tracking_date=today,
                status='TODO',
                deleted_at__isnull=True
            ).count()
            
            if task_count > 0:
                tracker_summaries.append(f"{tracker.name}: {task_count}")
                total_tasks += task_count
        
        if total_tasks == 0:
            return None
        
        message = f"You have {total_tasks} tasks across {len(tracker_summaries)} trackers today."
        
        return Notification.objects.create(
            user_id=user_id,
            type='reminder',
            title='🌅 Your Day Ahead',
            message=message,
            link='/today'
        )
```

### 6.6 Sharing & Security Edge Cases

#### Expired but Cached Links

**Problem**: Browser caches share link after expiry.

**Solution**: Always validate server-side.

```python
# core/services/share_service.py

class ShareService:
    @staticmethod
    def validate_and_use(token: str, password: str = None) -> tuple[TrackerDefinition | None, str]:
        """
        Validate share link and increment usage.
        
        Returns:
            Tuple of (tracker or None, error_message)
        """
        from django.db import transaction
        import hashlib
        
        try:
            share = ShareLink.objects.select_for_update().get(token=token)
        except ShareLink.DoesNotExist:
            return None, "Invalid share link"
        
        if not share.is_active:
            return None, "Share link has been deactivated"
        
        if share.is_expired:
            return None, "Share link has expired"
        
        if share.max_uses and share.use_count >= share.max_uses:
            return None, "Share link usage limit reached"
        
        if share.password_hash:
            if not password:
                return None, "Password required"
            if hashlib.sha256(password.encode()).hexdigest() != share.password_hash:
                return None, "Invalid password"
        
        with transaction.atomic():
            share.use_count = F('use_count') + 1
            share.save(update_fields=['use_count'])
        
        return share.tracker, ""
```

#### Concurrent Use Count

**Problem**: Race condition with max_uses=1.

**Solution**: Select for update (shown above).

### 6.7 Performance Edge Cases

#### Heavy Goal Recalculation

**Problem**: Goal scans all instances on every update.

**Solution**: Incremental updates via signals.

```python
# core/signals/task_signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from core.models import TaskInstance, GoalTaskMapping
from core.services.goal_service import GoalService

@receiver(post_save, sender=TaskInstance)
def update_goals_on_task_change(sender, instance, **kwargs):
    """Incrementally update linked goals when task changes."""
    # Find goals linked to this task's template
    mappings = GoalTaskMapping.objects.filter(
        template=instance.template
    ).select_related('goal')
    
    for mapping in mappings:
        GoalService.update_goal_progress(mapping.goal)

# Note: For very high volume, use async task queue:
# from celery import shared_task
# @receiver(post_save, sender=TaskInstance)
# def trigger_goal_update(sender, instance, **kwargs):
#     update_goal_async.delay(instance.template_id)
```

---

## 7. API Endpoints Specification

### 7.1 Trackers API

```
GET    /api/v1/trackers/                  - List user's trackers
POST   /api/v1/trackers/                  - Create tracker
GET    /api/v1/trackers/{id}/             - Get tracker detail
PUT    /api/v1/trackers/{id}/             - Update tracker
DELETE /api/v1/trackers/{id}/             - Soft delete tracker
POST   /api/v1/trackers/{id}/restore/     - Restore deleted
POST   /api/v1/trackers/{id}/clone/       - Duplicate tracker
POST   /api/v1/trackers/{id}/change-mode/ - Change time_mode
```

### 7.2 Instances API

```
GET    /api/v1/trackers/{id}/instances/          - List instances
POST   /api/v1/trackers/{id}/instances/          - Create instance
GET    /api/v1/trackers/{id}/instances/{date}/   - Get by date
POST   /api/v1/trackers/{id}/instances/generate/ - Generate for range
POST   /api/v1/trackers/{id}/instances/fill/     - Fill missing gaps
```

### 7.3 Tasks API

```
GET    /api/v1/tasks/today/              - Today's tasks (all trackers)
GET    /api/v1/tasks/{instance_id}/      - Tasks for instance
PATCH  /api/v1/tasks/{task_id}/status/   - Update status
POST   /api/v1/tasks/{task_id}/note/     - Add note
POST   /api/v1/tasks/bulk-update/        - Batch status update
```

### 7.4 Goals API

```
GET    /api/v1/goals/                    - List goals
POST   /api/v1/goals/                    - Create goal
GET    /api/v1/goals/{id}/               - Goal detail + insights
PATCH  /api/v1/goals/{id}/               - Update goal
DELETE /api/v1/goals/{id}/               - Delete goal
POST   /api/v1/goals/{id}/mappings/      - Add task mapping
DELETE /api/v1/goals/{id}/mappings/{template_id}/ - Remove mapping
POST   /api/v1/goals/{id}/recalculate/   - Force progress recalc
```

### 7.5 Analytics API

```
GET    /api/v1/analytics/daily/{date}/   - Daily summary
GET    /api/v1/analytics/weekly/{date}/  - Weekly summary
GET    /api/v1/analytics/tracker/{id}/   - Tracker analytics
GET    /api/v1/analytics/heatmap/{year}/ - Year heatmap
GET    /api/v1/analytics/streaks/        - All user streaks
GET    /api/v1/analytics/insights/       - AI insights
```

### 7.6 Notifications API

```
GET    /api/v1/notifications/            - List notifications
GET    /api/v1/notifications/unread-count/ - Unread count
POST   /api/v1/notifications/mark-read/  - Mark all read
PATCH  /api/v1/notifications/{id}/       - Mark single read
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# core/tests/test_streak_service.py

from datetime import date, timedelta
from django.test import TestCase
from core.models import TrackerDefinition, TrackerInstance, TaskInstance, TaskTemplate
from core.services.streak_service import StreakService

class StreakServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('test', 'test@test.com', 'pw')
        self.tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Test Tracker',
            time_mode='daily'
        )
        self.template = TaskTemplate.objects.create(
            tracker=self.tracker,
            description='Test Task'
        )
    
    def test_streak_counts_consecutive_days(self):
        # Create 5 consecutive days, all 100% complete
        today = date.today()
        for i in range(5):
            d = today - timedelta(days=i)
            instance = TrackerInstance.objects.create(
                tracker=self.tracker,
                tracking_date=d,
                period_start=d,
                period_end=d
            )
            TaskInstance.objects.create(
                tracker_instance=instance,
                template=self.template,
                status='DONE'
            )
        
        result = StreakService.calculate_streak(
            self.tracker.tracker_id, 
            self.user.id
        )
        
        self.assertEqual(result.current_streak, 5)
        self.assertTrue(result.streak_active)
    
    def test_streak_breaks_on_missed_day(self):
        today = date.today()
        
        # Day 1 and 2: complete
        for i in [0, 1]:
            d = today - timedelta(days=i)
            instance = TrackerInstance.objects.create(
                tracker=self.tracker, tracking_date=d,
                period_start=d, period_end=d
            )
            TaskInstance.objects.create(
                tracker_instance=instance,
                template=self.template,
                status='DONE'
            )
        
        # Day 3: skip (gap)
        
        # Day 4: complete
        d = today - timedelta(days=3)
        instance = TrackerInstance.objects.create(
            tracker=self.tracker, tracking_date=d,
            period_start=d, period_end=d
        )
        TaskInstance.objects.create(
            tracker_instance=instance,
            template=self.template,
            status='DONE'
        )
        
        result = StreakService.calculate_streak(
            self.tracker.tracker_id, 
            self.user.id
        )
        
        self.assertEqual(result.current_streak, 2)  # Only last 2 days
```

### 8.2 Integration Tests

```python
# core/tests/test_goal_integration.py

class GoalIntegrationTest(TestCase):
    def test_goal_progress_updates_on_task_completion(self):
        # Setup
        user = User.objects.create_user('test', 'test@test.com', 'pw')
        tracker = TrackerDefinition.objects.create(user=user, name='Test')
        template = TaskTemplate.objects.create(tracker=tracker, description='Task')
        
        goal = Goal.objects.create(
            user=user,
            tracker=tracker,
            title='Complete 10 tasks',
            target_value=10,
            unit='completions'
        )
        GoalTaskMapping.objects.create(goal=goal, template=template)
        
        # Create instances and complete tasks
        for i in range(5):
            instance = TrackerInstance.objects.create(
                tracker=tracker,
                tracking_date=date.today() - timedelta(days=i),
                period_start=date.today() - timedelta(days=i),
                period_end=date.today() - timedelta(days=i)
            )
            task = TaskInstance.objects.create(
                tracker_instance=instance,
                template=template,
                status='DONE'
            )
        
        # Verify goal updated
        goal.refresh_from_db()
        GoalService.update_goal_progress(goal)
        
        self.assertEqual(goal.current_value, 5)
        self.assertEqual(goal.progress, 50)  # 5/10 = 50%
```

### 8.3 Edge Case Tests

```python
# core/tests/test_edge_cases.py

class EdgeCaseTests(TestCase):
    def test_timezone_boundary_handling(self):
        """Ensure tasks near midnight don't shift days."""
        pass
    
    def test_restore_with_name_conflict(self):
        """Verify restored tracker gets renamed if conflict exists."""
        pass
    
    def test_goal_with_deleted_template(self):
        """Ensure deleted templates don't affect goal calculation."""
        pass
    
    def test_concurrent_share_link_usage(self):
        """Verify race condition handling for max_uses."""
        pass
```

---

## 9. Migration Plan

### Phase 1: Services Layer (Week 1-2)
- [ ] Create `core/services/` directory structure
- [ ] Implement `instance_service.py`
- [ ] Implement `streak_service.py`  
- [ ] Implement `goal_service.py`
- [ ] Write unit tests for each service

### Phase 2: Signals & Background Tasks (Week 2-3)
- [ ] Set up Django signals for goal updates
- [ ] Configure Celery for scheduled tasks
- [ ] Implement notification scheduling
- [ ] Add `notification_service.py`

### Phase 3: Analytics (Week 3-4)
- [ ] Implement `analytics_service.py`
- [ ] Add heatmap data endpoints
- [ ] Add streak summary endpoints
- [ ] Create insights algorithms

### Phase 4: API Enhancement (Week 4-5)
- [ ] Update existing views to use services
- [ ] Add missing endpoints
- [ ] Add batch operations
- [ ] Write integration tests

### Phase 5: Edge Cases & Polish (Week 5-6)
- [ ] Implement all edge case handlers
- [ ] Add model field additions (snapshots, etc.)
- [ ] Create database migrations
- [ ] Performance testing
- [ ] Documentation

---

## Appendix: Additional Edge Cases Discovered

### A.1 Instance Without Templates
**Problem**: Create TrackerInstance when tracker has no templates.
**Solution**: Allow empty instances, show "No tasks defined" in UI.

### A.2 Template Deletion Mid-Day
**Problem**: Template deleted after today's instance created.
**Solution**: TaskInstance keeps reference (soft-delete cascade).

### A.3 Goal Date in Past
**Problem**: Goal created with target_date already passed.
**Solution**: Validate on creation, or mark immediately as 'abandoned'.

### A.4 Negative Points
**Problem**: Template points set to negative.
**Solution**: Validate `points >= 0` on save.

### A.5 Empty Search Query
**Problem**: User submits empty search.
**Solution**: Return recent items instead of empty results.

### A.6 Very Long Note Content
**Problem**: DayNote content is massive.
**Solution**: Add `max_length` validation or truncate for analytics.

### A.7 Circular Entity Relations
**Problem**: Task A depends_on Task B depends_on Task A.
**Solution**: Validate no cycles on EntityRelation creation.

### A.8 Orphaned GoalTaskMapping
**Problem**: Template deleted, mapping remains.
**Solution**: Use on_delete=CASCADE (already configured).

### A.9 User Account Deletion
**Problem**: User deleted, data orphaned.
**Solution**: CASCADE configured on user FKs.

### A.10 Duplicate Share Tokens
**Problem**: UUID collision on token.
**Solution**: Regenerate on unique constraint error.

---

**End of Implementation Plan**

*Document Version: 1.0*
*Total Estimated Development Time: 6 weeks*
*Priority: P0 features first, then P1, then P2*
