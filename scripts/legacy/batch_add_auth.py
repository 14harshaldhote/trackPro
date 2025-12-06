"""
Batch script to add @login_required to all remaining views.
Adds decorators to views that don't have them yet.
"""
import re

VIEWS_FILE = '/Users/harshalsmac/WORK/personal/Tracker/core/views.py'

# Views that should have @login_required (excluding already done)
VIEWS_TO_UPDATE = [
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

def add_login_required_decorator(content, view_name):
    """Add @login_required before a view function"""
    pattern = rf'(^def {view_name}\(request)'
    replacement = r'@login_required\n\1'
    return re.sub(pattern, replacement, content, flags=re.MULTILINE)

def main():
    with open(VIEWS_FILE, 'r') as f:
        content = f.read()
    
    # Track changes
    changes_made = []
    
    for view in VIEWS_TO_UPDATE:
        # Check if decorator already exists
        if not re.search(rf'@login_required\s*\ndef {view}\(request', content):
            content = add_login_required_decorator(content, view)
            changes_made.append(view)
    
    # Write back
    with open(VIEWS_FILE, 'w') as f:
        f.write(content)
    
    print(f"✅ Added @login_required to {len(changes_made)} views:")
    for view in changes_made:
        print(f"   - {view}")

if __name__ == '__main__':
    main()
