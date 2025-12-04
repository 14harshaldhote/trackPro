"""
Synthetic Data Generator for testing behavior analytics.
Creates realistic tracker data with various patterns.
"""
import os
import sys
import uuid
import random
from datetime import date, timedelta

# Setup Django environment
sys.path.append('/Users/harshalsmac/WORK/personal/Tracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackerWeb.settings')

import django
django.setup()

from core.repositories import base_repository as crud

def generate_synthetic_tracker(
    name: str,
    days: int = 60,
    pattern: str = 'mixed',
    include_notes: bool = True
):
    """
    Generates a tracker with synthetic data.
    
    Args:
        name: Tracker name
        days: Number of days to generate
        pattern: 'perfect', 'good', 'inconsistent', 'sparse', 'mixed'
        include_notes: Whether to generate day notes
    
    Returns:
        tracker_id: str
    """
    # Create tracker
    tracker_id = str(uuid.uuid4())
    crud.db.insert('TrackerDefinitions', {
        'tracker_id': tracker_id,
        'name': name,
        'time_mode': 'daily',
        'description': f'Synthetic tracker with {pattern} pattern',
        'created_at': date.today().isoformat()
    })
    
    # Create templates with different categories
    categories = ['Health', 'Work', 'Personal', 'Learning']
    templates = []
    
    for i, category in enumerate(categories):
        template_id = str(uuid.uuid4())
        crud.db.insert('TaskTemplates', {
            'template_id': template_id,
            'tracker_id': tracker_id,
            'description': f'{category} Task {i+1}',
            'is_recurring': True,
            'category': category,
            'weight': random.randint(1, 3)
        })
        templates.append(template_id)
    
    # Generate instances and tasks
    start_date = date.today() - timedelta(days=days)
    
    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        
        # Create instance
        instance_id = str(uuid.uuid4())
        crud.db.insert('TrackerInstances', {
            'instance_id': instance_id,
            'tracker_id': tracker_id,
            'period_start': current_date.isoformat(),
            'period_end': current_date.isoformat(),
            'status': 'active'
        })
        
        # Determine completion based on pattern
        completion_prob = _get_completion_probability(pattern, day_offset, days)
        
        # Create tasks
        for template_id in templates:
            task_id = str(uuid.uuid4())
            
            # Randomly complete based on probability
            completed = random.random() < completion_prob
            
            crud.db.insert('TaskInstances', {
                'task_instance_id': task_id,
                'tracker_instance_id': instance_id,
                'template_id': template_id,
                'description': f'Task for {current_date}',
                'status': 'DONE' if completed else 'TODO',
                'date': current_date.isoformat(),
                'notes': '',
                'metadata': '{}'
            })
        
        # Generate note with sentiment
        if include_notes and random.random() < 0.7:  # 70% of days have notes
            note_id = str(uuid.uuid4())
            note_content = _generate_note(completion_prob, current_date)
            
            crud.db.insert('DayNotes', {
                'note_id': note_id,
                'tracker_id': tracker_id,
                'date': current_date.isoformat(),
                'content': note_content,
                'sentiment_score': None,  # Will be computed by analytics
                'keywords': '[]'
            })
    
    print(f"✅ Generated tracker '{name}' with {days} days of {pattern} data")
    print(f"   Tracker ID: {tracker_id}")
    return tracker_id

def _get_completion_probability(pattern: str, day_offset: int, total_days: int) -> float:
    """Returns completion probability based on pattern type."""
    if pattern == 'perfect':
        return 1.0
    elif pattern == 'good':
        return 0.85
    elif pattern == 'inconsistent':
        # Varies by week
        week = day_offset // 7
        return 0.9 if week % 2 == 0 else 0.4
    elif pattern == 'sparse':
        return 0.3
    elif pattern == 'mixed':
        # Starts high, declines, then recovers
        if day_offset < total_days * 0.3:
            return 0.9
        elif day_offset < total_days * 0.6:
            return 0.5
        else:
            return 0.75
    else:
        return 0.5

def _generate_note(completion_prob: float, current_date: date) -> str:
    """Generates a note with sentiment matching completion."""
    positive_notes = [
        "Feeling great today! Made good progress.",
        "Productive day, accomplished all my goals.",
        "Feeling motivated and energized.",
        "Great sleep last night, ready to tackle the day.",
        "Happy with my consistency this week."
    ]
    
    neutral_notes = [
        "Regular day, nothing special.",
        "Slept 7 hours. Feeling okay.",
        "Completed some tasks.",
        "Normal energy levels today.",
        "Just another day."
    ]
    
    negative_notes = [
        "Feeling a bit overwhelmed today.",
        "Struggled to focus, low energy.",
        "Didn't sleep well, only 5 hours.",
        "Feeling stressed about work.",
        "Tired and unmotivated."
    ]
    
    if completion_prob > 0.7:
        return random.choice(positive_notes)
    elif completion_prob > 0.4:
        return random.choice(neutral_notes)
    else:
        return random.choice(negative_notes)

def generate_all_patterns():
    """Generates trackers with all pattern types for testing."""
    patterns = {
        'Perfect Tracker': 'perfect',
        'Good Tracker': 'good',
        'Inconsistent Tracker': 'inconsistent',
        'Sparse Tracker': 'sparse',
        'Mixed Tracker': 'mixed'
    }
    
    tracker_ids = {}
    for name, pattern in patterns.items():
        tracker_id = generate_synthetic_tracker(name, days=60, pattern=pattern)
        tracker_ids[name] = tracker_id
    
    return tracker_ids

if __name__ == '__main__':
    print("🧪 Generating synthetic tracker data...")
    print("=" * 60)
    
    tracker_ids = generate_all_patterns()
    
    print("\n" + "=" * 60)
    print("🎉 Synthetic data generation complete!")
    print("\nGenerated trackers:")
    for name, tid in tracker_ids.items():
        print(f"  - {name}: {tid}")
