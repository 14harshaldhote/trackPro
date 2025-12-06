"""
iOS-Specific API Views
Endpoints for iOS Widgets and Siri Shortcuts integration
"""
import json
from datetime import date, datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.models import TaskInstance, TrackerDefinition, TaskTemplate
from core.services import instance_service as services
from core.utils.ios_helpers import (
    format_widget_timeline_entry,
    format_siri_response,
    create_widget_snapshot,
    format_siri_task_list
)
from core.utils.response_helpers import UXResponse


# ============================================================================
# WIDGET TIMELINE ENDPOINTS
# ============================================================================

@login_required
@require_GET
def widget_today(request):
    """
    Widget timeline: Today's tasks summary.
    
    Optimized for iOS WidgetKit - includes caching headers.
    Widget sizes: small (progress ring), medium (3 tasks), large (6 tasks + streak)
    """
    widget_size = request.GET.get('size', 'small')  # small, medium, large
    
    # Create widget snapshot
    snapshot = create_widget_snapshot(request.user, widget_size)
    
    response = JsonResponse(snapshot)
    
    # Add caching headers for widget efficiency
    # Widgets refresh every 15 minutes minimum
    response['Cache-Control'] = 'public, max-age=900'  # 15 minutes
    response['Expires'] = (datetime.now() + timedelta(minutes=15)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    return response


@login_required
@require_GET  
def widget_timeline(request):
    """
    Widget timeline entries for the next 24 hours.
    
    iOS WidgetKit uses timeline to know when to refresh widgets.
    Provides entries for morning (6am), afternoon (12pm), evening (6pm).
    """
    today = date.today()
    now = datetime.now()
    
    # Get today's tasks
    tasks_qs = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user,
        tracker_instance__period_start__lte=today,
        tracker_instance__period_end__gte=today
    ).select_related('template', 'tracker_instance__tracker')
    
    task_data = [{
        'id': str(t.task_instance_id),
        'description': t.template.description,
        'status': t.status,
        'tracker': t.tracker_instance.tracker.name,
        'completed': t.status == 'DONE'
    } for t in tasks_qs]
    
    # Create timeline entries
    timeline_entries = []
    
    # Entry 1: Current state (now)
    timeline_entries.append(format_widget_timeline_entry(
        tasks=task_data,
        date=now,
        relevance_score=1.0
    ))
    
    # Entry 2: Afternoon update (12pm)
    noon_today = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if noon_today > now:
        timeline_entries.append(format_widget_timeline_entry(
            tasks=task_data,
            date=noon_today,
            relevance_score=0.8
        ))
    
    # Entry 3: Evening update (6pm)
    evening_today = now.replace(hour=18, minute=0, second=0, microsecond=0)
    if evening_today > now:
        timeline_entries.append(format_widget_timeline_entry(
            tasks=task_data,
            date=evening_today,
            relevance_score=0.9  # High relevance - end of day summary
        ))
    
    # Entry 4: Tomorrow morning (6am)
    tomorrow_morning = (now + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    timeline_entries.append(format_widget_timeline_entry(
        tasks=[],  # Tomorrow's tasks not created yet
        date=tomorrow_morning,
        relevance_score=0.7
    ))
    
    return JsonResponse({
        'timeline': timeline_entries,
        'policy': {
            'refresh_interval': 900,  # 15 minutes in seconds
            'expiration': (now + timedelta(hours=24)).isoformat()
        }
    })


# ============================================================================
# SIRI SHORTCUTS INTENT ENDPOINTS
# ============================================================================

@login_required
@require_POST
def siri_complete_task(request):
    """
    Siri Intent: Complete a task by name.
    
    Usage: "Hey Siri, complete morning workout in Tracker Pro"
    """
    try:
        data = json.loads(request.body)
        task_name = data.get('task_name', '').strip()
        
        if not task_name:
            return JsonResponse(
                format_siri_response(
                    spoken_text="I didn't catch the task name. Can you try again?",
                    success=False
                ),
                status=400
            )
        
        # Find matching task (case-insensitive partial match)
        today = date.today()
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__lte=today,
            tracker_instance__period_end__gte=today,
            template__description__icontains=task_name,
            status__in=['TODO', 'IN_PROGRESS']
        ).select_related('template')
        
        if not tasks.exists():
            return JsonResponse(
                format_siri_response(
                    spoken_text=f"I couldn't find a pending task matching '{task_name}'.",
                    success=False
                )
            )
        
        # Complete the first matching task
        task = tasks.first()
        task.status = 'DONE'
        task.completed_at = timezone.now()
        task.save()
        
        return JsonResponse(
            format_siri_response(
                spoken_text=f"Done! I've marked '{task.template.description}' as complete.",
                display_title="✓ Task Completed",
                display_subtitle=task.template.description
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I had trouble completing that task.",
                success=False
            ),
            status=500
        )


