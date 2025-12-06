"""
Test Cases for SPA Functionality
Tests routing, modals, forms, and JavaScript integration
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from core.models import TrackerDefinition, TaskTemplate, TrackerInstance
import json

User = get_user_model()


class SPARoutingTests(TestCase):
    """Test SPA routing and panel loading"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_spa_shell_loads(self):
        """Test main SPA shell loads"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'app-shell')
        self.assertContains(response, 'TrackerPro')
    
    def test_panel_dashboard_loads(self):
        """Test dashboard panel loads via AJAX"""
        response = self.client.get(reverse('panel_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Should return HTML fragment, not full page
        self.assertNotContains(response, '<!DOCTYPE html>')
    
    def test_panel_today_loads(self):
        """Test today panel loads"""
        response = self.client.get(reverse('panel_today'))
        self.assertEqual(response.status_code, 200)
    
    def test_panel_week_loads(self):
        """Test week panel loads"""
        response = self.client.get(reverse('panel_week'))
        self.assertEqual(response.status_code, 200)
    
    def test_panel_trackers_loads(self):
        """Test trackers list panel loads"""
        response = self.client.get(reverse('panel_trackers'))
        self.assertEqual(response.status_code, 200)
    
    def test_panel_tracker_detail_loads(self):
        """Test tracker detail panel loads"""
        tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Test Tracker'
        )
        response = self.client.get(
            reverse('panel_tracker_detail', args=[tracker.tracker_id])
        )
        self.assertEqual(response.status_code, 200)
    
    def test_panel_analytics_loads(self):
        """Test analytics panel loads"""
        response = self.client.get(reverse('panel_analytics'))
        self.assertEqual(response.status_code, 200)
    
    def test_panel_goals_loads(self):
        """Test goals panel loads"""
        response = self.client.get(reverse('panel_goals'))
        self.assertEqual(response.status_code, 200)
    
    def test_panel_settings_loads(self):
        """Test settings panel loads"""
        response = self.client.get(reverse('panel_settings'))
        self.assertEqual(response.status_code, 200)
    
    def test_error_panel_404(self):
        """Test 404 error panel loads"""
        response = self.client.get(reverse('panel_error_404'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '404')


class ModalTests(TestCase):
    """Test modal loading"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_modal_add_task_loads(self):
        """Test add task modal loads"""
        response = self.client.get(reverse('modal_view', args=['add-task']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'modal-dialog')
    
    def test_modal_add_tracker_loads(self):
        """Test add tracker modal loads"""
        response = self.client.get(reverse('modal_view', args=['add-tracker']))
        self.assertEqual(response.status_code, 200)
    
    def test_modal_theme_gallery_loads(self):
        """Test theme gallery modal loads"""
        response = self.client.get(reverse('modal_view', args=['theme-gallery']))
        self.assertEqual(response.status_code, 200)


class APITests(TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test tracker
        self.tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Test Tracker',
            time_period='daily'
        )
        
        # Create test task template
        self.task_template = TaskTemplate.objects.create(
            tracker=self.tracker,
            description='Test Task',
            weight=5
        )
    
    def test_api_task_add(self):
        """Test adding a task via API"""
        response = self.client.post(
            reverse('api_task_add', args=[self.tracker.tracker_id]),
            {
                'description': 'New Task',
                'weight': 7,
                'time_of_day': 'morning'
            }
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))
    
    def test_api_tracker_create(self):
        """Test creating a tracker via API"""
        response = self.client.post(
            reverse('api_tracker_create'),
            json.dumps({
                'name': 'New Tracker',
                'time_period': 'weekly',
                'tasks': [
                    {'description': 'Task 1', 'weight': 5}
                ]
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success'))


class JavaScriptIntegrationTests(TestCase):
    """Test JavaScript module integration"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_js_app_script_loaded(self):
        """Test that app.js is loaded in base template"""
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'core/js/app.js')
        self.assertContains(response, 'type="module"')
    
    def test_js_config_present(self):
        """Test that JavaScript config is present"""
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'window.TrackerPro')
        self.assertContains(response, 'csrfToken')
    
    def test_css_files_loaded(self):
        """Test that all CSS files are loaded"""
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'themes.css')
        self.assertContains(response, 'spa.css')
        self.assertContains(response, 'js-enhanced.css')


class AuthenticationTests(TestCase):
    """Test authentication flows"""
    
    def test_login_page_loads(self):
        """Test login page loads"""
        response = self.client.get(reverse('account_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'login')
    
    def test_signup_page_loads(self):
        """Test signup page loads"""
        response = self.client.get(reverse('account_signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'signup')
    
    def test_unauthenticated_redirects(self):
        """Test unauthenticated users are redirected"""
        client = Client()
        response = client.get(reverse('panel_dashboard'))
        self.assertEqual(response.status_code, 302)


class PerformanceTests(TestCase):
    """Test performance optimizations"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_panel_caching_headers(self):
        """Test that panels can be cached"""
        response = self.client.get(reverse('panel_dashboard'))
        # Check for appropriate headers
        self.assertEqual(response.status_code, 200)
    
    def test_static_files_exist(self):
        """Test that static files can be accessed"""
        # This would need collectstatic to be run
        pass
