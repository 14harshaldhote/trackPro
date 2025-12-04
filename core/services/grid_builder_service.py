"""
Grid Builder Service

Consolidates duplicated grid-building logic from time views.
Reduces 520 lines of duplicated code to ~200 lines of reusable service.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional
from core.repositories import base_repository as crud


class GridBuilderService:
    """
    Unified service for building task grids across different time views.
    
    Eliminates code duplication between:
    - monthly_tracker
    - week_view
    - today_view  
    - custom_range_view
    """
    
    def __init__(self, tracker_id: str):
        """
        Initialize grid builder for a specific tracker.
        
        Args:
            tracker_id: Tracker ID to build grids for
        """
        self.tracker_id = tracker_id
    
    def build_grid(self, dates: List[date], layout: str = 'date') -> Dict:
        """
        Unified grid builder for all time views.
        
        Args:
            dates: List of dates to include in grid
            layout: 'date' (rows=templates, cols=dates) or 'task' (rows=dates, cols=templates)
            
        Returns:
            {
                'tracker': tracker dict,
                'templates': list of templates,
                'grid': grid data structure,
                'stats': calculated statistics,
                'dates': processed dates list
            }
        """
        # Fetch all data efficiently using optimized queries
        data = crud.get_day_grid_data(self.tracker_id, dates)
        
        tracker = data['tracker']
        if not tracker:
            return {
                'tracker': None,
                'templates': [],
                'grid': [],
                'stats': {},
                'dates': dates
            }
        
        templates = data['templates']
        instances_map = data['instances_map']
        
        # Build grid based on layout
        if layout == 'date':
            grid = self._build_date_grid(templates, instances_map, dates)
        elif layout == 'task':
            grid = self._build_task_grid(templates, instances_map, dates)
        else:
            grid = self._build_date_grid(templates, instances_map, dates)
        
        # Calculate statistics
        stats = self._calculate_grid_stats(grid, layout)
        
        return {
            'tracker': tracker,
            'templates': templates,
            'grid': grid,
            'stats': stats,
            'dates': dates
        }
    
    def _build_date_grid(self, templates: List[Dict], instances_map: Dict, dates: List[date]) -> List[Dict]:
        """
        Build grid with templates as rows and dates as columns.
        Used by: monthly_tracker, week_view, custom_range_view
        
        Returns:
            [
                {
                    'template': template_dict,
                    'days': [
                        {'date': date, 'task': task_dict, 'status': str, ...},
                        ...
                    ]
                },
                ...
            ]
        """
        today = date.today()
        grid = []
        
        for template in templates:
            row = {
                'template': template,
                'days': []
            }
            
            for current_date in dates:
                date_str = current_date.isoformat()
                
                # O(1) lookup from pre-built map
                inst = instances_map.get(date_str)
                task = None
                
                if inst and 'tasks' in inst:
                    # Find matching task from prefetched tasks
                    task = next(
                        (t for t in inst['tasks'] if t.get('template_id') == template['template_id']),
                        None
                    )
                
                row['days'].append({
                    'date': current_date,
                    'day': current_date.day,
                    'task': task,
                    'status': task.get('status', 'TODO') if task else 'TODO',
                    'is_done': task and task.get('status') == 'DONE',
                    'is_today': current_date == today,
                    'notes': task.get('notes', '') if task else ''
                })
            
            grid.append(row)
        
        return grid
    
    def _build_task_grid(self, templates: List[Dict], instances_map: Dict, dates: List[date]) -> List[Dict]:
        """
        Build grid with dates as rows and templates as columns.
        Alternative layout - could be used for different visualizations.
        
        Returns:
            [
                {
                    'date': date,
                    'tasks': [
                        {'template': template_dict, 'task': task_dict, 'status': str, ...},
                        ...
                    ]
                },
                ...
            ]
        """
        today = date.today()
        grid = []
        
        for current_date in dates:
            date_str = current_date.isoformat()
            inst = instances_map.get(date_str)
            
            row = {
                'date': current_date,
                'day': current_date.day,
                'is_today': current_date == today,
                'tasks': []
            }
            
            for template in templates:
                task = None
                
                if inst and 'tasks' in inst:
                    task = next(
                        (t for t in inst['tasks'] if t.get('template_id') == template['template_id']),
                        None
                    )
                
                row['tasks'].append({
                    'template': template,
                    'task': task,
                    'status': task.get('status', 'TODO') if task else 'TODO',
                    'is_done': task and task.get('status') == 'DONE',
                    'notes': task.get('notes', '') if task else ''
                })
            
            grid.append(row)
        
        return grid
    
    def _calculate_grid_stats(self, grid: List[Dict], layout: str) -> Dict:
        """
        Calculate statistics for the grid.
        
        Args:
            grid: Grid data structure
            layout: Grid layout type
            
        Returns:
            {
                'total_tasks': int,
                'done_tasks': int,
                'in_progress_tasks': int,
                'todo_tasks': int,
                'missed_tasks': int,
                'completion_rate': float
            }
        """
        total_tasks = 0
        done_tasks = 0
        in_progress_tasks = 0
        todo_tasks = 0
        missed_tasks = 0
        
        if layout == 'date':
            # Grid format: rows=templates, cols=days
            for row in grid:
                for day in row.get('days', []):
                    task = day.get('task')
                    if task:
                        total_tasks += 1
                        status = task.get('status', 'TODO')
                        if status == 'DONE':
                            done_tasks += 1
                        elif status == 'IN_PROGRESS':
                            in_progress_tasks += 1
                        elif status == 'MISSED':
                            missed_tasks += 1
                        else:
                            todo_tasks += 1
        elif layout == 'task':
            # Grid format: rows=dates, cols=tasks
            for row in grid:
                for task_item in row.get('tasks', []):
                    task = task_item.get('task')
                    if task:
                        total_tasks += 1
                        status = task.get('status', 'TODO')
                        if status == 'DONE':
                            done_tasks += 1
                        elif status == 'IN_PROGRESS':
                            in_progress_tasks += 1
                        elif status == 'MISSED':
                            missed_tasks += 1
                        else:
                            todo_tasks += 1
        
        completion_rate = (done_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        
        return {
            'total_tasks': total_tasks,
            'done_tasks': done_tasks,
            'in_progress_tasks': in_progress_tasks,
            'todo_tasks': todo_tasks,
            'missed_tasks': missed_tasks,
            'completion_rate': round(completion_rate, 1)
        }
    
    def build_monthly_grid(self, year: int, month: int) -> Dict:
        """
        Convenience method for monthly view.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            Grid data with monthly-specific metadata
        """
        from calendar import monthrange
        
        _, num_days = monthrange(year, month)
        dates = [date(year, month, day) for day in range(1, num_days + 1)]
        
        result = self.build_grid(dates, layout='date')
        
        # Add monthly-specific metadata
        result['year'] = year
        result['month'] = month
        result['month_name'] = date(year, month, 1).strftime('%B %Y')
        result['num_days'] = num_days
        
        # Navigation
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        result['prev_month'] = prev_month
        result['prev_year'] = prev_year
        result['next_month'] = next_month
        result['next_year'] = next_year
        
        return result
    
    def build_week_grid(self, week_offset: int = 0) -> Dict:
        """
        Convenience method for week view.
        
        Args:
            week_offset: Weeks from current week (0 = this week, -1 = last week, +1 = next week)
            
        Returns:
            Grid data with week-specific metadata
        """
        today = date.today()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
        
        # Generate 7 days (Mon-Sun)
        dates = [week_start + timedelta(days=i) for i in range(7)]
        
        result = self.build_grid(dates, layout='date')
        
        # Add week-specific metadata
        result['week_start'] = week_start
        result['week_end'] = dates[-1]
        result['week_offset'] = week_offset
        result['today'] = today
        
        return result
    
    def build_custom_range_grid(self, start_date: date, end_date: date) -> Dict:
        """
        Convenience method for custom date range view.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Grid data with range-specific metadata
        """
        # Generate date range
        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)
        
        result = self.build_grid(dates, layout='date')
        
        # Add range-specific metadata
        result['start_date'] = start_date
        result['end_date'] = end_date
        result['num_days'] = len(dates)
        result['today'] = date.today()
        
        return result
