"""
Analytics Service

Generate analytics and insights for trackers.
"""
from datetime import date, timedelta
from collections import defaultdict
from django.db.models import Count, Q, Avg, F
from core.models import (
    TrackerDefinition, TrackerInstance, TaskInstance,
    TaskTemplate, Goal
)

class AnalyticsService:
    """Generate analytics and insights."""
    
    @staticmethod
    def get_daily_summary(user_id: int, target_date: date = None) -> dict:
        """Get summary stats for a specific day."""
        target_date = target_date or date.today()
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date=target_date,
            deleted_at__isnull=True
        )
        
        stats = tasks.aggregate(
            total=Count('task_instance_id'),
            done=Count('task_instance_id', filter=Q(status='DONE')),
            in_progress=Count('task_instance_id', filter=Q(status='IN_PROGRESS')),
            missed=Count('task_instance_id', filter=Q(status='MISSED')),
            skipped=Count('task_instance_id', filter=Q(status='SKIPPED')),
            blocked=Count('task_instance_id', filter=Q(status='BLOCKED'))
        )
        
        # Handle cases where aggregate returns None for counts if no rows (though usually Count returns 0)
        # Django Count returns 0 if no objects, but let's be safe.
        total = stats['total'] or 0
        done = stats['done'] or 0
        
        stats['todo'] = total - done - (stats['in_progress'] or 0) - (stats['missed'] or 0) - (stats['skipped'] or 0) - (stats['blocked'] or 0)
        stats['completion_rate'] = (done / total * 100) if total > 0 else 0
        stats['date'] = target_date.isoformat()
        
        return stats
    
    @staticmethod
    def get_weekly_summary(user_id: int, week_start: date = None) -> dict:
        """Get summary for an entire week."""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date__range=(week_start, week_end),
            deleted_at__isnull=True
        )
        
        daily_stats = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            # We reuse get_daily_summary but it queries DB each time. 
            # Optimization: aggregate all at once? The plan uses reuse.
            daily_stats.append(AnalyticsService.get_daily_summary(user_id, day))
        
        total = tasks.count()
        done = tasks.filter(status='DONE').count()
        
        return {
            'week_start': week_start.isoformat(),
            'week_end': week_end.isoformat(),
            'total_tasks': total,
            'completed_tasks': done,
            'completion_rate': (done / total * 100) if total > 0 else 0,
            'daily_breakdown': daily_stats,
            'best_day': max(daily_stats, key=lambda x: x['completion_rate'])['date'] if daily_stats else None
        }
    
    @staticmethod
    def get_tracker_analytics(tracker_id: str, days: int = 30) -> dict:
        """Get analytics for a specific tracker."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        instances = TrackerInstance.objects.filter(
            tracker_id=tracker_id,
            tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).prefetch_related('tasks')
        
        daily_data = []
        total_tasks = 0
        total_done = 0
        
        for instance in instances:
            tasks = instance.tasks.filter(deleted_at__isnull=True)
            day_total = tasks.count()
            day_done = tasks.filter(status='DONE').count()
            
            total_tasks += day_total
            total_done += day_done
            
            daily_data.append({
                'date': instance.tracking_date.isoformat(),
                'total': day_total,
                'done': day_done,
                'rate': (day_done / day_total * 100) if day_total > 0 else 0
            })
        
        # Sort daily data by date to ensure trend calculation is correct
        daily_data.sort(key=lambda x: x['date'])
        
        return {
            'tracker_id': tracker_id,
            'period_days': days,
            'total_tasks': total_tasks,
            'completed_tasks': total_done,
            'overall_rate': (total_done / total_tasks * 100) if total_tasks > 0 else 0,
            'daily_data': daily_data,
            'trend': AnalyticsService._calculate_trend(daily_data)
        }
    
    @staticmethod
    def _calculate_trend(daily_data: list) -> str:
        """Calculate if performance is improving, declining, or stable."""
        if len(daily_data) < 7:
            return 'insufficient_data'
        
        # Compare first half vs second half
        mid = len(daily_data) // 2
        first_half = daily_data[:mid]
        second_half = daily_data[mid:]
        
        first_half_avg = sum(d['rate'] for d in first_half) / len(first_half)
        second_half_avg = sum(d['rate'] for d in second_half) / len(second_half)
        
        diff = second_half_avg - first_half_avg
        
        if diff > 5:
            return 'improving'
        elif diff < -5:
            return 'declining'
        else:
            return 'stable'
    
    @staticmethod
    def get_heatmap_data(user_id: int, year: int = None) -> list[dict]:
        """Get completion heatmap data for calendar visualization."""
        year = year or date.today().year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        instances = TrackerInstance.objects.filter(
            tracker__user_id=user_id,
            tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).prefetch_related('tasks')
        
        # Aggregate by date
        date_stats = defaultdict(lambda: {'total': 0, 'done': 0})
        
        for instance in instances:
            tasks = instance.tasks.filter(deleted_at__isnull=True)
            date_key = instance.tracking_date.isoformat()
            
            # Optimization: could use annotation but loop is fine for now
            t_count = tasks.count()
            d_count = tasks.filter(status='DONE').count()
            
            date_stats[date_key]['total'] += t_count
            date_stats[date_key]['done'] += d_count
        
        return [
            {
                'date': d,
                'count': stats['done'],
                'level': AnalyticsService._get_activity_level(stats['done'], stats['total'])
            }
            for d, stats in sorted(date_stats.items())
        ]
    
    @staticmethod
    def _get_activity_level(done: int, total: int) -> int:
        """Get 0-4 activity level for heatmap."""
        if total == 0:
            return 0
        rate = done / total
        if rate >= 0.9:
            return 4
        elif rate >= 0.7:
            return 3
        elif rate >= 0.5:
            return 2
        elif rate > 0:
            return 1
        return 0
    
    @staticmethod
    def get_most_missed_tasks(user_id: int, limit: int = 5) -> list[dict]:
        """Get tasks with highest miss rate."""
        templates = TaskTemplate.objects.filter(
            tracker__user_id=user_id,
            deleted_at__isnull=True
        ).annotate(
            total_instances=Count('instances', filter=Q(instances__deleted_at__isnull=True)),
            missed_count=Count('instances', filter=Q(instances__status='MISSED', instances__deleted_at__isnull=True))
        ).filter(
            total_instances__gt=5  # Only include with enough data
        ).order_by('-missed_count')[:limit]
        
        return [
            {
                'template_id': str(t.template_id),
                'description': t.description,
                'tracker_name': t.tracker.name,
                'missed_count': t.missed_count,
                'total': t.total_instances,
                'miss_rate': (t.missed_count / t.total_instances * 100) if t.total_instances > 0 else 0
            }
            for t in templates
        ]
    
    @staticmethod
    def get_best_days(user_id: int) -> dict:
        """Analyze which days of week user performs best."""
        # Get last 90 days of data
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).select_related('tracker_instance')
        
        day_stats = defaultdict(lambda: {'total': 0, 'done': 0})
        
        for task in tasks:
            if not task.tracker_instance.tracking_date:
                continue
            weekday = task.tracker_instance.tracking_date.weekday()
            day_stats[weekday]['total'] += 1
            if task.status == 'DONE':
                day_stats[weekday]['done'] += 1
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        results = [
            {
                'day': day_names[i],
                'day_num': i,
                'total': stats['total'],
                'done': stats['done'],
                'rate': (stats['done'] / stats['total'] * 100) if stats['total'] > 0 else 0
            }
            for i, stats in sorted(day_stats.items())
        ]
        
        best_day = max(results, key=lambda x: x['rate']) if results else None
        worst_day = min(results, key=lambda x: x['rate']) if results else None
        
        return {
            'breakdown': results,
            'best_day': best_day['day'] if best_day else None,
            'worst_day': worst_day['day'] if worst_day else None
        }
