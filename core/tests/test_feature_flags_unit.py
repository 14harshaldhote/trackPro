"""
Unit tests for core/utils/feature_flags.py

Tests feature flag system:
- Flag enabling/disabling
- Percentage-based rollouts
- Flag value retrieval
- require_feature decorator
- Flag overrides and caching
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from core.utils.feature_flags import (
    _get_flags,
    _get_user_bucket,
    is_feature_enabled,
    get_flag_value,
    require_feature,
    set_flag_override,
    clear_flag_cache,
    DEFAULT_FLAGS,
)


# ============================================================================
# Tests for _get_flags
# ============================================================================

class TestGetFlags:
    """Tests for _get_flags function."""
    
    def test_returns_default_flags(self):
        """Should return default flags when settings not configured."""
        with patch('core.utils.feature_flags.settings') as mock_settings:
            delattr(mock_settings, 'FEATURE_FLAGS')
            flags = _get_flags()
        
        assert flags == DEFAULT_FLAGS
    
    def test_returns_settings_flags(self):
        """Should return flags from settings when configured."""
        custom_flags = {'my_feature': {'enabled': True, 'rollout_percent': 50}}
        
        with patch('core.utils.feature_flags.settings') as mock_settings:
            mock_settings.FEATURE_FLAGS = custom_flags
            flags = _get_flags()
        
        assert flags == custom_flags


# ============================================================================
# Tests for _get_user_bucket
# ============================================================================

class TestGetUserBucket:
    """Tests for _get_user_bucket function."""
    
    def test_returns_bucket_for_user(self):
        """Should return bucket 0-99 based on user ID."""
        user = Mock(id=42)
        
        bucket = _get_user_bucket(user)
        
        assert 0 <= bucket < 100
        assert bucket == 42  # 42 % 100 = 42
    
    def test_handles_none_user(self):
        """Should return 0 for None user."""
        bucket = _get_user_bucket(None)
        
        assert bucket == 0
    
    def test_handles_user_without_id(self):
        """Should return 0 for user without id attribute."""
        user = Mock(spec=[])  # No id attribute
        
        bucket = _get_user_bucket(user)
        
        assert bucket == 0
    
    def test_consistent_for_same_user(self):
        """Same user should always get same bucket."""
        user = Mock(id=123)
        
        bucket1 = _get_user_bucket(user)
        bucket2 = _get_user_bucket(user)
        
        assert bucket1 == bucket2
    
    def test_different_users_may_differ(self):
        """Different users should get different buckets (usually)."""
        user1 = Mock(id=1)
        user2 = Mock(id=2)
        
        bucket1 = _get_user_bucket(user1)
        bucket2 = _get_user_bucket(user2)
        
        assert bucket1 != bucket2


# ============================================================================
# Tests for is_feature_enabled
# ============================================================================

class TestIsFeatureEnabled:
    """Tests for is_feature_enabled function."""
    
    def test_enabled_flag_returns_true(self):
        """Enabled flag at 100% should return True."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = {'enabled': True, 'rollout_percent': 100}
            
            result = is_feature_enabled('test_feature')
        
        assert result is True
    
    def test_disabled_flag_returns_false(self):
        """Disabled flag should return False."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = {'enabled': False, 'rollout_percent': 0}
            
            result = is_feature_enabled('test_feature')
        
        assert result is False
    
    def test_unknown_flag_returns_false(self):
        """Unknown flag should return False."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = None
            with patch('core.utils.feature_flags._get_flags') as mock_flags:
                mock_flags.return_value = {}  # Flag not defined
                
                result = is_feature_enabled('nonexistent_flag')
        
        assert result is False
    
    def test_percentage_rollout_includes_low_bucket(self):
        """Users in rollout percentage should have feature enabled."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = {'enabled': True, 'rollout_percent': 50}
            
            # User with ID 10 -> bucket 10, should be in 50% rollout
            user = Mock(id=10)
            result = is_feature_enabled('test_feature', user)
        
        assert result is True
    
    def test_percentage_rollout_excludes_high_bucket(self):
        """Users outside rollout percentage should not have feature."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = {'enabled': True, 'rollout_percent': 10}
            
            # User with ID 50 -> bucket 50, should NOT be in 10% rollout
            user = Mock(id=50)
            result = is_feature_enabled('test_feature', user)
        
        assert result is False
    
    def test_zero_percent_returns_false(self):
        """0% rollout should return False even if enabled."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = {'enabled': True, 'rollout_percent': 0}
            
            user = Mock(id=1)
            result = is_feature_enabled('test_feature', user)
        
        assert result is False
    
    def test_hundred_percent_returns_true(self):
        """100% rollout should return True for all users."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = {'enabled': True, 'rollout_percent': 100}
            
            user = Mock(id=99)
            result = is_feature_enabled('test_feature', user)
        
        assert result is True
    
    def test_caches_flag_config(self):
        """Should cache flag config after fetching."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = None  # Cache miss
            with patch('core.utils.feature_flags._get_flags') as mock_flags:
                mock_flags.return_value = {
                    'test_flag': {'enabled': True, 'rollout_percent': 100}
                }
                
                is_feature_enabled('test_flag')
        
        mock_cache.set.assert_called_once()


# ============================================================================
# Tests for get_flag_value
# ============================================================================

class TestGetFlagValue:
    """Tests for get_flag_value function."""
    
    def test_returns_value_from_flag(self):
        """Should return value from flag config."""
        with patch('core.utils.feature_flags._get_flags') as mock_flags:
            mock_flags.return_value = {
                'my_flag': {'enabled': True, 'value': 42}
            }
            
            result = get_flag_value('my_flag')
        
        assert result == 42
    
    def test_returns_default_when_missing(self):
        """Should return default when flag doesn't have value."""
        with patch('core.utils.feature_flags._get_flags') as mock_flags:
            mock_flags.return_value = {
                'my_flag': {'enabled': True}  # No 'value' key
            }
            
            result = get_flag_value('my_flag', default='default')
        
        assert result == 'default'
    
    def test_returns_default_when_flag_unknown(self):
        """Should return default for unknown flags."""
        with patch('core.utils.feature_flags._get_flags') as mock_flags:
            mock_flags.return_value = {}
            
            result = get_flag_value('unknown_flag', default='fallback')
        
        assert result == 'fallback'


