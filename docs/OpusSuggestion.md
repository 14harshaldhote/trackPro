# OpusSuggestion: Backend Optimization for Premium UX/UI

> **Author**: Claude (Opus-class analysis)  
> **Date**: 2025-12-05  
> **Scope**: Django Backend Refactoring for iOS + Web SPA Optimization


## Executive Summary

This document provides a comprehensive refactoring roadmap for the Tracker Pro Django backend, targeting all 36 UX/UI requirements specified for iOS and web applications. The current codebase is functional but lacks optimizations for:

1. **SPA Behavior** - Fast panel transitions with preloaded data
2. **Dashboard UX** - Filter behaviors with backend-driven state
3. **Modal Loading** - Instant modal content with skeleton support
4. **iOS Native Patterns** - Touch-optimized API responses
5. **Performance UX** - Optimistic updates, prefetching, offline support

---

## Part 1: SPA & Dashboard Optimization

### 1.1 Unified Response Format for SPA Panels

**Target UX Points**: #4 Feedback & Confirmation, #26 Animation & Motion, #27 Visual Feedback, #31 Perceived Performance

**Current State**: Panels return raw HTML without metadata for client-side state management.

**Proposed Changes**:

#### [MODIFY] [views_spa.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_spa.py)

Create a unified response wrapper for all panel views:

```python
from django.http import JsonResponse
from django.template.loader import render_to_string

class SPAResponse:
    """Unified SPA response with HTML content and metadata for frontend state."""
    
    @staticmethod
    def panel(request, template, context, panel_id, title=None, meta=None):
        """
        Returns JSON response with:
        - html: Rendered panel content
        - panelId: Unique identifier for caching/navigation
        - title: Page title for browser history
        - meta: Additional data (stats, counts, timestamps)
        - skeleton: Pre-computed skeleton structure
        - actions: Available quick actions for FAB/shortcuts
        """
        html_content = render_to_string(template, context, request)
        
        return JsonResponse({
            'html': html_content,
            'panelId': panel_id,
            'title': title or panel_id.replace('_', ' ').title(),
            'meta': meta or {},
            'timestamp': int(time.time()),
            'actions': context.get('quick_actions', []),
            'skeleton': generate_skeleton_structure(template)
        })
```

**Apply to all panel views**:
- `panel_dashboard` → Add `meta` with stats for header display
- `panel_today` → Add `meta` with progress, completion counts
- `panel_week` → Add `meta` with week summary
- `panel_tracker_detail` → Add `meta` with tracker-specific stats

---

### 1.2 Dashboard Filter Behavior (Backend-Driven)

**Target UX Points**: #5 Data Visualization Hierarchy, #14 Data Density, #31 Perceived Performance

**Current State**: Filters are query parameters but don't return optimized response payloads.

**Proposed Changes**:

#### [MODIFY] [views_spa.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_spa.py#L43-L181)

Enhance `panel_dashboard` with filter-aware responses:

```python
@login_required
def panel_dashboard(request):
    """Dashboard panel with filter-optimized responses"""
    
    period = request.GET.get('period', 'daily')
    include_skeleton = request.GET.get('skeleton', 'false') == 'true'
    
    # ... existing logic ...
    
    # Add filter state for client-side sync
    filter_state = {
        'current_period': period,
        'available_periods': ['daily', 'weekly', 'monthly', 'all'],
        'period_dates': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }
    
    # Add quick stats for header badges (iOS badge counts)
    quick_stats = {
        'pending_count': pending_count,  # For badge on tab
        'completed_today': completed_count,
        'streak_at_risk': streak < 3 and completed_count < pending_count
    }
    
    context['filter_state'] = filter_state
    context['quick_stats'] = quick_stats
    
    if include_skeleton:
        return JsonResponse({
            'skeleton': True,
            'item_count': len(dashboard_tasks),
            'groups': len(active_trackers)
        })
    
    return render(request, 'panels/dashboard.html', context)
```

---

### 1.3 Prefetch API for SPA Navigation

**Target UX Points**: #9 Mobile Performance, #20 Offline Experience, #31 Perceived Performance

**Proposed Changes**:

#### [NEW] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py) - Add prefetch endpoint

```python
@login_required
@require_GET
def api_prefetch(request):
    """
    Returns lightweight data for likely next navigations.
    Called on page load to preload adjacent panels.
    
    UX Target: Instant panel transitions via client-side caching.
    """
    current_panel = request.GET.get('current', 'dashboard')
    
    # Define navigation probabilities
    likely_next = {
        'dashboard': ['today', 'trackers'],
        'today': ['tracker_detail', 'week'],
        'week': ['today', 'month'],
        'trackers': ['tracker_detail'],
    }
    
    prefetch_data = {}
    
    for panel in likely_next.get(current_panel, []):
        prefetch_data[panel] = get_lightweight_panel_data(request.user, panel)
    
    return JsonResponse({
        'prefetch': prefetch_data,
        'ttl': 60  # Cache for 60 seconds
    })


def get_lightweight_panel_data(user, panel):
    """Return minimal data for skeleton rendering"""
    if panel == 'today':
        count = TaskInstance.objects.filter(
            tracker_instance__tracker__user=user,
            status__in=['TODO', 'IN_PROGRESS']
        ).count()
        return {'task_count': count, 'skeleton_items': min(count, 10)}
    
    elif panel == 'trackers':
        count = TrackerDefinition.objects.filter(user=user).exclude(status='archived').count()
        return {'tracker_count': count, 'skeleton_items': min(count, 6)}
    
    return {}
```

#### [MODIFY] [urls.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/urls.py)

Add route:
```python
path('api/prefetch/', views_api.api_prefetch, name='api_prefetch'),
```

---

## Part 2: Feedback & Confirmation System

### 2.1 Enhanced API Responses with Action Metadata

**Target UX Points**: #4 Feedback & Confirmation, #27 Visual Feedback, #32 Error Handling

**Current State**: API responses return basic `success/error` without detailed action context.

**Proposed Changes**:

#### [MODIFY] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py#L24-L71)

Enhance `api_task_toggle` with rich response:

