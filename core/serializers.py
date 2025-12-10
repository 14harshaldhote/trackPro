"""
Input Validation Serializers

Provides validation for user input using Django REST Framework serializers.
Ensures data integrity before it reaches the database.
"""
from rest_framework import serializers
from datetime import date


class TrackerCreateSerializer(serializers.Serializer):
    """Validate tracker creation data"""
    
    TIME_MODE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    GOAL_PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom'),
    ]
    
    name = serializers.CharField(
        max_length=200,
        required=True,
        help_text="Tracker name (e.g., 'Daily Habits')"
    )
    
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional description"
    )
    
    time_mode = serializers.ChoiceField(
        choices=TIME_MODE_CHOICES,
        default='daily',
        help_text="Tracking frequency"
    )
    
    # Goal Configuration
    target_points = serializers.IntegerField(
        min_value=0,
        default=0,
        required=False,
        help_text="Target points for the goal (0 = no goal set)"
    )
    
    goal_period = serializers.ChoiceField(
        choices=GOAL_PERIOD_CHOICES,
        default='daily',
        required=False,
        help_text="Period for goal reset (daily/weekly/custom)"
    )
    
    goal_start_day = serializers.IntegerField(
        min_value=0,
        max_value=6,
        default=0,
        required=False,
        help_text="Start day for weekly goals (0=Monday, 6=Sunday)"
    )
    
    def validate_name(self, value):
        """Ensure name is not empty and has minimum length"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Name must be at least 3 characters long"
            )
        return value.strip()


class TrackerGoalSerializer(serializers.Serializer):
    """Validate tracker goal update data"""
    
    GOAL_PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom'),
    ]
    
    target_points = serializers.IntegerField(
        min_value=0,
        required=False,
        help_text="Target points for the goal (0 = no goal set)"
    )
    
    goal_period = serializers.ChoiceField(
        choices=GOAL_PERIOD_CHOICES,
        required=False,
        help_text="Period for goal reset (daily/weekly/custom)"
    )
    
    goal_start_day = serializers.IntegerField(
        min_value=0,
        max_value=6,
        required=False,
        help_text="Start day for weekly goals (0=Monday, 6=Sunday)"
    )


class TaskToggleGoalSerializer(serializers.Serializer):
    """Validate task goal toggle request"""
    
    include = serializers.BooleanField(
        required=True,
        help_text="Whether to include task points in goal calculation"
    )


class TaskPointsUpdateSerializer(serializers.Serializer):
    """Validate task points update request"""
    
    points = serializers.IntegerField(
        min_value=0,
        max_value=1000,
        required=True,
        help_text="Points awarded when task is completed"
    )


class TaskTemplateSerializer(serializers.Serializer):
    """Validate task template data"""
    
    description = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Task description"
    )
    
    category = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Task category (e.g., 'Health', 'Work')"
    )
    
    weight = serializers.IntegerField(
        min_value=1,
        max_value=10,
        default=1,
        help_text="Task priority/ordering weight (1-10)"
    )
    
    points = serializers.IntegerField(
        min_value=0,
        max_value=1000,
        default=1,
        required=False,
        help_text="Points awarded when task is completed"
    )
    
    include_in_goal = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Whether this task's points count towards the tracker goal"
    )
    
    is_recurring = serializers.BooleanField(
        default=True,
        help_text="Whether task repeats daily"
    )
    
    def validate_description(self, value):
        """Ensure description is meaningful"""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Description must be at least 2 characters"
            )
        return value.strip()
    
    def validate_weight(self, value):
        """Ensure weight is in valid range"""
        if value < 1 or value > 10:
            raise serializers.ValidationError(
                "Weight must be between 1 and 10"
            )
        return value
    
    def validate_points(self, value):
        """Ensure points is non-negative"""
        if value < 0:
            raise serializers.ValidationError(
                "Points must be 0 or greater"
            )
        return value


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Validate task status updates"""
    
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
        ('MISSED', 'Missed'),
        ('BLOCKED', 'Blocked'),
        ('SKIPPED', 'Skipped'),  # ← Added for test TASK_011
    ]
    
    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        required=True,
        help_text="New task status"
    )
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about the task"
    )
    
    def validate_status(self, value):
        """Ensure status is valid"""
        valid_statuses = [choice[0] for choice in self.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value


class BulkStatusUpdateSerializer(serializers.Serializer):
    """Validate bulk task status updates"""
    
    STATUS_CHOICES = TaskStatusUpdateSerializer.STATUS_CHOICES
    
    task_ids = serializers.ListField(
        child=serializers.CharField(max_length=36),
        required=True,
        min_length=1,
        help_text="List of task IDs to update"
    )
    
    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        required=True,
        help_text="Status to apply to all tasks"
    )
    
    def validate_task_ids(self, value):
        """Ensure task IDs list is not empty"""
        if not value:
            raise serializers.ValidationError("At least one task ID is required")
        return value


