"""
SPA Views - Single Page Application endpoints
All views render through base_spa.html with AJAX panel loading
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from datetime import date, timedelta
from functools import wraps
import json

from core.models import TrackerDefinition, TrackerInstance, TaskInstance, Goal
from core.repositories import base_repository as crud
from core.services import instance_service as services
from core import analytics
from core.utils.skeleton_helpers import generate_panel_skeleton, get_modal_config
from core.utils.constants import UI_COLORS, TOUCH_TARGET_MIN_SIZE
from core.services.tracker_service import TrackerService
from core.services.view_service import ViewService
from core.services.task_service import TaskService
from core.services.goal_service import GoalProgressService
from core.utils.error_handlers import handle_view_errors
from django.http import Http404


# ============================================================================
# SKELETON SUPPORT DECORATOR
# ============================================================================

def supports_skeleton(default_item_count=5):
    """
    Decorator to add skeleton support to panel views.
    When request contains ?skeleton=true, returns skeleton structure instead of full data.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check if skeleton-only request
            if request.GET.get('skeleton') == 'true':
                panel_type = view_func.__name__.replace('panel_', '')
                item_count = int(request.GET.get('count', default_item_count))
                
                skeleton = generate_panel_skeleton(panel_type, item_count)
                
                return JsonResponse({
                    'skeleton': True,
                    'structure': skeleton,
                    'estimated_load_time': 300  # ms
                })
            
            # Normal request - proceed with view
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# MAIN SPA SHELL
# ============================================================================

@login_required
@handle_view_errors
def spa_shell(request, **kwargs):
    """
    Main SPA entry point. Renders the shell with sidebar.
    All content is loaded via AJAX into the main area.
    Accepts **kwargs to handle legacy routes that pass tracker_id, etc.
    """
    # Use TrackerService
    tracker_svc = TrackerService()
    user_trackers = tracker_svc.get_active_trackers(request.user, order_by='name')
    
    context = {
        'trackers': user_trackers,
        'user': request.user,
    }
    return render(request, 'base.html', context)


# ============================================================================
# PANEL ENDPOINTS (Return HTML fragments)
# ============================================================================

@login_required
@supports_skeleton(default_item_count=8)
@handle_view_errors
def panel_dashboard(request):
    """Dashboard panel with quick stats, filtering, and skeleton support"""
    from datetime import datetime
    import calendar
    
    today = date.today()
    now = datetime.now()
    # Use TrackerService
    tracker_svc = TrackerService()
    user_trackers = tracker_svc.get_active_trackers(request.user)
    
    # Get filter period
    period = request.GET.get('period', 'daily')
    
    # Determine date range based on period
    start_date = today
    end_date = today
    period_title = "Today's Tasks"
    
    if period == 'weekly':
        start_date = today - timedelta(days=today.weekday()) # Monday
        end_date = start_date + timedelta(days=6) # Sunday
        period_title = "This Week's Tasks"
    elif period == 'monthly':
        start_date = today.replace(day=1)
        end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        period_title = "This Month's Tasks"
    elif period == 'all':
        start_date = today - timedelta(days=365) # Sort of arbitrary "all" for performance
        end_date = today + timedelta(days=365)
        period_title = "All Active Tasks"

    # Determine time of day for greeting
    hour = now.hour
    if hour < 12:
        time_of_day = 'morning'
    elif hour < 17:
        time_of_day = 'afternoon'
    else:
        time_of_day = 'evening'
    
    # Ensure instances exist for current period (at least today)
    if period == 'daily':
        for tracker in user_trackers:
            services.ensure_tracker_instance(tracker.tracker_id, today, request.user)
    
    # Get tasks across all trackers for the period using TaskService
    task_svc = TaskService()
    all_tasks = task_svc.get_all_tasks_for_user_range(request.user, start_date, end_date)
    
    dashboard_tasks = []
    completed_count = 0
    pending_count = 0
    
    for task in all_tasks:
        # Convert to display dict
        dashboard_tasks.append({
            'id': task.task_instance_id,
            'status': task.status,
            'description': task.template.description if task.template else '',
            'category': task.template.category if task.template else '',
            'tracker_name': task.tracker_instance.tracker.name if task.tracker_instance and task.tracker_instance.tracker else '',
            'weight': task.template.weight if task.template else 0,
            'created_at': task.created_at
        })
        
        if task.status == 'DONE':
            completed_count += 1
        elif task.status in ['TODO', 'IN_PROGRESS']:
            pending_count += 1
    
    # Sort tasks: Weight desc, then creation
    dashboard_tasks.sort(key=lambda x: (-x.get('weight', 0), x.get('created_at')))
    
    # Compute streak
    streak = analytics.compute_user_streak(request.user) if hasattr(analytics, 'compute_user_streak') else 0
    
    # Build stats object
    total = completed_count + pending_count
    completion_rate = int(completed_count / total * 100) if total > 0 else 0
    
    stats = {
        'completed_today': completed_count, # Label might stay 'today' or be dynamic
        'pending_today': pending_count,
        'current_streak': streak,
        'active_trackers': user_trackers.count(),
        'completion_rate': completion_rate,
    }
    
    # Active trackers - active stats
    # We can skip complex instance query and just list them, 
    # or use analytics service for quick stats.
    # For now, just listing active trackers is enough for dashboard list.
    active_trackers = []
    
    for tracker in user_trackers[:6]:
        # Calculate stats for this tracker in the period from all_tasks match
        # Using list comprehension since all_tasks is already fetched (prefetch/select_related should be minimal overhead)
        tracker_tasks = [t for t in all_tasks if t.tracker_instance.tracker_id == tracker.tracker_id]
        
        period_total = len(tracker_tasks)
        period_completed = sum(1 for t in tracker_tasks if t.status == 'DONE')
        period_progress = int(period_completed / period_total * 100) if period_total > 0 else 0
        
        active_trackers.append({
            'id': tracker.tracker_id,
            'name': tracker.name,
            'time_period': tracker.time_mode,
            'progress': period_progress,
            'completed_count': period_completed,
            'task_count': period_total,
        })
    
    context = {
        'time_of_day': time_of_day,
        'today': today,
        'stats': stats,
        'today_tasks': dashboard_tasks[:50], # Limit to avoid overload
        'active_trackers': active_trackers,
        'current_period': period,
        'period_title': period_title,
    }
    
    return render(request, 'panels/dashboard.html', context)


