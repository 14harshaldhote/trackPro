"""
Cursor-Based Pagination for Mobile Performance
More efficient than offset pagination for large datasets.

Following OpusSuggestion.md Part 4.1: Infinite Scroll for Task Lists
"""
from typing import Dict, List, Any, Optional, Callable
from django.db.models import QuerySet
from django.http import JsonResponse


class CursorPaginator:
    """
    Cursor-based pagination for infinite scroll.
    
    Usage:
        paginator = CursorPaginator(
            queryset=TaskInstance.objects.all(),
            cursor_field='created_at',
            page_size=20
        )
        
        result = paginator.paginate(cursor=request.GET.get('cursor'))
    """
    
    def __init__(
        self,
        queryset: QuerySet,
        cursor_field: str = 'created_at',
        page_size: int = 20,
        max_page_size: int = 100
    ):
        """
        Initialize cursor paginator.
        
        Args:
            queryset: Django queryset to paginate
            cursor_field: Field to use for cursor (should be indexed)
            page_size: Number of items per page
            max_page_size: Maximum allowed page size
        """
        self.queryset = queryset
        self.cursor_field = cursor_field
        self.page_size = min(page_size, max_page_size)
    
    def paginate(self, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Paginate queryset.
        
        Args:
            cursor: Cursor value from previous page
        
        Returns:
            {
                'items': [...],
                'pagination': {
                    'has_more': bool,
                    'next_cursor': str,
                    'count': int
                }
            }
        """
        # Apply cursor filter
        qs = self.queryset
        if cursor:
            # Use __lt for descending order (most recent first)
            qs = qs.filter(**{f'{self.cursor_field}__lt': cursor})
        
        # Order by cursor field (descending for recent-first)
        qs = qs.order_by(f'-{self.cursor_field}')
        
        # Fetch one extra to determine if there are more
        items = list(qs[:self.page_size + 1])
        
        has_more = len(items) > self.page_size
        if has_more:
            items = items[:self.page_size]
        
        # Get next cursor
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            cursor_value = getattr(last_item, self.cursor_field)
            # Convert datetime to ISO format string
            if hasattr(cursor_value, 'isoformat'):
                next_cursor = cursor_value.isoformat()
            else:
                next_cursor = str(cursor_value)
        
        return {
            'items': items,
            'pagination': {
                'has_more': has_more,
                'next_cursor': next_cursor,
                'page_size': self.page_size,
                'returned_count': len(items)
            }
        }


def paginated_response(
    items: List[Any],
    serializer_func: Callable,
    has_more: bool,
    next_cursor: Optional[str],
    meta: Optional[Dict] = None
) -> JsonResponse:
    """
    Create standardized paginated response.
    
    Args:
        items: List of items to serialize
        serializer_func: Function to serialize each item
        has_more: Whether more items exist
        next_cursor: Cursor for next page
        meta: Additional metadata
    
    Returns:
        JsonResponse with paginated data
    """
    return JsonResponse({
        'data': [serializer_func(item) for item in items],
        'pagination': {
            'has_more': has_more,
            'next_cursor': next_cursor,
            'count': len(items)
        },
        'meta': meta or {}
    })


class OffsetPaginator:
    """
    Traditional offset-based pagination (less efficient for large datasets).
    Use CursorPaginator for mobile infinite scroll.
    """
    
    def __init__(
        self,
        queryset: QuerySet,
        page_size: int = 20,
        max_page_size: int = 100
    ):
        self.queryset = queryset
        self.page_size = min(page_size, max_page_size)
    
    def paginate(self, page: int = 1) -> Dict[str, Any]:
        """
        Paginate queryset with offset.
        
        Args:
            page: Page number (1-indexed)
        
        Returns:
            Dict with items and pagination info
        """
        offset = (page - 1) * self.page_size
        items = list(self.queryset[offset:offset + self.page_size])
        total_count = self.queryset.count()
        
        return {
            'items': items,
            'pagination': {
                'page': page,
                'page_size': self.page_size,
                'total_count': total_count,
                'total_pages': (total_count + self.page_size - 1) // self.page_size,
                'has_next': offset + self.page_size < total_count,
                'has_prev': page > 1
            }
        }
