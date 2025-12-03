"""
Custom template filters and tags for the tracker app.
"""
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to safely get dictionary items or list elements.
    Usage: {{ dict|get_item:key }} or {{ list|get_item:index }}
    """
    if dictionary is None:
        return None
    
    try:
        # Handle dictionaries
        if isinstance(dictionary, dict):
            return dictionary.get(key)
        # Handle lists/tuples
        elif isinstance(dictionary, (list, tuple)):
            return dictionary[int(key)]
        else:
            return dictionary.get(key) if hasattr(dictionary, 'get') else None
    except (KeyError, IndexError, ValueError, TypeError):
        return None

@register.filter
def add_days(value, days):
    """
    Add days to a date.
    Usage: {{ date|add_days:7 }}
    """
    from datetime import timedelta
    try:
        return value + timedelta(days=days)
    except:
        return value

@register.filter
def percentage(value):
    """Convert decimal to percentage."""
    try:
        return f"{float(value) * 100:.1f}"
    except (ValueError, TypeError):
        return "0.0"
