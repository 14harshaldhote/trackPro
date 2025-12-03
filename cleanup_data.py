"""
Script to clean up test data from Excel database.
Removes all existing data to start fresh.
"""
import os
import sys
from pathlib import Path

# Add project to path
sys.path.append('/Users/harshalsmac/WORK/personal/Tracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackerWeb.settings')

import django
django.setup()

from django.conf import settings
from core.db_engine import ExcelDB
import pandas as pd

def cleanup_database():
    """Remove all data from Excel database."""
    db = ExcelDB()
    
    print("🧹 Cleaning up database...")
    
    # Get all sheets
    sheets_to_clean = [
        'TrackerDefinitions',
        'TaskTemplates',
        'TrackerInstances',
        'TaskInstances',
        'DayNotes',
        'AuditLogs',
        'Quarantine'
    ]
    
    for sheet_name in sheets_to_clean:
        try:
            # Fetch all records
            records = db.fetch_all(sheet_name)
            count = len(records)
            
            # Clear by creating empty DataFrame with correct columns
            empty_df = pd.DataFrame(columns=db.SHEETS[sheet_name])
            
            with db.lock:
                wb = db._load_workbook()
                ws = wb[sheet_name]
                
                # Clear all rows except header
                ws.delete_rows(2, ws.max_row)
                
                db._safe_save(wb)
            
            # Clear cache
            if sheet_name in db._cache:
                del db._cache[sheet_name]
            if sheet_name in db._indices:
                del db._indices[sheet_name]
            
            print(f"  ✅ Cleaned {sheet_name}: Removed {count} records")
        except Exception as e:
            print(f"  ⚠️  {sheet_name}: {e}")
    
    print("\n✨ Database cleanup complete!")
    print(f"📁 File location: {db.file_path}")
    print("\n💡 Database is now empty and ready for fresh data.")

if __name__ == '__main__':
    confirm = input("⚠️  This will DELETE ALL data from the Excel database. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        cleanup_database()
    else:
        print("❌ Cleanup cancelled.")
