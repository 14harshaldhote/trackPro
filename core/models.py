from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords
import uuid


class SoftDeleteModel(models.Model):
    """
    Abstract model to support soft deletion.
    Essential for sync systems to track deleted items.
    """
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
        
    def soft_delete(self):
        """Mark object as deleted"""
        self.deleted_at = timezone.now()
        self.save()
        
    def restore(self):
        """Restore deleted object"""
        self.deleted_at = None
        self.save()


class TrackerDefinition(SoftDeleteModel):
    """Main tracker definition - what you're tracking (e.g., Daily Habits, Weekly Goals)"""
    
    TIME_MODE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    GOAL_PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('custom', 'Custom'),
    ]
    
    tracker_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='trackers', null=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    time_mode = models.CharField(max_length=20, choices=TIME_MODE_CHOICES, default='daily')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Goal Configuration - points-based goal tracking
    target_points = models.IntegerField(
        default=0,
        help_text="Target points for the goal (0 = no goal set)"
    )
    goal_period = models.CharField(
        max_length=20,
        choices=GOAL_PERIOD_CHOICES,
        default='daily',
        help_text="Period for goal reset (daily/weekly/custom)"
    )
    goal_start_day = models.IntegerField(
        default=0,
        help_text="Start day for weekly goals (0=Monday, 6=Sunday)"
    )
    
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
    
    @property
    def time_period(self):
        """Alias for time_mode for template compatibility."""
        return self.time_mode
    
    @property
    def id(self):
        """Alias for tracker_id for template compatibility."""
        return self.tracker_id
    
    @property
    def task_count(self):
        """Total number of task templates for this tracker."""
        return self.templates.count()
    
    @property
    def completed_count(self):
        """Count of completed task instances across all tracker instances."""
        from django.db.models import Count
        return TaskInstance.objects.filter(
            tracker_instance__tracker=self,
            status='DONE'
        ).count()
    
    @property
    def progress(self):
        """Overall completion percentage (0-100)."""
        total = TaskInstance.objects.filter(tracker_instance__tracker=self).count()
        if total == 0:
            return 0
        done = self.completed_count
        return int((done / total) * 100)
    
    @property
    def is_active(self):
        """Check if tracker status is active."""
        return self.status == 'active'


class TaskTemplate(SoftDeleteModel):
    """Template for tasks within a tracker (e.g., Exercise, Meditate, Read)"""
    
    TIME_OF_DAY_CHOICES = [
        ('anytime', 'Any Time'),
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ('night', 'Night'),
    ]
    
    template_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    tracker = models.ForeignKey(TrackerDefinition, on_delete=models.CASCADE, related_name='templates')
    description = models.CharField(max_length=500)
    is_recurring = models.BooleanField(default=True)
    category = models.CharField(max_length=100, blank=True, default='')
    weight = models.IntegerField(default=1, help_text="Task priority/ordering weight (1-10)")
    time_of_day = models.CharField(max_length=20, choices=TIME_OF_DAY_CHOICES, default='anytime')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Points and Goal Integration
    points = models.IntegerField(
        default=1,
        help_text="Points awarded when task is completed (0 or more)"
    )
    include_in_goal = models.BooleanField(
        default=True,
        help_text="Whether this task's points count towards the tracker goal"
    )
    
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


class TrackerInstance(SoftDeleteModel):
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


class TaskInstance(SoftDeleteModel):
    """Actual task completion record for a specific date"""
    
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('DONE', 'Done'),
        ('MISSED', 'Missed'),
        ('BLOCKED', 'Blocked'),
        ('SKIPPED', 'Skipped'),
    ]
    
    task_instance_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    tracker_instance = models.ForeignKey(TrackerInstance, on_delete=models.CASCADE, related_name='tasks')
    template = models.ForeignKey(TaskTemplate, on_delete=models.CASCADE, related_name='instances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TODO')
    notes = models.TextField(blank=True, default='')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    first_completed_at = models.DateTimeField(null=True, blank=True)
    last_status_change = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    # Snapshot fields (copied from template at creation)
    snapshot_description = models.CharField(max_length=500, blank=True)
    snapshot_points = models.IntegerField(default=0)
    snapshot_weight = models.IntegerField(default=1)

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
    
    def save(self, *args, **kwargs):
        if not self.pk:  # New instance
            if self.template:
                self.snapshot_description = self.template.description
                self.snapshot_points = self.template.points
                self.snapshot_weight = self.template.weight
        super().save(*args, **kwargs)

    def set_status(self, new_status: str):
        """Properly handle status changes."""
        old_status = self.status
        self.status = new_status
        
        if new_status == 'DONE':
            now = timezone.now()
            if self.first_completed_at is None:
                self.first_completed_at = now
            self.completed_at = now
        elif old_status == 'DONE':
            # Was done, now not - keep completed_at for history if desired, 
            # currently we might want to clear it or keep it. 
            # The edge case plan says: last completion timestamp updates each time.
            # first_completed_at never changes.
            pass
        
        self.save()
    
    def mark_done(self):
        """Helper method to mark task as done"""
        self.set_status('DONE')


