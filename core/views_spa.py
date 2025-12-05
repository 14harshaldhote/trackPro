"""
SPA Views - Single Page Application endpoints
All views render through base_spa.html with AJAX panel loading
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from datetime import date, timedelta
import json

from core.models import TrackerDefinition, TrackerInstance, TaskInstance, Goal
from core.repositories import base_repository as crud
from core.services import instance_service as services
from core import analytics


# ============================================================================
# MAIN SPA SHELL
# ============================================================================

@login_required
def spa_shell(request):
    """
    Main SPA entry point. Renders the shell with sidebar.
    All content is loaded via AJAX into the main area.
    """
    user_trackers = TrackerDefinition.objects.filter(user=request.user).order_by('name')
    
    context = {
        'trackers': user_trackers,
        'user': request.user,
    }
    return render(request, 'base.html', context)


# ============================================================================
# PANEL ENDPOINTS (Return HTML fragments)
# ============================================================================

@login_required
def panel_dashboard(request):
    """Dashboard panel with quick stats"""
    from datetime import datetime
    today = date.today()
    now = datetime.now()
    user_trackers = TrackerDefinition.objects.filter(user=request.user, status='active')
    
    # Determine time of day for greeting
    hour = now.hour
    if hour < 12:
        time_of_day = 'morning'
    elif hour < 17:
        time_of_day = 'afternoon'
    else:
        time_of_day = 'evening'
    
    # Ensure instances exist for today
    for tracker in user_trackers:
        services.ensure_tracker_instance(tracker.tracker_id, today)
    
    # Get today's tasks across all trackers
    today_tasks = []
    completed_today = 0
    pending_today = 0
    
    for tracker in user_trackers:
        try:
            instance = TrackerInstance.objects.filter(
                tracker=tracker,
                period_start__lte=today,
                period_end__gte=today
            ).first()
            
            if instance:
                tasks = TaskInstance.objects.filter(tracker_instance=instance).select_related('template')
                for task in tasks:
                    today_tasks.append({
                        'id': task.task_instance_id,
                        'status': task.status,
                        'description': task.template.description,
                        'category': task.template.category,
                        'tracker_name': tracker.name,
                    })
                    if task.status == 'DONE':
                        completed_today += 1
                    elif task.status in ['TODO', 'IN_PROGRESS']:
                        pending_today += 1
        except Exception:
            pass
    
    # Compute streak
    streak = analytics.compute_user_streak(request.user) if hasattr(analytics, 'compute_user_streak') else 0
    
    # Build stats object
    total = completed_today + pending_today
    completion_rate = int(completed_today / total * 100) if total > 0 else 0
    
    stats = {
        'completed_today': completed_today,
        'pending_today': pending_today,
        'current_streak': streak,
        'active_trackers': user_trackers.count(),
        'completion_rate': completion_rate,
    }
    
    # Active trackers  - using model properties for progress/counts
    active_trackers = []
    for tracker in user_trackers[:6]:  # Limit to 6 for dashboard
        active_trackers.append({
            'id': tracker.tracker_id,
            'name': tracker.name,
            'time_period': tracker.time_period,
            'progress': tracker.progress,
            'completed_count': tracker.completed_count,
            'task_count': tracker.task_count,
        })
    
    context = {
        'time_of_day': time_of_day,
        'today': today,
        'stats': stats,
        'today_tasks': today_tasks[:10],  # Limit for dashboard
        'active_trackers': active_trackers,
    }
    
    return render(request, 'panels/dashboard.html', context)


@login_required  
def panel_today(request):
    """Today's tasks panel"""
    today = date.today()
    date_str = request.GET.get('date')
    if date_str:
        try:
            today = date.fromisoformat(date_str)
        except:
            pass
    
    user_trackers = TrackerDefinition.objects.filter(user=request.user)
    
    all_tasks = []
    for tracker in user_trackers:
        instance = services.ensure_tracker_instance(tracker.tracker_id, today)
        if instance:
            tasks = crud.get_instance_tasks(instance.instance_id)
            for task in tasks:
                task['tracker_name'] = tracker.name
                task['tracker_id'] = tracker.tracker_id
            all_tasks.extend(tasks)
    
    # Sort by time_of_day
    time_order = {'morning': 0, 'afternoon': 1, 'evening': 2, 'anytime': 3}
    all_tasks.sort(key=lambda t: time_order.get(t.get('time_of_day', 'anytime'), 3))
    
    context = {
        'today': today,
        'tasks': all_tasks,
        'is_today': today == date.today(),
        'prev_date': (today - timedelta(days=1)).isoformat(),
        'next_date': (today + timedelta(days=1)).isoformat(),
    }
    
    return render(request, 'panels/today.html', context)


