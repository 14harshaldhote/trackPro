"""
Tag Service - V1.5 Feature

Handle tag management, filtering, and group analytics.
Enables views like "show only Health-related tasks today" or weekly stats grouped by tag.

Written from scratch for Version 1.5
"""
from typing import List, Dict, Optional
from django.db import transaction
from django.db.models import Count, Q, Avg
from core.models import Tag, TaskTemplateTag, TaskTemplate, TaskInstance, TrackerDefinition
import uuid
import logging

logger = logging.getLogger(__name__)


class TagService:
    """Service for managing tags and tag-based filtering."""
    
    @staticmethod
    def create_tag(user_id: int, name: str, color: str = None, icon: str = None) -> Tag:
        """
        Create a new tag for a user.
        
        Args:
            user_id: User creating the tag
            name: Tag name
            color: Optional hex color (e.g., '#FF5733')
            icon: Optional icon name/emoji
            
        Returns:
            Created Tag object
        """
        tag = Tag.objects.create(
            tag_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name.strip(),
            color=color or '#6366F1',  # Default indigo
            icon=icon or '🏷️'
        )
        return tag
    
    @staticmethod
    def get_user_tags(user_id: int) -> List[Dict]:
        """
        Get all tags for a user with usage counts.
        
        Returns:
            List of tag dicts with usage statistics
        """
        tags = Tag.objects.filter(
            user_id=user_id
        ).annotate(
            usage_count=Count('task_tags')
        ).order_by('name')
        
        return [
            {
                'tag_id': str(tag.tag_id),
                'name': tag.name,
                'color': tag.color,
                'icon': tag.icon,
                'usage_count': tag.usage_count
            }
            for tag in tags
        ]
    
    @staticmethod
    def add_tag_to_template(template_id: str, tag_id: str, user_id: int) -> bool:
        """
        Add a tag to a task template.
        
        Args:
            template_id: Template to tag
            tag_id: Tag to apply
            user_id: User for permission check
            
        Returns:
            Success boolean
        """
        try:
            # Verify ownership
            template = TaskTemplate.objects.get(
                template_id=template_id,
                tracker__user_id=user_id,
                deleted_at__isnull=True
            )
            tag = Tag.objects.get(tag_id=tag_id, user_id=user_id)
            
            # Create relationship (if not exists)
            TaskTemplateTag.objects.get_or_create(
                template=template,
                tag=tag
            )
            return True
            
        except (TaskTemplate.DoesNotExist, Tag.DoesNotExist):
            return False
    
    @staticmethod
    def remove_tag_from_template(template_id: str, tag_id: str, user_id: int) -> bool:
        """
        Remove a tag from a task template.
        """
        try:
            TaskTemplateTag.objects.filter(
                template__template_id=template_id,
                template__tracker__user_id=user_id,
                tag__tag_id=tag_id
            ).delete()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_templates_by_tag(tag_id: str, user_id: int) -> List[Dict]:
        """
        Get all templates with a specific tag.
        
        Args:
            tag_id: Tag to filter by
            user_id: User for permission check
            
        Returns:
            List of template dicts
        """
        templates = TaskTemplate.objects.filter(
            tags__tag_id=tag_id,
            tracker__user_id=user_id,
            deleted_at__isnull=True
        ).select_related('tracker')
        
        return [
            {
                'template_id': str(t.template_id),
                'description': t.description,
                'tracker_id': str(t.tracker_id),
                'tracker_name': t.tracker.name,
                'category': t.category,
                'points': t.points
            }
            for t in templates
        ]
    
    @staticmethod
    def get_today_tasks_by_tag(user_id: int, tag_ids: List[str] = None) -> Dict:
        """
        Get today's tasks filtered by tags.
        
        Args:
            user_id: User ID
            tag_ids: Optional list of tag IDs to filter by
            
        Returns:
            Dict with tasks grouped by tag
        """
        from datetime import date
        today = date.today()
        
        # Base query for today's tasks
        tasks_query = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date=today,
            deleted_at__isnull=True
        ).select_related('template', 'tracker_instance__tracker')
        
        # Filter by tags if specified
        if tag_ids:
            tasks_query = tasks_query.filter(
                template__tags__tag_id__in=tag_ids
            ).distinct()
        
        # Group by tag
        result = {
            'date': today.isoformat(),
            'total_tasks': tasks_query.count(),
            'completed': tasks_query.filter(status='DONE').count(),
            'tasks': [],
            'by_tag': {}
        }
        
        for task in tasks_query.prefetch_related('template__tags'):
            task_dict = {
                'task_id': str(task.task_instance_id),
                'description': task.template.description,
                'status': task.status,
                'tracker_name': task.tracker_instance.tracker.name,
                'tags': [
                    {'tag_id': str(t.tag_id), 'name': t.name, 'color': t.color}
                    for t in task.template.tags.all()
                ]
            }
            result['tasks'].append(task_dict)
            
            # Group by tag
            for tag in task.template.tags.all():
                tag_key = str(tag.tag_id)
                if tag_key not in result['by_tag']:
                    result['by_tag'][tag_key] = {
                        'name': tag.name,
                        'color': tag.color,
                        'tasks': [],
                        'total': 0,
                        'done': 0
                    }
                result['by_tag'][tag_key]['tasks'].append(task_dict)
                result['by_tag'][tag_key]['total'] += 1
                if task.status == 'DONE':
                    result['by_tag'][tag_key]['done'] += 1
        
        return result
    
    @staticmethod
    def get_tag_analytics(user_id: int, days: int = 30) -> List[Dict]:
        """
        Get completion analytics grouped by tag.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            List of tag analytics
        """
        from datetime import date, timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get all tasks in range with their tags
        tasks = TaskInstance.objects.filter(
            tracker_instance__tracker__user_id=user_id,
            tracker_instance__tracking_date__range=(start_date, end_date),
            deleted_at__isnull=True
        ).prefetch_related('template__tags')
        
        tag_stats = {}
        
        for task in tasks:
            for tag in task.template.tags.all():
                tag_key = str(tag.tag_id)
                if tag_key not in tag_stats:
                    tag_stats[tag_key] = {
                        'tag_id': tag_key,
                        'name': tag.name,
                        'color': tag.color,
                        'total': 0,
                        'done': 0,
                        'missed': 0
                    }
                tag_stats[tag_key]['total'] += 1
                if task.status == 'DONE':
                    tag_stats[tag_key]['done'] += 1
                elif task.status == 'MISSED':
                    tag_stats[tag_key]['missed'] += 1
        
        # Calculate rates
        result = []
        for tag_data in tag_stats.values():
            tag_data['completion_rate'] = (
                tag_data['done'] / tag_data['total'] * 100
            ) if tag_data['total'] > 0 else 0
            tag_data['miss_rate'] = (
                tag_data['missed'] / tag_data['total'] * 100
            ) if tag_data['total'] > 0 else 0
            result.append(tag_data)
        
        # Sort by completion rate descending
        result.sort(key=lambda x: x['completion_rate'], reverse=True)
        
        return result
    
    @staticmethod
    def delete_tag(tag_id: str, user_id: int) -> bool:
        """
        Delete a tag and remove it from all templates.
        
        Args:
            tag_id: Tag to delete
            user_id: User for permission check
            
        Returns:
            Success boolean
        """
        try:
            Tag.objects.filter(
                tag_id=tag_id,
                user_id=user_id
            ).delete()
            return True
        except Exception:
            return False
    
    @staticmethod
    def update_tag(tag_id: str, user_id: int, name: str = None, 
                   color: str = None, icon: str = None) -> Optional[Dict]:
        """
        Update tag properties.
        
        Returns:
            Updated tag dict or None if not found
        """
        try:
            tag = Tag.objects.get(tag_id=tag_id, user_id=user_id)
            
            if name is not None:
                tag.name = name.strip()
            if color is not None:
                tag.color = color
            if icon is not None:
                tag.icon = icon
                
            tag.save()
            
            return {
                'tag_id': str(tag.tag_id),
                'name': tag.name,
                'color': tag.color,
                'icon': tag.icon
            }
        except Tag.DoesNotExist:
            return None
