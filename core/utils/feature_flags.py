"""
Feature Flags Utility for Safe Rollouts.

Provides a simple, database/cache-backed feature flag system for:
- Gradual feature rollouts
- A/B testing
- Quick feature kill switches

Usage:
    from core.utils.feature_flags import is_feature_enabled, get_flag_value
    
    if is_feature_enabled('new_dashboard', user):
        return render_new_dashboard()
"""
import logging
from functools import wraps
from typing import Optional, Any

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


# Default flags - override in settings.py or database
DEFAULT_FLAGS = {
    'new_sync_api': {'enabled': True, 'rollout_percent': 100},
    'push_notifications': {'enabled': False, 'rollout_percent': 0},
    'advanced_analytics': {'enabled': True, 'rollout_percent': 100},
    'api_v2': {'enabled': False, 'rollout_percent': 0},
}


def _get_flags() -> dict:
    """Get feature flags from settings or defaults."""
    return getattr(settings, 'FEATURE_FLAGS', DEFAULT_FLAGS)


def _get_user_bucket(user) -> int:
    """Get consistent bucket (0-99) for user-based rollout."""
    if not user or not hasattr(user, 'id'):
        return 0
    return user.id % 100


def is_feature_enabled(flag_name: str, user=None) -> bool:
    """
    Check if a feature flag is enabled.
    
    Args:
        flag_name: Name of the feature flag
        user: Optional user for percentage-based rollout
        
    Returns:
        True if feature is enabled for this user
    """
    # Check cache first
    cache_key = f"ff:{flag_name}"
    cached = cache.get(cache_key)
    
    if cached is None:
        flags = _get_flags()
        flag_config = flags.get(flag_name, {'enabled': False, 'rollout_percent': 0})
        cache.set(cache_key, flag_config, 300)  # Cache for 5 minutes
    else:
        flag_config = cached
    
    if not flag_config.get('enabled', False):
        return False
    
    rollout_percent = flag_config.get('rollout_percent', 100)
    
    if rollout_percent >= 100:
        return True
    
    if rollout_percent <= 0:
        return False
    
    # User-based rollout
    user_bucket = _get_user_bucket(user)
    return user_bucket < rollout_percent


def get_flag_value(flag_name: str, default: Any = None) -> Any:
    """
    Get arbitrary value associated with a feature flag.
    
    Useful for config values like:
    - max_items: 50
    - api_timeout: 30
    """
    flags = _get_flags()
    flag_config = flags.get(flag_name, {})
    return flag_config.get('value', default)


def require_feature(flag_name: str, fallback=None):
    """
    Decorator to require a feature flag for a view.
    
    Usage:
        @require_feature('new_dashboard')
        def new_dashboard_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, 'user', None)
            
            if is_feature_enabled(flag_name, user):
                return view_func(request, *args, **kwargs)
            
            if fallback:
                return fallback(request, *args, **kwargs)
            
            # Return 404 if feature not enabled
            from django.http import Http404
            raise Http404("Feature not available")
        
        return wrapper
    return decorator


def set_flag_override(flag_name: str, enabled: bool, duration: int = 3600):
    """
    Temporarily override a feature flag (useful for testing).
    
    Args:
        flag_name: Flag to override
        enabled: New enabled state
        duration: Override duration in seconds (default 1 hour)
    """
    cache_key = f"ff:{flag_name}"
    cache.set(cache_key, {'enabled': enabled, 'rollout_percent': 100 if enabled else 0}, duration)
    logger.info(f"Feature flag '{flag_name}' overridden to {enabled} for {duration}s")


def clear_flag_cache():
    """Clear all feature flag cache entries."""
    flags = _get_flags()
    for flag_name in flags.keys():
        cache.delete(f"ff:{flag_name}")