@login_required
def panel_trackers_list(request):
    """Trackers list panel with pagination and complete tracker data"""
    PAGE_SIZE = 20
    
    page = int(request.GET.get('page', 1))
    offset = (page - 1) * PAGE_SIZE
    
    # Get all user trackers ordered by most recent activity
    all_trackers = TrackerDefinition.objects.filter(user=request.user).order_by('-updated_at', 'name')
    total_count = all_trackers.count()
    
    # Paginate
    paginated_trackers = all_trackers[offset:offset + PAGE_SIZE]
    has_more = total_count > (offset + PAGE_SIZE)
    next_page = page + 1 if has_more else None
    
    # Build tracker data with stats
    trackers = []
    for tracker in paginated_trackers:
        stats = analytics.compute_tracker_stats(tracker.tracker_id)
        
        # Calculate progress
        done = stats.get('done_count', 0)
        total = stats.get('total_count', 0)
        progress = int(done / total * 100) if total else 0
        
        trackers.append({
            'id': tracker.tracker_id,
            'tracker_id': tracker.tracker_id,
            'name': tracker.name,
            'description': tracker.description or '',
            'time_period': tracker.time_mode,
            'status': 'active' if tracker.is_active else 'paused',
            'progress': progress,
            'task_count': total,
            'updated_at': tracker.updated_at,
        })
    
    context = {
        'trackers': trackers,
        'total_count': total_count,
        'has_more': has_more,
        'next_page': next_page,
        'page': page,
    }
    
    return render(request, 'panels/trackers_list.html', context)


@login_required
def panel_tracker_detail(request, tracker_id):
    """Single tracker detail panel with pagination and grouping"""
    from django.core.paginator import Paginator
    from core.services.analytics_service import AnalyticsService
    from core.behavioral import get_insights, get_top_insight
    
    tracker = get_object_or_404(TrackerDefinition, tracker_id=tracker_id, user=request.user)
    
    today = date.today()
    page = int(request.GET.get('page', 1))
    group_by = request.GET.get('group', 'status')  # 'status', 'date', 'category'
    
    # Ensure today's instance exists
    instance = services.ensure_tracker_instance(tracker_id, today, request.user)
    
    # Get today's tasks
    today_tasks = TaskInstance.objects.filter(
        tracker_instance__tracker=tracker,
        tracker_instance__period_start__lte=today,
        tracker_instance__period_end__gte=today
    ).select_related('template').order_by('order')
    
    # Get historical tasks (last 30 days) with pagination
    thirty_days_ago = today - timedelta(days=30)
    historical_tasks = TaskInstance.objects.filter(
        tracker_instance__tracker=tracker,
        tracker_instance__period_start__gte=thirty_days_ago,
        tracker_instance__period_start__lt=today
    ).select_related('template', 'tracker_instance').order_by('-tracker_instance__period_start')
    
    paginator = Paginator(historical_tasks, 20)  # 20 tasks per page
    page_obj = paginator.get_page(page)
    
    # Group tasks by status
    grouped_tasks = {
        'todo': [t for t in today_tasks if t.status in ['TODO', 'IN_PROGRESS']],
        'done': [t for t in today_tasks if t.status == 'DONE'],
        'skipped': [t for t in today_tasks if t.status in ['SKIPPED', 'MISSED', 'BLOCKED']]
    }
    
    # Get analytics using service with user isolation
    analytics_svc = AnalyticsService(tracker_id=tracker_id, user=request.user)
    stats = analytics_svc.get_quick_summary()
    detailed_metrics = analytics_svc.get_detailed_metrics(window_days=7)
    
    # Get top insight for this tracker
    top_insight = get_top_insight(tracker_id)
    
    # Time distribution from historical data
    time_distribution = {
        'morning': TaskInstance.objects.filter(
            tracker_instance__tracker=tracker,
            template__time_of_day='morning'
        ).count(),
        'afternoon': TaskInstance.objects.filter(
            tracker_instance__tracker=tracker,
            template__time_of_day='afternoon'
        ).count(),
        'evening': TaskInstance.objects.filter(
            tracker_instance__tracker=tracker,
            template__time_of_day='evening'
        ).count()
    }
    
    context = {
        'tracker': tracker,
        'today_tasks': today_tasks,
        'grouped_tasks': grouped_tasks,
        'historical_tasks': page_obj,
        'page_obj': page_obj,
        'stats': stats,
        'detailed_metrics': detailed_metrics,
        'top_insight': top_insight,
        'time_distribution': time_distribution,
        'today': today,
        'group_by': group_by,
    }
    
    return render(request, 'panels/tracker_detail.html', context)