@login_required
@supports_skeleton(default_item_count=10)  
@handle_view_errors
def panel_today(request):
    """Today's tasks panel with iOS swipe actions and skeleton support"""
    today = date.today()
    date_str = request.GET.get('date')
    if date_str:
        try:
            today = date.fromisoformat(date_str)
        except:
            pass
    
    # Use TrackerService
    tracker_svc = TrackerService()
    user_trackers = tracker_svc.get_active_trackers(request.user)
    
    task_groups = []
    total_count = 0
    completed_count = 0
    pending_count = 0
    missed_count = 0
    
    for tracker in user_trackers:
        instance = services.ensure_tracker_instance(tracker.tracker_id, today)
        tasks = []
        if instance:
            instance_id = instance.instance_id if hasattr(instance, 'instance_id') else instance.get('instance_id')
            if instance_id:
                # Use InstanceService/Repository via Service
                # services is instance_service
                raw_tasks = services.get_tasks_for_instance(instance_id)
                
                # Format tasks using ViewService
                for task in raw_tasks:
                    enhanced_task = ViewService.format_task_for_list(task, tracker)
                    
                    if not enhanced_task: 
                        continue
                    
                    tasks.append(enhanced_task)
                    
                    # Update counts (using standardized keys from ViewService)
                    status = enhanced_task['status']
                    total_count += 1
                    if status == 'DONE':
                        completed_count += 1
                    elif status in ['TODO', 'IN_PROGRESS']:
                        pending_count += 1
                    elif status in ['MISSED', 'SKIPPED', 'BLOCKED']:
                        missed_count += 1

        if tasks:
            # Sort by time of day
            time_order = {'morning': 0, 'afternoon': 1, 'evening': 2, 'anytime': 3}
            tasks.sort(key=lambda t: time_order.get(t.get('time_of_day', 'anytime'), 3))
            
            group_completed = sum(1 for t in tasks if t.get('status') == 'DONE')
            
            task_groups.append({
                'tracker': tracker,
                'tasks': tasks,
                'total': len(tasks),
                'completed': group_completed
            })
            
    progress = int(completed_count / total_count * 100) if total_count > 0 else 0
    
    context = {
        'today': today,
        'task_groups': task_groups,
        'is_today': today == date.today(),
        'prev_day': today - timedelta(days=1),
        'next_day': today + timedelta(days=1),
        'total_count': total_count,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'missed_count': missed_count,
        'progress': progress,
        'day_note': '', 
    }
    
    return render(request, 'panels/today.html', context)


