from django.contrib import admin
from core.models import TrackerDefinition, TaskTemplate, TrackerInstance, TaskInstance, DayNote


@admin.register(TrackerDefinition)
class TrackerDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'time_mode', 'created_at']
    list_filter = ['time_mode', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['tracker_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tracker_id', 'name', 'description', 'time_mode')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ['description', 'tracker', 'category', 'weight', 'is_recurring']
    list_filter = ['tracker', 'is_recurring', 'category']
    search_fields = ['description', 'category']
    readonly_fields = ['template_id', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('template_id', 'tracker', 'description')
        }),
        ('Details', {
            'fields': ('category', 'weight', 'is_recurring')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TrackerInstance)
class TrackerInstanceAdmin(admin.ModelAdmin):
    list_display = ['tracker', 'tracking_date', 'status', 'created_at']
    list_filter = ['tracker', 'status', 'tracking_date']
    date_hierarchy = 'tracking_date'
    readonly_fields = ['instance_id', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('instance_id', 'tracker', 'tracking_date')
        }),
        ('Period', {
            'fields': ('period_start', 'period_end', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(TaskInstance)
class TaskInstanceAdmin(admin.ModelAdmin):
    list_display = ['template', 'tracker_instance', 'status', 'completed_at']
    list_filter = ['status', 'tracker_instance__tracker', 'completed_at']
    search_fields = ['template__description', 'notes']
    readonly_fields = ['task_instance_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('task_instance_id', 'tracker_instance', 'template')
        }),
        ('Status', {
            'fields': ('status', 'completed_at')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DayNote)
class DayNoteAdmin(admin.ModelAdmin):
    list_display = ['tracker', 'date', 'sentiment_score', 'created_at']
    list_filter = ['tracker', 'date']
    search_fields = ['content']
    date_hierarchy = 'date'
    readonly_fields = ['note_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('note_id', 'tracker', 'date')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Analysis', {
            'fields': ('sentiment_score', 'keywords')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