@login_required
def panel_week(request):
    """Week view panel with full statistics and time-of-day breakdown"""
    today = date.today()
    week_offset = int(request.GET.get('week', 0))
    
    # Calculate week boundaries with offset
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    
    # Navigation dates
    prev_week = start_of_week - timedelta(weeks=1)
    next_week = start_of_week + timedelta(weeks=1)
    
    # Week number
    week_number = start_of_week.isocalendar()[1]
    is_current_week = (week_offset == 0)
    
    user_trackers = TrackerDefinition.objects.filter(user=request.user)
    
    # Build days data with time-of-day breakdown
    days = []
    total_completed = 0
    total_tasks = 0
    best_day = None
    best_day_rate = 0
    
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_tasks = []
        
        # Time of day counters
        time_breakdown = {
            'morning': {'total': 0, 'completed': 0},
            'afternoon': {'total': 0, 'completed': 0},
            'evening': {'total': 0, 'completed': 0}
        }
        
        for tracker in user_trackers:
            # Ensure instance exists for this day
            instance = services.ensure_tracker_instance(tracker.tracker_id, day)
            if instance:
                instance_id = instance.instance_id if hasattr(instance, 'instance_id') else instance.get('instance_id')
                tasks = crud.get_instance_tasks(instance_id)
                for task in tasks:
                    task['tracker_name'] = tracker.name
                    task['tracker_id'] = tracker.tracker_id
                    day_tasks.append(task)
                    
                    # Categorize by time of day
                    tod = task.get('time_of_day', 'morning') or 'morning'
                    if tod in time_breakdown:
                        time_breakdown[tod]['total'] += 1
                        if task.get('status') == 'DONE':
                            time_breakdown[tod]['completed'] += 1
        
        done = sum(1 for t in day_tasks if t.get('status') == 'DONE')
        total = len(day_tasks)
        progress = int(done / total * 100) if total else 0
        
        total_completed += done
        total_tasks += total
        
        # Track best day
        if progress > best_day_rate:
            best_day_rate = progress
            best_day = day.strftime('%A')
        
        # Calculate time-of-day rates
        def calc_rate(breakdown):
            return int(breakdown['completed'] / breakdown['total'] * 100) if breakdown['total'] else 0
        
        days.append({
            'date': day,
            'is_today': day == today,
            'is_future': day > today,
            'tasks': day_tasks,
            'completed': done,
            'total': total,
            'progress': progress,
            # Time of day breakdown
            'morning_completed': time_breakdown['morning']['completed'],
            'morning_total': time_breakdown['morning']['total'],
            'morning_rate': calc_rate(time_breakdown['morning']),
            'afternoon_completed': time_breakdown['afternoon']['completed'],
            'afternoon_total': time_breakdown['afternoon']['total'],
            'afternoon_rate': calc_rate(time_breakdown['afternoon']),
            'evening_completed': time_breakdown['evening']['completed'],
            'evening_total': time_breakdown['evening']['total'],
            'evening_rate': calc_rate(time_breakdown['evening']),
        })
    
    # Calculate overall week stats
    completion_rate = int(total_completed / total_tasks * 100) if total_tasks else 0
    
    # Get user's current streak (aggregate across trackers)
    streak = 0
    for tracker in user_trackers:
        try:
            tracker_streaks = analytics.detect_streaks(tracker.tracker_id)
            streak_val = tracker_streaks.get('value', {})
            if isinstance(streak_val, dict):
                streak = max(streak, streak_val.get('current_streak', 0))
        except Exception:
            pass
    
    week_stats = {
        'completed': total_completed,
        'completion_rate': completion_rate,
        'best_day': best_day,
        'streak': streak
    }
    
    context = {
        'days': days,
        'week': days,  # Alias for template compatibility
        'week_stats': week_stats,
        'week_start': start_of_week,
        'week_end': end_of_week,
        'week_number': week_number,
        'is_current_week': is_current_week,
        'prev_week': prev_week,
        'next_week': next_week,
        'today': today,
        'start_of_week': start_of_week,  # Compatibility
    }
    
    return render(request, 'panels/week.html', context)


