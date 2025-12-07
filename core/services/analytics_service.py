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

    def get_time_distribution(self) -> Dict[str, int]:
        """
        Get distribution of tasks by time of day.
        
        Returns:
            {'morning': count, 'afternoon': count, 'evening': count}
        """
        if not self.tracker_id:
            return {'morning': 0, 'afternoon': 0, 'evening': 0}
            
        result = TaskInstance.objects.filter(
            tracker_instance__tracker__tracker_id=self.tracker_id
        ).values('template__time_of_day').annotate(count=Count('task_instance_id'))
        
        dist = {item['template__time_of_day']: item['count'] for item in result}
        
        return {
            'morning': dist.get('morning', 0),
            'afternoon': dist.get('afternoon', 0),
            'evening': dist.get('evening', 0)
        }
    
    # =========================================================================
    # NEW: Chart Data Methods for Analytics Dashboard
    # =========================================================================
    
    def get_completion_trend_chart(self, days=30):
        """
        Get daily completion rate for Chart.js line chart
        
        Returns:
            {
                'labels': ['Dec 1', 'Dec 2', ...],
                'data': [85.5, 90.0, ...],
                'dates': ['2024-12-01', '2024-12-02', ...]
            }
        """
        from datetime import timedelta
        from django.utils import timezone
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        # Get all task instances in range for this user
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__tracking_date__gte=start_date,
            tracker_instance__tracking_date__lte=end_date,
            deleted_at__isnull=True
        )
        
        if self.tracker_id:
            tasks = tasks.filter(tracker_instance__tracker__tracker_id=self.tracker_id)
        
        # Group by date
        daily_stats = {}
        current_date = start_date
        
        while current_date <= end_date:
            day_tasks = tasks.filter(tracker_instance__tracking_date=current_date)
            total = day_tasks.count()
            completed = day_tasks.filter(status='DONE').count()
            
            rate = (completed / total * 100) if total > 0 else 0
            daily_stats[current_date] = round(rate, 1)
            
            current_date += timedelta(days=1)
        
        # Format for Chart.js
        labels = [d.strftime('%b %d') for d in sorted(daily_stats.keys())]
        data = [daily_stats[d] for d in sorted(daily_stats.keys())]
        dates = [d.isoformat() for d in sorted(daily_stats.keys())]
        
        return {
            'labels': labels,
            'data': data,
            'dates': dates
        }
    
    def get_category_chart(self, days=30):
        """
        Get category distribution for pie/doughnut chart
        
        Returns:
            {
                'labels': ['Work', 'Health', ...],
                'data': [35.5, 25.0, ...],  # percentages
                'counts': [150, 100, ...]   # actual counts
            }
        """
        from datetime import timedelta
        from django.utils import timezone
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__tracking_date__gte=start_date,
            tracker_instance__tracking_date__lte=end_date,
            status='DONE',
            deleted_at__isnull=True
        )
        
        # Group by category
        category_stats = tasks.values('template__category').annotate(
            count=Count('task_instance_id')
        ).order_by('-count')
        
        labels = []
        counts = []
        
        for stat in category_stats[:6]:  # Top 6 categories
            category = stat['template__category'] or 'Uncategorized'
            labels.append(category)
            counts.append(stat['count'])
        
        # Calculate percentages
        total = sum(counts)
        percentages = [round(c / total * 100, 1) if total > 0 else 0 for c in counts]
        
        return {
            'labels': labels,
            'data': percentages,
            'counts': counts
        }
    
    def get_time_of_day_chart(self, days=30):
        """
        Get time-of-day distribution for bar chart
        
        Returns:
            {
                'labels': ['Morning', 'Afternoon', 'Evening', 'Night'],
                'data': [45, 65, 40, 15]  # percentages
            }
        """
        from datetime import timedelta
        from django.utils import timezone
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__tracking_date__gte=start_date,
            tracker_instance__tracking_date__lte=end_date,
            status='DONE',
            deleted_at__isnull=True
        )
        
        # Group by time_of_day
        time_stats = tasks.values('template__time_of_day').annotate(
            count=Count('task_instance_id')
        )
        
        time_counts = {
            'morning': 0,
            'afternoon': 0,
            'evening': 0,
            'night': 0
        }
        
        for stat in time_stats:
            time_key = stat['template__time_of_day'] or 'morning'
            if time_key in time_counts:
                time_counts[time_key] += stat['count']
        
        total = sum(time_counts.values())
        percentages = [round(count / total * 100, 1) if total > 0 else 0 for count in time_counts.values()]
        
        return {
            'labels': ['Morning', 'Afternoon', 'Evening', 'Night'],
            'data': percentages
        }
    
    def get_year_heatmap_data(self):
        """
        Get full year heatmap data for contribution-style calendar
        
        Returns:
            [
                {'date': '2024-01-01', 'count': 8, 'level': 3},
                ...
            ]
        """
        from datetime import timedelta
        from django.utils import timezone
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)
        
        # Get all tasks in past year
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__tracking_date__gte=start_date,
            tracker_instance__tracking_date__lte=end_date,
            deleted_at__isnull=True
        )
        
        # Group by date
        daily_counts = tasks.values('tracker_instance__tracking_date').annotate(
            total=Count('task_instance_id'),
            completed=Count('task_instance_id', filter=Q(status='DONE'))
        )
        
        # Create lookup
        counts_by_date = {
            stat['tracker_instance__tracking_date']: stat['completed']
            for stat in daily_counts
        }
        
        # Generate all dates
        heatmap_data = []
        current_date = start_date
        
        while current_date <= end_date:
            completed = counts_by_date.get(current_date, 0)
            
            # Calculate level (0-4)
            if completed == 0:
                level = 0
            elif completed <= 3:
                level = 1
            elif completed <= 6:
                level = 2
            elif completed <= 10:
                level = 3
            else:
                level = 4
            
            heatmap_data.append({
                'date': current_date.isoformat(),
                'count': completed,
                'level': level
            })
            
            current_date += timedelta(days=1)
        
        return heatmap_data
    
    def generate_insights(self, days=30):
        """
        Generate insights from user data
        
        Returns:
            [
                {
                    'type': 'pattern',
                    'icon': '📅',
                    'title': 'Best Day',
                    'message': 'You are most productive on Tuesdays'
                },
                ...
            ]
        """
        from datetime import timedelta
        from django.utils import timezone
        
        insights = []
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__tracking_date__gte=start_date,
            tracker_instance__tracking_date__lte=end_date,
            deleted_at__isnull=True
        )
        
        # Best day analysis
        day_stats = {}
        for task in tasks:
            # Safely access date
            if not task.tracker_instance or not task.tracker_instance.tracking_date:
                continue
                
            day_index = task.tracker_instance.tracking_date.weekday()
            if day_index not in day_stats:
                day_stats[day_index] = {'total': 0, 'completed': 0}
            
            day_stats[day_index]['total'] += 1
            if task.status == 'DONE':
                day_stats[day_index]['completed'] += 1
        
        # Find best day
        best_day_index = None
        best_rate = 0
        
        for day_index, stats in day_stats.items():
            rate = stats['completed'] / stats['total'] if stats['total'] > 0 else 0
            if rate > best_rate:
                best_rate = rate
                best_day_index = day_index
        
        if best_day_index is not None and best_rate > 0:
            days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            insights.append({
                'type': 'pattern',
                'icon': '📅',
                'title': 'Best Day',
                'message': f"You're most productive on {days_of_week[best_day_index]}s"
            })
        
        # Consistency
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='DONE').count()
        consistency = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        if consistency >= 80:
            insights.append({
                'type': 'success',
                'icon': '⭐',
                'title': 'Highly Consistent',
                'message': f'{round(consistency)}% completion rate - Keep it up!'
            })
        
        return insights
    
    def get_analytics_data(self, days=30):
        """
        Get all analytics data for dashboard in one call
        
        Returns comprehensive analytics object for Chart.js
        """
        return {
            'completion_trend': self.get_completion_trend_chart(days),
            'category_distribution': self.get_category_chart(days),
            'time_of_day': self.get_time_of_day_chart(days),
            'heatmap': self.get_year_heatmap_data(),
            'insights': self.generate_insights(days),
            'summary': self.get_user_overview() if self.user else {}
        }
