"""
Unit tests for core/templatetags/tracker_filters.py

Tests custom template filters:
- get_item filter for dict/list access
- add_days filter for date manipulation
- percentage filter for conversion
"""
import pytest
from datetime import date, timedelta

from core.templatetags.tracker_filters import (
    get_item,
    add_days,
    percentage,
)


# ============================================================================
# Tests for get_item filter
# ============================================================================

class TestGetItemFilter:
    """Tests for get_item template filter."""
    
    def test_get_dict_item_by_key(self):
        """Should get dictionary item by key."""
        data = {'name': 'John', 'age': 30}
        
        result = get_item(data, 'name')
        
        assert result == 'John'
    
    def test_get_dict_missing_key(self):
        """Should return None for missing key."""
        data = {'name': 'John'}
        
        result = get_item(data, 'missing')
        
        assert result is None
    
    def test_get_list_item_by_index(self):
        """Should get list item by index."""
        data = ['a', 'b', 'c']
        
        result = get_item(data, 1)
        
        assert result == 'b'
    
    def test_get_list_item_string_index(self):
        """Should handle string index for list."""
        data = ['a', 'b', 'c']
        
        result = get_item(data, '2')
        
        assert result == 'c'
    
    def test_get_tuple_item(self):
        """Should get tuple item by index."""
        data = ('x', 'y', 'z')
        
        result = get_item(data, 0)
        
        assert result == 'x'
    
    def test_none_dictionary(self):
        """Should return None for None dictionary."""
        result = get_item(None, 'key')
        
        assert result is None
    
    def test_list_index_out_of_range(self):
        """Should return None for out-of-range index."""
        data = ['a', 'b']
        
        result = get_item(data, 10)
        
        assert result is None
    
    def test_invalid_index_type(self):
        """Should handle invalid index types gracefully."""
        data = ['a', 'b']
        
        result = get_item(data, 'not_a_number')
        
        assert result is None
    
    def test_nested_dict(self):
        """Should work with nested dictionaries (one level)."""
        data = {
            'user': {'name': 'John'},
            'score': 100
        }
        
        result = get_item(data, 'user')
        
        assert result == {'name': 'John'}
    
    def test_empty_dict(self):
        """Should handle empty dictionary."""
        data = {}
        
        result = get_item(data, 'any_key')
        
        assert result is None
    
    def test_empty_list(self):
        """Should handle empty list."""
        data = []
        
        result = get_item(data, 0)
        
        assert result is None
    
    def test_object_with_get_method(self):
        """Should use get method if available."""
        class DictLike:
            def get(self, key, default=None):
                if key == 'special':
                    return 'value'
                return default
        
        data = DictLike()
        
        result = get_item(data, 'special')
        
        assert result == 'value'
    
    def test_object_without_get_method(self):
        """Should return None for objects without get method."""
        class PlainObject:
            pass
        
        data = PlainObject()
        
        result = get_item(data, 'attr')
        
        assert result is None


# ============================================================================
# Tests for add_days filter
# ============================================================================

class TestAddDaysFilter:
    """Tests for add_days template filter."""
    
    def test_add_positive_days(self):
        """Should add days to date."""
        start_date = date(2025, 12, 10)
        
        result = add_days(start_date, 7)
        
        assert result == date(2025, 12, 17)
    
    def test_add_negative_days(self):
        """Should subtract days when negative."""
        start_date = date(2025, 12, 10)
        
        result = add_days(start_date, -3)
        
        assert result == date(2025, 12, 7)
    
    def test_add_zero_days(self):
        """Should return same date when adding zero."""
        start_date = date(2025, 12, 10)
        
        result = add_days(start_date, 0)
        
        assert result == start_date
    
    def test_cross_month_boundary(self):
        """Should handle month boundary crossing."""
        start_date = date(2025, 12, 28)
        
        result = add_days(start_date, 7)
        
        assert result == date(2026, 1, 4)
    
    def test_cross_year_boundary(self):
        """Should handle year boundary crossing."""
        start_date = date(2025, 12, 31)
        
        result = add_days(start_date, 1)
        
        assert result == date(2026, 1, 1)
    
    def test_leap_year_february(self):
        """Should handle leap year February."""
        start_date = date(2024, 2, 28)
        
        result = add_days(start_date, 1)
        
        assert result == date(2024, 2, 29)
    
    def test_non_leap_year_february(self):
        """Should handle non-leap year February."""
        start_date = date(2025, 2, 28)
        
        result = add_days(start_date, 1)
        
        assert result == date(2025, 3, 1)
    
    def test_invalid_date_returns_original(self):
        """Should return original value if can't add days."""
        result = add_days("not a date", 5)
        
        assert result == "not a date"
    
    def test_none_returns_none(self):
        """Should handle None gracefully."""
        result = add_days(None, 5)
        
        assert result is None
    
    def test_large_number_of_days(self):
        """Should handle large day values."""
        start_date = date(2025, 1, 1)
        
        result = add_days(start_date, 365)
        
        assert result == date(2026, 1, 1)


# ============================================================================
# Tests for percentage filter
# ============================================================================

class TestPercentageFilter:
    """Tests for percentage template filter."""
    
    def test_decimal_to_percentage(self):
        """Should convert decimal to percentage."""
        result = percentage(0.75)
        
        assert result == "75.0"
    
    def test_zero(self):
        """Should handle zero."""
        result = percentage(0)
        
        assert result == "0.0"
    
    def test_one(self):
        """Should convert 1 to 100%."""
        result = percentage(1)
        
        assert result == "100.0"
    
    def test_small_decimal(self):
        """Should handle small decimals."""
        result = percentage(0.001)
        
        assert result == "0.1"
    
    def test_large_value(self):
        """Should handle values greater than 1."""
        result = percentage(1.5)
        
        assert result == "150.0"
    
    def test_negative_value(self):
        """Should handle negative values."""
        result = percentage(-0.25)
        
        assert result == "-25.0"
    
    def test_string_number(self):
        """Should convert string numbers."""
        result = percentage("0.5")
        
        assert result == "50.0"
    
    def test_invalid_string(self):
        """Should return 0.0 for invalid string."""
        result = percentage("not a number")
        
        assert result == "0.0"
    
    def test_none_value(self):
        """Should return 0.0 for None."""
        result = percentage(None)
        
        assert result == "0.0"
    
    def test_integer_input(self):
        """Should handle integer input."""
        result = percentage(1)
        
        assert result == "100.0"
    
    def test_precision(self):
        """Should round to one decimal place."""
        result = percentage(0.33333333)
        
        assert result == "33.3"


# ============================================================================
# Integration Tests
# ============================================================================

class TestFiltersIntegration:
    """Integration tests for template filters."""
    
    def test_combined_usage(self):
        """Test filters in combination."""
        data = {
            'users': [
                {'name': 'Alice', 'score': 0.95},
                {'name': 'Bob', 'score': 0.78}
            ]
        }
        
        # Get first user
        users = get_item(data, 'users')
        first_user = get_item(users, 0)
        score = get_item(first_user, 'score')
        score_pct = percentage(score)
        
        assert score_pct == "95.0"
    
    def test_date_calculation_chain(self):
        """Test date calculations."""
        today = date.today()
        
        # Add week, then display
        next_week = add_days(today, 7)
        two_weeks = add_days(next_week, 7)
        
        assert two_weeks == today + timedelta(days=14)
