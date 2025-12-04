from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords
import uuid


class TrackerDefinition(models.Model):
    """Main tracker definition - what you're tracking (e.g., Daily Habits, Weekly Goals)"""
    
    TIME_MODE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    tracker_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='trackers', null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    time_mode = models.CharField(max_length=20, choices=TIME_MODE_CHOICES, default='daily')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit history - tracks all changes with user attribution
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'tracker_definitions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'time_mode']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['time_mode']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.time_mode})"


class TaskTemplate(models.Model):
    """Template for tasks within a tracker (e.g., Exercise, Meditate, Read)"""
    
    template_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    tracker = models.ForeignKey(TrackerDefinition, on_delete=models.CASCADE, related_name='templates')
    description = models.CharField(max_length=500)
    is_recurring = models.BooleanField(default=True)
    category = models.CharField(max_length=100, blank=True, default='')
    weight = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Audit history
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'task_templates'
        ordering = ['tracker', 'description']
        indexes = [
            models.Index(fields=['tracker', 'category']),
        ]
    
    def __str__(self):
        return f"{self.description} ({self.tracker.name})"


class TrackerInstance(models.Model):
    """Specific instance of tracking for a particular date/period"""
    
    instance_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    tracker = models.ForeignKey(TrackerDefinition, on_delete=models.CASCADE, related_name='instances')
    tracking_date = models.DateField()
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Audit history
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'tracker_instances'
        unique_together = [['tracker', 'tracking_date']]
        ordering = ['-tracking_date']
        indexes = [
            # Date range queries (optimized for get_day_grid_data)
            models.Index(fields=['tracker', 'tracking_date', 'status'], name='instance_date_lookup'),
            models.Index(fields=['tracker', '-tracking_date'], name='instance_recent'),
            
            # Single field indexes
            models.Index(fields=['tracking_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.tracker.name} - {self.tracking_date}"


class TaskInstance(models.Model):
    """Actual task completion record for a specific date"""
    
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
        ('MISSED', 'Missed'),
        ('BLOCKED', 'Blocked'),
    ]
    
    task_instance_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    tracker_instance = models.ForeignKey(TrackerInstance, on_delete=models.CASCADE, related_name='tasks')
    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, related_name='instances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    notes = models.TextField(blank=True, default='')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit history - critical for tracking task status changes
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'task_instances'
        ordering = ['-created_at']
        indexes = [
            # Optimized for grid queries (get_day_grid_data)
            models.Index(fields=['tracker_instance', 'template', 'status'], name='task_grid_lookup'),
            
            # Analytics queries
            models.Index(fields=['status', 'completed_at'], name='task_analytics'),
            models.Index(fields=['template', 'status'], name='task_template_status'),
            
            # Single field indexes
            models.Index(fields=['tracker_instance']),
            models.Index(fields=['template']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.template.description} - {self.status}"
    
    def mark_done(self):
        """Helper method to mark task as done"""
        self.status = 'DONE'
        self.completed_at = timezone.now()
        self.save()


class DayNote(models.Model):
    """Daily notes/journal entries for a tracker"""
    
    note_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    tracker = models.ForeignKey(TrackerDefinition, on_delete=models.CASCADE, related_name='notes')
    date = models.DateField()
    content = models.TextField()
    sentiment_score = models.FloatField(null=True, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit history - tracks journal edits
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'day_notes'
        unique_together = [['tracker', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['tracker', 'date']),
        ]
    
    def __str__(self):
        return f"Note for {self.tracker.name} on {self.date}"


# ============================================================================
# NEW MODELS: Tags, Goals, UserPreferences, Knowledge Graph
# ============================================================================

class Tag(models.Model):
    """User-defined tags for organizing tasks and trackers."""
    
    tag_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='tags')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#6366f1')  # hex color
    icon = models.CharField(max_length=50, blank=True, default='')  # emoji or icon name
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tags'
        unique_together = [['user', 'name']]
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TaskTemplateTag(models.Model):
    """Many-to-many relationship between TaskTemplates and Tags."""
    
    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, related_name='task_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='tagged_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_template_tags'
        unique_together = [['template', 'tag']]
    
    def __str__(self):
        return f"{self.template.description} - {self.tag.name}"


class Goal(models.Model):
    """User goals that tasks contribute towards."""
    
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
    
    goal_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    progress = models.FloatField(default=0.0)  # 0-100%
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit history
    history = HistoricalRecords()
    
    class Meta:
        db_table = 'goals'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.status})"
    
    def update_progress(self):
        """Calculate progress based on linked task completions."""
        mappings = self.task_mappings.all()
        if not mappings.exists():
            return
        
        total_weight = sum(m.contribution_weight for m in mappings)
        weighted_completion = 0
        
        for mapping in mappings:
            # Get completion rate for this template
            total = mapping.template.instances.count()
            done = mapping.template.instances.filter(status='DONE').count()
            if total > 0:
                completion_rate = done / total
                weighted_completion += completion_rate * mapping.contribution_weight
        
        self.progress = (weighted_completion / total_weight * 100) if total_weight > 0 else 0
        self.save(update_fields=['progress', 'updated_at'])


class GoalTaskMapping(models.Model):
    """Links Goals to TaskTemplates with contribution weights."""
    
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name='task_mappings')
    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, related_name='goal_mappings')
    contribution_weight = models.FloatField(default=1.0)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'goal_task_mappings'
        unique_together = [['goal', 'template']]
    
    def __str__(self):
        return f"{self.goal.title} <- {self.template.description}"


