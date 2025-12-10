
import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from django.http import HttpResponse

from core.helpers.monitoring import (
    track_performance, track_view_performance, PerformanceMonitor,
    get_query_stats, log_slow_queries, MetricsCollector
)

class TestMonitoringHelpers:
    
    def test_track_performance_decorator(self):
        """Test basic function performance tracking."""
        with patch('core.helpers.monitoring.logger') as mock_logger:
            @track_performance(threshold_seconds=0.01)
            def quick_func():
                return "success"
                
            result = quick_func()
            assert result == "success"
            mock_logger.debug.assert_called()
            
    def test_track_performance_slow(self):
        """Test tracking catches slow functions."""
        with patch('core.helpers.monitoring.logger') as mock_logger:
            @track_performance(threshold_seconds=0.01)
            def slow_func():
                time.sleep(0.02)
                return "done"
                
            slow_func()
            mock_logger.warning.assert_called()
            assert "SLOW:" in mock_logger.warning.call_args[0][0]

    def test_track_performance_with_queries(self):
        """Test tracking with query counting."""
        with patch('core.helpers.monitoring.logger') as mock_logger, \
             patch('core.helpers.monitoring.connection') as mock_conn, \
             patch('core.helpers.monitoring.CaptureQueriesContext') as MockContext:
            
            # Setup context manager
            ctx = Mock()
            ctx.__len__ = lambda x: 5
            MockContext.return_value.__enter__.return_value = ctx
            MockContext.return_value.__exit__.return_value = None
            
            @track_performance(log_queries=True)
            def db_func():
                return "db_done"
                
            db_func()
            
            # Should log with query count
            mock_logger.debug.assert_called()
            assert "with 5 queries" in mock_logger.debug.call_args[0][0]

    def test_track_view_performance(self):
        """Test view decorator."""
        with patch('core.helpers.monitoring.logger') as mock_logger, \
             patch('core.helpers.monitoring.CaptureQueriesContext') as MockContext:
            
            # Setup context
            ctx = Mock()
            ctx.__len__ = lambda x: 2
            MockContext.return_value.__enter__.return_value = ctx
            
            # Mock view
            request = Mock()
            request.method = "GET"
            
            @track_view_performance
            def my_view(req):
                res = HttpResponse("OK")
                return res
            
            response = my_view(request)
            assert response.status_code == 200
            
            mock_logger.info.assert_called()
            assert "VIEW:" in mock_logger.info.call_args[0][0]

    def test_performance_monitor_context(self):
        """Test context manager."""
        with patch('core.helpers.monitoring.logger') as mock_logger:
            with PerformanceMonitor("test_op", log_queries=False):
                pass
                
            mock_logger.info.assert_called()
            assert "PERF: test_op" in mock_logger.info.call_args[0][0]

    def test_get_query_stats(self):
        """Test fetching query stats."""
        with patch('core.helpers.monitoring.connection') as mock_conn:
            mock_conn.queries = [
                {'sql': 'SELECT * FROM table', 'time': '0.001'}
            ]
            
            stats = get_query_stats()
            assert stats['query_count'] == 1
            assert stats['queries'][0]['sql'] == 'SELECT * FROM table'

    def test_log_slow_queries(self):
        """Test logging slow queries."""
        with patch('core.helpers.monitoring.logger') as mock_logger, \
             patch('core.helpers.monitoring.connection') as mock_conn:
            
            mock_conn.queries = [
                {'sql': 'FAST', 'time': '0.01'},
                {'sql': 'SLOW', 'time': '0.2'} # 200ms
            ]
            
            log_slow_queries(threshold_ms=100)
            
            mock_logger.warning.assert_called()
            # Should only log the slow one
            assert "SLOW QUERY" in mock_logger.warning.call_args[0][0]
            assert "SLOW" in mock_logger.warning.call_args[0][0]

    def test_metrics_collector(self):
        """Test in-memory metrics collector."""
        MetricsCollector.clear()
        
        MetricsCollector.record('response_time', 0.1)
        MetricsCollector.record('response_time', 0.2)
        MetricsCollector.record('cpu_usage', 50)
        
        stats = MetricsCollector.get_stats('response_time')
        assert stats['count'] == 2
        assert stats['avg'] == pytest.approx(0.15)
        
        all_stats = MetricsCollector.get_stats()
        assert all_stats['count'] == 3
        
        MetricsCollector.clear()
        assert MetricsCollector.get_stats()['count'] == 0
        
    def test_metrics_collector_thread_safety(self):
        """Test concurrent access to metrics collector."""
        MetricsCollector.clear()
        
        def add_metrics():
            for _ in range(100):
                MetricsCollector.record('concurrent', 1.0)
                
        threads = [threading.Thread(target=add_metrics) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        stats = MetricsCollector.get_stats('concurrent')
        assert stats['count'] == 500