@login_required
def panel_month(request):
    """Month view panel with full calendar grid and tracker breakdown"""
    from calendar import monthrange, monthcalendar
    
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Ensure valid month/year
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1
    
    first_day = date(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    last_day = date(year, month, days_in_month)
    
    # Navigation
    prev_month_date = first_day - timedelta(days=1)
    next_month_date = last_day + timedelta(days=1)
    is_current_month = (year == today.year and month == today.month)
    
    user_trackers = TrackerDefinition.objects.filter(user=request.user)
    
    # Build calendar grid with padding for week alignment
    calendar_days = []
    
    # Get the weekday of the first day (0=Monday, 6=Sunday)
    # Template expects Sunday first, so adjust
    first_weekday = (first_day.weekday() + 1) % 7  # Convert to Sunday=0
    
    # Add padding days from prev month
    prev_month = first_day - timedelta(days=1)
    for i in range(first_weekday):
        padding_day = prev_month - timedelta(days=(first_weekday - 1 - i))
        calendar_days.append({
            'date': padding_day,
            'in_month': False,
            'is_today': False,
            'is_future': False,
            'total': 0,
            'completed': 0,
            'progress': 0
        })
    
    # Stats tracking
    total_tasks = 0
    total_completed = 0
    active_days = 0
    longest_streak = 0
    current_streak = 0
    
    # Per-tracker stats
    tracker_monthly = {t.tracker_id: {'name': t.name, 'id': t.id, 'total': 0, 'completed': 0} for t in user_trackers}
    
    # Add actual month days
    for day_num in range(1, days_in_month + 1):
        day = date(year, month, day_num)
        
        # Get completion for this day
        day_total = 0
        day_completed = 0
        
        for tracker in user_trackers:
            instance = services.ensure_tracker_instance(tracker.tracker_id, day)
            if instance:
                instance_id = instance.instance_id if hasattr(instance, 'instance_id') else instance.get('instance_id')
                tasks = crud.get_instance_tasks(instance_id)
                for task in tasks:
                    day_total += 1
                    tracker_monthly[tracker.tracker_id]['total'] += 1
                    if task.get('status') == 'DONE':
                        day_completed += 1
                        tracker_monthly[tracker.tracker_id]['completed'] += 1
        
        progress = int(day_completed / day_total * 100) if day_total else 0
        
        # Track stats
        total_tasks += day_total
        total_completed += day_completed
        if day_completed > 0:
            active_days += 1
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0
        
        calendar_days.append({
            'date': day,
            'in_month': True,
            'is_today': day == today,
            'is_future': day > today,
            'total': day_total,
            'completed': day_completed,
            'progress': progress
        })
    
    # Add padding days for next month to complete the grid
    remaining = (7 - len(calendar_days) % 7) % 7
    for i in range(remaining):
        padding_day = last_day + timedelta(days=(i + 1))
        calendar_days.append({
            'date': padding_day,
            'in_month': False,
            'is_today': False,
            'is_future': True,
            'total': 0,
            'completed': 0,
            'progress': 0
        })
    
    # Build tracker stats list
    tracker_stats = []
    for tracker_id, data in tracker_monthly.items():
        rate = int(data['completed'] / data['total'] * 100) if data['total'] else 0
        tracker_stats.append({
            'id': data['id'],
            'name': data['name'],
            'total': data['total'],
            'completed': data['completed'],
            'completion_rate': rate
        })
    tracker_stats.sort(key=lambda x: x['completion_rate'], reverse=True)
    
    month_stats = {
        'completion_rate': int(total_completed / total_tasks * 100) if total_tasks else 0,
        'total_tasks': total_tasks,
        'completed': total_completed,
        'longest_streak': longest_streak,
        'active_days': active_days
    }
    
    context = {
        'calendar_days': calendar_days,
        'month_data': calendar_days,  # Compatibility
        'month_stats': month_stats,
        'tracker_stats': tracker_stats,
        'current_month': first_day,
        'month_name': first_day.strftime('%B %Y'),
        'year': year,
        'month': month,
        'prev_month': prev_month_date,
        'next_month': next_month_date,
        'is_current_month': is_current_month,
        'today': today,
    }
    
    return render(request, 'panels/month.html', context)


@login_required
def panel_analytics(request):
    """Analytics panel with comprehensive behavioral analytics"""
    from core.services.analytics_service import AnalyticsService
    from core.behavioral import get_insights
    
    user_trackers = TrackerDefinition.objects.filter(user=request.user, status='active')
    
    # Initialize service with user isolation
    analytics_svc = AnalyticsService(user=request.user)
    
    # Get user overview stats
    overview = analytics_svc.get_user_overview()
    
    # Get tracker comparison
    tracker_comparison = analytics_svc.get_tracker_comparison()
    
    # Get forecast for next 7 days
    forecast = analytics_svc.get_forecast(days=7)
    
    # Get charts for top tracker
    charts = {}
    top_tracker = user_trackers.first()
    if top_tracker:
        tracker_analytics = AnalyticsService(tracker_id=top_tracker.tracker_id, user=request.user)
        charts = tracker_analytics.generate_charts()
    
    # Weekly comparison (this week vs last week)
    today = date.today()
    this_week = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user,
        tracker_instance__period_start__gte=today - timedelta(days=7)
    )
    last_week = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user,
        tracker_instance__period_start__gte=today - timedelta(days=14),
        tracker_instance__period_start__lt=today - timedelta(days=7)
    )
    
    this_week_completed = this_week.filter(status='DONE').count()
    this_week_total = this_week.count()
    last_week_completed = last_week.filter(status='DONE').count()
    last_week_total = last_week.count()
    
    week_comparison = {
        'this_week': {
            'completed': this_week_completed,
            'total': this_week_total,
            'rate': int(this_week_completed / this_week_total * 100) if this_week_total else 0
        },
        'last_week': {
            'completed': last_week_completed,
            'total': last_week_total,
            'rate': int(last_week_completed / last_week_total * 100) if last_week_total else 0
        },
        'change': ((this_week_completed / this_week_total) - (last_week_completed / last_week_total)) * 100 
                  if this_week_total and last_week_total else 0
    }
    
    context = {
        'trackers': user_trackers,
        'overview': overview,
        'tracker_comparison': tracker_comparison,
        'forecast': forecast,
        'charts': charts,
        'week_comparison': week_comparison,
        'total_completed': overview.get('completed_tasks', 0),
        'total_tasks': overview.get('total_tasks', 0),
        'completion_rate': int(overview.get('completion_rate', 0)),
    }
    
    return render(request, 'panels/analytics.html', context)


