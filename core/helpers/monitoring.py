"""
Performance Monitoring Utilities

Provides decorators and helpers for tracking application performance,
identifying slow operations, and logging metrics.
"""
import time
import logging
from functools import wraps
from typing import Callable, Any
from django.db import connection
from django.test.utils import CaptureQueriesContext

logger = logging.getLogger(__name__)


def track_performance(threshold_seconds: float = 1.0, log_queries: bool = False):
    """
    Decorator to track function execution time and optionally query count.
    
    Args:
        threshold_seconds: Log warning if execution exceeds this (default: 1s)
        log_queries: Whether to log database query count (default: False)
        
    Usage:
        @track_performance(threshold_seconds=0.5, log_queries=True)
        def slow_function():
            # ... expensive operation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            if log_queries:
                with CaptureQueriesContext(connection) as queries:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    query_count = len(queries)
                    
                    if duration > threshold_seconds:
                        logger.warning(
                            f"SLOW: {func_name} took {duration:.2f}s with {query_count} queries"
                        )
                    else:
                        logger.debug(
                            f"{func_name} took {duration:.2f}s with {query_count} queries"
                        )
            else:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > threshold_seconds:
                    logger.warning(f"SLOW: {func_name} took {duration:.2f}s")
                else:
                    logger.debug(f"{func_name} took {duration:.2f}s")
            
            return result
        return wrapper
    return decorator


def track_view_performance(view_func: Callable) -> Callable:
    """
    Decorator specifically for Django views to track performance.
    
    Logs: View name, execution time, query count, and response status.
    
    Usage:
        @track_view_performance
        def my_view(request):
            # ... view logic
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        view_name = f"{view_func.__module__}.{view_func.__name__}"
        start_time = time.time()
        
        with CaptureQueriesContext(connection) as queries:
            response = view_func(request, *args, **kwargs)
            duration = time.time() - start_time
            query_count = len(queries)
            
            # Log performance metrics
            log_data = {
                'view': view_name,
                'method': request.method,
                'duration': f"{duration:.2f}s",
                'queries': query_count,
                'status': getattr(response, 'status_code', 'N/A')
            }
            
            if duration > 1.0 or query_count > 10:
                logger.warning(f"VIEW PERFORMANCE: {log_data}")
            else:
                logger.info(f"VIEW: {log_data}")
        
        return response
    return wrapper


class PerformanceMonitor:
    """
    Context manager for tracking performance of code blocks.
    
    Usage:
        with PerformanceMonitor("analytics_computation"):
            # ... expensive operation
    """
    
    def __init__(self, operation_name: str, log_queries: bool = True):
        self.operation_name = operation_name
        self.log_queries = log_queries
        self.start_time = None
        self.queries_context = None
    
    def __enter__(self):
        self.start_time = time.time()
        if self.log_queries:
            self.queries_context = CaptureQueriesContext(connection)
            self.queries_context.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if self.log_queries and self.queries_context:
            self.queries_context.__exit__(exc_type, exc_val, exc_tb)
            query_count = len(self.queries_context)
            logger.info(
                f"PERF: {self.operation_name} - {duration:.2f}s, {query_count} queries"
            )
        else:
            logger.info(f"PERF: {self.operation_name} - {duration:.2f}s")


def get_query_stats() -> dict:
    """
    Get current database query statistics.
    
    Returns:
        {
            'query_count': int,
            'queries': list of query info
        }
    """
    from django.db import reset_queries
    
    queries = connection.queries
    
    return {
        'query_count': len(queries),
        'queries': [
            {
                'sql': q['sql'][:100],  # First 100 chars
                'time': q['time']
            }
            for q in queries
        ]
    }


def log_slow_queries(threshold_ms: float = 100):
    """
    Log queries that exceed the time threshold.
    
    Args:
        threshold_ms: Threshold in milliseconds (default: 100ms)
    """
    for query in connection.queries:
        time_ms = float(query['time']) * 1000
        if time_ms > threshold_ms:
            logger.warning(
                f"SLOW QUERY ({time_ms:.1f}ms): {query['sql'][:200]}"
            )


# Metrics collection
import threading

class MetricsCollector:
    """
    Thread-safe in-memory metrics collector.
    Uses locking for safe access in WSGI multi-threaded environments.
    """
    
    _metrics = []
    _max_size = 1000
    _lock = threading.Lock()
    
    @classmethod
    def record(cls, metric_type: str, value: float, metadata: dict = None):
        """Record a metric (thread-safe)"""
        entry = {
            'type': metric_type,
            'value': value,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }
        
        with cls._lock:
            cls._metrics.append(entry)
            
            # Keep only recent metrics
            if len(cls._metrics) > cls._max_size:
                cls._metrics = cls._metrics[-cls._max_size:]
    
    @classmethod
    def get_stats(cls, metric_type: str = None) -> dict:
        """Get statistics for a metric type (thread-safe)"""
        with cls._lock:
            if metric_type:
                values = [m['value'] for m in cls._metrics if m['type'] == metric_type]
            else:
                values = [m['value'] for m in cls._metrics]
        
        if not values:
            return {'count': 0}
        
        import statistics
        return {
            'count': len(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
        }
    
    @classmethod
    def clear(cls):
        """Clear all metrics (thread-safe)"""
        with cls._lock:
            cls._metrics = []
