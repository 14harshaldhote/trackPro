"""
Entity Relations Service - V1.5 Feature

Handle relationships between entities, primarily task dependencies.
Enables "depends_on" relationships and circular dependency detection.

Written from scratch for Version 1.5
"""
from typing import List, Dict, Optional, Set
from django.db import transaction
from django.db.models import Q
from core.models import EntityRelation, TaskInstance, TaskTemplate
import logging

logger = logging.getLogger(__name__)


class EntityRelationService:
    """Service for managing entity relationships, especially task dependencies."""
    
    # Relationship types
    DEPENDS_ON = 'depends_on'
    BLOCKS = 'blocks'
    RELATED_TO = 'related_to'
    SUBTASK_OF = 'subtask_of'
    
    VALID_RELATION_TYPES = [DEPENDS_ON, BLOCKS, RELATED_TO, SUBTASK_OF]
    
    @staticmethod
    def create_relation(
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relation_type: str,
        user_id: int,
        metadata: dict = None
    ) -> Optional[EntityRelation]:
        """
        Create a relationship between two entities.
        
        Args:
            source_type: Type of source entity ('task', 'template', 'tracker', 'goal')
            source_id: ID of source entity
            target_type: Type of target entity
            target_id: ID of target entity
            relation_type: Type of relationship (DEPENDS_ON, BLOCKS, etc.)
            user_id: User creating the relationship
            metadata: Optional additional metadata
            
        Returns:
            Created EntityRelation or None if invalid
        """
        if relation_type not in EntityRelationService.VALID_RELATION_TYPES:
            logger.warning(f"Invalid relation type: {relation_type}")
            return None
        
        # Check for existing relation
        existing = EntityRelation.objects.filter(
            from_entity_type=source_type,
            from_entity_id=source_id,
            to_entity_type=target_type,
            to_entity_id=target_id,
            relation_type=relation_type
        ).first()
        
        if existing:
            return existing  # Already exists
        
        # Check for circular dependencies
        if relation_type == EntityRelationService.DEPENDS_ON:
            if EntityRelationService._would_create_cycle(
                source_type, source_id, target_type, target_id
            ):
                logger.warning(f"Circular dependency detected: {source_id} -> {target_id}")
                return None
        
        relation = EntityRelation.objects.create(
            from_entity_type=source_type,
            from_entity_id=source_id,
            to_entity_type=target_type,
            to_entity_id=target_id,
            relation_type=relation_type,
            user_id=user_id,
            metadata=metadata or {}
        )
        
        return relation
    
    @staticmethod
    def _would_create_cycle(
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str
    ) -> bool:
        """
        Check if creating a depends_on relation would create a cycle.
        
        If A depends_on B, and B depends_on A, that's a cycle.
        This checks transitively.
        """
        # Get all entities that target depends on (transitively)
        visited: Set[str] = set()
        to_check = [(target_type, target_id)]
        
        while to_check:
            check_type, check_id = to_check.pop()
            key = f"{check_type}:{check_id}"
            
            if key in visited:
                continue
            visited.add(key)
            
            # If we find the source in the dependency chain, it's a cycle
            if check_type == source_type and check_id == source_id:
                return True
            
            # Get what this entity depends on
            dependencies = EntityRelation.objects.filter(
                from_entity_type=check_type,
                from_entity_id=check_id,
                relation_type=EntityRelationService.DEPENDS_ON
            ).values_list('to_entity_type', 'to_entity_id')
            
            for dep_type, dep_id in dependencies:
                to_check.append((dep_type, dep_id))
        
        return False
    
    @staticmethod
    def get_dependencies(
        entity_type: str,
        entity_id: str
    ) -> List[Dict]:
        """
        Get what this entity depends on.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            List of dependency dicts
        """
        relations = EntityRelation.objects.filter(
            from_entity_type=entity_type,
            from_entity_id=entity_id,
            relation_type=EntityRelationService.DEPENDS_ON
        )
        
        return [
            {
                'target_type': r.to_entity_type,
                'target_id': r.to_entity_id,
                'created_at': r.created_at.isoformat() if r.created_at else None
            }
            for r in relations
        ]
    
    @staticmethod
    def get_dependents(
        entity_type: str,
        entity_id: str
    ) -> List[Dict]:
        """
        Get what depends on this entity.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            List of dependent dicts
        """
        relations = EntityRelation.objects.filter(
            to_entity_type=entity_type,
            to_entity_id=entity_id,
            relation_type=EntityRelationService.DEPENDS_ON
        )
        
        return [
            {
                'source_type': r.from_entity_type,
                'source_id': r.from_entity_id,
                'created_at': r.created_at.isoformat() if r.created_at else None
            }
            for r in relations
        ]
    
    @staticmethod
    def remove_relation(
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relation_type: str
    ) -> bool:
        """
        Remove a relationship between entities.
        
        Returns:
            True if deleted, False if not found
        """
        count, _ = EntityRelation.objects.filter(
            from_entity_type=source_type,
            from_entity_id=source_id,
            to_entity_type=target_type,
            to_entity_id=target_id,
            relation_type=relation_type
        ).delete()
        
        return count > 0
    
    @staticmethod
    def check_task_blocked(task_instance_id: str) -> Dict:
        """
        Check if a task is blocked by incomplete dependencies.
        
        Args:
            task_instance_id: TaskInstance ID
            
        Returns:
            Dict with blocking info
        """
        # Get the task's template dependencies
        try:
            task = TaskInstance.objects.select_related('template').get(
                task_instance_id=task_instance_id
            )
        except TaskInstance.DoesNotExist:
            return {'blocked': False, 'reason': 'Task not found'}
        
        # Check template-level dependencies
        dependencies = EntityRelation.objects.filter(
            from_entity_type='template',
            from_entity_id=str(task.template_id),
            relation_type=EntityRelationService.DEPENDS_ON
        )
        
        if not dependencies.exists():
            return {'blocked': False, 'blockers': []}
        
        # Check if dependencies are completed
        blockers = []
        for dep in dependencies:
            if dep.to_entity_type == 'template':
                # Find the corresponding task instance for this template
                blocking_tasks = TaskInstance.objects.filter(
                    template_id=dep.to_entity_id,
                    tracker_instance=task.tracker_instance,
                    deleted_at__isnull=True
                ).exclude(status='DONE')
                
                for bt in blocking_tasks:
                    blockers.append({
                        'task_id': str(bt.task_instance_id),
                        'description': bt.template.description if bt.template else 'Unknown',
                        'status': bt.status
                    })
        
        return {
            'blocked': len(blockers) > 0,
            'blockers': blockers
        }
    
    @staticmethod
    def get_task_dependency_graph(tracker_id: str) -> Dict:
        """
        Get the complete dependency graph for a tracker's tasks.
        
        Args:
            tracker_id: Tracker ID
            
        Returns:
            Dict with nodes and edges for visualization
        """
        # Get all templates in the tracker
        templates = TaskTemplate.objects.filter(
            tracker__tracker_id=tracker_id,
            deleted_at__isnull=True
        )
        
        nodes = []
        edges = []
        
        for template in templates:
            nodes.append({
                'id': str(template.template_id),
                'label': template.description[:30],
                'type': 'template'
            })
            
            # Get dependencies
            deps = EntityRelation.objects.filter(
                from_entity_type='template',
                from_entity_id=str(template.template_id),
                relation_type=EntityRelationService.DEPENDS_ON
            )
            
            for dep in deps:
                edges.append({
                    'from': str(template.template_id),
                    'to': dep.to_entity_id,
                    'type': dep.relation_type
                })
        
        return {
            'nodes': nodes,
            'edges': edges
        }
    
    @staticmethod
    def get_all_relations(entity_type: str, entity_id: str) -> List[Dict]:
        """
        Get all relationships for an entity (both as source and target).
        
        Returns:
            List of all relations
        """
        as_source = EntityRelation.objects.filter(
            from_entity_type=entity_type,
            from_entity_id=entity_id
        )
        
        as_target = EntityRelation.objects.filter(
            to_entity_type=entity_type,
            to_entity_id=entity_id
        )
        
        result = []
        
        for r in as_source:
            result.append({
                'direction': 'outgoing',
                'relation_type': r.relation_type,
                'target_type': r.to_entity_type,
                'target_id': r.to_entity_id
            })
        
        for r in as_target:
            result.append({
                'direction': 'incoming',
                'relation_type': r.relation_type,
                'source_type': r.from_entity_type,
                'source_id': r.from_entity_id
            })
        
        return result
