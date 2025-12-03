from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from core import crud, services, templates, analytics, exports
from datetime import date, datetime, timedelta
import uuid

def dashboard(request):
    """
    Main dashboard view.
    Shows today's tasks and active trackers with quick stats.
    """
    today = date.today()
    
    # Ensure instances exist for today
    services.check_all_trackers(today)
    
    # Get all trackers with stats
    trackers = crud.get_all_tracker_definitions()
    
    tracker_stats = []
    for tracker in trackers:
        try:
            stats = analytics.compute_tracker_stats(tracker['tracker_id'])
            tracker_stats.append({
                'tracker': tracker,
                'stats': stats
            })
        except:
            tracker_stats.append({
                'tracker': tracker,
                'stats': {}
            })
    
    context = {
        'trackers': tracker_stats,
        'today': today,
    }
    return render(request, 'core/dashboard.html', context)

def tracker_list(request):
    """List and manage trackers."""
    trackers = crud.get_all_tracker_definitions()
    return render(request, 'core/tracker_list.html', {'trackers': trackers})

def create_tracker(request):
    """Create a new tracker."""
    if request.method == 'POST':
        name = request.POST.get('name')
        time_mode = request.POST.get('time_mode')
        description = request.POST.get('description', '')
        category = request.POST.get('category')
        
        tracker_id = str(uuid.uuid4())
        crud.db.insert('TrackerDefinitions', {
            'tracker_id': tracker_id,
            'name': name,
            'time_mode': time_mode,
            'description': description,
            'created_at': date.today().isoformat()
        })
        
        if category:
            templates.initialize_templates(tracker_id, category)
            
        return redirect('tracker_detail', tracker_id=tracker_id)
        
    return render(request, 'core/create_tracker.html')

def tracker_detail(request, tracker_id):
    """Detailed tracker view with inline analytics."""
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Get comprehensive stats
    completion = analytics.compute_completion_rate(tracker_id)
    streaks = analytics.detect_streaks(tracker_id)
    consistency = analytics.compute_consistency_score(tracker_id)
    balance = analytics.compute_balance_score(tracker_id)
    
    # Get recent instances
    instances = crud.get_tracker_instances(tracker_id)[-10:]  # Last 10
    
    # Get charts
    completion_chart = analytics.generate_completion_chart(tracker_id)
    category_chart = analytics.generate_category_pie_chart(tracker_id)
    
    context = {
        'tracker': tracker,
        'completion': completion,
        'streaks': streaks,
        'consistency': consistency,
        'balance': balance,
        'instances': instances,
        'completion_chart': completion_chart,
        'category_chart': category_chart,
    }
    return render(request, 'core/tracker_detail.html', context)

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

def monthly_tracker(request, tracker_id):
    """
    Interactive monthly habit tracker view.
    Shows a grid with tasks/activities as rows and days of month as columns.
    """
    from calendar import monthrange
    
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Get current month or from query params
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # Get number of days in month
    _, num_days = monthrange(year, month)
    
    # Get all task templates for this tracker
    templates = crud.get_task_templates_for_tracker(tracker_id)
    
    # Build calendar matrix
    calendar_data = []
    for template in templates:
        row = {
            'template': template,
            'days': []
        }
        
        for day in range(1, num_days + 1):
            current_date = date(year, month, day)
            
            # Find if there's a task instance for this day
            instances = crud.get_tracker_instances(tracker_id)
            task_instance = None
            
            for inst in instances:
                if inst['period_start'] == current_date.isoformat():
                    tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
                    task_instance = next((t for t in tasks if t['template_id'] == template['template_id']), None)
                    break
            
            row['days'].append({
                'day': day,
                'date': current_date,
                'task': task_instance,
                'is_done': task_instance and task_instance.get('status') == 'DONE' if task_instance else False,
                'is_today': current_date == today
            })
        
        calendar_data.append(row)
    
    # Month navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'tracker': tracker,
        'calendar_data': calendar_data,
        'year': year,
        'month': month,
        'month_name': date(year, month, 1).strftime('%B %Y'),
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'num_days': num_days,
    }
    return render(request, 'core/monthly_tracker.html', context)