```python
@login_required
@require_POST
def api_task_toggle(request, task_id):
    """Toggle task status with UX-optimized response"""
    try:
        task = get_object_or_404(TaskInstance, task_instance_id=task_id, ...)
        
        old_status = task.status
        new_status = status_cycle.get(old_status, 'DONE')
        task.status = new_status
        
        # Calculate celebration trigger
        is_completion = new_status == 'DONE' and old_status != 'DONE'
        
        # Get updated stats for instant UI refresh
        tracker_instance = task.tracker_instance
        remaining = TaskInstance.objects.filter(
            tracker_instance=tracker_instance,
            status__in=['TODO', 'IN_PROGRESS']
        ).count()
        
        task.save()
        
        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'old_status': old_status,
            'new_status': new_status,
            
            # UX Enhancement: Feedback metadata
            'feedback': {
                'type': 'celebration' if is_completion else 'status_change',
                'message': get_completion_message(new_status),
                'haptic': 'success' if is_completion else 'light',  # iOS haptic type
                'sound': 'complete' if is_completion else None,
                'animation': 'confetti' if is_completion and remaining == 0 else 'checkmark'
            },
            
            # UX Enhancement: Undo support
            'undo': {
                'enabled': True,
                'timeout_ms': 5000,
                'undo_data': {'task_id': task_id, 'old_status': old_status}
            },
            
            # UX Enhancement: Stats for optimistic update
            'stats_delta': {
                'remaining_tasks': remaining,
                'all_complete': remaining == 0
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'feedback': {
                'type': 'error',
                'message': 'Failed to update task. Please try again.',
                'haptic': 'error',
                'retry': True
            }
        }, status=400)


def get_completion_message(status):
    """Return celebratory or informational message based on status"""
    messages = {
        'DONE': ["Great job! 🎉", "Task completed! ✅", "You're on fire! 🔥", "Keep it up! 💪"],
        'SKIPPED': "Task skipped",
        'TODO': "Task reopened",
    }
    if status == 'DONE':
        import random
        return random.choice(messages['DONE'])
    return messages.get(status, 'Status updated')
```

---

### 2.2 Destructive Action Confirmation API

**Target UX Points**: #4 Destructive actions require confirmation

**Proposed Changes**:

#### [NEW] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py) - Add confirmation metadata endpoint

```python
@login_required
@require_GET  
def api_action_metadata(request, action_type, resource_id):
    """
    Returns metadata for confirmation dialogs before destructive actions.
    
    iOS Pattern: Action sheets with contextual information.
    Web Pattern: Confirmation modals with impact summary.
    """
    metadata = {
        'requires_confirmation': False,
        'confirmation': None
    }
    
    if action_type == 'delete_tracker':
        tracker = get_object_or_404(TrackerDefinition, tracker_id=resource_id, user=request.user)
        task_count = TaskInstance.objects.filter(tracker_instance__tracker=tracker).count()
        
        metadata = {
            'requires_confirmation': True,
            'confirmation': {
                'title': f'Delete "{tracker.name}"?',
                'message': f'This will permanently delete {task_count} tasks and all associated data.',
                'destructive': True,
                'buttons': [
                    {'label': 'Cancel', 'style': 'cancel'},
                    {'label': 'Delete', 'style': 'destructive', 'action': f'/api/tracker/{resource_id}/delete/'}
                ],
                'ios_style': 'actionSheet',  # iOS: Action sheet vs alert
                'web_style': 'modal'
            }
        }
    
    elif action_type == 'delete_task':
        task = get_object_or_404(TaskInstance, task_instance_id=resource_id, ...)
        is_recurring = task.template.is_recurring
        
        metadata = {
            'requires_confirmation': is_recurring,  # Only confirm recurring tasks
            'confirmation': {
                'title': 'Delete Task?',
                'message': 'This will delete this task instance.' + 
                          (' Future occurrences will still appear.' if is_recurring else ''),
                'destructive': True,
                'buttons': [
                    {'label': 'Cancel', 'style': 'cancel'},
                    {'label': 'Delete', 'style': 'destructive'}
                ]
            } if is_recurring else None
        }
    
    return JsonResponse(metadata)
```

---

## Part 3: iOS-Specific Optimizations

### 3.1 Touch-Optimized List Data

**Target UX Points**: #6 Touch Targets, #7 Native iOS Patterns, #8 iOS Navigation

**Proposed Changes**:

#### [MODIFY] [views_spa.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_spa.py#L185-L263)

Enhance `panel_today` with swipe action metadata:

```python
@login_required  
def panel_today(request):
    """Today's tasks panel with iOS swipe actions"""
    
    # ... existing logic ...
    
    for task in raw_tasks:
        task_data = {
            # Existing fields...
            'id': task.task_instance_id,
            'status': task.status,
            'description': task.template.description,
            
            # iOS Swipe Actions (44pt minimum touch target)
            'swipe_actions': {
                'leading': [  # Swipe right to reveal
                    {
                        'action': 'complete',
                        'label': '✓',
                        'color': '#22c55e',  # Green
                        'endpoint': f'/api/task/{task.task_instance_id}/toggle/',
                        'haptic': 'success'
                    }
                ],
                'trailing': [  # Swipe left to reveal
                    {
                        'action': 'skip',
                        'label': 'Skip',
                        'color': '#f59e0b',  # Amber
                        'endpoint': f'/api/task/{task.task_instance_id}/status/',
                        'payload': {'status': 'SKIPPED'}
                    },
                    {
                        'action': 'delete',
                        'label': 'Delete',
                        'color': '#ef4444',  # Red
                        'destructive': True,
                        'endpoint': f'/api/task/{task.task_instance_id}/delete/'
                    }
                ]
            },
            
            # Long-press context menu
            'context_menu': [
                {'label': 'Edit', 'icon': 'pencil', 'action': 'edit'},
                {'label': 'Move to Tomorrow', 'icon': 'arrow.right', 'action': 'move'},
                {'label': 'Add Note', 'icon': 'note.text', 'action': 'note'},
                {'label': 'Delete', 'icon': 'trash', 'destructive': True, 'action': 'delete'}
            ]
        }
        tasks.append(task_data)
```

