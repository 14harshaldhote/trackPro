"""
Cursor-Based Pagination for Mobile Performance

More efficient than offset pagination for large datasets.
Provides consistent performance regardless of page depth.
"""
from typing import Dict, List, Any, Optional, Callable
from django.db.models import QuerySet
from django.http import JsonResponse


class CursorPaginator:
    """
    Cursor-based pagination for infinite scroll.
    
    Advantages over offset pagination:
    - Consistent performance (no count queries)
    - Works well with real-time data changes
    - Better for mobile (3G/4G optimized)
    
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
        Initialize paginator.
        
        Args:
            queryset: Django QuerySet to paginate
            cursor_field: Field to use as cursor (should be indexed)
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
            cursor: Cursor value from previous page (string)
        
        Returns:
            {
                'items': List of model instances,
                'pagination': {
                    'has_more': bool,
                    'next_cursor': str or None,
                    'page_size': int,
                    'returned_count': int
                }
            }
        """
        # Apply cursor filter
        qs = self.queryset
        if cursor:
            # Filter for items "older" than cursor
            qs = qs.filter(**{f'{self.cursor_field}__lt': cursor})
        
        # Order by cursor field (descending for "latest first")
        qs = qs.order_by(f'-{self.cursor_field}')
        
        # Fetch one extra to determine if there are more
        items = list(qs[:self.page_size + 1])
        
        has_more = len(items) > self.page_size
        if has_more:
            items = items[:self.page_size]
        
        # Get next cursor from last item
        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            cursor_value = getattr(last_item, self.cursor_field)
            # Convert to ISO format if datetime
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
    serializer_func: Callable[[Any], Dict],
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


def offset_pagination(
    queryset: QuerySet,
    page: int = 1,
    per_page: int = 20,
    max_per_page: int = 100
) -> Dict:
    """
    Traditional offset-based pagination (for simpler use cases).
    
    Args:
        queryset: Django QuerySet to paginate
        page: Page number (1-indexed)
        per_page: Items per page
        max_per_page: Maximum allowed per page
    
    Returns:
        {
            'items': List of items,
            'pagination': {
                'page': int,
                'per_page': int,
                'total_pages': int,
                'total_count': int,
                'has_next': bool,
                'has_prev': bool
            }
        }
    """
    per_page = min(per_page, max_per_page)
    page = max(1, page)
    
    # Get total count
    total_count = queryset.count()
    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1
    
    # Clamp page to valid range
    page = min(page, total_pages)
    
    # Get items for this page
    offset = (page - 1) * per_page
    items = list(queryset[offset:offset + per_page])
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_count': total_count,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }
