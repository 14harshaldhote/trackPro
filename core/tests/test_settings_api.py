"""
Automated Tests for Settings API Endpoints
Tests all 6 new API endpoints: profile, avatar, data export/import, clear, delete
"""
import json
import io
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from core.models import TrackerDefinition, TaskTemplate, UserPreferences, Goal


class SettingsAPITestCase(TestCase):
    """Base test case with common setup for all settings tests"""
    
    def setUp(self):
        """Create test user and authenticate"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create user preferences
        self.prefs = UserPreferences.objects.create(
            user=self.user,
            timezone='UTC',
            date_format='YYYY-MM-DD',
            week_start=0,
            theme='light'
        )
    
    def tearDown(self):
        """Clean up test data"""
        User.objects.all().delete()
        TrackerDefinition.objects.all().delete()
        TaskTemplate.objects.all().delete()
        UserPreferences.objects.all().delete()


class UserProfileAPITests(SettingsAPITestCase):
    """Tests for GET/PUT /api/v1/user/profile/"""
    
    def test_get_profile_authenticated(self):
        """Test getting user profile returns correct data"""
        response = self.client.get('/api/v1/user/profile/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['profile']['email'], 'test@example.com')
        self.assertEqual(data['profile']['first_name'], 'Test')
        self.assertEqual(data['profile']['last_name'], 'User')
        self.assertEqual(data['profile']['username'], 'testuser')
        self.assertEqual(data['profile']['timezone'], 'UTC')
        self.assertEqual(data['profile']['date_format'], 'YYYY-MM-DD')
        self.assertEqual(data['profile']['week_start'], 0)
    
    def test_get_profile_unauthenticated(self):
        """Test getting profile requires authentication"""
        self.client.logout()
        response = self.client.get('/api/v1/user/profile/')
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_update_profile_success(self):
        """Test updating profile with valid data"""
        response = self.client.put(
            '/api/v1/user/profile/',
            data=json.dumps({
                'first_name': 'John',
                'last_name': 'Doe',
                'timezone': 'Asia/Kolkata',
                'date_format': 'DD/MM/YYYY',
                'week_start': 1
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Profile updated successfully')
        self.assertEqual(data['profile']['first_name'], 'John')
        self.assertEqual(data['profile']['last_name'], 'Doe')
        self.assertEqual(data['profile']['timezone'], 'Asia/Kolkata')
        self.assertEqual(data['profile']['date_format'], 'DD/MM/YYYY')
        self.assertEqual(data['profile']['week_start'], 1)
        
        # Verify database was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        
        self.prefs.refresh_from_db()
        self.assertEqual(self.prefs.timezone, 'Asia/Kolkata')
    
    def test_update_email_unique_validation(self):
        """Test email uniqueness validation"""
        # Create another user with different email
        User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='pass123'
        )
        
        # Try to update current user's email to existing one
        response = self.client.put(
            '/api/v1/user/profile/',
            data=json.dumps({'email': 'other@example.com'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('already in use', data['error'])
    
    def test_update_profile_invalid_json(self):
        """Test updating with invalid JSON returns error"""
        response = self.client.put(
            '/api/v1/user/profile/',
            data='invalid json{',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid JSON', data['error'])


class AvatarAPITests(SettingsAPITestCase):
    """Tests for POST/DELETE /api/v1/user/avatar/"""
    
    def create_test_image(self, format='JPEG', size=(100, 100), color='red'):
        """Helper to create test image file"""
        file = io.BytesIO()
        image = Image.new('RGB', size, color)
        image.save(file, format)
        file.seek(0)
        return file
    
    @override_settings(MEDIA_ROOT='/tmp/test_media')
    def test_upload_avatar_success(self):
        """Test successful avatar upload"""
        image_file = self.create_test_image()
        avatar = SimpleUploadedFile(
            'test_avatar.jpg',
            image_file.read(),
            content_type='image/jpeg'
        )
        
        response = self.client.post(
            '/api/v1/user/avatar/',
            {'avatar': avatar}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Avatar uploaded successfully')
        self.assertIn('avatar_url', data)
        self.assertIn('user_', data['avatar_url'])
    
    def test_upload_avatar_no_file(self):
        """Test upload without file returns error"""
        response = self.client.post('/api/v1/user/avatar/', {})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('No avatar file provided', data['error'])
    
    def test_upload_avatar_invalid_type(self):
        """Test upload with invalid file type"""
        text_file = SimpleUploadedFile(
            'test.txt',
            b'not an image',
            content_type='text/plain'
        )
        
        response = self.client.post(
            '/api/v1/user/avatar/',
            {'avatar': text_file}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid file type', data['error'])
    
    def test_upload_avatar_too_large(self):
        """Test upload with file size > 5MB"""
        # Create a large fake file (6MB)
        large_file = SimpleUploadedFile(
            'large.jpg',
            b'x' * (6 * 1024 * 1024),
            content_type='image/jpeg'
        )
        
        response = self.client.post(
            '/api/v1/user/avatar/',
            {'avatar': large_file}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('too large', data['error'])
    
    @override_settings(MEDIA_ROOT='/tmp/test_media')
    def test_remove_avatar_success(self):
        """Test successful avatar removal"""
        response = self.client.delete('/api/v1/user/avatar/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Avatar removed successfully')
        self.assertIn('default-avatar', data['avatar_url'])


class DataExportAPITests(SettingsAPITestCase):
    """Tests for POST /api/v1/data/export/"""
    
    def setUp(self):
        super().setUp()
        
        # Create test tracker and tasks
        self.tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Test Tracker',
            description='Test Description',
            time_mode='daily',
            status='active'
        )
        
        self.task1 = TaskTemplate.objects.create(
            tracker=self.tracker,
            description='Task 1',
            category='Work',
            weight=1,
            time_of_day='morning'
        )
        
        self.task2 = TaskTemplate.objects.create(
            tracker=self.tracker,
            description='Task 2',
            category='Personal',
            weight=2,
            time_of_day='evening'
        )
    
    def test_export_json_success(self):
        """Test exporting data as JSON"""
        response = self.client.post(
            '/api/v1/data/export/',
            data=json.dumps({'format': 'json'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response['Content-Disposition'])
        
        data = response.json()
        
        self.assertIn('export_date', data)
        self.assertIn('user', data)
        self.assertIn('trackers', data)
        self.assertIn('preferences', data)
        
        # Verify tracker data
        self.assertEqual(len(data['trackers']), 1)
        tracker_data = data['trackers'][0]
        self.assertEqual(tracker_data['name'], 'Test Tracker')
        self.assertEqual(len(tracker_data['tasks']), 2)
    
    def test_export_csv_success(self):
        """Test exporting data as CSV"""
        response = self.client.post(
            '/api/v1/data/export/',
            data=json.dumps({'format': 'csv'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Verify CSV content
        csv_content = response.content.decode('utf-8')
        self.assertIn('Tracker Name', csv_content)
        self.assertIn('Test Tracker', csv_content)
        self.assertIn('Task 1', csv_content)
        self.assertIn('Task 2', csv_content)
    
    def test_export_invalid_format(self):
        """Test export with invalid format"""
        response = self.client.post(
            '/api/v1/data/export/',
            data=json.dumps({'format': 'pdf'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid format', data['error'])
    
    def test_export_default_format(self):
        """Test export defaults to JSON if format not specified"""
        response = self.client.post(
            '/api/v1/data/export/',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')


class DataImportAPITests(SettingsAPITestCase):
    """Tests for POST /api/v1/data/import/"""
    
    def create_valid_export_json(self):
        """Helper to create valid export JSON"""
        export_data = {
            'export_date': '2024-01-01T00:00:00',
            'user': {
                'username': 'testuser',
                'email': 'test@example.com'
            },
            'trackers': [
                {
                    'tracker_id': 'test-tracker-1',
                    'name': 'Imported Tracker',
                    'description': 'Imported Description',
                    'time_mode': 'daily',
                    'status': 'active',
                    'created_at': '2024-01-01T00:00:00',
                    'tasks': [
                        {
                            'template_id': 'task-1',
                            'description': 'Imported Task 1',
                            'category': 'Work',
                            'weight': 1,
                            'time_of_day': 'morning'
                        },
                        {
                            'template_id': 'task-2',
                            'description': 'Imported Task 2',
                            'category': 'Personal',
                            'weight': 2,
                            'time_of_day': 'evening'
                        }
                    ]
                }
            ],
            'preferences': {}
        }
        
        json_file = io.BytesIO(json.dumps(export_data).encode('utf-8'))
        return SimpleUploadedFile('export.json', json_file.read(), content_type='application/json')
    
    def test_import_success(self):
        """Test successful data import"""
        import_file = self.create_valid_export_json()
        
        response = self.client.post(
            '/api/v1/data/import/',
            {'file': import_file}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['imported_trackers'], 1)
        self.assertEqual(data['imported_tasks'], 2)
        
        # Verify data was imported
        tracker = TrackerDefinition.objects.get(name='Imported Tracker')
        self.assertEqual(tracker.user, self.user)
        self.assertEqual(tracker.time_mode, 'daily')
        
        tasks = TaskTemplate.objects.filter(tracker=tracker)
        self.assertEqual(tasks.count(), 2)
    
    def test_import_no_file(self):
        """Test import without file"""
        response = self.client.post('/api/v1/data/import/', {})
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('No file provided', data['error'])
    
    def test_import_invalid_file_type(self):
        """Test import with non-JSON file"""
        text_file = SimpleUploadedFile('test.txt', b'not json', content_type='text/plain')
        
        response = self.client.post(
            '/api/v1/data/import/',
            {'file': text_file}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Only JSON files', data['error'])
    
    def test_import_invalid_json(self):
        """Test import with invalid JSON content"""
        invalid_json = SimpleUploadedFile(
            'invalid.json',
            b'{ invalid json',
            content_type='application/json'
        )
        
        response = self.client.post(
            '/api/v1/data/import/',
            {'file': invalid_json}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid JSON', data['error'])
    
    def test_import_missing_trackers_key(self):
        """Test import with missing trackers key in JSON"""
        invalid_export = json.dumps({'user': {}, 'preferences': {}})
        invalid_file = SimpleUploadedFile(
            'invalid.json',
            invalid_export.encode('utf-8'),
            content_type='application/json'
        )
        
        response = self.client.post(
            '/api/v1/data/import/',
            {'file': invalid_file}
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('missing trackers data', data['error'])


class ClearDataAPITests(SettingsAPITestCase):
    """Tests for POST /api/v1/data/clear/"""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Test Tracker',
            time_mode='daily',
            status='active'
        )
        
        self.goal = Goal.objects.create(
            user=self.user,
            title='Test Goal',
            description='Test Description',
            target_date='2024-12-31'
        )
    
    def test_clear_data_success(self):
        """Test successful data clearing"""
        response = self.client.post(
            '/api/v1/data/clear/',
            data=json.dumps({'confirmation': 'DELETE ALL DATA'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'All data cleared successfully')
        self.assertIn('deleted_counts', data)
        self.assertEqual(data['deleted_counts']['trackers'], 1)
        self.assertEqual(data['deleted_counts']['goals'], 1)
        
        # Verify soft delete (data still exists but marked deleted)
        self.tracker.refresh_from_db()
        self.assertIsNotNone(self.tracker.deleted_at)
        
        self.goal.refresh_from_db()
        self.assertIsNotNone(self.goal.deleted_at)
    
    def test_clear_data_invalid_confirmation(self):
        """Test clear data with wrong confirmation string"""
        response = self.client.post(
            '/api/v1/data/clear/',
            data=json.dumps({'confirmation': 'wrong string'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid confirmation', data['error'])
        
        # Verify data was NOT deleted
        self.tracker.refresh_from_db()
        self.assertIsNone(self.tracker.deleted_at)
    
    def test_clear_data_missing_confirmation(self):
        """Test clear data without confirmation"""
        response = self.client.post(
            '/api/v1/data/clear/',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])


class DeleteAccountAPITests(SettingsAPITestCase):
    """Tests for DELETE /api/v1/user/delete/"""
    
    def test_delete_account_success(self):
        """Test successful account deletion"""
        response = self.client.delete(
            '/api/v1/user/delete/',
            data=json.dumps({
                'confirmation': 'DELETE MY ACCOUNT',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('permanently deleted', data['message'])
        self.assertEqual(data['redirect'], '/logout/')
        
        # Verify user was completely deleted (hard delete)
        self.assertFalse(User.objects.filter(username='testuser').exists())
    
    def test_delete_account_wrong_password(self):
        """Test delete account with incorrect password"""
        response = self.client.delete(
            '/api/v1/user/delete/',
            data=json.dumps({
                'confirmation': 'DELETE MY ACCOUNT',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Incorrect password', data['error'])
        
        # Verify user still exists
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_delete_account_invalid_confirmation(self):
        """Test delete account with wrong confirmation"""
        response = self.client.delete(
            '/api/v1/user/delete/',
            data=json.dumps({
                'confirmation': 'wrong confirmation',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid confirmation', data['error'])
        
        # Verify user still exists
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_delete_account_missing_password(self):
        """Test delete account without password"""
        response = self.client.delete(
            '/api/v1/user/delete/',
            data=json.dumps({
                'confirmation': 'DELETE MY ACCOUNT'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        
        self.assertFalse(data['success'])


class IntegrationTests(SettingsAPITestCase):
    """Integration tests for combined workflows"""
    
    def test_export_and_reimport_workflow(self):
        """Test exporting data and re-importing it"""
        # Create test data
        tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Original Tracker',
            time_mode='daily'
        )
        
        TaskTemplate.objects.create(
            tracker=tracker,
            description='Original Task',
            category='Work'
        )
        
        # Export data
        export_response = self.client.post(
            '/api/v1/data/export/',
            data=json.dumps({'format': 'json'}),
            content_type='application/json'
        )
        
        self.assertEqual(export_response.status_code, 200)
        export_data = export_response.json()
        
        # Clear original data
        clear_response = self.client.post(
            '/api/v1/data/clear/',
            data=json.dumps({'confirmation': 'DELETE ALL DATA'}),
            content_type='application/json'
        )
        
        self.assertEqual(clear_response.status_code, 200)
        
        # Re-import data
        import_file = SimpleUploadedFile(
            'export.json',
            json.dumps(export_data).encode('utf-8'),
            content_type='application/json'
        )
        
        import_response = self.client.post(
            '/api/v1/data/import/',
            {'file': import_file}
        )
        
        self.assertEqual(import_response.status_code, 200)
        import_data = import_response.json()
        
        self.assertTrue(import_data['success'])
        self.assertEqual(import_data['imported_trackers'], 1)
        self.assertEqual(import_data['imported_tasks'], 1)
        
        # Verify re-imported data
        new_tracker = TrackerDefinition.objects.filter(
            user=self.user,
            deleted_at__isnull=True,
            name='Original Tracker'
        ).first()
        
        self.assertIsNotNone(new_tracker)
        
        # Use correct relationship name
        task_count = TaskTemplate.objects.filter(tracker=new_tracker).count()
        self.assertEqual(task_count, 1)
    
    def test_profile_update_persistence(self):
        """Test profile updates persist correctly"""
        # Update profile
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'timezone': 'America/New_York',
            'date_format': 'MM/DD/YYYY',
            'week_start': 6
        }
        
        update_response = self.client.put(
            '/api/v1/user/profile/',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(update_response.status_code, 200)
        
        # Logout and login again
        self.client.logout()
        self.client.login(username='testuser', password='testpass123')
        
        # Verify profile persisted
        get_response = self.client.get('/api/v1/user/profile/')
        
        self.assertEqual(get_response.status_code, 200)
        profile = get_response.json()['profile']
        
        self.assertEqual(profile['first_name'], 'Updated')
        self.assertEqual(profile['last_name'], 'Name')
        self.assertEqual(profile['email'], 'updated@example.com')
        self.assertEqual(profile['timezone'], 'America/New_York')
        self.assertEqual(profile['date_format'], 'MM/DD/YYYY')
        self.assertEqual(profile['week_start'], 6)