---

### 3.2 Bottom Sheet Modal Endpoints

**Target UX Points**: #7 iOS Modals slide up, #8 iOS Navigation Patterns

**Proposed Changes**:

#### [MODIFY] [views_spa.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_spa.py) - Modal view enhancements

```python
@login_required
def modal_view(request, modal_name):
    """
    Modal content endpoint with iOS bottom sheet support.
    Returns HTML + metadata for modal presentation.
    """
    
    modal_config = {
        'add-task': {
            'template': 'modals/add_task.html',
            'title': 'New Task',
            'presentation': 'sheet',  # iOS: .sheet()
            'detents': ['medium', 'large'],  # iOS 15+ detents
            'grabber_visible': True,
            'corner_radius': 12
        },
        'edit-task': {
            'template': 'modals/edit_task.html',
            'title': 'Edit Task',
            'presentation': 'sheet',
            'detents': ['large'],
            'keyboard_avoidance': True
        },
        'add-tracker': {
            'template': 'modals/add_tracker.html',
            'title': 'New Tracker',
            'presentation': 'fullscreen',  # iOS: .fullScreenCover()
            'dismissable': True
        },
        'quick-add': {
            'template': 'modals/quick_add.html',
            'title': 'Quick Add',
            'presentation': 'sheet',
            'detents': ['medium'],
            'interactive_dismiss_disabled': False
        }
    }
    
    config = modal_config.get(modal_name, {
        'template': f'modals/{modal_name}.html',
        'presentation': 'sheet',
        'detents': ['large']
    })
    
    # ... existing context building ...
    
    html_content = render_to_string(config['template'], context, request)
    
    return JsonResponse({
        'html': html_content,
        'modal': {
            'id': modal_name,
            'title': config.get('title', modal_name.replace('-', ' ').title()),
            'presentation': config['presentation'],
            'ios': {
                'detents': config.get('detents', ['large']),
                'grabber_visible': config.get('grabber_visible', True),
                'corner_radius': config.get('corner_radius', 10),
                'keyboard_avoidance': config.get('keyboard_avoidance', False)
            },
            'web': {
                'position': 'center' if config['presentation'] == 'fullscreen' else 'bottom',
                'overlay': True,
                'closable': config.get('dismissable', True)
            }
        }
    })
```

---

### 3.3 Haptic Feedback Configuration

**Target UX Points**: #7 Haptic feedback on key actions

**Proposed Changes**:

#### [NEW] [utils/constants.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/utils/constants.py)

Add haptic feedback configuration:

```python
# Haptic Feedback Types (iOS UIImpactFeedbackGenerator)
HAPTIC_FEEDBACK = {
    'task_complete': 'success',      # UINotificationFeedbackGenerator.success
    'task_skip': 'warning',          # UINotificationFeedbackGenerator.warning  
    'task_delete': 'error',          # UINotificationFeedbackGenerator.error
    'button_tap': 'light',           # UIImpactFeedbackGenerator.light
    'toggle': 'medium',              # UIImpactFeedbackGenerator.medium
    'drag_drop': 'rigid',            # UIImpactFeedbackGenerator.rigid
    'selection_change': 'selection', # UISelectionFeedbackGenerator
    'streak_milestone': 'heavy',     # UIImpactFeedbackGenerator.heavy
}

# Action types that trigger haptics
HAPTIC_ACTIONS = [
    'task_toggle',
    'task_delete', 
    'tracker_create',
    'goal_achieved',
    'streak_continued',
]
```

---

## Part 4: Performance & Offline Optimization

### 4.1 Infinite Scroll for Task Lists

**Target UX Points**: #9 Infinite scroll for long lists, #14 Data Density

**Proposed Changes**:

#### [MODIFY] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

Add paginated task list endpoint:

```python
@login_required
@require_GET
def api_tasks_paginated(request, tracker_id=None):
    """
    Paginated task list for infinite scroll.
    Returns cursor-based pagination for efficient mobile performance.
    
    UX Target: 3G/4G optimized, lazy loading.
    """
    cursor = request.GET.get('cursor')  # Last task timestamp or ID
    limit = min(int(request.GET.get('limit', 20)), 50)  # Max 50 per request
    status_filter = request.GET.get('status')
    
    queryset = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user
    ).select_related('template', 'tracker_instance__tracker')
    
    if tracker_id:
        queryset = queryset.filter(tracker_instance__tracker__tracker_id=tracker_id)
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if cursor:
        # Cursor-based pagination (more efficient than offset)
        queryset = queryset.filter(created_at__lt=cursor)
    
    queryset = queryset.order_by('-created_at')[:limit + 1]
    tasks = list(queryset)
    
    has_more = len(tasks) > limit
    if has_more:
        tasks = tasks[:limit]
    
    return JsonResponse({
        'tasks': [serialize_task_for_list(t) for t in tasks],
        'pagination': {
            'has_more': has_more,
            'next_cursor': tasks[-1].created_at.isoformat() if tasks else None,
            'total_estimate': queryset.count() if not cursor else None  # Only on first page
        }
    })


def serialize_task_for_list(task):
    """Lightweight serialization for list views"""
    return {
        'id': task.task_instance_id,
        'description': task.template.description[:100],  # Truncate for list
        'status': task.status,
        'category': task.template.category,
        'tracker_name': task.tracker_instance.tracker.name,
        'time_of_day': task.template.time_of_day,
        'weight': task.template.weight,
        # Minimal for list, expand on detail view
    }
```

---

### 4.2 Offline Data Sync Endpoint

**Target UX Points**: #9 Cache data locally, #20 Offline Experience, #10 Background sync

**Proposed Changes**:

#### [NEW] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

Add sync endpoint for offline-first architecture:

```python
@login_required
@require_POST
def api_sync(request):
    """
    Bidirectional sync endpoint for offline-first mobile apps.
    
    Request body:
    - last_sync: ISO timestamp of last successful sync
    - pending_actions: Array of queued offline actions
    
    Response:
    - server_changes: Changes since last_sync
    - action_results: Results of pending actions
    - new_sync_timestamp: Timestamp for next sync
    """
    data = json.loads(request.body)
    last_sync = data.get('last_sync')
    pending_actions = data.get('pending_actions', [])
    
    # Process queued offline actions
    action_results = []
    for action in pending_actions:
        result = process_offline_action(request.user, action)
        action_results.append(result)
    
    # Get server changes since last sync
    changes = {}
    if last_sync:
        last_sync_dt = datetime.fromisoformat(last_sync)
        
        # Changed trackers
        changes['trackers'] = list(TrackerDefinition.objects.filter(
            user=request.user,
            updated_at__gt=last_sync_dt
        ).values('tracker_id', 'name', 'status', 'updated_at'))
        
        # Changed tasks
        changes['tasks'] = list(TaskInstance.objects.filter(
            tracker_instance__tracker__user=request.user,
            updated_at__gt=last_sync_dt
        ).values('task_instance_id', 'status', 'notes', 'updated_at'))
        
        # Deleted items (need soft delete or deletion log)
        changes['deletions'] = get_deletions_since(request.user, last_sync_dt)
    
    return JsonResponse({
        'action_results': action_results,
        'server_changes': changes,
        'new_sync_timestamp': timezone.now().isoformat(),
        'sync_status': 'complete'
    })


def process_offline_action(user, action):
    """Process a single queued offline action"""
    action_type = action.get('type')
    action_id = action.get('id')
    
    try:
        if action_type == 'task_toggle':
            task = TaskInstance.objects.get(
                task_instance_id=action['task_id'],
                tracker_instance__tracker__user=user
            )
            task.status = action['new_status']
            task.save()
            return {'id': action_id, 'success': True}
        
        # ... handle other action types ...
        
    except Exception as e:
        return {'id': action_id, 'success': False, 'error': str(e)}
```

---

### 4.3 Enhanced Caching Strategy

**Target UX Points**: #9 Cache data locally, #31 Perceived Performance

**Proposed Changes**:

#### [MODIFY] [helpers/cache_helpers.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/helpers/cache_helpers.py)

Add user-scoped caching:

```python
# Add to existing file

CACHE_TIMEOUTS = {
    # ... existing ...
    'user_dashboard': 30,       # 30 seconds (frequently changes)
    'user_overview': 120,       # 2 minutes
    'prefetch_data': 60,        # 1 minute
    'modal_content': 300,       # 5 minutes (static-ish)
}


def cache_per_user(timeout=60, key_prefix='user'):
    """Decorator for user-specific caching"""
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            cache_key = make_cache_key(f'{key_prefix}:{user_id}:{func.__name__}', *args, **kwargs)
            
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(request, *args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


def generate_etag(content):
    """Generate ETag for conditional GET requests"""
    import hashlib
    if isinstance(content, str):
        content = content.encode()
    return hashlib.md5(content).hexdigest()


def conditional_cache_response(request, content, timeout=60):
    """
    Return cached response with ETag/Last-Modified headers.
    Supports 304 Not Modified for unchanged content.
    """
    etag = generate_etag(content)
    
    # Check If-None-Match header
    if request.headers.get('If-None-Match') == etag:
        return HttpResponse(status=304)  # Not Modified
    
    response = JsonResponse(content if isinstance(content, dict) else {'data': content})
    response['ETag'] = etag
    response['Cache-Control'] = f'private, max-age={timeout}'
    return response
```

---

## Part 5: Notifications & Real-Time

### 5.1 Notification System Backend

**Target UX Points**: #17 Notifications System, #10 Notifications for reminders/streaks

**Proposed Changes**:

#### [MODIFY] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

Enhance notifications endpoint:

```python
@login_required
@require_GET
def api_notifications(request):
    """
    Get user notifications with badge count and grouping.
    
    iOS: Supports APNS payload format
    Web: Standard notification format
    """
    # Get unread count for badge
    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    # Get recent notifications grouped by type
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]
    
    grouped = {}
    for notif in notifications:
        if notif.type not in grouped:
            grouped[notif.type] = []
        grouped[notif.type].append({
            'id': notif.notification_id,
            'title': notif.title,
            'message': notif.message,
            'type': notif.type,
            'is_read': notif.is_read,
            'link': notif.link,
            'created_at': notif.created_at.isoformat(),
            'time_ago': humanize_time(notif.created_at)
        })
    
    return JsonResponse({
        'notifications': [n for group in grouped.values() for n in group],
        'grouped': grouped,
        'unread_count': unread_count,
        'badge': {
            'count': unread_count,
            'visible': unread_count > 0
        }
    })


@login_required
@require_POST
def api_notifications_mark_read(request):
    """Mark notifications as read"""
    data = json.loads(request.body)
    notification_ids = data.get('ids', [])
    mark_all = data.get('all', False)
    
    if mark_all:
        Notification.objects.filter(user=request.user).update(is_read=True)
    elif notification_ids:
        Notification.objects.filter(
            user=request.user,
            notification_id__in=notification_ids
        ).update(is_read=True)
    
    return JsonResponse({'success': True})
```

---

### 5.2 Push Notification Service Integration

**Target UX Points**: #10 Quick actions from app icon, #35 iOS Integration

**Proposed Changes**:

#### [NEW] [services/notification_service.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/services/notification_service.py)

