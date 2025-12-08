"""
Enhanced Forecast Service - Pure Python Implementation

Uses ONLY lightweight standard library features:
- math: Core numerical operations
- statistics: Basic stat helper
- datetime: Time handling

NO heavy dependencies: pandas ❌, numpy ❌, scipy ❌, sklearn ❌
Optimized for Vercel/Serverless deployment.
"""
import math
import statistics
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from core.models import TaskInstance
from core.helpers.metric_helpers import (
    calculate_trend, 
    calculate_ema, 
    detect_streaks
)

logger = logging.getLogger(__name__)

# =========================================================================
# FORECAST MATH UTILS (Pure Python)
# =========================================================================

def _linear_regression_python(y: List[float]) -> Dict:
    """Pure Python linear regression (y vs index)"""
    n = len(y)
    if n < 2:
        return {'slope': 0, 'intercept': 0, 'r2': 0, 'std_err': 0}
        
    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    # Sums for slope
    numer = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denom = sum((xi - mean_x) ** 2 for xi in x)
    
    if denom == 0:
        return {'slope': 0, 'intercept': mean_y, 'r2': 0, 'std_err': 0}
        
    slope = numer / denom
    intercept = mean_y - slope * mean_x
    
    # R2 and Std Err calculation
    y_pred = [slope * xi + intercept for xi in x]
    ss_res = sum((yi - ypi) ** 2 for yi, ypi in zip(y, y_pred))
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    std_err = math.sqrt(ss_res / (n - 2)) if n > 2 else 0
    
    return {
        'slope': slope,
        'intercept': intercept,
        'r2': r2,
        'std_err': std_err
    }

def _double_exponential_smoothing_python(series: List[float], periods: int = 7) -> List[float]:
    """Double Exponential Smoothing (Holt's method)"""
    if not series:
        return []
    if len(series) < 2:
        return [series[-1]] * periods
        
    alpha = 0.3
    beta = 0.1
    
    level = series[0]
    trend = series[1] - series[0]
    
    # Fit history
    for i in range(1, len(series)):
        val = series[i]
        last_level = level
        level = alpha * val + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend
        
    # Forecast
    forecast = []
    for p in range(1, periods + 1):
        prediction = level + p * trend
        forecast.append(max(0, min(100, prediction)))
        
    return forecast

# =========================================================================
# FORECAST SERVICE CLASS
# =========================================================================

