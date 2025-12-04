"""
Helper functions for multi-user authentication.

Provides utilities to ensure users can only access their own data.
"""
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from core.models import TrackerDefinition


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
    
    Args:
        tracker_id: Tracker ID
        user: User object (request.user)
        
    Raises:
        PermissionDenied: If user doesn't own the tracker
    """
    tracker = TrackerDefinition.objects.filter(tracker_id=tracker_id).first()
    
    if not tracker:
        raise PermissionDenied("Tracker not found")
    
    if tracker.user != user:
        raise PermissionDenied("You don't have permission to access this tracker")


def get_user_trackers(user):
    """
    Get all trackers belonging to a user.
    
    Args:
        user: User object (request.user)
        
    Returns:
        QuerySet of TrackerDefinition objects
    """
    return TrackerDefinition.objects.filter(user=user).order_by('-created_at')
