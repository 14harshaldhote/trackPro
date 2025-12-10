"""
Search Service

Handles global search across Trackers, Tasks, and Goals.
Enhanced for V1.5 with search history, suggestions, and analytics.
"""
from typing import Dict, List, Optional
from datetime import date, timedelta
from django.db.models import Q, Count
from django.utils import timezone
from core.models import TrackerDefinition, TaskTemplate, Goal, SearchHistory, Tag
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """
    Service for search operations.
    Enhanced for V1.5 with history and personalization.
    """
    
    def search(self, user, query: str, save_history: bool = True) -> Dict:
        """
        Perform global search.
        
        Args:
            user: User object
            query: Search string
            save_history: Whether to save to history
            
        Returns:
            Dict with results for trackers, tasks, goals.
        """
        results = {
            'query': query,
            'trackers': [],
            'tasks': [],
            'goals': [],
            'tags': [],
            'suggestions': [],
        }
        
        if not query or len(query) < 2:
            recent_queries = list(SearchHistory.get_recent_searches(user, limit=5))
            results['suggestions'] = [{'query': item['query'], 'type': 'recent'} for item in recent_queries]
            return results

        # Search Trackers
        trackers = TrackerDefinition.objects.filter(
            user=user,
            name__icontains=query
        ).exclude(status='archived')[:5]
        
        results['trackers'] = [
            {
                'id': str(t.tracker_id),
                'name': t.name,
                'type': 'tracker',
                'description': t.description[:100] if t.description else '',
                'url': f'/tracker/{t.tracker_id}/',
                'status': t.status,
                'task_count': getattr(t, 'task_count', 0) 
            }
            for t in trackers
        ]
        
        # Search Task Templates
        task_templates = TaskTemplate.objects.filter(
            tracker__user=user,
            description__icontains=query
        ).select_related('tracker')[:10]
        
        results['tasks'] = [
            {
                'id': str(t.template_id),
                'name': t.description,
                'type': 'task',
                'tracker_name': t.tracker.name,
                'category': t.category,
                'url': f'/tracker/{t.tracker.tracker_id}/?highlight={t.template_id}'
            }
            for t in task_templates
        ]
        
        # Search Goals
        goals = Goal.objects.filter(
            user=user,
            title__icontains=query
        ).exclude(status='abandoned')[:5]
        
        results['goals'] = [
            {
                'id': str(g.goal_id),
                'name': g.title,
                'type': 'goal',
                'icon': g.icon,
                'progress': g.progress,
                'url': '/goals/'
            }
            for g in goals
        ]
        
        # V1.5: Search Tags
        tags = Tag.objects.filter(
            user=user,
            name__icontains=query
        )[:5]
        
        results['tags'] = [
            {
                'id': str(t.tag_id),
                'name': t.name,
                'type': 'tag',
                'color': t.color,
                'icon': t.icon
            }
            for t in tags
        ]
        
        total_count = (
            len(results['trackers']) + 
            len(results['tasks']) + 
            len(results['goals']) + 
            len(results['tags'])
        )
        results['total_count'] = total_count
        
        if save_history and total_count > 0:
            SearchHistory.objects.create(
                user=user,
                query=query,
                result_count=total_count,
                search_context='global'
            )
            
        return results

    # =========================================================================
    # V1.5 SEARCH HISTORY FEATURES
    # =========================================================================
    
    @staticmethod
    def get_recent_searches(user, limit: int = 10) -> List[Dict]:
        """
        Get user's recent search queries.
        
        Args:
            user: User object
            limit: Maximum number of results
            
        Returns:
            List of recent search dicts
        """
        recent = SearchHistory.objects.filter(
            user=user
        ).values('query').annotate(
            count=Count('search_id'),
            last_searched=Count('created_at')
        ).order_by('-last_searched')[:limit]
        
        return [
            {
                'query': item['query'],
                'count': item['count'],
                'type': 'recent'
            }
            for item in recent
        ]
    
    @staticmethod
    def get_popular_searches(user=None, days: int = 30, limit: int = 10) -> List[Dict]:
        """
        Get popular search queries across all users or for a specific user.
        
        Args:
            user: Optional user to filter by
            days: Number of days to look back
            limit: Maximum number of results
            
        Returns:
            List of popular search dicts
        """
        since = timezone.now() - timedelta(days=days)
        
        query = SearchHistory.objects.filter(
            created_at__gte=since
        )
        
        if user:
            query = query.filter(user=user)
        
        popular = query.values('query').annotate(
            search_count=Count('search_id'),
            avg_results=Count('result_count')
        ).filter(
            search_count__gte=2  # Must be searched at least twice
        ).order_by('-search_count')[:limit]
        
        return [
            {
                'query': item['query'],
                'popularity': item['search_count'],
                'type': 'popular'
            }
            for item in popular
        ]
    
    @staticmethod
    def get_search_suggestions(user, partial_query: str, limit: int = 5) -> List[Dict]:
        """
        Get search suggestions based on partial query.
        Combines recent searches, popular searches, and content matching.
        
        Args:
            user: User object
            partial_query: Partial search query
            limit: Maximum suggestions
            
        Returns:
            List of suggestion dicts
        """
        suggestions = []
        
        if len(partial_query) < 2:
            # Return recent searches for short queries
            recent = SearchHistory.objects.filter(
                user=user
            ).values_list('query', flat=True).distinct()[:limit]
            return [{'query': q, 'type': 'recent'} for q in recent]
        
        # 1. Match from user's search history
        history_matches = SearchHistory.objects.filter(
            user=user,
            query__icontains=partial_query
        ).values_list('query', flat=True).distinct()[:3]
        
        for q in history_matches:
            suggestions.append({'query': q, 'type': 'history'})
        
        # 2. Match from tracker names
        tracker_names = TrackerDefinition.objects.filter(
            user=user,
            name__icontains=partial_query,
            deleted_at__isnull=True
        ).values_list('name', flat=True)[:2]
        
        for name in tracker_names:
            suggestions.append({'query': name, 'type': 'tracker'})
        
        # 3. Match from task descriptions
        task_descriptions = TaskTemplate.objects.filter(
            tracker__user=user,
            description__icontains=partial_query,
            deleted_at__isnull=True
        ).values_list('description', flat=True)[:2]
        
        for desc in task_descriptions:
            # Truncate long descriptions
            short_desc = desc[:50] if len(desc) > 50 else desc
            suggestions.append({'query': short_desc, 'type': 'task'})
        
        # Deduplicate and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s['query'] not in seen:
                seen.add(s['query'])
                unique_suggestions.append(s)
        
        return unique_suggestions[:limit]
    
    @staticmethod
    def clear_search_history(user, older_than_days: int = None) -> int:
        """
        Clear user's search history.
        
        Args:
            user: User object
            older_than_days: If set, only clear entries older than this
            
        Returns:
            Number of entries deleted
        """
        query = SearchHistory.objects.filter(user=user)
        
        if older_than_days:
            cutoff = timezone.now() - timedelta(days=older_than_days)
            query = query.filter(created_at__lt=cutoff)
        
        count, _ = query.delete()
        return count
    
    @staticmethod
    def get_search_analytics(user) -> Dict:
        """
        Get analytics about user's search behavior.
        
        Returns:
            Dict with search analytics
        """
        history = SearchHistory.objects.filter(user=user)
        
        total_searches = history.count()
        
        if total_searches == 0:
            return {
                'total_searches': 0,
                'unique_queries': 0,
                'top_queries': [],
                'avg_results_per_search': 0
            }
        
        unique_queries = history.values('query').distinct().count()
        
        top_queries = history.values('query').annotate(
            count=Count('search_id')
        ).order_by('-count')[:5]
        
        from django.db.models import Avg
        avg_results = history.aggregate(avg=Avg('result_count'))
        
        return {
            'total_searches': total_searches,
            'unique_queries': unique_queries,
            'top_queries': list(top_queries),
            'avg_results_per_search': avg_results['avg'] or 0
        }
