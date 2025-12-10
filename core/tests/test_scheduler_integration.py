
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.integrations.scheduler import (
    with_lock, precompute_analytics, check_trackers_locked, 
    run_integrity_locked, start_scheduler
)

class TestSchedulerIntegration:

    def test_with_lock_decorator_success(self):
        """Test lock acquisition allows execution."""
        with patch('core.integrations.scheduler.cache') as mock_cache:
            mock_cache.add.return_value = True # Lock acquired
            
            @with_lock('test_lock')
            def job():
                return "execution_result"
            
            result = job()
            assert result == "execution_result"
            mock_cache.add.assert_called_with('scheduler_lock:test_lock', 'locked', 3600)
            mock_cache.delete.assert_called_with('scheduler_lock:test_lock')

    def test_with_lock_decorator_locked(self):
        """Test lock failure skips execution."""
        with patch('core.integrations.scheduler.cache') as mock_cache:
            mock_cache.add.return_value = False # Lock NOT acquired
            
            @with_lock('test_lock')
            def job():
                return "execution_result"
            
            result = job()
            assert result is None
            
            # Ensure function body was not executed (implied by return None)
            # and delete was NOT called (we didn't own the lock)
            mock_cache.delete.assert_not_called()

    def test_precompute_analytics(self):
        """Test analytics job logic."""
        with patch('core.integrations.scheduler.cache') as mock_cache, \
             patch('core.models.TrackerDefinition') as MockTrackerDef, \
             patch('core.analytics.compute_completion_rate') as mock_compute, \
             patch('core.analytics.detect_streaks'), \
             patch('core.analytics.compute_consistency_score'), \
             patch('core.analytics.compute_balance_score'), \
             patch('core.analytics.compute_effort_index'), \
             patch('core.analytics.analyze_notes_sentiment'), \
             patch('core.behavioral.get_insights') as mock_insights:
             
            mock_cache.add.return_value = True 
            
            # Mock trackers
            t1 = Mock(); t1.tracker_id = "t1"
            t2 = Mock(); t2.tracker_id = "t2"
            MockTrackerDef.objects.filter.return_value = [t1, t2]
            
            precompute_analytics()
            
            assert mock_compute.call_count == 2
            assert mock_insights.call_count == 2
            
    def test_precompute_analytics_error_handling(self):
        """Test that one failure doesn't stop the job."""
        with patch('core.integrations.scheduler.cache') as mock_cache, \
             patch('core.models.TrackerDefinition') as MockTrackerDef, \
             patch('core.analytics.compute_completion_rate') as mock_compute, \
             patch('core.analytics.detect_streaks'), \
             patch('core.analytics.compute_consistency_score'), \
             patch('core.analytics.compute_balance_score'), \
             patch('core.analytics.compute_effort_index'), \
             patch('core.analytics.analyze_notes_sentiment'), \
             patch('core.behavioral.get_insights'):
            
            mock_cache.add.return_value = True
            
            t1 = Mock(); t1.tracker_id = "t1"
            t2 = Mock(); t2.tracker_id = "t2"
            MockTrackerDef.objects.filter.return_value = [t1, t2]
            
            # t1 raises error
            mock_compute.side_effect = [Exception("Fail"), None]
            
            precompute_analytics()
            
            # Should have tried both
            assert mock_compute.call_count == 2

    def test_check_trackers_locked(self):
        """Test hourly check wrapper."""
        with patch('core.integrations.scheduler.instance_service') as mock_service, \
             patch('core.integrations.scheduler.cache'):
             
             check_trackers_locked()
             mock_service.check_all_trackers.assert_called()

    def test_run_integrity_locked(self):
        """Test integrity check wrapper."""
        with patch('core.integrations.scheduler.integrity') as mock_integrity, \
             patch('core.integrations.scheduler.cache'):
             
             service_instance = mock_integrity.IntegrityService.return_value
             
             run_integrity_locked()
             service_instance.run_integrity_check.assert_called()

    def test_start_scheduler(self):
        """Test scheduler startup."""
        with patch('core.integrations.scheduler.BackgroundScheduler') as MockSched:
            scheduler_instance = MockSched.return_value
            
            start_scheduler()
            
            assert scheduler_instance.add_job.call_count == 3
            scheduler_instance.start.assert_called()