def today_view(request, tracker_id):
    """
    Today-focused view: Simple grid of tasks with status toggles.
    Focus on "What do I need to do TODAY?"
    """
    from core.constants import STATUS_INFO
    
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    today = date.today()
    
    # Ensure instances exist for today
    services.ensure_tracker_instance(tracker_id, today)
    
    # Get all task templates
    templates = crud.get_task_templates_for_tracker(tracker_id)
    
    # Get today's tracker instance
    instances = crud.get_tracker_instances(tracker_id)
    today_instance = next((inst for inst in instances if inst['period_start'] == today.isoformat()), None)
    
    # Build task list with status
    tasks_data = []
    if today_instance:
        task_instances = crud.get_task_instances_for_tracker_instance(today_instance['instance_id'])
        
        for template in templates:
            task = next((t for t in task_instances if t['template_id'] == template['template_id']), None)
            
            tasks_data.append({
                'template': template,
                'task': task,
                'status': task.get('status', 'TODO') if task else 'TODO',
                'notes': task.get('notes', '') if task else '',
            })
    else:
        for template in templates:
            tasks_data.append({
                'template': template,
                'task': None,
                'status': 'TODO',
                'notes': '',
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

def week_view(request, tracker_id):
    """
    Week view: 7-day grid (Mon-Sun) × Tasks with status cells.
    """
    from core.constants import STATUS_INFO
    from calendar import day_name
    
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
    # Get week offset from query params (default = current week)
    week_offset = int(request.GET.get('week', 0))
    
    # Calculate week start (Monday)
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    
    # Generate 7 days
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    
    # Ensure instances exist
    for day in week_days:
        services.ensure_tracker_instance(tracker_id, day)
    
    # Get templates
    templates = crud.get_task_templates_for_tracker(tracker_id)
    
    # Build grid: rows = templates, cols = 7 days
    grid_data = []
    for template in templates:
        row = {
            'template': template,
            'days': []
        }
        
        for day in week_days:
            # Find instance for this day
            instances = crud.get_tracker_instances(tracker_id)
            day_instance = next((inst for inst in instances if inst['period_start'] == day.isoformat()), None)
            
            if day_instance:
                task_instances = crud.get_task_instances_for_tracker_instance(day_instance['instance_id'])
                task = next((t for t in task_instances if t['template_id'] == template['template_id']), None)
            else:
                task = None
            
            row['days'].append({
                'date': day,
                'task': task,
                'status': task.get('status', 'TODO') if task else 'TODO',
                'is_today': day == today
            })
        
        grid_data.append(row)
    
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

def custom_range_view(request, tracker_id):
    """
    Custom date range view: User selects start and end dates.
    """
    from core.constants import STATUS_INFO
    
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        return redirect('tracker_list')
    
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
    
    # Generate date range
    date_range = []
    current = start_date
    while current <= end_date:
        date_range.append(current)
        current += timedelta(days=1)
    
    # Ensure instances exist
    for day in date_range:
        services.ensure_tracker_instance(tracker_id, day)
    
    # Get templates
    templates = crud.get_task_templates_for_tracker(tracker_id)
    
    # Build grid
    grid_data = []
    for template in templates:
        row = {
            'template': template,
            'days': []
        }
        
        for day in date_range:
            instances = crud.get_tracker_instances(tracker_id)
            day_instance = next((inst for inst in instances if inst['period_start'] == day.isoformat()), None)
            
            if day_instance:
                task_instances = crud.get_task_instances_for_tracker_instance(day_instance['instance_id'])
                task = next((t for t in task_instances if t['template_id'] == template['template_id']), None)
            else:
                task = None
            
            row['days'].append({
                'date': day,
                'task': task,
                'status': task.get('status', 'TODO') if task else 'TODO',
                'is_today': day == today
            })
        
        grid_data.append(row)
    
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
            
        streaks = analytics.detect_streaks(tracker_id)
        
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

def help_center(request):
    """
    Help center with guides, FAQs, and getting started info.
    """
    return render(request, 'core/help_center.html')

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
def api_toggle_task(request, task_id):
    """
    Toggle task status through cycle: TODO → IN_PROGRESS → DONE → TODO.
    Also supports direct status setting via 'status' POST parameter.
    """
    from core.constants import STATUS_TODO, STATUS_IN_PROGRESS, STATUS_DONE
    
    task = crud.db.fetch_by_id('TaskInstances', 'task_instance_id', task_id)
    if not task:
        return JsonResponse({'status': 'error', 'message': 'Task not found'}, status=404)
    
    # Check if explicit status is provided
    new_status = request.POST.get('status')
    
    if not new_status:
        # Cycle through statuses
        current_status = task.get('status', STATUS_TODO)
        status_cycle = {
            STATUS_TODO: STATUS_IN_PROGRESS,
            STATUS_IN_PROGRESS: STATUS_DONE,
            STATUS_DONE: STATUS_TODO,
        }
        new_status = status_cycle.get(current_status, STATUS_TODO)
    
    # Update task
    crud.db.update('TaskInstances', 'task_instance_id', task_id, {'status': new_status})
    
    return JsonResponse({
        'status': 'success',
        'task_id': task_id,
        'new_status': new_status
    })

@require_http_methods(["POST"])
def api_bulk_status_update(request):
    """
    Update multiple tasks to the same status.
    POST params: task_ids (comma-separated), status
    """
    from core.constants import STATUS_CHOICES
    
    task_ids_str = request.POST.get('task_ids', '')
    new_status = request.POST.get('status', 'DONE')
    
    if not task_ids_str or new_status not in STATUS_CHOICES:
        return JsonResponse({'status': 'error', 'message': 'Invalid parameters'}, status=400)
    
    task_ids = [tid.strip() for tid in task_ids_str.split(',')]
    updated = 0
    
    for task_id in task_ids:
        task = crud.db.fetch_by_id('TaskInstances', 'task_instance_id', task_id)
        if task:
            crud.db.update('TaskInstances', 'task_instance_id', task_id, {'status': new_status})
            updated += 1
    
    return JsonResponse({
        'status': 'success',
        'updated_count': updated,
        'new_status': new_status
    })

@require_http_methods(["POST"])
def api_mark_overdue_missed(request, tracker_id):
    """
    Automatically mark all overdue TODO tasks as MISSED.
    """
    from core.constants import STATUS_TODO, STATUS_MISSED
    
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
