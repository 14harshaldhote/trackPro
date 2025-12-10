"""
Base test classes for TrackPro API tests.

All test classes should inherit from BaseAPITestCase.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
import json

User = get_user_model()


class BaseAPITestCase(TestCase):
    """
    Base class for all API tests.
    
    Provides:
    - Pre-authenticated API client
    - Helper assertion methods
    - Test user setup
    """
    
    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Use Django's force_login which sets session-based auth
        # This makes request.user.is_authenticated return True
        self.client.force_login(self.user)
        self.token = None
    
    def tearDown(self):
        """Clean up after test."""
        self.client.logout()
    
    # =========================================================================
    # ASSERTION HELPERS
    # =========================================================================
    
    def assertSuccess(self, response, expected_status=200):
        """
        Assert response indicates success.
        
        Args:
            response: HTTP response object
            expected_status: Expected HTTP status code (default 200)
        
        Returns:
            Parsed JSON data
        """
        self.assertEqual(
            response.status_code, 
            expected_status,
            f"Expected {expected_status}, got {response.status_code}: {response.content[:500]}"
        )
        data = response.json()
        self.assertTrue(
            data.get('success', True),  # Some endpoints don't have 'success' field
            f"Expected success=True, got: {data}"
        )
        return data
    
    def assertError(self, response, expected_status=400):
        """
        Assert response indicates error.
        
        Args:
            response: HTTP response object
            expected_status: Expected HTTP status code (default 400)
        
        Returns:
            Parsed JSON data
        """
        self.assertEqual(
            response.status_code,
            expected_status,
            f"Expected {expected_status}, got {response.status_code}"
        )
        data = response.json()
        self.assertFalse(
            data.get('success', False),
            f"Expected success=False, got: {data}"
        )
        return data
    
    def assertUnauthorized(self, response):
        """Assert response is 401 Unauthorized."""
        self.assertIn(response.status_code, [401, 403])
    
    def assertNotFound(self, response):
        """Assert response is 404 Not Found."""
        self.assertEqual(response.status_code, 404)
    
    def assertValidationError(self, response, field=None):
        """
        Assert response has validation error.
        
        Args:
            response: HTTP response object
            field: Optional field name to check for error
        """
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        if field:
            # Check for field-specific error
            errors = data.get('errors', data.get('error', {}))
            if isinstance(errors, dict):
                self.assertIn(field, errors)
    
    # =========================================================================
    # REQUEST HELPERS
    # =========================================================================
    
    def get(self, url, **kwargs):
        """Make authenticated GET request."""
        return self.client.get(url, **kwargs)
    
    def post(self, url, data=None, **kwargs):
        """Make authenticated POST request."""
        return self.client.post(url, data, format='json', **kwargs)
    
    def put(self, url, data=None, **kwargs):
        """Make authenticated PUT request."""
        return self.client.put(url, data, format='json', **kwargs)
    
    def delete(self, url, **kwargs):
        """Make authenticated DELETE request."""
        return self.client.delete(url, **kwargs)
    
    # =========================================================================
    # DATA HELPERS
    # =========================================================================
    
    def create_tracker(self, **kwargs):
        """Create a test tracker for the authenticated user."""
        from core.tests.factories import TrackerFactory
        return TrackerFactory.create(self.user, **kwargs)
    
    def create_template(self, tracker, **kwargs):
        """Create a test task template."""
        from core.tests.factories import TemplateFactory
        return TemplateFactory.create(tracker, **kwargs)
    
    def create_instance(self, tracker, target_date=None, **kwargs):
        """Create a test tracker instance."""
        from core.tests.factories import InstanceFactory
        return InstanceFactory.create(tracker, target_date, **kwargs)
    
    def create_task_instance(self, instance, template, **kwargs):
        """Create a test task instance."""
        from core.tests.factories import TaskInstanceFactory
        return TaskInstanceFactory.create(instance, template, **kwargs)
    
    def create_task(self, instance, template=None, **kwargs):
        """Alias for create_task_instance for convenience."""
        if template is None:
            # Create a default template for the tracker
            template = self.create_template(instance.tracker)
        return self.create_task_instance(instance, template, **kwargs)


class BaseTransactionTestCase(TransactionTestCase):
    """
    Base class for tests that need real database transactions.
    
    Use this for tests involving:
    - select_for_update
    - Concurrent access
    - Database constraints
    """
    
    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)


class UnauthenticatedTestCase(TestCase):
    """
    Base class for tests without authentication.
    
    Use for testing:
    - Public endpoints
    - Authentication flows
    - Share link access
    """
    
    def setUp(self):
        """Set up test client without authentication."""
        self.client = APIClient()
    
    def assertRequiresAuth(self, response):
        """Assert that endpoint requires authentication."""
        self.assertIn(response.status_code, [401, 403])
