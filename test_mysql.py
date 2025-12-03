#!/usr/bin/env python
"""
Test script to verify MySQL migration is working correctly.
Creates sample data and tests CRUD operations.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackerWeb.settings')
django.setup()

from core import crud
from datetime import date, timedelta
import uuid

def test_mysql_migration():
    """Test MySQL database with sample data"""
    
    print("="*60)
    print("TESTING MYSQL MIGRATION")
    print("="*60)
    
    # Test 1: Create Tracker
    print("\n1. Creating test tracker...")
    tracker_data = {
        'name': 'MySQL Test Tracker',
        'description': 'Testing MySQL migration',
        'time_mode': 'daily',
    }
    tracker = crud.create_tracker_definition(tracker_data)
    print(f"✓ Created tracker: {tracker['name']} (ID: {tracker['tracker_id']})")
    
    # Test 2: Create Task Templates
    print("\n2. Creating task templates...")
    tasks = ['Exercise', 'Meditate', 'Read', 'Code']
    templates = []
    
    for task_desc in tasks:
        task_data = {
            'tracker_id': tracker['tracker_id'],
            'description': task_desc,
            'is_recurring': True,
            'category': 'wellness' if task_desc in ['Exercise', 'Meditate'] else 'productivity',
            'weight': 1,
        }
        template = crud.create_task_template(task_data)
        templates.append(template)
        print(f"✓ Created template: {template['description']}")
    
    # Test 3: Create Tracker Instance for Today
    print("\n3. Creating tracker instance for today...")
    today = date.today()
    instance_data = {
        'tracker_id': tracker['tracker_id'],
        'tracking_date': today,
        'status': 'active',
    }
    instance = crud.create_tracker_instance(instance_data)
    print(f"✓ Created instance for {instance['tracking_date']}")
    
    # Test 4: Create Task Instances
    print("\n4. Creating task instances...")
    statuses = ['DONE', 'IN_PROGRESS', 'TODO', 'TODO']
    
    for i, template in enumerate(templates):
        task_instance_data = {
            'tracker_instance_id': instance['instance_id'],
            'template_id': template['template_id'],
            'status': statuses[i],
            'notes': f'Test note for {template["description"]}',
        }
        task_instance = crud.create_task_instance(task_instance_data)
        print(f"✓ Created task: {template['description']} - {statuses[i]}")
    
    # Test 5: Read Data
    print("\n5. Reading data back...")
    
    all_trackers = crud.get_all_tracker_definitions()
    print(f"✓ Found {len(all_trackers)} tracker(s)")
    
    tracker_templates = crud.get_task_templates_for_tracker(tracker['tracker_id'])
    print(f"✓ Found {len(tracker_templates)} template(s)")
    
    tracker_instances = crud.get_tracker_instances(tracker['tracker_id'])
    print(f"✓ Found {len(tracker_instances)} instance(s)")
    
    task_instances = crud.get_task_instances_for_tracker_instance(instance['instance_id'])
    print(f"✓ Found {len(task_instances)} task instance(s)")
    
    # Test 6: Update Task Status
    print("\n6. Testing status update...")
    task_to_update = task_instances[2]  # The TODO task
    updated_task = crud.update_task_instance_status(
        task_to_update['task_instance_id'], 
        'DONE'
    )
    print(f"✓ Updated task status from {task_to_update['status']} to {updated_task['status']}")
    
    # Test 7: Test db compatibility layer
    print("\n7. Testing db compatibility layer...")
    db_tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker['tracker_id'])
    print(f"✓ db.fetch_by_id works: {db_tracker['name']}")
    
    all_db_trackers = crud.db.fetch_all('TrackerDefinitions')
    print(f"✓ db.fetch_all works: Found {len(all_db_trackers)} tracker(s)")
    
    # Summary
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print(f"\nCreated:")
    print(f"  - 1 Tracker: {tracker['name']}")
    print(f"  - {len(templates)} Task Templates")
    print(f"  - 1 Tracker Instance ({today})")
    print(f"  - {len(task_instances)} Task Instances")
    print(f"\nMySQL migration is working correctly! 🎉")
    print(f"\nYou can now:")
    print(f"  1. Start the server: python manage.py runserver")
    print(f"  2. Visit http://127.0.0.1:8000")
    print(f"  3. Access Django Admin: http://127.0.0.1:8000/admin")
    print("="*60)
    

if __name__ == '__main__':
    try:
        test_mysql_migration()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
