from core import crud
import uuid

PREDEFINED_TEMPLATES = {
    'productivity': [
        {'description': 'Plan the day (Top 3 tasks)', 'category': 'planning', 'weight': 1},
        {'description': 'Deep Work Session (90 mins)', 'category': 'focus', 'weight': 3},
        {'description': 'Clear Inbox/Messages', 'category': 'admin', 'weight': 1},
        {'description': 'Review goals', 'category': 'planning', 'weight': 1},
    ],
    'wellbeing': [
        {'description': 'Morning Meditation (10 mins)', 'category': 'mindfulness', 'weight': 2},
        {'description': 'Drink 2L Water', 'category': 'health', 'weight': 1},
        {'description': 'No screens 1h before bed', 'category': 'sleep', 'weight': 2},
        {'description': 'Gratitude Journal', 'category': 'mindfulness', 'weight': 1},
    ],
    'fitness': [
        {'description': 'Warm-up / Mobility', 'category': 'warmup', 'weight': 1},
        {'description': 'Main Workout', 'category': 'workout', 'weight': 5},
        {'description': 'Protein intake met', 'category': 'nutrition', 'weight': 2},
        {'description': 'Stretching / Cool down', 'category': 'recovery', 'weight': 1},
    ],
    'study': [
        {'description': 'Review previous notes', 'category': 'review', 'weight': 1},
        {'description': 'Active Recall Session', 'category': 'learning', 'weight': 3},
        {'description': 'Practice Problems', 'category': 'practice', 'weight': 3},
        {'description': 'Summarize key concepts', 'category': 'synthesis', 'weight': 2},
    ]
}

def initialize_templates(tracker_id, category):
    """
    Initializes a tracker with predefined templates from a category.
    """
    if category not in PREDEFINED_TEMPLATES:
        return []
        
    created_templates = []
    for tmpl_data in PREDEFINED_TEMPLATES[category]:
        data = tmpl_data.copy()
        data['tracker_id'] = tracker_id
        data['template_id'] = str(uuid.uuid4())
        # Defaults
        data['is_recurring'] = True
        
        created = crud.create_task_template(data)
        created_templates.append(created)
        
    return created_templates
