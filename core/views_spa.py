"""
SPA Views - Single Page Application endpoints
All views render through base_spa.html with AJAX panel loading

Enhanced with skeleton support following OpusSuggestion.md
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from datetime import date, timedelta
import json
from functools import wraps

from core.models import TrackerDefinition, TrackerInstance, TaskInstance, Goal
from core.repositories import base_repository as crud
from core.services import instance_service as services
from core import analytics
from core.utils.skeleton_helpers import generate_panel_skeleton, estimate_load_time
from core.utils.constants import SWIPE_ACTION_COLORS, TOUCH_TARGETS, MODAL_DETENTS, MODAL_PRESENTATIONS
from core.utils.skeleton_helpers import generate_panel_skeleton, estimate_load_time
from core.utils.constants import SWIPE_ACTION_COLORS, TOUCH_TARGETS, MODAL_DETENTS, MODAL_PRESENTATIONS


# ============================================================================
# DECORATORS
# ============================================================================

def supports_skeleton(default_count=5):
    """
    Decorator to add skeleton loading support to panel views.
    
    Following OpusSuggestion.md Part 1.2: Enhanced Caching Strategy and Loading States
    
    When ?skeleton=true is in the query params, returns skeleton structure
    instead of full panel, enabling instant perceived loading.
    
    Args:
        default_count: Default number of skeleton items to generate
    
    Usage:
        @supports_skeleton(default_count=8)
        def panel_dashboard(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.GET.get('skeleton') == 'true':
                # Extract panel type from view function name
                panel_type = view_func.__name__.replace('panel_', '')
                item_count = int(request.GET.get('count', default_count))
                
                skeleton = generate_panel_skeleton(panel_type, item_count)
                estimated_time = estimate_load_time(item_count, has_complex_data=False)
               
                return JsonResponse({
                    'skeleton': True,
                    'structure': skeleton,
                    'estimated_load_time': estimated_time,
                    'panel_type': panel_type
                })
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# MAIN SPA SHELL
# ============================================================================

@login_required
def spa_shell(request, **kwargs):
    """
    Main SPA entry point. Renders the shell with sidebar.
    All content is loaded via AJAX into the main area.
    Accepts **kwargs to handle legacy routes that pass tracker_id, etc.
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
@supports_skeleton(default_count=8)
def panel_dashboard(request):
    """
    Dashboard panel with quick stats and filtering.
    
    Enhanced with:
    - Skeleton support for instant loading
    - Filter state metadata for SPA state management
    """
    from datetime import datetime
    import calendar
    
    today = date.today()
    now = datetime.now()
    user_trackers = TrackerDefinition.objects.filter(user=request.user, status='active')
    
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
            services.ensure_tracker_instance(tracker.tracker_id, today)
    
    # Get tasks across all trackers for the period
    dashboard_tasks = []
    completed_count = 0
    pending_count = 0
    
    for tracker in user_trackers:
        try:
            # Get instances overlapping the period
            instances = TrackerInstance.objects.filter(
                tracker=tracker,
                period_start__lte=end_date,
                period_end__gte=start_date
            )
            
            for instance in instances:
                tasks = TaskInstance.objects.filter(tracker_instance=instance).select_related('template')
                
                # Filter tasks if needed (e.g. for weekly view, check they fall in the week)
                # But simplified: if tracker instance overlaps, include its tasks
                
                for task in tasks:
                    # Deduplicate if necessary or just list all
                    dashboard_tasks.append({
                        'id': task.task_instance_id,
                        'status': task.status,
                        'description': task.template.description,
                        'category': task.template.category,
                        'tracker_name': tracker.name,
                        'tracker_id': tracker.tracker_id,
                        'weight': task.template.weight,
                        'created_at': task.created_at,
                        # iOS UX enhancements (sonnetSuggestion.md Phase 3)
                        'ios_context_menu': [
                            {'title': 'Edit', 'icon': 'pencil', 'action': 'edit'},
                            {'title': 'Complete', 'icon': 'checkmark.circle', 'action': 'complete'} if task.status != 'DONE' else {'title': 'Reopen', 'icon': 'arrow.uturn.backward', 'action': 'reopen'},
                            {'title': 'Skip', 'icon': 'forward.fill', 'action': 'skip'},
                            {'title': 'Add Note', 'icon': 'note.text', 'action': 'note'},
                            {'title': 'Delete', 'icon': 'trash', 'destructive': True, 'action': 'delete'}
                        ]
                    })
                    
                    if task.status == 'DONE':
                        completed_count += 1
                    elif task.status in ['TODO', 'IN_PROGRESS']:
                        pending_count += 1
        except Exception:
            pass
    
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
    
    # Active trackers - calculate stats based on current period filter
    active_trackers = []
    for tracker in user_trackers[:6]:
        # Get tracker instances for the period
        tracker_instances = TrackerInstance.objects.filter(
            tracker=tracker,
            period_start__lte=end_date,
            period_end__gte=start_date
        )
        
        # Calculate period-specific stats
        period_tasks = TaskInstance.objects.filter(
            tracker_instance__in=tracker_instances
        )
        period_total = period_tasks.count()
        period_completed = period_tasks.filter(status='DONE').count()
        period_progress = int(period_completed / period_total * 100) if period_total > 0 else 0
        
        active_trackers.append({
            'id': tracker.tracker_id,
            'name': tracker.name,
            'time_period': tracker.time_period,
            'progress': period_progress,
            'completed_count': period_completed,
            'task_count': period_total,
        })
    
    # Add filter state for SPA state management (OpusSuggestion.md Part 1.1)
    filter_state = {
        'current_period': period,
        'available_periods': ['daily', 'weekly', 'monthly', 'all'],
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
    
    # Add quick stats badges for display
    quick_stats = {
        'tasks_today': pending_count + completed_count,
        'completed_today': completed_count,
        'streak_days': streak,
        'completion_pct': completion_rate
    }
    
    # Integrate behavioral insights (OpusSuggestion.md - Smart Suggestions)
    smart_suggestions = []
    try:
        from core.behavioral.insights_engine import generate_smart_suggestions
        suggestions_data = generate_smart_suggestions(request.user)
        smart_suggestions = suggestions_data.get('suggestions', [])[:3]  # Top 3 suggestions
    except Exception:
        pass  # Gracefully handle if insights engine unavailable
    
    # Add insights widget metadata
    insights_widget = {
        'enabled': len(smart_suggestions) > 0,
        'suggestions': smart_suggestions,
        'cta_text': 'View All Insights',
        'cta_link': '/analytics/'
    }
    
    context = {
        'time_of_day': time_of_day,
        'today': today,
        'stats': stats,
        'today_tasks': dashboard_tasks[:50], # Limit to avoid overload
        'active_trackers': active_trackers,
        'current_period': period,
        'period_title': period_title,
        # New UX enhancements
        'filter_state': filter_state,
        'quick_stats': quick_stats,
        # Behavioral insights integration (OpusSuggestion.md Part 3.3)
        'smart_suggestions': smart_suggestions,
        'insights_widget': insights_widget,
    }
    
    return render(request, 'panels/dashboard.html', context)


@login_required
@supports_skeleton(default_count=6)
def panel_today(request):
    """Today's tasks panel"""
    today = date.today()
    date_str = request.GET.get('date')
    if date_str:
        try:
            today = date.fromisoformat(date_str)
        except:
            pass
    
    user_trackers = TrackerDefinition.objects.filter(user=request.user).exclude(status='archived')
    
    task_groups = []
    total_count = 0
    completed_count = 0
    pending_count = 0
    missed_count = 0
    
    for tracker in user_trackers:
        instance = services.ensure_tracker_instance(tracker.tracker_id, today)
        tasks = []
        if instance:
            instance_id = instance.get('instance_id') if isinstance(instance, dict) else instance.instance_id
            if instance_id:
                # get_instance_tasks usually returns a list of dictionaries or model instances
                # We need to standardize on what the template expects
                raw_tasks = crud.get_instance_tasks(instance_id)
                # Convert to list if queryset
                if hasattr(raw_tasks, 'all'):
                    raw_tasks = list(raw_tasks)
                
                # Filter/process tasks
                for task in raw_tasks:
                    # Handle both object and dict access
                    status = getattr(task, 'status', None) or task.get('status') if isinstance(task, dict) else None
                    if not status: continue
                    
                    # Get task data for enhanced structure (FinalRefactoringGuide.md lines 196-254)
                    task_id = task.task_instance_id if hasattr(task, 'task_instance_id') else task.get('task_instance_id')
                    description = task.template.description if hasattr(task, 'template') else task.get('description', '')
                    category = task.template.category if hasattr(task, 'template') else task.get('category', '')
                    time_of_day = task.template.time_of_day if hasattr(task, 'template') else task.get('time_of_day', 'anytime')
                    weight = task.template.weight if hasattr(task, 'template') else task.get('weight', 1)
                    
                    # Convert to enhanced dict with iOS UX metadata
                    task_data = {
                        'task_instance_id': task_id,
                        'status': status,
                        'description': description,
                        'category': category,
                        'time_of_day': time_of_day,
                        'weight': weight,
                        
                        # iOS swipe actions (44pt minimum per Apple HIG) - FinalRefactoringGuide.md
                        'ios_swipe_actions': {
                            'leading': [{
                                'id': 'complete',
                                'title': '✓',
                                'style': 'normal',
                                'backgroundColor': '#22c55e',  # Green
                                'endpoint': f'/api/task/{task_id}/toggle/',
                                'haptic': 'success',
                                'minWidth': 44
                            }] if status != 'DONE' else [{
                                'id': 'undo',
                                'title': '↶',
                                'style': 'normal',
                                'backgroundColor': '#64748b',  # Gray
                                'endpoint': f'/api/task/{task_id}/toggle/',
                                'haptic': 'light',
                                'minWidth': 44
                            }],
                            
                            'trailing': [
                                {
                                    'id': 'skip',
                                    'title': 'Skip',
                                    'style': 'normal',
                                    'backgroundColor': '#f59e0b',  # Amber
                                    'endpoint': f'/api/task/{task_id}/status/',
                                    'payload': {'status': 'SKIPPED'},
                                    'haptic': 'warning',
                                    'minWidth': 60
                                },
                                {
                                    'id': 'delete',
                                    'title': 'Delete',
                                    'style': 'destructive',
                                    'backgroundColor': '#ef4444',  # Red
                                    'confirmRequired': True,
                                    'endpoint': f'/api/task/{task_id}/delete/',
                                    'haptic': 'error',
                                    'minWidth': 70
                                }
                            ]
                        },
                        
                        # Long-press context menu - FinalRefactoringGuide.md
                        'ios_context_menu': [
                            {'title': 'Edit', 'icon': 'pencil', 'action': 'edit'},
                            {'title': 'Add Note', 'icon': 'note.text', 'action': 'note'},
                            {'title': 'Move to Tomorrow', 'icon': 'arrow.forward', 'action': 'reschedule'},
                            {'title': 'Delete', 'icon': 'trash', 'destructive': True, 'action': 'delete'}
                        ]
                    }
                    
                    tasks.append(task_data)
                    
                    # Update counts
                    total_count += 1
                    if status == 'DONE':
                        completed_count += 1
                    elif status in ['TODO', 'IN_PROGRESS']:
                        pending_count += 1
                    elif status in ['MISSED', 'SKIPPED', 'BLOCKED']:
                        missed_count += 1

        if tasks:
            # Sort by time of day (tasks are now dicts with time_of_day field)
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
    
    # Generate iOS swipe actions for all tasks (OpusSuggestion.md Part 2.2)
    ios_swipe_actions = {}
    for group in task_groups:
        for task in group['tasks']:
            task_id = getattr(task, 'task_instance_id', None) or task.get('id') if isinstance(task, dict) else None
            status = getattr(task, 'status', None) or task.get('status') if isinstance(task, dict) else None
            
            if task_id:
                # Leading swipe action (complete/uncomplete)
                leading_actions = []
                if status != 'DONE':
                    leading_actions.append({
                        'id': 'complete',
                        'title': '✓',
                        'color': SWIPE_ACTION_COLORS['complete'],
                        'endpoint': f'/api/task/{task_id}/toggle/',
                        'minWidth': TOUCH_TARGETS['minimum']
                    })
                else:
                    leading_actions.append({
                        'id': 'undo',
                        'title': '↶',
                        'color': SWIPE_ACTION_COLORS['undo'],
                        'endpoint': f'/api/task/{task_id}/toggle/',
                        'minWidth': TOUCH_TARGETS['minimum']
                    })
                
                # Trailing swipe actions (skip/delete)
                trailing_actions = [
                    {
                        'id': 'skip',
                        'title': 'Skip',
                        'color': SWIPE_ACTION_COLORS['skip'],
                        'endpoint': f'/api/task/{task_id}/status/',
                        'payload': {'status': 'SKIPPED'},
                        'minWidth': TOUCH_TARGETS['comfortable']
                    },
                    {
                        'id': 'delete',
                        'title': 'Delete',
                        'color': SWIPE_ACTION_COLORS['delete'],
                        'destructive': True,
                        'endpoint': f'/api/task/{task_id}/delete/',
                        'minWidth': TOUCH_TARGETS['comfortable']
                    }
                ]
                
                ios_swipe_actions[task_id] = {
                    'leading': leading_actions,
                    'trailing': trailing_actions
                }
    
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
        'day_note': '', # Placeholder until DayNote model is clarified or generic note is implemented
        # iOS UX enhancements (OpusSuggestion.md Part 2.2)
        'ios_swipe_actions': ios_swipe_actions,
        'touch_targets': TOUCH_TARGETS,  # For template usage
    }
    
    return render(request, 'panels/today.html', context)


