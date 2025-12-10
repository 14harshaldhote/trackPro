"""
Structured Logging with Request Correlation IDs.

Provides middleware and utilities for production-ready logging:
- Request ID correlation across log entries
- Structured JSON logging format
- Performance timing
"""
import json
import logging
import time
import uuid
import threading
from functools import wraps

logger = logging.getLogger(__name__)

# Thread-local storage for request context
_request_context = threading.local()


# ============================================================================
# REQUEST ID MANAGEMENT
# ============================================================================

def get_request_id() -> str:
    """Get current request ID or generate a new one."""
    return getattr(_request_context, 'request_id', None) or str(uuid.uuid4())[:8]


def set_request_id(request_id: str):
    """Set request ID in thread-local storage."""
    _request_context.request_id = request_id


def clear_request_context():
    """Clear all request context."""
    if hasattr(_request_context, 'request_id'):
        delattr(_request_context, 'request_id')


# ============================================================================
# STRUCTURED LOG FORMATTER
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Outputs logs in format:
    {"timestamp": "...", "level": "INFO", "request_id": "abc123", "message": "..."}
    """
    
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': get_request_id(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info',
                          'thread', 'threadName', 'exc_info', 'exc_text',
                          'message', 'taskName'):
                if not key.startswith('_'):
                    log_data[key] = value
        
        return json.dumps(log_data)


# ============================================================================
# LOGGING UTILITIES
# ============================================================================

def log_with_context(level: str, message: str, **extra):
    """
    Log with current request context and extra fields.
    
    Usage:
        log_with_context('info', 'User logged in', user_id=123, method='password')
    """
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, extra=extra)


def log_api_request(request, response_status: int, duration_ms: float):
    """Log API request with standard fields."""
    log_with_context(
        'info',
        f'{request.method} {request.path}',
        method=request.method,
        path=request.path,
        status=response_status,
        duration_ms=round(duration_ms, 2),
        user_id=getattr(getattr(request, 'user', None), 'id', None),
        ip=request.META.get('REMOTE_ADDR')
    )


# ============================================================================
# MIDDLEWARE
# ============================================================================

class RequestIDMiddleware:
    """
    Django middleware to add request ID correlation.
    
    Add to MIDDLEWARE in settings.py:
        'core.utils.logging_utils.RequestIDMiddleware',
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get or generate request ID
        request_id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4())[:8])
        set_request_id(request_id)
        
        start_time = time.time()
        
        try:
            response = self.get_response(request)
            
            # Add request ID to response headers
            response['X-Request-ID'] = request_id
            
            # Log request completion
            duration_ms = (time.time() - start_time) * 1000
            log_api_request(request, response.status_code, duration_ms)
            
            return response
        finally:
            clear_request_context()


# ============================================================================
# DECORATOR FOR FUNCTION LOGGING
# ============================================================================

def log_function_call(log_args: bool = False, log_result: bool = False):
    """
    Decorator to log function entry/exit with timing.
    
    Usage:
        @log_function_call(log_args=True)
        def my_function(arg1, arg2):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            
            # Log entry
            if log_args:
                log_with_context('debug', f'Entering {func_name}', 
                               func_args=str(args)[:200], func_kwargs=str(kwargs)[:200])
            
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                
                if log_result:
                    log_with_context('debug', f'Exited {func_name}',
                                   duration_ms=round(duration, 2),
                                   result=str(result)[:200])
                else:
                    log_with_context('debug', f'Exited {func_name}',
                                   duration_ms=round(duration, 2))
                
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                log_with_context('error', f'Error in {func_name}: {e}',
                               duration_ms=round(duration, 2),
                               error_type=type(e).__name__)
                raise
        
        return wrapper
    return decorator
