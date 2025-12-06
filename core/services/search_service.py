"""
Search Service

Handles global search across Trackers, Tasks, and Goals.
"""
from typing import Dict, List, Optional
from django.db.models import Q
from core.models import TrackerDefinition, TaskTemplate, Goal, SearchHistory

class SearchService:
    """
    Service for search operations.
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
        
        total_count = len(results['trackers']) + len(results['tasks']) + len(results['goals'])
        results['total_count'] = total_count
        
        if save_history and total_count > 0:
            SearchHistory.objects.create(
                user=user,
                query=query,
                result_count=total_count,
                search_context='global'
            )
            
        return results
