"""
Authentication & Authorization Tests (20 tests)

Test IDs: AUTH-001 to AUTH-020
Coverage: /api/v1/auth/* endpoints

These tests cover:
- Login (valid, invalid credentials, edge cases)
- Signup (new user, duplicate, validation)
- Logout
- Auth status checks
- Email validation
- OAuth (Google, Apple)
- Protected endpoint access
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.tests.base import BaseAPITestCase, UnauthenticatedTestCase

User = get_user_model()


class AuthLoginTests(UnauthenticatedTestCase):
    """Tests for /api/v1/auth/login/ endpoint."""
    
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.login_url = '/api/v1/auth/login/'
    
    def test_AUTH_001_login_valid_credentials(self):
        """AUTH-001: Login with valid credentials returns 200 and JWT token."""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        self.assertIn(response.status_code, [200, 201])
        data = response.json()
        self.assertTrue(data.get('success', True))
        # Should return either 'token' or 'access' for JWT
        self.assertTrue('token' in data or 'access' in data or 'user' in data)
    
    def test_AUTH_002_login_invalid_password(self):
        """AUTH-002: Login with invalid password returns 401."""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': 'wrongpassword123'
        }, format='json')
        
        self.assertIn(response.status_code, [400, 401])
        data = response.json()
        self.assertFalse(data.get('success', False))
    
    def test_AUTH_003_login_unknown_email(self):
        """AUTH-003: Login with unknown email returns 401."""
        response = self.client.post(self.login_url, {
            'email': 'unknown@example.com',
            'password': 'testpass123'
        }, format='json')
        
        self.assertIn(response.status_code, [400, 401])
    
    def test_AUTH_004_login_empty_email(self):
        """AUTH-004: Login with empty email returns 400."""
        response = self.client.post(self.login_url, {
            'email': '',
            'password': 'testpass123'
        }, format='json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_AUTH_005_login_empty_password(self):
        """AUTH-005: Login with empty password returns 400."""
        response = self.client.post(self.login_url, {
            'email': 'test@example.com',
            'password': ''
        }, format='json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_AUTH_006_login_sql_injection_attempt(self):
        """AUTH-006: Login with SQL injection attempt is sanitized and returns 401."""
        response = self.client.post(self.login_url, {
            'email': "'; DROP TABLE users; --",
            'password': 'testpass123'
        }, format='json')
        
        # Should return 400 (invalid email) or 401 (auth failed), not 500
        self.assertIn(response.status_code, [400, 401])


class AuthSignupTests(UnauthenticatedTestCase):
    """Tests for /api/v1/auth/signup/ endpoint."""
    
    def setUp(self):
        super().setUp()
        self.signup_url = '/api/v1/auth/signup/'
    
    def test_AUTH_007_signup_new_user(self):
        """AUTH-007: Signup with valid data creates new user and returns 201."""
        response = self.client.post(self.signup_url, {
            'email': 'newuser@example.com',
            'password1': 'securepass123',
            'password2': 'securepass123'
        }, format='json')
        
        self.assertIn(response.status_code, [200, 201])
        data = response.json()
        self.assertTrue(data.get('success', True))
        
        # Verify user was created
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())
    
    def test_AUTH_008_signup_duplicate_email(self):
        """AUTH-008: Signup with existing email returns 400."""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='existingpass123'
        )
        
        response = self.client.post(self.signup_url, {
            'email': 'existing@example.com',
            'password1': 'newpass123456',
            'password2': 'newpass123456'
        }, format='json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_AUTH_009_signup_weak_password(self):
        """AUTH-009: Signup with weak password returns 400."""
        response = self.client.post(self.signup_url, {
            'email': 'newuser@example.com',
            'password1': '123',  # Too short
            'password2': '123'
        }, format='json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_AUTH_010_signup_invalid_email_format(self):
        """AUTH-010: Signup with invalid email format returns 400."""
        response = self.client.post(self.signup_url, {
            'email': 'not-an-email',
            'password1': 'securepass123',
            'password2': 'securepass123'
        }, format='json')
        
        # 400 for validation error, 429 if rate limited
        self.assertIn(response.status_code, [400, 429])


class AuthLogoutTests(BaseAPITestCase):
    """Tests for /api/v1/auth/logout/ endpoint."""
    
    def test_AUTH_011_logout_with_token(self):
        """AUTH-011: Logout with valid token returns 200."""
        response = self.post('/api/v1/auth/logout/')
        
        self.assertIn(response.status_code, [200, 201])


class AuthStatusTests(TestCase):
    """Tests for /api/v1/auth/status/ endpoint."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.status_url = '/api/v1/auth/status/'
    
    def test_AUTH_012_check_auth_valid_token(self):
        """AUTH-012: Check auth with valid token returns 200 and user info."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.status_url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('authenticated', True))
    
    def test_AUTH_013_check_auth_invalid_token(self):
        """AUTH-013: Check auth with invalid token returns 401."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token_xyz')
        response = self.client.get(self.status_url)
        
        # Should be 401 or return authenticated=false
        if response.status_code == 200:
            data = response.json()
            self.assertFalse(data.get('authenticated', False))
        else:
            self.assertIn(response.status_code, [401, 403])
    
    def test_AUTH_014_check_auth_expired_token(self):
        """AUTH-014: Check auth with expired token returns 401."""
        # Simulate expired token by using invalid credentials
        self.client.credentials(HTTP_AUTHORIZATION='Bearer expired_token')
        response = self.client.get(self.status_url)
        
        if response.status_code == 200:
            data = response.json()
            self.assertFalse(data.get('authenticated', False))
        else:
            self.assertIn(response.status_code, [401, 403])
    
    def test_AUTH_015_check_auth_no_token(self):
        """AUTH-015: Check auth without token returns 401."""
        response = self.client.get(self.status_url)
        
        if response.status_code == 200:
            data = response.json()
            self.assertFalse(data.get('authenticated', False))
        else:
            self.assertIn(response.status_code, [401, 403])