@login_required
def panel_goals(request):
    """Goals panel with Goal model integration"""
    from datetime import datetime, timedelta
    today = date.today()
    
    user_goals = Goal.objects.filter(user=request.user).select_related('tracker')
    
    active_goals = []
    completed_goals = []
    
    for goal in user_goals:
        goal_data = {
            'id': goal.goal_id,
            'name': goal.title,
            'icon': goal.icon,
            'tracker_name': goal.tracker.name if goal.tracker else 'No tracker',
            'progress': int(goal.progress),
            'target': goal.target_value or 100,
            'current': goal.current_value,
            'unit': goal.unit or 'tasks',
            'completed_at': goal.updated_at if goal.status == 'achieved' else None,
        }
        
        # Calculate days left
        if goal.target_date:
            days_left = (goal.target_date - today).days
            goal_data['days_left'] = max(0, days_left)
            
            # Calculate if on track
            if days_left > 0 and goal.target_value:
                expected_progress = ((goal.target_date - goal.created_at.date()).days - days_left) / (goal.target_date - goal.created_at.date()).days * 100
                goal_data['on_track'] = goal.progress >= expected_progress * 0.9  # 10% buffer
                goal_data['behind_by'] = f"{int(expected_progress - goal.progress)}%"
            else:
                goal_data['on_track'] = True
                goal_data['behind_by'] = ''
        else:
            goal_data['days_left'] = None
            goal_data['on_track'] = True
            goal_data['behind_by'] = ''
        
        if goal.status == 'achieved':
            completed_goals.append(goal_data)
        elif goal.status == 'active':
            active_goals.append(goal_data)
    
    context = {
        'active_goals': active_goals,
        'completed_goals': completed_goals,
    }
    return render(request, 'panels/goals.html', context)


