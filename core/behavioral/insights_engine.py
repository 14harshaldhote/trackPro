"""
Behavioral Insights Engine

Rule-based insights tied to behavioral science research.
Generates actionable suggestions based on tracker metrics and NLP analysis.

No AI/ML - purely deterministic rules grounded in research.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
import numpy as np

from core import analytics
from core.helpers import nlp_helpers, metric_helpers
from core.repositories import base_repository as crud


class InsightType(Enum):
    """Types of behavioral insights"""
    LOW_CONSISTENCY = "low_consistency"
    WEEKEND_DIP = "weekend_dip"
    MORNING_ADVANTAGE = "morning_advantage"
    STREAK_RISK = "streak_risk"
    MOOD_CORRELATION = "mood_correlation"
    SLEEP_IMPACT = "sleep_impact"
    CATEGORY_IMBALANCE = "category_imbalance"
    HIGH_EFFORT_RECOVERY = "high_effort_recovery"
    IMPROVEMENT_TREND = "improvement_trend"
    DECLINING_TREND = "declining_trend"


class Severity(Enum):
    """Severity levels for insights"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Insight:
    """
    A behavioral insight with evidence and suggested action.
    
    Attributes:
        insight_type: Type of insight (from InsightType enum)
        severity: How urgent/important (HIGH, MEDIUM, LOW)
        title: Short, actionable title
        description: Detailed explanation with evidence
        evidence: Raw data supporting this insight
        suggested_action: What the user should do
        research_note: Behavioral science backing
        confidence: Confidence level based on data quality (0-1)
    """
    insight_type: InsightType
    severity: Severity
    title: str
    description: str
    evidence: Dict
    suggested_action: str
    research_note: str
    confidence: float


# =============================================================================
# RESEARCH NOTES (Citations for insights)
# =============================================================================

RESEARCH_NOTES = {
    InsightType.LOW_CONSISTENCY: (
        "Habit formation requires consistent repetition in stable contexts. "
        "'Get yourself to repeat something often enough – and in the same context – "
        "and ultimately it might become automatic' (Wood & Rünger, 2016)."
    ),
    InsightType.WEEKEND_DIP: (
        "Context changes disrupt habits. Weekend routines differ from weekday "
        "patterns, which can break established cues (Neal et al., 2012)."
    ),
    InsightType.STREAK_RISK: (
        "Loss aversion makes streak breaks psychologically costly. Users expend "
        "~40% more effort to maintain streaks (Sela & Shiv, 2009)."
    ),
    InsightType.MOOD_CORRELATION: (
        "Behavior and mood are bidirectionally linked. Task completion can "
        "improve mood through accomplishment, and mood affects motivation "
        "(Baumeister et al., 2018)."
    ),
    InsightType.SLEEP_IMPACT: (
        "Sleep quality strongly predicts next-day cognitive performance and "
        "emotional regulation (Walker, 2017)."
    ),
    InsightType.CATEGORY_IMBALANCE: (
        "Well-being involves multiple life domains (PERMA+). Neglecting areas "
        "like relationships or health reduces overall flourishing "
        "(Seligman, 2011)."
    ),
    InsightType.HIGH_EFFORT_RECOVERY: (
        "Recovery periods are essential after high-intensity effort to prevent "
        "burnout. Scheduled rest improves long-term productivity (Sonnentag, 2012)."
    ),
    InsightType.IMPROVEMENT_TREND: (
        "Positive feedback on progress reinforces behavior. Celebrating "
        "improvement builds self-efficacy (Bandura, 1997)."
    ),
    InsightType.DECLINING_TREND: (
        "Early detection of declining trends allows intervention before "
        "complete habit breakdown. Self-monitoring enables self-correction "
        "(Michie et al., 2013)."
    ),
    InsightType.MORNING_ADVANTAGE: (
        "Cognitive performance peaks in the morning for most people. "
        "Scheduling demanding tasks early leverages natural rhythms (Kahneman, 2011)."
    ),
}