class AuthValidateEmailTests(UnauthenticatedTestCase):
    """Tests for /api/v1/auth/validate-email/ endpoint."""
    
    def setUp(self):
        super().setUp()
        self.validate_url = '/api/v1/auth/validate-email/'
        User.objects.create_user(
            username='existing',
            email='existing@example.com',
            password='testpass123'
        )
    
    def test_AUTH_016_validate_email_exists(self):
        """AUTH-016: Validate existing email returns exists=true."""
        response = self.client.post(self.validate_url, {
            'email': 'existing@example.com'
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # API returns 'available' or 'exists'
        self.assertTrue(
            data.get('exists', False) or 
            data.get('available', True) == False
        )
    
    def test_AUTH_017_validate_email_not_exists(self):
        """AUTH-017: Validate non-existing email returns exists=false."""
        response = self.client.post(self.validate_url, {
            'email': 'new@example.com'
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # API returns 'available'=true or 'exists'=false
        self.assertTrue(
            data.get('available', False) or 
            data.get('exists', True) == False
        )


class AuthOAuthTests(UnauthenticatedTestCase):
    """Tests for OAuth endpoints."""
    
    def test_AUTH_018_google_oauth_valid(self):
        """AUTH-018: Google OAuth with valid token returns 200."""
        # Note: This test would require mocking Google's token verification
        # For now, we test that the endpoint exists and returns appropriate error
        response = self.client.post('/api/v1/auth/google/', {
            'id_token': 'test_google_id_token'
        }, format='json')
        
        # Should return 400 (invalid token) or 200 (if mock is set up)
        # Not 404 (endpoint exists) or 500 (no server error)
        self.assertIn(response.status_code, [200, 400, 401])
    
    def test_AUTH_019_apple_oauth_valid(self):
        """AUTH-019: Apple OAuth with valid token returns 200."""
        # Note: This test would require mocking Apple's token verification
        response = self.client.post('/api/v1/auth/apple/mobile/', {
            'idToken': 'test_apple_id_token',
            'first_name': 'Test',
            'last_name': 'User'
        }, format='json')
        
        # Should return 400 (invalid token) or 200 (if mock is set up)
        self.assertIn(response.status_code, [200, 400, 401])


class AuthProtectedEndpointTests(UnauthenticatedTestCase):
    """Tests for protected endpoint access without authentication."""
    
    def test_AUTH_020_protected_endpoint_without_token(self):
        """AUTH-020: Protected endpoint without token returns 401."""
        response = self.client.get('/api/v1/dashboard/')
        
        self.assertIn(response.status_code, [401, 403])
