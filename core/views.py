from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from datetime import date, timedelta, datetime
import json

from core.repositories import base_repository as crud
from core.services import instance_service as services
from core import templates, analytics
from core.exports import exporter as exports
from core.models import TrackerDefinition
import uuid
from core.utils.constants import STATUS_INFO

# ============================================================================
# DASHBOARD & HOME
# ============================================================================

@login_required # Added decorator
def dashboard(request):
    """
    Main dashboard showing all trackers and their quick stats.
    Optimized with caching (analytics decorated with @cache_result).
    MULTI-USER: Filters trackers by logged-in user.
    """
    from core.models import TrackerDefinition # Added import inside function
    
    today = date.today()
    
    # Ensure instances exist for all active trackers (user's trackers only)
    user_trackers = TrackerDefinition.objects.filter(user=request.user) # Filter by user
    for tracker in user_trackers:
        services.ensure_tracker_instance(tracker.tracker_id, today) # Fixed function call
    
    # Get all trackers with their stats (filtered by user)
    tracker_stats = []
    for tracker in user_trackers: # Iterate over user's trackers
        try:
            # compute_tracker_stats is now cached (5 min timeout)
            stats = analytics.compute_tracker_stats(tracker.tracker_id)
            tracker_stats.append({
                'tracker': crud.model_to_dict(tracker), # Convert model to dict
                'stats': stats
            })
        except Exception as e:
            # Log error but continue with other trackers
            tracker_stats.append({
                'tracker': crud.model_to_dict(tracker), # Convert model to dict
                'stats': {}
            })
    
    context = {
        'trackers': tracker_stats,
        'today': today,
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def tracker_list(request):
    """List and manage trackers (user's trackers only)."""
    from core.helpers.auth_helpers import get_user_trackers
    trackers = [crud.model_to_dict(t) for t in get_user_trackers(request.user)]
    return render(request, 'core/tracker_list.html', {'trackers': trackers})

@login_required
def create_tracker(request):
    """Create a new tracker (assigns to logged-in user)."""
    if request.method == 'POST':
        name = request.POST.get('name')
        time_mode = request.POST.get('time_mode')
        description = request.POST.get('description', '')
        category = request.POST.get('category')
        
        tracker_id = str(uuid.uuid4())
        # Create using ORM to handle user field
        tracker = TrackerDefinition.objects.create(
            tracker_id=tracker_id,
            user=request.user,  # Assign to logged-in user
            name=name,
            time_mode=time_mode,
            description=description
        )
        
        if category:
            templates.initialize_templates(tracker_id, category)
            
        return redirect('tracker_detail', tracker_id=tracker_id)
        
    return render(request, 'core/create_tracker.html')

@login_required
def tracker_detail(request, tracker_id):
    """Detailed tracker view with inline analytics (user must own tracker)."""
    from core.helpers.auth_helpers import get_user_tracker_or_404
    
    # Permission check: user must own this tracker
    tracker_obj = get_user_tracker_or_404(tracker_id, request.user)
    tracker = crud.model_to_dict(tracker_obj)
    
    # Get comprehensive stats
    completion = analytics.compute_completion_rate(tracker_id)
    streaks = analytics.detect_streaks(tracker_id)
    consistency = analytics.compute_consistency_score(tracker_id)
    balance = analytics.compute_balance_score(tracker_id)
    
    context = {
        'tracker': tracker,
        'completion': completion,
        'streaks': streaks,
        'consistency': consistency,
        'balance': balance,
    }
    return render(request, 'core/tracker_detail.html', context)

@login_required
def analytics_dashboard(request, tracker_id):
    """Full analytics dashboard with all metrics."""
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Core metrics
    completion = analytics.compute_completion_rate(tracker_id)
    streaks = analytics.detect_streaks(tracker_id)
    consistency = analytics.compute_consistency_score(tracker_id)
    balance = analytics.compute_balance_score(tracker_id)
    effort = analytics.compute_effort_index(tracker_id)
    
    # Charts
    completion_chart = analytics.generate_completion_chart(tracker_id)
    heatmap = analytics.generate_completion_heatmap(tracker_id, days=30)
    streak_timeline = analytics.generate_streak_timeline(tracker_id)
    progress_trend = analytics.generate_progress_chart_with_trend(tracker_id)
    
    context = {
        'tracker': tracker,
        'completion': completion,
        'streaks': streaks,
        'consistency': consistency,
        'balance': balance,
        'effort': effort,
        'completion_chart': completion_chart,
        'heatmap': heatmap,
        'streak_timeline': streak_timeline,
        'progress_trend': progress_trend,
    }
    return render(request, 'core/analytics_dashboard.html', context)


@login_required
def delete_tracker(request, tracker_id):
    """
    Delete a tracker and all associated data.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
    
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return JsonResponse({'status': 'error', 'message': 'Tracker not found'}, status=404)
    
    try:
        # Delete all task instances for this tracker
        instances = crud.get_tracker_instances(tracker_id)
        for instance in instances:
            tasks = crud.get_task_instances_for_tracker_instance(instance['instance_id'])
            for task in tasks:
                crud.db.delete('TaskInstances', 'task_instance_id', task['task_instance_id'])
            crud.db.delete('TrackerInstances', 'instance_id', instance['instance_id'])
        
        # Delete all task templates
        templates = crud.get_task_templates_for_tracker(tracker_id)
        for template in templates:
            crud.db.delete('TaskTemplates', 'template_id', template['template_id'])
        
        # Delete the tracker itself
        crud.db.delete('TrackerDefinitions', 'tracker_id', tracker_id)
        
        return JsonResponse({'status': 'success', 'message': 'Tracker deleted successfully'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def behavior_analysis(request, tracker_id):
    """Behavior insights with NLP analysis."""
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # NLP metrics
    sentiment = analytics.analyze_notes_sentiment(tracker_id)
    keywords = analytics.extract_keywords_from_notes(tracker_id, top_n=10)
    mood_trends = analytics.compute_mood_trends(tracker_id, window_days=7)
    
    context = {
        'tracker': tracker,
        'sentiment': sentiment,
        'keywords': keywords,
        'mood_trends': mood_trends,
    }
    return render(request, 'core/behavior_analysis.html', context)

@login_required
def correlations(request, tracker_id):
    """Correlation matrix and insights."""
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Compute correlations
    corr_data = analytics.compute_correlations(tracker_id)
    
    # Generate heatmap
    heatmap = analytics.generate_correlation_heatmap(tracker_id)
    
    context = {
        'tracker': tracker,
        'correlations': corr_data,
        'heatmap': heatmap,
    }
    return render(request, 'core/correlations.html', context)

@login_required
def forecast_view(request, tracker_id):
    """Time-series forecasts."""
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Time-series analysis
    ts_data = analytics.analyze_time_series(tracker_id, metric='completion_rate', forecast_days=7)
    
    # Trend analysis
    trends = analytics.analyze_trends(tracker_id, window=14)
    
    # Generate forecast chart
    forecast_chart = analytics.generate_forecast_chart(tracker_id, metric='completion_rate', days=7)
    
    context = {
        'tracker': tracker,
        'ts_data': ts_data,
        'trends': trends,
        'forecast_chart': forecast_chart,
    }
    return render(request, 'core/forecast.html', context)

@login_required
def export_center(request, tracker_id):
    """Export hub for all formats."""
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    if request.method == 'POST':
        export_type = request.POST.get('export_type')
        
        if export_type == 'excel_summary':
            # Generate Excel summary
            import tempfile
            import os
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            temp_file.close()
            
            exports.generate_behavior_summary(tracker_id, temp_file.name)
            
            with open(temp_file.name, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="tracker_{tracker["name"]}_summary.xlsx"'
            
            os.unlink(temp_file.name)
            return response
        
        elif export_type in ['csv', 'json', 'yaml']:
            # Generate data export
            data = exports.export_data(tracker_id, format=export_type)
            
            content_types = {
                'csv': 'text/csv',
                'json': 'application/json',
                'yaml': 'text/yaml'
            }
            
            response = HttpResponse(data, content_type=content_types[export_type])
            response['Content-Disposition'] = f'attachment; filename="tracker_{tracker["name"]}_data.{export_type}"'
            return response
        
        elif export_type == 'journey':
            # Generate journey report
            import tempfile
            import os
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            temp_file.close()
            
            exports.generate_journey_report(tracker_id, output_path=temp_file.name)
            
            with open(temp_file.name, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="my_journey_{tracker["name"]}.xlsx"'
            
            os.unlink(temp_file.name)
            return response
    
    context = {
        'tracker': tracker,
    }
    return render(request, 'core/export_center.html', context)

@login_required
def my_journey(request, tracker_id):
    """Audit log timeline."""
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Generate journey data
    journey_data = exports.generate_journey_report(tracker_id)
    
    context = {
        'tracker': tracker,
        'journey': journey_data,
    }
    return render(request, 'core/my_journey.html', context)

@login_required
def monthly_tracker(request, tracker_id):
    """
    Interactive monthly habit tracker view.
    Shows a grid with tasks/activities as rows and days of month as columns.
    
    REFACTORED: Uses GridBuilderService to eliminate code duplication
    """
    from core.services.grid_builder_service import GridBuilderService
    
    # Get current month or from query params
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Ensure instances exist for the month
    from calendar import monthrange
    _, num_days = monthrange(year, month)
    for day in range(1, num_days + 1):
        services.ensure_tracker_instance(tracker_id, date(year, month, day))
    
    # Build grid using service
    builder = GridBuilderService(tracker_id)
    result = builder.build_monthly_grid(year, month)
    
    if not result['tracker']:
        return redirect('tracker_list')
    
    # Prepare context
    context = {
        'tracker': result['tracker'],
        'calendar_data': result['grid'],
        'year': result['year'],
        'month': result['month'],
        'month_name': result['month_name'],
        'prev_year': result['prev_year'],
        'prev_month': result['prev_month'],
        'next_year': result['next_year'],
        'next_month': result['next_month'],
        'num_days': result['num_days'],
    }
    return render(request, 'core/monthly_tracker.html', context)



@login_required
def today_view(request, tracker_id):
    """
    Today-focused view: Simple grid of tasks with status toggles.
    Focus on "What do I need to do TODAY?"
    
    OPTIMIZED: Uses get_day_grid_data to fetch all data in ~3 queries
    """
    from core.utils.constants import STATUS_INFO
    
    today = date.today()
    
    # Ensure instances exist for today
    services.ensure_tracker_instance(tracker_id, today)
    
    # OPTIMIZED: Fetch all data in minimal queries
    grid_data = crud.get_day_grid_data(tracker_id, [today])
    
    tracker = grid_data['tracker']
    if not tracker:
        return redirect('tracker_list')
    
    templates = grid_data['templates']
    instances_map = grid_data['instances_map']
    
    # Get today's instance from map
    today_instance = instances_map.get(today.isoformat())
    
    # Build task list with status
    tasks_data = []
    for template in templates:
        task = None
        if today_instance and 'tasks' in today_instance:
            task = next(
                (t for t in today_instance['tasks'] if t.get('template_id') == template['template_id']),
                None
            )
        
        tasks_data.append({
            'template': template,
            'task': task,
            'status': task.get('status', 'TODO') if task else 'TODO',
            'notes': task.get('notes', '') if task else '',
        })
    
    # Calculate completion stats
    total_tasks = len(tasks_data)
    done_tasks = sum(1 for t in tasks_data if t['status'] == 'DONE')
    in_progress_tasks = sum(1 for t in tasks_data if t['status'] == 'IN_PROGRESS')
    completion_rate = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    context = {
        'tracker': tracker,
        'tasks': tasks_data,
        'today': today,
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completion_rate': completion_rate,
        'status_info': STATUS_INFO,
    }
    return render(request, 'core/today.html', context)

@login_required
def week_view(request, tracker_id):
    """
    Week view: 7-day grid (Mon-Sun) × Tasks with status cells.
    
    REFACTORED: Uses GridBuilderService to eliminate code duplication
    """
    from core.services.grid_builder_service import GridBuilderService
    
    # Get week offset from query params (default = current week)
    week_offset = int(request.GET.get('week', 0))
    
    # Ensure instances exist for the week
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    
    for day in week_days:
        services.ensure_tracker_instance(tracker_id, day)
    
    # Build grid using service
    builder = GridBuilderService(tracker_id)
    result = builder.build_week_grid(week_offset)
    
    if not result['tracker']:
        return redirect('tracker_list')
    
    # Calculate week stats from grid
    context = {
        'tracker': result['tracker'],
        'grid_data': result['grid'],
        'week_days': result['dates'],
        'week_start': result['week_start'],
        'week_end': result['week_end'],
        'week_offset': week_offset,
        'prev_week': week_offset - 1,
        'next_week': week_offset + 1,
        'total_tasks': result['stats']['total_tasks'],
        'done_tasks': result['stats']['done_tasks'],
        'completion_rate': result['stats']['completion_rate'],
        'today': today,
    }
    return render(request, 'core/week.html', context)
    
    # Calculate week stats
    all_tasks = [day['task'] for row in grid_data for day in row['days'] if day['task']]
    total_tasks = len(all_tasks)
    done_tasks = sum(1 for t in all_tasks if t.get('status') == 'DONE')
    completion_rate = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    context = {
        'tracker': tracker,
        'grid_data': grid_data,
        'week_days': week_days,
        'week_start': week_start,
        'week_end': week_days[-1],
        'prev_week': week_offset - 1,
        'next_week': week_offset + 1,
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'completion_rate': completion_rate,
        'status_info': STATUS_INFO,
        'day_names': [day_name[d.weekday()] for d in week_days],
        'today': today,
    }
    return render(request, 'core/week.html', context)

@login_required
def custom_range_view(request, tracker_id):
    """
    Custom date range view: User selects start and end dates.
    
    REFACTORED: Uses GridBuilderService to eliminate code duplication
    """
    from core.services.grid_builder_service import GridBuilderService
    from core.utils.constants import STATUS_INFO
    
    # Get date range from query params or default to last 7 days
    today = date.today()
    start_date_str = request.GET.get('start', (today - timedelta(days=6)).isoformat())
    end_date_str = request.GET.get('end', today.isoformat())
    
    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        start_date = today - timedelta(days=6)
        end_date = today
    
    # Generate date range and ensure instances exist
    date_range = []
    current = start_date
    while current <= end_date:
        date_range.append(current)
        services.ensure_tracker_instance(tracker_id, current)
        current += timedelta(days=1)
    
    # Build grid using service
    builder = GridBuilderService(tracker_id)
    result = builder.build_custom_range_grid(start_date, end_date)
    
    if not result['tracker']:
        return redirect('tracker_list')
    
    context = {
        'tracker': result['tracker'],
        'grid_data': result['grid'],
        'start_date': start_date,
        'end_date': end_date,
        'num_days': result['num_days'],
        'total_tasks': result['stats']['total_tasks'],
        'done_tasks': result['stats']['done_tasks'],
        'completion_rate': result['stats']['completion_rate'],
        'status_info': STATUS_INFO,
        'today': today,
    }
    return render(request, 'core/custom_range.html', context)
    
    # Calculate stats
    all_tasks = [day['task'] for row in grid_data for day in row['days'] if day['task']]
    total_tasks = len(all_tasks)
    done_tasks = sum(1 for t in all_tasks if t.get('status') == 'DONE')
    completion_rate = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    context = {
        'tracker': tracker,
        'grid_data': grid_data,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'completion_rate': completion_rate,
        'status_info': STATUS_INFO,
        'today': today,
    }
    return render(request, 'core/custom_range.html', context)

@login_required
def manage_tasks(request, tracker_id):
    """
    Manage all tasks for a tracker: view, edit, delete, reorder.
    """
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    templates = crud.get_task_templates_for_tracker(tracker_id)
    
    context = {
        'tracker': tracker,
        'templates': templates,
    }
    return render(request, 'core/manage_tasks.html', context)

@login_required
def add_task(request, tracker_id):
    """
    Add a new task template to tracker.
    """
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    if request.method == 'POST':
        description = request.POST.get('description')
        category = request.POST.get('category', '')
        is_recurring = request.POST.get('is_recurring') == 'on'
        weight = int(request.POST.get('weight', 1))
        
        # Create template
        template_data = {
            'template_id': str(uuid.uuid4()),
            'tracker_id': tracker_id,
            'description': description,
            'is_recurring': is_recurring,
            'category': category,
            'weight': weight
        }
        
        crud.create_task_template(template_data)
        
        return redirect('manage_tasks', tracker_id=tracker_id)
    
    context = {
        'tracker': tracker,
    }
    return render(request, 'core/add_task.html', context)

@login_required
def edit_task(request, template_id):
    """
    Edit existing task template.
    """
    template = crud.db.fetch_by_id('TaskTemplates', 'template_id', template_id)
    if not template:
        return redirect('tracker_list')
    
    tracker_id = template['tracker_id']
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    
    if request.method == 'POST':
        updates = {
            'description': request.POST.get('description'),
            'category': request.POST.get('category', ''),
            'is_recurring': request.POST.get('is_recurring') == 'on',
            'weight': int(request.POST.get('weight', 1))
        }
        
        crud.db.update('TaskTemplates', 'template_id', template_id, updates)
        
        return redirect('manage_tasks', tracker_id=tracker_id)
    
    context = {
        'tracker': tracker,
        'template': template,
    }
    return render(request, 'core/edit_task.html', context)

@login_required
def delete_task(request, template_id):
    """
    Delete task template and optionally all instances.
    """
    if request.method != 'POST':
        return redirect('tracker_list')
    
    template = crud.db.fetch_by_id('TaskTemplates', 'template_id', template_id)
    if not template:
        return JsonResponse({'status': 'error', 'message': 'Template not found'}, status=404)
    
    tracker_id = template['tracker_id']
    delete_instances = request.POST.get('delete_instances') == 'yes'
    
    # Delete all task instances if requested
    if delete_instances:
        all_instances = crud.get_tracker_instances(tracker_id)
        for instance in all_instances:
            tasks = crud.get_task_instances_for_tracker_instance(instance['instance_id'])
            for task in tasks:
                if task['template_id'] == template_id:
                    crud.db.delete('TaskInstances', 'task_instance_id', task['task_instance_id'])
    
    # Delete template
    crud.db.delete('TaskTemplates', 'template_id', template_id)
    
    return redirect('manage_tasks', tracker_id=tracker_id)

@login_required
def duplicate_task(request, template_id):
    """
    Duplicate an existing task template.
    """
    template = crud.db.fetch_by_id('TaskTemplates', 'template_id', template_id)
    if not template:
        return redirect('tracker_list')
    
    # Create new template with same properties
    new_template = {
        'template_id': str(uuid.uuid4()),
        'tracker_id': template['tracker_id'],
        'description': f"{template['description']} (Copy)",
        'is_recurring': template['is_recurring'],
        'category': template.get('category', ''),
        'weight': template.get('weight', 1)
    }
    
    crud.create_task_template(new_template)
    
    return redirect('manage_tasks', tracker_id=template['tracker_id'])

@login_required
def templates_library(request):
    """
    View all available templates (pre-built + user-created).
    """
    from core.templates import PREDEFINED_TEMPLATES
    
    # Get all user templates grouped by tracker
    all_trackers = crud.get_all_tracker_definitions()
    user_templates = {}
    
    for tracker in all_trackers:
        templates = crud.get_task_templates_for_tracker(tracker['tracker_id'])
        if templates:
            user_templates[tracker['name']] = {
                'tracker': tracker,
                'templates': templates
            }
    
    context = {
        'predefined': PREDEFINED_TEMPLATES,
        'user_templates': user_templates,
    }
    return render(request, 'core/templates_library.html', context)

@login_required
def save_as_template(request, tracker_id):
    """
    Save current tracker tasks as a reusable template.
    """
    if request.method != 'POST':
        return redirect('tracker_detail', tracker_id=tracker_id)
    
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    templates = crud.get_task_templates_for_tracker(tracker_id)
    
    template_name = request.POST.get('template_name', f"{tracker['name']} Template")
    
    # Store as custom template in templates.py or database
    # For now, this is a placeholder - you could extend core/templates.py
    
    return redirect('templates_library')

@login_required
def apply_template(request, tracker_id):
    """
    Apply a template to tracker (add all template tasks).
    """
    if request.method != 'POST':
        return redirect('tracker_detail', tracker_id=tracker_id)
    
    from core.templates import initialize_templates
    
    category = request.POST.get('category')
    if category:
        initialize_templates(tracker_id, category)
    
    return redirect('manage_tasks', tracker_id=tracker_id)

@login_required
def insights_view(request, tracker_id):
    """
    Simple, plain-English insights and recommendations.
    """
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Get basic stats
    try:
        completion_data = analytics.compute_completion_rate(tracker_id)
        # Handle both dict and float returns
        if isinstance(completion_data, dict):
            completion = completion_data.get('completion_rate', 0)
        else:
            completion = completion_data or 0
            
        streaks_data = analytics.detect_streaks(tracker_id)
        # Ensure streaks is a dict with required keys
        if isinstance(streaks_data, dict) and 'current' in streaks_data and 'longest' in streaks_data:
            streaks = streaks_data
        else:
            streaks = {'current': 0, 'longest': 0}
        
        consistency_data = analytics.compute_consistency_score(tracker_id)
        if isinstance(consistency_data, dict):
            consistency = consistency_data.get('consistency_score', 0)
        else:
            consistency = consistency_data or 0
    except Exception as e:
        print(f"Error getting analytics: {e}")
        completion = 0
        streaks = {'current': 0, 'longest': 0}
        consistency = 0
    
    # Generate insights
    insights = generate_plain_english_insights(tracker_id, completion, consistency, streaks)
    recommendations = generate_recommendations(tracker_id, completion, consistency)
    
    # Get per-task performance
    templates = crud.get_task_templates_for_tracker(tracker_id)
    task_insights = []
    
    for template in templates[:5]:  # Top 5 tasks
        task_perf = get_task_performance(tracker_id, template['template_id'])
        task_insights.append({
            'task': template,
            'performance': task_perf
        })
    
    context = {
        'tracker': tracker,
        'completion': completion,
        'consistency': consistency,
        'streaks': streaks,
        'insights': insights,
        'recommendations': recommendations,
        'task_insights': task_insights,
    }
    return render(request, 'core/insights.html', context)

def generate_plain_english_insights(tracker_id, completion, consistency, streaks):
    """Generate human-readable insights."""
    insights = []
    
    # Completion insight
    if completion >= 80:
        insights.append({
            'type': 'success',
            'title': 'Excellent Progress!',
            'message': f"You're completing {completion:.0f}% of your tasks. Keep up the great work!"
        })
    elif completion >= 50:
        insights.append({
            'type': 'info',
            'title': 'Good Momentum',
            'message': f"You're at {completion:.0f}% completion. A few more consistent days will push you to excellence!"
        })
    else:
        insights.append({
            'type': 'warning',
            'title': 'Room for Improvement',
            'message': f"Currently at {completion:.0f}% completion. Try focusing on 2-3 key tasks first."
        })
    
    # Streak insight
    if streaks['current'] >= 7:
        insights.append({
            'type': 'success',
            'title': 'Amazing Streak!',
            'message': f"You've maintained a {streaks['current']}-day streak. That's dedication!"
        })
    elif streaks['current'] >= 3:
        insights.append({
            'type': 'info',
            'title': 'Building Momentum',
            'message': f"{streaks['current']} days in a row! Keep going to make it a habit."
        })
    
    # Consistency insight
    if consistency >= 0.8:
        insights.append({
            'type': 'success',
            'title': 'Highly Consistent',
            'message': "You show up regularly. This is how habits stick!"
        })
    
    return insights

def generate_recommendations(tracker_id, completion, consistency):
    """Generate actionable recommendations."""
    recommendations = []
    
    if completion < 60:
        recommendations.append({
            'title': 'Reduce Task Load',
            'suggestion': 'You have too many active tasks. Focus on 3-5 core habits to improve follow-through.',
            'action': 'Review tasks and archive less important ones'
        })
    
    if consistency < 0.5:
        recommendations.append({
            'title': 'Set Daily Reminders',
            'suggestion': 'Low consistency suggests you forget to track. Set a daily reminder at a specific time.',
            'action': 'Add a daily alarm for your tracking time'
        })
    
    if completion >= 80 and consistency >= 0.7:
        recommendations.append({
            'title': 'Level Up!',
            'suggestion': "You're crushing it! Consider adding one challenging task to push your limits.",
            'action': 'Add a stretch goal task'
        })
    
    return recommendations

def get_task_performance(tracker_id, template_id):
    """Get performance stats for a specific task."""
    instances = crud.get_tracker_instances(tracker_id)
    total = 0
    done = 0
    
    for instance in instances[-30:]:  # Last 30 days
        tasks = crud.get_task_instances_for_tracker_instance(instance['instance_id'])
        for task in tasks:
            if task['template_id'] == template_id:
                total += 1
                if task.get('status') == 'DONE':
                    done += 1
    
    rate = (done / total * 100) if total > 0 else 0
    
    # Generate insight
    if rate >= 80:
        message = f"Completed {done}/{total} times ({rate:.0f}%). Great consistency!"
    elif rate >= 50:
        message = f"Completed {done}/{total} times ({rate:.0f}%). Try pushing to 80%+."
    else:
        message = f"Completed {done}/{total} times ({rate:.0f}%). Often missed. Consider if this task fits your routine."
    
    return {
        'total': total,
        'done': done,
        'rate': rate,
        'message': message
    }

@login_required
def help_center(request):
    """
    Help center with guides, FAQs, and getting started info.
    """
    return render(request, 'core/help_center.html')

@login_required
def history(request):
    """View past performance across all trackers."""
    trackers = crud.get_all_tracker_definitions()
    
    tracker_history = []
    for tracker in trackers:
        try:
            completion = analytics.compute_completion_rate(tracker['tracker_id'])
            streaks = analytics.detect_streaks(tracker['tracker_id'])
            
            tracker_history.append({
                'tracker': tracker,
                'completion': completion,
                'streaks': streaks
            })
        except:
            pass
    
    context = {
        'tracker_history': tracker_history
    }
    return render(request, 'core/history.html', context)

# API Endpoints for dynamic interactions
@require_http_methods(["POST"])
@login_required
def api_toggle_task(request, task_id):
    """
    Toggle task status through cycle: TODO → IN_PROGRESS → DONE → TODO.
    Also supports direct status setting via 'status' POST parameter.
    
    REFACTORED: Uses TaskService with proper exception handling
    """
    from core.services.task_service import TaskService
    from core.exceptions import TaskNotFoundError, InvalidStatusError, ValidationError
    
    task_service = TaskService()
    
    try:
        # Check if explicit status is provided
        new_status = request.POST.get('status')
        
        if new_status:
            # Set specific status
            task = task_service.update_task_status(task_id, new_status)
        else:
            # Toggle through cycle
            task = task_service.toggle_task_status(task_id)
        
        return JsonResponse({
            'status': 'success',
            'new_status': task.get('status'),
            'task_id': task_id
        })
    
    except TaskNotFoundError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except InvalidStatusError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': f'{e.field}: {e.message}'}, status=400)
    except Exception as e:
        import logging
        logging.error(f"Unexpected error in api_toggle_task: {e}")
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred'}, status=500)

@require_http_methods(["POST"])
@login_required
def api_bulk_status_update(request):
    """
    Update multiple tasks to the same status in a single request.
    Expects: task_ids (list) and status (string) in POST data.
    
    REFACTORED: Uses TaskService for transaction-safe bulk updates
    """
    from core.services.task_service import TaskService
    import json
    
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        status = data.get('status')
        
        if not task_ids or not status:
            return JsonResponse({
                'status': 'error',
                'message': 'task_ids and status are required'
            }, status=400)
        
        # Use service for bulk update
        task_service = TaskService()
        result = task_service.bulk_update_tasks(task_ids, status)
        
        return JsonResponse({
            'status': 'success',
            'updated': result['updated'],
            'failed': result['failed'],
            'total': len(task_ids)
        })
    
    except ValueError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Bulk update failed'}, status=500)


@require_http_methods(["POST"])
@login_required
def api_mark_overdue_missed(request, tracker_id):
    """
    Automatically mark all overdue TODO tasks as MISSED.
    """
    from core.utils.constants import STATUS_TODO, STATUS_MISSED
    
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return JsonResponse({'status': 'error', 'message': 'Tracker not found'}, status=404)
    
    today = date.today()
    instances = crud.get_tracker_instances(tracker_id)
    marked = 0
    
    for instance in instances:
        instance_date = date.fromisoformat(instance['period_start'])
        
        # Only process past dates
        if instance_date >= today:
            continue
        
        task_instances = crud.get_task_instances_for_tracker_instance(instance['instance_id'])
        
        for task in task_instances:
            if task.get('status') == STATUS_TODO:
                crud.db.update('TaskInstances', 'task_instance_id', task['task_instance_id'], 
                             {'status': STATUS_MISSED})
                marked += 1
    
    return JsonResponse({
        'status': 'success',
        'marked_count': marked,
        'message': f'{marked} overdue tasks marked as MISSED'
    })
