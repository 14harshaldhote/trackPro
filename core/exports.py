"""
Data export and reporting module.
Generates professional reports using XlsxWriter and multi-format exports using tablib.
"""
import os
from datetime import datetime, date
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

def generate_behavior_summary(tracker_id: str, output_path: str) -> str:
    """
    Generates a comprehensive Excel report with multiple sheets and charts.
    
    Args:
        tracker_id: Tracker ID
        output_path: Path to save the Excel file
    
    Returns:
        Path to generated file
    """
    import xlsxwriter
    from core import crud, analytics
    
    # Fetch tracker info
    tracker = crud.db.fetch_by_id('TrackerDefinitions', 'tracker_id', tracker_id)
    if not tracker:
        raise ValueError(f"Tracker {tracker_id} not found")
    
    # Compute metrics
    completion = analytics.compute_completion_rate(tracker_id)
    streaks = analytics.detect_streaks(tracker_id)
    consistency = analytics.compute_consistency_score(tracker_id)
    balance = analytics.compute_balance_score(tracker_id)
    effort = analytics.compute_effort_index(tracker_id)
    
    # Create workbook
    workbook = xlsxwriter.Workbook(output_path)
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'bg_color': '#4CAF50',
        'font_color': 'white',
        'border': 1
    })
    
    metric_label_format = workbook.add_format({
        'bold': True,
        'font_size': 11
    })
    
    metric_value_format = workbook.add_format({
        'font_size': 14,
        'num_format': '0.00'
    })
    
    # Sheet 1: Overview
    overview = workbook.add_worksheet('Overview')
    overview.set_column('A:A', 30)
    overview.set_column('B:B', 20)
    
    overview.write('A1', 'Behavior Summary Report', header_format)
    overview.write('A2', 'Tracker:', metric_label_format)
    overview.write('B2', tracker['name'])
    overview.write('A3', 'Generated:', metric_label_format)
    overview.write('B3', datetime.now().strftime('%Y-%m-%d %H:%M'))
    
    overview.write('A5', 'Key Metrics', header_format)
    overview.write('A6', 'Completion Rate:', metric_label_format)
    overview.write('B6', completion['value'], metric_value_format)
    overview.write('C6', '%')
    
    overview.write('A7', 'Current Streak:', metric_label_format)
    overview.write('B7', streaks['value']['current_streak'])
    overview.write('C7', 'days')
    
    overview.write('A8', 'Longest Streak:', metric_label_format)
    overview.write('B8', streaks['value']['longest_streak'])
    overview.write('C8', 'days')
    
    overview.write('A9', 'Consistency Score:', metric_label_format)
    overview.write('B9', consistency['value'], metric_value_format)
    overview.write('C9', '/100')
    
    overview.write('A10', 'Balance Score:', metric_label_format)
    overview.write('B10', balance['value'], metric_value_format)
    overview.write('C10', '/100')
    
    overview.write('A11', 'Effort Index:', metric_label_format)
    overview.write('B11', effort['value'], metric_value_format)
    
    # Sheet 2: Daily Data
    daily_sheet = workbook.add_worksheet('Daily Data')
    daily_data = completion.get('daily_rates', [])
    
    if daily_data:
        daily_sheet.write('A1', 'Date', header_format)
        daily_sheet.write('B1', 'Total Tasks', header_format)
        daily_sheet.write('C1', 'Completed', header_format)
        daily_sheet.write('D1', 'Completion %', header_format)
        
        for i, row in enumerate(daily_data, start=2):
            daily_sheet.write(f'A{i}', str(row['date']))
            daily_sheet.write(f'B{i}', row['total'])
            daily_sheet.write(f'C{i}', row['completed'])
            daily_sheet.write(f'D{i}', row['rate'])
        
        # Add chart
        chart = workbook.add_chart({'type': 'line'})
        chart.add_series({
            'name': 'Completion Rate',
            'categories': f'=\'Daily Data\'!$A$2:$A${len(daily_data)+1}',
            'values': f'=\'Daily Data\'!$D$2:$D${len(daily_data)+1}',
            'line': {'color': '#4CAF50', 'width': 2}
        })
        chart.set_title({'name': 'Completion Rate Over Time'})
        chart.set_x_axis({'name': 'Date'})
        chart.set_y_axis({'name': 'Completion %'})
        chart.set_size({'width': 600, 'height': 300})
        
        overview.insert_chart('A13', chart)
    
    # Sheet 3: Category Balance
    balance_sheet = workbook.add_worksheet('Category Balance')
    category_dist = balance['category_distribution']
    
    if category_dist:
        balance_sheet.write('A1', 'Category', header_format)
        balance_sheet.write('B1', 'Percentage', header_format)
        
        for i, (cat, pct) in enumerate(category_dist.items(), start=2):
            balance_sheet.write(f'A{i}', cat)
            balance_sheet.write(f'B{i}', pct)
        
        # Add pie chart
        pie_chart = workbook.add_chart({'type': 'pie'})
        pie_chart.add_series({
            'name': 'Task Distribution',
            'categories': f'=\'Category Balance\'!$A$2:$A${len(category_dist)+1}',
            'values': f'=\'Category Balance\'!$B$2:$B${len(category_dist)+1}',
        })
        pie_chart.set_title({'name': 'Task Distribution by Category'})
        pie_chart.set_size({'width': 400, 'height': 300})
        
        balance_sheet.insert_chart('D2', pie_chart)
    
    workbook.close()
    return output_path

