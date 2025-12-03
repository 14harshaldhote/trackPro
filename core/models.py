from django.db import models
from django.utils import timezone
import uuid


class TrackerDefinition(models.Model):
    """Main tracker definition - what you're tracking (e.g., Daily Habits, Weekly Goals)"""
    
    TIME_MODE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    
    tracker_id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    time_mode = models.CharField(max_length=20, choices=TIME_MODE_CHOICES, default='daily')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tracker_definitions'
        ordering = ['-created_at']
        indexes = [
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
    
    class Meta:
        db_table = 'tracker_instances'
        unique_together = [['tracker', 'tracking_date']]
        ordering = ['-tracking_date']
        indexes = [
            models.Index(fields=['tracker', 'tracking_date']),
            models.Index(fields=['tracking_date']),
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
    
    class Meta:
        db_table = 'task_instances'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tracker_instance', 'status']),
            models.Index(fields=['template']),
            models.Index(fields=['status']),
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
    
    class Meta:
        db_table = 'day_notes'
        unique_together = [['tracker', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['tracker', 'date']),
        ]
    
    def __str__(self):
        return f"Note for {self.tracker.name} on {self.date}"
