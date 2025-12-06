"""
API v1 URL Configuration.

This module defines versioned API endpoints for backward compatibility
with iOS and other mobile clients.

All v1 endpoints are proxies to the main API views, ensuring:
- Stable URLs that won't change
- Clear versioning for mobile app updates
- Easy deprecation path for future versions
"""
from django.urls import path
from core import views_api, views_auth

app_name = 'api_v1'

urlpatterns = [
    # =========================================================================
    # TASK ENDPOINTS
    # =========================================================================
    path('task/<str:task_id>/toggle/', views_api.api_task_toggle, name='task_toggle'),
    path('task/<str:task_id>/status/', views_api.api_task_status, name='task_status'),
    path('task/<str:task_id>/edit/', views_api.api_task_edit, name='task_edit'),
    path('task/<str:task_id>/delete/', views_api.api_task_delete, name='task_delete'),
    path('tasks/bulk/', views_api.api_tasks_bulk, name='tasks_bulk'),
    
    # =========================================================================
    # TRACKER ENDPOINTS
    # =========================================================================
    path('tracker/<str:tracker_id>/task/add/', views_api.api_task_add, name='tracker_add_task'),
    path('tracker/<str:tracker_id>/reorder/', views_api.api_tracker_reorder, name='tracker_reorder'),
    path('tracker/create/', views_api.api_tracker_create, name='tracker_create'),
    path('tracker/<str:tracker_id>/delete/', views_api.api_tracker_delete, name='tracker_delete'),
    path('tracker/<str:tracker_id>/update/', views_api.api_tracker_update, name='tracker_update'),
    path('tracker/<str:tracker_id>/share/', views_api.api_share_tracker, name='tracker_share'),
    path('tracker/<str:tracker_id>/export/', views_api.api_export, name='tracker_export'),
    
    # =========================================================================
    # UTILITY ENDPOINTS
    # =========================================================================
    path('search/', views_api.api_search, name='search'),
    path('notes/<str:date_str>/', views_api.api_day_note, name='day_note'),
    path('undo/', views_api.api_undo, name='undo'),
    path('validate/', views_api.api_validate_field, name='validate_field'),
    
    # =========================================================================
    # ANALYTICS & INSIGHTS
    # =========================================================================
    path('insights/', views_api.api_insights, name='insights'),
    path('insights/<str:tracker_id>/', views_api.api_insights, name='insights_tracker'),
    path('chart-data/', views_api.api_chart_data, name='chart_data'),
    path('heatmap/', views_api.api_heatmap_data, name='heatmap'),
    
    # =========================================================================
    # BULK & MAINTENANCE
    # =========================================================================
    path('tasks/bulk-update/', views_api.api_bulk_status_update, name='bulk_update'),
    path('tracker/<str:tracker_id>/mark-overdue/', views_api.api_mark_overdue_missed, name='mark_overdue'),
    
    # =========================================================================
    # GOALS, PREFERENCES, NOTIFICATIONS
    # =========================================================================
    path('goals/', views_api.api_goals, name='goals'),
    path('preferences/', views_api.api_preferences, name='preferences'),
    path('notifications/', views_api.api_notifications, name='notifications'),
    
    # =========================================================================
    # UX OPTIMIZATION
    # =========================================================================
    path('prefetch/', views_api.api_prefetch, name='prefetch'),
    path('tasks/infinite/', views_api.api_tasks_infinite, name='tasks_infinite'),
    path('suggestions/', views_api.api_smart_suggestions, name='suggestions'),
    path('sync/', views_api.api_sync, name='sync'),
    
    # =========================================================================
    # SYSTEM
    # =========================================================================
    path('health/', views_api.api_health, name='health'),
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    path('auth/login/', views_auth.api_login, name='auth_login'),
    path('auth/signup/', views_auth.api_signup, name='auth_signup'),
    path('auth/logout/', views_auth.api_logout, name='auth_logout'),
    path('auth/status/', views_auth.api_check_auth, name='auth_status'),
    path('auth/validate-email/', views_auth.api_validate_email, name='auth_validate_email'),
]