```python
"""
Push Notification Service for iOS and Web.

Supports:
- APNS (Apple Push Notification Service) for iOS
- Web Push for browsers
- In-app notifications
"""
from django.conf import settings
from core.models import Notification, UserPreferences
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Unified notification service for all platforms"""
    
    NOTIFICATION_TYPES = {
        'streak_at_risk': {
            'title': '⚠️ Streak at Risk!',
            'body_template': 'Complete at least one task to maintain your {streak_count}-day streak!',
            'category': 'reminder',
            'sound': 'streak_alert.aiff',
            'badge_increment': 1
        },
        'daily_reminder': {
            'title': '📋 Daily Check-in',
            'body_template': 'You have {pending_count} tasks waiting for you today.',
            'category': 'reminder',
            'sound': 'default'
        },
        'goal_achieved': {
            'title': '🎉 Goal Achieved!',
            'body_template': 'Congratulations! You completed "{goal_name}"',
            'category': 'achievement',
            'sound': 'celebration.aiff'
        },
        'weekly_review': {
            'title': '📊 Weekly Review Ready',
            'body_template': 'See how you performed this week. Tap to view insights.',
            'category': 'insight'
        },
        'task_reminder': {
            'title': 'Task Reminder',
            'body_template': '{task_description}',
            'category': 'task',
            'sound': 'reminder.aiff'
        }
    }
    
    def __init__(self, user):
        self.user = user
        self.preferences = UserPreferences.objects.get_or_create(user=user)[0]
    
    def create_notification(self, notification_type, context=None, send_push=True):
        """Create in-app notification and optionally send push"""
        
        notif_config = self.NOTIFICATION_TYPES.get(notification_type, {})
        context = context or {}
        
        title = notif_config.get('title', 'Notification')
        body = notif_config.get('body_template', '').format(**context)
        
        # Create in-app notification
        notification = Notification.objects.create(
            user=self.user,
            type=notif_config.get('category', 'info'),
            title=title,
            message=body,
            link=context.get('link', '')
        )
        
        # Send push if enabled and user has opted in
        if send_push and self.preferences.push_enabled:
            self._send_push(notification, notif_config)
        
        return notification
    
    def _send_push(self, notification, config):
        """Send push notification (APNS/Web Push)"""
        # Implementation depends on your push service (Firebase, APNs, etc.)
        # Placeholder for platform-specific implementation
        
        payload = {
            'aps': {
                'alert': {
                    'title': notification.title,
                    'body': notification.message
                },
                'badge': Notification.objects.filter(
                    user=self.user, is_read=False
                ).count(),
                'sound': config.get('sound', 'default'),
                'category': config.get('category', 'default')
            },
            'notification_id': notification.notification_id,
            'link': notification.link
        }
        
        logger.info(f"Push notification payload: {payload}")
        # apns.send(device_token, payload)  # Actual implementation
    
    def check_streak_risk(self):
        """Check if any trackers have streaks at risk"""
        from core import analytics
        
        user_trackers = TrackerDefinition.objects.filter(
            user=self.user, 
            status='active'
        )
        
        for tracker in user_trackers:
            streaks = analytics.detect_streaks(tracker.tracker_id)
            current = streaks.get('value', {}).get('current_streak', 0)
            
            if current >= 3:  # Only warn for meaningful streaks
                # Check today's completion
                today_tasks = TaskInstance.objects.filter(
                    tracker_instance__tracker=tracker,
                    tracker_instance__period_start=date.today()
                )
                pending = today_tasks.filter(status__in=['TODO', 'IN_PROGRESS']).count()
                
                if pending > 0:
                    self.create_notification(
                        'streak_at_risk',
                        context={'streak_count': current},
                        send_push=True
                    )
```

---

## Part 6: Search & Global Navigation

### 6.1 Enhanced Global Search

**Target UX Points**: #16 Search Experience, #12 Keyboard shortcuts

**Current State**: Basic search with trackers and tasks only.

**Proposed Changes**:

#### [MODIFY] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py#L516-L570)

Enhance `api_search`:

```python
@login_required
@require_GET
def api_search(request):
    """
    Global search with type filtering and keyboard shortcut support (Cmd/Ctrl + K).
    
    Returns results grouped by type with relevance scoring.
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type')  # 'all', 'trackers', 'tasks', 'goals', 'notes'
    limit = min(int(request.GET.get('limit', 10)), 50)
    
    if len(query) < 2:
        return JsonResponse({
            'results': [],
            'suggestions': get_search_suggestions(request.user)
        })
    
    results = {
        'trackers': [],
        'tasks': [],
        'goals': [],
        'notes': [],
        'quick_actions': []
    }
    
    # Trackers
    if search_type in ['all', 'trackers', None]:
        trackers = TrackerDefinition.objects.filter(
            user=request.user,
            name__icontains=query
        )[:limit]
        
        results['trackers'] = [{
            'id': t.tracker_id,
            'name': t.name,
            'type': 'tracker',
            'icon': '📊',
            'subtitle': f'{t.time_period} • {t.task_count} tasks',
            'link': f'/tracker/{t.tracker_id}/'
        } for t in trackers]
    
    # Tasks (search in templates)
    if search_type in ['all', 'tasks', None]:
        templates = TaskTemplate.objects.filter(
            tracker__user=request.user,
            description__icontains=query
        ).select_related('tracker')[:limit]
        
        results['tasks'] = [{
            'id': t.template_id,
            'name': t.description[:50],
            'type': 'task',
            'icon': '✅',
            'subtitle': t.tracker.name,
            'link': f'/tracker/{t.tracker.tracker_id}/'
        } for t in templates]
    
    # Goals
    if search_type in ['all', 'goals', None]:
        goals = Goal.objects.filter(
            user=request.user,
            title__icontains=query
        )[:limit]
        
        results['goals'] = [{
            'id': g.goal_id,
            'name': g.title,
            'type': 'goal',
            'icon': g.icon,
            'subtitle': f'{int(g.progress)}% complete',
            'link': '/goals/'
        } for g in goals]
    
    # Notes
    if search_type in ['all', 'notes', None]:
        notes = DayNote.objects.filter(
            tracker__user=request.user,
            content__icontains=query
        ).select_related('tracker')[:limit]
        
        results['notes'] = [{
            'id': n.note_id,
            'name': n.content[:50] + '...',
            'type': 'note',
            'icon': '📝',
            'subtitle': f'{n.date} • {n.tracker.name}',
            'link': f'/tracker/{n.tracker.tracker_id}/'
        } for n in notes]
    
    # Quick actions (commands)
    if search_type in ['all', None]:
        commands = [
            {'name': 'New Tracker', 'action': 'create_tracker', 'shortcut': 'Ctrl+N'},
            {'name': 'Today View', 'action': 'goto_today', 'shortcut': 'T'},
            {'name': 'Week View', 'action': 'goto_week', 'shortcut': 'W'},
            {'name': 'Settings', 'action': 'goto_settings', 'shortcut': 'Ctrl+,'},
        ]
        results['quick_actions'] = [
            c for c in commands if query.lower() in c['name'].lower()
        ]
    
    return JsonResponse({
        'results': results,
        'query': query,
        'total': sum(len(v) for v in results.values()),
        'recent_searches': get_recent_searches(request.user)
    })


def get_search_suggestions(user):
    """Return suggestions when search is empty"""
    return {
        'recent': get_recent_searches(user)[:5],
        'popular': ['Daily Habits', 'Exercise', 'Reading', 'Work Tasks'],
        'quick_actions': [
            {'name': 'New Tracker', 'shortcut': 'Ctrl+N'},
            {'name': 'Today', 'shortcut': 'T'}
        ]
    }
```