def export_data(tracker_id: str, format: str = 'csv') -> str:
    """
    Exports tracker data in specified format using tablib.
    
    Args:
        tracker_id: Tracker ID
        format: 'csv', 'json', 'xlsx', 'yaml'
    
    Returns:
        Export data as string (or file path for xlsx)
    """
    import tablib
    from core import crud, analytics
    
    # Fetch completion data
    completion_data = analytics.compute_completion_rate(tracker_id)
    daily_rates = completion_data.get('daily_rates', [])
    
    # Create tablib Dataset
    dataset = tablib.Dataset()
    dataset.headers = ['Date', 'Total Tasks', 'Completed', 'Completion Rate']
    
    for row in daily_rates:
        dataset.append([
            str(row['date']),
            row['total'],
            row['completed'],
            row['rate']
        ])
    
    # Export in requested format
    if format == 'csv':
        return dataset.export('csv')
    elif format == 'json':
        return dataset.export('json')
    elif format == 'xlsx':
        # For xlsx, return the bytes
        return dataset.export('xlsx')
    elif format == 'yaml':
        return dataset.export('yaml')
    else:
        raise ValueError(f"Unsupported format: {format}")

def generate_journey_report(tracker_id: str, output_path: Optional[str] = None) -> Dict:
    """
    Generates "My Journey" timeline from audit logs.
    
    Args:
        tracker_id: Tracker ID
        output_path: Optional path to save HTML/Excel report
    
    Returns:
        {
            'timeline': list of events,
            'summary': narrative summary,
            'milestones': list of milestone events
        }
    """
    from core import crud
    
    # Fetch all audit logs for this tracker
    all_logs = crud.db.fetch_all('AuditLogs')
    
    # Filter for this tracker
    tracker_logs = [
        log for log in all_logs
        if tracker_id in str(log.get('entity_id', '')) or tracker_id in str(log.get('details', ''))
    ]
    
    # Sort by timestamp
    tracker_logs.sort(key=lambda x: x['timestamp'])
    
    # Build timeline
    timeline = []
    milestones = []
    
    for log in tracker_logs:
        event = {
            'timestamp': log['timestamp'],
            'action': log['action_type'],
            'entity': log['entity_type'],
            'details': log.get('details', ''),
            'origin': log.get('origin', 'user')
        }
        timeline.append(event)
        
        # Identify milestones
        if log['action_type'] in ['CREATE', 'BATCH_UPDATE', 'AUTO_FIX']:
            milestones.append(event)
    
    # Generate narrative summary
    summary_lines = []
    summary_lines.append(f"Your journey with this tracker began on {tracker_logs[0]['timestamp'] if tracker_logs else 'unknown'}.")
    summary_lines.append(f"\nYou have {len(timeline)} recorded activities.")
    
    # Count action types
    action_counts = {}
    for log in tracker_logs:
        action = log['action_type']
        action_counts[action] = action_counts.get(action, 0) + 1
    
    summary_lines.append(f"\nBreakdown:")
    for action, count in action_counts.items():
        summary_lines.append(f"  - {action}: {count} times")
    
    summary = '\n'.join(summary_lines)
    
    # If output_path specified, generate Excel report
    if output_path:
        _generate_journey_excel(timeline, milestones, summary, output_path)
    
    return {
        'timeline': timeline,
        'summary': summary,
        'milestones': milestones,
        'total_events': len(timeline)
    }