@login_required
@supports_skeleton(default_item_count=5)
@handle_view_errors
def panel_trackers_list(request):
    """
    List active user trackers with archived section.
    Fetch from Service Layer.
    """
    PAGE_SIZE = 6
    
    page = int(request.GET.get('page', 1))
    offset = (page - 1) * PAGE_SIZE
    
    # Get non-archived user trackers ordered by most recent activity
    tracker_svc = TrackerService()
    active_trackers_qs = tracker_svc.get_active_trackers(
        request.user, 
        order_by='-updated_at'
    )
    
    # Get archived trackers separately
    archived_trackers_qs = tracker_svc.get_archived_trackers(request.user)
    
    total_count = active_trackers_qs.count()
    
    # Paginate active trackers only
    paginated_trackers = active_trackers_qs[offset:offset + PAGE_SIZE]
    has_more = total_count > (offset + PAGE_SIZE)
    next_page = page + 1 if has_more else None
    
    # Build tracker data with stats
    trackers = []
    for tracker in paginated_trackers:
        trackers.append({
            'id': tracker.tracker_id,
            'tracker_id': tracker.tracker_id,
            'name': tracker.name,
            'description': tracker.description or '',
            'time_period': tracker.time_period,
            'status': tracker.status,
            'progress': tracker.progress,
            'task_count': tracker.task_count,
            'completed_count': tracker.completed_count,
            'updated_at': tracker.updated_at,
        })
    
    # Build archived tracker data
    archived_trackers = []
    for tracker in archived_trackers_qs:
        archived_trackers.append({
            'id': tracker.tracker_id,
            'name': tracker.name,
            'time_period': tracker.time_period,
        })
    
    context = {
        'trackers': trackers,
        'archived_trackers': archived_trackers,
        'total_count': total_count,
        'has_more': has_more,
        'next_page': next_page,
        'page': page,
    }
    
    return render(request, 'panels/trackers_list.html', context)


@login_required
@supports_skeleton(default_item_count=5)
@handle_view_errors
def panel_tracker_detail(request, tracker_id):
    """Detailed view of a specific tracker"""
    tracker_svc = TrackerService()
    instance_svc = services # Alias for instance_service
    task_svc = TaskService()
    view_svc = ViewService()

    tracker = tracker_svc.get_tracker_by_id(tracker_id, request.user)
    
    # Rest of logic...
    today = date.today()
    
    # 1. Today's Status (Service)
    # We need instance ID. get_tracker_by_id returns definition.
    # Check if instance exists for today
    instance = instance_svc.ensure_tracker_instance(tracker.tracker_id, today, request.user) 
    # ensure_tracker_instance returns ORM object or None/Dict? 
    # It returns TaskInstance (not TrackerInstance? No, ensure_tracker_instance returns TrackerInstance)
    # Refactored in Phase 2 to return ORM object.
    
    todays_tasks = []
    if instance:
        # Use TaskService
        todays_tasks_objs = task_svc.get_tasks_for_instance(instance.instance_id)
        # Format for view
        for t in todays_tasks_objs:
             todays_tasks.append(view_svc.format_task_for_list(t))
    
    # 2. Historical Stats (Service)
    # We need last 30 days history or simplified stats
    # get_tracker_stats in TaskService? 
    # Or use AnalyticsService for distribution
    
    # ... (Keep existing logic just remove try/except and add decorator)
    
    history_days = 30
    # start_date not needed for this call if passing days
    historical_tasks = task_svc.get_historical_tasks(tracker.tracker_id, history_days, today)
    
    # Compute completion rate manually or via service? 
    # Existing code used manual computation or analytics.
    # Let's preserve existing logic flow but cleaned.
    
    # ... (Assuming subsequent lines are fine)
    
    from django.core.paginator import Paginator
    from core.services.analytics_service import AnalyticsService
    from core.behavioral import get_insights, get_top_insight
    
    # Use TrackerService
    # tracker_svc = TrackerService() # Already instantiated above
    # try: # Removed by instruction
    #     tracker = tracker_svc.get_tracker_by_id(tracker_id, request.user) # Already called above
    # except TrackerDefinition.DoesNotExist: # Removed by instruction
    #     raise Http404("Tracker not found") # Removed by instruction
    
    # today = date.today() # Already defined above
    page = int(request.GET.get('page', 1))
    group_by = request.GET.get('group', 'status')  # 'status', 'date', 'category'
    
    # Ensure today's instance exists
    instance = services.ensure_tracker_instance(tracker_id, today, request.user)
    
    # Get today's tasks using InstanceService (via services alias)
    # This returns values compatible with template (ORM objects)
    today_tasks = services.get_tasks_for_instance(instance.instance_id)
    
    # Get historical tasks using TaskService
    task_svc = TaskService()
    historical_tasks = task_svc.get_historical_tasks(tracker_id, days=30, end_date=today)
    
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
    
    # Time distribution from analytics service
    time_distribution = analytics_svc.get_time_distribution()
    
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
        # Variables used by template
        'tasks': today_tasks,  # Alias for template iteration
        'task_count': today_tasks.count(),
        'completed_count': today_tasks.filter(status='DONE').count(),
        'pending_count': today_tasks.exclude(status__in=['DONE', 'SKIPPED', 'MISSED', 'BLOCKED']).count(),
        'skipped_count': today_tasks.filter(status__in=['SKIPPED', 'MISSED', 'BLOCKED']).count(),
        'progress': int((today_tasks.filter(status='DONE').count() / today_tasks.count() * 100)) if today_tasks.count() > 0 else 0,
        'has_more_tasks': page_obj.has_next() if hasattr(page_obj, 'has_next') else False,
        'next_page': page_obj.next_page_number() if hasattr(page_obj, 'has_next') and page_obj.has_next() else None,
    }
    
    return render(request, 'panels/tracker_detail.html', context)


