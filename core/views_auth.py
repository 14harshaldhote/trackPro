"""
Authentication API Views

Provides JSON API endpoints for AJAX-based authentication.
All views return JSON responses and integrate with django-allauth.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from rest_framework import serializers
from functools import wraps
import json
import hashlib


# ============================================================================
# RATE LIMITING
# ============================================================================

def rate_limit(max_requests: int, window_seconds: int, key_prefix: str = 'rate'):
    """
    Rate limiting decorator using Django cache.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
        key_prefix: Cache key prefix for this endpoint
        
    Returns 429 Too Many Requests if limit exceeded.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get client IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            
            # Create cache key
            ip_hash = hashlib.md5(ip.encode()).hexdigest()[:12]
            cache_key = f"{key_prefix}:{ip_hash}"
            
            # Get current count
            request_count = cache.get(cache_key, 0)
            
            if request_count >= max_requests:
                return JsonResponse({
                    'success': False,
                    'errors': {
                        'non_field_errors': [
                            f'Too many requests. Please try again in {window_seconds // 60} minutes.'
                        ]
                    },
                    'feedback': {
                        'type': 'error',
                        'message': 'Rate limit exceeded'
                    }
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, request_count + 1, window_seconds)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# SERIALIZERS (inline for simplicity)
# ============================================================================

class LoginSerializer(serializers.Serializer):
    """Validate login credentials"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, min_length=8)
    remember = serializers.BooleanField(required=False, default=False)


class SignupSerializer(serializers.Serializer):
    """Validate signup data"""
    email = serializers.EmailField(required=True)
    password1 = serializers.CharField(required=True, min_length=8)
    password2 = serializers.CharField(required=True, min_length=8)
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value
    
    def validate(self, data):
        """Check password match"""
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({
                'password2': 'Passwords do not match.'
            })
        return data


# ============================================================================
# API ENDPOINTS
# ============================================================================

@require_http_methods(["POST"])
@rate_limit(max_requests=5, window_seconds=300, key_prefix='login')  # 5 attempts per 5 minutes
def api_login(request):
    """
    Login via AJAX
    
    POST /api/auth/login/
    {
        "email": "user@example.com",
        "password": "password123",
        "remember": true
    }
    
    Returns: {"success": true, "redirect": "/"}
    """
    try:
        data = json.loads(request.body)
        serializer = LoginSerializer(data=data)
        
        if not serializer.is_valid():
            return JsonResponse({
                'success': False,
                'errors': serializer.errors
            }, status=400)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        remember = serializer.validated_data.get('remember', False)
        
        # Get user by email (allauth uses email as login method)
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'errors': {'email': ['Invalid email or password.']}
            }, status=400)
        
        # Authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Set session expiry based on remember me
            if not remember:
                request.session.set_expiry(0)  # Session expires on browser close
            
            return JsonResponse({
                'success': True,
                'redirect': '/',
                'user': {
                    'email': user.email,
                    'username': user.username,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': {'password': ['Invalid email or password.']}
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'errors': {'non_field_errors': ['Invalid JSON data.']}
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': {'non_field_errors': [str(e)]}
        }, status=500)


@require_http_methods(["POST"])
@rate_limit(max_requests=3, window_seconds=3600, key_prefix='signup')  # 3 signups per hour
def api_signup(request):
    """
    Signup via AJAX
    
    POST /api/auth/signup/
    {
        "email": "user@example.com",
        "password1": "password123",
        "password2": "password123"
    }
    
    Returns: {"success": true, "redirect": "/"}
    """
    try:
        data = json.loads(request.body)
        serializer = SignupSerializer(data=data)
        
        if not serializer.is_valid():
            return JsonResponse({
                'success': False,
                'errors': serializer.errors
            }, status=400)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password1']
        
        # Create user
        username = email.split('@')[0]  # Use email prefix as username
        
        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Auto-login after signup
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'redirect': '/',
            'user': {
                'email': user.email,
                'username': user.username,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'errors': {'non_field_errors': ['Invalid JSON data.']}
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'errors': {'non_field_errors': [str(e)]}
        }, status=500)


@require_http_methods(["GET", "POST"])
@login_required
def api_logout(request):
    """
    Logout via AJAX or Standard Request
    
    POST /api/auth/logout/ (AJAX)
    GET /logout/ (Standard)
    
    Returns: 
        - JSON {"success": true, "redirect": "/accounts/login/"} for AJAX/POST
        - Redirect to login page for GET
    """
    logout(request)
    
    if request.method == 'GET':
        from django.shortcuts import redirect
        return redirect('account_login')
        
    return JsonResponse({
        'success': True,
        'redirect': '/accounts/login/'
    })


@require_http_methods(["GET"])
@ensure_csrf_cookie
def api_check_auth(request):
    """
    Check authentication status
    
    GET /api/auth/status/
    
    Returns current user info if authenticated
    """
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'email': request.user.email,
                'username': request.user.username,
            }
        })
    else:
        return JsonResponse({
            'authenticated': False
        })


@require_http_methods(["POST"])
@rate_limit(max_requests=10, window_seconds=60, key_prefix='validate_email')  # 10 per minute
def api_validate_email(request):
    """
    Check if email is available (for real-time validation)
    
    POST /api/auth/validate-email/
    {"email": "test@example.com"}
    
    Returns: {"available": true/false}
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({'available': False, 'error': 'Email required'}, status=400)
        
        exists = User.objects.filter(email=email).exists()
        
        return JsonResponse({
            'available': not exists,
            'message': 'Email already registered.' if exists else 'Email available.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'available': False, 'error': 'Invalid JSON'}, status=400)


# ============================================================================
# AUTH PAGES (Render custom templates)
# ============================================================================

def login_page(request):
    """Render login page"""
    from django.shortcuts import render, redirect
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'auth/login.html')


def signup_page(request):
    """Render signup page"""
    from django.shortcuts import render, redirect
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'auth/signup.html')


def forgot_password(request):
    """Render forgot password page"""
    from django.shortcuts import render
    return render(request, 'auth/forgot_password.html')
