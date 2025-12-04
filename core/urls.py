from django.urls import path
from . import views
from . import views_auth

urlpatterns = [
    # Main pages
    path('', views.dashboard, name='dashboard'),
    path('trackers/', views.tracker_list, name='tracker_list'),
    path('trackers/create/', views.create_tracker, name='create_tracker'),
    path('history/', views.history, name='history'),
    path('help/', views.help_center, name='help_center'),
    
    # Templates
    path('templates/', views.templates_library, name='templates_library'),
    
    # Tracker-specific pages
    path('tracker/<str:tracker_id>/', views.tracker_detail, name='tracker_detail'),
    path('tracker/<str:tracker_id>/delete/', views.delete_tracker, name='delete_tracker'),
    path('tracker/<str:tracker_id>/today/', views.today_view, name='today_view'),
    path('tracker/<str:tracker_id>/week/', views.week_view, name='week_view'),
    path('tracker/<str:tracker_id>/custom/', views.custom_range_view, name='custom_range'),
    path('tracker/<str:tracker_id>/monthly/', views.monthly_tracker, name='monthly_tracker'),
    path('tracker/<str:tracker_id>/insights/', views.insights_view, name='insights_view'),
    path('tracker/<str:tracker_id>/analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('tracker/<str:tracker_id>/behavior/', views.behavior_analysis, name='behavior_analysis'),
    path('tracker/<str:tracker_id>/correlations/', views.correlations, name='correlations'),
    path('tracker/<str:tracker_id>/forecast/', views.forecast_view, name='forecast_view'),
    path('tracker/<str:tracker_id>/export/', views.export_center, name='export_center'),
    path('tracker/<str:tracker_id>/journey/', views.my_journey, name='my_journey'),
    
    # Task Management
    path('tracker/<str:tracker_id>/tasks/', views.manage_tasks, name='manage_tasks'),
    path('tracker/<str:tracker_id>/tasks/add/', views.add_task, name='add_task'),
    path('tracker/<str:tracker_id>/apply-template/', views.apply_template, name='apply_template'),
    path('tracker/<str:tracker_id>/save-template/', views.save_as_template, name='save_as_template'),
    path('task/<str:template_id>/edit/', views.edit_task, name='edit_task'),
    path('task/<str:template_id>/delete/', views.delete_task, name='delete_task'),
    path('task/<str:template_id>/duplicate/', views.duplicate_task, name='duplicate_task'),
    
    # API endpoints
    path('api/task/<str:task_id>/toggle/', views.api_toggle_task, name='api_toggle_task'),
    path('api/tasks/bulk-update/', views.api_bulk_status_update, name='api_bulk_update'),
    path('api/tracker/<str:tracker_id>/mark-overdue/', views.api_mark_overdue_missed, name='api_mark_overdue'),
    
    # Authentication API
    path('api/auth/login/', views_auth.api_login, name='api_login'),
    path('api/auth/signup/', views_auth.api_signup, name='api_signup'),
    path('api/auth/logout/', views_auth.api_logout, name='api_logout'),
    path('api/auth/status/', views_auth.api_check_auth, name='api_check_auth'),
    path('api/auth/validate-email/', views_auth.api_validate_email, name='api_validate_email'),
    
    # Standard Logout (for non-AJAX fallbacks)
    path('logout/', views_auth.api_logout, name='logout'),
]
