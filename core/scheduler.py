from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from core import services
import atexit

def start_scheduler():
    scheduler = BackgroundScheduler()
    # We don't necessarily need DjangoJobStore if we are just running in-memory for this local app,
    # but it's good practice if we wanted persistence. 
    # For this "Excel DB" project, let's keep it simple and in-memory.
    
    # Run check_all_trackers every hour
    scheduler.add_job(services.check_all_trackers, 'interval', minutes=60, id='check_trackers_hourly', replace_existing=True)

    # Run integrity check every 24 hours (midnight)
    from core.integrity import IntegrityService
    integrity_service = IntegrityService()
    scheduler.add_job(integrity_service.run_integrity_check, 'cron', hour=0, minute=0, id='integrity_check_daily', replace_existing=True)
    
    # Also run it once on startup (we can call this manually in apps.py)
    
    scheduler.start()
    print("⏰ Scheduler started!")
    
    atexit.register(lambda: scheduler.shutdown())
