"""
Analytics Service (Enhanced with User Isolation)

Wraps analytics functions with cleaner interface, caching, and user context.
Provides high-level methods for common analytics operations with multi-user support.
"""
from datetime import date, timedelta
from typing import Dict, List, Optional
from django.db.models import Count, Q, Avg

from core import analytics
from core.models import TrackerDefinition, TrackerInstance, TaskInstance, Goal
from core.helpers.cache_helpers import cache_result, CACHE_TIMEOUTS


class AnalyticsService:
    """
    Service for analytics operations with user isolation.
    
    Wraps lower-level analytics functions with business logic, caching, and user context.
    All queries are scoped to the authenticated user.
    """
    
    def __init__(self, tracker_id: str = None, user=None):
        """
        Initialize analytics service.
        
        Args:
            tracker_id: Optional tracker ID for tracker-specific analytics
            user: Django User object for user isolation
        """
        self.tracker_id = tracker_id
        self.user = user
        
        # Validate user has access to tracker
        if tracker_id and user:
            self._validate_access()
    
    def _validate_access(self):
        """Ensure user has access to the tracker."""
        if self.tracker_id and self.user:
            exists = TrackerDefinition.objects.filter(
                tracker_id=self.tracker_id,
                user=self.user
            ).exists()
            if not exists:
                raise PermissionError(f"User does not have access to tracker {self.tracker_id}")
    
    def get_tracker_dashboard_stats(self) -> Dict:
        """
        Get comprehensive statistics for tracker detail page.
        
        Combines multiple analytics calls into single dashboard dataset.
        """
        if not self.tracker_id:
            return {}
            
        return {
            'completion': analytics.compute_completion_rate(self.tracker_id),
            'streaks': analytics.detect_streaks(self.tracker_id),
            'consistency': analytics.compute_consistency_score(self.tracker_id),
            'balance': analytics.compute_balance_score(self.tracker_id),
            'effort': analytics.compute_effort_index(self.tracker_id)
        }
    
    def get_user_overview(self) -> Dict:
        """
        Get overview stats for all user trackers (dashboard).
        
        Uses ORM with optimizations for efficient querying.
        """
        if not self.user:
            return {}
        
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        trackers = TrackerDefinition.objects.filter(user=self.user, status='active')
        
        # Aggregate task stats using ORM
        task_stats = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__period_start__gte=week_ago
        ).aggregate(
            total_tasks=Count('task_instance_id'),
            completed_tasks=Count('task_instance_id', filter=Q(status='DONE')),
            pending_tasks=Count('task_instance_id', filter=Q(status__in=['TODO', 'IN_PROGRESS']))
        )
        
        # Goal progress
        goal_stats = Goal.objects.filter(user=self.user, status='active').aggregate(
            avg_progress=Avg('progress')
        )
        
        return {
            'tracker_count': trackers.count(),
            'total_tasks': task_stats['total_tasks'] or 0,
            'completed_tasks': task_stats['completed_tasks'] or 0,
            'pending_tasks': task_stats['pending_tasks'] or 0,
            'completion_rate': (task_stats['completed_tasks'] / task_stats['total_tasks'] * 100) if task_stats['total_tasks'] else 0,
            'avg_goal_progress': goal_stats['avg_progress'] or 0
        }
    
    def get_behavior_insights(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
        """Get NLP and behavioral analysis insights."""
        if not self.tracker_id:
            return {}
            
        return {
            'sentiment': analytics.analyze_notes_sentiment(self.tracker_id, start_date, end_date),
            'keywords': analytics.extract_keywords_from_notes(self.tracker_id),
            'mood_trends': analytics.compute_mood_trends(self.tracker_id)
        }
    
    def get_time_series_analysis(self, metric: str = 'completion_rate', forecast_days: int = 7) -> Dict:
        """Get time series analysis with forecasting."""
        if not self.tracker_id:
            return {}
            
        return analytics.analyze_time_series(self.tracker_id, metric, forecast_days)
    
    def get_correlations(self, metrics: Optional[List[str]] = None) -> Dict:
        """Compute correlations between metrics."""
        if not self.tracker_id:
            return {}
            
        return analytics.compute_correlations(self.tracker_id, metrics)
    
    def generate_charts(self) -> Dict:
        """Generate all visualization charts."""
        if not self.tracker_id:
            return {}
            
        return {
            'completion_chart': analytics.generate_completion_chart(self.tracker_id),
            'category_pie': analytics.generate_category_pie_chart(self.tracker_id),
            'heatmap': analytics.generate_completion_heatmap(self.tracker_id),
            'streak_timeline': analytics.generate_streak_timeline(self.tracker_id)
        }
    
    def get_quick_summary(self) -> Dict:
        """Get quick summary stats for dashboard/list views."""
        if not self.tracker_id:
            return {}
            
        return analytics.compute_tracker_stats(self.tracker_id)
    
    def get_detailed_metrics(self, window_days: int = 7) -> Dict:
        """Get all metrics for analytics dashboard."""
        if not self.tracker_id:
            return {}
            
        return {
            'completion': analytics.compute_completion_rate(self.tracker_id),
            'streaks': analytics.detect_streaks(self.tracker_id),
            'consistency': analytics.compute_consistency_score(self.tracker_id, window_days),
            'balance': analytics.compute_balance_score(self.tracker_id),
            'effort': analytics.compute_effort_index(self.tracker_id),
            'trends': analytics.analyze_trends(self.tracker_id, window=window_days)
        }
    
    def get_tracker_comparison(self) -> List[Dict]:
        """
        Compare all user's trackers by key metrics.
        
        Returns list of tracker comparisons with completion rates, streaks, trends.
        """
        if not self.user:
            return []
        
        trackers = TrackerDefinition.objects.filter(user=self.user, status='active')
        
        comparison = []
        for tracker in trackers:
            try:
                stats = analytics.compute_tracker_stats(tracker.tracker_id)
                trends = analytics.analyze_trends(tracker.tracker_id, window=7)
                
                comparison.append({
                    'tracker_id': tracker.tracker_id,
                    'name': tracker.name,
                    'time_period': tracker.time_period,
                    'completion_rate': stats.get('completion_rate', 0),
                    'current_streak': stats.get('current_streak', 0),
                    'trend_direction': trends.get('trend_direction', 'stable'),
                    'improving': trends.get('improving_periods', 0) > trends.get('total_periods', 1) / 2
                })
            except Exception:
                comparison.append({
                    'tracker_id': tracker.tracker_id,
                    'name': tracker.name,
                    'time_period': tracker.time_period,
                    'completion_rate': 0,
                    'current_streak': 0,
                    'trend_direction': 'stable',
                    'improving': False
                })
        
        return comparison
    
    def get_forecast(self, days: int = 7) -> Dict:
        """
        Get completion forecast for the user's trackers.
        
        Uses time series analysis for prediction.
        """
        if not self.user:
            return {}
        
        trackers = TrackerDefinition.objects.filter(user=self.user, status='active')[:5]
        
        forecasts = []
        for tracker in trackers:
            try:
                ts_analysis = analytics.analyze_time_series(tracker.tracker_id, 'completion_rate', days)
                forecasts.append({
                    'tracker_id': tracker.tracker_id,
                    'tracker_name': tracker.name,
                    'forecast': ts_analysis.get('forecast', {}).get('forecast', []),
                    'trend': ts_analysis.get('trend', {}).get('direction', 'stable')
                })
            except Exception:
                continue
        
        return {
            'forecasts': forecasts,
            'forecast_days': days
        }
