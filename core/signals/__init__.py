"""
Django Signals for TrackPro

This package contains signal handlers for automatic updates:
- Goal progress updates on task status changes
- Streak milestone notifications
- Cache invalidation triggers
"""

# Import signals so they register when Django loads
from . import task_signals  # noqa

default_app_config = 'core.signals'
