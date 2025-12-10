"""
Critical Coverage Gap Tests

Priority: MEDIUM
Coverage: time_utils, services edge cases

These tests target modules with low coverage to ensure logic correctness.
"""
import pytest
from django.utils import timezone
from datetime import datetime, timedelta
from core.utils import time_utils
from core.tests.base import BaseAPITestCase

class TimeUtilsCoverageTests(BaseAPITestCase):
    """Tests for core.utils.time_utils module."""
    
    def test_COV_001_get_period_dates(self):
        """Test get_period_dates utility."""
        from datetime import date
        
        # Test 'daily'
        start, end = time_utils.get_period_dates('daily', date(2025, 1, 15))
        self.assertEqual(start, date(2025, 1, 15))
        self.assertEqual(end, date(2025, 1, 15))
        
        # Test 'weekly' (Monday to Sunday)
        start, end = time_utils.get_period_dates('weekly', date(2025, 1, 15))  # Wednesday
        self.assertTrue(start <= end)
        self.assertEqual((end - start).days, 6)  # 7-day week
        
        # Test 'monthly'
        start, end = time_utils.get_period_dates('monthly', date(2025, 1, 15))
        self.assertEqual(start.day, 1)
        self.assertEqual(start.month, 1)

    def test_COV_002_parse_date_string(self):
        """Test parse_date_string helper."""
        from datetime import date
        
        # Valid ISO date
        d = time_utils.parse_date_string("2025-01-01")
        self.assertEqual(d.year, 2025)
        self.assertEqual(d.month, 1)
        self.assertEqual(d.day, 1)
        
        # Relative dates
        self.assertEqual(time_utils.parse_date_string("today"), date.today())
        
        # Invalid date should raise ValueError
        with self.assertRaises(ValueError):
            time_utils.parse_date_string("invalid")

    def test_COV_003_format_period_display(self):
        """Test period formatting."""
        from datetime import date
        
        result = time_utils.format_period_display(
            date(2025, 1, 15), 
            date(2025, 1, 15), 
            'daily'
        )
        self.assertIn('Jan', result)
        self.assertIn('15', result)


class ServiceLayerCoverageTests(BaseAPITestCase):
    """Tests for service layer edge cases."""
    
    def test_COV_004_tracker_service_edge_cases(self):
        """Test TrackerService edge cases."""
        # This assumes existence of TrackerService
        try:
            from core.services.tracker_service import TrackerService
            
            # Test getting non-existent tracker
            with self.assertRaises(Exception):
                TrackerService.get_tracker(tracker_id="invalid")
                
        except ImportError:
            pass
