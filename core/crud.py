"""
CRUD operations using Django ORM.
Migrated from Excel-based storage to MySQL database.
Function signatures remain the same for backward compatibility.
"""
from core.models import TrackerDefinition, TaskTemplate, TrackerInstance, TaskInstance, DayNote
from django.db.models import Q, Prefetch
from django.utils import timezone
import uuid
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# TRACKER DEFINITIONS
# =============================================================================

def create_tracker_definition(data):
    """Create a new tracker definition"""
    try:
        tracker_id = data.get('tracker_id') or str(uuid.uuid4())
        tracker = TrackerDefinition.objects.create(
            tracker_id=tracker_id,
            name=data['name'],
            description=data.get('description', ''),
            time_mode=data.get('time_mode', 'daily'),
        )
        return model_to_dict(tracker)
    except Exception as e:
        logger.error(f"Error creating tracker definition: {e}")
        raise


def get_all_tracker_definitions():
    """Get all tracker definitions"""
    try:
        trackers = TrackerDefinition.objects.all().order_by('-created_at')
        return [model_to_dict(t) for t in trackers]
    except Exception as e:
        logger.error(f"Error fetching tracker definitions: {e}")
        return []


def get_tracker_by_id(tracker_id):
    """Get a specific tracker by ID"""
    try:
        tracker = TrackerDefinition.objects.get(tracker_id=tracker_id)
        return model_to_dict(tracker)
    except TrackerDefinition.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error fetching tracker {tracker_id}: {e}")
        return None


# =============================================================================
# TASK TEMPLATES
# =============================================================================

def create_task_template(data):
    """Create a new task template"""
    try:
        template_id = data.get('template_id') or str(uuid.uuid4())
        tracker = TrackerDefinition.objects.get(tracker_id=data['tracker_id'])
        
        template = TaskTemplate.objects.create(
            template_id=template_id,
            tracker=tracker,
            description=data['description'],
            is_recurring=data.get('is_recurring', True),
            category=data.get('category', ''),
            weight=data.get('weight', 1),
        )
        return model_to_dict(template)
    except Exception as e:
        logger.error(f"Error creating task template: {e}")
        raise


def get_task_templates_for_tracker(tracker_id):
    """Get all task templates for a tracker"""
    try:
        templates = TaskTemplate.objects.filter(tracker_id=tracker_id).order_by('description')
        return [model_to_dict(t) for t in templates]
    except Exception as e:
        logger.error(f"Error fetching task templates for tracker {tracker_id}: {e}")
        return []


def get_task_template_by_id(template_id):
    """Get a specific task template by ID"""
    try:
        template = TaskTemplate.objects.get(template_id=template_id)
        return model_to_dict(template)
    except TaskTemplate.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error fetching task template {template_id}: {e}")
        return None


# =============================================================================
# TRACKER INSTANCES
# =============================================================================

def create_tracker_instance(data):
    """Create a tracker instance for a specific date"""
    try:
        instance_id = data.get('instance_id') or str(uuid.uuid4())
        tracker = TrackerDefinition.objects.get(tracker_id=data['tracker_id'])
        
        # Convert datetime to date if needed
        tracking_date = data['tracking_date']
        if isinstance(tracking_date, datetime):
            tracking_date = tracking_date.date()
        
        instance, created = TrackerInstance.objects.get_or_create(
            tracker=tracker,
            tracking_date=tracking_date,
            defaults={
                'instance_id': instance_id,
                'period_start': data.get('period_start'),
                'period_end': data.get('period_end'),
                'status': data.get('status', 'active'),
            }
        )
        return model_to_dict(instance)
    except Exception as e:
        logger.error(f"Error creating tracker instance: {e}")
        raise


def get_tracker_instances(tracker_id, start_date=None, end_date=None):
    """Get tracker instances, optionally filtered by date range"""
    try:
        instances = TrackerInstance.objects.filter(tracker_id=tracker_id)
        
        if start_date:
            instances = instances.filter(tracking_date__gte=start_date)
        if end_date:
            instances = instances.filter(tracking_date__lte=end_date)
            
        instances = instances.order_by('-tracking_date')
        return [model_to_dict(i) for i in instances]
    except Exception as e:
        logger.error(f"Error fetching tracker instances: {e}")
        return []


def get_tracker_instance_by_date(tracker_id, tracking_date):
    """Get a specific tracker instance by date"""
    try:
        # Convert datetime to date if needed
        if isinstance(tracking_date, datetime):
            tracking_date = tracking_date.date()
            
        instance = TrackerInstance.objects.get(
            tracker_id=tracker_id,
            tracking_date=tracking_date
        )
        return model_to_dict(instance)
    except TrackerInstance.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error fetching tracker instance: {e}")
        return None


# =============================================================================
# TASK INSTANCES
# =============================================================================

