"""
Training Data Exporter

Exports clean, labeled datasets for future AI training.
Prepares behavior samples, audit logs, and event sequences in CSV format.

No AI used - just creates training-ready data exports.
"""
import csv
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import json
import logging

from core.models import (
    TrackerDefinition, TrackerInstance, TaskInstance, 
    TaskTemplate, DayNote
)
from core import analytics
from core.helpers import nlp_helpers

logger = logging.getLogger(__name__)


def export_behavior_samples(
    tracker_id: str,
    output_path: str,
    days: int = 60
) -> Dict:
    """
    Export behavior samples with features and labels for ML training.
    
    Creates a CSV with daily behavior features:
    - completion_rate: % of tasks completed
    - streak_active: 1 if in a streak, 0 otherwise
    - day_of_week: 0-6 (Monday-Sunday)
    - is_weekend: 1 or 0
    - sentiment_score: -1 to 1 if note exists
    - task_count: number of tasks scheduled
    - completed_count: number completed
    - category_balance: entropy score
    
    Args:
        tracker_id: Tracker to export
        output_path: Path to write CSV
        days: Number of days to include
        
    Returns:
        Dict with export stats
    """
    tracker = TrackerDefinition.objects.filter(tracker_id=tracker_id).first()
    if not tracker:
        return {'error': 'Tracker not found', 'rows': 0}
    
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Get instances
    instances = TrackerInstance.objects.filter(
        tracker_id=tracker_id,
        tracking_date__gte=start_date,
        tracking_date__lte=end_date
    ).order_by('tracking_date')
    
    # Get notes for sentiment
    notes = {n.date: n for n in DayNote.objects.filter(
        tracker_id=tracker_id,
        date__gte=start_date,
        date__lte=end_date
    )}
    
    # Build samples
    rows = []
    streak_count = 0
    
    for instance in instances:
        inst_date = instance.tracking_date
        
        # Get tasks for this instance
        tasks = TaskInstance.objects.filter(tracker_instance=instance)
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='DONE').count()
        
        # Calculate completion rate
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Update streak
        if completion_rate >= 80:
            streak_count += 1
        else:
            streak_count = 0
        
        # Get sentiment from note if exists
        sentiment = 0.0
        note = notes.get(inst_date)
        if note and note.sentiment_score is not None:
            sentiment = note.sentiment_score
        elif note and note.content:
            # Compute sentiment if not cached
            sentiment_result = nlp_helpers.analyze_sentiment(note.content)
            sentiment = sentiment_result.get('compound', 0)
        
        # Category balance for the day
        categories = {}
        for task in tasks:
            cat = task.template.category or 'Uncategorized'
            categories[cat] = categories.get(cat, 0) + 1
        
        # Simple balance: 1 if evenly distributed, lower if imbalanced
        if categories:
            total = sum(categories.values())
            proportions = [c / total for c in categories.values()]
            balance = 1 - max(proportions)  # Higher = more balanced
        else:
            balance = 0
        
        row = {
            'date': inst_date.isoformat(),
            'day_of_week': inst_date.weekday(),
            'is_weekend': 1 if inst_date.weekday() >= 5 else 0,
            'task_count': total_tasks,
            'completed_count': completed_tasks,
            'completion_rate': round(completion_rate, 2),
            'streak_active': 1 if streak_count > 0 else 0,
            'streak_length': streak_count,
            'sentiment_score': round(sentiment, 3),
            'category_balance': round(balance, 3),
            'has_note': 1 if note else 0
        }
        rows.append(row)
    
    # Write CSV
    if rows:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Exported {len(rows)} behavior samples to {output_path}")
    
    return {
        'tracker_id': tracker_id,
        'tracker_name': tracker.name,
        'rows_exported': len(rows),
        'date_range': f"{start_date} to {end_date}",
        'output_path': output_path
    }