@login_required
@require_POST
def siri_add_task(request):
    """
    Siri Intent: Add a new task.
    
    Usage: "Hey Siri, add 'buy groceries' to my daily tracker in Tracker Pro"
    """
    try:
        data = json.loads(request.body)
        task_description = data.get('task_description', '').strip()
        tracker_name = data.get('tracker_name', '').strip()
        
        if not task_description:
            return JsonResponse(
                format_siri_response(
                    spoken_text="What task would you like to add?",
                    success=False
                ),
                status=400
            )
        
        # Find tracker
        if tracker_name:
            tracker = TrackerDefinition.objects.filter(
                user=request.user,
                name__icontains=tracker_name,
                status='active'
            ).first()
        else:
            # Use the most recently active tracker
            tracker = TrackerDefinition.objects.filter(
                user=request.user,
                status='active'
            ).order_by('-updated_at').first()
        
        if not tracker:
            return JsonResponse(
                format_siri_response(
                    spoken_text="I couldn't find that tracker. Which tracker should I add this to?",
                    success=False
                ),
                status=404
            )
        
        # Ensure tracker instance for today
        today = date.today()
        tracker_instance = services.ensure_tracker_instance(tracker.tracker_id, today, request.user)
        
        if isinstance(tracker_instance, dict):
            from core.models import TrackerInstance
            tracker_instance = TrackerInstance.objects.get(instance_id=tracker_instance['instance_id'])
        
        # Create task template and instance
        template = TaskTemplate.objects.create(
            tracker=tracker,
            description=task_description,
            category='',
            weight=1,
            time_of_day='anytime',
            is_recurring=False
        )
        
        TaskInstance.objects.create(
            tracker_instance=tracker_instance,
            template=template,
            status='TODO'
        )
        
        return JsonResponse(
            format_siri_response(
                spoken_text=f"Got it! I've added '{task_description}' to {tracker.name}.",
                display_title="✓ Task Added",
                display_subtitle=f"{task_description} → {tracker.name}"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't add that task right now.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_today_summary(request):
    """
    Siri Intent: Get today's task summary.
    
    Usage: "Hey Siri, what are my tasks today in Tracker Pro?"
    """
    try:
        today = date.today()
        
        # Get today's tasks
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__lte=today,
            tracker_instance__period_end__gte=today
        ).select_related('template', 'tracker_instance__tracker')
        
        task_data = [{
            'description': t.template.description,
            'status': t.status,
            'tracker': t.tracker_instance.tracker.name
        } for t in tasks]
        
        spoken_response = format_siri_task_list(task_data)
        
        completed = sum(1 for t in task_data if t['status'] == 'DONE')
        total = len(task_data)
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_response,
                display_title=f"{completed}/{total} Tasks Complete",
                display_subtitle=f"{total - completed} remaining"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't get your tasks right now.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_streak(request):
    """
    Siri Intent: Get current streak.
    
    Usage: "Hey Siri, what's my streak in Tracker Pro?"
    """
    try:
        from core.services.analytics_service import compute_user_streak
        
        streak_days = compute_user_streak(request.user)
        
        if streak_days == 0:
            spoken_text = "You don't have an active streak yet. Complete some tasks to start building one!"
        elif streak_days == 1:
            spoken_text = "You have a 1-day streak. Keep it going!"
        else:
            spoken_text = f"Awesome! You're on a {streak_days}-day streak. Keep up the great work!"
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"🔥 {streak_days}-Day Streak",
                display_subtitle="Keep it going!" if streak_days > 0 else "Start your streak today"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't check your streak right now.",
                success=False
            ),
            status=500
        )


