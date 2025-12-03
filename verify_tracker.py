import os
import sys
import django
from datetime import date
import shutil

# Setup Django environment
sys.path.append('/Users/harshalsmac/WORK/personal/Tracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackerWeb.settings')
django.setup()

from core.db_engine import ExcelDB
from django.conf import settings

def test_db_engine():
    print("Testing ExcelDB Engine...")
    
    # Clean up previous test data
    db_path = os.path.join(settings.DATA_DIR, 'tracker.xlsx')
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing tracker.xlsx")
    
    db = ExcelDB()
    
    # Test 1: Get Day (should create new)
    today = date.today()
    print(f"Getting day for {today}...")
    data = db.get_day(today)
    assert data['day']['date'] == today.isoformat()
    print("✅ Day creation/retrieval passed")
    
    # Test 2: Add Task
    print("Adding task...")
    task_id = db.add_task(today.isoformat(), "Test Task", "work")
    print(f"Task added with ID: {task_id}")
    
    data = db.get_day(today)
    tasks = data['tasks']
    assert len(tasks) == 1
    assert tasks[0]['description'] == "Test Task"
    assert tasks[0]['status'] == "TODO"
    print("✅ Add task passed")
    
    # Test 3: Update Task
    print("Updating task...")
    success = db.update_task(task_id, status="DONE")
    assert success
    
    data = db.get_day(today)
    tasks = data['tasks']
    assert tasks[0]['status'] == "DONE"
    print("✅ Update task passed")
    
    print("🎉 All DB Engine tests passed!")

if __name__ == "__main__":
    test_db_engine()
