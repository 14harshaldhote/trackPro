"""
API Response Helpers for UX-Optimized Responses
Provides consistent response format with feedback metadata for iOS and Web.

Following OpusSuggestion.md Part 2.1: Enhanced API Responses with Action Metadata
"""
from django.http import JsonResponse
from typing import Dict, Any, Optional
import random


class UXResponse:
    """Helper for creating UX-optimized API responses with feedback metadata."""
    
    @staticmethod
    def success(
        message: str = "Action completed",
        data: Optional[Dict] = None,
        feedback: Optional[Dict] = None,
        stats_delta: Optional[Dict] = None,
        undo: Optional[Dict] = None
    ) -> JsonResponse:
        """
        Success response with UX metadata.
        
        Args:
            message: User-friendly success message
            data: Response data
            feedback: Visual feedback configuration (haptic, animation, etc.)
            stats_delta: Changed stats for optimistic updates
            undo: Undo configuration with timeout and data
        
        Returns:
            JsonResponse with standardized success format
        """
        response = {
            'success': True,
            'message': message,
            'data': data or {},
            'feedback': feedback or {
                'type': 'success',
                'haptic': 'success',
                'toast': True,
                'message': message
            }
        }
        
        if stats_delta:
            response['stats_delta'] = stats_delta
        
        if undo:
            response['undo'] = undo
        
        return JsonResponse(response)
    
    @staticmethod
    def error(
        message: str = "An error occurred",
        error_code: str = "GENERAL_ERROR",
        retry: bool = False,
        help_link: Optional[str] = None,
        status: int = 400
    ) -> JsonResponse:
        """
        Error response with helpful messaging.
        
        Args:
            message: Clear, actionable error message
            error_code: Error code for debugging
            retry: Whether user should retry
            help_link: Link to help documentation
            status: HTTP status code
        
        Returns:
            JsonResponse with standardized error format
        """
        response = {
            'success': False,
            'error': {
                'message': message,
                'code': error_code,
                'retry': retry
            },
            'feedback': {
                'type': 'error',
                'haptic': 'error',
                'toast': True,
                'message': message
            }
        }
        
        if help_link:
            response['error']['help_link'] = help_link
        
        return JsonResponse(response, status=status)
    
    @staticmethod
    def celebration(
        achievement: str,
        animation: str = "confetti",
        sound: str = "celebration"
    ) -> Dict:
        """
        Celebration feedback for milestones.
        
        Args:
            achievement: What was achieved
            animation: Animation type (confetti, fireworks, checkmark)
            sound: Sound effect to play
        
        Returns:
            Dict with celebration metadata
        """
        return {
            'type': 'celebration',
            'message': achievement,
            'animation': animation,
            'haptic': 'heavy',
            'sound': sound,
            'toast': True
        }
    
    @staticmethod
    def undo_metadata(
        task_id: str,
        old_status: str,
        timeout_ms: int = 5000
    ) -> Dict:
        """
        Generate undo metadata for reversible actions.
        
        Args:
            task_id: ID of the affected task
            old_status: Previous status for undo
            timeout_ms: Undo timeout in milliseconds
        
        Returns:
            Dict with undo configuration
        """
        return {
            'enabled': True,
            'timeout_ms': timeout_ms,
            'undo_data': {
                'task_id': task_id,
                'old_status': old_status
            }
        }


def get_completion_message(status: str) -> str:
    """
    Return celebratory or informational message based on status.
    
    Args:
        status: Task status
    
    Returns:
        User-friendly status message
    """
    messages = {
        'DONE': [
            "Great job! 🎉",
            "Task completed! ✅",
            "You're on fire! 🔥",
            "Keep it up! 💪",
            "Awesome work! ⭐",
            "Well done! 👏"
        ],
        'SKIPPED': "Task skipped",
        'TODO': "Task reopened",
        'IN_PROGRESS': "Task in progress",
        'BLOCKED': "Task blocked",
        'MISSED': "Task marked as missed"
    }
    
    if status == 'DONE':
        return random.choice(messages['DONE'])
    
    return messages.get(status, 'Status updated')


def generate_feedback_metadata(
    action_type: str,
    is_completion: bool = False,
    all_complete: bool = False
) -> Dict:
    """
    Generate appropriate feedback metadata based on action type.
    
    Args:
        action_type: Type of action performed
        is_completion: Whether this is a task completion
        all_complete: Whether all tasks are now complete
    
    Returns:
        Dict with feedback metadata
    """
    if all_complete:
        return UXResponse.celebration(
            achievement="All tasks complete! 🎉",
            animation="confetti",
            sound="celebration"
        )
    
    if is_completion:
        return {
            'type': 'success',
            'message': get_completion_message('DONE'),
            'haptic': 'success',
            'animation': 'checkmark',
            'toast': True
        }
    
    feedback_map = {
        'skip': {
            'type': 'info',
            'message': 'Task skipped',
            'haptic': 'light',
            'toast': True
        },
        'delete': {
            'type': 'warning',
            'message': 'Task deleted',
            'haptic': 'warning',
            'toast': True
        },
        'reopen': {
            'type': 'info',
            'message': 'Task reopened',
            'haptic': 'light',
            'toast': True
        }
    }
    
    return feedback_map.get(action_type, {
        'type': 'info',
        'haptic': 'light',
        'toast': False
    })