class InsightsEngine:
    """
    Generates behavioral insights from tracker data.
    
    All rules are deterministic (no AI/ML) and grounded in behavioral science.
    Each insight includes evidence, suggested actions, and research citations.
    
    Example usage:
        engine = InsightsEngine(tracker_id)
        insights = engine.generate_insights()
        for insight in insights:
            print(f"{insight.title}: {insight.suggested_action}")
    """
    
    def __init__(self, tracker_id: str):
        self.tracker_id = tracker_id
        self.insights: List[Insight] = []
        
        # Load metrics (cached)
        self._load_metrics()
    
    def _load_metrics(self):
        """Load all metrics needed for insight generation."""
        self.completion = analytics.compute_completion_rate(self.tracker_id)
        self.streaks = analytics.detect_streaks(self.tracker_id)
        self.consistency = analytics.compute_consistency_score(self.tracker_id)
        self.balance = analytics.compute_balance_score(self.tracker_id)
        self.effort = analytics.compute_effort_index(self.tracker_id)
        self.sentiment = analytics.analyze_notes_sentiment(self.tracker_id)
        self.trends = analytics.analyze_trends(self.tracker_id)
    
    def generate_insights(self) -> List[Insight]:
        """
        Generate all applicable insights based on current metrics.
        
        Returns:
            List of Insight objects, sorted by severity (HIGH first)
        """
        self.insights = []
        
        # Run all insight detection rules
        self._check_consistency()
        self._check_weekend_pattern()
        self._check_streak_risk()
        self._check_mood_correlation()
        self._check_sleep_impact()
        self._check_category_balance()
        self._check_effort_recovery()
        self._check_trends()
        
        # Sort by severity
        severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
        self.insights.sort(key=lambda x: severity_order[x.severity])
        
        return self.insights
    
    def _check_consistency(self):
        """Check for low consistency and suggest improvements."""
        consistency_score = self.consistency.get('value', 0)
        
        if consistency_score < 60:
            self.insights.append(Insight(
                insight_type=InsightType.LOW_CONSISTENCY,
                severity=Severity.HIGH if consistency_score < 40 else Severity.MEDIUM,
                title="Build a Stronger Routine",
                description=(
                    f"Your consistency score is {consistency_score:.0f}%. "
                    f"Irregular patterns make habits harder to form."
                ),
                evidence={
                    'consistency_score': consistency_score,
                    'rolling_scores': self.consistency.get('rolling_scores', [])[-7:]
                },
                suggested_action=(
                    "Try scheduling this tracker at the same time daily. "
                    "Context cues (same time, same place) help automate behaviors."
                ),
                research_note=RESEARCH_NOTES[InsightType.LOW_CONSISTENCY],
                confidence=0.8 if self.consistency.get('raw_inputs', {}).get('total_days', 0) > 14 else 0.5
            ))
    
    def _check_weekend_pattern(self):
        """Detect weekend vs weekday performance differences."""
        daily_rates = self.completion.get('daily_rates', [])
        
        if len(daily_rates) < 14:
            return
        
        # Separate weekday and weekend performance
        weekday_rates = []
        weekend_rates = []
        
        for entry in daily_rates:
            entry_date = entry.get('date')
            if isinstance(entry_date, str):
                entry_date = date.fromisoformat(entry_date)
            
            if entry_date.weekday() < 5:  # Monday-Friday
                weekday_rates.append(entry['rate'])
            else:
                weekend_rates.append(entry['rate'])
        
        if not weekend_rates or not weekday_rates:
            return
        
        weekday_avg = np.mean(weekday_rates)
        weekend_avg = np.mean(weekend_rates)
        difference = weekday_avg - weekend_avg
        
        if difference > 20:  # 20% drop on weekends
            self.insights.append(Insight(
                insight_type=InsightType.WEEKEND_DIP,
                severity=Severity.MEDIUM,
                title="Weekend Performance Drops",
                description=(
                    f"Your weekday completion ({weekday_avg:.0f}%) is significantly higher "
                    f"than weekends ({weekend_avg:.0f}%). The {difference:.0f}% difference "
                    f"suggests your routine changes on weekends."
                ),
                evidence={
                    'weekday_average': round(weekday_avg, 1),
                    'weekend_average': round(weekend_avg, 1),
                    'difference': round(difference, 1)
                },
                suggested_action=(
                    "Consider lighter weekend goals or adjust tasks to fit weekend routines. "
                    "A 'maintenance mode' on weekends may preserve streaks."
                ),
                research_note=RESEARCH_NOTES[InsightType.WEEKEND_DIP],
                confidence=0.75
            ))
    
    def _check_streak_risk(self):
        """Warn when current streak is at risk."""
        current_streak = self.streaks.get('value', {}).get('current_streak', 0)
        longest_streak = self.streaks.get('value', {}).get('longest_streak', 0)
        
        # Check recent completion
        daily_rates = self.completion.get('daily_rates', [])
        if len(daily_rates) >= 2:
            recent_rate = daily_rates[-1].get('rate', 0)
            prev_rate = daily_rates[-2].get('rate', 0)
            
            # Streak at risk if recent completion dropped significantly
            if current_streak >= 3 and recent_rate < 70 and prev_rate > 80:
                self.insights.append(Insight(
                    insight_type=InsightType.STREAK_RISK,
                    severity=Severity.HIGH,
                    title=f"Protect Your {current_streak}-Day Streak!",
                    description=(
                        f"Your completion dropped from {prev_rate:.0f}% to {recent_rate:.0f}% recently. "
                        f"Your {current_streak}-day streak is at risk."
                    ),
                    evidence={
                        'current_streak': current_streak,
                        'longest_streak': longest_streak,
                        'recent_rate': recent_rate,
                        'previous_rate': prev_rate
                    },
                    suggested_action=(
                        "Focus on completing at least one priority task today. "
                        "Even partial progress maintains momentum."
                    ),
                    research_note=RESEARCH_NOTES[InsightType.STREAK_RISK],
                    confidence=0.9
                ))
    
    def _check_mood_correlation(self):
        """Check if mood correlates with task completion."""
        try:
            correlations = analytics.compute_correlations(self.tracker_id)
            corr_matrix = correlations.get('correlation_matrix', {})
            
            if 'mood' in corr_matrix and 'completion_rate' in corr_matrix.get('mood', {}):
                mood_completion_corr = corr_matrix['mood'].get('completion_rate', 0)
                is_significant = correlations.get('significant', {}).get('mood', {}).get('completion_rate', False)
                
                if abs(mood_completion_corr) > 0.3 and is_significant:
                    if mood_completion_corr > 0:
                        self.insights.append(Insight(
                            insight_type=InsightType.MOOD_CORRELATION,
                            severity=Severity.LOW,
                            title="Mood Boosts When You Complete Tasks",
                            description=(
                                f"There's a positive correlation (r={mood_completion_corr:.2f}) between "
                                f"your mood and task completion. Completing tasks may improve your mood."
                            ),
                            evidence={
                                'correlation': round(mood_completion_corr, 2),
                                'is_significant': is_significant
                            },
                            suggested_action=(
                                "On low-mood days, try completing easy tasks first "
                                "to build momentum and lift your spirits."
                            ),
                            research_note=RESEARCH_NOTES[InsightType.MOOD_CORRELATION],
                            confidence=0.7
                        ))
                    else:
                        self.insights.append(Insight(
                            insight_type=InsightType.MOOD_CORRELATION,
                            severity=Severity.MEDIUM,
                            title="Low Mood Affects Productivity",
                            description=(
                                f"There's a negative correlation (r={mood_completion_corr:.2f}) "
                                f"suggesting mood dips coincide with lower completion."
                            ),
                            evidence={
                                'correlation': round(mood_completion_corr, 2),
                                'is_significant': is_significant
                            },
                            suggested_action=(
                                "Consider mood-boosting activities (exercise, social time) "
                                "as prerequisites for difficult tasks."
                            ),
                            research_note=RESEARCH_NOTES[InsightType.MOOD_CORRELATION],
                            confidence=0.7
                        ))
        except Exception:
            pass  # Not enough data for correlation
    
    def _check_sleep_impact(self):
        """Check if sleep mentions correlate with performance."""
        # Get notes and look for sleep patterns
        notes = crud.db.fetch_filter('DayNotes', tracker_id=self.tracker_id)
        
        sleep_data = []
        for note in notes:
            sleep_info = nlp_helpers.extract_sleep_pattern(note.get('content', ''))
            if sleep_info.get('hours'):
                note_date = note.get('date')
                sleep_data.append({
                    'date': note_date,
                    'hours': sleep_info['hours']
                })
        
        if len(sleep_data) < 5:
            return
        
        # Check if low sleep correlates with low completion
        avg_sleep = np.mean([s['hours'] for s in sleep_data])
        low_sleep_days = [s['date'] for s in sleep_data if s['hours'] < 6]
        
        if len(low_sleep_days) > 2:
            self.insights.append(Insight(
                insight_type=InsightType.SLEEP_IMPACT,
                severity=Severity.MEDIUM,
                title="Sleep Affects Your Performance",
                description=(
                    f"You average {avg_sleep:.1f} hours of sleep based on your notes. "
                    f"You've had {len(low_sleep_days)} days with less than 6 hours."
                ),
                evidence={
                    'average_sleep': round(avg_sleep, 1),
                    'low_sleep_days': len(low_sleep_days),
                    'total_tracked_days': len(sleep_data)
                },
                suggested_action=(
                    "Try a wind-down routine and 7-8 hour sleep target. "
                    "Quality sleep significantly impacts next-day productivity."
                ),
                research_note=RESEARCH_NOTES[InsightType.SLEEP_IMPACT],
                confidence=0.6
            ))
    
    def _check_category_balance(self):
        """Check for category imbalances."""
        balance_score = self.balance.get('value', 0)
        category_dist = self.balance.get('category_distribution', {})
        
        if not category_dist or len(category_dist) < 2:
            return
        
        if balance_score < 50:
            # Find the dominant category
            max_cat = max(category_dist, key=category_dist.get)
            max_pct = category_dist[max_cat]
            
            # Find neglected categories
            neglected = [cat for cat, pct in category_dist.items() if pct < 10]
            
            self.insights.append(Insight(
                insight_type=InsightType.CATEGORY_IMBALANCE,
                severity=Severity.MEDIUM if balance_score < 30 else Severity.LOW,
                title="Life Balance Check",
                description=(
                    f"Your balance score is {balance_score:.0f}%. "
                    f"'{max_cat}' dominates at {max_pct:.0f}% of tasks"
                    + (f", while {', '.join(neglected)} are nearly neglected." if neglected else ".")
                ),
                evidence={
                    'balance_score': round(balance_score, 1),
                    'category_distribution': category_dist,
                    'dominant_category': max_cat,
                    'neglected_categories': neglected
                },
                suggested_action=(
                    f"Consider adding tasks in {', '.join(neglected) if neglected else 'other categories'}. "
                    f"Well-being comes from attending to multiple life domains."
                ),
                research_note=RESEARCH_NOTES[InsightType.CATEGORY_IMBALANCE],
                confidence=0.75
            ))
    
    def _check_effort_recovery(self):
        """Suggest recovery after high-effort periods."""
        effort_value = self.effort.get('value', 0)
        completed_tasks = self.effort.get('raw_inputs', {}).get('completed_tasks', 0)
        
        # Check recent daily completion to see if efforts are sustained
        daily_rates = self.completion.get('daily_rates', [])
        
        if len(daily_rates) >= 5:
            recent_rates = [d['rate'] for d in daily_rates[-5:]]
            recent_avg = np.mean(recent_rates)
            
            # High completion + high effort suggests need for recovery
            if recent_avg > 85 and completed_tasks > 20:
                self.insights.append(Insight(
                    insight_type=InsightType.HIGH_EFFORT_RECOVERY,
                    severity=Severity.LOW,
                    title="Consider a Recovery Day",
                    description=(
                        f"You've maintained {recent_avg:.0f}% completion over the last 5 days "
                        f"with high effort. Scheduled recovery prevents burnout."
                    ),
                    evidence={
                        'recent_average': round(recent_avg, 1),
                        'effort_index': effort_value,
                        'completed_tasks': completed_tasks
                    },
                    suggested_action=(
                        "Schedule a lighter day soon with only essential tasks. "
                        "Strategic rest improves long-term performance."
                    ),
                    research_note=RESEARCH_NOTES[InsightType.HIGH_EFFORT_RECOVERY],
                    confidence=0.65
                ))
    
    def _check_trends(self):
        """Check for improving or declining trends."""
        trend_direction = self.trends.get('trend_direction', 'stable')
        improving_periods = self.trends.get('improving_periods', 0)
        total_periods = self.trends.get('total_periods', 0)
        
        if total_periods < 7:
            return
        
        improvement_ratio = improving_periods / total_periods if total_periods > 0 else 0
        
        if trend_direction == 'improving' and improvement_ratio > 0.6:
            self.insights.append(Insight(
                insight_type=InsightType.IMPROVEMENT_TREND,
                severity=Severity.LOW,
                title="Great Progress! You're Improving",
                description=(
                    f"Your performance is trending upward! "
                    f"{improving_periods} of {total_periods} periods showed improvement."
                ),
                evidence={
                    'trend_direction': trend_direction,
                    'improving_periods': improving_periods,
                    'total_periods': total_periods,
                    'improvement_ratio': round(improvement_ratio, 2)
                },
                suggested_action=(
                    "Keep up the momentum! Consider raising your targets slightly."
                ),
                research_note=RESEARCH_NOTES[InsightType.IMPROVEMENT_TREND],
                confidence=0.8
            ))
        
        elif trend_direction == 'declining' and improvement_ratio < 0.4:
            self.insights.append(Insight(
                insight_type=InsightType.DECLINING_TREND,
                severity=Severity.MEDIUM,
                title="Performance Trend Declining",
                description=(
                    f"Your performance has been trending down. "
                    f"Only {improving_periods} of {total_periods} periods improved."
                ),
                evidence={
                    'trend_direction': trend_direction,
                    'improving_periods': improving_periods,
                    'total_periods': total_periods,
                    'improvement_ratio': round(improvement_ratio, 2)
                },
                suggested_action=(
                    "Consider reducing task count temporarily or reviewing your goals. "
                    "Early intervention prevents habit breakdown."
                ),
                research_note=RESEARCH_NOTES[InsightType.DECLINING_TREND],
                confidence=0.75
            ))
    
    def to_dict(self) -> List[Dict]:
        """Convert insights to dictionary format for JSON serialization."""
        return [
            {
                'type': insight.insight_type.value,
                'severity': insight.severity.value,
                'title': insight.title,
                'description': insight.description,
                'evidence': insight.evidence,
                'suggested_action': insight.suggested_action,
                'research_note': insight.research_note,
                'confidence': insight.confidence
            }
            for insight in self.insights
        ]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_insights(tracker_id: str) -> List[Dict]:
    """
    Generate insights for a tracker.
    
    Args:
        tracker_id: Tracker ID
        
    Returns:
        List of insight dictionaries
    """
    engine = InsightsEngine(tracker_id)
    engine.generate_insights()
    return engine.to_dict()