# ============================================================================
# EXTENDED SIRI SHORTCUTS - Tracker, Weekly, Monthly, Analytics
# ============================================================================

@login_required
@require_GET
def siri_tracker_progress(request):
    """
    Siri Intent: Get progress for a specific tracker.
    
    Usage: "Hey Siri, what's my progress on Daily Habits in Tracker Pro?"
    """
    try:
        tracker_name = request.GET.get('tracker_name', '').strip()
        
        if not tracker_name:
            return JsonResponse(
                format_siri_response(
                    spoken_text="Which tracker would you like to check?",
                    success=False
                ),
                status=400
            )
        
        # Find tracker (fuzzy match)
        tracker = TrackerDefinition.objects.filter(
            user=request.user,
            name__icontains=tracker_name,
            status='active'
        ).first()
        
        if not tracker:
            return JsonResponse(
                format_siri_response(
                    spoken_text=f"I couldn't find a tracker called '{tracker_name}'.",
                    success=False
                ),
                status=404
            )
        
        # Get tracker tasks for today
        today = date.today()
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker=tracker,
            tracker_instance__period_start__lte=today,
            tracker_instance__period_end__gte=today
        )
        
        total = tasks.count()
        completed = tasks.filter(status='DONE').count()
        pending = total - completed
        percentage = int(completed / total * 100) if total > 0 else 0
        
        if total == 0:
            spoken_text = f"You don't have any tasks for {tracker.name} today."
        elif pending == 0:
            spoken_text = f"Great job! You've completed all {total} tasks in {tracker.name}."
        else:
            spoken_text = f"In {tracker.name}, you've completed {completed} out of {total} tasks. That's {percentage}% done. {pending} remaining."
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"{tracker.name}: {percentage}%",
                display_subtitle=f"{completed}/{total} complete"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't get that tracker's progress.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_weekly_summary(request):
    """
    Siri Intent: Get this week's summary.
    
    Usage: "Hey Siri, what's my weekly summary in Tracker Pro?"
    """
    try:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        # Get week's tasks
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__gte=week_start,
            tracker_instance__period_start__lte=week_end
        )
        
        total = tasks.count()
        completed = tasks.filter(status='DONE').count()
        completion_rate = int(completed / total * 100) if total > 0 else 0
        
        # Calculate daily average
        days_elapsed = (today - week_start).days + 1
        avg_per_day = completed / days_elapsed if days_elapsed > 0 else 0
        
        if total == 0:
            spoken_text = "You don't have any tasks logged this week yet."
        else:
            spoken_text = f"This week, you've completed {completed} out of {total} tasks. That's a {completion_rate}% completion rate. You're averaging {avg_per_day:.1f} completed tasks per day."
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"Week: {completion_rate}% Complete",
                display_subtitle=f"{completed}/{total} tasks • {avg_per_day:.1f}/day avg"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't get your weekly summary.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_monthly_summary(request):
    """
    Siri Intent: Get this month's summary.
    
    Usage: "Hey Siri, show me my monthly report in Tracker Pro"
    """
    try:
        today = date.today()
        month_start = today.replace(day=1)
        
        # Calculate month end
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        # Get month's tasks
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__gte=month_start,
            tracker_instance__period_start__lte=month_end
        )
        
        total = tasks.count()
        completed = tasks.filter(status='DONE').count()
        completion_rate = int(completed / total * 100) if total > 0 else 0
        
        # Calculate daily average
        days_in_month = (today - month_start).days + 1
        avg_per_day = completed / days_in_month if days_in_month > 0 else 0
        
        month_name = today.strftime('%B')
        
        if total == 0:
            spoken_text = f"You don't have any tasks logged for {month_name} yet."
        else:
            spoken_text = f"In {month_name}, you've completed {completed} out of {total} tasks. That's {completion_rate}%. You're averaging {avg_per_day:.1f} completed tasks per day."
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"{month_name}: {completion_rate}%",
                display_subtitle=f"{completed}/{total} tasks • {avg_per_day:.1f}/day"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't get your monthly summary.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_completion_rate(request):
    """
    Siri Intent: Get overall completion rate.
    
    Usage: "Hey Siri, what's my completion rate in Tracker Pro?"
    """
    try:
        # Last 30 days
        thirty_days_ago = date.today() - timedelta(days=30)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__gte=thirty_days_ago
        )
        
        total = tasks.count()
        completed = tasks.filter(status='DONE').count()
        rate = int(completed / total * 100) if total > 0 else 0
        
        if total == 0:
            spoken_text = "You don't have enough data yet. Start completing tasks to build your completion rate!"
        elif rate >= 80:
            spoken_text = f"Excellent! Your completion rate is {rate}% over the last 30 days. You're crushing it!"
        elif rate >= 60:
            spoken_text = f"Great work! Your completion rate is {rate}% over the last 30 days. Keep it up!"
        elif rate >= 40:
            spoken_text = f"Your completion rate is {rate}% over the last 30 days. There's room for improvement!"
        else:
            spoken_text = f"Your completion rate is {rate}% over the last 30 days. Let's work on building that up!"
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"Completion Rate: {rate}%",
                display_subtitle=f"Last 30 days • {completed}/{total} tasks"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't calculate your completion rate.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_whats_next(request):
    """
    Siri Intent: Get next pending task.
    
    Usage: "Hey Siri, what's next on my list in Tracker Pro?"
    """
    try:
        today = date.today()
        
        # Get next pending task (by priority: time of day, then weight)
        time_order = {'morning': 0, 'afternoon': 1, 'evening': 2, 'night': 3, 'anytime': 4}
        
        pending_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__lte=today,
            tracker_instance__period_end__gte=today,
            status__in=['TODO', 'IN_PROGRESS']
        ).select_related('template', 'tracker_instance__tracker')
        
        if not pending_tasks.exists():
            return JsonResponse(
                format_siri_response(
                    spoken_text="You're all caught up! No pending tasks right now.",
                    display_title="✓ All Done!",
                    display_subtitle="No pending tasks"
                )
            )
        
        # Sort by time of day, then weight
        sorted_tasks = sorted(
            pending_tasks,
            key=lambda t: (time_order.get(t.template.time_of_day, 4), -t.template.weight)
        )
        
        next_task = sorted_tasks[0]
        tracker_name = next_task.tracker_instance.tracker.name
        
        spoken_text = f"Next up: '{next_task.template.description}' from {tracker_name}."
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title="Next Task",
                display_subtitle=f"{next_task.template.description} • {tracker_name}"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't find your next task.",
                success=False
            ),
            status=500
        )