class EntityRelation(models.Model):
    """Knowledge Graph edges: relationships between entities."""
    
    RELATION_TYPES = [
        ('done_on', 'Done On'),  # task → date
        ('blocked_by', 'Blocked By'),  # task → task/note
        ('related_to', 'Related To'),  # generic relation
        ('depends_on', 'Depends On'),  # task → task
        ('inspired_by', 'Inspired By'),  # task → note/goal
        ('replaces', 'Replaces'),  # task → task
    ]
    
    ENTITY_TYPES = [
        ('task', 'Task Instance'),
        ('template', 'Task Template'),
        ('tracker', 'Tracker'),
        ('note', 'Day Note'),
        ('goal', 'Goal'),
    ]
    
    relation_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='relations')
    
    from_entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    from_entity_id = models.CharField(max_length=36)
    
    to_entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    to_entity_id = models.CharField(max_length=36)
    
    relation_type = models.CharField(max_length=20, choices=RELATION_TYPES)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'entity_relations'
        indexes = [
            models.Index(fields=['from_entity_type', 'from_entity_id']),
            models.Index(fields=['to_entity_type', 'to_entity_id']),
            models.Index(fields=['relation_type']),
            models.Index(fields=['user', 'relation_type']),
        ]
    
    def __str__(self):
        return f"{self.from_entity_type}:{self.from_entity_id[:8]} --{self.relation_type}--> {self.to_entity_type}:{self.to_entity_id[:8]}"


class UserPreferences(models.Model):
    """User-specific settings and personalization options."""
    
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
    
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, primary_key=True, related_name='preferences')
    
    # Notifications
    daily_reminder_enabled = models.BooleanField(default=True)
    daily_reminder_time = models.TimeField(null=True, blank=True)  # e.g., 08:00
    weekly_review_enabled = models.BooleanField(default=True)
    weekly_review_day = models.IntegerField(default=0)  # 0=Monday, 6=Sunday
    
    # Display preferences
    default_view = models.CharField(max_length=20, choices=VIEW_CHOICES, default='week')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    show_completed_tasks = models.BooleanField(default=True)
    
    # Analytics settings
    streak_threshold = models.IntegerField(default=80)  # % completion for streak
    consistency_window = models.IntegerField(default=7)  # days
    
    # Privacy
    public_profile = models.BooleanField(default=False)
    share_streaks = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


