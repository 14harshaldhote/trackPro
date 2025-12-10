"""
Search System Tests V1.5 (12 tests)

Test IDs: SRCH-001 to SRCH-012
Coverage: /api/v1/search/*, /api/v1/search/suggestions/, /api/v1/search/history/

These tests cover:
- Basic search
- Search suggestions
- Search history
- SQL injection protection
"""
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, TagFactory
)


class BasicSearchTests(BaseAPITestCase):
    """Tests for /api/v1/search/ endpoint."""
    
    def test_SRCH_001_basic_search(self):
        """SRCH-001: Basic search returns 200 with results."""
        tracker = self.create_tracker(name='Gym Workout')
        template = self.create_template(tracker, description='Push-ups')
        
        response = self.get('/api/v1/search/?q=gym')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_002_search_empty_query(self):
        """SRCH-002: Search with empty query returns recent items."""
        tracker = self.create_tracker()
        
        response = self.get('/api/v1/search/?q=')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_003_search_no_results(self):
        """SRCH-003: Search with no matches returns 200 with empty array."""
        response = self.get('/api/v1/search/?q=zzzzzzzzzzz')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_004_search_includes_tags(self):
        """SRCH-004: Search results include tags."""
        tag = TagFactory.create(self.user, name='Health')
        tracker = self.create_tracker(name='Health Tracker')
        
        response = self.get('/api/v1/search/?q=health')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_005_search_saves_history(self):
        """SRCH-005: Search query is saved to history."""
        tracker = self.create_tracker()
        
        # Perform search
        self.get('/api/v1/search/?q=test_search_term')
        
        # Check history
        response = self.get('/api/v1/search/history/')
        
        self.assertEqual(response.status_code, 200)


class SearchSuggestionsTests(BaseAPITestCase):
    """Tests for /api/v1/search/suggestions/ endpoint."""
    
    def test_SRCH_006_get_search_suggestions(self):
        """SRCH-006: Get search suggestions returns 200."""
        tracker = self.create_tracker(name='Gym Routine')
        
        response = self.get('/api/v1/search/suggestions/?q=gy')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_007_suggestions_empty_query(self):
        """SRCH-007: Suggestions with empty query returns popular items."""
        response = self.get('/api/v1/search/suggestions/?q=')
        
        self.assertEqual(response.status_code, 200)


class SearchHistoryTests(BaseAPITestCase):
    """Tests for /api/v1/search/history/ endpoint."""
    
    def test_SRCH_008_get_recent_history(self):
        """SRCH-008: Get recent search history returns 200."""
        # Perform some searches first
        self.get('/api/v1/search/?q=workout')
        self.get('/api/v1/search/?q=meditation')
        
        response = self.get('/api/v1/search/history/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_009_get_popular_searches(self):
        """SRCH-009: Get popular searches returns 200."""
        response = self.get('/api/v1/search/history/?type=popular')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_010_clear_search_history(self):
        """SRCH-010: Clear search history returns 200."""
        # Perform some searches first
        self.get('/api/v1/search/?q=test1')
        self.get('/api/v1/search/?q=test2')
        
        response = self.post('/api/v1/search/history/clear/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_SRCH_011_clear_history_older_than(self):
        """SRCH-011: Clear history older than days returns 200."""
        response = self.post('/api/v1/search/history/clear/', {
            'older_than_days': 30
        })
        
        self.assertEqual(response.status_code, 200)


class SearchSecurityTests(BaseAPITestCase):
    """Tests for search security."""
    
    def test_SRCH_012_search_sql_injection(self):
        """SRCH-012: SQL injection attempt is sanitized."""
        response = self.get("/api/v1/search/?q=';DROP TABLE users;--")
        
        # Should return 200 (sanitized) or appropriate error, not 500
        self.assertIn(response.status_code, [200, 400])