---

## Part 7: Analytics & Insights UX

### 7.1 Smart Suggestions API

**Target UX Points**: #33 User Insights Features, #34 Smart Suggestions

**Proposed Changes**:

#### [MODIFY] [behavioral/insights_engine.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/behavioral/insights_engine.py)

Add smart suggestions:

```python
# Add to InsightsEngine class

def generate_smart_suggestions(self) -> List[Dict]:
    """
    Generate personalized suggestions based on user behavior patterns.
    
    UX Target: "You usually complete tasks on Mondays" type insights.
    """
    suggestions = []
    
    # Best day analysis
    daily_rates = self.completion.get('daily_rates', [])
    if len(daily_rates) >= 14:
        day_performance = analyze_day_of_week_performance(daily_rates)
        best_day = max(day_performance, key=day_performance.get)
        worst_day = min(day_performance, key=day_performance.get)
        
        if day_performance[best_day] - day_performance[worst_day] > 20:
            suggestions.append({
                'type': 'best_day',
                'title': f'You perform best on {best_day}s',
                'description': f'Your {best_day} completion rate is {day_performance[best_day]:.0f}%',
                'action': f'Schedule important tasks for {best_day}s'
            })
    
    # Best time of day analysis
    time_distribution = self._get_time_distribution()
    if time_distribution:
        best_time = max(time_distribution, key=time_distribution.get)
        suggestions.append({
            'type': 'best_time',
            'title': f'You\'re most productive in the {best_time}',
            'description': f'{time_distribution[best_time]:.0f}% of completed tasks are done in the {best_time}',
            'action': f'Focus on challenging tasks in the {best_time}'
        })
    
    # Streak prediction
    current_streak = self.streaks.get('value', {}).get('current_streak', 0)
    if current_streak >= 5:
        suggestions.append({
            'type': 'streak_encouragement',
            'title': f'🔥 {current_streak}-day streak!',
            'description': 'You\'re building strong momentum. Keep it going!',
            'action': 'Complete today\'s tasks to extend your streak'
        })
    
    # Goal progress prediction
    # Add goal-based suggestions...
    
    return suggestions


def _get_time_distribution(self):
    """Analyze task completion by time of day"""
    # Query task instances by time_of_day
    from core.models import TaskInstance
    
    completed = TaskInstance.objects.filter(
        tracker_instance__tracker__tracker_id=self.tracker_id,
        status='DONE'
    ).select_related('template')
    
    distribution = {'morning': 0, 'afternoon': 0, 'evening': 0}
    total = 0
    
    for task in completed:
        tod = task.template.time_of_day
        if tod in distribution:
            distribution[tod] += 1
            total += 1
    
    if total > 0:
        return {k: v/total*100 for k, v in distribution.items()}
    return {}
```

---

### 7.2 Chart Data API Optimization

**Target UX Points**: #5 Sparklines/mini charts, #33 Productivity trends

**Proposed Changes**:

#### [MODIFY] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

Optimize chart data endpoint:

```python
@login_required
@require_GET
def api_chart_data(request):
    """
    Optimized chart data for various visualization types.
    
    Supports:
    - Sparklines (minimal 7-14 point arrays)
    - Full charts (30+ points with labels)
    - Heatmaps (calendar grid data)
    """
    chart_type = request.GET.get('type', 'sparkline')
    tracker_id = request.GET.get('tracker_id')
    days = min(int(request.GET.get('days', 7)), 365)
    
    if chart_type == 'sparkline':
        # Minimal data for inline mini-charts
        data = get_sparkline_data(request.user, tracker_id, days)
        return JsonResponse({
            'type': 'sparkline',
            'data': data,
            'trend': calculate_trend(data)
        })
    
    elif chart_type == 'completion':
        data = get_completion_chart_data(request.user, tracker_id, days)
        return JsonResponse({
            'type': 'line',
            'labels': data['labels'],
            'datasets': [{
                'label': 'Completion Rate',
                'data': data['values'],
                'borderColor': '#6366f1',
                'fill': True,
                'backgroundColor': 'rgba(99, 102, 241, 0.1)'
            }],
            'annotations': data.get('annotations', [])
        })
    
    elif chart_type == 'category_pie':
        data = get_category_distribution(request.user, tracker_id)
        return JsonResponse({
            'type': 'doughnut',
            'labels': list(data.keys()),
            'datasets': [{
                'data': list(data.values()),
                'backgroundColor': generate_color_palette(len(data))
            }]
        })
    
    elif chart_type == 'weekly_comparison':
        data = get_weekly_comparison(request.user)
        return JsonResponse({
            'type': 'bar',
            'labels': ['This Week', 'Last Week'],
            'datasets': [{
                'label': 'Completion Rate',
                'data': [data['this_week'], data['last_week']],
                'backgroundColor': ['#22c55e', '#94a3b8']
            }],
            'change': data['change'],
            'change_direction': 'up' if data['change'] > 0 else 'down'
        })


def get_sparkline_data(user, tracker_id, days):
    """Return minimal array for sparkline chart"""
    today = date.today()
    data = []
    
    for i in range(days):
        day = today - timedelta(days=days - 1 - i)
        
        queryset = TaskInstance.objects.filter(
            tracker_instance__tracker__user=user,
            tracker_instance__period_start=day
        )
        
        if tracker_id:
            queryset = queryset.filter(tracker_instance__tracker__tracker_id=tracker_id)
        
        total = queryset.count()
        done = queryset.filter(status='DONE').count()
        rate = int(done / total * 100) if total > 0 else 0
        data.append(rate)
    
    return data


def calculate_trend(data):
    """Calculate trend direction from data array"""
    if len(data) < 3:
        return 'stable'
    
    first_half = sum(data[:len(data)//2]) / (len(data)//2)
    second_half = sum(data[len(data)//2:]) / (len(data) - len(data)//2)
    
    diff = second_half - first_half
    if diff > 5:
        return 'up'
    elif diff < -5:
        return 'down'
    return 'stable'
```

