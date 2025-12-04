# Google OAuth Configuration Guide

## The Problem

You're seeing the error:
```
Error 400: redirect_uri_mismatch
```

This happens because the redirect URI configured in your Google Cloud Console doesn't match what django-allauth is using.

## How to Fix It

### Step 1: Find Your Redirect URI

Django-allauth uses this pattern for Google OAuth:
```
http://127.0.0.1:8000/accounts/google/login/callback/
```

For production, it will be:
```
https://yourdomain.com/accounts/google/login/callback/
```

### Step 2: Update Google Cloud Console

1. **Go to Google Cloud Console**
   - Visit: https://console.cloud.google.com/

2. **Navigate to your OAuth Application**
   - Go to "APIs & Services" → "Credentials"
   - Click on your OAuth 2.0 Client ID

3. **Add Authorized Redirect URIs**
   
   Add these URIs to your application:
   
   **For Development:**
   ```
   http://127.0.0.1:8000/accounts/google/login/callback/
   http://localhost:8000/accounts/google/login/callback/
   ```
   
   **For Production (when you deploy):**
   ```
   https://yourdomain.com/accounts/google/login/callback/
   ```

4. **Save Changes**
   - Click "Save" at the bottom

### Step 3: Restart Your Django Server

After updating the redirect URIs in Google Cloud Console, restart your Django server:

```bash
# Stop current server (Ctrl+C)
# Then restart
python manage.py runserver
```

### Step 4: Test Google Login

1. Navigate to: `http://localhost:8000/accounts/login/`
2. Click "Continue with Google"
3. You should now be redirected to Google's OAuth page successfully

## Troubleshooting

### Still Getting Error 400?

**Check these things:**

1. **Exact Match Required**
   - The URIs in Google Cloud Console must EXACTLY match what django-allauth uses
   - Include the trailing slash: `/callback/`
   - Use `127.0.0.1` not `localhost` (or add both)

2. **Wait a Few Minutes**
   - Google Cloud Console changes can take 1-2 minutes to propagate
   - Clear your browser cache and cookies

3. **Verify Your Settings**
   
   In `trackerWeb/settings.py`, confirm:
   ```python
   SOCIALACCOUNT_PROVIDERS = {
       'google': {
           'SCOPE': ['profile', 'email'],
           'AUTH_PARAMS': {
               'access_type': 'online',
           },
           'APP': {
               'client_id': 'YOUR_CLIENT_ID',
               'secret': 'YOUR_SECRET',
               'key': ''
           }
       }
   }
   ```

4. **Check Authorized JavaScript Origins**
   
   In Google Cloud Console, also add:
   ```
   http://127.0.0.1:8000
   http://localhost:8000
   ```

### Alternative: Disable Google OAuth Temporarily

If you want to test without Google OAuth:

1. Remove or comment out the Google OAuth button in templates:
   
   In `core/templates/account/login.html` and `signup.html`, comment out:
   ```html
   <!-- Temporarily disabled
   <a href="{% provider_login_url 'google' %}" class="btn-google">
       ...Google button content...
   </a>
   <div class="auth-divider"><span>or</span></div>
   -->
   ```

2. Use email/password authentication only until you fix the Google OAuth setup

## Quick Reference: Google Cloud Console

**Project:** Your Google Cloud Project  
**Location:** APIs & Services → Credentials  
**OAuth 2.0 Client IDs:** Click on your client  
**Authorized redirect URIs:** Add the callback URL  

**Remember:**
- Development: `http://127.0.0.1:8000/accounts/google/login/callback/`
- Production: `https://yourdomain.com/accounts/google/login/callback/`

## After Fixing

Once configured correctly:
- Users can sign in with Google
- Django-allauth automatically creates user accounts
- No email verification required for OAuth users
- User data (email, name) is pulled from Google

---

**Need More Help?**

1. Check your Google Cloud Console logs for more specific errors
2. Enable django-allauth debug logging in `settings.py`:
   ```python
   LOGGING = {
       'version': 1,
       'handlers': {
           'console': {
               'class': 'logging.StreamHandler',
           },
       },
       'loggers': {
           'allauth': {
               'handlers': ['console'],
               'level': 'DEBUG',
           },
       },
   }
   ```

3. Test the redirect URI directly in your browser to verify it's reachable
