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

from core.models import TrackerDefinition, TrackerInstance
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
    today = date.today()
    user_trackers = TrackerDefinition.objects.filter(user=request.user)
    
    # Ensure instances exist
    for tracker in user_trackers:
        services.ensure_tracker_instance(tracker.tracker_id, today)
    
    # Compute stats
    tracker_stats = []
    total_done = 0
    total_pending = 0
    
    for tracker in user_trackers:
        try:
            stats = analytics.compute_tracker_stats(tracker.tracker_id)
            tracker_stats.append({
                'tracker': tracker,
                'stats': stats
            })
            total_done += stats.get('done_count', 0)
            total_pending += stats.get('pending_count', 0)
        except:
            tracker_stats.append({'tracker': tracker, 'stats': {}})
    
    # Get current streak
    streak = analytics.compute_user_streak(request.user) if hasattr(analytics, 'compute_user_streak') else 7
    
    context = {
        'trackers': tracker_stats,
        'today': today,
        'total_done': total_done,
        'total_pending': total_pending,
        'streak': streak,
        'completion_rate': int(total_done / (total_done + total_pending) * 100) if (total_done + total_pending) > 0 else 0
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
    """Trackers list panel"""
    user_trackers = TrackerDefinition.objects.filter(user=request.user).order_by('name')
    
    tracker_data = []
    for tracker in user_trackers:
        stats = analytics.compute_tracker_stats(tracker.tracker_id)
        tracker_data.append({
            'tracker': tracker,
            'stats': stats
        })
    
    context = {
        'trackers': tracker_data
    }
    
    return render(request, 'panels/trackers_list.html', context)


@login_required
def panel_tracker_detail(request, tracker_id):
    """Single tracker detail panel"""
    tracker = get_object_or_404(TrackerDefinition, tracker_id=tracker_id, user=request.user)
    
    today = date.today()
    instance = services.ensure_tracker_instance(tracker_id, today)
    tasks = crud.get_instance_tasks(instance.instance_id) if instance else []
    stats = analytics.compute_tracker_stats(tracker_id)
    
    context = {
        'tracker': tracker,
        'tasks': tasks,
        'stats': stats,
        'today': today,
    }
    
    return render(request, 'panels/tracker_detail.html', context)


@login_required
def panel_week(request):
    """Week view panel"""
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    
    week_data = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_tasks = []
        
        user_trackers = TrackerDefinition.objects.filter(user=request.user)
        for tracker in user_trackers:
            instance = TrackerInstance.objects.filter(
                tracker__tracker_id=tracker.tracker_id,
                date=day
            ).first()
            if instance:
                tasks = crud.get_instance_tasks(instance.instance_id)
                day_tasks.extend(tasks)
        
        done = sum(1 for t in day_tasks if t.get('status') == 'DONE')
        total = len(day_tasks)
        
        week_data.append({
            'date': day,
            'day_name': day.strftime('%A'),
            'is_today': day == today,
            'tasks': day_tasks,
            'done': done,
            'total': total,
            'percent': int(done/total*100) if total else 0
        })
    
    context = {
        'week': week_data,
        'start_of_week': start_of_week,
    }
    
    return render(request, 'panels/week.html', context)


@login_required
def panel_month(request):
    """Month view panel"""
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    from calendar import monthrange
    first_day = date(year, month, 1)
    days_in_month = monthrange(year, month)[1]
    
    month_data = []
    for day_num in range(1, days_in_month + 1):
        day = date(year, month, day_num)
        # Get completion data for this day
        completion = 0  # Placeholder
        month_data.append({
            'date': day,
            'day': day_num,
            'completion': completion
        })
    
    context = {
        'month_data': month_data,
        'month_name': first_day.strftime('%B %Y'),
        'year': year,
        'month': month,
    }
    
    return render(request, 'panels/month.html', context)


@login_required
def panel_analytics(request):
    """Analytics panel"""
    user_trackers = TrackerDefinition.objects.filter(user=request.user)
    
    # Aggregate stats
    total_completed = 0
    total_tasks = 0
    
    for tracker in user_trackers:
        stats = analytics.compute_tracker_stats(tracker.tracker_id)
        total_completed += stats.get('done_count', 0)
        total_tasks += stats.get('total_count', 0)
    
    context = {
        'trackers': user_trackers,
        'total_completed': total_completed,
        'total_tasks': total_tasks,
        'completion_rate': int(total_completed/total_tasks*100) if total_tasks else 0,
    }
    
    return render(request, 'panels/analytics.html', context)


@login_required
def panel_goals(request):
    """Goals panel"""
    context = {
        'goals': [],  # Populate from goals model when created
    }
    return render(request, 'panels/goals.html', context)


@login_required
def panel_insights(request):
    """Insights panel"""
    context = {
        'insights': [],
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