---

## Part 8: Empty States & Onboarding

### 8.1 Empty State Content API

**Target UX Points**: #28 Empty States

**Proposed Changes**:

#### [NEW] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

Add empty state content endpoint:

```python
@login_required
@require_GET
def api_empty_state(request, state_type):
    """
    Return empty state content for various panels.
    
    UX Target: Illustrative graphics, clear CTAs, sample data options.
    """
    
    EMPTY_STATES = {
        'no_trackers': {
            'illustration': '/static/illustrations/empty-trackers.svg',
            'title': 'Create your first tracker',
            'description': 'Trackers help you build habits and track progress over time.',
            'cta': {
                'label': 'Create Tracker',
                'action': 'open_modal',
                'modal': 'add-tracker'
            },
            'secondary_cta': {
                'label': 'Use a Template',
                'action': 'navigate',
                'link': '/templates/'
            },
            'sample_data': {
                'available': True,
                'description': 'Try with sample data',
                'action': 'load_sample_data'
            }
        },
        'no_tasks_today': {
            'illustration': '/static/illustrations/all-done.svg',
            'title': 'All caught up! 🎉',
            'description': 'No tasks for today. Enjoy your free time or add something new.',
            'cta': {
                'label': 'Quick Add Task',
                'action': 'open_modal',
                'modal': 'quick-add'
            }
        },
        'no_goals': {
            'illustration': '/static/illustrations/set-goals.svg',
            'title': 'Set meaningful goals',
            'description': 'Link tasks to goals to see how your daily habits contribute to the bigger picture.',
            'cta': {
                'label': 'Create Goal',
                'action': 'open_modal',
                'modal': 'add-goal'
            },
            'tips': [
                'Start with one achievable goal',
                'Link existing tasks to your goal',
                'Track progress daily'
            ]
        },
        'no_insights': {
            'illustration': '/static/illustrations/gathering-data.svg',
            'title': 'Gathering insights...',
            'description': 'Complete more tasks to unlock personalized insights and suggestions.',
            'progress': {
                'current': get_total_completions(request.user),
                'target': 14,  # 2 weeks of data
                'label': 'tasks completed'
            }
        },
        'no_search_results': {
            'illustration': '/static/illustrations/no-results.svg',
            'title': 'No results found',
            'description': 'Try different keywords or check your spelling.',
            'suggestions': get_search_suggestions(request.user)
        }
    }
    
    state = EMPTY_STATES.get(state_type, {
        'title': 'Nothing here yet',
        'description': 'Get started by adding some content.'
    })
    
    return JsonResponse(state)
```

---

## Part 9: Accessibility & Preferences

### 9.1 Accessibility Settings API

**Target UX Points**: #29 Screen Reader Support, #30 Inclusive Design

**Proposed Changes**:

#### [MODIFY] [models.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/models.py#L408-L467)

Enhance UserPreferences model:

```python
class UserPreferences(models.Model):
    # ... existing fields ...
    
    # Accessibility Settings (NEW)
    high_contrast_mode = models.BooleanField(default=False)
    reduced_motion = models.BooleanField(default=False)  # Respect prefers-reduced-motion
    font_size_scale = models.FloatField(default=1.0)  # 0.8 to 1.5
    screen_reader_hints = models.BooleanField(default=True)  # Extra ARIA hints
    voice_over_optimized = models.BooleanField(default=False)  # iOS VoiceOver
    
    # Color blindness accommodations
    color_blind_mode = models.CharField(
        max_length=20,
        choices=[
            ('none', 'None'),
            ('protanopia', 'Red-blind'),
            ('deuteranopia', 'Green-blind'),
            ('tritanopia', 'Blue-blind')
        ],
        default='none'
    )
```

#### [MODIFY] [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

Enhance preferences endpoint:

```python
@login_required
def api_preferences(request):
    """Get/update user preferences including accessibility"""
    prefs, created = UserPreferences.objects.get_or_create(user=request.user)
    
    if request.method == 'GET':
        return JsonResponse({
            'preferences': {
                # Display
                'theme': prefs.theme,
                'default_view': prefs.default_view,
                'compact_mode': prefs.compact_mode,
                'animations': prefs.animations,
                
                # Accessibility
                'accessibility': {
                    'high_contrast': prefs.high_contrast_mode,
                    'reduced_motion': prefs.reduced_motion,
                    'font_scale': prefs.font_size_scale,
                    'screen_reader_hints': prefs.screen_reader_hints,
                    'voice_over_optimized': prefs.voice_over_optimized,
                    'color_blind_mode': prefs.color_blind_mode
                },
                
                # Notifications
                'notifications': {
                    'daily_reminder': prefs.daily_reminder_enabled,
                    'daily_reminder_time': prefs.daily_reminder_time.isoformat() if prefs.daily_reminder_time else None,
                    'weekly_review': prefs.weekly_review_enabled,
                    'push_enabled': prefs.push_enabled
                },
                
                # Sounds
                'sounds': {
                    'complete': prefs.sound_complete,
                    'notify': prefs.sound_notify,
                    'volume': prefs.sound_volume
                }
            },
            
            # CSS custom properties for accessibility
            'css_variables': generate_accessibility_css(prefs)
        })
    
    # POST: Update preferences
    # ... existing update logic ...


def generate_accessibility_css(prefs):
    """Generate CSS custom properties based on user accessibility preferences"""
    css = {}
    
    if prefs.high_contrast_mode:
        css['--contrast-multiplier'] = '1.3'
        css['--border-width'] = '2px'
    
    if prefs.reduced_motion:
        css['--animation-duration'] = '0ms'
        css['--transition-duration'] = '0ms'
    
    css['--font-scale'] = str(prefs.font_size_scale)
    
    if prefs.color_blind_mode != 'none':
        # Provide alternative color palettes
        palettes = {
            'protanopia': {
                '--color-success': '#0ea5e9',  # Blue instead of green
                '--color-error': '#f59e0b',    # Amber instead of red
            },
            'deuteranopia': {
                '--color-success': '#0ea5e9',
                '--color-error': '#f59e0b',
            },
            'tritanopia': {
                '--color-success': '#22c55e',
                '--color-warning': '#ec4899',  # Pink instead of yellow
            }
        }
        css.update(palettes.get(prefs.color_blind_mode, {}))
    
    return css
```

