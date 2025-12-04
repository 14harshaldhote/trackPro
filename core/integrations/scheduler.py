"""
Scheduler integration for Tracker Pro.

Handles periodic background tasks using APScheduler:
- Automatic tracker instance creation
- Data integrity checks
- Nightly analytics precomputation
- Scheduled maintenance tasks

Author: Tracker Pro Team 
"""
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import logging
from datetime import datetime

# Use new service locations
from core.services import instance_service
from core.integrations import integrity

logger = logging.getLogger(__name__)


def precompute_analytics():
    """
    Nightly job to precompute analytics for all trackers.
    
    Runs at 2 AM to:
    - Generate and cache all metrics
    - Generate insights
    - Clear stale cache entries
    
    This improves dashboard load times during the day.
    """
    from core.models import TrackerDefinition
    from core import analytics
    from core.behavioral import get_insights
    
    logger.info("🌙 Starting nightly analytics precomputation...")
    start_time = datetime.now()
    
    trackers = TrackerDefinition.objects.all()
    success_count = 0
    error_count = 0
    
    for tracker in trackers:
        try:
            tracker_id = str(tracker.tracker_id)
            
            # Precompute all core metrics (will cache automatically)
            analytics.compute_completion_rate(tracker_id)
            analytics.detect_streaks(tracker_id)
            analytics.compute_consistency_score(tracker_id)
            analytics.compute_balance_score(tracker_id)
            analytics.compute_effort_index(tracker_id)
            analytics.analyze_notes_sentiment(tracker_id)
            analytics.analyze_trends(tracker_id)
            
            # Generate insights
            get_insights(tracker_id)
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"Failed to precompute for tracker {tracker.tracker_id}: {e}")
            error_count += 1
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"✅ Analytics precomputation complete: "
        f"{success_count} successful, {error_count} errors, {elapsed:.1f}s elapsed"
    )


def start_scheduler():
    """
    Start the background scheduler for automated tasks.
    
    Schedules:
        - Tracker instance checks every hour
        - Data integrity checks daily at midnight
        - Analytics precomputation daily at 2 AM
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
    
    # Run nightly analytics precomputation at 2 AM
    scheduler.add_job(
        precompute_analytics,
        'cron',
        hour=2,
        minute=0,
        id='nightly_analytics_precompute',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("⏰ Scheduler started with 3 jobs: hourly checks, nightly integrity, nightly analytics")
    print("⏰ Scheduler started!")
    
    atexit.register(lambda: scheduler.shutdown())