@login_required
@login_required
@handle_view_errors
def panel_week(request):
    """Week view for habits"""
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # 1. Fetch Active Trackers (Service)
    tracker_svc = TrackerService()
    trackers = tracker_svc.get_active_trackers(request.user)
    
    # 2. Fetch Tasks (Service, optimized batch)
    task_svc = TaskService()
    all_tasks = task_svc.get_all_tasks_for_user_range(request.user, start_of_week, end_of_week)
    
    # Organize tasks by (tracker_id, date) for O(1) lookup
    tasks_map = {}
    for t in all_tasks:
        t_date = t.tracker_instance.period_start
        if isinstance(t_date, str):
            from datetime import date as dt
            t_date = dt.fromisoformat(t_date)
            if hasattr(t_date, 'date'):
                 t_date = t_date.date()
        elif hasattr(t_date, 'date'):
             # If datetime, get date
             t_date = t_date.date()
             
        tasks_map[(t.tracker_instance.tracker.tracker_id, t_date)] = t
    
    dates = [start_of_week + timedelta(days=i) for i in range(7)]
    
    tracker_data = []
    
    for tracker in trackers:
        week_data = []
        for d in dates:
            # Use map lookup
            instance = tasks_map.get((tracker.tracker_id, d))
            
            week_data.append({
                'date': d,
                'task': instance,
                'status': instance.status if instance else 'PENDING',
                'is_today': d == today
            })
            
        tracker_data.append({
            'tracker': tracker,
            'week_data': week_data
        })
        
    context = {
        'dates': dates,
        'tracker_data': tracker_data,
        'today': today,
        'start_of_week': start_of_week,
        'end_of_week': end_of_week,
    }
    
    if request.headers.get('X-Skeleton-Request'):
         return render(request, 'panels/week_content.html', context)
         
    return render(request, 'panels/week.html', context)


