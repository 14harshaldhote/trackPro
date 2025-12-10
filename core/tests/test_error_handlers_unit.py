"""
Unit tests for core/utils/error_handlers.py

Tests error handling decorators:
- handle_service_errors decorator for API views
- Exception handling for all custom exception types
"""
import pytest
import json
from unittest.mock import Mock, patch
from django.http import HttpResponse, Http404, JsonResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied

from core.utils.error_handlers import handle_service_errors, handle_view_errors
from core.exceptions import (
    TrackerException,
    TrackerNotFoundError,
    TaskNotFoundError,
    TemplateNotFoundError,
    PermissionDeniedError

 as TrackerPermissionDeniedError,
    InvalidDateRangeError,
    InvalidStatusError,
    ValidationError as TrackerValidationError,
    DuplicateError
)


# ============================================================================
# Test Fixtures and Helpers
# ============================================================================

class MockRequest:
    """Mock request object for testing."""
    def __init__(self):
        self.method = 'GET'
        self.path = '/api/test/'
        self.user = Mock(id=1, is_authenticated=True)


# ============================================================================
# Tests for handle_service_errors decorator
# ============================================================================

class TestHandleServiceErrorsDecorator:
    """Tests for the handle_service_errors decorator."""
    
    def test_happy_path_passes_through(self):
        """Normal response should pass through unchanged."""
        @handle_service_errors
        def view_func(request):
            return JsonResponse({'success': True})
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 200
    
    def test_tracker_not_found_returns_404(self):
        """TrackerNotFoundError should return 404."""
        @handle_service_errors
        def view_func(request):
            raise TrackerNotFoundError("Tracker not found")
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 404
        data = json.loads(response.content)
        assert data['success'] is False
        assert 'NOT_FOUND' in data.get('error', {}).get('code', '')
    
    def test_permission_denied_error_returns_403(self):
        """PermissionDeniedError should return 403."""
        @handle_service_errors
        def view_func(request):
            raise TrackerPermissionDeniedError("read", "resource")
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 403
        data = json.loads(response.content)
        assert 'FORBIDDEN' in data.get('error', {}).get('code', '')
    
    def test_tracker_validation_error_returns_400(self):
        """TrackerValidationError should return 400."""
        @handle_service_errors
        def view_func(request):
            raise TrackerValidationError("field_name", "Invalid input")
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'VALIDATION_ERROR' in data.get('error', {}).get('code', '')
    
    def test_invalid_date_range_error_returns_400(self):
        """InvalidDateRangeError should return 400."""
        @handle_service_errors
        def view_func(request):
            raise InvalidDateRangeError("2025-01-02", "2025-01-01")
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'INVALID_DATE_RANGE' in data.get('error', {}).get('code', '')
    
    def test_invalid_status_error_returns_400(self):
        """InvalidStatusError should return 400."""
        @handle_service_errors
        def view_func(request):
            raise InvalidStatusError("invalid", ["TODO", "DONE"])
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'INVALID_STATUS' in data.get('error', {}).get('code', '')
    
    def test_duplicate_error_returns_400(self):
        """DuplicateError should return 400."""
        @handle_service_errors
        def view_func(request):
            raise DuplicateError("Resource", "id123")
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'DUPLICATE' in data.get('error', {}).get('code', '')
    
    def test_json_decode_error_returns_400(self):
        """JSONDecodeError should return 400."""
        @handle_service_errors
        def view_func(request):
            raise json.JSONDecodeError("Bad JSON", "doc", 0)
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'JSON' in data.get('error', {}).get('message', '')
    
    def test_generic_tracker_exception_returns_400(self):
        """Generic TrackerException should return 400."""
        @handle_service_errors
        def view_func(request):
            raise TrackerException("Generic tracker error")
        
        request = MockRequest()
        response = view_func(request)
        
        assert response.status_code == 400
        data = json.loads(response.content)
        assert 'TRACKER_ERROR' in data.get('error', {}).get('code', '')
    
    def test_unexpected_exception_returns_500(self):
        """Unexpected exceptions should return 500."""
        @handle_service_errors
        def view_func(request):
            raise RuntimeError("Unexpected error")
        
        request = MockRequest()
        with patch('builtins.print'):  # Suppress error printing
            response = view_func(request)
        
        assert response.status_code == 500
        data = json.loads(response.content)
        assert 'INTERNAL_ERROR' in data.get('error', {}).get('code', '')
    
    def test_preserves_function_metadata(self):
        """Decorator should preserve function metadata."""
        @handle_service_errors
        def my_view_func(request):
            """My docstring."""
            return JsonResponse({})
        
        assert my_view_func.__name__ == 'my_view_func'
        assert 'My docstring' in my_view_func.__doc__


# ============================================================================
# Integration Tests
# ============================================================================

class TestErrorHandlersIntegration:
    """Integration tests for error handlers."""
    
    def test_error_message_extraction_from_django_validation(self):
        """Django validation errors should extract meaningful messages."""
        @handle_service_errors
        def view_func(request):
            error = DjangoValidationError({'email': ['Invalid email format']})
            raise error
        
        request = MockRequest()
        response = view_func(request)
        
        data = json.loads(response.content)
        message = data.get('error', {}).get('message', '')
        assert 'email' in message or 'Invalid' in message
    
    def test_error_message_extraction_from_drf_validation(self):
        """DRF validation errors should extract meaningful messages."""
        @handle_service_errors
        def view_func(request):
            raise DRFValidationError({'username': ['Required field']})
        
        request = MockRequest()
        response = view_func(request)
        
        data = json.loads(response.content)
        message = data.get('error', {}).get('message', '')
        assert 'username' in message or 'required' in message.lower()
    
    def test_args_passed_to_view(self):
        """View arguments should be passed correctly."""
        @handle_service_errors
        def view_func(request, tracker_id, action=None):
            return JsonResponse({'tracker_id': tracker_id, 'action': action})
        
        request = MockRequest()
        response = view_func(request, 'abc123', action='update')
        
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['tracker_id'] == 'abc123'
        assert data['action'] == 'update'
