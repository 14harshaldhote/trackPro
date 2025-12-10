"""
Unit tests for core/utils/time_utils.py

Tests time calculation utilities including:
- Period dates (start/end of day, week, month)
- Timezone conversions
- Date parsing and formatting
- Edge cases (DST, leap years, boundaries)
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch
import pytz

from core.utils.time_utils import (
    get_period_dates,
    get_week_boundaries,
    get_next_period_start,
    format_period_display,
    get_user_today,
    to_user_datetime,
    get_day_boundaries,
    get_month_boundaries,
    calculate_days_in_range,
    get_relative_date_description,
    parse_date_string,
)


class TestGetPeriodDates:
    """Tests for get_period_dates function."""
    
    def test_daily_mode_returns_same_date_for_start_and_end(self):
        """Daily mode should return the same date for both start and end."""
        ref_date = date(2025, 12, 10)
        start, end = get_period_dates('daily', ref_date)
        
        assert start == ref_date
        assert end == ref_date
    
    def test_daily_mode_with_none_uses_today(self):
        """When reference_date is None, should use today."""
        start, end = get_period_dates('daily', None)
        
        assert start == date.today()
        assert end == date.today()
    
    def test_weekly_mode_monday_start(self):
        """Weekly mode should return Monday as start, Sunday as end."""
        # December 10, 2025 is a Wednesday
        ref_date = date(2025, 12, 10)
        start, end = get_period_dates('weekly', ref_date)
        
        assert start == date(2025, 12, 8)  # Monday
        assert end == date(2025, 12, 14)   # Sunday
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6    # Sunday
    
    def test_weekly_mode_when_ref_is_monday(self):
        """When reference is already Monday, should still return same week."""
        ref_date = date(2025, 12, 8)  # Monday
        start, end = get_period_dates('weekly', ref_date)
        
        assert start == date(2025, 12, 8)
        assert end == date(2025, 12, 14)
    
    def test_weekly_mode_when_ref_is_sunday(self):
        """When reference is Sunday, should return same week."""
        ref_date = date(2025, 12, 14)  # Sunday
        start, end = get_period_dates('weekly', ref_date)
        
        assert start == date(2025, 12, 8)
        assert end == date(2025, 12, 14)
    
    def test_monthly_mode_returns_first_and_last_day(self):
        """Monthly mode should return first and last day of month."""
        ref_date = date(2025, 12, 15)
        start, end = get_period_dates('monthly', ref_date)
        
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)
    
    def test_monthly_mode_february_non_leap_year(self):
        """February in non-leap year should end on 28th."""
        ref_date = date(2025, 2, 15)
        start, end = get_period_dates('monthly', ref_date)
        
        assert start == date(2025, 2, 1)
        assert end == date(2025, 2, 28)
    
    def test_monthly_mode_february_leap_year(self):
        """February in leap year should end on 29th."""
        ref_date = date(2024, 2, 15)
        start, end = get_period_dates('monthly', ref_date)
        
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)
    
    def test_unknown_mode_defaults_to_daily(self):
        """Unknown time modes should default to daily behavior."""
        ref_date = date(2025, 12, 10)
        start, end = get_period_dates('unknown_mode', ref_date)
        
        assert start == ref_date
        assert end == ref_date


class TestGetWeekBoundaries:
    """Tests for get_week_boundaries function."""
    
    def test_default_week_start_monday(self):
        """Default week should start on Monday."""
        target = date(2025, 12, 10)  # Wednesday
        start, end = get_week_boundaries(target)
        
        assert start == date(2025, 12, 8)   # Monday
        assert end == date(2025, 12, 14)    # Sunday
    
    def test_week_start_sunday(self):
        """Week can start on Sunday (week_start=6)."""
        target = date(2025, 12, 10)  # Wednesday
        start, end = get_week_boundaries(target, week_start=6)
        
        assert start == date(2025, 12, 7)   # Sunday
        assert end == date(2025, 12, 13)    # Saturday
    
    def test_week_boundaries_year_crossing(self):
        """Week boundaries around New Year should work correctly."""
        target = date(2025, 1, 1)  # Wednesday
        start, end = get_week_boundaries(target)
        
        assert start == date(2024, 12, 30)  # Monday of that week
        assert end == date(2025, 1, 5)      # Sunday


class TestGetNextPeriodStart:
    """Tests for get_next_period_start function."""
    
    def test_next_day_for_daily(self):
        """For daily tracker, next period starts next day."""
        current_end = date(2025, 12, 10)
        next_start = get_next_period_start('daily', current_end)
        
        assert next_start == date(2025, 12, 11)
    
    def test_next_monday_for_weekly(self):
        """For weekly tracker, next period starts next Monday."""
        current_end = date(2025, 12, 14)  # Sunday
        next_start = get_next_period_start('weekly', current_end)
        
        assert next_start == date(2025, 12, 15)  # Monday
    
    def test_first_of_next_month_for_monthly(self):
        """For monthly tracker, next period starts 1st of next month."""
        current_end = date(2025, 12, 31)
        next_start = get_next_period_start('monthly', current_end)
        
        assert next_start == date(2026, 1, 1)


class TestFormatPeriodDisplay:
    """Tests for format_period_display function."""
    
    def test_daily_format(self):
        """Daily periods show single date."""
        result = format_period_display(date(2025, 12, 10), date(2025, 12, 10), 'daily')
        
        assert '10' in result or 'Dec' in result
    
    def test_weekly_format(self):
        """Weekly periods show date range."""
        result = format_period_display(date(2025, 12, 8), date(2025, 12, 14), 'weekly')
        
        assert '8' in result or 'Dec' in result
    
    def test_monthly_format(self):
        """Monthly periods show month name."""
        result = format_period_display(date(2025, 12, 1), date(2025, 12, 31), 'monthly')
        
        assert 'December' in result or 'Dec' in result
        assert '2025' in result


class TestGetUserToday:
    """Tests for get_user_today function."""
    
    def test_utc_timezone(self):
        """UTC timezone should return consistent date."""
        result = get_user_today('UTC')
        
        assert isinstance(result, date)
        assert result is not None
    
    def test_new_york_timezone(self):
        """America/New_York timezone should return valid date."""
        result = get_user_today('America/New_York')
        
        assert isinstance(result, date)
    
    def test_asia_kolkata_timezone(self):
        """Asia/Kolkata timezone should return valid date."""
        result = get_user_today('Asia/Kolkata')
        
        assert isinstance(result, date)
    
    def test_edge_time_near_midnight_utc(self):
        """Edge case: Test behavior around midnight UTC."""
        # At 23:59 UTC, some timezones are already in the next day
        with patch('django.utils.timezone') as mock_tz:
            mock_tz.now.return_value = datetime(2025, 12, 10, 23, 59, 0, tzinfo=pytz.UTC)
            
            utc_today = get_user_today('UTC')
            kolkata_today = get_user_today('Asia/Kolkata')  # UTC+5:30
            
            # Kolkata at 23:59 UTC is 05:29 next day
            assert kolkata_today >= utc_today


class TestToUserDatetime:
    """Tests for to_user_datetime function."""
    
    def test_convert_utc_to_eastern(self):
        """Convert UTC datetime to Eastern time."""
        utc_dt = datetime(2025, 12, 10, 18, 0, 0, tzinfo=pytz.UTC)
        result = to_user_datetime(utc_dt, 'America/New_York')
        
        assert result.hour == 13  # EST is UTC-5
    
    def test_naive_datetime_assumed_utc(self):
        """Naive datetime should be assumed UTC."""
        naive_dt = datetime(2025, 12, 10, 12, 0, 0)
        result = to_user_datetime(naive_dt, 'Asia/Kolkata')
        
        assert result.hour == 17  # IST is UTC+5:30
        assert result.minute == 30


class TestGetDayBoundaries:
    """Tests for get_day_boundaries function."""
    
    def test_utc_day_boundaries(self):
        """UTC day boundaries should be 00:00 to 23:59:59."""
        target = date(2025, 12, 10)
        start, end = get_day_boundaries(target, 'UTC')
        
        assert start.hour == 0
        assert start.minute == 0
        assert end.date() == target or end.date() == date(2025, 12, 11)
    
    def test_different_timezone_boundaries(self):
        """Different timezone should shift UTC boundaries."""
        target = date(2025, 12, 10)
        start_utc, end_utc = get_day_boundaries(target, 'UTC')
        start_ny, end_ny = get_day_boundaries(target, 'America/New_York')
        
        # NYC midnight happens at 05:00 UTC
        assert start_ny != start_utc


class TestGetMonthBoundaries:
    """Tests for get_month_boundaries function."""
    
    def test_regular_month(self):
        """Test boundaries for a regular 31-day month."""
        target = date(2025, 12, 15)
        start, end = get_month_boundaries(target)
        
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)
    
    def test_february_non_leap(self):
        """February non-leap year ends on 28th."""
        target = date(2025, 2, 10)
        start, end = get_month_boundaries(target)
        
        assert start == date(2025, 2, 1)
        assert end == date(2025, 2, 28)
    
    def test_february_leap(self):
        """February leap year ends on 29th."""
        target = date(2024, 2, 10)
        start, end = get_month_boundaries(target)
        
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)
    
    def test_thirty_day_month(self):
        """April has 30 days."""
        target = date(2025, 4, 15)
        start, end = get_month_boundaries(target)
        
        assert start == date(2025, 4, 1)
        assert end == date(2025, 4, 30)


class TestCalculateDaysInRange:
    """Tests for calculate_days_in_range function."""
    
    def test_same_day_returns_one(self):
        """Same start and end date should return 1."""
        result = calculate_days_in_range(date(2025, 12, 10), date(2025, 12, 10))
        
        assert result == 1
    
    def test_two_consecutive_days(self):
        """Two consecutive days should return 2."""
        result = calculate_days_in_range(date(2025, 12, 10), date(2025, 12, 11))
        
        assert result == 2
    
    def test_week_range(self):
        """One week should return 7."""
        result = calculate_days_in_range(date(2025, 12, 8), date(2025, 12, 14))
        
        assert result == 7
    
    def test_month_range(self):
        """Full month of December should return 31."""
        result = calculate_days_in_range(date(2025, 12, 1), date(2025, 12, 31))
        
        assert result == 31


class TestGetRelativeDateDescription:
    """Tests for get_relative_date_description function."""
    
    def test_today(self):
        """Today should return 'Today'."""
        result = get_relative_date_description(date.today())
        
        assert result.lower() == 'today'
    
    def test_yesterday(self):
        """Yesterday should return 'Yesterday'."""
        result = get_relative_date_description(date.today() - timedelta(days=1))
        
        assert result.lower() == 'yesterday'
    
    def test_tomorrow(self):
        """Tomorrow should return 'Tomorrow'."""
        result = get_relative_date_description(date.today() + timedelta(days=1))
        
        assert 'tomorrow' in result.lower()
    
    def test_days_ago(self):
        """Past dates should show 'X days ago'."""
        result = get_relative_date_description(date.today() - timedelta(days=3))
        
        assert '3' in result or 'days' in result.lower()
    
    def test_with_reference_date(self):
        """Should work with explicit reference date."""
        ref = date(2025, 12, 15)
        target = date(2025, 12, 14)
        result = get_relative_date_description(target, ref)
        
        assert 'yesterday' in result.lower() or '1' in result


class TestParseDateString:
    """Tests for parse_date_string function."""
    
    def test_iso_format(self):
        """Parse ISO format date string."""
        result = parse_date_string('2025-12-10')
        
        assert result == date(2025, 12, 10)
    
    def test_relative_today(self):
        """Parse 'today' string."""
        result = parse_date_string('today')
        
        assert result == date.today()
    
    def test_relative_yesterday(self):
        """Parse 'yesterday' string."""
        result = parse_date_string('yesterday')
        
        assert result == date.today() - timedelta(days=1)
    
    def test_relative_tomorrow(self):
        """Parse 'tomorrow' string."""
        result = parse_date_string('tomorrow')
        
        assert result == date.today() + timedelta(days=1)
    
    def test_short_format(self):
        """Parse short format dates (MM/DD/YYYY)."""
        result = parse_date_string('12/10/2025')
        
        assert result == date(2025, 12, 10)
    
    def test_invalid_format_raises_error(self):
        """Invalid format should raise ValueError."""
        with pytest.raises(ValueError):
            parse_date_string('not-a-date')
    
    def test_empty_string_raises_error(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError):
            parse_date_string('')


class TestEdgeCases:
    """Edge case tests for time utilities."""
    
    def test_year_boundary_weekly(self):
        """Week spanning year boundary."""
        ref_date = date(2025, 12, 31)  # Wednesday
        start, end = get_period_dates('weekly', ref_date)
        
        # Week should span from Dec 29, 2025 to Jan 4, 2026
        assert start.year == 2025
        assert end.year == 2026
    
    def test_year_boundary_monthly(self):
        """Month at year boundary."""
        ref_date = date(2025, 12, 15)
        start, end = get_period_dates('monthly', ref_date)
        
        assert start == date(2025, 12, 1)
        assert end == date(2025, 12, 31)
    
    def test_leap_day_2024(self):
        """February 29 in leap year."""
        ref_date = date(2024, 2, 29)
        start, end = get_period_dates('daily', ref_date)
        
        assert start == date(2024, 2, 29)
        assert end == date(2024, 2, 29)
    
    def test_month_boundaries_january(self):
        """January month boundaries."""
        start, end = get_month_boundaries(date(2025, 1, 15))
        
        assert start == date(2025, 1, 1)
        assert end == date(2025, 1, 31)
