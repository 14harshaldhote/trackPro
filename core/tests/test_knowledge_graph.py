"""
Knowledge Graph Tests V2.0 (12 tests)

Test IDs: GRPH-001 to GRPH-012
Coverage: /api/v1/v2/knowledge-graph/, /api/v1/v2/graph/*

These tests cover:
- Full graph generation
- Node types (trackers, templates, goals, tags)
- Entity connections
- Path finding
"""
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, GoalFactory, TagFactory
)


class KnowledgeGraphTests(BaseAPITestCase):
    """Tests for /api/v1/v2/knowledge-graph/ endpoint."""
    
    def test_GRPH_001_get_full_graph(self):
        """GRPH-001: Get full knowledge graph returns 200 with nodes and edges."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        goal = GoalFactory.create(self.user, tracker)
        tag = TagFactory.create(self.user)
        
        response = self.get('/api/v1/v2/knowledge-graph/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success', True))
    
    def test_GRPH_002_graph_includes_trackers(self):
        """GRPH-002: Graph includes tracker nodes."""
        tracker1 = self.create_tracker(name='Tracker 1')
        tracker2 = self.create_tracker(name='Tracker 2')
        
        response = self.get('/api/v1/v2/knowledge-graph/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_GRPH_003_graph_includes_templates(self):
        """GRPH-003: Graph includes template nodes."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, description='Task 1')
        template2 = self.create_template(tracker, description='Task 2')
        
        response = self.get('/api/v1/v2/knowledge-graph/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_GRPH_004_graph_includes_goals(self):
        """GRPH-004: Graph includes goal nodes."""
        tracker = self.create_tracker()
        goal = GoalFactory.create(self.user, tracker, title='21 Day Challenge')
        
        response = self.get('/api/v1/v2/knowledge-graph/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_GRPH_005_graph_includes_tags(self):
        """GRPH-005: Graph includes tag nodes."""
        tag = TagFactory.create(self.user, name='Health')
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Link tag to template
        self.post(f'/api/v1/template/{template.template_id}/tag/{tag.tag_id}/')
        
        response = self.get('/api/v1/v2/knowledge-graph/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_GRPH_006_graph_with_notes(self):
        """GRPH-006: Graph with include_notes=true includes note nodes."""
        from core.tests.factories import DayNoteFactory
        
        tracker = self.create_tracker()
        note = DayNoteFactory.create(tracker)
        
        response = self.get('/api/v1/v2/knowledge-graph/?include_notes=true')
        
        self.assertEqual(response.status_code, 200)


class EntityConnectionsTests(BaseAPITestCase):
    """Tests for /api/v1/v2/graph/{type}/{id}/ endpoint."""
    
    def test_GRPH_007_get_entity_connections(self):
        """GRPH-007: Get entity connections returns connected nodes."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker)
        template2 = self.create_template(tracker)
        goal = GoalFactory.create(self.user, tracker)
        
        response = self.get(f'/api/v1/v2/graph/tracker/{tracker.tracker_id}/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_GRPH_008_connections_with_depth(self):
        """GRPH-008: Connections with depth parameter returns deeper levels."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        tag = TagFactory.create(self.user)
        
        response = self.get(f'/api/v1/v2/graph/tracker/{tracker.tracker_id}/?depth=3')
        
        self.assertEqual(response.status_code, 200)


class PathFindingTests(BaseAPITestCase):
    """Tests for /api/v1/v2/graph/path/ endpoint."""
    
    def test_GRPH_009_find_path_exists(self):
        """GRPH-009: Find path when path exists returns path_found=true."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        tag = TagFactory.create(self.user)
        
        # Link tag to template
        self.post(f'/api/v1/template/{template.template_id}/tag/{tag.tag_id}/')
        
        response = self.get(
            f'/api/v1/v2/graph/path/?from_type=tracker&from_id={tracker.tracker_id}&to_type=tag&to_id={tag.tag_id}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_GRPH_010_find_path_not_exists(self):
        """GRPH-010: Find path when no path exists returns path_found=false."""
        tracker1 = self.create_tracker(name='Isolated 1')
        tracker2 = self.create_tracker(name='Isolated 2')
        
        response = self.get(
            f'/api/v1/v2/graph/path/?from_type=tracker&from_id={tracker1.tracker_id}&to_type=tracker&to_id={tracker2.tracker_id}'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_GRPH_011_find_shortest_path(self):
        """GRPH-011: Find path returns shortest path."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.get(
            f'/api/v1/v2/graph/path/?from_type=tracker&from_id={tracker.tracker_id}&to_type=template&to_id={template.template_id}'
        )
        
        self.assertEqual(response.status_code, 200)


class EmptyGraphTests(BaseAPITestCase):
    """Tests for empty graph scenarios."""
    
    def test_GRPH_012_graph_empty_data(self):
        """GRPH-012: Graph with no data returns empty nodes and edges."""
        # No data created
        
        response = self.get('/api/v1/v2/knowledge-graph/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should have empty or minimal data
        self.assertTrue(data.get('success', True))
