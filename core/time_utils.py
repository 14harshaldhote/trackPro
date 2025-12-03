from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta

def get_period_dates(time_mode, reference_date=None):
    """
    Calculates the start and end dates for a period based on the mode and reference date.
    
    Args:
        time_mode (str): 'daily', 'weekly', 'monthly'
        reference_date (date): The date to calculate the period for. Defaults to today.
        
    Returns:
        tuple: (start_date, end_date)
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
        # Default to daily for unknown modes or custom (for now)
        return reference_date, reference_date

def get_next_period_start(time_mode, current_end_date):
    """Returns the start date of the next period."""
    return current_end_date + timedelta(days=1)