class DateRangeSerializer(serializers.Serializer):
    """Validate date range inputs"""
    
    start_date = serializers.DateField(
        required=True,
        help_text="Start date (YYYY-MM-DD)"
    )
    
    end_date = serializers.DateField(
        required=True,
        help_text="End date (YYYY-MM-DD)"
    )
    
    def validate(self, data):
        """Ensure end date is after start date"""
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError(
                "End date must be after start date"
            )
        
        # Prevent excessively long date ranges
        delta = (data['end_date'] - data['start_date']).days
        if delta > 365:
            raise serializers.ValidationError(
                "Date range cannot exceed 365 days"
            )
        
        return data


class DayNoteSerializer(serializers.Serializer):
    """Validate day note input"""
    
    date = serializers.DateField(
        required=True,
        help_text="Date of the note"
    )
    
    content = serializers.CharField(
        required=True,
        min_length=1,
        max_length=5000,
        help_text="Note content"
    )
    
    def validate_content(self, value):
        """Ensure content is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Note content cannot be empty")
        return value.strip()
    
    def validate_date(self, value):
        """Ensure date is not in the future"""
        if value > date.today():
            raise serializers.ValidationError("Cannot create notes for future dates")
        return value


class AnalyticsParametersSerializer(serializers.Serializer):
    """Validate analytics query parameters"""
    
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    
    window_days = serializers.IntegerField(
        min_value=1,
        max_value=90,
        default=7,
        help_text="Rolling window size in days"
    )
    
    metric = serializers.ChoiceField(
        choices=[
            ('completion_rate', 'Completion Rate'),
            ('mood', 'Mood/Sentiment'),
            ('effort', 'Effort Index'),
        ],
        default='completion_rate',
        required=False
    )
    
    forecast_days = serializers.IntegerField(
        min_value=1,
        max_value=30,
        default=7,
        help_text="Number of days to forecast"
    )
    
    def validate(self, data):
        """Validate date range if both dates provided"""
        if data.get('start_date') and data.get('end_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "End date must be after start date"
                )
        return data


# ============================================================================
# NEW SERIALIZERS: Tags, Goals, Preferences
# ============================================================================

class TagSerializer(serializers.Serializer):
    """Validate tag creation/update data"""
    
    name = serializers.CharField(
        max_length=50,
        required=True,
        help_text="Tag name"
    )
    
    color = serializers.RegexField(
        regex=r'^#[0-9A-Fa-f]{6}$',
        required=False,
        default='#6366f1',
        help_text="Hex color code (e.g., #6366f1)"
    )
    
    icon = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Emoji or icon name"
    )
    
    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Tag name must be at least 2 characters")
        return value.strip()


class GoalSerializer(serializers.Serializer):
    """Validate goal creation/update data"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('achieved', 'Achieved'),
        ('paused', 'Paused'),
        ('abandoned', 'Abandoned'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = serializers.CharField(
        max_length=200,
        required=True,
        help_text="Goal title"
    )
    
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Goal description"
    )
    
    target_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Target completion date"
    )
    
    status = serializers.ChoiceField(
        choices=STATUS_CHOICES,
        default='active'
    )
    
    priority = serializers.ChoiceField(
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    def validate_title(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters")
        return value.strip()


class GoalTaskMappingSerializer(serializers.Serializer):
    """Validate goal-task mapping data"""
    
    goal_id = serializers.CharField(
        max_length=36,
        required=True,
        help_text="Goal ID"
    )
    
    template_id = serializers.CharField(
        max_length=36,
        required=True,
        help_text="Task Template ID"
    )
    
    contribution_weight = serializers.FloatField(
        min_value=0.1,
        max_value=10.0,
        default=1.0,
        help_text="Weight of this task's contribution to goal"
    )
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Notes about this mapping"
    )


class EntityRelationSerializer(serializers.Serializer):
    """Validate entity relation (knowledge graph edge) data"""
    
    RELATION_TYPES = [
        ('done_on', 'Done On'),
        ('blocked_by', 'Blocked By'),
        ('related_to', 'Related To'),
        ('depends_on', 'Depends On'),
        ('inspired_by', 'Inspired By'),
        ('replaces', 'Replaces'),
    ]
    
    ENTITY_TYPES = [
        ('task', 'Task Instance'),
        ('template', 'Task Template'),
        ('tracker', 'Tracker'),
        ('note', 'Day Note'),
        ('goal', 'Goal'),
    ]
    
    from_entity_type = serializers.ChoiceField(
        choices=ENTITY_TYPES,
        required=True
    )
    
    from_entity_id = serializers.CharField(
        max_length=36,
        required=True
    )
    
    to_entity_type = serializers.ChoiceField(
        choices=ENTITY_TYPES,
        required=True
    )
    
    to_entity_id = serializers.CharField(
        max_length=36,
        required=True
    )
    
    relation_type = serializers.ChoiceField(
        choices=RELATION_TYPES,
        required=True
    )
    
    metadata = serializers.JSONField(
        required=False,
        default=dict
    )


class UserPreferencesSerializer(serializers.Serializer):
    """Validate user preferences data"""
    
    VIEW_CHOICES = [
        ('day', 'Day View'),
        ('week', 'Week View'),
        ('month', 'Month View'),
    ]
    
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'System Default'),
    ]
    
    # Notifications
    daily_reminder_enabled = serializers.BooleanField(default=True)
    daily_reminder_time = serializers.TimeField(required=False, allow_null=True)
    weekly_review_enabled = serializers.BooleanField(default=True)
    weekly_review_day = serializers.IntegerField(min_value=0, max_value=6, default=0)
    
    # Display
    default_view = serializers.ChoiceField(choices=VIEW_CHOICES, default='week')
    theme = serializers.ChoiceField(choices=THEME_CHOICES, default='light')
    show_completed_tasks = serializers.BooleanField(default=True)
    
    # Analytics
    streak_threshold = serializers.IntegerField(min_value=50, max_value=100, default=80)
    consistency_window = serializers.IntegerField(min_value=3, max_value=30, default=7)
    
    # Privacy
    public_profile = serializers.BooleanField(default=False)
    share_streaks = serializers.BooleanField(default=False)


class GoalRoutineInitSerializer(serializers.Serializer):
    """Validate goal routine initialization request"""
    
    goal_key = serializers.ChoiceField(
        choices=[
            ('lose_weight', 'Lose Weight'),
            ('improve_fitness', 'Improve Fitness'),
            ('reduce_stress', 'Reduce Stress'),
            ('learn_coding', 'Learn Coding'),
            ('read_more', 'Read More'),
            ('save_money', 'Save Money'),
            ('wake_early', 'Wake Early'),
            ('improve_focus', 'Improve Focus'),
        ],
        required=True,
        help_text="Goal template key"
    )
    
    tracker_id = serializers.CharField(
        max_length=36,
        required=True,
        help_text="Tracker to create templates in"
    )

