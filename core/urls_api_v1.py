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
    # DASHBOARD ENDPOINTS - Main app data
    # =========================================================================
    path('dashboard/', views_api.api_dashboard, name='dashboard'),
    path('dashboard/trackers/', views_api.api_dashboard_trackers, name='dashboard_trackers'),
    path('dashboard/today/', views_api.api_dashboard_today, name='dashboard_today'),
    path('dashboard/week/', views_api.api_dashboard_week, name='dashboard_week'),
    path('dashboard/goals/', views_api.api_dashboard_goals, name='dashboard_goals'),
    path('dashboard/streaks/', views_api.api_dashboard_streaks, name='dashboard_streaks'),
    path('dashboard/activity/', views_api.api_dashboard_activity, name='dashboard_activity'),
    path('trackers/', views_api.api_trackers_list, name='trackers_list'),
    path('tracker/<str:tracker_id>/', views_api.api_tracker_detail, name='tracker_detail'),
    
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
    path('templates/activate/', views_api.api_template_activate, name='template_activate'),
    
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
    # USER PROFILE & DATA MANAGEMENT
    # =========================================================================
    path('user/profile/', views_api.api_user_profile, name='user_profile'),
    path('user/avatar/', views_api.api_user_avatar, name='user_avatar'),
    path('user/delete/', views_api.api_user_delete, name='user_delete'),
    path('data/export/', views_api.api_data_export, name='data_export'),
    path('data/import/', views_api.api_data_import, name='data_import'),
    path('data/clear/', views_api.api_data_clear, name='data_clear'),
    
    # =========================================================================
    # ANALYTICS & EXPORT
    # =========================================================================
    path('analytics/data/', views_api.api_analytics_data, name='analytics_data'),
    path('analytics/forecast/', views_api.api_analytics_forecast, name='analytics_forecast'),
    path('export/month/', views_api.api_export_month, name='export_month'),
    
    # =========================================================================
    # UX OPTIMIZATION
    # =========================================================================
    path('prefetch/', views_api.api_prefetch, name='prefetch'),
    path('tasks/infinite/', views_api.api_tasks_infinite, name='tasks_infinite'),
    path('suggestions/', views_api.api_smart_suggestions, name='suggestions'),
    path('sync/', views_api.api_sync, name='sync'),
    
    # =========================================================================
    # POINTS & GOALS - Task Points and Tracker Goal Management
    # =========================================================================
    path('tracker/<str:tracker_id>/progress/', views_api.api_tracker_progress, name='tracker_progress'),
    path('tracker/<str:tracker_id>/goal/', views_api.api_tracker_goal, name='tracker_goal'),
    path('tracker/<str:tracker_id>/points-breakdown/', views_api.api_task_points_breakdown, name='tracker_points_breakdown'),
    path('task/<str:template_id>/toggle-goal/', views_api.api_toggle_task_goal, name='task_toggle_goal'),
    path('task/<str:template_id>/points/', views_api.api_update_task_points, name='task_update_points'),
    
    # =========================================================================
    # SYSTEM
    # =========================================================================
    path('feature-flags/<str:flag_name>/', views_api.api_feature_flag, name='feature_flag'),
    path('health/', views_api.api_health, name='health'),
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    path('auth/login/', views_auth.api_login, name='auth_login'),
    path('auth/signup/', views_auth.api_signup, name='auth_signup'),
    path('auth/logout/', views_auth.api_logout, name='auth_logout'),
    path('auth/status/', views_auth.api_check_auth, name='auth_status'),
    path('auth/validate-email/', views_auth.api_validate_email, name='auth_validate_email'),
    path('auth/google/', views_auth.api_google_auth_mobile, name='auth_google_mobile'),
    path('auth/apple/mobile/', views_auth.api_apple_auth_mobile, name='auth_apple_mobile'),
]
