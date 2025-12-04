"""
Analytics Service

Wraps analytics functions with cleaner interface and caching.
Provides high-level methods for common analytics operations.
"""
from datetime import date
from typing import Dict, List, Optional

from core import analytics
from core.helpers.cache_helpers import cache_result, CACHE_TIMEOUTS


class AnalyticsService:
    """
    Service for analytics operations.
    
    Wraps lower-level analytics functions with business logic and caching.
    """
    
    def __init__(self, tracker_id: str):
        """
        Initialize analytics service for a tracker.
        
        Args:
            tracker_id: Tracker ID to analyze
        """
        self.tracker_id = tracker_id
    
    def get_tracker_dashboard_stats(self) -> Dict:
        """
        Get comprehensive statistics for tracker detail page.
        
        Combines multiple analytics calls into single dashboard dataset.
        
        Returns:
            {
                'completion': {...},
                'streaks': {...},
                'consistency': {...},
                'balance': {...},
                'effort': {...}
            }
        """
        return {
            'completion': analytics.compute_completion_rate(self.tracker_id),
            'streaks': analytics.detect_streaks(self.tracker_id),
            'consistency': analytics.compute_consistency_score(self.tracker_id),
            'balance': analytics.compute_balance_score(self.tracker_id),
            'effort': analytics.compute_effort_index(self.tracker_id)
        }
    
    def get_behavior_insights(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
        """
        Get NLP and behavioral analysis insights.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            {
                'sentiment': {...},
                'keywords': [...],
                'mood_trends': {...}
            }
        """
        return {
            'sentiment': analytics.analyze_notes_sentiment(self.tracker_id, start_date, end_date),
            'keywords': analytics.extract_keywords_from_notes(self.tracker_id),
            'mood_trends': analytics.compute_mood_trends(self.tracker_id)
        }
    
    def get_time_series_analysis(self, metric: str = 'completion_rate', forecast_days: int = 7) -> Dict:
        """
        Get time series analysis with forecasting.
        
        Args:
            metric: Metric to analyze ('completion_rate', 'mood', 'effort')
            forecast_days: Days to forecast ahead
            
        Returns:
            Time series analysis dict with trend, forecast, change points, seasonality
        """
        return analytics.analyze_time_series(self.tracker_id, metric, forecast_days)
    
    def get_correlations(self, metrics: Optional[List[str]] = None) -> Dict:
        """
        Compute correlations between metrics.
        
        Args:
            metrics: List of metrics to correlate (default: completion_rate, mood, effort)
            
        Returns:
            Correlation matrix with p-values and significance
        """
        return analytics.compute_correlations(self.tracker_id, metrics)
    
    def generate_charts(self) -> Dict:
        """
        Generate all visualization charts.
        
        Returns:
            {
                'completion_chart': base64_image,
                'category_pie': base64_image,
                'heatmap': base64_image,
                'streak_timeline': base64_image
            }
        """
        return {
            'completion_chart': analytics.generate_completion_chart(self.tracker_id),
            'category_pie': analytics.generate_category_pie_chart(self.tracker_id),
            'heatmap': analytics.generate_completion_heatmap(self.tracker_id),
            'streak_timeline': analytics.generate_streak_timeline(self.tracker_id)
        }
    
    def get_quick_summary(self) -> Dict:
        """
        Get quick summary stats for dashboard/list views.
        
        Returns:
            {
                'total_tasks': int,
                'completed_tasks': int,
                'completion_rate': float,
                'current_streak': int
            }
        """
        return analytics.compute_tracker_stats(self.tracker_id)
    
    def get_detailed_metrics(self, window_days: int = 7) -> Dict:
        """
        Get all metrics for analytics dashboard.
        
        Args:
            window_days: Window for rolling calculations
            
        Returns:
            Complete set of metrics
        """
        return {
            'completion': analytics.compute_completion_rate(self.tracker_id),
            'streaks': analytics.detect_streaks(self.tracker_id),
            'consistency': analytics.compute_consistency_score(self.tracker_id, window_days),
            'balance': analytics.compute_balance_score(self.tracker_id),
            'effort': analytics.compute_effort_index(self.tracker_id),
            'trends': analytics.analyze_trends(self.tracker_id, window=window_days)
        }
