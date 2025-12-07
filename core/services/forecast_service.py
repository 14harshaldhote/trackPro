"""
Enhanced Forecast Service with Behavioral Analytics Integration

Combines statistical forecasting with behavioral insights for more accurate predictions.
Integrates with the behavioral insights engine for context-aware forecasting.
"""
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from django.utils import timezone
from typing import Dict, List, Optional, Tuple

from core.models import TaskInstance
from core import analytics
from core.behavioral.insights_engine import InsightsEngine, InsightType


class ForecastService:
    """
    Advanced forecast service that combines:
    1. Statistical regression (trend analysis)
    2. Behavioral pattern recognition (weekend dips, mood impacts, etc.)
    3. Contextual adjustments (upcoming patterns, historical performance)
    """
    
    def __init__(self, user):
        self.user = user
    
    def forecast_completion_rate(
        self, 
        days_ahead=7, 
        history_days=30, 
        tracker_id=None,
        include_behavioral_adjustments=True
    ):
        """
        Advanced forecast using behavioral analytics
        
        Args:
            days_ahead: Number of days to forecast
            history_days: Historical data window
            tracker_id: Optional tracker UUID
            include_behavioral_adjustments: Apply behavioral corrections
        
        Returns:
            Enhanced forecast with behavioral context
        """
        # Step 1: Get baseline statistical forecast
        baseline_forecast = self._statistical_forecast(
            days_ahead, 
            history_days, 
            tracker_id
        )
        
        if not baseline_forecast['success']:
            return baseline_forecast
        
        # Step 2: Apply behavioral adjustments if enabled
        if include_behavioral_adjustments and tracker_id:
            behavioral_adjustments = self._get_behavioral_adjustments(
                tracker_id, 
                baseline_forecast
            )
            
            # Adjust predictions based on behavioral patterns
            adjusted_forecast = self._apply_behavioral_corrections(
                baseline_forecast,
                behavioral_adjustments
            )
            
            return {
                **adjusted_forecast,
                'behavioral_factors': behavioral_adjustments,
                'model': 'behavioral_regression',
                'baseline_model': 'linear_regression'
            }
        
        return {
            **baseline_forecast,
            'model': 'linear_regression'
        }
    
    def _statistical_forecast(
        self, 
        days_ahead: int, 
        history_days: int, 
        tracker_id: Optional[str]
    ) -> Dict:
        """
        Pure statistical forecast using linear regression
        (Original implementation - now baseline)
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=history_days - 1)
        
        tasks = TaskInstance.objects.filter(
            tracker__user=self.user,
            date__gte=start_date,
            date__lte=end_date,
            deleted_at__isnull=True
        )
        
        if tracker_id:
            tasks = tasks.filter(tracker__tracker__tracker_id=tracker_id)
        
        # Build daily completion rates
        daily_rates = []
        date_index = []
        current_date = start_date
        
        while current_date <= end_date:
            day_tasks = tasks.filter(date=current_date)
            total = day_tasks.count()
            completed = day_tasks.filter(status='completed').count()
            
            rate = (completed / total * 100) if total > 0 else None
            
            if rate is not None:
                daily_rates.append(rate)
                date_index.append(current_date)
            
            current_date += timedelta(days=1)
        
        # Check minimum data requirement
        if len(daily_rates) < 7:
            return {
                'success': False,
                'error': 'Insufficient data for forecasting (need at least 7 days)',
                'days_analyzed': len(daily_rates)
            }
        
        # Linear regression
        x = np.arange(len(daily_rates))
        y = np.array(daily_rates)
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Calculate variance-weighted confidence
        variance = np.var(y)
        data_quality = 1.0 - min(variance / 1000, 0.5)  # Lower variance = higher quality
        
        # Forecast future
        future_x = np.arange(len(daily_rates), len(daily_rates) + days_ahead)
        predictions = slope * future_x + intercept
        predictions = np.clip(predictions, 0, 100)
        
        # Enhanced confidence intervals considering variance
        base_stderr = std_err * np.sqrt(
            1 + 1/len(x) + (future_x - x.mean())**2 / ((x - x.mean())**2).sum()
        )
        
        # Adjust by data quality
        adjusted_stderr = base_stderr * (1 + (1 - data_quality))
        confidence_interval = 1.96 * adjusted_stderr
        
        upper_bound = np.clip(predictions + confidence_interval, 0, 100)
        lower_bound = np.clip(predictions - confidence_interval, 0, 100)
        
        # Determine trend
        if slope > 0.5:
            trend = 'increasing'
        elif slope < -0.5:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Generate dates and labels
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
            'predictions': [round(p, 1) for p in predictions.tolist()],
            'upper_bound': [round(u, 1) for u in upper_bound.tolist()],
            'lower_bound': [round(l, 1) for l in lower_bound.tolist()],
            'confidence': round(r_value ** 2 * data_quality, 2),  # Adjusted R²
            'trend': trend,
            'slope': round(slope, 3),
            'days_analyzed': len(daily_rates),
            'dates': forecast_dates,
            'labels': forecast_labels,
            'weekdays': forecast_weekdays,  # For behavioral adjustments
            'current_rate': round(y[-1], 1) if len(y) > 0 else 0,
            'variance': round(variance, 1),
            'data_quality': round(data_quality, 2)
        }
    
    def _get_behavioral_adjustments(
        self, 
        tracker_id: str, 
        baseline_forecast: Dict
    ) -> Dict:
        """
        Identify behavioral patterns that should adjust the forecast
        
        Returns dict with adjustment factors and reasons
        """
        adjustments = {
            'weekend_factor': 0,
            'mood_factor': 0,
            'streak_boost': 0,
            'consistency_penalty': 0,
            'recovery_needed': False,
            'reasons': []
        }
        
        try:
            # Get behavioral insights
            engine = InsightsEngine(tracker_id)
            insights = engine.generate_insights()
            
            # Get historical metrics
            completion_data = analytics.compute_completion_rate(tracker_id)
            consistency_data = analytics.compute_consistency_score(tracker_id)
            
            # Check for weekend pattern
            weekend_insight = next(
                (i for i in insights if i.insight_type == InsightType.WEEKEND_DIP), 
                None
            )
            
            if weekend_insight:
                # Apply weekend penalty to weekend days in forecast
                weekday_avg = weekend_insight.evidence.get('weekday_average', 0)
                weekend_avg = weekend_insight.evidence.get('weekend_average', 0)
                
                if weekday_avg > 0:
                    adjustments['weekend_factor'] = (weekend_avg - weekday_avg) / weekday_avg
                    adjustments['reasons'].append(
                        f"Weekend completion typically {abs(adjustments['weekend_factor']*100):.0f}% lower"
                    )
            
            # Check for low consistency
            consistency_insight = next(
                (i for i in insights if i.insight_type == InsightType.LOW_CONSISTENCY),
                None
            )
            
            if consistency_insight:
                consistency_score = consistency_insight.evidence.get('consistency_score', 100)
                if consistency_score < 60:
                    # Reduce confidence for inconsistent patterns
                    adjustments['consistency_penalty'] = (60 - consistency_score) / 100
                    adjustments['reasons'].append(
                        f"Low consistency ({consistency_score:.0f}%) increases uncertainty"
                    )
            
            # Check for streak at risk
            streak_insight = next(
                (i for i in insights if i.insight_type == InsightType.STREAK_RISK),
                None
            )
            
            if streak_insight:
                # Users work harder to maintain streaks (research-backed)
                adjustments['streak_boost'] = 0.1  # 10% boost when protecting streak
                adjustments['reasons'].append(
                    f"Active streak provides motivation boost"
                )
            
            # Check if recovery needed (high effort)
            recovery_insight = next(
                (i for i in insights if i.insight_type == InsightType.HIGH_EFFORT_RECOVERY),
                None
            )
            
            if recovery_insight:
                adjustments['recovery_needed'] = True
                adjustments['reasons'].append(
                    "Recent high effort may lead to recovery dip"
                )
            
            # Check trend insights for additional context
            improving_insight = next(
                (i for i in insights if i.insight_type == InsightType.IMPROVEMENT_TREND),
                None
            )
            
            if improving_insight:
                # Positive momentum
                adjustments['reasons'].append("Positive improvement momentum detected")
            
            declining_insight = next(
                (i for i in insights if i.insight_type == InsightType.DECLINING_TREND),
                None
            )
            
            if declining_insight:
                # Declining pattern already captured in slope, just note it
                adjustments['reasons'].append("Declining trend pattern identified")
            
        except Exception as e:
            # Behavioral adjustments are optional - don't fail forecast
            adjustments['reasons'].append(f"Unable to load behavioral context: {str(e)}")
        
        return adjustments
    
    def _apply_behavioral_corrections(
        self, 
        baseline: Dict, 
        adjustments: Dict
    ) -> Dict:
        """
        Apply behavioral corrections to baseline statistical forecast
        """
        corrected_predictions = []
        corrected_upper = []
        corrected_lower = []
        
        predictions = baseline['predictions']
        upper = baseline['upper_bound']
        lower = baseline['lower_bound']
        weekdays = baseline['weekdays']
        
        for i, (pred, up, low, weekday) in enumerate(zip(predictions, upper, lower, weekdays)):
            # Start with baseline
            corrected_pred = pred
            corrected_up = up
            corrected_low = low
            
            # Apply weekend adjustment (weekday: 0=Mon, 5=Sat, 6=Sun)
            if weekday >= 5 and adjustments['weekend_factor'] != 0:
                weekend_adj = corrected_pred * adjustments['weekend_factor']
                corrected_pred += weekend_adj
                corrected_up += weekend_adj
                corrected_low += weekend_adj
            
            # Apply streak boost (affects all days)
            if adjustments['streak_boost'] > 0:
                boost = corrected_pred * adjustments['streak_boost']
                corrected_pred += boost
                corrected_up += boost
                corrected_low += boost
            
            # Apply recovery dip (affects days 1-2 after high effort)
            if adjustments['recovery_needed'] and i < 2:
                recovery_dip = corrected_pred * 0.15  # 15% temporary dip
                corrected_pred -= recovery_dip
                corrected_up -= recovery_dip * 0.5
                corrected_low -= recovery_dip
            
            # Clip to valid range
            corrected_pred = np.clip(corrected_pred, 0, 100)
            corrected_up = np.clip(corrected_up, 0, 100)
            corrected_low = np.clip(corrected_low, 0, 100)
            
            corrected_predictions.append(round(corrected_pred, 1))
            corrected_upper.append(round(corrected_up, 1))
            corrected_lower.append(round(corrected_low, 1))
        
        # Adjust confidence based on consistency
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
        """
        Enhanced summary with behavioral context
        """
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
        
        # Generate context-aware message
        confidence_text = self._get_confidence_text(confidence)
        
        # Build message with behavioral context
        base_message = f"Your completion rate is trending {trend}"
        
        if 'behavioral_factors' in forecast:
            behavioral_notes = forecast['behavioral_factors'].get('reasons', [])
            if behavioral_notes:
                base_message += f". {behavioral_notes[0]}"
        
        prediction_text = f"Expected to {('reach' if change >= 0 else 'drop to')} {future}% in {days_ahead} days"
        
        message = f"{base_message} ({confidence_text}). {prediction_text}."
        
        # Generate smart recommendation
        recommendation = self._generate_recommendation(forecast, change)
        
        return {
            'message': message,
            'recommendation': recommendation,
            'predicted_change': round(change, 1),
            'confidence': confidence,
            'trend': trend,
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
        
        # Check for specific behavioral patterns
        if behavioral_factors.get('recovery_needed'):
            return "Consider a recovery day soon to maintain long-term performance."
        
        if behavioral_factors.get('weekend_factor', 0) < -0.2:
            return "Your weekends show lower completion - consider lighter weekend goals."
        
        if behavioral_factors.get('consistency_penalty', 0) > 0.3:
            return "Focus on building a consistent daily routine to improve predictions."
        
        # Default recommendations based on trend
        if trend == 'increasing':
            return "Keep up the excellent momentum! Your habits are strengthening."
        elif trend == 'declining':
            if change < -10:
                return "Consider reviewing your task load or priorities to reverse the trend."
            else:
                return "Monitor your patterns closely and consider slight adjustments."
        else:
            return "You're maintaining a steady pace - consistency is key to habit formation."
    
    def get_moving_average(self, days=7, history_days=30, tracker_id=None):
        """
        Calculate moving average (unchanged from original)
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=history_days - 1)
        
        tasks = TaskInstance.objects.filter(
            tracker__user=self.user,
            date__gte=start_date,
            date__lte=end_date,
            deleted_at__isnull=True
        )
        
        if tracker_id:
            tasks = tasks.filter(tracker__tracker__tracker_id=tracker_id)
        
        daily_rates = []
        labels = []
        current_date = start_date
        
        while current_date <= end_date:
            day_tasks = tasks.filter(date=current_date)
            total = day_tasks.count()
            completed = day_tasks.filter(status='completed').count()
            
            rate = (completed / total * 100) if total > 0 else 0
            daily_rates.append(rate)
            labels.append(current_date.strftime('%b %d'))
            
            current_date += timedelta(days=1)
        
        if len(daily_rates) < days:
            return {
                'labels': labels,
                'data': daily_rates,
                'average': sum(daily_rates) / len(daily_rates) if daily_rates else 0
            }
        
        moving_avg = []
        for i in range(len(daily_rates)):
            if i < days - 1:
                window = daily_rates[:i+1]
            else:
                window = daily_rates[i-days+1:i+1]
            moving_avg.append(sum(window) / len(window))
        
        return {
            'labels': labels,
            'data': [round(ma, 1) for ma in moving_avg],
            'average': round(sum(moving_avg) / len(moving_avg), 1)
        }