# ============================================================================
# Tests for require_feature decorator
# ============================================================================

class TestRequireFeatureDecorator:
    """Tests for require_feature decorator."""
    
    def test_allows_when_enabled(self):
        """Should allow access when feature is enabled."""
        @require_feature('test_feature')
        def my_view(request):
            return 'success'
        
        request = Mock()
        request.user = Mock(id=1)
        
        with patch('core.utils.feature_flags.is_feature_enabled') as mock_enabled:
            mock_enabled.return_value = True
            result = my_view(request)
        
        assert result == 'success'
    
    def test_blocks_when_disabled(self):
        """Should raise 404 when feature is disabled."""
        from django.http import Http404
        
        @require_feature('test_feature')
        def my_view(request):
            return 'success'
        
        request = Mock()
        request.user = Mock(id=99)
        
        with patch('core.utils.feature_flags.is_feature_enabled') as mock_enabled:
            mock_enabled.return_value = False
            
            with pytest.raises(Http404):
                my_view(request)
    
    def test_uses_fallback_when_disabled(self):
        """Should use fallback view when feature disabled."""
        def fallback_view(request):
            return 'fallback'
        
        @require_feature('test_feature', fallback=fallback_view)
        def my_view(request):
            return 'success'
        
        request = Mock()
        request.user = Mock(id=99)
        
        with patch('core.utils.feature_flags.is_feature_enabled') as mock_enabled:
            mock_enabled.return_value = False
            result = my_view(request)
        
        assert result == 'fallback'
    
    def test_passes_args_to_view(self):
        """Should pass arguments to view function."""
        @require_feature('test_feature')
        def my_view(request, id, action=None):
            return f'{id}:{action}'
        
        request = Mock()
        request.user = Mock(id=1)
        
        with patch('core.utils.feature_flags.is_feature_enabled') as mock_enabled:
            mock_enabled.return_value = True
            result = my_view(request, 'abc123', action='update')
        
        assert result == 'abc123:update'
    
    def test_preserves_function_metadata(self):
        """Should preserve function name and docstring."""
        @require_feature('test_feature')
        def documented_view(request):
            """My docstring."""
            pass
        
        assert documented_view.__name__ == 'documented_view'
        assert 'docstring' in documented_view.__doc__


# ============================================================================
# Tests for set_flag_override
# ============================================================================

