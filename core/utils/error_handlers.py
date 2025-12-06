"""
Error Handling Utilities

Provides decorators and helpers for consistent exception handling across
views and services, ensuring unified response formats.
"""
from functools import wraps
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import Http404, JsonResponse
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
import json

from core.exceptions import (
    TrackerException,
    TrackerNotFoundError,
    TaskNotFoundError,
    TemplateNotFoundError,
    PermissionDeniedError,
    InvalidDateRangeError,
    InvalidStatusError,
    ValidationError as TrackerValidationError,
    DuplicateError
)
from core.utils.response_helpers import UXResponse


def handle_service_errors(view_func):
    """
    Decorator for API views to handle exceptions and return consistent UXResponses.
    Catches Service-layer exceptions and standard Django/DRF exceptions.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        
        # --- Not Found Errors ---
        except (TrackerNotFoundError, TaskNotFoundError, TemplateNotFoundError, Http404, ObjectDoesNotExist) as e:
            return UXResponse.error(
                message=str(e),
                error_code="NOT_FOUND",
                status=404
            )
            
        # --- Permission Errors ---
        except (PermissionDeniedError, PermissionDenied, DRFPermissionDenied) as e:
            return UXResponse.error(
                message=str(e) or "Permission denied",
                error_code="PERMISSION_DENIED",
                status=403
            )
            
        # --- Validation Errors ---
        except (TrackerValidationError, InvalidDateRangeError, InvalidStatusError, DuplicateError, json.JSONDecodeError) as e:
            msg = str(e)
            if isinstance(e, json.JSONDecodeError):
                msg = "Invalid JSON body"
                
            return UXResponse.error(
                message=msg,
                error_code="VALIDATION_ERROR",
                status=400
            )
        
        except (DjangoValidationError, DRFValidationError) as e:
            # Extract meaningful message from validation error containers
            msg = str(e)
            if hasattr(e, 'message_dict') and e.message_dict:
                # Use first error for UX clarity
                first_field = next(iter(e.message_dict))
                first_err = e.message_dict[first_field][0]
                msg = f"{first_field}: {first_err}"
            elif hasattr(e, 'detail') and e.detail:
                if isinstance(e.detail, dict):
                    first_field = next(iter(e.detail))
                    msg = f"{first_field}: {str(e.detail[first_field])}"
                else:
                    msg = str(e.detail)
                    
            return UXResponse.error(
                message=msg,
                error_code="VALIDATION_ERROR",
                status=400
            )
            
        # --- Generic Tracker Errors ---
        except TrackerException as e:
            return UXResponse.error(
                message=str(e),
                error_code="TRACKER_ERROR",
                status=400
            )
            
        # --- Unexpected Errors ---
        except Exception as e:
            # In production, log this error
            import traceback
            print(f"INTERNAL ERROR: {str(e)}")
            traceback.print_exc()
            
            
            return UXResponse.error(
                message="An unexpected error occurred",
                error_code="INTERNAL_ERROR",
                retry=True,
                status=500
            )
            
    return wrapper


def handle_view_errors(view_func):
    """
    Decorator for SPA views to handle exceptions and return Error Pages.
    """
    from django.shortcuts import render
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        
        # --- Not Found Errors ---
        except (TrackerNotFoundError, TaskNotFoundError, TemplateNotFoundError, Http404, ObjectDoesNotExist) as e:
            return render(request, 'panels/error_404.html', {
                'message': str(e)
            }, status=404)
            
        # --- Permission Errors ---
        except (PermissionDeniedError, PermissionDenied, DRFPermissionDenied) as e:
            return render(request, 'panels/error_404.html', {
                'message': "Permission Denied: " + str(e)
            }, status=403)
            
        # --- Unexpected Errors ---
        except Exception as e:
            # In production, log this error
            import traceback
            print(f"VIEW ERROR: {str(e)}")
            traceback.print_exc()
            
            return render(request, 'panels/error_404.html', {
                'message': "An unexpected error occurred. Please try again."
            }, status=500)
            
    return wrapper