def _generate_journey_excel(timeline: List[Dict], milestones: List[Dict], summary: str, output_path: str):
    """Generates Excel report for journey timeline."""
    import xlsxwriter
    
    workbook = xlsxwriter.Workbook(output_path)
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#2196F3',
        'font_color': 'white',
        'border': 1
    })
    
    milestone_format = workbook.add_format({
        'bg_color': '#FFF9C4',
        'border': 1
    })
    
    # Timeline sheet
    timeline_sheet = workbook.add_worksheet('Timeline')
    timeline_sheet.set_column('A:A', 20)
    timeline_sheet.set_column('B:B', 15)
    timeline_sheet.set_column('C:C', 20)
    timeline_sheet.set_column('D:D', 40)
    
    timeline_sheet.write('A1', 'Timestamp', header_format)
    timeline_sheet.write('B1', 'Action', header_format)
    timeline_sheet.write('C1', 'Entity', header_format)
    timeline_sheet.write('D1', 'Details', header_format)
    
    milestone_ids = {m['timestamp'] for m in milestones}
    
    for i, event in enumerate(timeline, start=2):
        format_to_use = milestone_format if event['timestamp'] in milestone_ids else None
        timeline_sheet.write(f'A{i}', str(event['timestamp']), format_to_use)
        timeline_sheet.write(f'B{i}', event['action'], format_to_use)
        timeline_sheet.write(f'C{i}', event['entity'], format_to_use)
        timeline_sheet.write(f'D{i}', event['details'], format_to_use)
    
    # Summary sheet
    summary_sheet = workbook.add_worksheet('Summary')
    summary_sheet.set_column('A:A', 80)
    summary_sheet.write('A1', 'My Journey Summary', header_format)
    
    for i, line in enumerate(summary.split('\n'), start=3):
        summary_sheet.write(f'A{i}', line)
    
    workbook.close()

def export_all_notes(tracker_id: str, format: str = 'csv') -> str:
    """
    Exports all notes for a tracker.
    
    Args:
        tracker_id: Tracker ID
        format: 'csv', 'json', 'xlsx'
    
    Returns:
        Exported data as string
    """
    import tablib
    from core import crud
    
    notes = crud.db.fetch_filter('DayNotes', tracker_id=tracker_id)
    
    dataset = tablib.Dataset()
    dataset.headers = ['Date', 'Content', 'Sentiment Score']
    
    for note in notes:
        dataset.append([
            str(note['date']),
            note.get('content', ''),
            note.get('sentiment_score', '')
        ])
    
    if format == 'csv':
        return dataset.export('csv')
    elif format == 'json':
        return dataset.export('json')
    elif format == 'xlsx':
        return dataset.export('xlsx')
    else:
        raise ValueError(f"Unsupported format: {format}")
