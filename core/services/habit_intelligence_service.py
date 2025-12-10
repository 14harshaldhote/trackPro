"""
Habit Intelligence Service - V2.0 Feature

Pattern detection and predictive insights for user habits.
Surfaces patterns like "you miss gym most often on Mondays" or
"your mood dips correlate with skipped meditation."

Written from scratch for Version 2.0
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import ExtractWeekDay, ExtractHour
from core.models import (
    TaskInstance, TrackerInstance, TrackerDefinition, 
    TaskTemplate, DayNote, UserPreferences
)
import logging

logger = logging.getLogger(__name__)


class HabitIntelligenceService:
    """
    Service for detecting patterns and generating habit insights.
    
    Key capabilities:
    - Day-of-week analysis (when do users perform best/worst)
    - Time-of-day patterns (morning vs evening performance)
    - Streak correlation (what behaviors co-occur with streaks)
    - Mood correlations (if DayNotes have sentiment)
    - Task difficulty prediction
    - Optimal scheduling suggestions
    """
    
    # Minimum data points needed for reliable patterns
    MIN_DATA_POINTS = 14
    
    # Insight types and their priority
    INSIGHT_PRIORITIES = {
        'critical_weakness': 1,
        'strong_pattern': 2,
        'opportunity': 3,
        'positive_reinforcement': 4,
        'suggestion': 5
    }
    
    @staticmethod
    def analyze_day_of_week_patterns(user_id: int, days: int = 90) -> Dict:
        """
        Analyze which days of the week the user performs best/worst.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Dict with day-by-day analysis
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get all task instances in range
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).select_related('tracker_instance')
        
        # Calculate by day of week (0=Monday, 6=Sunday)
        day_stats = defaultdict(lambda: {'total': 0, 'done': 0, 'missed': 0})
        
        for task in tasks:
            weekday = task.tracker_instance.tracking_date.weekday()
            day_stats[weekday]['total'] += 1
            if task.status == 'DONE':
                day_stats[weekday]['done'] += 1
            elif task.status == 'MISSED':
                day_stats[weekday]['missed'] += 1
        
        # Calculate rates and rankings
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        results = []
        
        for day, stats in day_stats.items():
            if stats['total'] > 0:
                completion_rate = (stats['done'] / stats['total']) * 100
                miss_rate = (stats['missed'] / stats['total']) * 100
            else:
                completion_rate = 0
                miss_rate = 0
            
            results.append({
                'day': day,
                'day_name': day_names[day],
                'total_tasks': stats['total'],
                'completed': stats['done'],
                'missed': stats['missed'],
                'completion_rate': round(completion_rate, 1),
                'miss_rate': round(miss_rate, 1)
            })
        
        # Sort by completion rate
        results.sort(key=lambda x: x['completion_rate'], reverse=True)
        
        best_day = results[0] if results else None
        worst_day = results[-1] if results else None
        
        insights = []
        if best_day and worst_day and len(results) >= 3:
            if best_day['completion_rate'] - worst_day['completion_rate'] > 20:
                insights.append({
                    'type': 'strong_pattern',
                    'message': f"You're {best_day['completion_rate'] - worst_day['completion_rate']:.0f}% more productive on {best_day['day_name']}s than {worst_day['day_name']}s",
                    'actionable': f"Consider scheduling important tasks on {best_day['day_name']}s"
                })
            
            if worst_day['miss_rate'] > 30:
                insights.append({
                    'type': 'critical_weakness',
                    'message': f"You miss {worst_day['miss_rate']:.0f}% of tasks on {worst_day['day_name']}s",
                    'actionable': f"Try reducing {worst_day['day_name']} workload or setting extra reminders"
                })
        
        return {
            'by_day': results,
            'best_day': best_day,
            'worst_day': worst_day,
            'insights': insights,
            'data_points': sum(r['total_tasks'] for r in results)
        }
    
    @staticmethod
    def analyze_task_difficulty(user_id: int, days: int = 90) -> List[Dict]:
        """
        Identify which tasks are most frequently missed or abandoned.
        
        Returns:
            List of tasks ranked by difficulty (miss rate)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get task stats grouped by template
        template_stats = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).values('template_id', 'template__description').annotate(
            total=Count('task_instance_id'),
            done=Count('task_instance_id', filter=Q(status='DONE')),
            missed=Count('task_instance_id', filter=Q(status='MISSED')),
            in_progress=Count('task_instance_id', filter=Q(status='IN_PROGRESS'))
        ).filter(total__gte=5)  # Minimum instances
        
        results = []
        for stat in template_stats:
            completion_rate = (stat['done'] / stat['total']) * 100 if stat['total'] > 0 else 0
            miss_rate = (stat['missed'] / stat['total']) * 100 if stat['total'] > 0 else 0
            abandon_rate = (stat['in_progress'] / stat['total']) * 100 if stat['total'] > 0 else 0
            
            # Calculate difficulty score (0-100)
            difficulty_score = (miss_rate * 0.6) + (abandon_rate * 0.3) + ((100 - completion_rate) * 0.1)
            
            results.append({
                'template_id': str(stat['template_id']),
                'description': stat['template__description'],
                'total_instances': stat['total'],
                'completion_rate': round(completion_rate, 1),
                'miss_rate': round(miss_rate, 1),
                'abandon_rate': round(abandon_rate, 1),
                'difficulty_score': round(difficulty_score, 1)
            })
        
        # Sort by difficulty
        results.sort(key=lambda x: x['difficulty_score'], reverse=True)
        
        return results
    
    @staticmethod
    def find_streak_correlations(user_id: int) -> Dict:
        """
        Find which behaviors correlate with maintaining streaks.
        
        Analyzes what tasks were completed on successful streak days
        vs days when streaks broke.
        """
        from core.services.streak_service import StreakService
        
        # Get all user trackers
        trackers = TrackerDefinition.objects.filter(
            user_id=user_id,
            deleted_at__isnull=True
        )
        
        correlations = []
        
        for tracker in trackers:
            streak_data = StreakService.calculate_streak(
                str(tracker.tracker_id), 
                user_id
            )
            
            if streak_data.current_streak >= 7:
                # Analyze what makes streaks work
                # Get the tasks that are most consistently done during streaks
                instances = TrackerInstance.objects.filter(
                    tracker=tracker,
                    tracking_date__gte=date.today() - timedelta(days=streak_data.current_streak),
                    deleted_at__isnull=True
                ).prefetch_related('tasks')
                
                task_completion_during_streak = defaultdict(int)
                task_total_during_streak = defaultdict(int)
                
                for instance in instances:
                    for task in instance.tasks.filter(deleted_at__isnull=True):
                        task_total_during_streak[task.template_id] += 1
                        if task.status == 'DONE':
                            task_completion_during_streak[task.template_id] += 1
                
                # Find anchor tasks (always completed during streak)
                anchor_tasks = []
                for template_id, total in task_total_during_streak.items():
                    done = task_completion_during_streak.get(template_id, 0)
                    if total > 0 and done / total >= 0.95:
                        try:
                            template = TaskTemplate.objects.get(template_id=template_id)
                            anchor_tasks.append({
                                'description': template.description,
                                'completion_rate': round((done / total) * 100, 1)
                            })
                        except TaskTemplate.DoesNotExist:
                            pass
                
                if anchor_tasks:
                    correlations.append({
                        'tracker_name': tracker.name,
                        'current_streak': streak_data.current_streak,
                        'anchor_tasks': anchor_tasks,
                        'insight': f"Your {tracker.name} streak relies on consistently doing: {', '.join(t['description'] for t in anchor_tasks[:3])}"
                    })
        
        return {
            'correlations': correlations,
            'total_trackers_analyzed': len(trackers)
        }
    
    @staticmethod
    def analyze_mood_task_correlation(user_id: int, days: int = 90) -> Dict:
        """
        Correlate task completion with mood (from DayNotes sentiment).
        
        Requires DayNotes to have sentiment_score populated.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get notes with sentiment
        notes_with_sentiment = DayNote.objects.filter(
            tracker__user_id=user_id,
            date__range=(start_date, end_date),
            sentiment_score__isnull=False
        ).values('date', 'tracker_id', 'sentiment_score')
        
        if not notes_with_sentiment:
            return {'message': 'Not enough mood data for correlation analysis'}
        
        # Create date -> sentiment mapping
        date_sentiment = {}
        for note in notes_with_sentiment:
            key = (note['date'], note['tracker_id'])
            date_sentiment[key] = note['sentiment_score']
        
        # Get task completion for those dates
        high_mood_completion = []
        low_mood_completion = []
        
        for (note_date, tracker_id), sentiment in date_sentiment.items():
            tasks = TaskInstance.objects.filter(
                tracker_instance__tracker_id=tracker_id,
                tracker_instance__tracking_date=note_date,
                deleted_at__isnull=True
            )
            
            total = tasks.count()
            done = tasks.filter(status='DONE').count()
            
            if total > 0:
                rate = done / total
                if sentiment >= 0.6:  # Positive mood
                    high_mood_completion.append(rate)
                elif sentiment <= 0.4:  # Negative mood
                    low_mood_completion.append(rate)
        
        insights = []
        
        if high_mood_completion and low_mood_completion:
            avg_high = sum(high_mood_completion) / len(high_mood_completion) * 100
            avg_low = sum(low_mood_completion) / len(low_mood_completion) * 100
            
            if avg_high - avg_low > 15:
                insights.append({
                    'type': 'strong_pattern',
                    'message': f"You complete {avg_high - avg_low:.0f}% more tasks when in a good mood",
                    'actionable': "Try starting your day with a mood-boosting activity"
                })
        
        return {
            'high_mood_completion_rate': round(
                sum(high_mood_completion) / len(high_mood_completion) * 100, 1
            ) if high_mood_completion else None,
            'low_mood_completion_rate': round(
                sum(low_mood_completion) / len(low_mood_completion) * 100, 1
            ) if low_mood_completion else None,
            'data_points': len(date_sentiment),
            'insights': insights
        }
    
    @staticmethod
    def get_optimal_schedule_suggestions(user_id: int) -> List[Dict]:
        """
        Suggest optimal times/days for tasks based on historical performance.
        
        Returns:
            List of scheduling suggestions
        """
        suggestions = []
        
        # Get day-of-week analysis
        dow_analysis = HabitIntelligenceService.analyze_day_of_week_patterns(user_id)
        
        # Get difficulty analysis
        task_difficulty = HabitIntelligenceService.analyze_task_difficulty(user_id)
        
        if dow_analysis['best_day'] and task_difficulty:
            best_day = dow_analysis['best_day']['day_name']
            hardest_tasks = task_difficulty[:3]
            
            for task in hardest_tasks:
                if task['miss_rate'] > 30:
                    suggestions.append({
                        'task': task['description'],
                        'current_miss_rate': task['miss_rate'],
                        'suggestion': f"Consider moving '{task['description']}' to {best_day} when you're most productive",
                        'priority': 'high' if task['miss_rate'] > 50 else 'medium'
                    })
        
        # Suggest reducing load on worst days
        if dow_analysis['worst_day'] and dow_analysis['worst_day']['miss_rate'] > 30:
            worst_day = dow_analysis['worst_day']['day_name']
            suggestions.append({
                'task': None,
                'suggestion': f"Consider reducing your task load on {worst_day}s - your miss rate is {dow_analysis['worst_day']['miss_rate']:.0f}%",
                'priority': 'medium'
            })
        
        return suggestions
    
    @staticmethod
    def generate_all_insights(user_id: int) -> Dict:
        """
        Generate all available insights for a user.
        
        Returns:
            Comprehensive insights package
        """
        insights = []
        
        # Day of week patterns
        dow = HabitIntelligenceService.analyze_day_of_week_patterns(user_id)
        insights.extend(dow.get('insights', []))
        
        # Task difficulty
        difficulty = HabitIntelligenceService.analyze_task_difficulty(user_id)
        if difficulty and difficulty[0]['miss_rate'] > 40:
            hardest = difficulty[0]
            insights.append({
                'type': 'critical_weakness',
                'message': f"'{hardest['description']}' is your most challenging task with a {hardest['miss_rate']:.0f}% miss rate",
                'actionable': "Consider breaking this task into smaller steps or scheduling it when you have more energy"
            })
        
        # Streak correlations
        streaks = HabitIntelligenceService.find_streak_correlations(user_id)
        for corr in streaks.get('correlations', []):
            insights.append({
                'type': 'positive_reinforcement',
                'message': corr['insight'],
                'actionable': "Keep prioritizing these anchor tasks to maintain your streak"
            })
        
        # Mood correlations
        mood = HabitIntelligenceService.analyze_mood_task_correlation(user_id)
        insights.extend(mood.get('insights', []))
        
        # Get suggestions
        suggestions = HabitIntelligenceService.get_optimal_schedule_suggestions(user_id)
        for sug in suggestions:
            insights.append({
                'type': 'suggestion',
                'message': sug['suggestion'],
                'priority': sug.get('priority', 'low')
            })
        
        # Sort by priority
        priority_order = {'critical_weakness': 0, 'strong_pattern': 1, 'opportunity': 2, 
                         'positive_reinforcement': 3, 'suggestion': 4}
        insights.sort(key=lambda x: priority_order.get(x.get('type', 'suggestion'), 5))
        
        return {
            'insights': insights[:10],  # Top 10 insights
            'analysis': {
                'day_of_week': dow,
                'task_difficulty': difficulty[:5] if difficulty else [],
                'streak_correlations': streaks,
                'mood_correlation': mood
            }
        }