class DayNote(SoftDeleteModel):
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


class Goal(SoftDeleteModel):
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
    
    GOAL_TYPE_CHOICES = [
        ('habit', 'Habit'),
        ('achievement', 'Achievement'),
        ('project', 'Project'),
    ]
    
    goal_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='goals')
    tracker = models.ForeignKey('TrackerDefinition', on_delete=models.SET_NULL, null=True, blank=True, related_name='goals')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, blank=True, default='🎯')
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES, default='habit')
    target_date = models.DateField(null=True, blank=True)
    target_value = models.FloatField(null=True, blank=True)  # Numeric target (e.g., 30 days)
    current_value = models.FloatField(default=0.0)  # Current progress value
    unit = models.CharField(max_length=50, blank=True, default='')  # e.g., 'days', 'hours', 'tasks'
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
    
    # Localization
    timezone = models.CharField(max_length=50, default='UTC')
    date_format = models.CharField(max_length=20, default='YYYY-MM-DD')  # Display format
    week_start = models.IntegerField(default=0)  # 0=Monday, 6=Sunday
    
    # Notifications
    daily_reminder_enabled = models.BooleanField(default=True)
    daily_reminder_time = models.TimeField(null=True, blank=True)  # e.g., 08:00
    weekly_review_enabled = models.BooleanField(default=True)
    weekly_review_day = models.IntegerField(default=0)  # 0=Monday, 6=Sunday
    
    # Display preferences
    default_view = models.CharField(max_length=20, choices=VIEW_CHOICES, default='week')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='light')
    show_completed_tasks = models.BooleanField(default=True)
    compact_mode = models.BooleanField(default=False)
    animations = models.BooleanField(default=True)
    
    # Sound settings
    sound_complete = models.BooleanField(default=True)
    sound_notify = models.BooleanField(default=True)
    sound_volume = models.IntegerField(default=50)  # 0-100
    
    # Keyboard & Push
    keyboard_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=False)
    
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


class Notification(models.Model):
    """In-app notifications for users."""
    
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('reminder', 'Reminder'),
        ('achievement', 'Achievement'),
    ]
    
    notification_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.type}: {self.title}"


class ShareLink(models.Model):
    """Shareable links for trackers."""
    
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('edit', 'Can Edit'),
    ]
    
    share_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    tracker = models.ForeignKey(TrackerDefinition, on_delete=models.CASCADE, related_name='share_links')
    created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='created_shares')
    token = models.CharField(max_length=64, unique=True)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES, default='view')
    password_hash = models.CharField(max_length=128, blank=True, default='')
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.IntegerField(null=True, blank=True)
    use_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'share_links'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['tracker', 'is_active']),
        ]
    
    def __str__(self):
        return f"Share: {self.tracker.name} ({self.permission})"
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate token if not set."""
        if not self.token:
            import secrets
            # Generate a URL-safe token
            # Keep trying until we get a unique one (handle collision)
            max_attempts = 10
            for _ in range(max_attempts):
                self.token = secrets.token_urlsafe(32)
                # Check if this token already exists
                if not ShareLink.objects.filter(token=self.token).exists():
                    break
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if the share link has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if the share link is still valid."""
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.max_uses and self.use_count >= self.max_uses:
            return False
        return True


class SearchHistory(models.Model):
    """
    Tracks user search queries for:
    - Recent search suggestions
    - Search analytics
    - Personalized results ranking
    """
    
    search_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=200)
    result_count = models.IntegerField(default=0)
    clicked_result_type = models.CharField(max_length=50, blank=True, default='')
    clicked_result_id = models.CharField(max_length=36, blank=True, default='')
    search_context = models.CharField(max_length=50, default='global')  # 'global', 'trackers', 'tasks'
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'search_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'query']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: '{self.query}' ({self.result_count} results)"
    
    @classmethod
    def get_recent_searches(cls, user, limit=5):
        """Get user's most recent distinct searches."""
        return cls.objects.filter(user=user).values('query').annotate(
            latest=models.Max('created_at')
        ).order_by('-latest')[:limit]
    
    @classmethod
    def get_popular_searches(cls, user, limit=5):
        """Get user's most frequently used searches."""
        from django.db.models import Count
        return cls.objects.filter(user=user).values('query').annotate(
            count=Count('search_id')
        ).order_by('-count')[:limit]