@login_required
@require_POST
def siri_skip_all_remaining(request):
    """
    Siri Intent: Skip all remaining tasks for today.
    
    Usage: "Hey Siri, skip all remaining tasks in Tracker Pro"
    """
    try:
        today = date.today()
        
        # Get all pending tasks for today
        pending_tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__lte=today,
            tracker_instance__period_end__gte=today,
            status__in=['TODO', 'IN_PROGRESS']
        )
        
        count = pending_tasks.count()
        
        if count == 0:
            return JsonResponse(
                format_siri_response(
                    spoken_text="You don't have any pending tasks to skip.",
                    display_title="No Pending Tasks",
                    display_subtitle="All caught up!"
                )
            )
        
        # Skip all
        pending_tasks.update(status='SKIPPED')
        
        spoken_text = f"Done! I've skipped {count} pending task{'s' if count != 1 else ''}."
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"Skipped {count} Task{'s' if count != 1 else ''}",
                display_subtitle="All remaining tasks skipped"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't skip those tasks.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_my_goals(request):
    """
    Siri Intent: Get active goals summary.
    
    Usage: "Hey Siri, what are my goals in Tracker Pro?"
    """
    try:
        from core.models import Goal
        
        # Get active goals
        goals = Goal.objects.filter(
            user=request.user,
            status='active'
        ).order_by('-progress')
        
        if not goals.exists():
            return JsonResponse(
                format_siri_response(
                    spoken_text="You don't have any active goals set. Create some to get started!",
                    display_title="No Active Goals",
                    display_subtitle="Create your first goal"
                )
            )
        
        # Format goals list
        goal_count = goals.count()
        if goal_count <= 3:
            goal_descriptions = []
            for g in goals:
                progress = int(g.progress)
                goal_descriptions.append(f"{g.title} at {progress}%")
            
            goals_text = ', '.join(goal_descriptions[:-1]) + (', and ' if len(goal_descriptions) > 1 else '') + goal_descriptions[-1]
            spoken_text = f"You have {goal_count} active goal{'s' if goal_count != 1 else ''}: {goals_text}."
        else:
            spoken_text = f"You have {goal_count} active goals. Check the app to see them all."
        
        # Calculate average progress
        avg_progress = sum(int(g.progress) for g in goals) / goal_count
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"{goal_count} Active Goal{'s' if goal_count != 1 else ''}",
                display_subtitle=f"Avg progress: {int(avg_progress)}%"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't get your goals right now.",
                success=False
            ),
            status=500
        )


