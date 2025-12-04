from django.urls import path
from . import views
from . import views_auth
from . import views_api
from . import views_spa

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
    path('api/tasks/bulk/', views_api.api_tasks_bulk, name='api_tasks_bulk'),
    
    # Tracker API
    path('api/tracker/<str:tracker_id>/task/add/', views_api.api_task_add, name='api_task_add'),
    path('api/tracker/<str:tracker_id>/reorder/', views_api.api_tracker_reorder, name='api_tracker_reorder'),
    path('api/tracker/create/', views_api.api_tracker_create, name='api_tracker_create'),
    path('api/tracker/<str:tracker_id>/delete/', views_api.api_tracker_delete, name='api_tracker_delete'),
    path('api/tracker/<str:tracker_id>/share/', views_api.api_share_tracker, name='api_share_tracker'),
    path('api/tracker/<str:tracker_id>/export/', views_api.api_export, name='api_export'),
    
    # Utility API
    path('api/search/', views_api.api_search, name='api_search'),
    path('api/notes/<str:date_str>/', views_api.api_day_note, name='api_day_note'),
    path('api/undo/', views_api.api_undo, name='api_undo'),
    path('api/validate/', views_api.api_validate_field, name='api_validate_field'),
    
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
    
    # =========================================================================
    # LEGACY API (kept for backwards compatibility)
    # =========================================================================
    path('api/tasks/bulk-update/', views.api_bulk_status_update, name='api_bulk_update'),
    path('api/tracker/<str:tracker_id>/mark-overdue/', views.api_mark_overdue_missed, name='api_mark_overdue'),
]
