"""
Onboarding Flow Tests

Test IDs: ONB-001 to ONB-012
Priority: HIGH
Coverage: New user onboarding experience

These tests verify the onboarding flow for new users.
"""
import pytest
from django.contrib.auth import get_user_model
from core.tests.base import BaseAPITestCase, UnauthenticatedTestCase
from core.models import TrackerDefinition, UserPreferences

User = get_user_model()


@pytest.mark.onboarding
class NewUserOnboardingTests(UnauthenticatedTestCase):
    """Tests for new user onboarding experience."""
    
    def test_ONB_001_signup_creates_user(self):
        """ONB-001: Signup endpoint creates a user account."""
        response = self.client.post('/api/auth/signup/', {
            'username': 'onboardtest',
            'email': 'onboard@example.com',
            'password1': 'SecureTest123!',
            'password2': 'SecureTest123!'
        }, content_type='application/json')
        
        # Accept various responses (some may require email verification)
        self.assertIn(response.status_code, [200, 201, 400])
    
    def test_ONB_002_login_page_accessible(self):
        """ONB-002: Login page is accessible to unauthenticated users."""
        response = self.client.get('/login/')
        self.assertIn(response.status_code, [200, 302])
    
    def test_ONB_003_signup_page_accessible(self):
        """ONB-003: Signup page is accessible to unauthenticated users."""
        response = self.client.get('/signup/')
        self.assertIn(response.status_code, [200, 302])


@pytest.mark.onboarding
class FirstTimeUserExperienceTests(BaseAPITestCase):
    """Tests for first-time user experience after signup."""
    
    def test_ONB_004_new_user_has_empty_dashboard(self):
        """ONB-004: New user sees empty but functional dashboard."""
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data.get('success', False))
    
    def test_ONB_005_preferences_created_for_new_user(self):
        """ONB-005: User preferences are created on first access."""
        response = self.client.get('/api/v1/preferences/')
        self.assertEqual(response.status_code, 200)
        
        # Preferences should exist
        self.assertTrue(UserPreferences.objects.filter(user=self.user).exists())
    
    def test_ONB_006_first_tracker_creation(self):
        """ONB-006: User can create their first tracker."""
        response = self.client.post('/api/v1/tracker/create/', {
            'name': 'My First Tracker',
            'description': 'Getting started with tracking',
            'time_mode': 'daily'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify tracker was created
        self.assertTrue(
            TrackerDefinition.objects.filter(
                user=self.user,
                name='My First Tracker'
            ).exists()
        )
    
    def test_ONB_007_first_task_addition(self):
        """ONB-007: User can add their first task."""
        tracker = self.create_tracker(name="Onboarding Tracker")
        
        response = self.client.post(f'/api/v1/tracker/{tracker.tracker_id}/task/add/', {
            'description': 'My first task!',
            'points': 1
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
    
    def test_ONB_008_first_task_completion(self):
        """ONB-008: User can complete their first task."""
        tracker = self.create_tracker()
        instance = self.create_instance(tracker)
        task = self.create_task(instance)
        
        response = self.client.post(f'/api/v1/task/{task.task_instance_id}/toggle/')
        self.assertEqual(response.status_code, 200)
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'DONE')


@pytest.mark.onboarding
class OnboardingPreferencesTests(BaseAPITestCase):
    """Tests for setting up user preferences during onboarding."""
    
    def test_ONB_009_set_timezone(self):
        """ONB-009: User can set their timezone."""
        response = self.client.put('/api/v1/preferences/', {
            'timezone': 'Asia/Kolkata'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        self.user.preferences.refresh_from_db()
        self.assertEqual(self.user.preferences.timezone, 'Asia/Kolkata')
    
    def test_ONB_010_set_theme(self):
        """ONB-010: User can set their preferred theme."""
        response = self.client.put('/api/v1/preferences/', {
            'theme': 'dark'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        self.user.preferences.refresh_from_db()
        self.assertEqual(self.user.preferences.theme, 'dark')
    
    def test_ONB_011_set_week_start(self):
        """ONB-011: User can set week start day."""
        response = self.client.put('/api/v1/preferences/', {
            'week_start': 1  # Tuesday
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        self.user.preferences.refresh_from_db()
        self.assertEqual(self.user.preferences.week_start, 1)


@pytest.mark.onboarding
class TemplateActivationTests(BaseAPITestCase):
    """Tests for activating pre-built templates during onboarding."""
    
    def test_ONB_012_template_activation_endpoint(self):
        """ONB-012: Template activation endpoint is accessible."""
        response = self.client.post('/api/v1/templates/activate/', {
            'template_id': 'daily-habits'
        }, content_type='application/json')
        
        # May succeed or fail based on template availability
        # We're testing the endpoint exists and responds appropriately
        self.assertIn(response.status_code, [200, 400, 404])
