"""
Scheduler integration for Tracker Pro.

Handles periodic background tasks using APScheduler:
- Automatic tracker instance creation
- Data integrity checks
- Scheduled maintenance tasks

Author: Tracker Pro Team 
"""
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Use new service location
from core.services import instance_service
from core.integrations import integrity


def start_scheduler():
    """
    Start the background scheduler for automated tasks.
    
    Schedules:
        - Tracker instance checks every hour
        - Data integrity checks daily at midnight
    """
    scheduler = BackgroundScheduler()
    
    # Run check_all_trackers every hour
    scheduler.add_job(
        instance_service.check_all_trackers, 
        'interval', 
        minutes=60, 
        id='check_trackers_hourly', 
        replace_existing=True
    )

    # Run integrity check every 24 hours (midnight)
    integrity_svc = integrity.IntegrityService()
    scheduler.add_job(
        integrity_svc.run_integrity_check, 
        'cron', 
        hour=0, 
        minute=0, 
        id='integrity_check_daily', 
        replace_existing=True
    )
    
    scheduler.start()
    print("⏰ Scheduler started!")
    
    atexit.register(lambda: scheduler.shutdown())
