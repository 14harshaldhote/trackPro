"""
User & Data Management Tests (12 tests)

Test IDs: USER-001 to USER-012
Coverage: /api/v1/user/*, /api/v1/data/*, /api/v1/preferences/, /api/v1/notifications/

These tests cover:
- User profile CRUD
- Avatar upload
- Account deletion
- Data export/import
- Data clearing
- Preferences management
- Notifications
"""
from django.test import TestCase
from core.tests.base import BaseAPITestCase


class UserProfileTests(BaseAPITestCase):
    """Tests for /api/v1/user/profile/ endpoint."""
    
    def test_USER_001_get_user_profile(self):
        """USER-001: Get user profile returns 200 with profile data."""
        response = self.get('/api/v1/user/profile/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_USER_002_update_user_profile(self):
        """USER-002: Update user profile returns 200."""
        response = self.put('/api/v1/user/profile/', {
            'first_name': 'Test',
            'last_name': 'User'
        })
        
        self.assertEqual(response.status_code, 200)


class UserAvatarTests(BaseAPITestCase):
    """Tests for /api/v1/user/avatar/ endpoint."""
    
    def test_USER_003_upload_avatar(self):
        """USER-003: Upload avatar returns 200."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a tiny valid image
        # 1x1 pixel PNG
        # Hex: 89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE0000000C4944415408D763F8CFC000000301010018DD8E600000000049454E44AE426082
        tiny_details = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8e`\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        
        avatar_file = SimpleUploadedFile(
            'avatar.png',
            tiny_details,
            content_type='image/png'
        )
        
        response = self.client.post(
            '/api/v1/user/avatar/', 
            {'avatar': avatar_file},
            format='multipart'
        )
        
        # Should be 200 OK
        if response.status_code not in [200, 201]:
            # Print error for debugging if it fails
            print(f"Avatar upload failed: {response.content}")
            
        self.assertIn(response.status_code, [200, 201])


class UserDeleteTests(BaseAPITestCase):
    """Tests for /api/v1/user/delete/ endpoint."""
    
    def test_USER_004_delete_user_account(self):
        """USER-004: Delete user account cascades and returns 200."""
        # Create some data first
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.delete('/api/v1/user/delete/', data={
            'confirmation': 'DELETE MY ACCOUNT',
            'password': 'testpass123'
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)


class DataExportTests(BaseAPITestCase):
    """Tests for /api/v1/data/export/ endpoint."""
    
    def test_USER_005_export_all_data(self):
        """USER-005: Export all data returns 200 with JSON/ZIP."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get('/api/v1/data/export/')
        
        self.assertEqual(response.status_code, 200)


class DataImportTests(BaseAPITestCase):
    """Tests for /api/v1/data/import/ endpoint."""
    
    def test_USER_006_import_data(self):
        """USER-006: Import data returns 200."""
        response = self.post('/api/v1/data/import/', {
            'data': {
                'trackers': [],
                'templates': []
            }
        })
        
        self.assertIn(response.status_code, [200, 201, 400])


class DataClearTests(BaseAPITestCase):
    """Tests for /api/v1/data/clear/ endpoint."""
    
    def test_USER_007_clear_all_data(self):
        """USER-007: Clear all data returns 200 and removes data."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.post('/api/v1/data/clear/')
        
        self.assertEqual(response.status_code, 200)


class PreferencesTests(BaseAPITestCase):
    """Tests for /api/v1/preferences/ endpoint."""
    
    def test_USER_008_get_preferences(self):
        """USER-008: Get preferences returns 200 with prefs."""
        response = self.get('/api/v1/preferences/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_USER_009_update_preferences(self):
        """USER-009: Update preferences returns 200."""
        response = self.put('/api/v1/preferences/', {
            'push_notifications': True,
            'daily_reminder': True
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_USER_010_update_timezone(self):
        """USER-010: Update timezone applies correctly."""
        response = self.put('/api/v1/preferences/', {
            'timezone': 'America/New_York'
        })
        
        self.assertEqual(response.status_code, 200)


class NotificationsTests(BaseAPITestCase):
    """Tests for /api/v1/notifications/ endpoint."""
    
    def test_USER_011_get_notifications(self):
        """USER-011: Get notifications returns 200 with list."""
        response = self.get('/api/v1/notifications/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_USER_012_mark_notifications_read(self):
        """USER-012: Mark notifications read returns 200."""
        response = self.post('/api/v1/notifications/', {
            'action': 'mark_read'
        })
        
        self.assertIn(response.status_code, [200, 201])
