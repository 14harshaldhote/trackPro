"""
Tracker Pro - SPA API Views
AJAX endpoints for interactive components
"""
import json
from datetime import date, datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
# from django.contrib.auth.decorators import login_required  <-- Replaced with custom decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from functools import wraps

from .models import TrackerDefinition, TrackerInstance, TaskInstance, DayNote, TaskTemplate
from .services import instance_service as services
from .services.task_service import TaskService
from .services.tracker_service import TrackerService
from .services.search_service import SearchService
from .utils.response_helpers import UXResponse
from .utils.constants import HAPTIC_FEEDBACK, UI_COLORS
from .utils.error_handlers import handle_service_errors
from .helpers.cache_helpers import check_etag

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

def require_auth(view_func):
    """
    Decorator to ensure user is logged in for API endpoints.
    Supports both Session (Browser) and JWT (Mobile) authentication.
    Returns 401 JSON instead of redirecting to login page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Check existing Session Auth (Django Middleware)
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        # 2. Check JWT Auth (Mobile)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                # Manually authenticate using SimpleJWT
                jwt_auth = JWTAuthentication()
                # authenticate() returns (user, token) or None
                auth_result = jwt_auth.authenticate(request)
                if auth_result:
                    request.user, _ = auth_result
                    return view_func(request, *args, **kwargs)
            except (InvalidToken, TokenError) as e:
                return JsonResponse({
                    'success': False,
                    'error': {
                        'message': f'Invalid token: {str(e)}',
                        'code': 'INVALID_TOKEN',
                        'retry': False
                    }
                }, status=401)
        
        # 3. No valid auth found
        return JsonResponse({
            'success': False,
            'error': {
                'message': 'Authentication required',
                'code': 'UNAUTHORIZED',
                'retry': True
            }
        }, status=401)
    return _wrapped_view

# Initialize Services
task_service = TaskService()
tracker_service = TrackerService()
search_service = SearchService()


# ============================================================================
# TASK ENDPOINTS
# ============================================================================

@require_auth
@require_POST
@handle_service_errors
def api_task_toggle(request, task_id):
    """Toggle task status with UX-optimized response including celebration feedback"""
    # Use Service
    result = task_service.toggle_task_status(task_id)
    task_id = result['task_instance_id']
    new_status = result['status']
    
    # Calculate remaining tasks for stats delta (Keep read-logic here or move to service? 
    # For now, quick read is fine, or add get_remaining_count to service. 
    # To minimize risk, we keep the read logic but use the updated task from service)
    
    # We need the task object for tracker info, or we can fetch it. 
    # Service returns dict. Let's fetch lightweight or assume we have info.
    # Actually proper refactor would put Feedback logic in Service or specialized View Helper.
    # I'll keep Feedback logic in View for now as it's View-specific (UX), but use Service for mutation.
    
    # Re-fetch for context (or service returns it)
    task = TaskInstance.objects.select_related('tracker_instance__tracker').get(task_instance_id=task_id)
    tracker_instance = task.tracker_instance
    
    remaining = TaskInstance.objects.filter(
        tracker_instance=tracker_instance,
        status__in=['TODO', 'IN_PROGRESS']
    ).count()
    
    # Determine feedback type based on action
    feedback = None
    if new_status == 'DONE':
        if remaining == 0:
            # All tasks complete - celebration!
            feedback = UXResponse.celebration(
                "All tasks complete! 🎉",
                animation="confetti"
            )
        else:
            feedback = {
                'type': 'success',
                'message': UXResponse.get_completion_message('DONE'),
                'haptic': 'success',
                'animation': 'checkmark',
                'toast': True
            }
    elif new_status == 'SKIPPED':
        feedback = {
            'type': 'info',
            'message': 'Task skipped',
            'haptic': 'warning',
            'toast': False
        }
    else:
        feedback = {
            'type': 'info',
            'message': 'Task reopened',
            'haptic': 'light',
            'toast': False
        }
    
    return UXResponse.success(
        message=f"Task {new_status.lower()}",
        data=UXResponse.with_undo(
            {
                'task_id': task_id,
                'old_status': 'TODO' if new_status == 'DONE' else 'DONE', # Approx for undo
                'new_status': new_status,
            },
            undo_data={'task_id': task_id, 'old_status': 'TODO'} # Simplified
        ),
        feedback=feedback,
        stats_delta={
            'remaining_tasks': remaining,
            'all_complete': remaining == 0,
            'tracker_id': str(tracker_instance.tracker.tracker_id)
        }
    )


@require_auth
@require_POST
@handle_service_errors
def api_task_delete(request, task_id):
    """Delete a single task instance with UX feedback"""
    # Use Service
    info = task_service.delete_task_instance(task_id, request.user)
    
    return UXResponse.success(
        message='Task deleted',
        data={
            'task_id': task_id,
            'deleted': True,
            **info
        },
        feedback={
            'type': 'info',
            'message': 'Task deleted',
            'haptic': 'light',
            'toast': True
        }
    )


@require_auth
@require_POST
@handle_service_errors
def api_task_status(request, task_id):
    """Set specific task status and update notes with UX feedback"""
    data = json.loads(request.body)
    status = data.get('status')
    notes = data.get('notes')
    
    # Service Call
    updated_task = task_service.update_task_status(task_id, status, notes)
    
    # Haptic mapping logic for Feedback (Keep in view)
    haptic_map = {
        'DONE': 'success',
        'SKIPPED': 'warning',
        'TODO': 'light',
        'IN_PROGRESS': 'medium',
        'MISSED': 'warning',
        'BLOCKED': 'warning'
    }
    
    status_val = updated_task['status'] if isinstance(updated_task, dict) else updated_task.status
    
    return UXResponse.success(
        message=UXResponse.get_completion_message(status_val),
        data={
            'task_id': task_id,
            'new_status': status_val,
            'notes': notes
        },
        feedback={
            'type': 'success' if status_val == 'DONE' else 'info',
            'message': UXResponse.get_completion_message(status_val),
            'haptic': haptic_map.get(status_val, 'light'),
            'toast': status_val == 'DONE'
        }
    )


@require_auth
@require_POST
@handle_service_errors
def api_tasks_bulk(request):
    """Bulk actions on multiple tasks"""
    data = json.loads(request.body)
    action = data.get('action')
    task_ids = data.get('task_ids', [])
    
    if not task_ids:
        return UXResponse.error('No tasks selected', error_code='NO_SELECTION')
        
    # Map frontend actions to status
    status_map = {
        'complete': 'DONE',
        'skip': 'SKIPPED',
        'pending': 'TODO',
    }
    
    if action in status_map:
        result = task_service.bulk_update_tasks(task_ids, status_map[action])
        return UXResponse.success(
            message=f"{result['updated']} tasks updated",
            data={
                'action': action,
                'count': result['updated']
            }
        )
    elif action == 'delete':
        # Implement bulk delete in service if needed, for now loop? 
        # Or simplified bulk delete. task_service.delete_task_instance is single.
        # I'll stick to legacy ORM for bulk delete as it wasn't added to service yet, 
        # OR I should have added it. For now, let's leave legacy for DELETE only or implement loop.
        # Efficient way:
        TaskInstance.objects.filter(task_instance_id__in=task_ids, tracker_instance__tracker__user=request.user).update(deleted_at=timezone.now())
        return UXResponse.success(message='Tasks deleted')
    else:
        return UXResponse.error('Unknown action', error_code='INVALID_ACTION')


@require_auth
@require_POST
@handle_service_errors
def api_task_add(request, tracker_id):
    """Quick add task to tracker"""
    data = json.loads(request.body)
    task = task_service.quick_add_task(
        tracker_id=tracker_id,
        user=request.user,
        description=data.get('description', ''),
        category=data.get('category', ''),
        weight=data.get('weight', 1),
        time_of_day=data.get('time_of_day', 'anytime')
    )
    return UXResponse.success(
        message='Task added',
        data={'task': task},
        feedback={'type': 'success', 'haptic': 'success', 'toast': True}
    )


@require_auth
@require_POST
@handle_service_errors
def api_task_edit(request, task_id):
    """Edit full task details"""
    data = json.loads(request.body)
    updated = task_service.update_task_details(task_id, request.user, data)
    return UXResponse.success(
        message='Task updated successfully',
        data={'task': updated},
        feedback={'type': 'success', 'haptic': 'light', 'toast': True}
    )


@require_auth
@require_POST
@handle_service_errors
def api_tracker_reorder(request, tracker_id):
    """Reorder tasks in a tracker"""
    data = json.loads(request.body)
    order = data.get('order', [])
    
    # Service Call
    tracker_service.reorder_tasks(tracker_id, request.user, order)
    
    return UXResponse.success(
        message='Order saved',
        feedback={'type': 'none', 'haptic': 'light', 'toast': False}
    )


# ============================================================================
# TRACKER ENDPOINTS
# ============================================================================

@require_auth
@require_POST
@handle_service_errors
def api_tracker_create(request):
    """Create new tracker via AJAX"""
    data = json.loads(request.body)
    tracker = tracker_service.create_tracker(request.user, data)
    return UXResponse.success(
        message='Tracker created successfully',
        data={
            'tracker': tracker,
            'redirect': f'/tracker/{tracker["id"]}/'
        },
        feedback={'type': 'success', 'haptic': 'success', 'toast': True}
    )


@require_auth
@require_POST
@handle_service_errors
def api_tracker_delete(request, tracker_id):
    """Delete tracker via AJAX"""
    info = tracker_service.delete_tracker(tracker_id, request.user)
    return UXResponse.success(
        message=f'"{info["name"]}" deleted',
        data={'tracker_id': tracker_id, 'redirect': '/trackers/'},
        feedback={'type': 'info', 'message': f'"{info["name"]}" deleted', 'toast': True}
    )


@require_auth
@require_POST
@handle_service_errors
def api_tracker_update(request, tracker_id):
    """Update tracker details via AJAX"""
    data = json.loads(request.body)
    tracker = tracker_service.update_tracker(tracker_id, request.user, data)
    return UXResponse.success(
        message='Tracker updated successfully',
        data={'tracker': tracker},
        feedback={'type': 'success', 'haptic': 'light', 'toast': True}
    )


@csrf_exempt  # Required for iOS/mobile clients
@require_auth
@require_POST
def api_template_activate(request):
    """
    Create tracker from predefined template.
    
    POST /api/v1/templates/activate/
    Body: {'template_key': 'morning'}
    
    Returns: {'tracker_id': '...', 'message': '...'}
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError as e:
        logger.error(f"Template activate - JSON parse error: {e}")
        return UXResponse.error(
            message='Invalid JSON in request body',
            error_code='INVALID_JSON',
            status=400
        )
    
    template_key = data.get('template_key')
    
    logger.info(f"Template activation requested: {template_key} by user {request.user.id}")
    
    # Define all template configurations matching templates.html
    TEMPLATES = {
        'morning': {
            'name': 'Morning Routine',
            'description': 'Start your day with purpose. Includes meditation, exercise, and planning.',
            'time_period': 'daily',
            'tasks': [
                {'description': 'Wake up at target time', 'category': 'routine', 'weight': 1, 'time_of_day': 'morning'},
                {'description': 'Meditation (10 min)', 'category': 'mindfulness', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Morning exercise (30 min)', 'category': 'fitness', 'weight': 3, 'time_of_day': 'morning'},
                {'description': 'Healthy breakfast', 'category': 'nutrition', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Review daily goals', 'category': 'planning', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Shower and get ready', 'category': 'routine', 'weight': 1, 'time_of_day': 'morning'},
                { 'description': 'Journal (5 min)', 'category': 'mindfulness', 'weight': 1, 'time_of_day': 'morning'},
                {'description': 'Check calendar and priorities', 'category': 'planning', 'weight': 1, 'time_of_day': 'morning'},
            ]
        },
        'fitness': {
            'name': 'Fitness Tracker',
            'description': 'Track workouts, nutrition, and recovery for optimal fitness.',
            'time_period': 'daily',
            'tasks': [
                {'description': 'Cardio workout (30 min)', 'category': 'cardio', 'weight': 3, 'time_of_day': 'morning'},
                {'description': 'Strength training', 'category': 'strength', 'weight': 3, 'time_of_day': 'afternoon'},
                {'description': 'Log meals and track calories', 'category': 'nutrition', 'weight': 2, 'time_of_day': 'evening'},
                {'description': 'Drink 8 glasses of water', 'category': 'hydration', 'weight': 2, 'time_of_day': 'anytime'},
                {'description': 'Stretching (15 min)', 'category': 'flexibility', 'weight': 1, 'time_of_day': 'evening'},
                {'description': 'Track weight and measurements', 'category': 'tracking', 'weight': 1, 'time_of_day': 'morning'},
            ]
        },
        'study': {
            'name': 'Study Plan',
            'description': 'Structured learning with reading, practice, and review sessions.',
            'time_period': 'daily',
            'tasks': [
                {'description': 'Review notes from previous session', 'category': 'review', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Active learning (2 hours)', 'category': 'study', 'weight': 3, 'time_of_day': 'afternoon'},
                {'description': 'Practice problems', 'category': 'practice', 'weight': 3, 'time_of_day': 'afternoon'},
                {'description': 'Create flashcards for new concepts', 'category': 'review', 'weight': 2, 'time_of_day': 'evening'},
                {'description': 'Evening review (30 min)', 'category': 'review', 'weight': 2, 'time_of_day': 'evening'},
            ]
        },
        'work': {
            'name': 'Work Productivity',
            'description': 'Focus blocks, email management, and daily planning.',
            'time_period': 'daily',
            'tasks': [
                {'description': 'Plan top 3 priorities', 'category': 'planning', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Deep work block 1 (2 hours)', 'category': 'focus', 'weight': 3, 'time_of_day': 'morning'},
                {'description': 'Check and respond to emails', 'category': 'communication', 'weight': 1, 'time_of_day': 'afternoon'},
                {'description': 'Deep work block 2 (2 hours)', 'category': 'focus', 'weight': 3, 'time_of_day': 'afternoon'},
                {'description': 'Team meetings and collaboration', 'category': 'collaboration', 'weight': 2, 'time_of_day': 'afternoon'},
                {'description': 'Review progress and plan tomorrow', 'category': 'planning', 'weight': 2, 'time_of_day': 'evening'},
                {'description': 'Clear inbox to zero', 'category': 'communication', 'weight': 1, 'time_of_day': 'evening'},
            ]
        },
        'mindfulness': {
            'name': 'Mindfulness',
            'description': 'Meditation, gratitude journaling, and mental wellness.',
            'time_period': 'daily',
            'tasks': [
                {'description': 'Morning meditation (15 min)', 'category': 'meditation', 'weight': 3, 'time_of_day': 'morning'},
                {'description': 'Gratitude journal (3 things)', 'category': 'journaling', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Midday breathing exercise (5 min)', 'category': 'breathwork', 'weight': 1, 'time_of_day': 'afternoon'},
                {'description': 'Evening reflection', 'category': 'journaling', 'weight': 2, 'time_of_day': 'evening'},
            ]
        },
        'evening': {
            'name': 'Evening Wind Down',
            'description': 'Prepare for restful sleep with relaxation routines.',
            'time_period': 'daily',
            'tasks': [
                {'description': 'No screens 1 hour before bed', 'category': 'digital detox', 'weight': 2, 'time_of_day': 'evening'},
                {'description': 'Light dinner (3 hours before bed)', 'category': 'nutrition', 'weight': 1, 'time_of_day': 'evening'},
                {'description': 'Evening walk or gentle yoga', 'category': 'movement', 'weight': 2, 'time_of_day': 'evening'},
                {'description': 'Read for 30 minutes', 'category': 'relaxation', 'weight': 2, 'time_of_day': 'evening'},
                {'description': 'Bedtime routine (skincare, etc.)', 'category': 'routine', 'weight': 1, 'time_of_day': 'evening'},
            ]
        },
        'weekly-review': {
            'name': 'Weekly Review',
            'description': 'Reflect on the week and plan for success ahead.',
            'time_period': 'weekly',
            'tasks': [
                {'description': 'Review completed tasks from week', 'category': 'review', 'weight': 2, 'time_of_day': 'anytime'},
                {'description': 'Celebrate wins and progress', 'category': 'reflection', 'weight': 1, 'time_of_day': 'anytime'},
                {'description': 'Identify lessons learned', 'category': 'reflection', 'weight': 2, 'time_of_day': 'anytime'},
                {'description': 'Plan goals for next week', 'category': 'planning', 'weight': 3, 'time_of_day': 'anytime'},
                {'description': 'Schedule important tasks', 'category': 'planning', 'weight': 2, 'time_of_day': 'anytime'},
                {'description': 'Review analytics and adjust habits', 'category': 'optimization', 'weight': 2, 'time_of_day': 'anytime'},
            ]
        },
        'language': {
            'name': 'Language Learning',
            'description': 'Vocabulary, grammar, speaking practice, and immersion.',
            'time_period': 'daily',
            'tasks': [
                {'description': 'App practice (15 min)', 'category': 'digital practice', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Learn 10 new vocabulary words', 'category': 'vocabulary', 'weight': 2, 'time_of_day': 'morning'},
                {'description': 'Grammar exercises', 'category': 'grammar', 'weight': 2, 'time_of_day': 'afternoon'},
                {'description': 'Speaking practice (10 min)', 'category': 'speaking', 'weight': 3, 'time_of_day': 'afternoon'},
                {'description': 'Watch content in target language', 'category': 'immersion', 'weight': 2, 'time_of_day': 'evening'},
            ]
        },
    }
    
    # Validate template_key is provided
    if not template_key:
        return UXResponse.error(
            message='template_key is required',
            error_code='MISSING_TEMPLATE_KEY',
            data={
                'available_templates': list(TEMPLATES.keys()),
                'usage': 'POST /api/v1/templates/activate/ with body {"template_key": "morning"}'
            },
            status=400
        )
    
    # Validate template exists
    if template_key not in TEMPLATES:
        return UXResponse.error(
            message=f'Template "{template_key}" not found',
            error_code='INVALID_TEMPLATE',
            data={
                'available_templates': list(TEMPLATES.keys()),
                'requested': template_key
            },
            status=404
        )
    
    template_config = TEMPLATES[template_key]
    
    # Create tracker manually to handle task dictionaries properly
    import uuid
    from django.db import transaction
    from .models import TrackerDefinition, TaskTemplate
    
    try:
        with transaction.atomic():
            # Create the tracker
            tracker = TrackerDefinition.objects.create(
                user=request.user,
                tracker_id=str(uuid.uuid4()),
                name=template_config['name'],
                description=template_config.get('description', ''),
                time_mode=template_config.get('time_period', 'daily'),
                status='active'
            )
            
            # Create task templates from task dictionaries
            tasks = template_config.get('tasks', [])
            for i, task_data in enumerate(tasks):
                if isinstance(task_data, dict):
                    TaskTemplate.objects.create(
                        template_id=str(uuid.uuid4()),
                        tracker=tracker,
                        description=task_data.get('description', ''),
                        category=task_data.get('category', ''),
                        weight=task_data.get('weight', len(tasks) - i),
                        time_of_day=task_data.get('time_of_day', 'anytime'),
                        is_recurring=True
                    )
                elif isinstance(task_data, str) and task_data.strip():
                    # Fallback for string tasks
                    TaskTemplate.objects.create(
                        template_id=str(uuid.uuid4()),
                        tracker=tracker,
                        description=task_data,
                        is_recurring=True,
                        weight=len(tasks) - i,
                        time_of_day='anytime'
                    )
            
            # Instantiate for today immediately to generate tasks
            from core.services.instance_service import ensure_tracker_instance
            ensure_tracker_instance(str(tracker.tracker_id), timezone.now().date(), request.user)
        
        return UXResponse.success(
            message=f'Created "{template_config["name"]}" tracker',
            data={
                'tracker_id': str(tracker.tracker_id),
                'tracker_name': template_config['name'],
                'task_count': len(tasks)
            },
            feedback={
                'type': 'success',
                'message': f'"{template_config["name"]}" tracker created!',
                'haptic': 'success',
                'toast': True
            }
        )
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Template activate error: {str(e)}")
        logger.error(f"Traceback: {error_traceback}")
        return UXResponse.error(
            message=f'Failed to create tracker: {str(e)}',
            error_code='CREATE_FAILED',
            status=500
        )


# ============================================================================
# SEARCH ENDPOINT (Enhanced with suggestions)
# ============================================================================

@require_GET
@handle_service_errors
def api_search(request):
    """
    Enhanced global search with:
    - Quick commands
    - Suggestions
    - Multi-entity search
    """
    query = request.GET.get('q', '').strip()
    save_history = request.GET.get('save', 'true') == 'true'
    
    results = search_service.search(request.user, query, save_history)
    
    # Enrich with commands (View specific)
    results['commands'] = [
        {'shortcut': 'Ctrl+N', 'label': 'New Tracker', 'action': 'modal', 'url': '/modals/add-tracker/'},
        {'shortcut': 'T', 'label': 'Today', 'action': 'navigate', 'url': '/today/'},
        {'shortcut': 'W', 'label': 'Week View', 'action': 'navigate', 'url': '/week/'},
        {'shortcut': 'D', 'label': 'Dashboard', 'action': 'navigate', 'url': '/'},
        {'shortcut': 'A', 'label': 'Analytics', 'action': 'navigate', 'url': '/analytics/'},
    ]
    
    return JsonResponse(results)


# ============================================================================
# DAY NOTE ENDPOINT
# ============================================================================

@require_auth
@require_POST
@handle_service_errors
def api_day_note(request, date_str):
    """Save day note"""
    data = json.loads(request.body)
    note_text = data.get('note', '')
    
    note_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    note, created = DayNote.objects.update_or_create(
        user=request.user,
        date=note_date,
        defaults={'content': note_text}
    )
    
    return UXResponse.success(
        message='Note saved',
        feedback={'type': 'success', 'haptic': 'light', 'toast': True}
    )


# ============================================================================
# UNDO ENDPOINT
# ============================================================================

@require_auth
@require_POST
@handle_service_errors
def api_undo(request):
    """Undo last action (stored in session)"""
    data = json.loads(request.body)
    undo_type = data.get('type')
    undo_data = data.get('data', {})
    
    if undo_type == 'task_toggle':
        task_id = undo_data.get('task_id')
        old_status = undo_data.get('old_status')
        
        # TaskInstance uses task_instance_id as primary key
        # Allow finding soft-deleted tasks for restoration
        try:
            # Try finding active task
            instance = TaskInstance.objects.get(
                task_instance_id=task_id,
                tracker_instance__tracker__user=request.user
            )
        except TaskInstance.DoesNotExist:
            # Try finding soft-deleted task
            instance = TaskInstance.objects.get(
                task_instance_id=task_id,
                tracker_instance__tracker__user=request.user,
                deleted_at__isnull=False
            )
            
        instance.status = old_status
        if instance.deleted_at:
            instance.restore()
        else:
            instance.save()
        
        return UXResponse.success(message='Action undone', feedback={'type': 'success', 'message': 'Action undone'})

    elif undo_type == 'task_delete':
        task_id = undo_data.get('task_id')
        
        # Find the soft-deleted task
        instance = get_object_or_404(
            TaskInstance,
            task_instance_id=task_id,
            tracker_instance__tracker__user=request.user
        )
        
        # Restore it
        if instance.deleted_at:
            instance.restore()
            
        return UXResponse.success(message='Task restored', feedback={'type': 'success', 'message': 'Task restored'})
    
    return UXResponse.error('Unknown undo type', error_code='INVALID_UNDO')


# ============================================================================
# EXPORT ENDPOINT
# ============================================================================

@require_auth
@require_GET
@handle_service_errors
def api_export(request, tracker_id):
    """Export tracker data"""
    import csv
    from django.http import HttpResponse
    
    tracker = get_object_or_404(
        TrackerDefinition,
        id=tracker_id,
        user=request.user
    )
    
    format_type = request.GET.get('format', 'csv')
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    instances = TrackerInstance.objects.filter(
        tracker_definition=tracker
    ).order_by('date')
    
    if start_date:
        instances = instances.filter(date__gte=start_date)
    if end_date:
        instances = instances.filter(date__lte=end_date)
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{tracker.name}_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Description', 'Category', 'Status', 'Weight'])
        
        for instance in instances:
            writer.writerow([
                instance.date,
                instance.description,
                instance.category,
                instance.status,
                instance.weight
            ])
        
        return response
    
    # JSON format
    return JsonResponse({
        'tracker': {
            'name': tracker.name,
            'description': tracker.description
        },
        'tasks': [
            {
                'date': str(i.date),
                'description': i.description,
                'category': i.category,
                'status': i.status,
                'weight': i.weight
            }
            for i in instances
        ]
    })


# ============================================================================
# SHARE ENDPOINT
# ============================================================================

@require_auth
@require_POST
@handle_service_errors
def api_share_tracker(request, tracker_id):
    """Generate share link for tracker"""
    import uuid
    
    tracker = get_object_or_404(
        TrackerDefinition,
        id=tracker_id,
        user=request.user
    )
    
    # Generate share token if not exists
    if not tracker.share_token:
        tracker.share_token = str(uuid.uuid4())[:8]
        tracker.save()
    
    share_url = request.build_absolute_uri(f'/shared/{tracker.share_token}/')
    
    return UXResponse.success(
        message='Share link generated',
        data={
            'share_url': share_url,
            'token': tracker.share_token
        }
    )


# ============================================================================
# FORM VALIDATION ENDPOINT
# ============================================================================

@require_auth
@require_POST
@handle_service_errors
def api_validate_field(request):
    """Real-time field validation"""
    data = json.loads(request.body)
    field = data.get('field')
    value = data.get('value', '')
    
    errors = []
    
    if field == 'tracker_name':
        if not value.strip():
            errors.append('Name is required')
        elif len(value) > 100:
            errors.append('Name must be less than 100 characters')
        elif TrackerDefinition.objects.filter(
            user=request.user,
            name__iexact=value.strip()
        ).exists():
            errors.append('A tracker with this name already exists')
    
    elif field == 'task_description':
        if not value.strip():
            errors.append('Description is required')
        elif len(value) > 500:
            errors.append('Description must be less than 500 characters')
    
    return JsonResponse({
        'valid': len(errors) == 0,
        'errors': errors
    })


# ============================================================================
# INSIGHTS API ENDPOINT
# ============================================================================

@require_auth
@require_GET
@handle_service_errors
def api_insights(request, tracker_id=None):
    """
    Get behavioral insights for tracker(s).
    
    GET /api/insights/              - All user's tracker insights
    GET /api/insights/<tracker_id>/ - Single tracker insights
    
    Returns: JSON list of insights with severity, description, actions
    """
    from core.behavioral import get_insights
    
    if tracker_id:
        # Single tracker
        tracker = get_object_or_404(
            TrackerDefinition,
            tracker_id=tracker_id,
            user=request.user
        )
        insights = get_insights(tracker_id)
        for insight in insights:
            insight['tracker_name'] = tracker.name
    else:
        # All user trackers
        insights = []
        trackers = TrackerDefinition.objects.filter(user=request.user, deleted_at__isnull=True)
        for tracker in trackers:
            try:
                tracker_insights = get_insights(tracker.tracker_id)
                for insight in tracker_insights:
                    insight['tracker_name'] = tracker.name
                    insight['tracker_id'] = tracker.tracker_id
                insights.extend(tracker_insights)
            except Exception:
                continue
    
    # Sort by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    insights.sort(key=lambda x: severity_order.get(x.get('severity', 'low'), 3))
    
    return JsonResponse({
        'success': True,
        'insights': insights,
        'count': len(insights)
    })


# ============================================================================
# CHART DATA API ENDPOINT
# ============================================================================

@require_auth
@require_GET
@handle_service_errors
def api_chart_data(request):
    """
    Get chart data for analytics visualizations.
    
    GET /api/chart-data/?type=bar&tracker_id=xxx&days=30
    
    Types: bar, line, pie, completion
    """
    from core import analytics
    
    chart_type = request.GET.get('type', 'bar')
    tracker_id = request.GET.get('tracker_id')
    days = int(request.GET.get('days', 30))
    
    if tracker_id:
        tracker = get_object_or_404(
            TrackerDefinition,
            tracker_id=tracker_id,
            user=request.user
        )
    
    if chart_type == 'completion':
        # Daily completion rates
        stats = analytics.compute_completion_rate(tracker_id) if tracker_id else {}
        return JsonResponse({
            'success': True,
            'chart_type': 'line',
            'data': {
                'labels': [],  # Dates
                'datasets': [{
                    'label': 'Completion Rate',
                    'data': [],
                    'borderColor': 'rgb(99, 102, 241)',
                    'tension': 0.3
                }]
            },
            'raw': stats
        })
    
    elif chart_type == 'pie':
        # Category distribution
        stats = analytics.compute_balance_score(tracker_id) if tracker_id else {}
        categories = stats.get('category_distribution', {})
        return JsonResponse({
            'success': True,
            'chart_type': 'pie',
            'data': {
                'labels': list(categories.keys()),
                'datasets': [{
                    'data': list(categories.values()),
                    'backgroundColor': [
                        'rgb(99, 102, 241)',
                        'rgb(34, 197, 94)',
                        'rgb(249, 115, 22)',
                        'rgb(236, 72, 153)',
                        'rgb(14, 165, 233)'
                    ]
                }]
            }
        })
    
    elif chart_type == 'bar':
        # Weekly task counts
        data = []
        labels = []
        today = date.today()
        for i in range(7):
            day = today - timedelta(days=6-i)
            labels.append(day.strftime('%a'))
            
            day_count = 0
            if tracker_id:
                instances = TaskInstance.objects.filter(
                    tracker_instance__tracker__tracker_id=tracker_id,
                    tracker_instance__tracking_date=day,
                    status='DONE'
                ).count()
                day_count = instances
            else:
                instances = TaskInstance.objects.filter(
                    tracker_instance__tracker__user=request.user,
                    tracker_instance__tracking_date=day,
                    status='DONE'
                ).count()
                day_count = instances
            data.append(day_count)
        
        return JsonResponse({
            'success': True,
            'chart_type': 'bar',
            'data': {
                'labels': labels,
                'datasets': [{
                    'label': 'Tasks Completed',
                    'data': data,
                    'backgroundColor': 'rgba(99, 102, 241, 0.8)'
                }]
            }
        })
        
    return JsonResponse({
        'success': False,
        'error': 'Invalid chart type'
    }, status=400)


# ============================================================================
# HEATMAP DATA API ENDPOINT
# ============================================================================

@require_auth
@require_GET
def api_heatmap_data(request):
    """
    Get heatmap data for completion visualization.
    
    GET /api/heatmap/?tracker_id=xxx&weeks=12
    
    Returns: Grid of completion levels (0-4) for GitHub-style heatmap
    """
    from django.core.cache import cache
    
    try:
        tracker_id = request.GET.get('tracker_id')
        weeks = int(request.GET.get('weeks', 12))
        
        # Create cache key based on user, tracker, and weeks
        cache_key = f"heatmap:{request.user.id}:{tracker_id or 'all'}:{weeks}:{date.today().isoformat()}"
        
        # Try to get cached data
        cached_data = cache.get(cache_key)
        if cached_data:
            return JsonResponse(cached_data)
        
        today = date.today()
        
        # Build grid: 7 rows (days) x N columns (weeks)
        heatmap_data = []
        
        # Start from Sunday
        days_since_sunday = (today.weekday() + 1) % 7
        start_date = today - timedelta(days=(weeks * 7) + days_since_sunday)
        
        # Import TaskInstance for task-based completion
        from .models import TaskInstance
        
        # Fetch all task instances in the date range at once (optimized query)
        base_query = TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            tracker_instance__period_start__gte=start_date,
            tracker_instance__period_end__lte=today
        ).select_related('tracker_instance')
        
        if tracker_id:
            base_query = base_query.filter(tracker_instance__tracker__tracker_id=tracker_id)
        
        # Aggregate by date for performance
        from django.db.models import Count, Q
        from django.db.models.functions import TruncDate
        
        # Get daily aggregates
        daily_stats = base_query.annotate(
            tracking_day=TruncDate('tracker_instance__period_start')
        ).values('tracking_day').annotate(
            total=Count('task_instance_id'),
            done=Count('task_instance_id', filter=Q(status='DONE'))
        ).order_by('tracking_day')
        
        # Convert to dict for fast lookup
        stats_by_date = {
            item['tracking_day']: {'total': item['total'], 'done': item['done']}
            for item in daily_stats
        }
        
        current_date = start_date
        for week in range(weeks + 1):
            week_data = []
            for day in range(7):
                if current_date > today:
                    week_data.append({'date': None, 'level': 0, 'count': 0})
                else:
                    stats = stats_by_date.get(current_date, {'total': 0, 'done': 0})
                    done = stats['done']
                    total = stats['total']
                    rate = (done / total * 100) if total else 0
                    
                    # Determine level (0-4) for GitHub-style heatmap
                    if total == 0:
                        level = 0
                    elif rate == 0:
                        level = 0
                    elif rate < 25:
                        level = 1
                    elif rate < 50:
                        level = 2
                    elif rate < 75:
                        level = 3
                    else:
                        level = 4
                    
                    week_data.append({
                        'date': current_date.isoformat(),
                        'level': level,
                        'count': done,
                        'total': total,
                        'rate': int(rate)
                    })
                
                current_date += timedelta(days=1)
            
            heatmap_data.append(week_data)
        
        response_data = {
            'success': True,
            'heatmap': heatmap_data,
            'weeks': weeks
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, response_data, 300)
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# BULK STATUS UPDATE (Moved from views.py)
# ============================================================================

@require_auth
@require_POST
def api_bulk_status_update(request):
    """
    Bulk update task statuses by date range and tracker.
    """
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        # Determine the new status based on action
        status_map = {
            'mark_missed': 'MISSED',
            'mark_done': 'DONE',
            'mark_skipped': 'SKIPPED',
            'mark_pending': 'TODO'
        }
        status = status_map.get(action, 'MISSED')
        
        filters = {
            'tracker_id': data.get('tracker_id'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'current_statuses': data.get('filter_status', ['TODO', 'IN_PROGRESS'])
        }
        
        # Service Call
        updated = task_service.bulk_update_by_filter(request.user, status, filters)
        
        return JsonResponse({
            'success': True,
            'updated': updated,
            'message': f'{updated} tasks updated to {status}'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_auth
@require_POST
def api_mark_overdue_missed(request, tracker_id):
    """
    Automatically mark all overdue TODO tasks as MISSED.
    """
    try:
        today = date.today()
        # Service Call
        marked = task_service.mark_overdue_as_missed(tracker_id, today)
        
        return JsonResponse({
            'success': True,
            'marked_count': marked,
            'message': f'{marked} overdue tasks marked as MISSED'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================================
# GOALS API
# ============================================================================

@require_auth
@require_http_methods(['GET', 'POST'])
def api_goals(request):
    """
    Goals API endpoint with pagination support
    
    GET params:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        status: Filter by status ('active', 'completed', 'archived')
        sort: Sort order ('created', '-created', 'priority', 'progress')
    
    Returns:
        Paginated goals list with metadata
    """
    from .models import Goal
    from django.core.paginator import Paginator, EmptyPage
    
    if request.method == 'GET':
        # Get query parameters
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 100)  # Max 100
        status_filter = request.GET.get('status', 'all')
        sort_order = request.GET.get('sort', '-created_at')
        
        # Build query
        goals_query = Goal.objects.filter(user=request.user, deleted_at__isnull=True)
        
        # Apply status filter
        if status_filter != 'all':
            goals_query = goals_query.filter(status=status_filter)
        
        # Apply sorting
        valid_sorts = ['created_at', '-created_at', 'priority', '-priority', 'progress', '-progress', 'target_date']
        if sort_order in valid_sorts:
            goals_query = goals_query.order_by(sort_order)
        else:
            goals_query = goals_query.order_by('-created_at')
        
        # Paginate
        paginator = Paginator(goals_query, per_page)
        
        try:
            page_obj = paginator.get_page(page)
        except EmptyPage:
            return JsonResponse({
                'success': True,
                'goals': [],
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': False,
                    'has_previous': False
                }
            })
        
        # Serialize goals
        goals_data = []
        for goal in page_obj:
            goals_data.append({
                'goal_id': goal.goal_id,
                'title': goal.title,
                'description': goal.description,
                'icon': goal.icon,
                'goal_type': goal.goal_type,
                'target_date': goal.target_date.isoformat() if goal.target_date else None,
                'target_value': goal.target_value,
                'current_value': goal.current_value,
                'unit': goal.unit,
                'status': goal.status,
                'priority': goal.priority,
                'progress': goal.progress,
                'created_at': goal.created_at.isoformat() if hasattr(goal, 'created_at') else None
            })
        
        return JsonResponse({
            'success': True,
            'goals': goals_data,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page + 1 if page_obj.has_next() else None,
                'previous_page': page - 1 if page_obj.has_previous() else None,
                'per_page': per_page
            }
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            goal_type = data.get('goal_type') or data.get('type', 'habit')
            goal = Goal.objects.create(
                user=request.user,
                title=data.get('title', ''),
                description=data.get('description', ''),
                icon=data.get('icon', '🎯'),
                goal_type=goal_type,
                target_date=data.get('target_date') or None,
                target_value=data.get('target_value'),
                unit=data.get('unit', ''),
                status='active',
            )
            return JsonResponse({
                'success': True, 
                'goal_id': goal.goal_id,
                'message': 'Goal created successfully',
                'refresh': True
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================================
# USER PREFERENCES API
# ============================================================================

@require_auth
@require_http_methods(['GET', 'PUT'])
def api_preferences(request):
    """User preferences API endpoint"""
    from .models import UserPreferences
    
    prefs, created = UserPreferences.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'preferences': {
                'theme': prefs.theme,
                'default_view': prefs.default_view,
                'timezone': prefs.timezone,
                'date_format': prefs.date_format,
                'week_start': prefs.week_start,
                'daily_reminder_enabled': prefs.daily_reminder_enabled,
                'sound_complete': prefs.sound_complete,
                'sound_notify': prefs.sound_notify,
                'sound_volume': prefs.sound_volume,
                'compact_mode': prefs.compact_mode,
                'animations': prefs.animations,
                'keyboard_enabled': prefs.keyboard_enabled,
                'push_enabled': prefs.push_enabled,
            }
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Update only provided fields
            fields = ['theme', 'default_view', 'timezone', 'date_format', 'week_start',
                     'daily_reminder_enabled', 'sound_complete', 'sound_notify', 
                     'sound_volume', 'compact_mode', 'animations', 'keyboard_enabled', 'push_enabled']
            
            for field in fields:
                if field in data:
                    setattr(prefs, field, data[field])
            
            prefs.save()
            return JsonResponse({'success': True, 'message': 'Preferences updated'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================================
# NOTIFICATIONS API
# ============================================================================

@require_auth
@require_http_methods(['GET', 'POST'])
def api_notifications(request):
    """
    Notifications API endpoint with pagination
    
    GET params:
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
        unread_only: Filter to unread only (default: false)
    """
    from .models import Notification
    from django.core.paginator import Paginator, EmptyPage
    
    if request.method == 'GET':
        # Get pagination params
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 100)
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
        
        # Build query
        query = Notification.objects.filter(user=request.user).order_by('-created_at')
        
        if unread_only:
            query = query.filter(is_read=False)
        
        # Get counts before pagination
        total_count = query.count()
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        # Paginate
        paginator = Paginator(query, per_page)
        
        try:
            page_obj = paginator.get_page(page)
        except EmptyPage:
            return JsonResponse({
                'success': True,
                'notifications': [],
                'unread_count': unread_count,
                'pagination': {
                    'current_page': page,
                    'total_pages': paginator.num_pages,
                    'total_count': total_count,
                    'has_next': False,
                    'has_previous': False,
                    'per_page': per_page
                }
            })
        
        # Serialize notifications
        notifications_data = [{
            'notification_id': n.notification_id,
            'type': n.type,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat() if n.created_at else None
        } for n in page_obj]
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': unread_count,
            'pagination': {
                'current_page': page,
                'total_pages': paginator.num_pages,
                'total_count': total_count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page': page + 1 if page_obj.has_next() else None,
                'previous_page': page - 1 if page_obj.has_previous() else None,
                'per_page': per_page
            }
        })
    
    elif request.method == 'POST':
        # Mark notifications as read
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'mark_read':
                notification_ids = data.get('ids', [])
                Notification.objects.filter(
                    user=request.user,
                    notification_id__in=notification_ids
                ).update(is_read=True)
                return JsonResponse({'success': True, 'message': 'Marked as read'})
            
            elif action == 'mark_all_read':
                Notification.objects.filter(user=request.user).update(is_read=True)
                return JsonResponse({'success': True, 'message': 'All marked as read'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)



# ============================================================================
# PREFETCH API - For SPA navigation (Phase 3)
# ============================================================================

@require_auth
@require_GET
@check_etag
def api_prefetch(request):
    """
    Prefetch data for likely next navigations.
    Used by SPA to preload adjacent panel data for instant navigation.
    
    Query params:
        panels: comma-separated list of panels to prefetch
        
    Example: /api/prefetch/?panels=today,dashboard
    """
    from django.utils import timezone as dj_timezone
    
    panels = request.GET.get('panels', 'today,dashboard').split(',')
    today = date.today()
    user = request.user
    
    prefetch_data = {}
    
    for panel in panels:
        panel = panel.strip()
        
        if panel == 'today':
            # Prefetch today's task count for quick display
            today_tasks = TaskInstance.objects.filter(
                tracker_instance__tracker__user=user,
                tracker_instance__period_start__lte=today,
                tracker_instance__period_end__gte=today
            )
            prefetch_data['today'] = {
                'total_count': today_tasks.count(),
                'done_count': today_tasks.filter(status='DONE').count(),
                'pending_count': today_tasks.filter(status__in=['TODO', 'IN_PROGRESS']).count()
            }
            
        elif panel == 'dashboard':
            # Prefetch active trackers count
            active_trackers = TrackerDefinition.objects.filter(user=user, status='active')
            prefetch_data['dashboard'] = {
                'tracker_count': active_trackers.count(),
                'has_tasks_today': TaskInstance.objects.filter(
                    tracker_instance__tracker__user=user,
                    tracker_instance__period_start__lte=today,
                    tracker_instance__period_end__gte=today
                ).exists()
            }
            
        elif panel == 'week':
            # Prefetch week summary
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            week_tasks = TaskInstance.objects.filter(
                tracker_instance__tracker__user=user,
                tracker_instance__period_start__gte=start_of_week,
                tracker_instance__period_end__lte=end_of_week
            )
            prefetch_data['week'] = {
                'total': week_tasks.count(),
                'done': week_tasks.filter(status='DONE').count()
            }
    
    return JsonResponse({
        'success': True,
        'data': prefetch_data,
        'timestamp': dj_timezone.now().isoformat()
    })


# ============================================================================
# INFINITE SCROLL API - For task lists (Phase 3)
# ============================================================================

@require_auth
@require_GET
@check_etag
def api_tasks_infinite(request):
    """
    Cursor-based paginated task list for infinite scroll.
    
    Query params:
        cursor: ISO datetime cursor from previous page
        limit: number of items per page (default: 20, max: 100)
        tracker_id: optional filter by tracker
        status: optional filter by status
        period: 'today', 'week', 'month', 'all'
    """
    from .utils.pagination_helpers import CursorPaginator, paginated_response
    
    cursor = request.GET.get('cursor')
    limit = min(int(request.GET.get('limit', 20)), 100)
    tracker_id = request.GET.get('tracker_id')
    status_filter = request.GET.get('status')
    period = request.GET.get('period', 'today')
    
    today = date.today()
    
    # Build base queryset
    queryset = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user,
        deleted_at__isnull=True
    ).select_related('template', 'tracker_instance__tracker')
    
    # Apply period filter
    if period == 'today':
        queryset = queryset.filter(
            tracker_instance__period_start__lte=today,
            tracker_instance__period_end__gte=today
        )
    elif period == 'week':
        start = today - timedelta(days=today.weekday())
        queryset = queryset.filter(
            tracker_instance__period_start__gte=start
        )
    elif period == 'month':
        start = today.replace(day=1)
        queryset = queryset.filter(
            tracker_instance__period_start__gte=start
        )
    
    # Apply optional filters
    if tracker_id:
        queryset = queryset.filter(tracker_instance__tracker__tracker_id=tracker_id)
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Order by creation time (newest first)
    queryset = queryset.order_by('-created_at')
    
    # Cursor pagination
    paginator = CursorPaginator(queryset, cursor_field='created_at', page_size=limit)
    result = paginator.paginate(cursor=cursor)
    
    # Serialize tasks
    def serialize_task(task):
        return {
            'id': task.task_instance_id,
            'description': task.template.description,
            'status': task.status,
            'category': task.template.category,
            'weight': task.template.weight,
            'time_of_day': task.template.time_of_day,
            'tracker_name': task.tracker_instance.tracker.name,
            'tracker_id': str(task.tracker_instance.tracker.tracker_id),
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        }
    
    return paginated_response(
        items=result['items'],
        serializer_func=serialize_task,
        has_more=result['pagination']['has_more'],
        next_cursor=result['pagination']['next_cursor'],
        meta={'period': period, 'limit': limit}
    )


# ============================================================================
# SMART SUGGESTIONS API (Phase 5)
# ============================================================================

@require_auth
@require_GET
def api_smart_suggestions(request):
    """
    Get smart suggestions based on user behavior.
    Returns insights like "You perform best on Mondays" or "Your optimal task time is morning".
    """
    from django.db.models import Count
    from django.db.models.functions import ExtractWeekDay, ExtractHour
    
    user = request.user
    today = date.today()
    
    suggestions = []
    
    # Analyze completion by day of week
    try:
        # Get completed tasks by day of week (1=Sunday, 7=Saturday in Django)
        day_stats = TaskInstance.objects.filter(
            tracker_instance__tracker__user=user,
            status='DONE',
            completed_at__isnull=False
        ).annotate(
            weekday=ExtractWeekDay('completed_at')
        ).values('weekday').annotate(
            count=Count('task_instance_id')
        ).order_by('-count')[:2]
        
        day_names = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 
                     5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
        
        if day_stats:
            best_day = day_stats[0]
            suggestions.append({
                'type': 'best_day',
                'icon': '📅',
                'message': f"You're most productive on {day_names.get(best_day['weekday'], 'Unknown')}s",
                'detail': f"{best_day['count']} tasks completed",
                'action': None
            })
    except Exception:
        pass
    
    # Analyze completion by time of day
    try:
        time_stats = TaskInstance.objects.filter(
            tracker_instance__tracker__user=user,
            status='DONE'
        ).values('template__time_of_day').annotate(
            count=Count('task_instance_id')
        ).order_by('-count')[:1]
        
        if time_stats:
            best_time = time_stats[0]
            time_name = best_time['template__time_of_day'] or 'anytime'
            suggestions.append({
                'type': 'best_time',
                'icon': '⏰',
                'message': f"Your optimal task time is {time_name}",
                'detail': f"{best_time['count']} tasks completed during this period",
                'action': None
            })
    except Exception:
        pass
    
    # Current streak
    try:
        from core import analytics
        streak = analytics.compute_user_streak(user) if hasattr(analytics, 'compute_user_streak') else 0
        if streak > 0:
            suggestions.append({
                'type': 'streak',
                'icon': '🔥',
                'message': f"You're on a {streak}-day streak!",
                'detail': "Keep it going",
                'action': {'label': 'View Stats', 'url': '/analytics/'}
            })
    except Exception:
        pass
    
    # Pending tasks reminder
    pending_count = TaskInstance.objects.filter(
        tracker_instance__tracker__user=user,
        tracker_instance__period_start__lte=today,
        tracker_instance__period_end__gte=today,
        status__in=['TODO', 'IN_PROGRESS']
    ).count()
    
    if pending_count > 0:
        suggestions.append({
            'type': 'pending',
            'icon': '📋',
            'message': f"{pending_count} tasks waiting for you today",
            'detail': None,
            'action': {'label': 'View Tasks', 'url': '/today/'}
        })
    
    return JsonResponse({
        'success': True,
        'suggestions': suggestions,
        'generated_at': timezone.now().isoformat()
    })


# ============================================================================
# SYNC ENDPOINT (Offline-First Support)
# ============================================================================

@require_auth
@require_POST
def api_sync(request):
    """
    Bidirectional sync endpoint for offline-first mobile apps.
    
    Accepts queued offline actions and returns server changes.
    Supports conflict detection and resolution.
    
    Request body:
        {
            'last_sync': ISO timestamp (optional, null for full sync),
            'pending_actions': [...],  # Queued offline actions
            'device_id': string        # Device identifier
        }
    
    Response:
        {
            'action_results': [...],   # Result per action
            'server_changes': {...},   # Changes since last sync
            'new_sync_timestamp': ISO timestamp,
            'sync_status': 'complete' or 'partial'
        }
    """
    from core.services.sync_service import SyncService
    
    try:
        data = json.loads(request.body)
        sync_service = SyncService(request.user)
        result = sync_service.process_sync_request(data)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'sync_status': 'failed',
            'error': 'Invalid JSON in request body',
            'retry_after': 0
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'sync_status': 'failed',
            'error': str(e),
            'retry_after': 5  # Seconds to wait before retry
        }, status=500)


# ============================================================================
# HEALTH CHECK ENDPOINT (Load Balancer Integration)
# ============================================================================

@require_GET
def api_health(request):
    """
    Health check endpoint for load balancers and monitoring.
    
    GET /api/health/
    
    Returns 200 if healthy, 503 if unhealthy.
    Does not require authentication.
    """
    from django.db import connection
    from django.conf import settings
    import time
    
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': getattr(settings, 'APP_VERSION', '1.0.0'),
        'checks': {}
    }
    
    # Database check
    db_start = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['checks']['database'] = {
            'status': 'ok',
            'latency_ms': round((time.time() - db_start) * 1000, 2)
        }
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # Cache check (optional, if enabled)
    try:
        from django.core.cache import cache
        cache_start = time.time()
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check')
        if cache_result == 'ok':
            health_status['checks']['cache'] = {
                'status': 'ok',
                'latency_ms': round((time.time() - cache_start) * 1000, 2)
            }
        else:
            health_status['checks']['cache'] = {'status': 'degraded'}
    except Exception:
        health_status['checks']['cache'] = {'status': 'unavailable'}
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return JsonResponse(health_status, status=status_code)


# ============================================================================
# USER PROFILE \u0026 SETTINGS ENDPOINTS (for both Web and iOS)
# ============================================================================

@require_auth
@require_http_methods(['GET', 'PUT'])
def api_user_profile(request):
    """
    Get or update user profile information.
    Used by both web frontend and iOS app.
    
    GET /api/v1/user/profile/
    PUT /api/v1/user/profile/
    
    PUT Body:
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "timezone": "Asia/Kolkata",
            "date_format": "DD/MM/YYYY",
            "week_start": 1
        }
    """
    from .models import UserPreferences
    
    if request.method == 'GET':
        # Get current profile
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
        
        return JsonResponse({
            'success': True,
            'profile': {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'username': request.user.username,
                'timezone': prefs.timezone,
                'date_format': prefs.date_format,
                'week_start': prefs.week_start,
            }
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Update User model fields
            if 'first_name' in data:
                request.user.first_name = data['first_name']
            if 'last_name' in data:
                request.user.last_name = data['last_name']
            if 'email' in data:
                # Validate email is not already taken by another user
                from django.contrib.auth.models import User
                email = data['email']
                if User.objects.filter(email=email).exclude(id=request.user.id).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Email already in use by another account'
                    }, status=400)
                request.user.email = email
            
            request.user.save()
            
            # Update UserPreferences fields
            prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
            if 'timezone' in data:
                prefs.timezone = data['timezone']
            if 'date_format' in data:
                prefs.date_format = data['date_format']
            if 'week_start' in data:
                prefs.week_start = int(data['week_start'])
            
            prefs.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully',
                'profile': {
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'email': request.user.email,
                    'timezone': prefs.timezone,
                    'date_format': prefs.date_format,
                    'week_start': prefs.week_start,
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@require_auth
@require_http_methods(['POST', 'DELETE'])
def api_user_avatar(request):
    """
    Upload or remove user avatar.
    
    POST /api/v1/user/avatar/ - Upload avatar (multipart/form-data with 'avatar' file)
    DELETE /api/v1/user/avatar/ - Remove avatar
    
    Returns avatar URL in response for immediate UI update.
    """
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import os
    from PIL import Image
    from io import BytesIO
    
    if request.method == 'POST':
        try:
            # Check if file exists in request
            if 'avatar' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No avatar file provided'
                }, status=400)
            
            avatar_file = request.FILES['avatar']
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if avatar_file.content_type not in allowed_types:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid file type. Only JPEG, PNG, GIF, and WebP are allowed.'
                }, status=400)
            
            # Validate file size (max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if avatar_file.size > max_size:
                return JsonResponse({
                    'success': False,
                    'error': 'File too large. Maximum size is 5MB.'
                }, status=400)
            
            # Process and resize image
            try:
                img = Image.open(avatar_file)
                
                # Convert to RGB if needed (for JPEG)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Resize to 400x400 (square)
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                
                # Save to BytesIO
                output = BytesIO()
                img.save(output, format='JPEG', quality=90)
                output.seek(0)
                
                # Generate filename
                file_ext = 'jpg'
                filename = f'avatars/user_{request.user.id}.{file_ext}'
                
                # Delete old avatar if exists
                if default_storage.exists(filename):
                    default_storage.delete(filename)
                
                # Save new avatar
                path = default_storage.save(filename, ContentFile(output.read()))
                avatar_url = default_storage.url(path)
                
                # Update user model if it has avatar field, or use preferences
                # For now, we'll store in session/preferences
                from .models import UserPreferences
                prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
                # Note: UserPreferences doesn't have avatar_url field in current model
                # You may need to add this field to the model or use a different approach
                # For now, returning the URL for frontend to handle
                
                return JsonResponse({
                    'success': True,
                    'message': 'Avatar uploaded successfully',
                    'avatar_url': avatar_url
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error processing image: {str(e)}'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    elif request.method == 'DELETE':
        try:
            # Delete avatar file
            filename = f'avatars/user_{request.user.id}.jpg'
            if default_storage.exists(filename):
                default_storage.delete(filename)
            
            return JsonResponse({
                'success': True,
                'message': 'Avatar removed successfully',
                'avatar_url': '/static/core/images/default-avatar.svg'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@require_auth
@require_POST
def api_data_export(request):
    """
    Export user data in JSON or CSV format.
    
    POST /api/v1/data/export/
    Body: {"format": "json"|"csv"}
    
    Returns JSON with download_url or direct file data.
    """
    try:
        data = json.loads(request.body)
        export_format = data.get('format', 'json').lower()
        
        if export_format not in ['json', 'csv']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid format. Use "json" or "csv".'
            }, status=400)
        
        # Gather user data
        user_data = {
            'export_date': timezone.now().isoformat(),
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            },
            'trackers': [],
            'preferences': {}
        }
        
        # Get all trackers
        trackers = TrackerDefinition.objects.filter(user=request.user, deleted_at__isnull=True)
        for tracker in trackers:
            tracker_data = {
                'tracker_id': tracker.tracker_id,
                'name': tracker.name,
                'description': tracker.description,
                'time_mode': tracker.time_mode,
                'status': tracker.status,
                'created_at': tracker.created_at.isoformat(),
                'tasks': []
            }
            
            # Get task templates
            templates = TaskTemplate.objects.filter(tracker=tracker, deleted_at__isnull=True)
            for template in templates:
                tracker_data['tasks'].append({
                    'template_id': template.template_id,
                    'description': template.description,
                    'category': template.category,
                    'weight': template.weight,
                    'time_of_day': template.time_of_day,
                })
            
            user_data['trackers'].append(tracker_data)
        
        # Get preferences
        from .models import UserPreferences
        try:
            prefs = UserPreferences.objects.get(user=request.user)
            user_data['preferences'] = {
                'theme': prefs.theme,
                'timezone': prefs.timezone,
                'date_format': prefs.date_format,
                'week_start': prefs.week_start,
                'default_view': prefs.default_view,
                'compact_mode': prefs.compact_mode,
                'animations': prefs.animations,
            }
        except UserPreferences.DoesNotExist:
            pass
        
        if export_format == 'json':
            # Return JSON data directly for download
            response = JsonResponse(user_data, json_dumps_params={'indent': 2})
            response['Content-Disposition'] = f'attachment; filename="tracker_export_{timezone.now().strftime("%Y%m%d")}.json"'
            return response
        
        else:  # CSV format
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write trackers and tasks
            writer.writerow(['Type', 'Tracker Name', 'Task Description', 'Category', 'Time Mode', 'Status'])
            for tracker in user_data['trackers']:
                for task in tracker['tasks']:
                    writer.writerow([
                        'Task',
                        tracker['name'],
                        task['description'],
                        task['category'],
                        tracker['time_mode'],
                        tracker['status']
                    ])
            
            from django.http import HttpResponse
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="tracker_export_{timezone.now().strftime("%Y%m%d")}.csv"'
            return response
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_POST
def api_data_import(request):
    """
    Import user data from JSON file.
    
    POST /api/v1/data/import/
    Body: multipart/form-data with 'file' field containing JSON export
    
    Returns count of imported trackers and tasks.
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No file provided'
            }, status=400)
        
        import_file = request.FILES['file']
        
        # Validate file type
        if not import_file.name.endswith('.json'):
            return JsonResponse({
                'success': False,
                'error': 'Only JSON files are supported'
            }, status=400)
        
        # Parse JSON
        try:
            import_data = json.loads(import_file.read().decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON file'
            }, status=400)
        
        # Validate structure
        if 'trackers' not in import_data:
            return JsonResponse({
                'success': False,
                'error': 'Invalid export format: missing trackers data'
            }, status=400)
        
        # Import trackers and tasks
        imported_trackers = 0
        imported_tasks = 0
        
        for tracker_data in import_data['trackers']:
            # Create tracker (with new UUID to avoid conflicts)
            tracker = TrackerDefinition.objects.create(
                user=request.user,
                name=tracker_data['name'],
                description=tracker_data.get('description', ''),
                time_mode=tracker_data.get('time_mode', 'daily'),
                status='active'  # Import as active
            )
            imported_trackers += 1
            
            # Create task templates
            for task_data in tracker_data.get('tasks', []):
                TaskTemplate.objects.create(
                    tracker=tracker,
                    description=task_data['description'],
                    category=task_data.get('category', ''),
                    weight=task_data.get('weight', 1),
                    time_of_day=task_data.get('time_of_day', 'anytime')
                )
                imported_tasks += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Imported {imported_trackers} trackers with {imported_tasks} tasks',
            'imported_trackers': imported_trackers,
            'imported_tasks': imported_tasks
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_POST
def api_data_clear(request):
    """
    Clear all user data (trackers, tasks, goals, etc.).
    Requires confirmation string to prevent accidental deletion.
    
    POST /api/v1/data/clear/
    Body: {"confirmation": "DELETE ALL DATA"}
    
    This is a DESTRUCTIVE operation. Use with extreme caution.
    """
    try:
        data = json.loads(request.body)
        confirmation = data.get('confirmation', '')
        
        if confirmation != 'DELETE ALL DATA':
            return JsonResponse({
                'success': False,
                'error': 'Invalid confirmation. Please type "DELETE ALL DATA" to confirm.'
            }, status=400)
        
        # Soft delete all user data
        from .models import Goal
        
        deleted_counts = {}
        
        # Soft delete trackers (cascades to instances and tasks via Django ORM)
        trackers = TrackerDefinition.objects.filter(user=request.user, deleted_at__isnull=True)
        deleted_counts['trackers'] = trackers.count()
        for tracker in trackers:
            tracker.soft_delete()
        
        # Soft delete goals
        goals = Goal.objects.filter(user=request.user, deleted_at__isnull=True)
        deleted_counts['goals'] = goals.count()
        for goal in goals:
            goal.soft_delete()
        
        return JsonResponse({
            'success': True,
            'message': 'All data cleared successfully',
            'deleted_counts': deleted_counts
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_http_methods(['DELETE'])
def api_user_delete(request):
    """
    Permanently delete user account and all associated data.
    Requires password confirmation to prevent accidental deletion.
    
    DELETE /api/v1/user/delete/
    Body: {"confirmation": "DELETE MY ACCOUNT", "password": "user_password"}
    
    This is an IRREVERSIBLE operation.
    """
    try:
        data = json.loads(request.body)
        confirmation = data.get('confirmation', '')
        password = data.get('password', '')
        
        if confirmation != 'DELETE MY ACCOUNT':
            return JsonResponse({
                'success': False,
                'error': 'Invalid confirmation. Please type "DELETE MY ACCOUNT" to confirm.'
            }, status=400)
        
        # Verify password
        from django.contrib.auth import authenticate
        user = authenticate(username=request.user.username, password=password)
        if user is None:
            return JsonResponse({
                'success': False,
                'error': 'Incorrect password'
            }, status=401)
        
        # Hard delete all user data (not soft delete, permanent)
        username = request.user.username
        
        # Delete user (cascades to all related data via ON_DELETE CASCADE)
        request.user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Account {username} permanently deleted',
            'redirect': '/logout/'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# ANALYTICS & EXPORT APIs
# =============================================================================

@require_auth
@require_http_methods(['GET'])
def api_analytics_data(request):
    """
    Get analytics data for charts dashboard
    
    Query params:
        days: number of days of data (default: 30)
        tracker_id: optional tracker UUID to filter
    
    Returns:
        {
            'success': true,
            'data': {
                'completion_trend': {...},
                'category_distribution': {...},
                'time_of_day': {...},
                'heatmap': [...],
                'insights': [...],
                'summary': {...}
            }
        }
    """
    from core.services.analytics_service import AnalyticsService
    
    try:
        days = int(request.GET.get('days', 30))
        tracker_id = request.GET.get('tracker_id', None)
        
        # Validate days range
        if days < 1 or days > 365:
            return JsonResponse({
                'success': False,
                'error': 'Days must be between 1 and 365'
            }, status=400)
        
        # Initialize service
        service = AnalyticsService(tracker_id=tracker_id, user=request.user)
        
        # Get all analytics data
        analytics_data = service.get_analytics_data(days=days)
        
        return JsonResponse({
            'success': True,
            'data': analytics_data,
            'days': days
        })
        
    except PermissionError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=403)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_http_methods(['POST'])
def api_export_month(request):
    """
    Export data for a specific month
    
    Body:
        {
            "year": 2024,
            "month": 12,
            "format": "json"|"csv"|"xlsx",
            "tracker_id": "optional-uuid"
        }
    
    Returns:
        File download (JSON/CSV/Excel)
    """
    from core.services.export_service import ExportService
    
    try:
        data = json.loads(request.body)
        
        year = data.get('year')
        month = data.get('month')
        format = data.get('format', 'json')
        tracker_id = data.get('tracker_id', None)
        
        # Validate inputs
        if not year or not month:
            return JsonResponse({
                'success': False,
                'error': 'Year and month are required'
            }, status=400)
        
        if not isinstance(year, int) or not isinstance(month, int):
            return JsonResponse({
                'success': False,
                'error': 'Year and month must be integers'
            }, status=400)
        
        if month < 1 or month > 12:
            return JsonResponse({
                'success': False,
                'error': 'Month must be between 1 and 12'
            }, status=400)
        
        if format not in ['json', 'csv', 'xlsx']:
            return JsonResponse({
                'success': False,
                'error': 'Format must be json, csv, or xlsx'
            }, status=400)
        
        # Initialize service and export
        service = ExportService(user=request.user)
        response = service.export_month(year, month, format, tracker_id)
        
        return response
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_http_methods(['GET'])
def api_analytics_forecast(request):
    """
    Get completion rate forecast using statistical analysis
    
    Query params:
        days: number of days to forecast (default: 7, max: 30)
        history_days: historical data to analyze (default: 30)
        tracker_id: optional tracker UUID to filter
    
    Returns:
        {
            'success': true,
            'forecast': {
                'predictions': [85.2, 86.1, ...],
                'upper_bound': [90.5, 91.2, ...],
                'lower_bound': [79.9, 81.0, ...],
                'confidence': 0.85,
                'trend': 'increasing',
                'dates': [...],
                'labels': [...]
            },
            'summary': {
                'message': '...',
                'recommendation': '...',
                'predicted_change': +5.2
            }
        }
    """
    from core.services.forecast_service import ForecastService
    
    try:
        days = int(request.GET.get('days', 7))
        history_days = int(request.GET.get('history_days', 30))
        tracker_id = request.GET.get('tracker_id', None)
        
        # Validate inputs
        if days < 1 or days > 30:
            return JsonResponse({
                'success': False,
                'error': 'Days must be between 1 and 30'
            }, status=400)
        
        if history_days < 7 or history_days > 365:
            return JsonResponse({
                'success': False,
                'error': 'History days must be between 7 and 365'
            }, status=400)
        
        # Initialize service
        service = ForecastService(user=request.user)
        
        # Get forecast
        forecast = service.forecast_completion_rate(
            days_ahead=days,
            history_days=history_days,
            tracker_id=tracker_id
        )
        
        if not forecast['success']:
            # Return user-friendly response for new users with insufficient data
            return JsonResponse({
                'success': True,  # Still success, but with empty forecast
                'forecast': {
                    'predictions': [],
                    'dates': [],
                    'labels': [],
                    'confidence': 0,
                    'trend': 'insufficient_data'
                },
                'summary': {
                    'message': 'Not enough data for forecasting yet',
                    'recommendation': 'Complete more tasks over the next few days to unlock predictions!',
                    'predicted_change': 0
                },
                'reason': forecast.get('error', 'Insufficient historical data'),
                'suggestions': [
                    'Complete at least 7 days of task tracking',
                    'Add more tasks to your trackers',
                    'Stay consistent with daily task completion'
                ]
            })
        
        # Get summary
        summary = service.get_forecast_summary(days_ahead=days)
        
        return JsonResponse({
            'success': True,
            'forecast': forecast,
            'summary': summary
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# UNDO SYSTEM
# =============================================================================

@require_auth
@require_POST
def api_undo(request):
    """
    Undo a recent destructive action
    
    Body:
        {
            "action_id": "undo_123_abc",
            "action_type": "delete_task"|"delete_goal"|"delete_tracker",
            "action_data": { "task_id": "...", ... }
        }
    
    Returns:
        {"success": true, "message": "Action undone"}
    """
    try:
        data = json.loads(request.body)
        
        action_type = data.get('action_type')
        action_data = data.get('action_data', {})
        
        if not action_type:
            return JsonResponse({
                'success': False,
                'error': 'action_type is required'
            }, status=400)
        
        # Handle different action types
        if action_type == 'delete_task':
            task_id = action_data.get('task_id')
            if not task_id:
                return JsonResponse({'success': False, 'error': 'task_id required'}, status=400)
            
            task = TaskInstance.objects.filter(
                task_instance_id=task_id,
                tracker__user=request.user
            ).first()
            
            if not task:
                return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)
            
            task.deleted_at = None
            task.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Task restored',
                'task_id': task_id
            })
        
        elif action_type == 'delete_goal':
            from .models import Goal
            
            goal_id = action_data.get('goal_id')
            if not goal_id:
                return JsonResponse({'success': False, 'error': 'goal_id required'}, status=400)
            
            goal = Goal.objects.filter(
                goal_id=goal_id,
                user=request.user
            ).first()
            
            if not goal:
                return JsonResponse({'success': False, 'error': 'Goal not found'}, status=404)
            
            goal.deleted_at = None
            goal.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Goal restored',
                'goal_id': goal_id
            })
        
        elif action_type == 'delete_tracker':
            tracker_id = action_data.get('tracker_id')
            if not tracker_id:
                return JsonResponse({'success': False, 'error': 'tracker_id required'}, status=400)
            
            tracker = TrackerDefinition.objects.filter(
                tracker_id=tracker_id,
                user=request.user
            ).first()
            
            if not tracker:
                return JsonResponse({'success': False, 'error': 'Tracker not found'}, status=404)
            
            tracker.deleted_at = None
            tracker.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Tracker restored',
                'tracker_id': tracker_id
            })
        
        else:
             return JsonResponse({
                'success': False,
                'error': f'Unsupported action_type: {action_type}'
            }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# FEATURE FLAGS
# =============================================================================

@require_auth
@require_GET
def api_feature_flag(request, flag_name):
    """
    Simple feature flag endpoint.
    Returns enabled status for requested feature flag.
    """
    # Define feature flags and their status
    FEATURE_FLAGS = {
        'behavioral_insights': True,  # Behavioral analytics and forecasting
        'export': True,               # Data export functionality
        'undo': True,                 # Undo/redo actions
        'pagination': True,           # Infinite scroll pagination
        'offline': True,              # Service worker offline support
    }
    
    enabled = FEATURE_FLAGS.get(flag_name, False)
    
    return JsonResponse({
        'enabled': enabled,
        'flag': flag_name
    })


# =============================================================================
# POINTS & GOALS API - Task Points and Tracker Goal Management
# =============================================================================

@require_auth
@require_GET
def api_tracker_progress(request, tracker_id):
    """
    Get current progress for a tracker's point-based goal.
    
    GET /api/v1/tracker/{tracker_id}/progress/
    
    Returns:
        {
            'success': true,
            'current_points': 35,
            'target_points': 50,
            'progress_percentage': 70.0,
            'goal_met': false,
            'period': 'daily',
            'period_start': '2025-12-08',
            'period_end': '2025-12-08',
            'task_breakdown': {...}
        }
    """
    from core.services.points_service import PointsCalculationService
    
    try:
        service = PointsCalculationService(tracker_id, request.user)
        progress = service.calculate_current_points()
        
        return JsonResponse({
            'success': True,
            **progress
        })
    except TrackerDefinition.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Tracker not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt  # For iOS clients
@require_auth
@require_POST
def api_toggle_task_goal(request, template_id):
    """
    Toggle whether a task's points count towards the tracker goal.
    
    POST /api/v1/task/{template_id}/toggle-goal/
    Body: {"include": true/false}
    
    Returns:
        {
            'success': true,
            'template_id': 'uuid',
            'include_in_goal': true,
            'tracker_progress': {...}  // Updated progress
        }
    """
    from core.services.points_service import toggle_task_goal_inclusion
    
    try:
        data = json.loads(request.body)
        include = data.get('include', True)
        
        result = toggle_task_goal_inclusion(template_id, request.user, include)
        
        return UXResponse.success(
            message=f"Task {'included in' if include else 'excluded from'} goal",
            data=result,
            feedback={
                'type': 'success',
                'message': 'Goal settings updated',
                'haptic': 'light',
                'toast': True
            }
        )
    except ValueError as e:
        return UXResponse.error(str(e), error_code='NOT_FOUND', status=404)
    except json.JSONDecodeError:
        return UXResponse.error('Invalid JSON', error_code='INVALID_JSON', status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_auth
@require_POST
def api_update_task_points(request, template_id):
    """
    Update the points value for a task.
    
    POST /api/v1/task/{template_id}/points/
    Body: {"points": 10}
    
    Returns:
        {
            'success': true,
            'template_id': 'uuid',
            'points': 10,
            'tracker_progress': {...}
        }
    """
    from core.services.points_service import update_task_points
    
    try:
        data = json.loads(request.body)
        points = int(data.get('points', 1))
        
        if points < 0:
            return UXResponse.error('Points must be 0 or greater', error_code='INVALID_POINTS', status=400)
        
        result = update_task_points(template_id, request.user, points)
        
        return UXResponse.success(
            message=f"Task points updated to {points}",
            data=result,
            feedback={
                'type': 'success',
                'haptic': 'light',
                'toast': True
            }
        )
    except ValueError as e:
        return UXResponse.error(str(e), error_code='NOT_FOUND', status=404)
    except json.JSONDecodeError:
        return UXResponse.error('Invalid JSON', error_code='INVALID_JSON', status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_auth
@require_http_methods(['GET', 'PUT'])
def api_tracker_goal(request, tracker_id):
    """
    Get or set the goal configuration for a tracker.
    
    GET /api/v1/tracker/{tracker_id}/goal/
    PUT /api/v1/tracker/{tracker_id}/goal/
    
    PUT Body: {
        "target_points": 50,
        "goal_period": "daily",  // 'daily', 'weekly', 'custom'
        "goal_start_day": 0      // 0=Monday, 6=Sunday (for weekly)
    }
    
    Returns:
        {
            'success': true,
            'tracker_id': 'uuid',
            'target_points': 50,
            'goal_period': 'daily',
            'progress': {...}
        }
    """
    from core.services.points_service import set_tracker_goal, PointsCalculationService
    
    try:
        tracker = TrackerDefinition.objects.get(tracker_id=tracker_id, user=request.user)
    except TrackerDefinition.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Tracker not found'
        }, status=404)
    
    if request.method == 'GET':
        # Get current goal settings and progress
        service = PointsCalculationService(tracker_id, request.user)
        progress = service.calculate_current_points()
        
        return JsonResponse({
            'success': True,
            'tracker_id': tracker_id,
            'tracker_name': tracker.name,
            'target_points': tracker.target_points,
            'goal_period': tracker.goal_period,
            'goal_start_day': tracker.goal_start_day,
            'progress': progress
        })
    
    else:  # PUT
        try:
            data = json.loads(request.body)
            
            target_points = data.get('target_points')
            goal_period = data.get('goal_period')
            goal_start_day = data.get('goal_start_day')
            
            # Update fields if provided
            if target_points is not None:
                if int(target_points) < 0:
                    return UXResponse.error('Target points must be 0 or greater', status=400)
                tracker.target_points = int(target_points)
            
            if goal_period and goal_period in ['daily', 'weekly', 'custom']:
                tracker.goal_period = goal_period
            
            if goal_start_day is not None:
                if not 0 <= int(goal_start_day) <= 6:
                    return UXResponse.error('Goal start day must be 0-6', status=400)
                tracker.goal_start_day = int(goal_start_day)
            
            tracker.save()
            
            # Calculate new progress
            service = PointsCalculationService(tracker_id, request.user)
            progress = service.calculate_current_points()
            
            return UXResponse.success(
                message='Goal settings updated',
                data={
                    'tracker_id': tracker_id,
                    'target_points': tracker.target_points,
                    'goal_period': tracker.goal_period,
                    'goal_start_day': tracker.goal_start_day,
                    'progress': progress
                },
                feedback={
                    'type': 'success',
                    'message': 'Goal updated!',
                    'haptic': 'success',
                    'toast': True
                }
            )
        except json.JSONDecodeError:
            return UXResponse.error('Invalid JSON', error_code='INVALID_JSON', status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


@require_auth
@require_GET
def api_task_points_breakdown(request, tracker_id):
    """
    Get detailed breakdown of each task's points contribution.
    
    GET /api/v1/tracker/{tracker_id}/points-breakdown/
    
    Returns:
        {
            'success': true,
            'tracker_id': 'uuid',
            'tasks': [
                {
                    'task_id': 'uuid',
                    'description': 'Exercise 30 min',
                    'points_possible': 10,
                    'points_earned': 10,
                    'include_in_goal': true,
                    'status': 'DONE',
                    'is_completed': true
                },
                ...
            ],
            'summary': {
                'total_possible': 50,
                'total_earned': 35,
                'tasks_included': 5,
                'tasks_excluded': 2
            }
        }
    """
    from core.services.points_service import PointsCalculationService
    
    try:
        service = PointsCalculationService(tracker_id, request.user)
        breakdown = service.get_task_points_breakdown()
        
        # Calculate summary
        total_possible = sum(t['points_possible'] for t in breakdown if t['include_in_goal'])
        total_earned = sum(t['points_earned'] for t in breakdown)
        tasks_included = sum(1 for t in breakdown if t['include_in_goal'])
        tasks_excluded = sum(1 for t in breakdown if not t['include_in_goal'])
        
        return JsonResponse({
            'success': True,
            'tracker_id': tracker_id,
            'tasks': breakdown,
            'summary': {
                'total_possible': total_possible,
                'total_earned': total_earned,
                'tasks_included': tasks_included,
                'tasks_excluded': tasks_excluded
            }
        })
    except TrackerDefinition.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Tracker not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# DASHBOARD API - Main Dashboard Data Endpoints
# =============================================================================

@require_auth
@require_GET
def api_dashboard(request):
    """
    Get complete dashboard data in one call.
    
    GET /api/v1/dashboard/
    
    Query params:
        date (optional): Target date in YYYY-MM-DD format
    
    Returns comprehensive dashboard data including:
    - Greeting message
    - All trackers with tasks for today
    - Today's stats (completion rate, points)
    - Active goals progress
    - Current streaks
    - Recent activity
    - Unread notifications count
    - Quick action suggestions
    """
    from core.services.dashboard_service import DashboardService
    from datetime import datetime
    
    try:
        # Parse optional date parameter
        date_str = request.GET.get('date')
        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
        
        service = DashboardService(request.user, target_date)
        dashboard_data = service.get_full_dashboard()
        
        return JsonResponse({
            'success': True,
            **dashboard_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET
def api_dashboard_trackers(request):
    """
    Get all trackers with their tasks for today (or specified date).
    
    GET /api/v1/dashboard/trackers/
    
    Query params:
        date (optional): Target date in YYYY-MM-DD format
    
    Returns list of tracker summaries with:
    - Tracker info (id, name, description)
    - Task list with status
    - Completion percentage
    - Points progress
    """
    from core.services.dashboard_service import DashboardService
    from datetime import datetime
    
    try:
        date_str = request.GET.get('date')
        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
        
        service = DashboardService(request.user, target_date)
        trackers = service.get_trackers_summary()
        
        return JsonResponse({
            'success': True,
            'date': service.target_date.isoformat(),
            'trackers': trackers,
            'count': len(trackers)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET
def api_dashboard_today(request):
    """
    Get today's aggregated stats only.
    
    GET /api/v1/dashboard/today/
    
    Returns:
    - Total tasks
    - Completed/In Progress/Todo/Missed counts
    - Completion rate
    - Points earned vs total possible
    """
    from core.services.dashboard_service import DashboardService
    
    try:
        service = DashboardService(request.user)
        stats = service.get_today_stats()
        
        return JsonResponse({
            'success': True,
            **stats
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET
def api_dashboard_week(request):
    """
    Get week overview with day-by-day breakdown.
    
    GET /api/v1/dashboard/week/
    
    Returns:
    - Week start/end dates
    - Day-by-day stats
    - Week totals
    """
    from core.services.dashboard_service import DashboardService
    
    try:
        service = DashboardService(request.user)
        week_data = service.get_week_overview()
        
        return JsonResponse({
            'success': True,
            **week_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET
def api_dashboard_goals(request):
    """
    Get active goals summary for dashboard.
    
    GET /api/v1/dashboard/goals/
    
    Returns list of active goals with progress info.
    """
    from core.services.dashboard_service import DashboardService
    
    try:
        service = DashboardService(request.user)
        goals = service.get_goals_progress()
        
        return JsonResponse({
            'success': True,
            'goals': goals,
            'count': len(goals)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET
def api_dashboard_streaks(request):
    """
    Get streak information.
    
    GET /api/v1/dashboard/streaks/
    
    Returns:
    - Current streak count
    - Longest streak (30 day window)
    - Streak threshold percentage
    - Days meeting threshold in last 30
    """
    from core.services.dashboard_service import DashboardService
    
    try:
        service = DashboardService(request.user)
        streaks = service.get_streaks()
        
        return JsonResponse({
            'success': True,
            **streaks
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET
def api_dashboard_activity(request):
    """
    Get recent activity feed.
    
    GET /api/v1/dashboard/activity/
    
    Query params:
        limit (optional): Number of items (default 10, max 50)
    
    Returns list of recent task completions.
    """
    from core.services.dashboard_service import DashboardService
    
    try:
        limit = int(request.GET.get('limit', 10))
        limit = min(max(1, limit), 50)  # Clamp between 1 and 50
        
        service = DashboardService(request.user)
        activity = service.get_recent_activity(limit)
        
        return JsonResponse({
            'success': True,
            'activity': activity,
            'count': len(activity)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET  
def api_trackers_list(request):
    """
    Get list of all user's trackers (summary only, no tasks).
    
    GET /api/v1/trackers/
    
    Query params:
        status (optional): Filter by status ('active', 'paused', 'archived')
        include_deleted (optional): Include soft-deleted trackers
    
    Returns list of tracker metadata.
    """
    try:
        status_filter = request.GET.get('status', 'active')
        include_deleted = request.GET.get('include_deleted', 'false').lower() == 'true'
        
        query = TrackerDefinition.objects.filter(user=request.user)
        
        if not include_deleted:
            query = query.filter(deleted_at__isnull=True)
        
        if status_filter and status_filter != 'all':
            query = query.filter(status=status_filter)
        
        trackers = query.order_by('-created_at')
        
        tracker_list = []
        for tracker in trackers:
            # Quick stats without loading all tasks
            template_count = tracker.templates.filter(deleted_at__isnull=True).count()
            
            tracker_list.append({
                'tracker_id': str(tracker.tracker_id),
                'name': tracker.name,
                'description': tracker.description,
                'time_mode': tracker.time_mode,
                'status': tracker.status,
                'target_points': getattr(tracker, 'target_points', 0),
                'goal_period': getattr(tracker, 'goal_period', 'daily'),
                'template_count': template_count,
                'created_at': tracker.created_at.isoformat(),
                'updated_at': tracker.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'trackers': tracker_list,
            'count': len(tracker_list)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_auth
@require_GET
def api_tracker_detail(request, tracker_id):
    """
    Get detailed information about a specific tracker.
    
    GET /api/v1/tracker/{tracker_id}/
    
    Returns full tracker info including templates (not instances).
    """
    try:
        tracker = TrackerDefinition.objects.get(
            tracker_id=tracker_id,
            user=request.user,
            deleted_at__isnull=True
        )
        
        # Get templates
        templates = tracker.templates.filter(deleted_at__isnull=True).order_by('-weight')
        
        template_list = [{
            'template_id': str(t.template_id),
            'description': t.description,
            'category': t.category,
            'weight': t.weight,
            'points': getattr(t, 'points', 1),
            'include_in_goal': getattr(t, 'include_in_goal', True),
            'is_recurring': t.is_recurring,
            'time_of_day': t.time_of_day,
        } for t in templates]
        
        return JsonResponse({
            'success': True,
            'tracker': {
                'tracker_id': str(tracker.tracker_id),
                'name': tracker.name,
                'description': tracker.description,
                'time_mode': tracker.time_mode,
                'status': tracker.status,
                'target_points': getattr(tracker, 'target_points', 0),
                'goal_period': getattr(tracker, 'goal_period', 'daily'),
                'goal_start_day': getattr(tracker, 'goal_start_day', 0),
                'created_at': tracker.created_at.isoformat(),
                'updated_at': tracker.updated_at.isoformat(),
            },
            'templates': template_list,
            'template_count': len(template_list)
        })
    except TrackerDefinition.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Tracker not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

