from django.urls import path
from . import views_auth
from . import views_api
from . import views_spa
from . import views_ios

urlpatterns = [
    # =========================================================================
    # SPA ROUTES - Main entry point and panel endpoints
    # =========================================================================
    
    # Main SPA shell (entry point)
    path('', views_spa.spa_shell, name='dashboard'),
    path('app/', views_spa.spa_shell, name='spa_shell'),
    
    # Panel endpoints (return HTML fragments for AJAX)
    path('panels/dashboard/', views_spa.panel_dashboard, name='panel_dashboard'),
    path('panels/today/', views_spa.panel_today, name='panel_today'),
    path('panels/trackers/', views_spa.panel_trackers_list, name='panel_trackers'),
    path('panels/tracker/<str:tracker_id>/', views_spa.panel_tracker_detail, name='panel_tracker_detail'),
    path('panels/week/', views_spa.panel_week, name='panel_week'),
    path('panels/month/', views_spa.panel_month, name='panel_month'),
    path('panels/analytics/', views_spa.panel_analytics, name='panel_analytics'),
    path('panels/goals/', views_spa.panel_goals, name='panel_goals'),
    path('panels/insights/', views_spa.panel_insights, name='panel_insights'),
    path('panels/help/', views_spa.panel_help, name='panel_help'),
    path('panels/templates/', views_spa.panel_templates, name='panel_templates'),
    path('panels/settings/', views_spa.panel_settings, name='panel_settings'),
    path('panels/settings/<str:section>/', views_spa.panel_settings, name='panel_settings_section'),
    
    # Modals
    path('modals/<str:modal_name>/', views_spa.modal_view, name='modal_view'),
    
    # Error panels
    path('panels/error/404/', views_spa.panel_error_404, name='panel_error_404'),
    path('panels/error/500/', views_spa.panel_error_500, name='panel_error_500'),
    
    # =========================================================================
    # LEGACY ROUTES - Redirect to SPA
    # =========================================================================
    path('trackers/', views_spa.spa_shell, name='tracker_list'),
    path('tracker/<str:tracker_id>/', views_spa.spa_shell, name='tracker_detail'),
    path('today/', views_spa.spa_shell, name='today_view'),
    path('week/', views_spa.spa_shell, name='week_view'),
    path('analytics/', views_spa.spa_shell, name='analytics_dashboard'),
    path('goals/', views_spa.spa_shell, name='goals'),
    path('insights/', views_spa.spa_shell, name='insights'),
    path('templates/', views_spa.spa_shell, name='templates'),
    path('help/', views_spa.spa_shell, name='help_center'),
    path('settings/', views_spa.spa_shell, name='settings'),
    
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
    
    # =========================================================================
    # UX-OPTIMIZED ENDPOINTS (Following OpusSuggestion.md)
    # =========================================================================
    
    # SPA Navigation & Performance
    path('api/prefetch/', views_api.api_prefetch, name='api_prefetch'),
    path('api/tasks/infinite/', views_api.api_tasks_infinite, name='api_tasks_infinite'),
    
    # Offline Sync
    path('api/sync/', views_api.api_sync, name='api_sync'),
    
    # Enhanced Notifications
    path('api/notifications/enhanced/', views_api.api_notifications_enhanced, name='api_notifications_enhanced'),
    path('api/notifications/mark-read/', views_api.api_notifications_mark_read, name='api_notifications_mark_read'),
    
    # Behavioral Insights
    path('api/smart-suggestions/', views_api.api_smart_suggestions, name='api_smart_suggestions'),
    path('api/action-metadata/', views_api.api_action_metadata, name='api_action_metadata'),
    
    # =========================================================================
    # iOS INTEGRATION - Widgets & Siri Shortcuts (UX #35-36)
    # =========================================================================
    
    # Widget Timeline Endpoints
    path('api/ios/widget/today/', views_ios.widget_today, name='ios_widget_today'),
    path('api/ios/widget/timeline/', views_ios.widget_timeline, name='ios_widget_timeline'),
    
    # Siri Shortcuts Intent Endpoints - Basic
    path('api/ios/siri/complete-task/', views_ios.siri_complete_task, name='ios_siri_complete_task'),
    path('api/ios/siri/add-task/', views_ios.siri_add_task, name='ios_siri_add_task'),
    path('api/ios/siri/today-summary/', views_ios.siri_today_summary, name='ios_siri_today_summary'),
    path('api/ios/siri/streak/', views_ios.siri_streak, name='ios_siri_streak'),
    
    # Siri Shortcuts Intent Endpoints - Extended
    path('api/ios/siri/tracker-progress/', views_ios.siri_tracker_progress, name='ios_siri_tracker_progress'),
    path('api/ios/siri/weekly-summary/', views_ios.siri_weekly_summary, name='ios_siri_weekly_summary'),
    path('api/ios/siri/monthly-summary/', views_ios.siri_monthly_summary, name='ios_siri_monthly_summary'),
    path('api/ios/siri/completion-rate/', views_ios.siri_completion_rate, name='ios_siri_completion_rate'),
    path('api/ios/siri/whats-next/', views_ios.siri_whats_next, name='ios_siri_whats_next'),
    path('api/ios/siri/skip-all-remaining/', views_ios.siri_skip_all_remaining, name='ios_siri_skip_all_remaining'),
    path('api/ios/siri/my-goals/', views_ios.siri_my_goals, name='ios_siri_my_goals'),
    path('api/ios/siri/best-day/', views_ios.siri_best_day, name='ios_siri_best_day'),
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    path('api/auth/login/', views_auth.api_login, name='api_login'),
    path('api/auth/signup/', views_auth.api_signup, name='api_signup'),
    path('api/auth/logout/', views_auth.api_logout, name='api_logout'),
    path('api/auth/status/', views_auth.api_check_auth, name='api_check_auth'),
    path('api/auth/validate-email/', views_auth.api_validate_email, name='api_validate_email'),
    
    # Auth Pages (custom templates)
    path('login/', views_auth.login_page, name='account_login'),
    path('signup/', views_auth.signup_page, name='account_signup'),
    path('forgot-password/', views_auth.forgot_password, name='forgot_password'),
    path('logout/', views_auth.api_logout, name='logout'),
]

