"""
Time utility functions for Tracker Pro.

This module provides date and time calculation utilities for tracker periods,
handling daily, weekly, and monthly time modes.

Author: Tracker Pro Team
Created: 2025-12-03
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Tuple, Optional


def get_period_dates(time_mode: str, reference_date: Optional[date] = None) -> Tuple[date, date]:
    """
    Calculate the start and end dates for a tracker period.
    
    This function determines the period boundaries based on the tracker's time mode
    and a reference date. For weekly trackers, weeks start on Monday.
    
    Args:
        time_mode (str): One of 'daily', 'weekly', 'monthly', or 'custom'
        reference_date (Optional[date]): Date to calculate period for. Defaults to today.
    
    Returns:
        Tuple[date, date]: (start_date, end_date) for the period
    
    Examples:
        >>> # Daily tracker for today
        >>> get_period_dates('daily')
        (date(2025, 12, 3), date(2025, 12, 3))
        
        >>> # Weekly tracker (Monday to Sunday)
        >>> get_period_dates('weekly', date(2025, 12, 3))  # Wednesday
        (date(2025, 12, 1), date(2025, 12, 7))  # Mon-Sun
        
        >>> # Monthly tracker
        >>> get_period_dates('monthly', date(2025, 12, 15))
        (date(2025, 12, 1), date(2025, 12, 31))
    
    Note:
        - Weekly periods always start on Monday (ISO week standard)
        - Monthly periods span the entire calendar month
        - Unknown modes default to daily behavior
    """
    if reference_date is None:
        reference_date = date.today()
    
    if time_mode == 'daily':
        return reference_date, reference_date
    
    elif time_mode == 'weekly':
        # Monday is 0, Sunday is 6
        weekday = reference_date.weekday()
        start_date = reference_date - timedelta(days=weekday)
        end_date = start_date + timedelta(days=6)
        return start_date, end_date
    
    elif time_mode == 'monthly':
        start_date = reference_date.replace(day=1)
        end_date = start_date + relativedelta(months=1, days=-1)
        return start_date, end_date
    
    else:
        # Default to daily for unknown modes or custom
        return reference_date, reference_date

def get_week_boundaries(target_date: date, week_start: int = 0) -> Tuple[date, date]:
    """
    Get week boundaries for a given date.
    
    Args:
        target_date: Date to get boundaries for
        week_start: 0=Monday, 6=Sunday
    """
    days_since_start = (target_date.weekday() - week_start) % 7
    period_start = target_date - timedelta(days=days_since_start)
    period_end = period_start + timedelta(days=6)
    return period_start, period_end


def get_next_period_start(time_mode: str, current_end_date: date) -> date:
    """
    Calculate the start date of the next period.
    
    Args:
        time_mode (str): Tracker's time mode
        current_end_date (date): End date of the current period
    
    Returns:
        date: Start date of the next period (always current_end + 1 day)
    
    Example:
        >>> get_next_period_start('weekly', date(2025, 12, 7))  # Sunday
        date(2025, 12, 8)  # Monday
    """
    return current_end_date + timedelta(days=1)


def format_period_display(start_date: date, end_date: date, time_mode: str) -> str:
    """
    Format a period as a human-readable string.
    
    Args:
        start_date (date): Period start
        end_date (date): Period end
        time_mode (str): Tracker's time mode
    
    Returns:
        str: Formatted period string
    
    Examples:
        >>> format_period_display(date(2025, 12, 3), date(2025, 12, 3), 'daily')
        'Dec 3, 2025'
        
        >>> format_period_display(date(2025, 12, 1), date(2025, 12, 7), 'weekly')
        'Dec 1-7, 2025'
        
        >>> format_period_display(date(2025, 12, 1), date(2025, 12, 31), 'monthly')
        'December 2025'
    """
    if time_mode == 'daily':
        return start_date.strftime('%b %d, %Y')
    elif time_mode == 'weekly':
        if start_date.month == end_date.month:
            return f"{start_date.strftime('%b')} {start_date.day}-{end_date.day}, {start_date.year}"
        else:
            return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    elif time_mode == 'monthly':
        return start_date.strftime('%B %Y')
    else:
        return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"


# =============================================================================
# TIMEZONE-AWARE UTILITIES (Added for V1.0 - finalePhase.md Section 6.1)
# =============================================================================

def get_user_today(user_timezone: str) -> date:
    """
    Get 'today' in user's timezone.
    
    This is critical for streak calculations and reminders - the user's
    local date determines what "today" means for them.
    
    Args:
        user_timezone: IANA timezone string (e.g., 'America/New_York')
        
    Returns:
        date: Today's date in the user's timezone
    """
    from django.utils import timezone
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo  # Python < 3.9
    
    try:
        tz = ZoneInfo(user_timezone)
        return timezone.now().astimezone(tz).date()
    except Exception:
        # Fallback to UTC if timezone is invalid
        return timezone.now().date()


def to_user_datetime(dt, user_timezone: str):
    """
    Convert UTC datetime to user's timezone.
    
    Args:
        dt: datetime object (assumes UTC if naive)
        user_timezone: IANA timezone string
        
    Returns:
        datetime: The datetime converted to user's timezone
    """
    from datetime import datetime, time
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    
    if dt is None:
        return None
    
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        return dt.astimezone(ZoneInfo(user_timezone))
    except Exception:
        return dt


def get_day_boundaries(target_date: date, user_timezone: str) -> tuple:
    """
    Get midnight-to-midnight in user's timezone as UTC.
    
    This is essential for querying tasks within a user's "day" which
    may span two UTC dates.
    
    Args:
        target_date: The date to get boundaries for
        user_timezone: IANA timezone string
        
    Returns:
        Tuple of (start_utc, end_utc) datetimes
    """
    from datetime import datetime, time as dt_time
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo
    
    try:
        tz = ZoneInfo(user_timezone)
        start = datetime.combine(target_date, dt_time.min).replace(tzinfo=tz)
        end = datetime.combine(target_date, dt_time.max).replace(tzinfo=tz)
        return start.astimezone(ZoneInfo('UTC')), end.astimezone(ZoneInfo('UTC'))
    except Exception:
        # Fallback to simple date boundaries
        start = datetime.combine(target_date, dt_time.min)
        end = datetime.combine(target_date, dt_time.max)
        return start, end


def get_month_boundaries(target_date: date) -> Tuple[date, date]:
    """
    Get first and last day of the month.
    
    Args:
        target_date: Any date within the target month
        
    Returns:
        Tuple of (period_start, period_end)
    """
    from calendar import monthrange
    
    period_start = target_date.replace(day=1)
    _, last_day = monthrange(target_date.year, target_date.month)
    period_end = target_date.replace(day=last_day)
    return period_start, period_end


def calculate_days_in_range(start_date: date, end_date: date) -> int:
    """
    Calculate the number of days between two dates (inclusive).
    
    Args:
        start_date: Range start
        end_date: Range end
        
    Returns:
        int: Number of days
    """
    return (end_date - start_date).days + 1


def get_relative_date_description(target_date: date, reference_date: date = None) -> str:
    """
    Get a human-friendly description of a date relative to today.
    
    Args:
        target_date: The date to describe
        reference_date: Optional reference (defaults to today)
        
    Returns:
        str: Human-friendly description like "Today", "Yesterday", "3 days ago"
    """
    if reference_date is None:
        reference_date = date.today()
    
    diff = (target_date - reference_date).days
    
    if diff == 0:
        return "Today"
    elif diff == 1:
        return "Tomorrow"
    elif diff == -1:
        return "Yesterday"
    elif diff > 0 and diff <= 7:
        return f"In {diff} days"
    elif diff < 0 and diff >= -7:
        return f"{abs(diff)} days ago"
    else:
        return target_date.strftime('%b %d, %Y')


def parse_date_string(date_str: str) -> date:
    """
    Parse various date string formats.
    
    Supports:
    - ISO format: '2025-12-09'
    - Short format: '12/09/2025'
    - Relative: 'today', 'yesterday', 'tomorrow'
    
    Args:
        date_str: Date string to parse
        
    Returns:
        date: Parsed date object
        
    Raises:
        ValueError: If format is unrecognized
    """
    from datetime import datetime
    
    date_str = date_str.strip().lower()
    today = date.today()
    
    # Relative dates
    if date_str == 'today':
        return today
    elif date_str == 'yesterday':
        return today - timedelta(days=1)
    elif date_str == 'tomorrow':
        return today + timedelta(days=1)
    
    # Try ISO format first
    try:
        return datetime.strptime(date_str.upper(), '%Y-%m-%d').date()
    except ValueError:
        pass
    
    # Try US format
    try:
        return datetime.strptime(date_str, '%m/%d/%Y').date()
    except ValueError:
        pass
    
    # Try European format
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        pass
    
    raise ValueError(f"Could not parse date string: {date_str}")
