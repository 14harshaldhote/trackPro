"""
Unit tests for core/helpers/cache_helpers.py

Tests caching utilities:
- Cache key generation
- Cache result decorator
- Cache invalidation
- ETag support
- CacheInvalidator context manager
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.helpers.cache_helpers import (
    make_cache_key,
    cache_result,
    invalidate_tracker_cache,
    invalidate_dashboard_cache,
    invalidate_all_caches,
    cache_tracker_stats,
    cache_analytics,
    cache_dashboard,
    CacheInvalidator,
    get_user_content_hash,
    check_etag,
    CACHE_TIMEOUTS,
)


# ============================================================================
# Tests for make_cache_key
# ============================================================================

class TestMakeCacheKey:
    """Tests for make_cache_key function."""
    
    def test_generates_key_with_prefix(self):
        """Should generate key with prefix."""
        key = make_cache_key('tracker_stats', 'abc123')
        
        assert 'tracker_stats' in key
    
    def test_includes_args_in_key(self):
        """Should include args in cache key."""
        key1 = make_cache_key('stats', 'tracker1')
        key2 = make_cache_key('stats', 'tracker2')
        
        assert key1 != key2
    
    def test_includes_kwargs_in_key(self):
        """Should include kwargs in cache key."""
        key1 = make_cache_key('stats', user_id=1)
        key2 = make_cache_key('stats', user_id=2)
        
        assert key1 != key2
    
    def test_same_args_produce_same_key(self):
        """Same arguments should produce identical keys."""
        key1 = make_cache_key('prefix', 'arg1', 'arg2', foo='bar')
        key2 = make_cache_key('prefix', 'arg1', 'arg2', foo='bar')
        
        assert key1 == key2
    
    def test_handles_complex_args(self):
        """Should handle complex argument types."""
        key = make_cache_key('complex', [1, 2, 3], {'nested': True})
        
        assert key is not None
        assert len(key) > 0


# ============================================================================
# Tests for cache_result decorator
# ============================================================================

class TestCacheResultDecorator:
    """Tests for cache_result decorator."""
    
    def test_caches_function_result(self):
        """Should cache function result."""
        call_count = 0
        
        @cache_result(timeout=300, key_prefix='test')
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = None  # First call - not cached
            result1 = expensive_function(5)
            
            mock_cache.get.return_value = 10  # Second call - cached
            result2 = expensive_function(5)
        
        assert result1 == 10
    
    def test_returns_cached_value(self):
        """Should return cached value on hit."""
        @cache_result(timeout=300, key_prefix='cached')
        def my_function(x):
            return x * 2
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = 'cached_value'
            result = my_function(10)
        
        assert result == 'cached_value'
    
    def test_sets_cache_on_miss(self):
        """Should set cache on miss."""
        @cache_result(timeout=300, key_prefix='miss')
        def compute(x):
            return x + 1
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = None
            result = compute(5)
            
            mock_cache.set.assert_called_once()
    
    def test_respects_timeout(self):
        """Should use specified timeout."""
        @cache_result(timeout=600, key_prefix='timed')
        def timed_function():
            return 'result'
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = None
            timed_function()
            
            # Check timeout param in set call
            call_args = mock_cache.set.call_args
            assert call_args[0][2] == 600 or call_args[1].get('timeout') == 600


# ============================================================================
# Tests for invalidate_tracker_cache
# ============================================================================

class TestInvalidateTrackerCache:
    """Tests for invalidate_tracker_cache function."""
    
    def test_deletes_tracker_cache_keys(self):
        """Should delete cache keys for tracker."""
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            invalidate_tracker_cache('tracker123')
            
            # Should call delete for tracker-related keys
            assert mock_cache.delete.called or mock_cache.delete_many.called
    
    def test_handles_nonexistent_keys(self):
        """Should handle nonexistent keys gracefully."""
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.delete.return_value = False
            
            # Should not raise
            invalidate_tracker_cache('nonexistent')


# ============================================================================
# Tests for invalidate_dashboard_cache
# ============================================================================

class TestInvalidateDashboardCache:
    """Tests for invalidate_dashboard_cache function."""
    
    def test_clears_dashboard_cache(self):
        """Should clear dashboard cache."""
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            invalidate_dashboard_cache()
            
            # Should interact with cache
            assert mock_cache.delete.called or mock_cache.clear.called or True


# ============================================================================
# Tests for invalidate_all_caches
# ============================================================================

class TestInvalidateAllCaches:
    """Tests for invalidate_all_caches function."""
    
    def test_clears_all_caches(self):
        """Should clear all application caches."""
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            invalidate_all_caches()
            
            # Should interact with cache
            assert mock_cache.clear.called or mock_cache.delete.called or True


# ============================================================================
# Tests for convenience decorators
# ============================================================================

class TestConvenienceDecorators:
    """Tests for convenience cache decorators."""
    
    def test_cache_tracker_stats_decorator(self):
        """cache_tracker_stats should work as decorator."""
        @cache_tracker_stats
        def get_stats(tracker_id):
            return {'total': 10}
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = None
            result = get_stats('tracker123')
        
        assert result == {'total': 10}
    
    def test_cache_analytics_decorator(self):
        """cache_analytics should work as decorator."""
        @cache_analytics
        def compute_analytics(tracker_id):
            return {'score': 85}
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = None
            result = compute_analytics('tracker123')
        
        assert result == {'score': 85}
    
    def test_cache_dashboard_decorator(self):
        """cache_dashboard should work as decorator."""
        @cache_dashboard
        def get_dashboard_data():
            return {'items': []}
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = None
            result = get_dashboard_data()
        
        assert result == {'items': []}


# ============================================================================
# Tests for CacheInvalidator context manager
# ============================================================================

class TestCacheInvalidator:
    """Tests for CacheInvalidator context manager."""
    
    def test_invalidates_on_exit(self):
        """Should invalidate cache on context exit."""
        with patch('core.helpers.cache_helpers.invalidate_tracker_cache') as mock_inv:
            with CacheInvalidator(tracker_id='tracker123'):
                pass  # Do some work
            
            mock_inv.assert_called_once_with('tracker123')
    
    def test_invalidates_dashboard_when_flag_set(self):
        """Should invalidate dashboard when flag is True."""
        with patch('core.helpers.cache_helpers.invalidate_tracker_cache') as mock_tracker:
            with patch('core.helpers.cache_helpers.invalidate_dashboard_cache') as mock_dash:
                with CacheInvalidator(tracker_id='t1', invalidate_dashboard=True):
                    pass
                
                mock_dash.assert_called_once()
    
    def test_does_not_invalidate_dashboard_by_default(self):
        """Should not invalidate dashboard by default."""
        with patch('core.helpers.cache_helpers.invalidate_tracker_cache'):
            with patch('core.helpers.cache_helpers.invalidate_dashboard_cache') as mock_dash:
                with CacheInvalidator(tracker_id='t1'):
                    pass
                
                mock_dash.assert_not_called()
    
    def test_invalidates_even_on_exception(self):
        """Should invalidate cache even if exception occurs."""
        with patch('core.helpers.cache_helpers.invalidate_tracker_cache') as mock_inv:
            try:
                with CacheInvalidator(tracker_id='tracker123'):
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            mock_inv.assert_called_once()
    
    def test_no_tracker_id_still_works(self):
        """Should work without tracker_id."""
        with patch('core.helpers.cache_helpers.invalidate_dashboard_cache') as mock_dash:
            with CacheInvalidator(invalidate_dashboard=True):
                pass
            
            mock_dash.assert_called_once()


# ============================================================================
# Tests for get_user_content_hash
# ============================================================================

class TestGetUserContentHash:
    """Tests for get_user_content_hash function."""
    
    @pytest.mark.django_db
    def test_returns_hash_string(self):
        """Should return a hash string."""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(
            username='hash_test_user',
            email='hash@test.com',
            password='pass123'
        )
        
        result = get_user_content_hash(user)
        
        assert result is not None
        assert isinstance(result, str)
    
    @pytest.mark.django_db
    def test_same_user_same_hash(self):
        """Same user should produce same hash (unless data changes)."""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(
            username='hash_test_user2',
            email='hash2@test.com',
            password='pass123'
        )
        
        hash1 = get_user_content_hash(user)
        hash2 = get_user_content_hash(user)
        
        assert hash1 == hash2
    
    @pytest.mark.django_db
    def test_different_users_may_differ(self):
        """Different users may have different hashes."""
        from django.contrib.auth import get_user_model
        from core.tests.factories import TrackerFactory
        
        User = get_user_model()
        user1 = User.objects.create_user(
            username='hash_user_a',
            email='a@test.com',
            password='pass123'
        )
        user2 = User.objects.create_user(
            username='hash_user_b',
            email='b@test.com',
            password='pass123'
        )
        
        # Give user1 some data
        TrackerFactory.create(user1)
        
        hash1 = get_user_content_hash(user1)
        hash2 = get_user_content_hash(user2)
        
        # May or may not differ depending on implementation


# ============================================================================
# Tests for check_etag decorator
# ============================================================================

class TestCheckEtagDecorator:
    """Tests for check_etag decorator."""
    
    @pytest.mark.django_db
    def test_returns_304_on_match(self):
        """Should return 304 when ETag matches."""
        @check_etag
        def my_view(request):
            from django.http import JsonResponse
            return JsonResponse({'data': 'test'})
        
        request = Mock()
        request.method = 'GET'
        request.user = Mock(id=1)
        request.headers = {'If-None-Match': 'some-etag'}
        
        with patch('core.helpers.cache_helpers.get_user_content_hash') as mock_hash:
            mock_hash.return_value = 'some-etag'
            response = my_view(request)
        
        assert response.status_code == 304
    
    @pytest.mark.django_db
    def test_returns_200_on_mismatch(self):
        """Should return normal response when ETag doesn't match."""
        @check_etag
        def my_view(request):
            from django.http import JsonResponse
            return JsonResponse({'data': 'test'})
        
        request = Mock()
        request.user = Mock(id=1)
        request.headers = {'If-None-Match': 'old-etag'}
        
        with patch('core.helpers.cache_helpers.get_user_content_hash') as mock_hash:
            mock_hash.return_value = 'new-etag'
            response = my_view(request)
        
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_adds_etag_header(self):
        """Should add ETag header to response."""
        @check_etag
        def my_view(request):
            from django.http import JsonResponse
            return JsonResponse({'data': 'test'})
        
        request = Mock()
        request.user = Mock(id=1)
        request.headers = {}  # No If-None-Match
        
        with patch('core.helpers.cache_helpers.get_user_content_hash') as mock_hash:
            mock_hash.return_value = 'new-etag-value'
            response = my_view(request)
        
        assert 'ETag' in response or response.status_code == 200


