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
from django.core.cache import cache
from functools import wraps
import atexit
import logging
from datetime import datetime

# Use new service locations
from core.services import instance_service
from core.integrations import integrity

logger = logging.getLogger(__name__)


# ============================================================================
# JOB LOCKING
# ============================================================================

def with_lock(lock_name: str, lock_timeout: int = 3600):
    """
    Decorator to prevent duplicate job execution using cache-based locking.
    
    Args:
        lock_name: Unique name for the lock
        lock_timeout: Lock timeout in seconds (default: 1 hour)
        
    This prevents the same job from running concurrently in multi-process
    deployments (e.g., gunicorn with multiple workers).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lock_key = f"scheduler_lock:{lock_name}"
            
            # Try to acquire lock
            acquired = cache.add(lock_key, "locked", lock_timeout)
            
            if not acquired:
                logger.warning(f"Job '{lock_name}' is already running, skipping...")
                return None
            
            try:
                return func(*args, **kwargs)
            finally:
                # Release lock
                cache.delete(lock_key)
        
        return wrapper
    return decorator


# ============================================================================
# SCHEDULED JOBS
# ============================================================================

@with_lock('nightly_analytics', lock_timeout=7200)  # 2 hour lock
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
    
    trackers = TrackerDefinition.objects.filter(deleted_at__isnull=True)
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


@with_lock('hourly_tracker_check', lock_timeout=3600)
def check_trackers_locked():
    """Wrapper to add locking to instance checks."""
    return instance_service.check_all_trackers()


@with_lock('integrity_check', lock_timeout=3600)
def run_integrity_locked():
    """Wrapper to add locking to integrity checks."""
    svc = integrity.IntegrityService()
    return svc.run_integrity_check()


def start_scheduler():
    """
    Start the background scheduler for automated tasks.
    
    Schedules:
        - Tracker instance checks every hour
        - Data integrity checks daily at midnight
        - Analytics precomputation daily at 2 AM
    """
    scheduler = BackgroundScheduler()
    
    # Run check_all_trackers every hour with locking
    scheduler.add_job(
        check_trackers_locked, 
        'interval', 
        minutes=60, 
        id='check_trackers_hourly', 
        replace_existing=True,
        misfire_grace_time=600  # 10 min grace period
    )

    # Run integrity check every 24 hours (midnight) with locking
    scheduler.add_job(
        run_integrity_locked, 
        'cron', 
        hour=0, 
        minute=0, 
        id='integrity_check_daily', 
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )
    
    # Run nightly analytics precomputation at 2 AM with locking
    scheduler.add_job(
        precompute_analytics,
        'cron',
        hour=2,
        minute=0,
        id='nightly_analytics_precompute',
        replace_existing=True,
        misfire_grace_time=3600  # 1 hour grace period
    )
    
    scheduler.start()
    logger.info("⏰ Scheduler started with 3 locked jobs: hourly checks, nightly integrity, nightly analytics")
    print("⏰ Scheduler started!")
    
    atexit.register(lambda: scheduler.shutdown())