def export_history_timeline(
    tracker_id: str,
    output_path: str
) -> Dict:
    """
    Export model change history from django-simple-history.
    
    Creates a CSV of all historical changes for audit/training:
    - timestamp
    - model_type
    - action (created/changed/deleted)
    - field_changes (JSON)
    - user_id
    
    Args:
        tracker_id: Tracker to export history for
        output_path: Path to write CSV
        
    Returns:
        Dict with export stats
    """
    from core.models import TrackerDefinition, TaskInstance, DayNote
    
    rows = []
    
    # Get tracker history
    tracker = TrackerDefinition.objects.filter(tracker_id=tracker_id).first()
    if not tracker:
        return {'error': 'Tracker not found', 'rows': 0}
    
    # Export TrackerDefinition history
    for hist in tracker.history.all():
        rows.append({
            'timestamp': hist.history_date.isoformat(),
            'model_type': 'TrackerDefinition',
            'entity_id': str(tracker.tracker_id),
            'action': hist.history_type,
            'user_id': hist.history_user_id or 'system',
            'changes': json.dumps({
                'name': hist.name,
                'time_mode': hist.time_mode
            })
        })
    
    # Export TaskInstance history for this tracker
    instances = TrackerInstance.objects.filter(tracker_id=tracker_id)
    for instance in instances:
        tasks = TaskInstance.objects.filter(tracker_instance=instance)
        for task in tasks:
            for hist in task.history.all():
                rows.append({
                    'timestamp': hist.history_date.isoformat(),
                    'model_type': 'TaskInstance',
                    'entity_id': str(task.task_instance_id),
                    'action': hist.history_type,
                    'user_id': hist.history_user_id or 'system',
                    'changes': json.dumps({
                        'status': hist.status,
                        'notes': hist.notes[:100] if hist.notes else ''
                    })
                })
    
    # Export DayNote history
    notes = DayNote.objects.filter(tracker_id=tracker_id)
    for note in notes:
        for hist in note.history.all():
            rows.append({
                'timestamp': hist.history_date.isoformat(),
                'model_type': 'DayNote',
                'entity_id': str(note.note_id),
                'action': hist.history_type,
                'user_id': hist.history_user_id or 'system',
                'changes': json.dumps({
                    'sentiment_score': hist.sentiment_score,
                    'content_length': len(hist.content) if hist.content else 0
                })
            })
    
    # Sort by timestamp
    rows.sort(key=lambda x: x['timestamp'])
    
    # Write CSV
    if rows:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Exported {len(rows)} history events to {output_path}")
    
    return {
        'tracker_id': tracker_id,
        'rows_exported': len(rows),
        'output_path': output_path
    }


def export_insights_dataset(
    output_path: str
) -> Dict:
    """
    Export insights generated across all trackers for analysis.
    
    Creates a CSV of all insights with their evidence and outcomes.
    Useful for analyzing which insights are most common/useful.
    
    Args:
        output_path: Path to write CSV
        
    Returns:
        Dict with export stats
    """
    from core.behavioral import get_insights
    
    rows = []
    trackers = TrackerDefinition.objects.all()
    
    for tracker in trackers:
        try:
            insights = get_insights(str(tracker.tracker_id))
            
            for insight in insights:
                rows.append({
                    'tracker_id': str(tracker.tracker_id),
                    'tracker_name': tracker.name,
                    'insight_type': insight['type'],
                    'severity': insight['severity'],
                    'title': insight['title'],
                    'confidence': insight['confidence'],
                    'evidence': json.dumps(insight['evidence']),
                    'generated_at': datetime.now().isoformat()
                })
        except Exception as e:
            logger.warning(f"Could not generate insights for {tracker.tracker_id}: {e}")
    
    # Write CSV
    if rows:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Exported {len(rows)} insights to {output_path}")
    
    return {
        'total_trackers': trackers.count(),
        'total_insights': len(rows),
        'output_path': output_path
    }


def export_all_training_data(base_dir: str = None) -> Dict:
    """
    Export all training datasets to a directory.
    
    Creates:
    - behavior_samples_{tracker_id}.csv for each tracker
    - history_timeline_{tracker_id}.csv for each tracker
    - insights_dataset.csv (all trackers)
    
    Args:
        base_dir: Base directory for exports (default: exports/)
        
    Returns:
        Dict with all export stats
    """
    if base_dir is None:
        base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'exports', 'training_data')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = os.path.join(base_dir, timestamp)
    os.makedirs(export_dir, exist_ok=True)
    
    results = {
        'export_dir': export_dir,
        'timestamp': timestamp,
        'behavior_samples': [],
        'history_timelines': [],
        'insights': None
    }
    
    # Export per-tracker data
    trackers = TrackerDefinition.objects.all()
    for tracker in trackers:
        tid = str(tracker.tracker_id)[:8]  # Short ID
        
        # Behavior samples
        behavior_path = os.path.join(export_dir, f'behavior_{tid}.csv')
        behavior_result = export_behavior_samples(str(tracker.tracker_id), behavior_path)
        results['behavior_samples'].append(behavior_result)
        
        # History timeline
        history_path = os.path.join(export_dir, f'history_{tid}.csv')
        history_result = export_history_timeline(str(tracker.tracker_id), history_path)
        results['history_timelines'].append(history_result)
    
    # Export insights dataset
    insights_path = os.path.join(export_dir, 'insights_all.csv')
    results['insights'] = export_insights_dataset(insights_path)
    
    logger.info(f"Exported all training data to {export_dir}")
    
    return results
