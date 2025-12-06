"""
Helper functions for multi-user authentication.

Provides utilities to ensure users can only access their own data.
"""
import logging
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.core.exceptions import PermissionDenied
from core.models import TrackerDefinition

logger = logging.getLogger(__name__)


def get_user_tracker_or_404(tracker_id, user):
    """
    Get a tracker that belongs to the specified user, or raise 404.
    
    Args:
        tracker_id: Tracker ID
        user: User object (request.user)
        
    Returns:
        TrackerDefinition instance
        
    Raises:
        Http404: If tracker doesn't exist or doesn't belong to user
    """
    return get_object_or_404(TrackerDefinition, tracker_id=tracker_id, user=user)


def check_tracker_permission(tracker_id, user):
    """
    Check if user has permission to access a tracker.
    
    Security: Uses 404 for both "not found" and "not authorized" to prevent
    leaking information about tracker existence.
    
    Args:
        tracker_id: Tracker ID
        user: User object (request.user)
        
    Raises:
        Http404: If user doesn't own the tracker OR tracker doesn't exist
    """
    tracker = TrackerDefinition.objects.filter(tracker_id=tracker_id).first()
    
    if not tracker:
        raise Http404("Tracker not found")
    
    if tracker.user != user:
        # Log for security monitoring (but don't reveal in response)
        logger.warning(
            f"Permission denied: user {user.id} attempted to access tracker {tracker_id} "
            f"owned by user {tracker.user_id}"
        )
        # Use 404 to avoid leaking tracker existence
        raise Http404("Tracker not found")


def get_user_trackers(user):
    """
    Get all trackers belonging to a user.
    
    Args:
        user: User object (request.user)
        
    Returns:
        QuerySet of TrackerDefinition objects
    """
    return TrackerDefinition.objects.filter(user=user).order_by('-created_at')
