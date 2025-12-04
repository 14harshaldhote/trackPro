"""
Caching utilities for Tracker Pro.
Implements Django's cache framework with smart invalidation patterns.
"""
from django.core.cache import cache
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# Cache timeout settings (in seconds)
CACHE_TIMEOUTS = {
    'tracker_stats': 300,      # 5 minutes
    'dashboard': 60,           # 1 minute
    'analytics': 600,          # 10 minutes
    'completion_rate': 300,    # 5 minutes
    'streaks': 300,            # 5 minutes
    'consistency': 300,        # 5 minutes
}


def make_cache_key(prefix, *args, **kwargs):
    """
    Generate a consistent cache key from function arguments.
    
    Args:
        prefix: Cache key prefix (e.g., 'tracker_stats')
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        String cache key
    """
    # Convert args and kwargs to a stable string representation
    key_parts = [prefix]
    
    # Add positional args
    for arg in args:
        if hasattr(arg, '__dict__'):
            # For objects, use their dict representation
            key_parts.append(str(sorted(arg.__dict__.items())))
        else:
            key_parts.append(str(arg))
    
    # Add keyword args (sorted for consistency)
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    # Create hash if key is too long
    key_string = ':'.join(key_parts)
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    return key_string


def cache_result(timeout=300, key_prefix='default'):
    """
    Decorator to cache function results using Django's cache framework.
    
    Usage:
        @cache_result(timeout=300, key_prefix='my_func')
        def my_function(arg1, arg2):
            # expensive computation
            return result
    
    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = make_cache_key(key_prefix, *args, **kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key)
            
            if result is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return result
            
            # Cache miss - compute result
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, timeout)
            
            return result
        
        # Add cache invalidation method to function
        wrapper.invalidate = lambda *args, **kwargs: cache.delete(
            make_cache_key(key_prefix, *args, **kwargs)
        )
        
        return wrapper
    return decorator


def invalidate_tracker_cache(tracker_id):
    """
    Invalidate all cached data for a specific tracker.
    Call this when tracker data is modified.
    
    Args:
        tracker_id: Tracker ID to invalidate
    """
    # Delete all tracker-related cache keys
    patterns = [
        f'tracker_stats:{tracker_id}',
        f'completion_rate:{tracker_id}',
        f'streaks:{tracker_id}',
        f'consistency:{tracker_id}',
        f'balance:{tracker_id}',
        f'analytics:{tracker_id}',
        f'grid_data:{tracker_id}',
    ]
    
    deleted_count = 0
    for pattern in patterns:
        # Django's cache.delete() with wildcards depends on backend
        # For simple implementation, delete exact keys
        try:
            cache.delete(pattern)
            deleted_count += 1
        except Exception as e:
            logger.warning(f"Failed to delete cache key {pattern}: {e}")
    
    logger.info(f"Invalidated {deleted_count} cache entries for tracker {tracker_id}")


def invalidate_dashboard_cache():
    """
    Invalidate dashboard-wide cached data.
    Call this when any tracker data changes.
    """
    cache.delete('dashboard_stats')
    cache.delete('all_trackers')
    logger.info("Invalidated dashboard cache")


def invalidate_all_caches():
    """
    Clear all application caches.
    Use sparingly - typically only for maintenance or debugging.
    """
    try:
        cache.clear()
        logger.info("Cleared all caches")
    except Exception as e:
        logger.error(f"Failed to clear all caches: {e}")


# Convenience decorators with preset timeouts
def cache_tracker_stats(func):
    """Cache tracker statistics for 5 minutes"""
    return cache_result(
        timeout=CACHE_TIMEOUTS['tracker_stats'],
        key_prefix=f'tracker_stats:{func.__name__}'
    )(func)


def cache_analytics(func):
    """Cache analytics results for 10 minutes"""
    return cache_result(
        timeout=CACHE_TIMEOUTS['analytics'],
        key_prefix=f'analytics:{func.__name__}'
    )(func)


def cache_dashboard(func):
    """Cache dashboard data for 1 minute"""
    return cache_result(
        timeout=CACHE_TIMEOUTS['dashboard'],
        key_prefix=f'dashboard:{func.__name__}'
    )(func)


class CacheInvalidator:
    """
    Context manager for operations that should invalidate caches.
    
    Usage:
        with CacheInvalidator(tracker_id):
            # Make changes to tracker
            task.status = 'DONE'
            task.save()
        # Cache automatically invalidated on exit
    """
    
    def __init__(self, tracker_id=None, invalidate_dashboard=False):
        self.tracker_id = tracker_id
        self.invalidate_dashboard = invalidate_dashboard
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Only invalidate if no exception occurred
        if exc_type is None:
            if self.tracker_id:
                invalidate_tracker_cache(self.tracker_id)
            
            if self.invalidate_dashboard:
                invalidate_dashboard_cache()