def create_task_instance(data):
    """Create a task instance"""
    try:
        task_instance_id = data.get('task_instance_id') or str(uuid.uuid4())
        tracker_instance = TrackerInstance.objects.get(instance_id=data['tracker_instance_id'])
        template = TaskTemplate.objects.get(template_id=data['template_id'])
        
        task = TaskInstance.objects.create(
            task_instance_id=task_instance_id,
            tracker_instance=tracker_instance,
            template=template,
            status=data.get('status', 'TODO'),
            notes=data.get('notes', ''),
        )
        
        if data.get('status') == 'DONE':
            task.completed_at = timezone.now()
            task.save()
            
        return model_to_dict(task)
    except Exception as e:
        logger.error(f"Error creating task instance: {e}")
        raise


def get_task_instances_for_tracker_instance(instance_id):
    """Get all task instances for a tracker instance"""
    try:
        tasks = TaskInstance.objects.filter(
            tracker_instance_id=instance_id
        ).select_related('template').order_by('template__description')
        return [model_to_dict(t) for t in tasks]
    except Exception as e:
        logger.error(f"Error fetching task instances: {e}")
        return []


def update_task_instance_status(task_instance_id, status):
    """Update the status of a task instance"""
    try:
        task = TaskInstance.objects.get(task_instance_id=task_instance_id)
        task.status = status
        
        if status == 'DONE' and not task.completed_at:
            task.completed_at = timezone.now()
        elif status != 'DONE':
            task.completed_at = None
            
        task.save()
        return model_to_dict(task)
    except TaskInstance.DoesNotExist:
        logger.error(f"Task instance {task_instance_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error updating task instance: {e}")
        raise


# =============================================================================
# GENERIC DATABASE OPERATIONS (for compatibility with db_engine)
# =============================================================================

class DatabaseEngine:
    """Compatibility wrapper to mimic ExcelDB interface"""
    
    MODEL_MAP = {
        'TrackerDefinitions': TrackerDefinition,
        'TaskTemplates': TaskTemplate,
        'TrackerInstances': TrackerInstance,
        'TaskInstances': TaskInstance,
        'DayNotes': DayNote,
    }
    
    def fetch_by_id(self, sheet_name, id_field, id_value):
        """Fetch a single record by ID"""
        try:
            model = self.MODEL_MAP.get(sheet_name)
            if not model:
                return None
                
            instance = model.objects.get(**{id_field: id_value})
            return model_to_dict(instance)
        except model.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error in fetch_by_id: {e}")
            return None
    
    def fetch_all(self, sheet_name, filters=None):
        """Fetch all records, optionally filtered"""
        try:
            model = self.MODEL_MAP.get(sheet_name)
            if not model:
                return []
                
            queryset = model.objects.all()
            if filters:
                queryset = queryset.filter(**filters)
                
            return [model_to_dict(obj) for obj in queryset]
        except Exception as e:
            logger.error(f"Error in fetch_all: {e}")
            return []
    
    def insert(self, sheet_name, data):
        """Insert a new record"""
        try:
            model = self.MODEL_MAP.get(sheet_name)
            if not model:
                raise ValueError(f"Unknown sheet: {sheet_name}")
                
            instance = model.objects.create(**data)
            return model_to_dict(instance)
        except Exception as e:
            logger.error(f"Error in insert: {e}")
            raise
    
    def update(self, sheet_name, id_field, id_value, updates):
        """Update a record"""
        try:
            model = self.MODEL_MAP.get(sheet_name)
            if not model:
                raise ValueError(f"Unknown sheet: {sheet_name}")
                
            instance = model.objects.get(**{id_field: id_value})
            for key, value in updates.items():
                setattr(instance, key, value)
            instance.save()
            return model_to_dict(instance)
        except model.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error in update: {e}")
            raise
    
    def delete(self, sheet_name, id_field, id_value):
        """Delete a record"""
        try:
            model = self.MODEL_MAP.get(sheet_name)
            if not model:
                raise ValueError(f"Unknown sheet: {sheet_name}")
                
            model.objects.filter(**{id_field: id_value}).delete()
            return True
        except Exception as e:
            logger.error(f"Error in delete: {e}")
            return False
    
    def fetch_filter(self, sheet_name, **filters):
        """
        Fetch records with filtering (backward compatibility method).
        
        Args:
            sheet_name: Table/model name
            **filters: Keyword arguments for filtering (e.g., tracker_id='123')
            
        Returns:
            list: List of matching records as dictionaries
        """
        try:
            model = self.MODEL_MAP.get(sheet_name)
            if not model:
                logger.warning(f"Unknown sheet: {sheet_name}")
                return []
            
            queryset = model.objects.filter(**filters)
            return [model_to_dict(obj) for obj in queryset]
        except Exception as e:
            logger.error(f"Error in fetch_filter: {e}")
            return []


# Global instance for backward compatibility
db = DatabaseEngine()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def model_to_dict(instance):
    """Convert a model instance to a dictionary"""
    if instance is None:
        return None
        
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.name)
        
        # Handle foreign keys
        if field.is_relation and value is not None:
            # Store just the ID
            data[field.name + '_id'] = str(value.pk)
        # Handle dates/datetimes
        elif isinstance(value, (date, datetime)):
            data[field.name] = value.isoformat() if value else None
        # Handle UUIDs
        elif isinstance(value, uuid.UUID):
            data[field.name] = str(value)
        else:
            data[field.name] = value
            
    return data
