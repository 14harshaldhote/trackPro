"""
Knowledge Graph Service - V2.0 Feature

Visualize relationships between entities: tasks, notes, goals, trackers, and moods.
Provides graph data for network visualization in the frontend.

Written from scratch for Version 2.0
"""
from typing import Dict, List, Optional, Tuple
from datetime import date, timedelta
from django.db.models import Count, Q
from core.models import (
    EntityRelation, TrackerDefinition, TaskTemplate, Goal, 
    GoalTaskMapping, DayNote, TaskInstance, TrackerInstance
)
import logging

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """
    Service for building and querying the knowledge graph.
    
    The knowledge graph connects:
    - Trackers -> Templates (has)
    - Templates -> Goals (contributes_to)
    - Templates -> Tags (categorized_by)
    - Tasks -> Tasks (depends_on, blocks, related_to)
    - Notes -> Trackers (attached_to)
    - Notes -> Moods (reflects)
    """
    
    RELATION_COLORS = {
        'depends_on': '#EF4444',     # Red
        'blocks': '#F97316',         # Orange
        'related_to': '#3B82F6',     # Blue
        'subtask_of': '#8B5CF6',     # Purple
        'contributes_to': '#22C55E', # Green
        'has': '#6B7280',            # Gray
        'categorized_by': '#06B6D4', # Cyan
        'attached_to': '#A855F7',    # Violet
    }
    
    NODE_TYPES = {
        'tracker': {'color': '#3B82F6', 'size': 'large'},
        'template': {'color': '#10B981', 'size': 'medium'},
        'goal': {'color': '#F59E0B', 'size': 'large'},
        'tag': {'color': '#8B5CF6', 'size': 'small'},
        'note': {'color': '#EC4899', 'size': 'small'},
    }
    
    @staticmethod
    def get_full_graph(user_id: int, include_notes: bool = False) -> Dict:
        """
        Get the complete knowledge graph for a user.
        
        Args:
            user_id: User ID
            include_notes: Whether to include DayNotes (can be large)
            
        Returns:
            Dict with nodes and edges for visualization
        """
        nodes = []
        edges = []
        node_ids = set()
        
        # 1. Add all trackers as nodes
        trackers = TrackerDefinition.objects.filter(
            user_id=user_id,
            deleted_at__isnull=True
        )
        
        for tracker in trackers:
            node_id = f"tracker:{tracker.tracker_id}"
            nodes.append({
                'id': node_id,
                'type': 'tracker',
                'label': tracker.name,
                'data': {
                    'tracker_id': str(tracker.tracker_id),
                    'time_mode': tracker.time_mode,
                    'status': tracker.status
                },
                **KnowledgeGraphService.NODE_TYPES['tracker']
            })
            node_ids.add(node_id)
            
            # 2. Add templates and connect to tracker
            templates = TaskTemplate.objects.filter(
                tracker=tracker,
                deleted_at__isnull=True
            ).prefetch_related('tags')
            
            for template in templates:
                tmpl_node_id = f"template:{template.template_id}"
                
                if tmpl_node_id not in node_ids:
                    nodes.append({
                        'id': tmpl_node_id,
                        'type': 'template',
                        'label': template.description[:30],
                        'data': {
                            'template_id': str(template.template_id),
                            'category': template.category,
                            'points': template.points
                        },
                        **KnowledgeGraphService.NODE_TYPES['template']
                    })
                    node_ids.add(tmpl_node_id)
                
                edges.append({
                    'source': node_id,
                    'target': tmpl_node_id,
                    'type': 'has',
                    'color': KnowledgeGraphService.RELATION_COLORS['has']
                })
                
                # Add tags
                for tag in template.tags.all():
                    tag_node_id = f"tag:{tag.tag_id}"
                    
                    if tag_node_id not in node_ids:
                        nodes.append({
                            'id': tag_node_id,
                            'type': 'tag',
                            'label': tag.name,
                            'data': {
                                'tag_id': str(tag.tag_id),
                                'color': tag.color,
                                'icon': tag.icon
                            },
                            **KnowledgeGraphService.NODE_TYPES['tag']
                        })
                        node_ids.add(tag_node_id)
                    
                    edges.append({
                        'source': tmpl_node_id,
                        'target': tag_node_id,
                        'type': 'categorized_by',
                        'color': KnowledgeGraphService.RELATION_COLORS['categorized_by']
                    })
        
        # 3. Add goals and their connections
        goals = Goal.objects.filter(
            user_id=user_id,
            deleted_at__isnull=True
        )
        
        for goal in goals:
            goal_node_id = f"goal:{goal.goal_id}"
            
            nodes.append({
                'id': goal_node_id,
                'type': 'goal',
                'label': goal.title[:30],
                'data': {
                    'goal_id': str(goal.goal_id),
                    'progress': goal.progress,
                    'status': goal.status,
                    'target_value': goal.target_value
                },
                **KnowledgeGraphService.NODE_TYPES['goal']
            })
            node_ids.add(goal_node_id)
            
            # Connect goal to tracker if exists
            if goal.tracker_id:
                tracker_node_id = f"tracker:{goal.tracker_id}"
                if tracker_node_id in node_ids:
                    edges.append({
                        'source': goal_node_id,
                        'target': tracker_node_id,
                        'type': 'attached_to',
                        'color': KnowledgeGraphService.RELATION_COLORS['attached_to']
                    })
            
            # Connect goal to templates via mappings
            mappings = GoalTaskMapping.objects.filter(goal=goal)
            for mapping in mappings:
                tmpl_node_id = f"template:{mapping.template_id}"
                if tmpl_node_id in node_ids:
                    edges.append({
                        'source': tmpl_node_id,
                        'target': goal_node_id,
                        'type': 'contributes_to',
                        'color': KnowledgeGraphService.RELATION_COLORS['contributes_to'],
                        'weight': mapping.contribution_weight
                    })
        
        # 4. Add entity relations (dependencies)
        relations = EntityRelation.objects.filter(
            created_by_id=user_id
        )
        
        for rel in relations:
            source_node_id = f"{rel.source_type}:{rel.source_id}"
            target_node_id = f"{rel.target_type}:{rel.target_id}"
            
            if source_node_id in node_ids and target_node_id in node_ids:
                edges.append({
                    'source': source_node_id,
                    'target': target_node_id,
                    'type': rel.relation_type,
                    'color': KnowledgeGraphService.RELATION_COLORS.get(
                        rel.relation_type, '#6B7280'
                    )
                })
        
        # 5. Optionally add notes
        if include_notes:
            notes = DayNote.objects.filter(
                tracker__user_id=user_id
            ).select_related('tracker')[:100]  # Limit for performance
            
            for note in notes:
                note_node_id = f"note:{note.id}"
                
                nodes.append({
                    'id': note_node_id,
                    'type': 'note',
                    'label': f"Note: {note.tracking_date.isoformat()}",
                    'data': {
                        'date': note.tracking_date.isoformat(),
                        'sentiment': note.sentiment_score,
                        'preview': note.content[:50] if note.content else ''
                    },
                    **KnowledgeGraphService.NODE_TYPES['note']
                })
                node_ids.add(note_node_id)
                
                tracker_node_id = f"tracker:{note.tracker_id}"
                if tracker_node_id in node_ids:
                    edges.append({
                        'source': note_node_id,
                        'target': tracker_node_id,
                        'type': 'attached_to',
                        'color': KnowledgeGraphService.RELATION_COLORS['attached_to']
                    })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'node_types': {
                    'trackers': sum(1 for n in nodes if n['type'] == 'tracker'),
                    'templates': sum(1 for n in nodes if n['type'] == 'template'),
                    'goals': sum(1 for n in nodes if n['type'] == 'goal'),
                    'tags': sum(1 for n in nodes if n['type'] == 'tag'),
                    'notes': sum(1 for n in nodes if n['type'] == 'note'),
                }
            }
        }
    
    @staticmethod
    def get_entity_connections(
        entity_type: str, 
        entity_id: str, 
        depth: int = 2
    ) -> Dict:
        """
        Get connections for a specific entity up to N levels deep.
        
        Args:
            entity_type: Type of entity (tracker, template, goal, tag)
            entity_id: Entity ID
            depth: How many levels of connections to explore
            
        Returns:
            Graph data centered on the entity
        """
        nodes = []
        edges = []
        visited = set()
        
        def explore(e_type: str, e_id: str, current_depth: int):
            node_key = f"{e_type}:{e_id}"
            if node_key in visited or current_depth > depth:
                return
            visited.add(node_key)
            
            # Get outgoing relations
            outgoing = EntityRelation.objects.filter(
                source_type=e_type,
                source_id=e_id
            )
            
            for rel in outgoing:
                target_key = f"{rel.target_type}:{rel.target_id}"
                edges.append({
                    'source': node_key,
                    'target': target_key,
                    'type': rel.relation_type
                })
                explore(rel.target_type, rel.target_id, current_depth + 1)
            
            # Get incoming relations
            incoming = EntityRelation.objects.filter(
                target_type=e_type,
                target_id=e_id
            )
            
            for rel in incoming:
                source_key = f"{rel.source_type}:{rel.source_id}"
                edges.append({
                    'source': source_key,
                    'target': node_key,
                    'type': rel.relation_type
                })
                explore(rel.source_type, rel.source_id, current_depth + 1)
        
        explore(entity_type, entity_id, 0)
        
        # Build nodes from visited set
        for node_key in visited:
            e_type, e_id = node_key.split(':', 1)
            nodes.append({
                'id': node_key,
                'type': e_type,
                'entity_id': e_id
            })
        
        return {'nodes': nodes, 'edges': edges, 'center': f"{entity_type}:{entity_id}"}
    
    @staticmethod
    def find_path(
        source_type: str, source_id: str,
        target_type: str, target_id: str,
        max_depth: int = 5
    ) -> Optional[List[Dict]]:
        """
        Find the shortest path between two entities.
        
        Uses BFS to find if two entities are connected.
        
        Returns:
            List of edges forming the path, or None if no path exists
        """
        from collections import deque
        
        start = f"{source_type}:{source_id}"
        end = f"{target_type}:{target_id}"
        
        if start == end:
            return []
        
        queue = deque([(start, [])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            c_type, c_id = current.split(':', 1)
            
            # Get all relations from current node
            relations = list(EntityRelation.objects.filter(
                Q(source_type=c_type, source_id=c_id) |
                Q(target_type=c_type, target_id=c_id)
            ))
            
            for rel in relations:
                if rel.source_type == c_type and rel.source_id == c_id:
                    next_node = f"{rel.target_type}:{rel.target_id}"
                    direction = 'forward'
                else:
                    next_node = f"{rel.source_type}:{rel.source_id}"
                    direction = 'backward'
                
                if next_node in visited:
                    continue
                
                new_path = path + [{
                    'from': current,
                    'to': next_node,
                    'relation': rel.relation_type,
                    'direction': direction
                }]
                
                if next_node == end:
                    return new_path
                
                if len(new_path) < max_depth:
                    visited.add(next_node)
                    queue.append((next_node, new_path))
        
        return None
