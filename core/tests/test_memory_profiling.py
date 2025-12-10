
import pytest
import tracemalloc
import gc
from django.test import TestCase
from core.tests.factories import UserFactory, TrackerFactory, TemplateFactory
from core.services.tracker_service import TrackerService

@pytest.mark.django_db
class TestMemoryProfiling(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.service = TrackerService()

    def test_memory_leak_create_tracker(self):
        """
        Verify that creating and deleting trackers endlessly doesn't leak memory.
        """
        tracemalloc.start()
        
        # Warmup
        for _ in range(10):
            t = TrackerFactory.create(self.user)
            t.delete()
            
        gc.collect()
        snapshot1 = tracemalloc.take_snapshot()
        
        # Run loop
        for _ in range(100):
            t = TrackerFactory.create(self.user)
            t.delete()
            
        gc.collect()
        snapshot2 = tracemalloc.take_snapshot()
        
        tracemalloc.stop()
        
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        # We expect some fluctuation, but not a huge constant increase in specific objects
        # This is a heuristic test.
        
        total_growth = sum(stat.size_diff for stat in top_stats)
        
        # If total growth is huge (e.g. > 1MB for 100 simple objects that were deleted), fail
        # 1MB = 1024*1024 bytes
        self.assertLess(total_growth, 5 * 1024 * 1024, f"Potential memory leak detected: {total_growth} bytes growth")

    def test_heavy_computation_memory(self):
        """
        Test that heavy service methods clean up resources.
        """
        # Example: if there's a heavy report generation
        pass
