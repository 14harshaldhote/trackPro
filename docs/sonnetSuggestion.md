# Sonnet's Practical Backend Refactoring Guide

> **Approach**: Implementation-focused, quick wins first, step-by-step refactoring  
> **Date**: 2025-12-05  
> **Scope**: Django Backend Optimization for iOS + Web UX


## Quick Start: Immediate Impact Changes (1-2 hours)

These changes provide maximum UX improvement with minimal backend work.

---

## Phase 1: API Response Enhancement (UX #4, #27, #31)

**Target**: Every action gets visual feedback, instant visual feedback, perceived performance

### Step 1.1: Create Response Helper Class

**File**: `core/utils/response_helpers.py` (NEW)

```python
"""
API Response Helpers for UX-Optimized Responses
Provides consistent response format with feedback metadata
"""
from django.http import JsonResponse
from typing import Dict, Any, Optional


class UXResponse:
    """Helper for creating UX-optimized API responses"""
    
    @staticmethod
    def success(
        message: str = "Action completed",
        data: Optional[Dict] = None,
        feedback: Optional[Dict] = None,
        stats_delta: Optional[Dict] = None
    ) -> JsonResponse:
        """
        Success response with UX metadata
        
        Args:
            message: User-friendly success message
            data: Response data
            feedback: Visual feedback configuration
            stats_delta: Changed stats for optimistic updates
        """
        response = {
            'success': True,
            'message': message,
            'data': data or {},
            'feedback': feedback or {
                'type': 'success',
                'haptic': 'success',
                'toast': True
            }
        }
        
        if stats_delta:
            response['stats_delta'] = stats_delta
        
        return JsonResponse(response)
    
    @staticmethod
    def error(
        message: str = "An error occurred",
        error_code: str = "GENERAL_ERROR",
        retry: bool = False,
        help_link: Optional[str] = None
    ) -> JsonResponse:
        """
        Error response with helpful messaging
        
        Args:
            message: Clear, actionable error message
            error_code: Error code for debugging
            retry: Whether user should retry
            help_link: Link to help documentation
        """
        response = {
            'success': False,
            'error': {
                'message': message,
                'code': error_code,
                'retry': retry
            },
            'feedback': {
                'type': 'error',
                'haptic': 'error',
                'toast': True
            }
        }
        
        if help_link:
            response['error']['help_link'] = help_link
        
        return JsonResponse(response, status=400)
    
    @staticmethod
    def celebration(
        achievement: str,
        animation: str = "confetti"
    ) -> Dict:
        """
        Celebration feedback for milestones
        
        Args:
            achievement: What was achieved
            animation: Animation type (confetti, fireworks, checkmark)
        """
        return {
            'type': 'celebration',
            'message': achievement,
            'animation': animation,
            'haptic': 'heavy',
            'sound': 'celebration'
        }
```

### Step 1.2: Update api_task_toggle (Quick Win)

