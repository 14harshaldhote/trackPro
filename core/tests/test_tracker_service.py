from django.test import TestCase
from django.contrib.auth import get_user_model
from core.services.tracker_service import TrackerService
from core.models import TrackerDefinition
from core.exceptions import TrackerNotFoundError, ValidationError as AppValidationError

User = get_user_model()

class TrackerServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.service = TrackerService()
        
    def test_create_tracker_success(self):
        """Test successful tracker creation"""
        data = {
            'name': 'Daily Habit',
            'description': 'Test Description',
            'time_mode': 'daily',
            'tasks': ['Task 1', 'Task 2']
        }
        
        result = self.service.create_tracker(self.user, data)
        
        self.assertIn('id', result)
        self.assertEqual(result['name'], 'Daily Habit')
        
        # Verify DB
        tracker = TrackerDefinition.objects.get(tracker_id=result['id'])
        self.assertEqual(tracker.user, self.user)
        self.assertEqual(tracker.status, 'active')
        self.assertEqual(tracker.templates.count(), 2)

    def test_create_tracker_validation_error(self):
        """Test validation failure (short name)"""
        data = {
            'name': 'A', # Too short
            'description': 'Test'
        }
        
        with self.assertRaises(AppValidationError):
            self.service.create_tracker(self.user, data)

    def test_update_tracker_success(self):
        """Test successful update"""
        tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='Old Name',
            tracker_id='test-id'
        )
        
        update_data = {'name': 'New Name'}
        self.service.update_tracker('test-id', self.user, update_data)
        
        tracker.refresh_from_db()
        self.assertEqual(tracker.name, 'New Name')

    def test_update_tracker_not_found(self):
        """Test update non-existent tracker"""
        with self.assertRaises(TrackerNotFoundError):
            self.service.update_tracker('missing-id', self.user, {})

    def test_get_tracker_by_id_success(self):
        """Test fetch by ID"""
        tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='My Tracker',
            tracker_id='test-id-2'
        )
        
        fetched = self.service.get_tracker_by_id('test-id-2', self.user)
        self.assertEqual(fetched.name, 'My Tracker')

    def test_get_tracker_by_id_not_found(self):
        """Test fetch missing ID raises domain exception"""
        with self.assertRaises(TrackerNotFoundError):
            self.service.get_tracker_by_id('missing', self.user)

    def test_delete_tracker(self):
        """Test soft deletion"""
        tracker = TrackerDefinition.objects.create(
            user=self.user,
            name='To Delete',
            tracker_id='delete-me'
        )
        
        self.service.delete_tracker('delete-me', self.user)
        
        tracker.refresh_from_db()
        self.assertIsNotNone(tracker.deleted_at)
        
        # Should not be retrievable by standard get
        with self.assertRaises(TrackerNotFoundError):
            self.service.get_tracker_by_id('delete-me', self.user)

    def test_get_active_trackers(self):
        """Test active trackers filter"""
        # Active
        t1 = TrackerDefinition.objects.create(user=self.user, name='Active 1')
        # Archived
        t2 = TrackerDefinition.objects.create(user=self.user, name='Archived', status='archived')
        # Deleted
        from django.utils import timezone
        t3 = TrackerDefinition.objects.create(user=self.user, name='Deleted', deleted_at=timezone.now())
        
        active = self.service.get_active_trackers(self.user)
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().name, 'Active 1')