class TestSetFlagOverride:
    """Tests for set_flag_override function."""
    
    def test_sets_override_in_cache(self):
        """Should set override in cache."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            set_flag_override('my_feature', True)
            
            mock_cache.set.assert_called_once()
    
    def test_sets_enabled_to_true(self):
        """Should set enabled=True when overriding to True."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            set_flag_override('my_feature', True)
            
            call_args = mock_cache.set.call_args
            config = call_args[0][1]
            assert config['enabled'] is True
            assert config['rollout_percent'] == 100
    
    def test_sets_enabled_to_false(self):
        """Should set enabled=False when overriding to False."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            set_flag_override('my_feature', False)
            
            call_args = mock_cache.set.call_args
            config = call_args[0][1]
            assert config['enabled'] is False
            assert config['rollout_percent'] == 0
    
    def test_respects_duration(self):
        """Should use specified duration."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            set_flag_override('my_feature', True, duration=7200)
            
            call_args = mock_cache.set.call_args
            assert call_args[0][2] == 7200


# ============================================================================
# Tests for clear_flag_cache
# ============================================================================

class TestClearFlagCache:
    """Tests for clear_flag_cache function."""
    
    def test_clears_all_flag_caches(self):
        """Should clear cache for all defined flags."""
        with patch('core.utils.feature_flags._get_flags') as mock_flags:
            mock_flags.return_value = {
                'flag1': {},
                'flag2': {},
                'flag3': {}
            }
            with patch('core.utils.feature_flags.cache') as mock_cache:
                clear_flag_cache()
                
                # Should delete cache for each flag
                assert mock_cache.delete.call_count == 3


# ============================================================================
# Tests for DEFAULT_FLAGS constant
# ============================================================================

class TestDefaultFlags:
    """Tests for DEFAULT_FLAGS configuration."""
    
    def test_has_expected_flags(self):
        """Should have expected default flags."""
        expected_flags = ['new_sync_api', 'push_notifications', 'advanced_analytics', 'api_v2']
        
        for flag in expected_flags:
            assert flag in DEFAULT_FLAGS
    
    def test_flags_have_required_keys(self):
        """Each flag should have enabled and rollout_percent."""
        for name, config in DEFAULT_FLAGS.items():
            assert 'enabled' in config
            assert 'rollout_percent' in config
    
    def test_rollout_percent_in_range(self):
        """Rollout percent should be 0-100."""
        for name, config in DEFAULT_FLAGS.items():
            assert 0 <= config['rollout_percent'] <= 100


# ============================================================================
# Integration Tests
# ============================================================================

class TestFeatureFlagsIntegration:
    """Integration tests for feature flags."""
    
    def test_full_workflow(self):
        """Test complete feature flag workflow."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = None
            
            with patch('core.utils.feature_flags._get_flags') as mock_flags:
                mock_flags.return_value = {
                    'new_feature': {'enabled': True, 'rollout_percent': 50}
                }
                
                # User in rollout (ID 10)
                user_in = Mock(id=10)
                assert is_feature_enabled('new_feature', user_in) is True
                
                # User out of rollout (ID 75)
                user_out = Mock(id=75)
                assert is_feature_enabled('new_feature', user_out) is False
    
    def test_override_takes_precedence(self):
        """Override should take precedence over default."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            # First, set override
            set_flag_override('disabled_feature', True)
            
            # Then check - should use cached override
            mock_cache.get.return_value = {'enabled': True, 'rollout_percent': 100}
            
            result = is_feature_enabled('disabled_feature')
            
            assert result is True


# ============================================================================
# Edge Cases
# ============================================================================

class TestFeatureFlagsEdgeCases:
    """Edge case tests for feature flags."""
    
    def test_empty_flag_name(self):
        """Should handle empty flag name."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = None
            with patch('core.utils.feature_flags._get_flags') as mock_flags:
                mock_flags.return_value = {}
                
                result = is_feature_enabled('')
        
        assert result is False
    
    def test_special_characters_in_flag_name(self):
        """Should handle special characters in flag name."""
        with patch('core.utils.feature_flags.cache') as mock_cache:
            mock_cache.get.return_value = {'enabled': True, 'rollout_percent': 100}
            
            result = is_feature_enabled('feature-with-dashes')
        
        # Should not crash
        assert isinstance(result, bool)
    
    def test_very_large_user_id(self):
        """Should handle very large user IDs."""
        user = Mock(id=99999999999)
        bucket = _get_user_bucket(user)
        
        assert 0 <= bucket < 100
    
    def test_negative_user_id(self):
        """Should handle negative user IDs (edge case)."""
        user = Mock(id=-5)
        bucket = _get_user_bucket(user)
        
        # Modulo should still work
        assert bucket == -5 % 100  # = 95