@login_required
@require_GET
def siri_best_day(request):
    """
    Siri Intent: Get your best performing day of the week.
    
    Usage: "Hey Siri, what's my best day in Tracker Pro?"
    """
    try:
        # Last 30 days
        thirty_days_ago = date.today() - timedelta(days=30)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__gte=thirty_days_ago
        ).select_related('tracker_instance')
        
        # Analyze by day of week
        day_stats = {i: {'total': 0, 'completed': 0} for i in range(7)}
        
        for task in tasks:
            day = task.tracker_instance.period_start.weekday()
            day_stats[day]['total'] += 1
            if task.status == 'DONE':
                day_stats[day]['completed'] += 1
        
        # Find best day (minimum 5 tasks for reliability)
        day_rates = {}
        for day, stats in day_stats.items():
            if stats['total'] >= 5:
                day_rates[day] = stats['completed'] / stats['total']
        
        if not day_rates:
            return JsonResponse(
                format_siri_response(
                    spoken_text="You don't have enough data yet. Keep tracking to discover your best day!",
                    display_title="Not Enough Data",
                    display_subtitle="Keep tracking to see patterns"
                )
            )
        
        best_day_num = max(day_rates, key=day_rates.get)
        best_rate = day_rates[best_day_num]
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        best_day_name = day_names[best_day_num]
        
        spoken_text = f"Your best day is {best_day_name}, with a {int(best_rate * 100)}% completion rate!"
        
        return JsonResponse(
            format_siri_response(
                spoken_text=spoken_text,
                display_title=f"Best Day: {best_day_name}",
                display_subtitle=f"{int(best_rate * 100)}% completion rate"
            )
        )
        
    except Exception as e:
        return JsonResponse(
            format_siri_response(
                spoken_text="Sorry, I couldn't analyze your best day.",
                success=False
            ),
            status=500
        )
