"""
API Response Helpers for UX-Optimized Responses

Provides consistent response format with feedback metadata for:
- Success responses with celebration/haptic hints
- Error responses with retry/help information
- iOS-specific feedback (haptics, sounds, animations)
"""
from django.http import JsonResponse
from typing import Dict, Any, Optional
import random


class UXResponse:
    """Helper for creating UX-optimized API responses"""
    
    # Celebratory messages for task completion
    COMPLETION_MESSAGES = [
        "Great job! 🎉",
        "Task completed! ✅",
        "You're on fire! 🔥",
        "Keep it up! 💪",
        "Excellent work! ⭐",
    ]
    
    @staticmethod
    def success(
        message: str = "Action completed",
        data: Optional[Dict] = None,
        feedback: Optional[Dict] = None,
        stats_delta: Optional[Dict] = None
    ) -> JsonResponse:
        """
        Success response with UX metadata.
        
        Args:
            message: User-friendly success message
            data: Response data
            feedback: Visual feedback configuration
                - type: 'success', 'celebration', 'info'
                - haptic: iOS haptic type ('success', 'light', 'medium', 'heavy')
                - animation: Animation name ('checkmark', 'confetti')
                - toast: Whether to show toast notification
            stats_delta: Changed stats for optimistic UI updates
        
        Returns:
            JsonResponse with success payload
        """
        response = {
            'success': True,
            'message': message,
            'data': data or {},
            'feedback': feedback or {
                'type': 'success',
                'haptic': 'success',
                'toast': True
            }
        }
        
        if stats_delta:
            response['stats_delta'] = stats_delta
        
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
            error_code: Error code for debugging/tracking
            retry: Whether user should retry the action
            help_link: Link to help documentation
            status: HTTP status code (default: 400)
        
        Returns:
            JsonResponse with error payload
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
                'toast': True
            }
        }
        
        if help_link:
            response['error']['help_link'] = help_link
        
        return JsonResponse(response, status=status)
    
    @staticmethod
    def celebration(
        achievement: str,
        animation: str = "confetti"
    ) -> Dict:
        """
        Celebration feedback for milestones.
        
        Args:
            achievement: What was achieved
            animation: Animation type ('confetti', 'fireworks', 'checkmark')
        
        Returns:
            Feedback dict (not a response - use with success())
        """
        return {
            'type': 'celebration',
            'message': achievement,
            'animation': animation,
            'haptic': 'heavy',
            'sound': 'celebration'
        }
    
    @staticmethod
    def with_undo(
        data: Dict,
        undo_data: Dict,
        timeout_ms: int = 5000
    ) -> Dict:
        """
        Add undo capability to response data.
        
        Args:
            data: Original response data
            undo_data: Data needed to undo the action
            timeout_ms: How long undo is available (default: 5 seconds)
        
        Returns:
            Enhanced data dict with undo info
        """
        data['undo'] = {
            'enabled': True,
            'timeout_ms': timeout_ms,
            'undo_data': undo_data
        }
        return data
    
    @classmethod
    def get_completion_message(cls, status: str) -> str:
        """Get appropriate message for status change."""
        if status == 'DONE':
            return random.choice(cls.COMPLETION_MESSAGES)
        
        messages = {
            'SKIPPED': 'Task skipped',
            'TODO': 'Task reopened',
            'IN_PROGRESS': 'Task started',
            'MISSED': 'Task marked as missed',
            'BLOCKED': 'Task blocked',
        }
        return messages.get(status, 'Status updated')


# Convenience functions
def success_response(message: str = "Success", data: Optional[Dict] = None) -> JsonResponse:
    """Quick success response without extra metadata."""
    return UXResponse.success(message=message, data=data)


def error_response(message: str, code: str = "ERROR", retry: bool = False) -> JsonResponse:
    """Quick error response."""
    return UXResponse.error(message=message, error_code=code, retry=retry)
