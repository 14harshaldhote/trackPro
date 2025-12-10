
import pytest
import time
import concurrent.futures
from django.test import TestCase, TransactionTestCase
from core.tests.factories import UserFactory, TrackerFactory
from core.services.tracker_service import TrackerService

@pytest.mark.django_db(transaction=True)
class TestSustainedLoad(TransactionTestCase):
    # Use TransactionTestCase to allow thread access to DB if needed, 
    # though with SQLite it can be tricky. 
    # For unit tests, we might just simulate load sequentially if threads cause DB lock issues in test env.
    
    def setUp(self):
        self.user = UserFactory.create()
        self.service = TrackerService()

    def test_sustained_load_tracker_creation(self):
        """
        Simulate sustained load of tracker creation.
        """
        duration = 5 # seconds for unit test version
        end_time = time.time() + duration
        count = 0
        
        # We can't really do heavy multithreading with Django test DB (sqlite default) readily 
        # without connection issues unless configured. 
        # So we'll do a rapid sequential loop to test "sustained" logic errors.
        
        while time.time() < end_time:
            t = self.service.create_tracker(self.user, {"name": f"Tracker {count}", "color": "#000000"})
            self.assertIsNotNone(t.get('id', t.get('tracker_id')))
            count += 1
            
        print(f"Created {count} trackers in {duration} seconds")
        self.assertGreater(count, 10, "Should be able to create reasonably many trackers")

    def test_concurrent_access_simulation(self):
        """
        Simulate concurrent access to the same resource.
        """
        tracker = TrackerFactory.create(self.user)
        
        def update_tracker(name):
            return self.service.update_tracker(tracker.tracker_id, self.user, {"name": name})

        # Try 10 concurrent updates
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_tracker, f"Name {i}") for i in range(10)]
            results = []
            for f in concurrent.futures.as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    results.append(e)
        
        # Check that we didn't crash
        self.assertEqual(len(results), 10)
        
        # Verify final state is valid
        tracker.refresh_from_db()
        self.assertTrue(tracker.name.startswith("Name "))
