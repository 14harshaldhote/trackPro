from django.urls import path, include
from django.shortcuts import redirect
from django.http import JsonResponse
from . import views_auth
from . import views_api
from . import urls_api_v1


def root_redirect(request):
    """
    Handle root URL based on client type and auth status.
    
    - API clients (Accept: application/json): Return JSON with API info
    - Browser clients (authenticated): Redirect to /login/ (no web dashboard yet)
    - Browser clients (unauthenticated): Redirect to login page
    """
    # Check if this is an API request
    accept = request.META.get('HTTP_ACCEPT', '')
    if 'application/json' in accept:
        return JsonResponse({
            'success': True,
            'message': 'Tracker Pro API',
            'version': '1.0',
            'endpoints': {
                'api_v1': '/api/v1/',
                'health': '/api/v1/health/',
                'auth': '/api/v1/auth/',
                'docs': '/docs/'  # Future: API documentation
            },
            'authenticated': request.user.is_authenticated
        })
    
    # Browser redirect
    return redirect('/login/')


urlpatterns = [
    # Root URL redirect
    path('', root_redirect, name='root'),
    
    # =========================================================================
    # API ENDPOINTS
    # =========================================================================
    
    # Task API
    path('api/task/<str:task_id>/toggle/', views_api.api_task_toggle, name='api_toggle_task'),
    path('api/task/<str:task_id>/status/', views_api.api_task_status, name='api_task_status'),
    path('api/task/<str:task_id>/edit/', views_api.api_task_edit, name='api_task_edit'),
    path('api/task/<str:task_id>/delete/', views_api.api_task_delete, name='api_task_delete'),
    path('api/tasks/bulk/', views_api.api_tasks_bulk, name='api_tasks_bulk'),
    
    # Tracker API
    path('api/tracker/<str:tracker_id>/task/add/', views_api.api_task_add, name='api_task_add'),
    path('api/tracker/<str:tracker_id>/reorder/', views_api.api_tracker_reorder, name='api_tracker_reorder'),
    path('api/tracker/create/', views_api.api_tracker_create, name='api_tracker_create'),
    path('api/tracker/<str:tracker_id>/delete/', views_api.api_tracker_delete, name='api_tracker_delete'),
    path('api/tracker/<str:tracker_id>/update/', views_api.api_tracker_update, name='api_tracker_update'),
    path('api/tracker/<str:tracker_id>/share/', views_api.api_share_tracker, name='api_share_tracker'),
    path('api/tracker/<str:tracker_id>/export/', views_api.api_export, name='api_export'),
    
    # Utility API
    path('api/search/', views_api.api_search, name='api_search'),
    path('api/notes/<str:date_str>/', views_api.api_day_note, name='api_day_note'),
    path('api/undo/', views_api.api_undo, name='api_undo'),
    path('api/validate/', views_api.api_validate_field, name='api_validate_field'),
    
    # Analytics & Insights API (NEW)
    path('api/insights/', views_api.api_insights, name='api_insights'),
    path('api/insights/<str:tracker_id>/', views_api.api_insights, name='api_insights_tracker'),
    path('api/chart-data/', views_api.api_chart_data, name='api_chart_data'),
    path('api/heatmap/', views_api.api_heatmap_data, name='api_heatmap_data'),
    
    # Bulk update and maintenance API (moved from legacy views.py)
    path('api/tasks/bulk-update/', views_api.api_bulk_status_update, name='api_bulk_update'),
    path('api/tracker/<str:tracker_id>/mark-overdue/', views_api.api_mark_overdue_missed, name='api_mark_overdue'),
    
    # Goals, Preferences, Notifications API (NEW)
    path('api/goals/', views_api.api_goals, name='api_goals'),
    path('api/preferences/', views_api.api_preferences, name='api_preferences'),
    path('api/notifications/', views_api.api_notifications, name='api_notifications'),
    
    # UX Optimization API (Phase 3)
    path('api/prefetch/', views_api.api_prefetch, name='api_prefetch'),
    path('api/tasks/infinite/', views_api.api_tasks_infinite, name='api_tasks_infinite'),
    path('api/suggestions/', views_api.api_smart_suggestions, name='api_smart_suggestions'),
    path('api/sync/', views_api.api_sync, name='api_sync'),
    
    # Health Check (no auth required)
    path('api/health/', views_api.api_health, name='api_health'),

    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    path('api/auth/login/', views_auth.api_login, name='api_login'),
    path('api/auth/signup/', views_auth.api_signup, name='api_signup'),
    path('api/auth/logout/', views_auth.api_logout, name='api_logout'),
    path('api/auth/status/', views_auth.api_check_auth, name='api_check_auth'),
    path('api/auth/validate-email/', views_auth.api_validate_email, name='api_validate_email'),
    path('api/auth/google/', views_auth.api_google_auth_mobile, name='api_google_auth_mobile'),
    
    # Auth Pages (custom templates)
    path('login/', views_auth.login_page, name='account_login'),
    path('signup/', views_auth.signup_page, name='account_signup'),
    path('forgot-password/', views_auth.forgot_password, name='forgot_password'),
    path('logout/', views_auth.api_logout, name='logout'),
    
    # =========================================================================
    # VERSIONED API (for iOS backward compatibility)
    # =========================================================================
    path('api/v1/', include((urls_api_v1.urlpatterns, 'api_v1'), namespace='api_v1')),
]

