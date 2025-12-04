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
