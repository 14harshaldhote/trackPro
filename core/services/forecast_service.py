"""
Enhanced Forecast Service - Pure NumPy/Pandas Implementation

Uses ONLY lightweight, serverless-safe libraries:
- numpy: Core numerical operations
- pandas: Data manipulation
- polars: Fast dataframe operations (optional, Rust-based)

NO heavy dependencies: scipy ❌, scikit-learn ❌, matplotlib ❌, statsmodels ❌
All forecasting uses pure mathematical implementations.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from django.utils import timezone
from typing import Dict, List, Optional, Tuple
import logging

from core.models import TaskInstance, TrackerInstance

logger = logging.getLogger(__name__)

# Optional Polars for faster data processing
try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False


def _linregress_numpy(x: np.ndarray, y: np.ndarray) -> Dict:
    """
    Pure numpy implementation of linear regression.
    
    Returns:
        Dict with slope, intercept, r_value, r_squared, std_err
    """
    n = len(x)
    if n < 2:
        return {'slope': 0, 'intercept': 0, 'r_value': 0, 'r_squared': 0, 'std_err': 0}
    
    # Calculate means
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    # Calculate slope and intercept
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sum((x - x_mean) ** 2)
    
    if denominator == 0:
        return {'slope': 0, 'intercept': y_mean, 'r_value': 0, 'r_squared': 0, 'std_err': 0}
    
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    
    # Calculate R-value (correlation coefficient)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)
    
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    r_value = np.sqrt(abs(r_squared)) * (1 if slope >= 0 else -1)
    
    # Standard error of the estimate
    if n > 2:
        std_err = np.sqrt(ss_res / (n - 2)) / np.sqrt(denominator) if denominator > 0 else 0
    else:
        std_err = 0
    
    return {
        'slope': float(slope),
        'intercept': float(intercept),
        'r_value': float(r_value),
        'r_squared': float(r_squared),
        'std_err': float(std_err)
    }


def _simple_exponential_smoothing(y: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    """
    Simple Exponential Smoothing (pure numpy)
    
    Args:
        y: Time series values
        alpha: Smoothing parameter (0-1)
    
    Returns:
        Smoothed values
    """
    if len(y) == 0:
        return np.array([])
    
    smoothed = np.zeros(len(y))
    smoothed[0] = y[0]
    
    for i in range(1, len(y)):
        smoothed[i] = alpha * y[i] + (1 - alpha) * smoothed[i-1]
    
    return smoothed


def _double_exponential_smoothing(y: np.ndarray, alpha: float = 0.3, beta: float = 0.1, periods: int = 7) -> Dict:
    """
    Double Exponential Smoothing (Holt's method) - Pure NumPy
    Handles trends better than simple exponential smoothing
    
    Args:
        y: Time series values
        alpha: Level smoothing parameter
        beta: Trend smoothing parameter
        periods: Number of periods to forecast
    
    Returns:
        Dict with forecast, level, and trend
    """
    if len(y) < 2:
        return {
            'forecast': [y[0]] * periods if len(y) > 0 else [0] * periods,
            'level': y[0] if len(y) > 0 else 0,
            'trend': 0
        }
    
    n = len(y)
    level = np.zeros(n)
    trend = np.zeros(n)
    
    # Initialize
    level[0] = y[0]
    trend[0] = y[1] - y[0] if n > 1 else 0
    
    # Smooth
    for i in range(1, n):
        level[i] = alpha * y[i] + (1 - alpha) * (level[i-1] + trend[i-1])
        trend[i] = beta * (level[i] - level[i-1]) + (1 - beta) * trend[i-1]
    
    # Forecast
    forecast = []
    for p in range(1, periods + 1):
        forecast.append(level[-1] + p * trend[-1])
    
    return {
        'forecast': forecast,
        'level': float(level[-1]),
        'trend': float(trend[-1])
    }


def _triple_exponential_smoothing(y: np.ndarray, season_length: int = 7, 
                                    alpha: float = 0.3, beta: float = 0.1, 
                                    gamma: float = 0.1, periods: int = 7) -> Dict:
    """
    Triple Exponential Smoothing (Holt-Winters) - Pure NumPy
    Handles trends AND seasonality
    
    Args:
        y: Time series values
        season_length: Length of seasonal cycle (7 for weekly)
        alpha: Level smoothing
        beta: Trend smoothing
        gamma: Seasonality smoothing
        periods: Periods to forecast
    
    Returns:
        Dict with forecast and components
    """
    n = len(y)
    
    # Need at least 2 full seasonal cycles
    if n < 2 * season_length:
        # Fallback to double exponential smoothing
        return _double_exponential_smoothing(y, alpha, beta, periods)
    
    # Initialize components
    level = np.zeros(n)
    trend = np.zeros(n)
    seasonal = np.zeros(n)
    
    # Initial seasonal component (simple average of first season)
    seasonal_init = np.zeros(season_length)
    for i in range(season_length):
        seasonal_init[i] = np.mean(y[i::season_length][:min(4, len(y[i::season_length]))])
    
    seasonal_avg = np.mean(seasonal_init)
    if seasonal_avg != 0:
        seasonal_init = seasonal_init / seasonal_avg
    else:
        seasonal_init = np.ones(season_length)
    
    # Initialize level and trend
    level[0] = y[0] / seasonal_init[0]
    trend[0] = (y[season_length] - y[0]) / season_length if n > season_length else 0
    seasonal[:season_length] = seasonal_init
    
    # Smooth through the series
    for i in range(n):
        season_idx = i % season_length
        
        if i == 0:
            continue
        
        # Level
        level[i] = alpha * (y[i] / seasonal[season_idx]) + (1 - alpha) * (level[i-1] + trend[i-1])
        
        # Trend
        trend[i] = beta * (level[i] - level[i-1]) + (1 - beta) * trend[i-1]
        
        # Seasonal
        if i >= season_length:
            seasonal[i] = gamma * (y[i] / level[i]) + (1 - gamma) * seasonal[i - season_length]
    
    # Forecast
    forecast = []
    for p in range(1, periods + 1):
        season_idx = (n - 1 + p) % season_length
        forecast_value = (level[-1] + p * trend[-1]) * seasonal[season_idx]
        forecast.append(forecast_value)
    
    return {
        'forecast': forecast,
        'level': float(level[-1]),
        'trend': float(trend[-1]),
        'seasonal': seasonal[-season_length:].tolist()
    }


class ForecastService:
    """
    Advanced forecast service using pure NumPy/Pandas
    
    Methods available (all serverless-safe):
    1. Linear Regression (baseline)
    2. Simple Exponential Smoothing (fast, no trend)
    3. Double Exponential Smoothing (captures trends)
    4. Triple Exponential Smoothing (captures trends + seasonality)
    5. Behavioral adjustments (integrates insights)
    """
    
    def __init__(self, user):
        self.user = user
    
    def forecast_completion_rate(
        self, 
        days_ahead=7, 
        history_days=30, 
        tracker_id=None,
        method='auto',
        include_behavioral_adjustments=True
    ):
        """
        Advanced forecast using multiple methods
        
        Args:
            days_ahead: Number of days to forecast
            history_days: Historical data window
            tracker_id: Optional tracker UUID
            method: 'auto', 'linear', 'ses', 'des', 'tes'
            include_behavioral_adjustments: Apply behavioral corrections
        
        Returns:
            Enhanced forecast with behavioral context
        """
        # Step 1: Get baseline forecast
        baseline_forecast = self._forecast_with_method(
            days_ahead,
            history_days,
            tracker_id,
            method
        )
        
        if not baseline_forecast['success']:
            return baseline_forecast
        
        # Step 2: Apply behavioral adjustments
        if include_behavioral_adjustments and tracker_id:
            behavioral_adjustments = self._get_behavioral_adjustments(
                tracker_id, 
                baseline_forecast
            )
            
            adjusted_forecast = self._apply_behavioral_corrections(
                baseline_forecast,
                behavioral_adjustments
            )
            
            return {
                **adjusted_forecast,
                'behavioral_factors': behavioral_adjustments,
                'baseline_model': baseline_forecast.get('model', 'unknown')
            }
        
        return baseline_forecast
    
    def _forecast_with_method(
        self,
        days_ahead: int,
        history_days: int,
        tracker_id: Optional[str],
        method: str
    ) -> Dict:
        """
        Generate forecast using specified method
        """
        # Fetch data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=history_days - 1)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user=self.user,
            tracker_instance__tracking_date__gte=start_date,
            tracker_instance__tracking_date__lte=end_date,
            deleted_at__isnull=True
        )
        
        if tracker_id:
            tasks = tasks.filter(tracker_instance__tracker__tracker_id=tracker_id)
        
        # Build daily completion rates
        daily_data = []
        current_date = start_date
        
        while current_date <= end_date:
            day_tasks = tasks.filter(tracker_instance__tracking_date=current_date)
            total = day_tasks.count()
            completed = day_tasks.filter(status='DONE').count()
            
            if total > 0:
                rate = (completed / total * 100)
                daily_data.append({
                    'date': current_date.isoformat(),
                    'rate': rate,
                    'total': total,
                    'completed': completed
                })
            
            current_date += timedelta(days=1)
        
        if len(daily_data) < 7:
            return {
                'success': False,
                'error': 'Insufficient data for forecasting (need at least 7 days)',
                'days_analyzed': len(daily_data)
            }
        
        # Convert to numpy
        rates = np.array([d['rate'] for d in daily_data])
        
        # Auto-select method
        if method == 'auto':
            if len(rates) >= 21:
                method = 'tes'  # Use triple exp smoothing for sufficient data
            elif len(rates) >= 14:
                method = 'des'  # Use double exp smoothing
            else:
                method = 'linear'
        
        # Generate forecast
        if method == 'tes':
            result = _triple_exponential_smoothing(rates, season_length=7, periods=days_ahead)
            forecast_values = result['forecast']
            model_name = 'triple_exponential_smoothing'
        elif method == 'des':
            result = _double_exponential_smoothing(rates, periods=days_ahead)
            forecast_values = result['forecast']
            model_name = 'double_exponential_smoothing'
        elif method == 'ses':
            smoothed = _simple_exponential_smoothing(rates)
            forecast_values = [smoothed[-1]] * days_ahead
            model_name = 'simple_exponential_smoothing'
        else:  # linear
            return self._linear_regression_forecast(rates, days_ahead, daily_data)
        
        # Calculate confidence intervals (using residual std)
        fitted = _simple_exponential_smoothing(rates)
        residuals = rates - fitted
        std_err = float(np.std(residuals))
        
        predictions = np.clip(forecast_values, 0, 100)
        upper = np.clip(predictions + 1.96 * std_err, 0, 100)
        lower = np.clip(predictions - 1.96 * std_err, 0, 100)
        
        # Calculate metrics
        variance = float(np.var(rates))
        data_quality = 1.0 - min(variance / 1000, 0.5)
        
        # Determine trend
        recent_trend = np.mean(rates[-3:]) - np.mean(rates[-7:-4]) if len(rates) >= 7 else rates[-1] - rates[0]
        if recent_trend > 2:
            trend = 'increasing'
        elif recent_trend < -2:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Generate dates
        forecast_dates = []
        forecast_labels = []
        forecast_weekdays = []
        current_forecast_date = end_date + timedelta(days=1)
        
        for _ in range(days_ahead):
            forecast_dates.append(current_forecast_date.isoformat())
            forecast_labels.append(current_forecast_date.strftime('%b %d'))
            forecast_weekdays.append(current_forecast_date.weekday())
            current_forecast_date += timedelta(days=1)
        
        return {
            'success': True,
            'predictions': [round(float(p), 1) for p in predictions],
            'upper_bound': [round(float(u), 1) for u in upper],
            'lower_bound': [round(float(l), 1) for l in lower],
            'confidence': round(data_quality, 2),
            'trend': trend,
            'days_analyzed': len(rates),
            'dates': forecast_dates,
            'labels': forecast_labels,
            'weekdays': forecast_weekdays,
            'current_rate': round(float(rates[-1]), 1),
            'variance': round(variance, 1),
            'data_quality': round(data_quality, 2),
            'model': model_name
        }
    
    def _linear_regression_forecast(self, y: np.ndarray, periods: int, daily_data: List[Dict]) -> Dict:
        """Linear regression baseline"""
        x = np.arange(len(y))
        reg_result = _linregress_numpy(x, y)
        
        slope = reg_result['slope']
        intercept = reg_result['intercept']
        std_err = reg_result['std_err']
        
        # Forecast
        future_x = np.arange(len(y), len(y) + periods)
        predictions = slope * future_x + intercept
        
        # Confidence intervals
        x_mean = np.mean(x)
        ss_x = np.sum((x - x_mean) ** 2)
        
        if ss_x > 0 and std_err > 0:
            stderr_forecast = std_err * np.sqrt(1 + 1/len(x) + (future_x - x_mean)**2 / ss_x)
        else:
            stderr_forecast = np.ones(periods) * max(np.std(y) * 0.1, 5)
        
        confidence_interval = 1.96 * stderr_forecast
        
        predictions_clipped = np.clip(predictions, 0, 100)
        upper = np.clip(predictions + confidence_interval, 0, 100)
        lower = np.clip(predictions - confidence_interval, 0, 100)
        
        # Determine trend
        if slope > 0.5:
            trend = 'increasing'
        elif slope < -0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Generate dates
        end_date = datetime.fromisoformat(daily_data[-1]['date']).date()
        forecast_dates = []
        forecast_labels = []
        forecast_weekdays = []
        current_date = end_date + timedelta(days=1)
        
        for _ in range(periods):
            forecast_dates.append(current_date.isoformat())
            forecast_labels.append(current_date.strftime('%b %d'))
            forecast_weekdays.append(current_date.weekday())
            current_date += timedelta(days=1)
        
        return {
            'success': True,
            'predictions': [round(float(p), 1) for p in predictions_clipped],
            'upper_bound': [round(float(u), 1) for u in upper],
            'lower_bound': [round(float(l), 1) for l in lower],
            'confidence': round(reg_result['r_squared'], 2),
            'trend': trend,
            'days_analyzed': len(y),
            'dates': forecast_dates,
            'labels': forecast_labels,
            'weekdays': forecast_weekdays,
            'current_rate': round(float(y[-1]), 1),
            'variance': round(float(np.var(y)), 1),
            'data_quality': round(reg_result['r_squared'], 2),
            'model': 'linear_regression',
            'slope': round(slope, 3)
        }
    
    def _get_behavioral_adjustments(self, tracker_id: str, baseline_forecast: Dict) -> Dict:
        """Identify behavioral patterns for forecast adjustment"""
        adjustments = {
            'weekend_factor': 0,
            'mood_factor': 0,
            'streak_boost': 0,
            'consistency_penalty': 0,
            'recovery_needed': False,
            'reasons': []
        }
        
        try:
            from core.behavioral.insights_engine import InsightsEngine, InsightType
            
            engine = InsightsEngine(tracker_id)
            insights = engine.generate_insights()
            
            # Weekend pattern
            weekend_insight = next(
                (i for i in insights if i.insight_type == InsightType.WEEKEND_DIP), 
                None
            )
            
            if weekend_insight:
                weekday_avg = weekend_insight.evidence.get('weekday_average', 0)
                weekend_avg = weekend_insight.evidence.get('weekend_average', 0)
                
                if weekday_avg > 0:
                    adjustments['weekend_factor'] = (weekend_avg - weekday_avg) / weekday_avg
                    adjustments['reasons'].append(
                        f"Weekend completion typically {abs(adjustments['weekend_factor']*100):.0f}% lower"
                    )
            
            # Low consistency
            consistency_insight = next(
                (i for i in insights if i.insight_type == InsightType.LOW_CONSISTENCY),
                None
            )
            
            if consistency_insight:
                consistency_score = consistency_insight.evidence.get('consistency_score', 100)
                if consistency_score < 60:
                    adjustments['consistency_penalty'] = (60 - consistency_score) / 100
                    adjustments['reasons'].append(
                        f"Low consistency ({consistency_score:.0f}%) increases uncertainty"
                    )
            
            # Streak boost
            streak_insight = next(
                (i for i in insights if i.insight_type == InsightType.STREAK_RISK),
                None
            )
            
            if streak_insight:
                adjustments['streak_boost'] = 0.1
                adjustments['reasons'].append("Active streak provides motivation boost")
            
            # Recovery needed
            recovery_insight = next(
                (i for i in insights if i.insight_type == InsightType.HIGH_EFFORT_RECOVERY),
                None
            )
            
            if recovery_insight:
                adjustments['recovery_needed'] = True
                adjustments['reasons'].append("Recent high effort may lead to recovery dip")
                    
        except Exception as e:
            logger.warning(f"Behavioral insights unavailable: {e}")
            adjustments['reasons'].append("Behavioral insights module not available")
        
        return adjustments
    
    def _apply_behavioral_corrections(self, baseline: Dict, adjustments: Dict) -> Dict:
        """Apply behavioral corrections to forecast"""
        corrected_predictions = []
        corrected_upper = []
        corrected_lower = []
        
        predictions = baseline['predictions']
        upper = baseline['upper_bound']
        lower = baseline['lower_bound']
        weekdays = baseline['weekdays']
        
        for i, (pred, up, low, weekday) in enumerate(zip(predictions, upper, lower, weekdays)):
            corrected_pred = pred
            corrected_up = up
            corrected_low = low
            
            # Weekend adjustment
            if weekday >= 5 and adjustments['weekend_factor'] != 0:
                weekend_adj = corrected_pred * adjustments['weekend_factor']
                corrected_pred += weekend_adj
                corrected_up += weekend_adj
                corrected_low += weekend_adj
            
            # Streak boost
            if adjustments['streak_boost'] > 0:
                boost = corrected_pred * adjustments['streak_boost']
                corrected_pred += boost
                corrected_up += boost
                corrected_low += boost
            
            # Recovery dip
            if adjustments['recovery_needed'] and i < 2:
                recovery_dip = corrected_pred * 0.15
                corrected_pred -= recovery_dip
                corrected_up -= recovery_dip * 0.5
                corrected_low -= recovery_dip
            
            # Clip to valid range
            corrected_pred = float(np.clip(corrected_pred, 0, 100))
            corrected_up = float(np.clip(corrected_up, 0, 100))
            corrected_low = float(np.clip(corrected_low, 0, 100))
            
            corrected_predictions.append(round(corrected_pred, 1))
            corrected_upper.append(round(corrected_up, 1))
            corrected_lower.append(round(corrected_low, 1))
        
        # Adjust confidence
        adjusted_confidence = baseline['confidence'] * (1 - adjustments['consistency_penalty'])
        
        return {
            **baseline,
            'predictions': corrected_predictions,
            'upper_bound': corrected_upper,
            'lower_bound': corrected_lower,
            'confidence': round(adjusted_confidence, 2),
            'adjustments_applied': adjustments['reasons']
        }
    
    def get_forecast_summary(self, days_ahead=7, tracker_id=None):
        """Enhanced summary with behavioral context"""
        forecast = self.forecast_completion_rate(
            days_ahead=days_ahead,
            tracker_id=tracker_id,
            include_behavioral_adjustments=True
        )
        
        if not forecast['success']:
            return {
                'message': 'Not enough data to generate a forecast',
                'recommendation': 'Complete more tasks to see predictions',
                'predicted_change': 0
            }
        
        current = forecast['current_rate']
        future = forecast['predictions'][-1]
        change = future - current
        trend = forecast['trend']
        confidence = forecast['confidence']
        
        confidence_text = self._get_confidence_text(confidence)
        base_message = f"Your completion rate is trending {trend}"
        
        if 'behavioral_factors' in forecast:
            behavioral_notes = forecast['behavioral_factors'].get('reasons', [])
            if behavioral_notes:
                base_message += f". {behavioral_notes[0]}"
        
        prediction_text = f"Expected to {('reach' if change >= 0 else 'drop to')} {future}% in {days_ahead} days"
        message = f"{base_message} ({confidence_text}). {prediction_text}."
        
        recommendation = self._generate_recommendation(forecast, change)
        
        return {
            'message': message,
            'recommendation': recommendation,
            'predicted_change': round(change, 1),
            'confidence': confidence,
            'trend': trend,
            'method': forecast.get('model', 'unknown'),
            'behavioral_insights': forecast.get('behavioral_factors', {}).get('reasons', [])
        }
    
    def _get_confidence_text(self, confidence: float) -> str:
        """Convert confidence score to human text"""
        if confidence >= 0.75:
            return 'high confidence'
        elif confidence >= 0.5:
            return 'moderate confidence'
        else:
            return 'low confidence due to irregular patterns'
    
    def _generate_recommendation(self, forecast: Dict, change: float) -> str:
        """Generate context-aware recommendation"""
        trend = forecast['trend']
        behavioral_factors = forecast.get('behavioral_factors', {})
        
        if behavioral_factors.get('recovery_needed'):
            return "Consider a recovery day soon to maintain long-term performance."
        
        if behavioral_factors.get('weekend_factor', 0) < -0.2:
            return "Your weekends show lower completion - consider lighter weekend goals."
        
        if behavioral_factors.get('consistency_penalty', 0) > 0.3:
            return "Focus on building a consistent daily routine to improve predictions."
        
        if trend == 'increasing':
            return "Keep up the excellent momentum! Your habits are strengthening."
        elif trend == 'decreasing':
            if change < -10:
                return "Consider reviewing your task load or priorities to reverse the trend."
            else:
                return "Monitor your patterns closely and consider slight adjustments."
        else:
            return "You're maintaining a steady pace - consistency is key to habit formation."
