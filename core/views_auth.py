"""
Authentication API Views

Provides JSON API endpoints for AJAX-based authentication.
All views return JSON responses and integrate with django-allauth.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
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
@csrf_exempt  # Mobile apps don't send CSRF tokens
@rate_limit(max_requests=10, window_seconds=300, key_prefix='login')  # 10 attempts per 5 minutes
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
                'redirect': '/',  # Root URL handles redirect based on auth status
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
@csrf_exempt  # Mobile apps don't send CSRF tokens
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
        
        # Auto-login after signup (must specify backend with multiple AUTHENTICATION_BACKENDS)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
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


@api_view(['GET'])
@permission_classes([AllowAny])
def api_check_auth(request):
    """
    Check authentication status via JWT or Session
    
    GET /api/auth/status/
    
    Returns current user info if authenticated
    """
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': {
                'email': request.user.email,
                'username': request.user.username,
            }
        })
    else:
        return Response({
            'authenticated': False
        })


@require_http_methods(["POST"])
@csrf_exempt  # Mobile apps don't send CSRF tokens
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


@require_http_methods(["POST"])
@csrf_exempt
@rate_limit(max_requests=20, window_seconds=300, key_prefix='google_mobile')
def api_google_auth_mobile(request):
    """
    Authenticate with Google ID token from iOS/mobile app and issue JWT.
    
    POST /api/auth/google/
    { "id_token": "<google_id_token>" }
    
    Returns:
    {
        "token": "<jwt_access_token>",
        "user": { ... }
    }
    """
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        from django.conf import settings
        from rest_framework_simplejwt.tokens import RefreshToken
        
        data = json.loads(request.body)
        token = data.get('idToken') or data.get('id_token')
        
        if not token:
            return JsonResponse({'detail': 'id_token is required.'}, status=400)
        
        # Verify the token with Google
        try:
            # We strictly verify against the iOS Client ID because the token comes from the iOS app
            CLIENT_ID = settings.GOOGLE_IOS_CLIENT_ID
            
            idinfo = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                audience=CLIENT_ID
            )
            
            # Check issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            # Get user info
            email = idinfo.get('email')
            if not email:
                raise ValueError('Email not found in token.')
                
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            
            # Get or create user
            # We match by email
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0], # Fallback username
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )
            
            # If created, ensure username uniqueness if collision occurred on default
            if created and User.objects.exclude(pk=user.pk).filter(username=user.username).exists():
                user.username = f"{user.username}{user.pk}"
                user.save()
            
            # Generate JWT (SimpleJWT)
            refresh = RefreshToken.for_user(user)
            
            return JsonResponse({
                'token': str(refresh.access_token),
                'refresh': str(refresh), # Optional: send refresh token if needed
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': f"{user.first_name} {user.last_name}".strip(),
                    'username': user.username
                }
            })
            
        except ValueError as e:
            return JsonResponse({'detail': f'Token verification failed: {str(e)}'}, status=400)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'detail': f'Internal Error: {str(e)}'}, status=500)


# ============================================================================
# AUTH PAGES (Render custom templates)
# ============================================================================

def login_page(request):
    """Render login page"""
    from django.shortcuts import render, redirect
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'account/login.html')


def signup_page(request):
    """Render signup page"""
    from django.shortcuts import render, redirect
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'account/signup.html')


def forgot_password(request):
    """Render forgot password page"""
    from django.shortcuts import render
    return render(request, 'auth/forgot_password.html')


@require_http_methods(["POST"])
@rate_limit(max_requests=10, window_seconds=300, key_prefix='apple_mobile')
def api_apple_auth_mobile(request):
    """
    Authenticate with Apple ID token from iOS/mobile app
    
    POST /api/auth/apple/mobile/
    {"idToken": "...", "first_name": "...", "last_name": "..."}
    """
    try:
        data = json.loads(request.body)
        token = data.get('idToken')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        if not token:
            return JsonResponse({
                'success': False,
                'errors': {'idToken': ['ID token is required.']}
            }, status=400)
            
        # Validate JWT
        try:
            import jwt
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            email = decoded.get('email')
            if not email:
                 return JsonResponse({'success': False, 'errors': {'email': ['Email not shared.']}}, status=400)
                 
            # Verify issuer
            if decoded.get('iss') != 'https://appleid.apple.com':
                return JsonResponse({'success': False, 'errors': {'idToken': ['Invalid issuer']}}, status=400)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': first_name or '',
                    'last_name': last_name or ''
                }
            )
            
            if created:
                base = user.username
                ctr = 1
                while User.objects.exclude(pk=user.pk).filter(username=user.username).exists():
                    user.username = f"{base}{ctr}"
                    ctr += 1
                user.save()
            elif first_name or last_name:
                if first_name and not user.first_name: user.first_name = first_name
                if last_name and not user.last_name: user.last_name = last_name
                user.save()
            
            # Generate JWT tokens (same as Google auth)
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            
            return JsonResponse({
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'username': user.username,
                }
            })
            
        except ImportError:
             return JsonResponse({
                'success': False, 
                'errors': {'non_field_errors': ['PyJWT library not installed']}
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': {'idToken': [f'Invalid token: {str(e)}']}
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': {'non_field_errors': ['Invalid JSON']}}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'errors': {'non_field_errors': [str(e)]}}, status=500)
