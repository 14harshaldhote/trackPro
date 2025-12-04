"""
Tracker Pro - SPA API Views
AJAX endpoints for interactive components
"""
import json
from datetime import date, datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.template.loader import render_to_string

from .models import TrackerDefinition, TrackerInstance, DayNote


# ============================================================================
# TASK ENDPOINTS
# ============================================================================

@login_required
@require_POST
def api_task_toggle(request, task_id):
    """Toggle task status with optimistic UI support"""
    try:
        instance = get_object_or_404(
            TrackerInstance, 
            id=task_id, 
            tracker_definition__user=request.user
        )
        
        old_status = instance.status
        
        # Cycle through statuses: PENDING -> DONE -> SKIPPED -> PENDING
        status_cycle = {
            'PENDING': 'DONE',
            'DONE': 'SKIPPED',
            'SKIPPED': 'PENDING',
            'MISSED': 'DONE'
        }
        
        new_status = status_cycle.get(old_status, 'DONE')
        instance.status = new_status
        instance.save()
        
        return JsonResponse({
            'success': True,
            'old_status': old_status,
            'new_status': new_status,
            'task_id': task_id,
            'can_undo': True
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def api_task_status(request, task_id):
    """Set specific task status"""
    try:
        data = json.loads(request.body)
        status = data.get('status', 'DONE')
        
        instance = get_object_or_404(
            TrackerInstance,
            id=task_id,
            tracker_definition__user=request.user
        )
        
        old_status = instance.status
        instance.status = status
        instance.save()
        
        return JsonResponse({
            'success': True,
            'old_status': old_status,
            'new_status': status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def api_tasks_bulk(request):
    """Bulk actions on multiple tasks"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return JsonResponse({
                'success': False,
                'error': 'No tasks selected'
            }, status=400)
        
        instances = TrackerInstance.objects.filter(
            id__in=task_ids,
            tracker_definition__user=request.user
        )
        
        count = instances.count()
        
        if action == 'complete':
            instances.update(status='DONE')
        elif action == 'skip':
            instances.update(status='SKIPPED')
        elif action == 'pending':
            instances.update(status='PENDING')
        elif action == 'delete':
            instances.delete()
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unknown action: {action}'
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'action': action,
            'count': count,
            'message': f'{count} tasks updated'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def api_task_add(request, tracker_id):
    """Quick add task to tracker"""
    try:
        data = json.loads(request.body)
        description = data.get('description', '').strip()
        
        if not description:
            return JsonResponse({
                'success': False,
                'error': 'Description is required'
            }, status=400)
        
        tracker = get_object_or_404(
            TrackerDefinition,
            id=tracker_id,
            user=request.user
        )
        
        # Create task for today
        instance = TrackerInstance.objects.create(
            tracker_definition=tracker,
            date=date.today(),
            description=description,
            status='PENDING',
            category=data.get('category', ''),
            weight=data.get('weight', 1),
            time_of_day=data.get('time_of_day', '')
        )
        
        return JsonResponse({
            'success': True,
            'task': {
                'id': str(instance.id),
                'description': instance.description,
                'status': instance.status
            },
            'message': 'Task added'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def api_tracker_reorder(request, tracker_id):
    """Reorder tasks in a tracker"""
    try:
        data = json.loads(request.body)
        order = data.get('order', [])
        
        tracker = get_object_or_404(
            TrackerDefinition,
            id=tracker_id,
            user=request.user
        )
        
        # Update order field for each task
        for index, task_id in enumerate(order):
            TrackerInstance.objects.filter(
                id=task_id,
                tracker_definition=tracker
            ).update(order=index)
        
        return JsonResponse({
            'success': True,
            'message': 'Order saved'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# TRACKER ENDPOINTS
# ============================================================================

@login_required
@require_POST
def api_tracker_create(request):
    """Create new tracker via AJAX"""
    try:
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({
                'success': False,
                'errors': {'name': 'Name is required'}
            }, status=400)
        
        tracker = TrackerDefinition.objects.create(
            user=request.user,
            name=name,
            description=data.get('description', ''),
            time_period=data.get('time_period', 'DAILY'),
            goal_type=data.get('goal_type', 'COMPLETE_ALL'),
            goal_target=data.get('goal_target', 100),
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'tracker': {
                'id': str(tracker.id),
                'name': tracker.name
            },
            'redirect': f'/tracker/{tracker.id}/',
            'message': 'Tracker created successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def api_tracker_delete(request, tracker_id):
    """Delete tracker via AJAX"""
    try:
        tracker = get_object_or_404(
            TrackerDefinition,
            id=tracker_id,
            user=request.user
        )
        
        name = tracker.name
        tracker.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'"{name}" deleted',
            'redirect': '/trackers/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# SEARCH ENDPOINT
# ============================================================================

@login_required
@require_GET
def api_search(request):
    """Global search across trackers and tasks"""
    try:
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({
                'trackers': [],
                'tasks': []
            })
        
        # Search trackers
        trackers = TrackerDefinition.objects.filter(
            user=request.user,
            name__icontains=query
        )[:5]
        
        # Search tasks
        tasks = TrackerInstance.objects.filter(
            tracker_definition__user=request.user,
            description__icontains=query
        ).select_related('tracker_definition')[:10]
        
        return JsonResponse({
            'trackers': [
                {
                    'id': str(t.id),
                    'name': t.name,
                    'task_count': TrackerInstance.objects.filter(
                        tracker_definition=t,
                        date=date.today()
                    ).count()
                }
                for t in trackers
            ],
            'tasks': [
                {
                    'id': str(t.id),
                    'description': t.description,
                    'tracker_id': str(t.tracker_definition.id),
                    'tracker_name': t.tracker_definition.name,
                    'category': t.category or ''
                }
                for t in tasks
            ]
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'trackers': [],
            'tasks': []
        })


# ============================================================================
# DAY NOTE ENDPOINT
# ============================================================================

@login_required
@require_POST
def api_day_note(request, date_str):
    """Save day note"""
    try:
        data = json.loads(request.body)
        note_text = data.get('note', '')
        
        note_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        note, created = DayNote.objects.update_or_create(
            user=request.user,
            date=note_date,
            defaults={'content': note_text}
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Note saved'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# UNDO ENDPOINT
# ============================================================================

@login_required
@require_POST
def api_undo(request):
    """Undo last action (stored in session)"""
    try:
        data = json.loads(request.body)
        undo_type = data.get('type')
        undo_data = data.get('data', {})
        
        if undo_type == 'task_toggle':
            task_id = undo_data.get('task_id')
            old_status = undo_data.get('old_status')
            
            instance = TrackerInstance.objects.get(
                id=task_id,
                tracker_definition__user=request.user
            )
            instance.status = old_status
            instance.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Action undone'
            })
        
        return JsonResponse({
            'success': False,
            'error': 'Unknown undo type'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# EXPORT ENDPOINT
# ============================================================================

@login_required
@require_GET
def api_export(request, tracker_id):
    """Export tracker data"""
    import csv
    from django.http import HttpResponse
    
    try:
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
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# SHARE ENDPOINT
# ============================================================================

@login_required
@require_POST
def api_share_tracker(request, tracker_id):
    """Generate share link for tracker"""
    import uuid
    
    try:
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
        
        return JsonResponse({
            'success': True,
            'share_url': share_url,
            'token': tracker.share_token
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================================================
# FORM VALIDATION ENDPOINT
# ============================================================================

@login_required
@require_POST
def api_validate_field(request):
    """Real-time field validation"""
    try:
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
        
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'errors': [str(e)]
        }, status=400)
