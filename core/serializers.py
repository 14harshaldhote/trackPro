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
    
    def validate_name(self, value):
        """Ensure name is not empty and has minimum length"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Name must be at least 3 characters long"
            )
        return value.strip()


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
        help_text="Task difficulty/importance (1-10)"
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


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Validate task status updates"""
    
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
        ('MISSED', 'Missed'),
        ('BLOCKED', 'Blocked'),
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
