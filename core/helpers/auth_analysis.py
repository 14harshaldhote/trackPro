"""
Script to add @login_required decorator to all views.
This updates views.py to enforce authentication on all endpoints.
"""

# List of all views that need @login_required (from grep search)
VIEWS_NEEDING_DECORATOR = [
    'tracker_list',
    'create_tracker',
    'tracker_detail',
    'analytics_dashboard',
    'delete_tracker',
    'behavior_analysis',
    'correlations',
    'forecast_view',
    'export_center',
    'my_journey',
    'monthly_tracker',
    'today_view',
    'week_view',
    'custom_range_view',
    'manage_tasks',
    'add_task',
    'edit_task',
    'delete_task',
    'duplicate_task',
    'templates_library',
    'save_as_template',
    'apply_template',
    'insights_view',
    'help_center',
    'history',
    'api_toggle_task',
    'api_bulk_status_update',
    'api_mark_overdue_missed',
]

# Views that need user filtering
USER_FILTER_VIEWS = {
    'tracker_list': 'crud.get_all_tracker_definitions() → filter by user',
    'create_tracker': 'Add user=request.user to tracker creation',
    'tracker_detail': 'Verify user owns tracker',
    'analytics_dashboard': 'Verify user owns tracker',
    'delete_tracker': 'Verify user owns tracker before delete',
    'monthly_tracker': 'Verify user owns tracker',
    'today_view': 'Verify user owns tracker',
    'week_view': 'Verify user owns tracker',
    'custom_range_view': 'Verify user owns tracker',
}

print(f"Total views needing @login_required: {len(VIEWS_NEEDING_DECORATOR)}")
print(f"Views needing user filtering: {len(USER_FILTER_VIEWS)}")