def get_top_insight(tracker_id: str) -> Optional[Dict]:
    """
    Get the most important insight for a tracker.
    
    Args:
        tracker_id: Tracker ID
        
    Returns:
        Single insight dictionary or None
    """
    insights = get_insights(tracker_id)
    return insights[0] if insights else None


def generate_smart_suggestions(user) -> List[Dict]:
    """
    Generate smart behavioral suggestions based on user patterns.
    
    Following OpusSuggestion.md - Analytics & Insights
    Analyzes historical data to provide personalized productivity insights.
    
    Args:
        user: Django User instance
    
    Returns:
        List of suggestion dictionaries with type, title, description, and action
    """
    from core.models import TaskInstance
    
    suggestions = []
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    
    # Get user's tasks from the last 30 days
    tasks = TaskInstance.objects.filter(
        tracker_instance__tracker__user=user,
        tracker_instance__period_start__gte=thirty_days_ago
    ).select_related('template', 'tracker_instance')
    
    if not tasks.exists():
        return []
    
    # =========================================================================
    # Day-of-Week Performance Analysis
    # =========================================================================
    
    day_stats = {i: {'total': 0, 'completed': 0} for i in range(7)}
    
    for task in tasks:
        day = task.tracker_instance.period_start.weekday()
        day_stats[day]['total'] += 1
        if task.status == 'DONE':
            day_stats[day]['completed'] += 1
    
    # Find best performing day
    day_rates = {}
    for day, stats in day_stats.items():
        if stats['total'] >= 5:  # Minimum 5 tasks for reliable analysis
            day_rates[day] = stats['completed'] / stats['total']
    
    if day_rates:
        best_day = max(day_rates, key=day_rates.get)
        best_rate = day_rates[best_day]
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        if best_rate > 0.7:  # 70%+ completion rate
            suggestions.append({
                'type': 'best_day',
                'title': f'You perform best on {day_names[best_day]}s',
                'description': f'Your completion rate is {best_rate*100:.0f}% on {day_names[best_day]}s, compared to your overall average.',
                'action': f'Schedule important or challenging tasks for {day_names[best_day]}s to leverage your peak performance.',
                'evidence': {
                  'day': day_names[best_day],
                    'rate': round(best_rate * 100, 1),
                    'sample_size': day_stats[best_day]['total']
                }
            })
        
        # Find worst performing day
        worst_day = min(day_rates, key=day_rates.get)
        worst_rate = day_rates[worst_day]
        
        if worst_rate < 0.4 and day_stats[worst_day]['total'] >= 5:  # 40% or less
            suggestions.append({
                'type': 'challenging_day',
                'title': f'{day_names[worst_day]}s are challenging for you',
                'description': f'Your completion rate drops to {worst_rate*100:.0f}% on {day_names[worst_day]}s.',
                'action': f'Consider lighter goals on {day_names[worst_day]}s or identify what makes this day difficult.',
                'evidence': {
                    'day': day_names[worst_day],
                    'rate': round(worst_rate * 100, 1),
                    'sample_size': day_stats[worst_day]['total']
                }
            })
    
    # =========================================================================
    # Time of Day Pattern Analysis
    # =========================================================================
    
    time_stats = {'morning': 0, 'afternoon': 0, 'evening': 0, 'night': 0, 'anytime': 0}
    time_completed = {'morning': 0, 'afternoon': 0, 'evening': 0, 'night': 0, 'anytime': 0}
    
    for task in tasks:
        time_of_day = task.template.time_of_day
        if time_of_day in time_stats:
            time_stats[time_of_day] += 1
            if task.status == 'DONE':
                time_completed[time_of_day] += 1
    
    # Find best time of day
    time_rates = {}
    for time_period, total in time_stats.items():
        if total >= 5 and time_period != 'anytime':
            time_rates[time_period] = time_completed[time_period] / total
    
    if time_rates:
        best_time = max(time_rates, key=time_rates.get)
        best_time_rate = time_rates[best_time]
        
        if best_time_rate > 0.75:
            suggestions.append({
                'type': 'best_time',
                'title': f'{best_time.capitalize()} is your most productive time',
                'description': f'You complete {best_time_rate*100:.0f}% of your {best_time} tasks.',
                'action': f'Schedule demanding tasks in the {best_time} when your energy is highest.',
                'evidence': {
                    'time_period': best_time,
                    'rate': round(best_time_rate * 100, 1)
                }
            })
    
    # =========================================================================
    # Streak Momentum Analysis
    # =========================================================================
    
    # Get recent tasks (last 7 days)
    seven_days_ago = today - timedelta(days=7)
    recent_tasks = tasks.filter(tracker_instance__period_start__gte=seven_days_ago)
    
    if recent_tasks.exists():
        recent_completed = recent_tasks.filter(status='DONE').count()
        recent_total = recent_tasks.count()
        recent_rate = recent_completed / recent_total if recent_total > 0 else 0
        
        if recent_rate >= 0.8:
            suggestions.append({
                'type': 'momentum',
                'title': "You're on a roll!",
                'description': f"You've completed {recent_rate*100:.0f}% of tasks in the last 7 days.",
                'action': 'Maintain this momentum! Consider adding a new challenge or goal.',
                'evidence': {
                    'completion_rate': round(recent_rate * 100, 1),
                    'days': 7
                }
            })
        elif recent_rate < 0.5:
            suggestions.append({
                'type': 'recovery_needed',
                'title': 'Time to rebuild momentum',
                'description': f"Your completion rate has dropped to {recent_rate*100:.0f}% this week.",
                'action': 'Start with one small win today. Small successes build momentum.',
                'evidence': {
                    'completion_rate': round(recent_rate * 100, 1),
                    'days': 7
                }
            })
    
    # =========================================================================
    # Category Balance Analysis
    # =========================================================================
    
    category_stats = {}
    for task in tasks:
        category = task.template.category or 'Uncategorized'
        if category not in category_stats:
            category_stats[category] = {'total': 0, 'completed': 0}
        category_stats[category]['total'] += 1
        if task.status == 'DONE':
            category_stats[category]['completed'] += 1
    
    if len(category_stats) >= 3:
        # Check for category imbalance
        total_tasks = sum(cat['total'] for cat in category_stats.values())
        dominant_category = max(category_stats, key=lambda k: category_stats[k]['total'])
        dominant_pct = (category_stats[dominant_category]['total'] / total_tasks) * 100
        
        if dominant_pct > 60:
            suggestions.append({
                'type': 'balance',
                'title': 'Life balance opportunity',
                'description': f'{dominant_pct:.0f}% of your tasks are in "{dominant_category}".',
                'action': 'Consider adding tasks from other life areas for better balance.',
                'evidence': {
                    'dominant_category': dominant_category,
                    'percentage': round(dominant_pct, 1)
                }
            })
    
    return suggestions

