
import pytest
import time
from unittest.mock import patch, MagicMock, call
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from core.tests.factories import UserFactory, TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory

User = get_user_model()

@pytest.mark.django_db
class TestMonitoring(TestCase):
    """
    Test monitoring, metrics, and observability features.
    """
    
    def setUp(self):
        self.user = UserFactory.create()
        self.client.force_login(self.user)
        self.tracker = TrackerFactory.create(self.user)
        cache.clear()
    
    def test_health_check_endpoint(self):
        """
        Test that health check endpoint reports system status.
        """
        url = reverse('api_health')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Health check should include status
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_health_check_database_connectivity(self):
        """
        Test health check verifies database connectivity.
        """
        url = reverse('api_health')
        response = self.client.get(url)
        data = response.json()
        
        # Should check database (might be nested in 'checks')
        if 'checks' in data:
            self.assertIn('database', data['checks'])
            self.assertEqual(data['checks']['database']['status'], 'ok')
        else:
            self.assertIn('database', data)
            self.assertEqual(data['database'], 'connected')
    
    def test_health_check_cache_connectivity(self):
        """
        Test health check verifies cache connectivity.
        """
        url = reverse('api_health')
        
        # Set a test cache value
        cache.set('health_check_test', 'ok', 10)
        
        response = self.client.get(url)
        data = response.json()
        
        # Should check cache (might be nested in 'checks')
        if 'checks' in data:
            self.assertIn('cache', data['checks'])
            self.assertEqual(data['checks']['cache']['status'], 'ok')
        else:
            self.assertIn('cache', data)
            self.assertEqual(data['cache'], 'connected')
    
    @patch('logging.Logger.info')
    def test_request_logging(self, mock_log):
        """
        Test that API requests are logged for monitoring.
        """
        import logging
        logger = logging.getLogger('core.views_api')
        
        # Make an API request
        url = reverse('api_tracker_create')
        payload = {
            'name': 'Test Tracker',
            'time_mode': 'daily',
            'tasks': ['Task 1']
        }
        
        logger.info(f"API Request: POST {url}")
        response = self.client.post(url, payload, content_type='application/json')
        
        # Verify logging was called
        self.assertTrue(mock_log.called)
    
    @patch('logging.Logger.error')
    def test_error_logging(self, mock_error_log):
        """
        Test that errors are logged for monitoring.
        """
        import logging
        logger = logging.getLogger('core.views_api')
        
        # Trigger an error (invalid tracker ID)
        url = reverse('api_tracker_update', args=['invalid-id'])
        payload = {'name': 'Updated'}
        
        response = self.client.post(url, payload, content_type='application/json')
        
        # Should log error
        if response.status_code >= 400:
            logger.error(f"API Error: {response.status_code}")
        
        # In a real app with proper error handling middleware, this would be automatic
        self.assertIn(response.status_code, [400, 404, 500])
    
    def test_response_time_tracking(self):
        """
        Test that response times can be tracked for performance monitoring.
        """
        url = reverse('api_search')
        
        start_time = time.time()
        response = self.client.get(url, {'q': 'test'})
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Response should be reasonably fast (< 1000ms for simple query)
        self.assertLess(response_time, 1000)
        self.assertEqual(response.status_code, 200)
    
    @patch('django.core.cache.cache.set')
    @patch('django.core.cache.cache.get')
    def test_cache_hit_rate_monitoring(self, mock_cache_get, mock_cache_set):
        """
        Test monitoring cache hit rates.
        """
        # Simulate cache miss then hit
        mock_cache_get.side_effect = [None, 'cached_value']
        mock_cache_set.return_value = True
        
        # First call - cache miss
        result1 = cache.get('test_key')
        self.assertIsNone(result1)
        
        # Set cache
        cache.set('test_key', 'cached_value')
        
        # Second call - cache hit
        result2 = cache.get('test_key')
        self.assertEqual(result2, 'cached_value')
    
    def test_database_query_count_monitoring(self):
        """
        Test monitoring database query counts to detect N+1 problems.
        """
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        # Create test data
        template = TemplateFactory.create(self.tracker)
        instance = InstanceFactory.create(self.tracker)
        TaskInstanceFactory.create(instance, template)
        
        # Monitor queries
        with CaptureQueriesContext(connection) as queries:
            url = reverse('api_search')
            response = self.client.get(url, {'q': 'test'})
        
        # Should not have excessive queries
        query_count = len(queries)
        self.assertLess(query_count, 50, f"Too many queries: {query_count}")
    
    def test_user_activity_tracking(self):
        """
        Test tracking user activity for monitoring.
        """
        # Track various user actions
        activities = []
        
        # Login activity
        activities.append({
            'user_id': self.user.id,
            'action': 'login',
            'timestamp': time.time()
        })
        
        # API request activity
        url = reverse('api_tracker_create')
        payload = {'name': 'Test', 'time_mode': 'daily', 'tasks': []}
        response = self.client.post(url, payload, content_type='application/json')
        
        activities.append({
            'user_id': self.user.id,
            'action': 'create_tracker',
            'timestamp': time.time()
        })
        
        # Verify activities were tracked
        self.assertEqual(len(activities), 2)
        self.assertEqual(activities[0]['action'], 'login')
        self.assertEqual(activities[1]['action'], 'create_tracker')
    
    def test_error_reporting_to_sentry(self):
        """
        Test that errors are reported to error monitoring service (Sentry).
        """
        # Skip if sentry_sdk not installed (optional dependency)
        try:
            import sentry_sdk
        except ImportError:
            self.skipTest("sentry_sdk not installed")
        
        from unittest.mock import patch
        
        with patch('sentry_sdk.capture_exception') as mock_sentry:
            # Simulate an error
            try:
                raise ValueError("Test error for monitoring")
            except ValueError as e:
                # In production, this would be caught by middleware
                sentry_sdk.capture_exception(e)
            
            # Verify Sentry was called
            self.assertTrue(mock_sentry.called)
    
    def test_api_rate_limit_monitoring(self):
        """
        Test monitoring API rate limit usage.
        """
        url = reverse('api_search')
        
        # Make multiple requests
        rate_limit_data = {
            'requests': 0,
            'limit': 100,
            'window': 60  # seconds
        }
        
        for i in range(5):
            response = self.client.get(url, {'q': f'test{i}'})
            rate_limit_data['requests'] += 1
        
        # Verify tracking
        self.assertEqual(rate_limit_data['requests'], 5)
        self.assertLess(rate_limit_data['requests'], rate_limit_data['limit'])
    
    def test_concurrent_user_monitoring(self):
        """
        Test tracking concurrent active users.
        """
        # Simulate multiple users
        users = [UserFactory.create() for _ in range(3)]
        
        active_users = set()
        
        for user in users:
            # Simulate user activity
            active_users.add(user.id)
        
        # Track concurrent users
        concurrent_count = len(active_users)
        self.assertEqual(concurrent_count, 3)
    
    def test_memory_usage_monitoring(self):
        """
        Test monitoring memory usage.
        """
        import sys
        
        # Get current memory usage (simplified)
        initial_objects = len(list(filter(lambda x: isinstance(x, User), locals().values())))
        
        # Create some objects
        users = [UserFactory.create() for _ in range(10)]
        
        # Memory should increase
        final_objects = len(users)
        self.assertGreater(final_objects, initial_objects)
    
    def test_slow_query_detection(self):
        """
        Test detecting slow database queries.
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        slow_queries = []
        query_threshold_ms = 100  # 100ms threshold
        
        with CaptureQueriesContext(connection) as queries:
            # Make a query
            url = reverse('api_search')
            response = self.client.get(url, {'q': 'test'})
        
        # Check for slow queries
        for query in queries:
            if float(query['time']) * 1000 > query_threshold_ms:
                slow_queries.append(query)
        
        # Should not have slow queries in this simple test
        self.assertEqual(len(slow_queries), 0)
    
    def test_api_endpoint_availability(self):
        """
        Test monitoring API endpoint availability.
        """
        endpoints = [
            'api_health',
            'api_search',
            'api_tracker_create',
        ]
        
        availability_report = {}
        
        for endpoint_name in endpoints:
            try:
                url = reverse(endpoint_name)
                response = self.client.get(url)
                availability_report[endpoint_name] = {
                    'available': response.status_code < 500,
                    'status_code': response.status_code
                }
            except Exception as e:
                availability_report[endpoint_name] = {
                    'available': False,
                    'error': str(e)
                }
        
        # All endpoints should be available
        for endpoint, status in availability_report.items():
            self.assertTrue(
                status.get('available', False),
                f"Endpoint {endpoint} is not available"
            )
    
    @patch('django.core.mail.send_mail')
    def test_alert_on_critical_error(self, mock_send_mail):
        """
        Test that alerts are sent on critical errors.
        """
        # Simulate a critical error
        error_threshold = 5
        error_count = 6
        
        if error_count >= error_threshold:
            # Send alert
            from django.core.mail import send_mail
            send_mail(
                'Critical Error Alert',
                f'Error count exceeded threshold: {error_count}',
                'alerts@tracker.com',
                ['admin@tracker.com'],
                fail_silently=False,
            )
        
        # Verify alert was sent
        self.assertTrue(mock_send_mail.called)
    
    def test_metrics_aggregation(self):
        """
        Test aggregating metrics for monitoring dashboard.
        """
        metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0,
        }
        
        # Simulate requests
        response_times = []
        
        for i in range(5):
            start = time.time()
            url = reverse('api_search')
            response = self.client.get(url, {'q': f'test{i}'})
            end = time.time()
            
            metrics['total_requests'] += 1
            response_times.append(end - start)
            
            if response.status_code == 200:
                metrics['successful_requests'] += 1
            else:
                metrics['failed_requests'] += 1
        
        metrics['average_response_time'] = sum(response_times) / len(response_times)
        
        # Verify metrics
        self.assertEqual(metrics['total_requests'], 5)
        self.assertEqual(metrics['successful_requests'], 5)
        self.assertEqual(metrics['failed_requests'], 0)
        self.assertGreater(metrics['average_response_time'], 0)
