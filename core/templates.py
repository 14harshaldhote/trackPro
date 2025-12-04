from core.repositories import base_repository as crud
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

# ============================================================================
# GOAL → ROUTINE MAPPINGS (Goal-based routine builder)
# ============================================================================

GOAL_ROUTINE_MAPPINGS = {
    'lose_weight': {
        'description': 'Lose weight and get healthier',
        'templates': [
            {'description': 'Exercise 30+ minutes', 'category': 'fitness', 'weight': 4},
            {'description': 'Track calorie intake', 'category': 'nutrition', 'weight': 2},
            {'description': 'Drink 8 glasses of water', 'category': 'health', 'weight': 1},
            {'description': 'No late-night snacking', 'category': 'nutrition', 'weight': 2},
            {'description': 'Sleep 7-8 hours', 'category': 'recovery', 'weight': 3},
        ]
    },
    'improve_fitness': {
        'description': 'Improve overall fitness level',
        'templates': [
            {'description': 'Morning workout (45 mins)', 'category': 'workout', 'weight': 5},
            {'description': 'Protein target met (1.5g/kg)', 'category': 'nutrition', 'weight': 3},
            {'description': 'Stretching / Mobility', 'category': 'recovery', 'weight': 2},
            {'description': 'Track workout progress', 'category': 'tracking', 'weight': 1},
            {'description': 'Active recovery day', 'category': 'recovery', 'weight': 2},
        ]
    },
    'reduce_stress': {
        'description': 'Reduce stress and improve mental health',
        'templates': [
            {'description': 'Morning meditation (15 mins)', 'category': 'mindfulness', 'weight': 3},
            {'description': 'Digital detox (1 hour)', 'category': 'wellness', 'weight': 2},
            {'description': 'Gratitude journaling', 'category': 'mindfulness', 'weight': 2},
            {'description': 'Nature walk / outdoor time', 'category': 'wellness', 'weight': 2},
            {'description': 'Deep breathing exercises', 'category': 'mindfulness', 'weight': 1},
        ]
    },
    'learn_coding': {
        'description': 'Learn programming and software development',
        'templates': [
            {'description': 'Practice coding (1 hour)', 'category': 'practice', 'weight': 4},
            {'description': 'Read documentation / tutorials', 'category': 'learning', 'weight': 2},
            {'description': 'Build side project', 'category': 'projects', 'weight': 3},
            {'description': 'Review and refactor code', 'category': 'review', 'weight': 2},
            {'description': 'Solve 1 algorithm problem', 'category': 'practice', 'weight': 3},
        ]
    },
    'read_more': {
        'description': 'Develop a reading habit',
        'templates': [
            {'description': 'Read 20+ pages', 'category': 'reading', 'weight': 3},
            {'description': 'Take notes on key concepts', 'category': 'notes', 'weight': 2},
            {'description': 'No phone before reading', 'category': 'focus', 'weight': 1},
            {'description': 'Review yesterday\'s highlights', 'category': 'review', 'weight': 1},
        ]
    },
    'save_money': {
        'description': 'Build savings and financial discipline',
        'templates': [
            {'description': 'Track all expenses', 'category': 'tracking', 'weight': 2},
            {'description': 'No impulse purchases', 'category': 'discipline', 'weight': 3},
            {'description': 'Transfer to savings', 'category': 'savings', 'weight': 3},
            {'description': 'Review budget status', 'category': 'review', 'weight': 1},
            {'description': 'Meal prep (avoid eating out)', 'category': 'savings', 'weight': 2},
        ]
    },
    'wake_early': {
        'description': 'Become a morning person',
        'templates': [
            {'description': 'In bed by 10 PM', 'category': 'sleep', 'weight': 3},
            {'description': 'No caffeine after 2 PM', 'category': 'health', 'weight': 2},
            {'description': 'Wake at alarm (no snooze)', 'category': 'discipline', 'weight': 4},
            {'description': 'Morning sunlight (10 mins)', 'category': 'health', 'weight': 2},
            {'description': 'No screens 1h before bed', 'category': 'sleep', 'weight': 2},
        ]
    },
    'improve_focus': {
        'description': 'Improve concentration and productivity',
        'templates': [
            {'description': 'Deep work block (90 mins)', 'category': 'focus', 'weight': 5},
            {'description': 'Phone on DND during work', 'category': 'discipline', 'weight': 2},
            {'description': 'Single-task (no multitasking)', 'category': 'focus', 'weight': 3},
            {'description': 'Take proper breaks', 'category': 'recovery', 'weight': 1},
            {'description': 'Plan tomorrow\'s priorities', 'category': 'planning', 'weight': 2},
        ]
    },
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


def initialize_goal_routine(user, goal_key: str, tracker_id: str):
    """
    Creates a Goal and links it to task templates based on goal-routine mappings.
    
    Args:
        user: Django User object
        goal_key: Key from GOAL_ROUTINE_MAPPINGS (e.g., 'lose_weight')
        tracker_id: Tracker ID to create templates in
        
    Returns:
        {
            'goal': Goal object,
            'templates': list of created TaskTemplate objects,
            'mappings': list of GoalTaskMapping objects
        }
    """
    from core.models import Goal, TaskTemplate, GoalTaskMapping
    
    if goal_key not in GOAL_ROUTINE_MAPPINGS:
        raise ValueError(f"Unknown goal key: {goal_key}. Available: {list(GOAL_ROUTINE_MAPPINGS.keys())}")
    
    goal_config = GOAL_ROUTINE_MAPPINGS[goal_key]
    
    # Create Goal
    goal = Goal.objects.create(
        user=user,
        title=goal_config['description'],
        description=f"Auto-generated goal from template: {goal_key}",
        status='active',
        priority='medium'
    )
    
    created_templates = []
    mappings = []
    
    # Create templates and link them to goal
    for tmpl_data in goal_config['templates']:
        template = TaskTemplate.objects.create(
            tracker_id=tracker_id,
            description=tmpl_data['description'],
            category=tmpl_data['category'],
            weight=tmpl_data['weight'],
            is_recurring=True
        )
        created_templates.append(template)
        
        # Create mapping: Goal ← Template
        mapping = GoalTaskMapping.objects.create(
            goal=goal,
            template=template,
            contribution_weight=tmpl_data['weight']
        )
        mappings.append(mapping)
    
    return {
        'goal': goal,
        'templates': created_templates,
        'mappings': mappings
    }


def get_available_goal_templates():
    """Returns list of available goal templates for UI dropdown."""
    return [
        {
            'key': key,
            'title': config['description'],
            'task_count': len(config['templates'])
        }
        for key, config in GOAL_ROUTINE_MAPPINGS.items()
    ]