class ForecastService:
    """
    Lightweight forecast service optimized for serverless environments.
    Strict separation from heavy data science libraries.
    """
    
    def __init__(self, user):
        self.user = user
        pass

    def forecast_completion_rate(
        self, 
        days_ahead=7, 
        history_days=30, 
        tracker_id=None,
        method='auto',  # Ignored in lightweight version, auto-selects best available
        include_behavioral_adjustments=True
    ):
        """Generates a forecast of future completion rates"""
        
        # 1. Fetch Data
        daily_rates, dates = self._fetch_history(history_days, tracker_id)
        
        if len(daily_rates) < 5:
             return {
                'success': False,
                'error': 'Insufficient data (need at least 5 days)',
                'days_analyzed': len(daily_rates)
            }
            
        # 2. Select & Run Model
        # Use simple EMA for short history, Double Exp Smoothing for longer history
        if len(daily_rates) >= 14:
            predictions = _double_exponential_smoothing_python(daily_rates, periods=days_ahead)
            model_name = 'double_exponential_smoothing'
        else:
            # Fallback to linear regression projection
            reg = _linear_regression_python(daily_rates)
            last_idx = len(daily_rates)
            predictions = [
                max(0, min(100, reg['slope'] * (last_idx + i) + reg['intercept']))
                for i in range(days_ahead)
            ]
            model_name = 'linear_regression'
            
        # 3. Calculate Confidence Intervals
        # Simplified: use standard deviation of recent history
        if len(daily_rates) > 1:
            std_dev = statistics.stdev(daily_rates)
        else:
            std_dev = 5.0 # Default fallback
            
        upper_bound = [min(100, p + 1.28 * std_dev) for p in predictions] # ~80% confidence
        lower_bound = [max(0, p - 1.28 * std_dev) for p in predictions]
        
        # 4. Generate Output Dates
        start_forecast_date = datetime.now().date() + timedelta(days=1)
        forecast_dates = [
            (start_forecast_date + timedelta(days=i)).isoformat() 
            for i in range(days_ahead)
        ]
        
        forecast_labels = [
            (start_forecast_date + timedelta(days=i)).strftime('%b %d')
            for i in range(days_ahead)
        ]

        # 5. Determine Trend
        trend_data = calculate_trend(daily_rates)
        trend_dir = 'stable'
        if trend_data['direction'] > 0: trend_dir = 'increasing'
        elif trend_data['direction'] < 0: trend_dir = 'decreasing'

        result = {
            'success': True,
            'predictions': [round(p, 1) for p in predictions],
            'upper_bound': [round(u, 1) for u in upper_bound],
            'lower_bound': [round(l, 1) for l in lower_bound],
            'dates': forecast_dates,
            'labels': forecast_labels,
            'trend': trend_dir,
            'current_rate': round(daily_rates[-1], 1),
            'confidence': 0.85 if len(daily_rates) > 14 else 0.60,
            'model': model_name
        }
        
        # 6. Optional Behavioral Adjustments (Placeholder for full implementation)
        if include_behavioral_adjustments and tracker_id:
            # Simplistic weekend adjustment if needed
            pass
            
        return result

    def _fetch_history(self, days, tracker_id):
        """Fetches daily task completion stats efficiently"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)
        
        # Determine scope
        filter_kwargs = {
            'tracker_instance__tracker__user': self.user,
            'tracker_instance__tracking_date__gte': start_date,
            'tracker_instance__tracking_date__lte': end_date,
            'deleted_at__isnull': True
        }
        
        if tracker_id:
            filter_kwargs['tracker_instance__tracker__tracker_id'] = tracker_id
            
        tasks = TaskInstance.objects.filter(**filter_kwargs).select_related('tracker_instance')
        
        # Aggregate in Python to avoid complex DB queries/deps
        # Map: date_str -> {total, completed}
        daily_map = {}
        
        # Pre-fill dates
        curr = start_date
        while curr <= end_date:
            daily_map[curr.isoformat()] = {'total': 0, 'completed': 0}
            curr += timedelta(days=1)
            
        for t in tasks:
            d_str = t.tracker_instance.tracking_date.isoformat()
            if d_str in daily_map:
                daily_map[d_str]['total'] += 1
                if t.status == 'DONE':
                    daily_map[d_str]['completed'] += 1
                    
        # Convert to list
        rates = []
        dates = []
        
        sorted_dates = sorted(daily_map.keys())
        for d in sorted_dates:
            data = daily_map[d]
            if data['total'] > 0:
                rate = (data['completed'] / data['total']) * 100.0
                rates.append(rate)
                dates.append(d)
                
        return rates, dates

    def get_forecast_summary(self, days_ahead=7, tracker_id=None):
        """Get text summary of forecast"""
        forecast = self.forecast_completion_rate(days_ahead, tracker_id=tracker_id)
        
        if not forecast.get('success'):
            return {
                'message': "Not enough data for a forecast yet.",
                'recommendation': "Keep tracking tasks daily to unlock insights.",
                'predicted_change': 0
            }
            
        start_val = forecast['current_rate']
        end_val = forecast['predictions'][-1]
        change = end_val - start_val
        trend = forecast['trend']
        
        msg = f"Your performance is trending {trend}."
        if trend == 'increasing':
            rec = "Great momentum! Keep pushing to maintain this growth."
        elif trend == 'decreasing':
            rec = "Consider simplifying your goals to regain consistency."
        else:
            rec = "You are consistent. Try increasing difficulty slightly if you're bored."
            
        return {
            'message': msg,
            'recommendation': rec,
            'predicted_change': round(change, 1),
            'trend': trend,
            'confidence': forecast['confidence']
        }