@login_required
@supports_skeleton(default_item_count=30)
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
    
    # Use TrackerService
    tracker_svc = TrackerService()
    user_trackers = tracker_svc.get_active_trackers(request.user)
    
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
            instance = services.ensure_tracker_instance(tracker.tracker_id, day, request.user)
            if instance:
                instance_id = instance.instance_id if hasattr(instance, 'instance_id') else instance.get('instance_id')
                tasks = services.get_tasks_for_instance(instance_id)
                for task in tasks:
                    day_total += 1
                    tracker_monthly[tracker.tracker_id]['total'] += 1
                    if task.status == 'DONE':
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
@supports_skeleton(default_item_count=4)
@handle_view_errors
def panel_analytics(request):
    """Analytics panel with comprehensive behavioral analytics"""
    from core.services.analytics_service import AnalyticsService
    from core.behavioral import get_insights
    
    # Use TrackerService
    tracker_svc = TrackerService()
    user_trackers = tracker_svc.get_active_trackers(request.user)
    
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
    # Weekly comparison (this week vs last week)
    today = date.today()
    task_svc = TaskService()
    
    this_week = task_svc.get_all_tasks_for_user_range(
        request.user, 
        today - timedelta(days=7), 
        today
    )
    
    last_week = task_svc.get_all_tasks_for_user_range(
        request.user, 
        today - timedelta(days=14), 
        today - timedelta(days=7) # Exclusive roughly
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
@supports_skeleton(default_item_count=5)
def panel_goals(request):
    """Goals panel with Goal model integration"""
    # Use GoalProgressService
    goal_svc = GoalProgressService(request.user)
    all_goals = goal_svc.get_all_goals_progress()
    
    active_goals = []
    completed_goals = []
    
    for goal in all_goals:
        # Map to template expectations
        goal_display = {
            'id': goal['goal_id'],
            'name': goal['title'],
            'icon': goal['icon'],
            'tracker_name': goal['tracker_name'],
            'progress': int(goal['progress']),
            'target': goal['target_value'] or 100,
            'current': goal['current_value'],
            'unit': goal['unit'],
            'completed_at': goal['completed_at'],
            'days_left': goal['days_left'],
            'on_track': goal['on_track'],
            'behind_by': goal['behind_by']
        }
        
        if goal['status'] == 'achieved':
            completed_goals.append(goal_display)
        elif goal['status'] == 'active':
            active_goals.append(goal_display)
    
    context = {
        'active_goals': active_goals,
        'completed_goals': completed_goals,
    }
    return render(request, 'panels/goals.html', context)


@login_required
@supports_skeleton(default_item_count=8)
def panel_insights(request):
    """Insights panel with comprehensive behavioral analytics"""
    from core.behavioral import get_insights
    from core.services.analytics_service import AnalyticsService
    
    # Use TrackerService
    tracker_svc = TrackerService()
    user_trackers = tracker_svc.get_active_trackers(request.user)
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
    # Week comparison using TaskService
    task_svc = TaskService()
    
    this_week = task_svc.get_all_tasks_for_user_range(
        request.user,
        today - timedelta(days=7),
        today
    )
    last_week = task_svc.get_all_tasks_for_user_range(
        request.user,
        today - timedelta(days=14),
        today - timedelta(days=7)
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
@handle_view_errors
def panel_settings(request, section='general'):
    """Settings panels"""
    from .models import UserPreferences
    
    template_map = {
        'general': 'settings/general.html',
        'preferences': 'settings/preferences.html',
        'keyboard': 'settings/keyboard.html',
        'data': 'settings/data.html',
        'about': 'settings/about.html',
    }
    
    template = template_map.get(section, 'settings/general.html')
    
    # Get or create user preferences
    prefs, created = UserPreferences.objects.get_or_create(user=request.user)
    
    # Define available themes
    themes = [
        {'id': 'working-hard', 'name': 'Working Hard', 'color': '#0277bd', 'bg': '#0c1929'},
        {'id': 'forest-focus', 'name': 'Forest Focus', 'color': '#2e7d32', 'bg': '#0a1f0c'},
        {'id': 'sunset-glow', 'name': 'Sunset Glow', 'color': '#e65100', 'bg': '#1f0c0a'},
        {'id': 'ocean-calm', 'name': 'Ocean Calm', 'color': '#00838f', 'bg': '#0a1a1f'},
        {'id': 'purple-haze', 'name': 'Purple Haze', 'color': '#6a1b9a', 'bg': '#150a1f'},
        {'id': 'midnight-dark', 'name': 'Midnight Dark', 'color': '#424242', 'bg': '#121212'},
        {'id': 'light-mode', 'name': 'Light Mode', 'color': '#1976d2', 'bg': '#ffffff'},
    ]
    
    context = {
        'user': request.user,
        'active': section,
        'preferences': prefs,
        'themes': themes,
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
@handle_view_errors
def load_modal_content(request, modal_name):
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
    tracker_svc = TrackerService()
    
    if modal_name == 'add_task':
        # Get user's trackers for the dropdown
        context['trackers'] = tracker_svc.get_active_trackers(request.user)
    
    elif modal_name == 'edit_task':
        task_id = request.GET.get('task_id')
        if task_id:
            try:
                task_svc = TaskService()
                task = task_svc.get_task_by_id(task_id, request.user)
                if task:
                    context['task'] = task
                    context['trackers'] = tracker_svc.get_active_trackers(request.user)
            except Exception:
                pass
    
    elif modal_name == 'edit_tracker':
        tracker_id = request.GET.get('tracker_id')
        if tracker_id:
            try:
                tracker = tracker_svc.get_tracker_by_id(tracker_id, request.user)
                if tracker:
                    context['tracker'] = tracker
            except Exception:
                pass
        
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
