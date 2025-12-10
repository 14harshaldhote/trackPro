
import pytest
from unittest.mock import Mock, patch
from django.http import Http404
from core.helpers.auth_helpers import (
    get_user_tracker_or_404, check_tracker_permission, get_user_trackers
)

class TestAuthHelpers:

    def test_get_user_tracker_or_404_success(self):
        """Test finding a valid user tracker."""
        user = Mock()
        
        with patch('core.helpers.auth_helpers.get_object_or_404') as mock_get:
            mock_tracker = Mock()
            mock_get.return_value = mock_tracker
            
            result = get_user_tracker_or_404("t-1", user)
            
            assert result == mock_tracker
            # Verify the call arguments. Note: get_object_or_404 arguments can be positional or keyword
            # depending on how it's called. The code calls it with kwargs.
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['tracker_id'] == "t-1"
            assert call_kwargs['user'] == user

    def test_check_tracker_permission_success(self):
        """Test checking permission for owner."""
        user = Mock()
        tracker = Mock()
        tracker.user = user
        
        with patch('core.helpers.auth_helpers.TrackerDefinition') as MockModel:
            MockModel.objects.filter.return_value.first.return_value = tracker
            
            # Should not raise exception
            check_tracker_permission("t-1", user)

    def test_check_tracker_permission_not_found(self):
        """Test permission check when tracker doesn't exist."""
        user = Mock()
        
        with patch('core.helpers.auth_helpers.TrackerDefinition') as MockModel:
            MockModel.objects.filter.return_value.first.return_value = None
            
            with pytest.raises(Http404) as exc:
                check_tracker_permission("t-1", user)
            assert str(exc.value) == "Tracker not found"

    def test_check_tracker_permission_denied(self):
        """Test permission check when user is not owner."""
        user1 = Mock()
        user1.id = 1
        user2 = Mock()
        user2.id = 2
        
        tracker = Mock()
        tracker.user_id = 1
        tracker.user = user1
        
        with patch('core.helpers.auth_helpers.TrackerDefinition') as MockModel:
            MockModel.objects.filter.return_value.first.return_value = tracker
            
            # Using user2 (not owner)
            with pytest.raises(Http404) as exc:
                check_tracker_permission("t-1", user2)
            assert str(exc.value) == "Tracker not found" # Should still say "Not found" for security

    def test_get_user_trackers(self):
        """Test retrieving user trackers."""
        user = Mock()
        
        with patch('core.helpers.auth_helpers.TrackerDefinition') as MockModel:
            mock_qs = MockModel.objects.filter.return_value.order_by.return_value
            
            result = get_user_trackers(user)
            
            assert result == mock_qs
            MockModel.objects.filter.assert_called_with(user=user)
