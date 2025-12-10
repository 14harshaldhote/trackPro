
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from core.views_auth import (
    api_login, api_signup, api_logout, api_check_auth, 
    api_validate_email, api_google_auth_mobile, api_apple_auth_mobile
)


@pytest.fixture
def factory():
    return RequestFactory()


@pytest.fixture
def mock_user():
    """Create a mock user for tests that don't need database access."""
    user = Mock(spec=User)
    user.username = 'testuser'
    user.email = 'test@example.com'
    user.id = 1
    user.first_name = 'Test'
    user.last_name = 'User'
    user.is_authenticated = True
    return user


def add_middleware_to_request(request, middleware_class):
    middleware = middleware_class(lambda x: x)
    middleware.process_request(request)
    request.session.save()


@pytest.mark.django_db
class TestViewsAuth:

    def test_api_login_success(self, factory, mock_user):
        data = {'email': 'test@example.com', 'password': 'password123'}
        request = factory.post(
            '/api/auth/login/',
            data=json.dumps(data),
            content_type='application/json'
        )
        add_middleware_to_request(request, SessionMiddleware)
        
        with patch('core.views_auth.User.objects.get') as mock_get_user, \
             patch('core.views_auth.authenticate') as mock_auth, \
             patch('core.views_auth.login') as mock_login:
            
            mock_get_user.return_value = mock_user
            mock_auth.return_value = mock_user
            
            response = api_login(request)
            assert response.status_code == 200
            resp_data = json.loads(response.content)
            assert resp_data['success'] is True
            mock_login.assert_called()

    def test_api_login_invalid_creds(self, factory):
        data = {'email': 'test@example.com', 'password': 'wrongpass'}
        request = factory.post(
            '/api/auth/login/',
            data=json.dumps(data),
            content_type='application/json'
        )
        add_middleware_to_request(request, SessionMiddleware)
        
        with patch('core.views_auth.User.objects.get') as mock_get_user, \
             patch('core.views_auth.authenticate') as mock_auth:
            
            mock_get_user.return_value = Mock(username='test')
            mock_auth.return_value = None
            
            response = api_login(request)
            assert response.status_code == 400
            resp_data = json.loads(response.content)
            assert resp_data['success'] is False

    def test_api_signup_success(self, factory):
        data = {
            'email': 'new@example.com', 
            'password1': 'password123',
            'password2': 'password123'
        }
        request = factory.post(
            '/api/auth/signup/',
            data=json.dumps(data),
            content_type='application/json'
        )
        add_middleware_to_request(request, SessionMiddleware)
        
        with patch('core.views_auth.User.objects.filter') as mock_filter, \
             patch('core.views_auth.User.objects.create_user') as mock_create, \
             patch('core.views_auth.login') as mock_login:
            
            mock_filter.return_value.exists.return_value = False
            mock_create.return_value = Mock(email='new@example.com', username='new')
            
            response = api_signup(request)
            assert response.status_code == 200
            mock_create.assert_called()

    def test_api_logout(self, factory):
        request = factory.post('/api/auth/logout/')
        add_middleware_to_request(request, SessionMiddleware)
        
        with patch('core.views_auth.logout') as mock_logout:
            response = api_logout(request)
            assert response.status_code == 200
            mock_logout.assert_called()

    def test_api_check_auth(self, factory, mock_user):
        """Test authentication status check with authenticated user."""
        request = factory.get('/api/auth/status/')
        request.user = mock_user
        
        response = api_check_auth(request)
        assert response.status_code == 200
        assert response.data['authenticated'] is True

    def test_api_check_auth_unauthenticated(self, factory):
        """Test authentication status check with unauthenticated user."""
        request = factory.get('/api/auth/status/')
        anon_user = Mock()
        anon_user.is_authenticated = False
        request.user = anon_user
        
        response = api_check_auth(request)
        assert response.status_code == 200
        assert response.data['authenticated'] is False

    def test_api_validate_email_available(self, factory):
        request = factory.post(
            '/api/auth/validate-email/',
            data=json.dumps({'email': 'check@example.com'}),
            content_type='application/json'
        )
        
        with patch('core.views_auth.User.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = False
            
            response = api_validate_email(request)
            assert response.status_code == 200
            resp_data = json.loads(response.content)
            assert resp_data['available'] is True

    def test_api_validate_email_taken(self, factory):
        """Test validation when email is already registered."""
        request = factory.post(
            '/api/auth/validate-email/',
            data=json.dumps({'email': 'existing@example.com'}),
            content_type='application/json'
        )
        
        with patch('core.views_auth.User.objects.filter') as mock_filter:
            mock_filter.return_value.exists.return_value = True
            
            response = api_validate_email(request)
            assert response.status_code == 200
            resp_data = json.loads(response.content)
            assert resp_data['available'] is False

    def test_api_google_auth_mobile_success(self, factory):
        """Test Google OAuth mobile authentication."""
        import sys
        
        data = {'id_token': 'fake_google_token'}
        request = factory.post(
            '/api/auth/google/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = 'google@example.com'
        mock_user.username = 'google'
        mock_user.first_name = 'Google'
        mock_user.last_name = 'User'
        mock_user.pk = 1
        
        mock_token = Mock()
        mock_token.access_token = 'mock_access_token'
        mock_token.__str__ = Mock(return_value='mock_refresh_token')
        
        # Create properly structured mock modules
        mock_id_token_module = MagicMock()
        mock_id_token_module.verify_oauth2_token = Mock(return_value={
            'iss': 'accounts.google.com',
            'email': 'google@example.com',
            'given_name': 'Google',
            'family_name': 'User'
        })
        
        mock_google_requests = MagicMock()
        mock_google_requests.Request = Mock(return_value=Mock())
        
        # Build the module hierarchy properly
        mock_google = MagicMock()
        mock_google_oauth2 = MagicMock()
        mock_google_oauth2.id_token = mock_id_token_module
        mock_google.oauth2 = mock_google_oauth2
        mock_google.oauth2.id_token = mock_id_token_module
        
        mock_google_auth = MagicMock()
        mock_google_auth_transport = MagicMock()
        mock_google_auth_transport.requests = mock_google_requests
        mock_google_auth.transport = mock_google_auth_transport
        mock_google_auth.transport.requests = mock_google_requests
        mock_google.auth = mock_google_auth
        
        # Pre-load mock modules into sys.modules
        original_modules = {}
        mock_modules = {
            'google': mock_google,
            'google.oauth2': mock_google_oauth2,
            'google.oauth2.id_token': mock_id_token_module,
            'google.auth': mock_google_auth,
            'google.auth.transport': mock_google_auth_transport,
            'google.auth.transport.requests': mock_google_requests,
        }
        
        for mod_name, mock_mod in mock_modules.items():
            original_modules[mod_name] = sys.modules.get(mod_name)
            sys.modules[mod_name] = mock_mod
        
        try:
            with patch('core.views_auth.User.objects.get_or_create') as mock_get_create, \
                 patch('core.views_auth.User.objects.exclude') as mock_exclude, \
                 patch('rest_framework_simplejwt.tokens.RefreshToken') as mock_refresh_class, \
                 patch('django.conf.settings') as mock_settings:
                 
                mock_settings.GOOGLE_IOS_CLIENT_ID = 'fake_client_id'
                mock_refresh_class.for_user.return_value = mock_token
                mock_get_create.return_value = (mock_user, True)
                mock_exclude.return_value.filter.return_value.exists.return_value = False
                
                response = api_google_auth_mobile(request)
                
            assert response.status_code == 200
            resp_data = json.loads(response.content)
            assert 'token' in resp_data
        finally:
            # Restore original modules
            for mod_name in mock_modules:
                if original_modules.get(mod_name) is not None:
                    sys.modules[mod_name] = original_modules[mod_name]
                elif mod_name in sys.modules:
                    del sys.modules[mod_name]

    def test_api_google_auth_mobile_missing_token(self, factory):
        """Test Google OAuth with missing token."""
        data = {}
        request = factory.post(
            '/api/auth/google/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        response = api_google_auth_mobile(request)
        assert response.status_code == 400

    def test_api_apple_auth_mobile_success(self, factory):
        """Test Apple OAuth mobile authentication."""
        data = {'idToken': 'fake_apple_token', 'first_name': 'Apple', 'last_name': 'User'}
        request = factory.post(
            '/api/auth/apple/mobile/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = 'apple@example.com'
        mock_user.username = 'apple'
        mock_user.first_name = 'Apple'
        mock_user.last_name = 'User'
        mock_user.pk = 1
        
        mock_token = Mock()
        mock_token.access_token = 'mock_access_token'
        mock_token.__str__ = Mock(return_value='mock_refresh_token')
        
        with patch('jwt.decode') as mock_decode, \
             patch('core.views_auth.User.objects.get_or_create') as mock_get_create, \
             patch('core.views_auth.User.objects.exclude') as mock_exclude, \
             patch('rest_framework_simplejwt.tokens.RefreshToken') as mock_refresh_class:
             
            mock_decode.return_value = {
                'email': 'apple@example.com',
                'iss': 'https://appleid.apple.com'
            }
            
            mock_get_create.return_value = (mock_user, True)
            mock_exclude.return_value.filter.return_value.exists.return_value = False
            mock_refresh_class.for_user.return_value = mock_token
            
            response = api_apple_auth_mobile(request)
            
            assert response.status_code == 200
            resp_data = json.loads(response.content)
            assert 'token' in resp_data

    def test_api_apple_auth_mobile_missing_token(self, factory):
        """Test Apple OAuth with missing token."""
        data = {'first_name': 'Apple'}
        request = factory.post(
            '/api/auth/apple/mobile/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        response = api_apple_auth_mobile(request)
        assert response.status_code == 400

    def test_api_apple_auth_mobile_invalid_issuer(self, factory):
        """Test Apple OAuth with invalid issuer."""
        data = {'idToken': 'fake_token'}
        request = factory.post(
            '/api/auth/apple/mobile/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {
                'email': 'apple@example.com',
                'iss': 'https://fake-issuer.com'
            }
            
            response = api_apple_auth_mobile(request)
            assert response.status_code == 400