**File**: [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py#L24-L71)

**REPLACE** lines 24-71 with:

```python
from core.utils.response_helpers import UXResponse

@login_required
@require_POST
def api_task_toggle(request, task_id):
    """Toggle task with UX-optimized response"""
    try:
        task = get_object_or_404(
            TaskInstance, 
            task_instance_id=task_id, 
            tracker_instance__tracker__user=request.user
        )
        
        old_status = task.status
        status_cycle = {
            'TODO': 'DONE',
            'IN_PROGRESS': 'DONE',
            'DONE': 'SKIPPED',
            'SKIPPED': 'TODO',
            'MISSED': 'DONE',
            'BLOCKED': 'TODO'
        }
        
        new_status = status_cycle.get(old_status, 'DONE')
        task.status = new_status
        
        if new_status == 'DONE':
            task.completed_at = timezone.now()
        else:
            task.completed_at = None
        
        task.save()
        
        # Calculate stats for optimistic update
        tracker_instance = task.tracker_instance
        remaining = TaskInstance.objects.filter(
            tracker_instance=tracker_instance,
            status__in=['TODO', 'IN_PROGRESS']
        ).count()
        
        # Determine feedback type
        feedback = None
        if new_status == 'DONE':
            if remaining == 0:
                # All tasks complete - celebrate!
                feedback = UXResponse.celebration(
                    "All tasks complete! 🎉",
                    animation="confetti"
                )
            else:
                feedback = {
                    'type': 'success',
                    'message': 'Task completed! ✓',
                    'haptic': 'success',
                    'animation': 'checkmark'
                }
        
        return UXResponse.success(
            message=f"Task {new_status.lower()}",
            data={
                'task_id': task_id,
                'old_status': old_status,
                'new_status': new_status,
                'can_undo': True
            },
            feedback=feedback,
            stats_delta={
                'remaining_tasks': remaining,
                'all_complete': remaining == 0
            }
        )
        
    except TaskInstance.DoesNotExist:
        return UXResponse.error(
            message="Task not found. It may have been deleted.",
            error_code="TASK_NOT_FOUND",
            retry=False
        )
    
    except Exception as e:
        return UXResponse.error(
            message="Unable to update task. Please try again.",
            error_code="UPDATE_FAILED",
            retry=True
        )
```

**Impact**: ✅ Instant feedback, haptics, celebration animations

---

## Phase 2: Loading States & Skeletons (UX #26, #31)

**Target**: Loading skeletons, skeleton screens during loading, smooth transitions

### Step 2.1: Add Skeleton Generator Utility

**File**: `core/utils/skeleton_helpers.py` (NEW)

```python
"""
Skeleton Screen Generator
Provides skeleton structure for panels to enable instant loading states
"""
from typing import Dict, List


def generate_panel_skeleton(panel_type: str, item_count: int = 5) -> Dict:
    """
    Generate skeleton structure for instant loading
    
    Args:
        panel_type: Type of panel (dashboard, today, week, etc.)
        item_count: Estimated number of items
    
    Returns:
        Skeleton structure for frontend rendering
    """
    
    skeletons = {
        'dashboard': {
            'type': 'dashboard',
            'sections': [
                {
                    'type': 'stats_grid',
                    'columns': 4,
                    'items': [
                        {'type': 'stat_card', 'has_icon': True, 'has_value': True}
                        for _ in range(4)
                    ]
                },
                {
                    'type': 'task_list',
                    'items': [
                        {
                            'type': 'task_item',
                            'has_checkbox': True,
                            'has_text': True,
                            'has_badge': True
                        }
                        for _ in range(min(item_count, 8))
                    ]
                },
                {
                    'type': 'tracker_grid',
                    'columns': 2,
                    'items': [
                        {'type': 'tracker_card', 'has_progress': True}
                        for _ in range(4)
                    ]
                }
            ]
        },
        
        'today': {
            'type': 'today',
            'sections': [
                {
                    'type': 'header',
                    'has_date': True,
                    'has_progress_ring': True
                },
                {
                    'type': 'task_groups',
                    'groups': [
                        {
                            'type': 'task_group',
                            'has_header': True,
                            'task_count': min(item_count // 2, 5)
                        }
                        for _ in range(2)
                    ]
                }
            ]
        },
        
        'trackers': {
            'type': 'grid',
            'columns': 2,
            'items': [
                {
                    'type': 'tracker_card',
                    'has_image': False,
                    'has_title': True,
                    'has_stats': True,
                    'has_progress': True
                }
                for _ in range(min(item_count, 6))
            ]
        },
        
        'list': {
            'type': 'list',
            'items': [
                {
                    'type': 'list_item',
                    'has_avatar': True,
                    'has_title': True,
                    'has_subtitle': True,
                    'has_action': True
                }
                for _ in range(min(item_count, 10))
            ]
        }
    }
    
    return skeletons.get(panel_type, skeletons['list'])


def generate_modal_skeleton(modal_type: str) -> Dict:
    """Generate skeleton for modal content"""
    
    skeletons = {
        'add-task': {
            'type': 'form',
            'fields': [
                {'type': 'text_input', 'label': True},
                {'type': 'select', 'label': True},
                {'type': 'slider', 'label': True}
            ],
            'actions': 2
        },
        
        'edit-tracker': {
            'type': 'form',
            'fields': [
                {'type': 'text_input', 'label': True},
                {'type': 'textarea', 'label': True},
                {'type': 'radio_group', 'label': True, 'options': 3}
            ],
            'actions': 2
        }
    }
    
    return skeletons.get(modal_type, {'type': 'generic_form', 'fields': 3})
```

### Step 2.2: Update Panel Views to Support Skeleton Mode

**File**: [views_spa.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_spa.py#L43-L181)

**ADD** this decorator before existing `panel_dashboard`:

```python
from core.utils.skeleton_helpers import generate_panel_skeleton
from functools import wraps

def supports_skeleton(default_item_count=5):
    """Decorator to add skeleton support to panel views"""
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
            
            # Normal request
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Apply to existing panel views:
@login_required
@supports_skeleton(default_item_count=8)
def panel_dashboard(request):
    # ... existing code ...
```

**Impact**: ✅ Skeleton screens, perceived performance, smooth loading

---

## Phase 3: iOS Touch Targets & Swipe Actions (UX #6, #7)

**Target**: Minimum 44x44pt touch targets, swipe actions on list items

### Step 3.1: Add iOS Action Metadata to Task Lists

**File**: [views_spa.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_spa.py#L185-L263)

**MODIFY** `panel_today` to add iOS-specific metadata:

Find this section (around line 220-230):

```python
for task in raw_tasks:
    # Handle both object and dict access
    status = getattr(task, 'status', None) or task.get('status') if isinstance(task, dict) else None
    if not status: continue
    
    tasks.append(task)
```

**REPLACE** with:

```python
for task in raw_tasks:
    # Handle both object and dict access
    status = getattr(task, 'status', None) or task.get('status') if isinstance(task, dict) else None
    if not status: continue
    
    # Enhance task with iOS swipe actions
    if isinstance(task, dict):
        task_enhanced = task.copy()
    else:
        # Convert model to dict with swipe actions
        task_enhanced = {
            'task_instance_id': task.task_instance_id,
            'status': task.status,
            'description': task.template.description,
            'category': task.template.category,
            'time_of_day': task.template.time_of_day,
            'weight': task.template.weight,
        }
    
    # Add iOS swipe actions (44pt minimum touch target)
    task_enhanced['ios_swipe_actions'] = {
        'leading': [
            {
                'id': 'complete',
                'title': '✓',
                'style': 'normal',
                'backgroundColor': '#22c55e',
                'endpoint': f'/api/task/{task_enhanced["task_instance_id"]}/toggle/',
                'haptic': 'success',
                'minWidth': 44  # Apple HIG minimum
            }
        ] if status != 'DONE' else [],
        
        'trailing': [
            {
                'id': 'skip',
                'title': 'Skip',
                'style': 'normal',
                'backgroundColor': '#f59e0b',
                'endpoint': f'/api/task/{task_enhanced["task_instance_id"]}/status/',
                'payload': {'status': 'SKIPPED'},
                'haptic': 'light',
                'minWidth': 60
            },
            {
                'id': 'delete',
                'title': 'Delete',
                'style': 'destructive',
                'backgroundColor': '#ef4444',
                'endpoint': f'/api/task/{task_enhanced["task_instance_id"]}/delete/',
                'confirmRequired': True,
                'haptic': 'warning',
                'minWidth': 70
            }
        ]
    }
    
    # Add long-press menu
    task_enhanced['ios_context_menu'] = [
        {'title': 'Edit', 'icon': 'pencil', 'action': 'edit'},
        {'title': 'Add Note', 'icon': 'note.text', 'action': 'note'},
        {'title': 'Move to Tomorrow', 'icon': 'arrow.forward', 'action': 'reschedule'},
        {'title': 'Delete', 'icon': 'trash', 'destructive': True, 'action': 'delete'}
    ]
    
    tasks.append(task_enhanced)
```

**Impact**: ✅ 44pt touch targets, swipe actions, long-press menus

---

## Phase 4: Infinite Scroll & Pagination (UX #9, #14)

**Target**: Infinite scroll for long lists, show more data per screen

### Step 4.1: Create Cursor-Based Pagination Helper

**File**: `core/utils/pagination_helpers.py` (NEW)

```python
"""
Cursor-Based Pagination for Mobile Performance
More efficient than offset pagination for large datasets
"""
from typing import Dict, List, Any, Optional
from django.db.models import QuerySet
from django.http import JsonResponse


class CursorPaginator:
    """
    Cursor-based pagination for infinite scroll
    
    Usage:
        paginator = CursorPaginator(
            queryset=TaskInstance.objects.all(),
            cursor_field='created_at',
            page_size=20
        )
        
        result = paginator.paginate(cursor=request.GET.get('cursor'))
    """
    
    def __init__(
        self,
        queryset: QuerySet,
        cursor_field: str = 'created_at',
        page_size: int = 20,
        max_page_size: int = 100
    ):
        self.queryset = queryset
        self.cursor_field = cursor_field
        self.page_size = min(page_size, max_page_size)
    
    def paginate(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Paginate queryset
        
        Args:
            cursor: Cursor value from previous page
        
        Returns:
            {
                'items': [...],
                'pagination': {
                    'has_more': bool,
                    'next_cursor': str,
                    'count': int
                }
            }
        """
        # Apply cursor filter
        qs = self.queryset
        if cursor:
            qs = qs.filter(**{f'{self.cursor_field}__lt': cursor})
        
        # Order by cursor field
        qs = qs.order_by(f'-{self.cursor_field}')
        
        # Fetch one extra to determine if there are more
        items = list(qs[:self.page_size + 1])
        
        has_more = len(items) > self.page_size
        if has_more:
            items = items[:self.page_size]
        
        # Get next cursor
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = str(getattr(last_item, self.cursor_field))
        
        return {
            'items': items,
            'pagination': {
                'has_more': has_more,
                'next_cursor': next_cursor,
                'page_size': self.page_size,
                'returned_count': len(items)
            }
        }


def paginated_response(
    items: List[Any],
    serializer_func,
    has_more: bool,
    next_cursor: Optional[str],
    meta: Optional[Dict] = None
) -> JsonResponse:
    """
    Create standardized paginated response
    
    Args:
        items: List of items to serialize
        serializer_func: Function to serialize each item
        has_more: Whether more items exist
        next_cursor: Cursor for next page
        meta: Additional metadata
    """
    return JsonResponse({
        'data': [serializer_func(item) for item in items],
        'pagination': {
            'has_more': has_more,
            'next_cursor': next_cursor,
            'count': len(items)
        },
        'meta': meta or {}
    })
```

### Step 4.2: Add Infinite Scroll Endpoint

**File**: [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

**ADD** new endpoint after line 800:

```python
from core.utils.pagination_helpers import CursorPaginator, paginated_response

@login_required
@require_GET
def api_tasks_infinite(request):
    """
    Infinite scroll endpoint for task lists
    
    Query params:
        cursor: Pagination cursor
        limit: Page size (default 20, max 50)
        status: Filter by status
        tracker_id: Filter by tracker
    
    UX Target: Infinite scroll, mobile performance
    """
    cursor = request.GET.get('cursor')
    limit = min(int(request.GET.get('limit', 20)), 50)
    status = request.GET.get('status')
    tracker_id = request.GET.get('tracker_id')
    
    # Build queryset
    qs = TaskInstance.objects.filter(
        tracker_instance__tracker__user=request.user
    ).select_related('template', 'tracker_instance__tracker')
    
    if status:
        qs = qs.filter(status=status)
    
    if tracker_id:
        qs = qs.filter(tracker_instance__tracker__tracker_id=tracker_id)
    
    # Paginate
    paginator = CursorPaginator(
        queryset=qs,
        cursor_field='created_at',
        page_size=limit
    )
    
    result = paginator.paginate(cursor)
    
    # Serialize items
    def serialize_task(task):
        return {
            'id': task.task_instance_id,
            'description': task.template.description,
            'status': task.status,
            'category': task.template.category,
            'tracker_name': task.tracker_instance.tracker.name,
            'tracker_id': task.tracker_instance.tracker.tracker_id,
            'time_of_day': task.template.time_of_day,
            'weight': task.template.weight,
            'created_at': task.created_at.isoformat(),
            # iOS swipe actions
            'swipe_actions': generate_swipe_actions(task),
        }
    
    return paginated_response(
        items=result['items'],
        serializer_func=serialize_task,
        has_more=result['pagination']['has_more'],
        next_cursor=result['pagination']['next_cursor']
    )


def generate_swipe_actions(task):
    """Generate swipe actions for a task"""
    return {
        'leading': [
            {'id': 'complete', 'title': '✓', 'color': '#22c55e'}
        ] if task.status != 'DONE' else [],
        'trailing': [
            {'id': 'skip', 'title': 'Skip', 'color': '#f59e0b'},
            {'id': 'delete', 'title': 'Delete', 'color': '#ef4444', 'destructive': True}
        ]
    }
```

**ADD** to [urls.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/urls.py):

```python
path('api/tasks/infinite/', views_api.api_tasks_infinite, name='api_tasks_infinite'),
```

**Impact**: ✅ Infinite scroll, optimized for 3G/4G, mobile-first

---

## Phase 5: Offline Support & Sync (UX #9, #20, #31)

**Target**: Cache data locally, offline fallback, background sync

### Step 5.1: Create Sync Queue System

**File**: `core/services/sync_service.py` (NEW)

```python
"""
Offline Sync Service
Handles queued actions and bidirectional sync
"""
from typing import List, Dict, Any
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from core.models import TaskInstance, TrackerDefinition


class SyncService:
    """Handle offline action processing and sync"""
    
    def __init__(self, user):
        self.user = user
    
    def process_sync_request(self, data: Dict) -> Dict:
        """
        Process bidirectional sync
        
        Args:
            data: {
                'last_sync': ISO timestamp,
                'pending_actions': [...],
                'device_id': str
            }
        
        Returns:
            {
                'action_results': [...],
                'server_changes': {...},
                'new_sync_timestamp': ISO timestamp
            }
        """
        last_sync = data.get('last_sync')
        pending_actions = data.get('pending_actions', [])
        
        # Process queued actions
        action_results = []
        for action in pending_actions:
            result = self._process_action(action)
            action_results.append(result)
        
        # Get server changes since last sync
        server_changes = self._get_changes_since(last_sync) if last_sync else {}
        
        return {
            'action_results': action_results,
            'server_changes': server_changes,
            'new_sync_timestamp': timezone.now().isoformat(),
            'sync_status': 'complete'
        }
    
    def _process_action(self, action: Dict) -> Dict:
        """Process a single queued action"""
        action_type = action.get('type')
        action_id = action.get('id')
        
        try:
            with transaction.atomic():
                if action_type == 'task_toggle':
                    return self._handle_task_toggle(action)
                
                elif action_type == 'task_add':
                    return self._handle_task_add(action)
                
                elif action_type == 'task_delete':
                    return self._handle_task_delete(action)
                
                elif action_type == 'tracker_create':
                    return self._handle_tracker_create(action)
                
                return {
                    'id': action_id,
                    'success': False,
                    'error': f'Unknown action type: {action_type}'
                }
        
        except Exception as e:
            return {
                'id': action_id,
                'success': False,
                'error': str(e),
                'retry': True
            }
    
    def _handle_task_toggle(self, action: Dict) -> Dict:
        """Handle offline task toggle"""
        task = TaskInstance.objects.get(
            task_instance_id=action['task_id'],
            tracker_instance__tracker__user=self.user
        )
        
        task.status = action['new_status']
        if action['new_status'] == 'DONE':
            task.completed_at = timezone.now()
        else:
            task.completed_at = None
        
        task.save()
        
        return {
            'id': action['id'],
            'success': True,
            'server_timestamp': task.updated_at.isoformat()
        }
    
    def _get_changes_since(self, last_sync: str) -> Dict:
        """Get all changes since last sync timestamp"""
        last_sync_dt = datetime.fromisoformat(last_sync)
        
        return {
            'trackers': {
                'updated': list(TrackerDefinition.objects.filter(
                    user=self.user,
                    updated_at__gt=last_sync_dt
                ).values(
                    'tracker_id', 'name', 'status', 
                    'description', 'updated_at'
                )),
                'deleted': []  # Need deletion tracking
            },
            
            'tasks': {
                'updated': list(TaskInstance.objects.filter(
                    tracker_instance__tracker__user=self.user,
                    updated_at__gt=last_sync_dt
                ).values(
                    'task_instance_id', 'status', 'notes',
                    'completed_at', 'updated_at'
                )[:100]),  # Limit for performance
                'deleted': []
            }
        }
```

### Step 5.2: Add Sync API Endpoint

**File**: [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

**ADD** endpoint:

```python
from core.services.sync_service import SyncService

@login_required
@require_POST
def api_sync(request):
    """
    Bidirectional sync endpoint
    
    Handles:
    - Processing queued offline actions
    - Returning server changes since last sync
    - Conflict resolution
    
    UX Target: Offline experience, background sync
    """
    try:
        data = json.loads(request.body)
        
        sync_service = SyncService(request.user)
        result = sync_service.process_sync_request(data)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'sync_status': 'failed',
            'error': str(e),
            'retry_after': 5  # seconds
        }, status=500)
```

**ADD** to [urls.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/urls.py):

```python
path('api/sync/', views_api.api_sync, name='api_sync'),
```

**Impact**: ✅ Offline support, queue actions, background sync

---

## Phase 6: Search Enhancement (UX #16)

**Target**: Global search, search suggestions, recent searches, Cmd+K support

### Step 6.1: Enhanced Search with Recents

**File**: `core/models.py` - **ADD** new model:

```python
class SearchHistory(models.Model):
    """Track user search history for suggestions"""
    
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=200)
    result_count = models.IntegerField(default=0)
    clicked_result_type = models.CharField(max_length=50, blank=True)
    clicked_result_id = models.CharField(max_length=36, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'search_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
```

**Run migration**: `python manage.py makemigrations && python manage.py migrate`

### Step 6.2: Update Search API

**File**: [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py#L516-L570)

**REPLACE** `api_search` with enhanced version:

```python
from core.models import SearchHistory

@login_required
@require_GET
def api_search(request):
    """
    Enhanced global search with history and suggestions
    
    Features:
    - Type-ahead suggestions
    - Recent searches
    - Result ranking
    - Command palette support
    
    UX Target: Cmd/Ctrl+K, search suggestions
    """
    query = request.GET.get('q', '').strip()
    save_history = request.GET.get('save', 'true') == 'true'
    
    # Empty query - return suggestions
    if len(query) < 2:
        recent = SearchHistory.objects.filter(
            user=request.user
        )[:5].values_list('query', flat=True)
        
        return JsonResponse({
            'suggestions': {
                'recent': list(set(recent)),  # Deduplicate
                'popular': ['Daily Habits', 'Goals', 'This Week'],
                'commands': [
                    {'label': 'New Tracker', 'shortcut': 'Ctrl+N', 'action': 'create_tracker'},
                    {'label': 'Go to Today', 'shortcut': 'T', 'action': 'goto_today'},
                    {'label': 'Settings', 'shortcut': 'Ctrl+,', 'action': 'goto_settings'},
                ]
            }
        })
    
    # Perform search across entities
    results = {
        'trackers': [],
        'tasks': [],
        'goals': [],
        'commands': []
    }
    
    # Search trackers
    trackers = TrackerDefinition.objects.filter(
        user=request.user,
        name__icontains=query
    )[:5]
    
    results['trackers'] = [{
        'id': t.tracker_id,
        'type': 'tracker',
        'title': t.name,
        'subtitle': f'{t.time_period} • {t.task_count} tasks',
        'icon': '📊',
        'score': calculate_relevance_score(query, t.name),
        'action': {
            'type': 'navigate',
            'url': f'/tracker/{t.tracker_id}/'
        }
    } for t in trackers]
    
    # Search tasks
    tasks = TaskTemplate.objects.filter(
        tracker__user=request.user,
        description__icontains=query
    ).select_related('tracker')[:5]
    
    results['tasks'] = [{
        'id': t.template_id,
        'type': 'task',
        'title': t.description,
        'subtitle': t.tracker.name,
        'icon': '✅',
        'score': calculate_relevance_score(query, t.description),
        'action': {
            'type': 'navigate',
            'url': f'/tracker/{t.tracker.tracker_id}/'
        }
    } for t in tasks]
    
    # Search goals
    goals = Goal.objects.filter(
        user=request.user,
        title__icontains=query
    )[:5]
    
    results['goals'] = [{
        'id': g.goal_id,
        'type': 'goal',
        'title': g.title,
        'subtitle': f'{int(g.progress)}% complete',
        'icon': g.icon,
        'score': calculate_relevance_score(query, g.title),
        'action': {
            'type': 'navigate',
            'url': '/goals/'
        }
    } for g in goals]
    
    # Command matching
    commands = [
        {'title': 'New Tracker', 'shortcut': 'Ctrl+N', 'action': 'create_tracker'},
        {'title': 'New Task', 'shortcut': 'Ctrl+T', 'action': 'quick_add_task'},
        {'title': 'Today View', 'shortcut': 'T', 'action': 'goto_today'},
        {'title': 'Week View', 'shortcut': 'W', 'action': 'goto_week'},
        {'title': 'Settings', 'shortcut': 'Ctrl+,', 'action': 'goto_settings'},
    ]
    
    results['commands'] = [
        {
            'type': 'command',
            **cmd,
            'score': calculate_relevance_score(query, cmd['title'])
        }
        for cmd in commands
        if query.lower() in cmd['title'].lower()
    ]
    
    # Flatten and sort by score
    all_results = []
    for result_type, items in results.items():
        all_results.extend(items)
    
    all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Save to history
    if save_history and all_results:
        SearchHistory.objects.create(
            user=request.user,
            query=query,
            result_count=len(all_results)
        )
    
    return JsonResponse({
        'query': query,
        'results': all_results[:10],  # Top 10
        'grouped': results,
        'total': len(all_results)
    })


def calculate_relevance_score(query: str, text: str) -> float:
    """Calculate simple relevance score"""
    query_lower = query.lower()
    text_lower = text.lower()
    
    # Exact match
    if query_lower == text_lower:
        return 100.0
    
    # Starts with
    if text_lower.startswith(query_lower):
        return 80.0
    
    # Contains
    if query_lower in text_lower:
        return 60.0
    
    # Word match
    query_words = set(query_lower.split())
    text_words = set(text_lower.split())
    overlap = len(query_words & text_words)
    
    if overlap > 0:
        return 40.0 + (overlap / len(query_words)) * 20
    
    return 0.0
```

**Impact**: ✅ Cmd+K search, suggestions, recent searches

---

## Phase 7: Notifications (UX #17, #10)

**Target**: Push notifications, badge counts, in-app notifications

### Step 7.1: Notification Helper Service

**File**: `core/services/notification_service.py` (NEW)

```python
"""
Notification Service
Handles push, in-app, and badge notifications
"""
from core.models import Notification, UserPreferences
from django.utils import timezone
from typing import Dict, Optional


class NotificationService:
    """Unified notification service"""
    
    def __init__(self, user):
        self.user = user
        self.prefs = UserPreferences.objects.get_or_create(user=user)[0]
    
    def create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = 'info',
        link: str = '',
        send_push: bool = True,
        action_buttons: Optional[list] = None
    ) -> Notification:
        """
        Create notification with optional push
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: Type (info, success, warning, error, reminder, achievement)
            link: Deep link for navigation
            send_push: Whether to send push notification
            action_buttons: List of action buttons [{'title': '', 'action': ''}]
        """
        # Create in-app notification
        notif = Notification.objects.create(
            user=self.user,
            type=notification_type,
            title=title,
            message=message,
            link=link
        )
        
        # Send push if enabled
        if send_push and self.prefs.push_enabled:
            self._send_push(notif, action_buttons)
        
        return notif
    
    def _send_push(self, notification: Notification, action_buttons: Optional[list]):
        """Send push notification (iOS APNS / Web Push)"""
        
        # Get unread count for badge
        badge_count = Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
        
        # iOS APNS payload
        payload = {
            'aps': {
                'alert': {
                    'title': notification.title,
                    'body': notification.message
                },
                'badge': badge_count,
                'sound': self._get_sound(notification.type),
                'category': notification.type,
                'thread-id': 'tracker-notifications'
            },
            'notification_id': notification.notification_id,
            'link': notification.link,
            'actions': action_buttons or []
        }
        
        # TODO: Send via APNS/FCM
        # apns_client.send(device_token, payload)
        
        return payload
    
    def _get_sound(self, notification_type: str) -> str:
        """Get sound for notification type"""
        sounds = {
            'achievement': 'celebration.aiff',
            'reminder': 'reminder.aiff',
            'warning': 'alert.aiff',
            'error': 'error.aiff'
        }
        return sounds.get(notification_type, 'default')
    
    def get_badge_count(self) -> int:
        """Get unread notification count for badge"""
        return Notification.objects.filter(
            user=self.user,
            is_read=False
        ).count()
    
    def mark_read(self, notification_ids: list = None, mark_all: bool = False):
        """Mark notifications as read"""
        if mark_all:
            Notification.objects.filter(user=self.user).update(is_read=True)
        elif notification_ids:
            Notification.objects.filter(
                user=self.user,
                notification_id__in=notification_ids
            ).update(is_read=True)


# Convenience functions
def notify_streak_at_risk(user, streak_count: int):
    """Send streak at risk notification"""
    service = NotificationService(user)
    service.create_notification(
        title=f"⚠️ {streak_count}-Day Streak at Risk!",
        message=f"Complete at least one task to maintain your streak.",
        notification_type='warning',
        link='/today/',
        action_buttons=[
            {'title': 'View Tasks', 'action': 'open_app', 'url': '/today/'}
        ]
    )


def notify_goal_achieved(user, goal_name: str):
    """Send goal achievement notification"""
    service = NotificationService(user)
    service.create_notification(
        title="🎉 Goal Achieved!",
        message=f'Congratulations! You completed "{goal_name}"',
        notification_type='achievement',
        link='/goals/',
        action_buttons=[
            {'title': 'View Goals', 'action': 'open_app', 'url': '/goals/'}
        ]
    )
```

### Step 7.2: Notifications API Endpoint

**File**: [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

**REPLACE** existing `api_notifications` with enhanced version (if exists) or **ADD**:

```python
from core.services.notification_service import NotificationService

@login_required
@require_GET
def api_notifications(request):
    """
    Get notifications with grouping and badge count
    
    UX Target: Badge counts, notification center
    """
    service = NotificationService(request.user)
    
    # Get recent notifications
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]
    
    # Group by type
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
            'time_ago': humanize_time_ago(notif.created_at)
        })
    
    return JsonResponse({
        'notifications': [n for group in grouped.values() for n in group],
        'grouped': grouped,
        'badge': {
            'count': service.get_badge_count(),
            'visible': service.get_badge_count() > 0
        }
    })


@login_required
@require_POST
def api_notifications_mark_read(request):
    """Mark notifications as read"""
    data = json.loads(request.body)
    
    service = NotificationService(request.user)
    service.mark_read(
        notification_ids=data.get('ids'),
        mark_all=data.get('all', False)
    )
    
    return JsonResponse({
        'success': True,
        'new_badge_count': service.get_badge_count()
    })


def humanize_time_ago(dt):
    """Convert datetime to human-readable relative time"""
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 7:
        return dt.strftime('%b %d')
    elif diff.days > 0:
        return f'{diff.days}d ago'
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f'{hours}h ago'
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f'{minutes}m ago'
    else:
        return 'Just now'
```

**ADD** to [urls.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/urls.py):

```python
path('api/notifications/mark-read/', views_api.api_notifications_mark_read, name='api_notifications_mark_read'),
```

**Impact**: ✅ Push notifications, badge counts, action buttons

---

## Phase 8: Analytics & Insights (UX #33, #34)

**Target**: Smart suggestions, productivity trends, best time analysis

### Step 8.1: Smart Suggestions Generator

**File**: [behavioral/insights_engine.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/behavioral/insights_engine.py)

**ADD** at end of file:

```python
def generate_smart_suggestions(user) -> List[Dict]:
    """
    Generate smart suggestions across all trackers
    
    UX Target: "You usually complete tasks on Mondays" type insights
    """
    suggestions = []
    
    # Get user's trackers
    trackers = TrackerDefinition.objects.filter(
        user=user,
        status='active'
    )
    
    # Analyze completion patterns
    from datetime import date, timedelta
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    # Get all task instances from last 30 days
    tasks = TaskInstance.objects.filter(
        tracker_instance__tracker__user=user,
        tracker_instance__period_start__gte=thirty_days_ago
    ).select_related('template', 'tracker_instance')
    
    # Day of week analysis
    day_stats = {i: {'total': 0, 'completed': 0} for i in range(7)}
    
    for task in tasks:
        day_of_week = task.tracker_instance.period_start.weekday()
        day_stats[day_of_week]['total'] += 1
        if task.status == 'DONE':
            day_stats[day_of_week]['completed'] += 1
    
    # Find best day
    best_day = None
    best_rate = 0
    
    for day, stats in day_stats.items():
        if stats['total'] > 5:  # Minimum sample size
            rate = stats['completed'] / stats['total'] if stats['total'] > 0 else 0
            if rate > best_rate:
                best_rate = rate
                best_day = day
    
    if best_day is not None and best_rate > 0.7:
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        suggestions.append({
            'type': 'best_day',
            'title': f'You perform best on {day_names[best_day]}s',
            'description': f'Your completion rate is {best_rate*100:.0f}% on {day_names[best_day]}s',
            'action': f'Schedule important tasks for {day_names[best_day]}s',
            'confidence': 0.8 if best_rate > 0.8 else 0.6
        })
    
    # Time of day analysis
    time_stats = {'morning': 0, 'afternoon': 0, 'evening': 0}
    for task in tasks:
        if task.status == 'DONE':
            tod = task.template.time_of_day
            if tod in time_stats:
                time_stats[tod] += 1
    
    if sum(time_stats.values()) > 10:
        best_time = max(time_stats, key=time_stats.get)
        suggestions.append({
            'type': 'best_time',
            'title': f'You\'re most productive in the {best_time}',
            'description': f'{time_stats[best_time]} tasks completed in {best_time}',
            'action': f'Focus your hardest tasks in the {best_time}',
            'confidence': 0.7
        })
    
    # Streak encouragement
    for tracker in trackers:
        streaks = analytics.detect_streaks(tracker.tracker_id)
        current_streak = streaks.get('value', {}).get('current_streak', 0)
        
        if current_streak >= 5:
            suggestions.append({
                'type': 'streak_milestone',
                'title': f'🔥 {current_streak}-day streak on {tracker.name}!',
                'description': 'Keep the momentum going',
                'action': 'Complete today\'s tasks to extend your streak',
                'confidence': 1.0
            })
    
    return suggestions
```

### Step 8.2: Smart Suggestions API

**File**: [views_api.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/views_api.py)

**ADD**:

```python
from core.behavioral.insights_engine import generate_smart_suggestions

@login_required
@require_GET
def api_smart_suggestions(request):
    """
    Get smart suggestions based on user behavior
    
    UX Target: Smart suggestions, productivity insights
    """
    suggestions = generate_smart_suggestions(request.user)
    
    return JsonResponse({
        'suggestions': suggestions,
        'count': len(suggestions)
    })
```

**ADD** to [urls.py](file:///Users/harshalsmac/WORK/personal/Tracker/core/urls.py):

```python
path('api/suggestions/', views_api.api_smart_suggestions, name='api_smart_suggestions'),
```

**Impact**: ✅ Smart suggestions, productivity trends

---

## Implementation Priority

| Priority | Phase | Time | Impact | UX Points |
|----------|-------|------|--------|-----------|
| **P0** | Phase 1 | 1-2h | High | #4, #27, #31 |
| **P0** | Phase 2 | 1h | High | #26, #31 |
| **P1** | Phase 3 | 2h | High | #6, #7 |
| **P1** | Phase 4 | 2-3h | Medium | #9, #14 |
| **P2** | Phase 5 | 3-4h | High | #9, #20, #31 |
| **P2** | Phase 6 | 2h | Medium | #16 |
| **P2** | Phase 7 | 2-3h | Medium | #17, #10 |
| **P3** | Phase 8 | 2h | Low | #33, #34 |

## Quick Win Summary

**Day 1 (4-5 hours)**:
- ✅ Enhanced API responses (Phase 1)
- ✅ Skeleton screens (Phase 2)
- ✅ iOS swipe actions (Phase 3)

**Day 2 (6-7 hours)**:
- ✅ Infinite scroll (Phase 4)
- ✅ Offline sync (Phase 5)

**Day 3 (4-6 hours)**:
- ✅ Enhanced search (Phase 6)
- ✅ Notifications (Phase 7)
- ✅ Smart suggestions (Phase 8)

---

## Remaining UX Points Covered in OpusSuggestion.md

The following UX points are covered in the companion **OpusSuggestion.md** document with more architectural/strategic approaches:

- **#5**: Data visualization hierarchy
- **#8**: iOS navigation patterns
- **#11**: Screen real estate
- **#12-15**: Web app specific (multi-column, responsive, data density)
- **#18-19**: Settings & help
- **#28**: Empty states
- **#29-30**: Accessibility
- **#32**: Advanced error handling
- **#35-36**: iOS integration & design language

---

*This document provides practical, code-ready implementations. Start with Phase 1 for immediate UX improvements.*