---

## Part 10: Settings & Help

### 10.1 Settings Panel Optimization

**Target UX Points**: #18 Settings & Preferences, #19 Help & Support

**Proposed Changes**:

#### [MODIFY] [views_spa.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_spa.py)

Enhance settings panel:

```python
@login_required
def panel_settings(request, section='general'):
    """Settings panel with sections"""
    
    sections = {
        'general': {
            'title': 'General',
            'icon': 'cog',
            'template': 'settings/general.html'
        },
        'preferences': {
            'title': 'Preferences',
            'icon': 'adjustments',
            'template': 'settings/preferences.html'
        },
        'notifications': {
            'title': 'Notifications',
            'icon': 'bell',
            'template': 'settings/notifications.html'
        },
        'accessibility': {
            'title': 'Accessibility',
            'icon': 'eye',
            'template': 'settings/accessibility.html'
        },
        'data': {
            'title': 'Data & Privacy',
            'icon': 'shield',
            'template': 'settings/data.html'
        },
        'keyboard': {
            'title': 'Keyboard Shortcuts',
            'icon': 'command',
            'template': 'settings/keyboard.html'
        },
        'about': {
            'title': 'About & Help',
            'icon': 'info',
            'template': 'settings/about.html'
        }
    }
    
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    
    context = {
        'sections': sections,
        'current_section': section,
        'preferences': prefs,
        'user': request.user,
        
        # Keyboard shortcuts reference
        'shortcuts': KEYBOARD_SHORTCUTS if section == 'keyboard' else [],
        
        # Help resources
        'help': {
            'faq_url': '/help/faq/',
            'contact_email': 'support@trackerapp.com',
            'changelog_url': '/help/changelog/',
            'feature_request_url': '/help/feedback/'
        } if section == 'about' else {}
    }
    
    return render(request, sections.get(section, sections['general'])['template'], context)


KEYBOARD_SHORTCUTS = [
    {'keys': ['Cmd/Ctrl', 'K'], 'action': 'Open Search'},
    {'keys': ['Cmd/Ctrl', 'N'], 'action': 'Create New Tracker'},
    {'keys': ['T'], 'action': 'Go to Today'},
    {'keys': ['W'], 'action': 'Go to Week View'},
    {'keys': ['M'], 'action': 'Go to Month View'},
    {'keys': ['G'], 'action': 'Go to Goals'},
    {'keys': ['?'], 'action': 'Show Keyboard Shortcuts'},
    {'keys': ['Esc'], 'action': 'Close Modal/Search'},
    {'keys': ['Enter'], 'action': 'Submit Form/Toggle Task'},
    {'keys': ['↑', '↓'], 'action': 'Navigate List'},
    {'keys': ['Space'], 'action': 'Toggle Selected Task'},
]
```

---

## Implementation Priority Matrix

| Priority | UX Points | Backend Changes | Effort |
|----------|-----------|-----------------|--------|
| **P0 (Critical)** | #4, #27, #31, #32 | Enhanced API responses with feedback metadata | Medium |
| **P0 (Critical)** | #9, #20 | Offline sync, prefetch endpoints | High |
| **P1 (High)** | #6, #7, #8 | iOS swipe actions, modal metadata | Medium |
| **P1 (High)** | #16 | Enhanced global search | Medium |
| **P1 (High)** | #17 | Notification system enhancements | Medium |
| **P2 (Medium)** | #33, #34 | Smart suggestions API | Medium |
| **P2 (Medium)** | #28 | Empty state content API | Low |
| **P2 (Medium)** | #29, #30 | Accessibility preferences | Medium |
| **P3 (Lower)** | #5 | Sparkline data optimization | Low |
| **P3 (Lower)** | #18, #19 | Settings/Help panel enhancements | Low |

---

## Summary of New Files

| File | Purpose |
|------|---------|
| `services/notification_service.py` | Push notification handling |
| (Modifications only - no new files needed for most changes) | |

## Summary of Modified Files

| File | Key Changes |
|------|-------------|
| `views_spa.py` | SPAResponse wrapper, iOS modal metadata, swipe actions |
| `views_api.py` | Prefetch, sync, enhanced feedback, pagination |
| `models.py` | Accessibility preferences |
| `urls.py` | New endpoints for prefetch, sync, empty states |
| `helpers/cache_helpers.py` | User-scoped caching, ETags |
| `behavioral/insights_engine.py` | Smart suggestions |
| `utils/constants.py` | Haptic feedback configuration |

---

## Verification Plan

### Automated Tests
1. Run existing test suite: `python manage.py test core`
2. Add API response format tests for new metadata fields
3. Add pagination tests for infinite scroll endpoints

### Manual Verification
1. Test SPA panel transitions with network throttling (3G simulation)
2. Verify offline mode with Service Worker
3. Test iOS swipe actions in Safari/mobile simulator
4. Verify accessibility with VoiceOver enabled

---

*This document provides the complete backend refactoring roadmap. Implementation should proceed in priority order, with P0 items being essential for the MVP iOS/Web experience.*