@login_required
def panel_trackers_list(request):
    """Trackers list panel with pagination and complete tracker data"""
    PAGE_SIZE = 6
    
    page = int(request.GET.get('page', 1))
    offset = (page - 1) * PAGE_SIZE
    
    # Get non-archived user trackers ordered by most recent activity
    active_trackers_qs = TrackerDefinition.objects.filter(
        user=request.user
    ).exclude(status='archived').order_by('-updated_at', 'name')
    
    # Get archived trackers separately
    archived_trackers_qs = TrackerDefinition.objects.filter(
        user=request.user, status='archived'
    ).order_by('-updated_at')
    
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
    
    # Get today's tasks - order by template weight (higher weight = more important)
    today_tasks = TaskInstance.objects.filter(
        tracker_instance__tracker=tracker,
        tracker_instance__period_start__lte=today,
        tracker_instance__period_end__gte=today
    ).select_related('template').order_by('-template__weight', 'template__time_of_day', 'created_at')
    
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
    
    # Enhanced week stats with time-of-day insights
    week_stats = {
        'completed': total_completed,
        'total': total_tasks,
        'completion_rate': completion_rate,
        'best_day': best_day,
        'best_day_rate': int(best_day_rate),
        'streak': streak,
        # Time distribution across whole week
        'morning_completion': sum(d['morning_completed'] for d in days),
        'afternoon_completion': sum(d['afternoon_completed'] for d in days),
        'evening_completion': sum(d['evening_completed'] for d in days),
        'morning_total': sum(d['morning_total'] for d in days),
        'afternoon_total': sum(d['afternoon_total'] for d in days),
        'evening_total': sum(d['evening_total'] for d in days),
    }
    
    # Calculate best time of day
    time_rates = {}
    if week_stats['morning_total'] > 0:
        time_rates['morning'] = week_stats['morning_completion'] / week_stats['morning_total']
    if week_stats['afternoon_total'] > 0:
        time_rates['afternoon'] = week_stats['afternoon_completion'] / week_stats['afternoon_total']
    if week_stats['evening_total'] > 0:
        time_rates['evening'] = week_stats['evening_completion'] / week_stats['evening_total']
    
    best_time = max(time_rates, key=time_rates.get) if time_rates else None
    week_stats['best_time'] = best_time
    week_stats['best_time_rate'] = int(time_rates.get(best_time, 0) * 100) if best_time else 0
    
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
    
    # Integrate comprehensive behavioral insights (OpusSuggestion.md Part 3.3)
    smart_suggestions = []
    insights_summary = {}
    try:
        from core.behavioral.insights_engine import generate_smart_suggestions
        insights_data = generate_smart_suggestions(request.user)
        smart_suggestions = insights_data.get('suggestions', [])
        insights_summary = insights_data.get('summary', {})
    except Exception:
        pass
    
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
        # Behavioral insights integration (OpusSuggestion.md Part 3.3)
        'smart_suggestions': smart_suggestions,
        'insights_summary': insights_summary,
        'show_insights': len(smart_suggestions) > 0,
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
def modal_view(request, modal_name):
    """
    Generic view to serve modal content.
    Loads templates from core/templates/modals/{modal_name}.html
    
    Enhanced with iOS bottom sheet configuration (OpusSuggestion.md Part 2.2)
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
    
    elif modal_name == 'edit_task':
        task_id = request.GET.get('task_id')
        if task_id:
            task = TaskInstance.objects.filter(
                task_instance_id=task_id,
                tracker_instance__tracker__user=request.user
            ).select_related('template', 'tracker_instance__tracker').first()
            if task:
                context['task'] = task
                context['trackers'] = TrackerDefinition.objects.filter(user=request.user)
    
    elif modal_name == 'edit_tracker':
        tracker_id = request.GET.get('tracker_id')
        if tracker_id:
            tracker = TrackerDefinition.objects.filter(
                tracker_id=tracker_id,
                user=request.user
            ).first()
            if tracker:
                context['tracker'] = tracker
    
    # iOS modal presentation configuration (OpusSuggestion.md Part 2.2)
    # Define detents (size options) for each modal type
    modal_detents = {
        'add_task': MODAL_DETENTS['large'],
        'edit_task': MODAL_DETENTS['large'],
        'add_tracker': MODAL_DETENTS['large'],
        'edit_tracker': MODAL_DETENTS['large'],
        'add_goal': MODAL_DETENTS['medium'],
        'task_detail': MODAL_DETENTS['medium'],
        'confirm_delete': MODAL_DETENTS['small'],
        'share': MODAL_DETENTS['medium'],
        'theme_gallery': MODAL_DETENTS['large'],
    }
    
    # Add iOS configuration to context
    context['ios_modal_config'] = {
        'presentation': MODAL_PRESENTATIONS['bottom_sheet'],
        'detents': modal_detents.get(modal_name, MODAL_DETENTS['medium']),
        'dismissible': True,
        'show_grabber': True,  # iOS drag handle
        'corner_radius': 20,
    }
        
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