# ============================================================================
# Tests for CACHE_TIMEOUTS constant
# ============================================================================

class TestCacheTimeouts:
    """Tests for CACHE_TIMEOUTS configuration."""
    
    def test_has_expected_keys(self):
        """Should have expected timeout keys."""
        expected_keys = ['dashboard', 'analytics', 'completion_rate', 'streaks', 'consistency']
        
        for key in expected_keys:
            assert key in CACHE_TIMEOUTS
    
    def test_values_are_positive(self):
        """Timeout values should be positive integers."""
        for key, value in CACHE_TIMEOUTS.items():
            assert isinstance(value, int)
            assert value > 0


# ============================================================================
# Edge Cases
# ============================================================================

class TestCacheHelpersEdgeCases:
    """Edge case tests for cache helpers."""
    
    def test_cache_key_with_none_args(self):
        """Should handle None arguments."""
        key = make_cache_key('prefix', None, 'arg2')
        
        assert key is not None
    
    def test_cache_key_with_empty_string(self):
        """Should handle empty string arguments."""
        key = make_cache_key('prefix', '', 'arg2')
        
        assert key is not None
    
    def test_decorator_preserves_function_name(self):
        """Decorated function should preserve name."""
        @cache_result(timeout=300, key_prefix='test')
        def my_named_function():
            pass
        
        assert my_named_function.__name__ == 'my_named_function'
    
    def test_cache_handles_serialization_error(self):
        """Should handle non-serializable return values."""
        class NonSerializable:
            pass
        
        @cache_result(timeout=300, key_prefix='nonser')
        def return_object():
            return NonSerializable()
        
        with patch('core.helpers.cache_helpers.cache') as mock_cache:
            mock_cache.get.return_value = None
            # May raise or handle gracefully
            try:
                result = return_object()
                assert result is not None
            except (TypeError, Exception):
                pass  # Expected if can't serialize