@login_required
def panel_insights(request):
    """Insights panel with comprehensive behavioral analytics"""
    from core.behavioral import get_insights
    from core.services.analytics_service import AnalyticsService
    
    user_trackers = TrackerDefinition.objects.filter(user=request.user, status='active')
    today = date.today()
    
    # Collect all insights
    all_insights = []
    patterns = {'weekend_dip': False, 'morning_advantage': False, 'streak_risk': False}
    
    for tracker in user_trackers:
        try:
            tracker_insights = get_insights(tracker.tracker_id)
            for insight in tracker_insights:
                insight['tracker_name'] = tracker.name
                insight['tracker_id'] = tracker.tracker_id
                # Track patterns
                if insight.get('type') == 'weekend_dip':
                    patterns['weekend_dip'] = True
                elif insight.get('type') == 'morning_advantage':
                    patterns['morning_advantage'] = True
                elif insight.get('type') == 'streak_risk':
                    patterns['streak_risk'] = True
            all_insights.extend(tracker_insights)
        except Exception:
            pass
    
    # Sort by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    all_insights.sort(key=lambda x: severity_order.get(x.get('severity', 'low'), 3))
    
    # Categorize insights
    categorized = {
        'high': [i for i in all_insights if i.get('severity') == 'high'],
        'medium': [i for i in all_insights if i.get('severity') == 'medium'],
        'low': [i for i in all_insights if i.get('severity') == 'low']
    }
    
    # Build recommendations based on patterns
    recommendations = []
    if patterns['weekend_dip']:
        recommendations.append({
            'title': 'Weekend Strategy',
            'description': 'Consider lighter goals on weekends or schedule different activities.',
            'icon': '📅'
        })
    if patterns['streak_risk']:
        recommendations.append({
            'title': 'Protect Your Streaks',
            'description': 'Focus on completing at least one priority task to maintain momentum.',
            'icon': '🔥'
        })
    if not patterns['morning_advantage']:
        recommendations.append({
            'title': 'Try Morning Sessions',
            'description': 'Research shows cognitive performance peaks in the morning for most people.',
            'icon': '🌅'
        })
    
    # Week comparison using ORM
    this_week = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user,
        tracker_instance__period_start__gte=today - timedelta(days=7)
    )
    last_week = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user,
        tracker_instance__period_start__gte=today - timedelta(days=14),
        tracker_instance__period_start__lt=today - timedelta(days=7)
    )
    
    this_rate = this_week.filter(status='DONE').count() / this_week.count() * 100 if this_week.count() else 0
    last_rate = last_week.filter(status='DONE').count() / last_week.count() * 100 if last_week.count() else 0
    
    week_comparison = {
        'this_week_rate': int(this_rate),
        'last_week_rate': int(last_rate),
        'change': int(this_rate - last_rate),
        'improving': this_rate > last_rate
    }
    
    context = {
        'insights': all_insights,
        'categorized': categorized,
        'top_insight': all_insights[0] if all_insights else None,
        'insight_count': len(all_insights),
        'patterns': patterns,
        'recommendations': recommendations,
        'week_comparison': week_comparison,
    }
    return render(request, 'panels/insights.html', context)


@login_required
def panel_settings(request, section='general'):
    """Settings panels"""
    template_map = {
        'general': 'settings/general.html',
        'preferences': 'settings/preferences.html',
        'keyboard': 'settings/keyboard.html',
        'data': 'settings/data.html',
        'about': 'settings/about.html',
    }
    
    template = template_map.get(section, 'settings/general.html')
    
    context = {
        'user': request.user,
        'active': section,
    }
    
    return render(request, template, context)


@login_required
def panel_help(request):
    """Help center panel"""
    return render(request, 'panels/help.html', {})


@login_required
def panel_templates(request):
    """Templates library panel"""
    return render(request, 'panels/templates.html', {})


@login_required
def modal_view(request, modal_name):
    """
    Generic view to serve modal content.
    Loads templates from core/templates/modals/{modal_name}.html
    """
    template_name = f'modals/{modal_name}.html'
    
    # Context can be expanded based on modal_name if needed
    context = {
        'user': request.user,
    }
    
    # Specific context for certain modals
    if modal_name == 'add_task':
        # Get user's trackers for the dropdown
        context['trackers'] = TrackerDefinition.objects.filter(user=request.user)
        
    return render(request, template_name, context)


def panel_error_404(request):
    """404 error panel for SPA"""
    return render(request, 'panels/error_404.html', {
        'message': 'The page you are looking for could not be found.',
    }, status=404)


def panel_error_500(request):
    """500 error panel for SPA"""
    return render(request, 'panels/error_500.html', {
        'message': 'An unexpected error occurred. Please try again later.',
    }, status=500)
