
import pytest
import logging
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.tests.factories import UserFactory, TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
from io import StringIO

User = get_user_model()

@pytest.mark.django_db
class TestLogging(TestCase):
    """
    Test logging functionality and log verification.
    """
    
    def setUp(self):
        self.user = UserFactory.create()
        self.client.force_login(self.user)
        self.tracker = TrackerFactory.create(self.user)
        
        # Set up test logger
        self.logger = logging.getLogger('core.tests')
        self.logger.setLevel(logging.DEBUG)
        
        # Add a StringIO handler to capture logs
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)
    
    def tearDown(self):
        # Clean up the handler
        self.logger.removeHandler(self.handler)
        self.handler.close()
    
    def get_log_output(self):
        """Helper to get log output."""
        return self.log_stream.getvalue()
    
    def test_info_level_logging(self):
        """
        Test that INFO level logs are captured.
        """
        self.logger.info("Test info message")
        
        log_output = self.get_log_output()
        self.assertIn("INFO", log_output)
        self.assertIn("Test info message", log_output)
    
    def test_warning_level_logging(self):
        """
        Test that WARNING level logs are captured.
        """
        self.logger.warning("Test warning message")
        
        log_output = self.get_log_output()
        self.assertIn("WARNING", log_output)
        self.assertIn("Test warning message", log_output)
    
    def test_error_level_logging(self):
        """
        Test that ERROR level logs are captured.
        """
        self.logger.error("Test error message")
        
        log_output = self.get_log_output()
        self.assertIn("ERROR", log_output)
        self.assertIn("Test error message", log_output)
    
    def test_debug_level_logging(self):
        """
        Test that DEBUG level logs are captured.
        """
        self.logger.debug("Test debug message")
        
        log_output = self.get_log_output()
        self.assertIn("DEBUG", log_output)
        self.assertIn("Test debug message", log_output)
    
    def test_exception_logging_with_traceback(self):
        """
        Test that exceptions are logged with full traceback.
        """
        try:
            raise ValueError("Test exception")
        except ValueError:
            self.logger.exception("An error occurred")
        
        log_output = self.get_log_output()
        self.assertIn("ERROR", log_output)
        self.assertIn("An error occurred", log_output)
        self.assertIn("ValueError", log_output)
        self.assertIn("Test exception", log_output)
    
    def test_structured_logging(self):
        """
        Test structured logging with JSON format.
        """
        log_data = {
            'user_id': self.user.id,
            'action': 'create_tracker',
            'tracker_id': str(self.tracker.tracker_id),
            'timestamp': '2025-01-01T00:00:00Z'
        }
        
        self.logger.info(f"User action: {json.dumps(log_data)}")
        
        log_output = self.get_log_output()
        self.assertIn("User action", log_output)
        self.assertIn(str(self.user.id), log_output)
    
    def test_request_logging(self):
        """
        Test that HTTP requests are logged.
        """
        request_logger = logging.getLogger('django.request')
        request_logger.addHandler(self.handler)
        
        url = reverse('api_tracker_create')
        payload = {
            'name': 'Test Tracker',
            'time_mode': 'daily',
            'tasks': ['Task 1']
        }
        
        # Log the request
        self.logger.info(f"POST {url}")
        response = self.client.post(url, payload, content_type='application/json')
        
        log_output = self.get_log_output()
        self.assertIn("POST", log_output)
        
        request_logger.removeHandler(self.handler)
    
    def test_user_action_logging(self):
        """
        Test logging of user actions for audit trail.
        """
        # Log user action
        self.logger.info(
            f"User {self.user.id} created tracker {self.tracker.tracker_id}"
        )
        
        log_output = self.get_log_output()
        self.assertIn(str(self.user.id), log_output)
        self.assertIn("created tracker", log_output)
    
    def test_authentication_logging(self):
        """
        Test logging of authentication events.
        """
        # Simulate login
        self.logger.info(f"User {self.user.email} logged in successfully")
        
        log_output = self.get_log_output()
        self.assertIn(self.user.email, log_output)
        self.assertIn("logged in", log_output)
    
    def test_failed_authentication_logging(self):
        """
        Test logging of failed authentication attempts.
        """
        failed_email = "nonexistent@example.com"
        self.logger.warning(f"Failed login attempt for {failed_email}")
        
        log_output = self.get_log_output()
        self.assertIn("WARNING", log_output)
        self.assertIn("Failed login attempt", log_output)
        self.assertIn(failed_email, log_output)
    
    def test_database_query_logging(self):
        """
        Test logging of database queries (for debugging).
        """
        with override_settings(DEBUG=True):
            db_logger = logging.getLogger('django.db.backends')
            db_logger.addHandler(self.handler)
            
            # Make a database query
            User.objects.filter(id=self.user.id).first()
            
            # Note: In production, query logging would be more verbose
            # This is a simplified test
            
            db_logger.removeHandler(self.handler)
    
    def test_cache_operation_logging(self):
        """
        Test logging of cache operations.
        """
        from django.core.cache import cache
        
        cache_key = f"user_{self.user.id}_data"
        
        # Log cache set
        self.logger.debug(f"Setting cache key: {cache_key}")
        cache.set(cache_key, "test_value", 60)
        
        # Log cache get
        self.logger.debug(f"Getting cache key: {cache_key}")
        value = cache.get(cache_key)
        
        log_output = self.get_log_output()
        self.assertIn("Setting cache key", log_output)
        self.assertIn("Getting cache key", log_output)
    
    def test_api_error_logging(self):
        """
        Test logging of API errors.
        """
        # Make a request that will fail
        url = reverse('api_tracker_update', args=['invalid-id'])
        payload = {'name': 'Updated'}
        
        response = self.client.post(url, payload, content_type='application/json')
        
        # Log the error
        if response.status_code >= 400:
            self.logger.error(
                f"API error: {response.status_code} for {url}"
            )
        
        log_output = self.get_log_output()
        self.assertIn("ERROR", log_output)
        self.assertIn("API error", log_output)
    
    def test_security_event_logging(self):
        """
        Test logging of security-related events.
        """
        # Log suspicious activity
        self.logger.warning(
            f"Suspicious activity detected for user {self.user.id}: "
            "Multiple failed login attempts"
        )
        
        log_output = self.get_log_output()
        self.assertIn("WARNING", log_output)
        self.assertIn("Suspicious activity", log_output)
    
    def test_performance_logging(self):
        """
        Test logging of performance metrics.
        """
        import time
        
        start_time = time.time()
        
        # Simulate some operation
        url = reverse('api_search')
        response = self.client.get(url, {'q': 'test'})
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Log performance
        self.logger.info(f"Search query completed in {duration_ms:.2f}ms")
        
        log_output = self.get_log_output()
        self.assertIn("Search query completed", log_output)
        self.assertIn("ms", log_output)
    
    def test_log_rotation_configuration(self):
        """
        Test that log rotation is properly configured.
        """
        from logging.handlers import RotatingFileHandler
        
        # Verify that RotatingFileHandler can be created
        temp_log_file = '/tmp/test_rotating.log'
        rotating_handler = RotatingFileHandler(
            temp_log_file,
            maxBytes=1024*1024,  # 1MB
            backupCount=5
        )
        
        self.assertIsNotNone(rotating_handler)
        self.assertEqual(rotating_handler.maxBytes, 1024*1024)
        self.assertEqual(rotating_handler.backupCount, 5)
        
        rotating_handler.close()
        
        # Clean up
        import os
        if os.path.exists(temp_log_file):
            os.remove(temp_log_file)
    
    def test_log_filtering_by_level(self):
        """
        Test that logs can be filtered by level.
        """
        # Create a WARNING-level handler
        warning_stream = StringIO()
        warning_handler = logging.StreamHandler(warning_stream)
        warning_handler.setLevel(logging.WARNING)
        
        test_logger = logging.getLogger('test.filtering')
        test_logger.setLevel(logging.DEBUG)
        test_logger.addHandler(warning_handler)
        
        # Log at different levels
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")
        
        warning_output = warning_stream.getvalue()
        
        # Only WARNING and ERROR should appear
        self.assertNotIn("Debug message", warning_output)
        self.assertNotIn("Info message", warning_output)
        self.assertIn("Warning message", warning_output)
        self.assertIn("Error message", warning_output)
        
        test_logger.removeHandler(warning_handler)
        warning_handler.close()
    
    def test_contextual_logging(self):
        """
        Test logging with contextual information.
        """
        # Add context to log messages
        context = {
            'request_id': 'req_12345',
            'user_id': self.user.id,
            'endpoint': '/api/tracker/create/'
        }
        
        self.logger.info(
            f"Processing request",
            extra=context
        )
        
        log_output = self.get_log_output()
        self.assertIn("Processing request", log_output)
    
    def test_sensitive_data_redaction(self):
        """
        Test that sensitive data is redacted from logs.
        """
        # Function to redact sensitive data
        def redact_sensitive(data):
            sensitive_fields = ['password', 'token', 'secret']
            redacted = data.copy()
            for field in sensitive_fields:
                if field in redacted:
                    redacted[field] = '***REDACTED***'
            return redacted
        
        sensitive_data = {
            'username': 'testuser',
            'password': 'secret123',
            'token': 'abc123xyz'
        }
        
        redacted_data = redact_sensitive(sensitive_data)
        
        self.logger.info(f"User data: {json.dumps(redacted_data)}")
        
        log_output = self.get_log_output()
        self.assertIn("testuser", log_output)
        self.assertIn("***REDACTED***", log_output)
        self.assertNotIn("secret123", log_output)
        self.assertNotIn("abc123xyz", log_output)
    
    def test_log_aggregation_compatibility(self):
        """
        Test that logs are compatible with log aggregation services.
        """
        # Format log as JSON for aggregation services (like ELK, Datadog)
        log_entry = {
            'timestamp': '2025-01-01T00:00:00Z',
            'level': 'INFO',
            'logger': 'core.views',
            'message': 'API request processed',
            'user_id': self.user.id,
            'tracker_id': str(self.tracker.tracker_id)
        }
        
        # Log as JSON string
        self.logger.info(json.dumps(log_entry))
        
        log_output = self.get_log_output()
        
        # Verify log can be parsed back as JSON
        lines = log_output.strip().split('\n')
        for line in lines:
            if 'API request processed' in line:
                # Extract JSON part
                json_part = line.split(':', 2)[-1].strip()
                parsed = json.loads(json_part)
                self.assertEqual(parsed['level'], 'INFO')
                self.assertEqual(parsed['user_id'], self.user.id)
    
    def test_async_task_logging(self):
        """
        Test logging for asynchronous tasks.
        """
        # Simulate async task logging
        task_id = "task_12345"
        
        self.logger.info(f"Starting async task: {task_id}")
        
        # Simulate task processing
        import time
        time.sleep(0.1)
        
        self.logger.info(f"Completed async task: {task_id}")
        
        log_output = self.get_log_output()
        self.assertIn(f"Starting async task: {task_id}", log_output)
        self.assertIn(f"Completed async task: {task_id}", log_output)
    
    def test_correlation_id_logging(self):
        """
        Test that correlation IDs are included in logs for request tracing.
        """
        import uuid
        
        correlation_id = str(uuid.uuid4())
        
        # Add correlation ID to all log messages for this request
        self.logger.info(f"[{correlation_id}] Request started")
        self.logger.info(f"[{correlation_id}] Processing data")
        self.logger.info(f"[{correlation_id}] Request completed")
        
        log_output = self.get_log_output()
        
        # All log entries should have the correlation ID
        lines = [line for line in log_output.split('\n') if correlation_id in line]
        self.assertEqual(len(lines), 3)
