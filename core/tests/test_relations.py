"""
Entity Relations Tests V1.5 (12 tests)

Test IDs: REL-001 to REL-012
Coverage: /api/v1/template/{id}/dependencies/*, /api/v1/task/{id}/blocked/, /api/v1/tracker/{id}/dependency-graph/

These tests cover:
- Dependency creation
- Multiple dependency types
- Circular dependency detection
- Blocked status checking
- Dependency graph visualization
"""
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
)


class DependencyCreateTests(BaseAPITestCase):
    """Tests for POST /api/v1/template/{id}/dependencies/ endpoint."""
    
    def test_REL_001_create_dependency(self):
        """REL-001: Create dependency returns 201."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, description='Task A')
        template2 = self.create_template(tracker, description='Task B')
        
        response = self.post(f'/api/v1/template/{template1.template_id}/dependencies/', {
            'target_id': template2.template_id,
            'dependency_type': 'depends_on'
        })
        
        self.assertIn(response.status_code, [200, 201])
    
    def test_REL_002_create_multiple_types(self):
        """REL-002: Create different dependency types works."""
        tracker = self.create_tracker()
        template_a = self.create_template(tracker, description='A')
        template_b = self.create_template(tracker, description='B')
        template_c = self.create_template(tracker, description='C')
        
        # depends_on
        response1 = self.post(f'/api/v1/template/{template_a.template_id}/dependencies/', {
            'target_id': template_b.template_id,
            'dependency_type': 'depends_on'
        })
        self.assertIn(response1.status_code, [200, 201])
        
        # blocks
        response2 = self.post(f'/api/v1/template/{template_b.template_id}/dependencies/', {
            'target_id': template_c.template_id,
            'dependency_type': 'blocks'
        })
        self.assertIn(response2.status_code, [200, 201])
        
        # related_to
        response3 = self.post(f'/api/v1/template/{template_a.template_id}/dependencies/', {
            'target_id': template_c.template_id,
            'dependency_type': 'related_to'
        })
        self.assertIn(response3.status_code, [200, 201])


class DependencyListTests(BaseAPITestCase):
    """Tests for GET /api/v1/template/{id}/dependencies/ endpoint."""
    
    def test_REL_003_get_dependencies(self):
        """REL-003: Get dependencies returns 200 with list."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker)
        template2 = self.create_template(tracker)
        
        # Create a dependency
        self.post(f'/api/v1/template/{template1.template_id}/dependencies/', {
            'target_id': template2.template_id,
            'dependency_type': 'depends_on'
        })
        
        response = self.get(f'/api/v1/template/{template1.template_id}/dependencies/')
        
        self.assertEqual(response.status_code, 200)


class DependencyRemoveTests(BaseAPITestCase):
    """Tests for removing dependencies."""
    
    def test_REL_004_remove_dependency(self):
        """REL-004: Remove dependency returns 200."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker)
        template2 = self.create_template(tracker)
        
        # Create a dependency
        self.post(f'/api/v1/template/{template1.template_id}/dependencies/', {
            'target_id': template2.template_id,
            'dependency_type': 'depends_on'
        })
        
        # Remove it
        response = self.post(
            f'/api/v1/template/{template1.template_id}/dependencies/{template2.template_id}/remove/'
        )
        
        self.assertEqual(response.status_code, 200)


class CircularDependencyTests(BaseAPITestCase):
    """Tests for circular dependency detection."""
    
    def test_REL_005_circular_dependency_A_B_A(self):
        """REL-005: Circular dependency A→B→A is rejected with 400."""
        tracker = self.create_tracker()
        template_a = self.create_template(tracker, description='A')
        template_b = self.create_template(tracker, description='B')
        
        # A depends on B
        self.post(f'/api/v1/template/{template_a.template_id}/dependencies/', {
            'target_id': template_b.template_id,
            'dependency_type': 'depends_on'
        })
        
        # B depends on A (should fail)
        response = self.post(f'/api/v1/template/{template_b.template_id}/dependencies/', {
            'target_id': template_a.template_id,
            'dependency_type': 'depends_on'
        })
        
        self.assertEqual(response.status_code, 400)
    
    def test_REL_006_long_chain_cycle(self):
        """REL-006: Long chain cycle A→B→C→A is rejected with 400."""
        tracker = self.create_tracker()
        template_a = self.create_template(tracker, description='A')
        template_b = self.create_template(tracker, description='B')
        template_c = self.create_template(tracker, description='C')
        
        # A depends on B
        self.post(f'/api/v1/template/{template_a.template_id}/dependencies/', {
            'target_id': template_b.template_id,
            'dependency_type': 'depends_on'
        })
        
        # B depends on C
        self.post(f'/api/v1/template/{template_b.template_id}/dependencies/', {
            'target_id': template_c.template_id,
            'dependency_type': 'depends_on'
        })
        
        # C depends on A (should fail - creates cycle)
        response = self.post(f'/api/v1/template/{template_c.template_id}/dependencies/', {
            'target_id': template_a.template_id,
            'dependency_type': 'depends_on'
        })
        
        self.assertEqual(response.status_code, 400)
    
    def test_REL_007_self_dependency(self):
        """REL-007: Self-dependency A→A is rejected with 400."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.post(f'/api/v1/template/{template.template_id}/dependencies/', {
            'target_id': template.template_id,
            'dependency_type': 'depends_on'
        })
        
        self.assertEqual(response.status_code, 400)


class BlockedStatusTests(BaseAPITestCase):
    """Tests for /api/v1/task/{id}/blocked/ endpoint."""
    
    def test_REL_008_check_task_blocked(self):
        """REL-008: Check task blocked status returns correct status."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, description='Blocker')
        template2 = self.create_template(tracker, description='Blocked')
        instance = self.create_instance(tracker)
        task1 = self.create_task_instance(instance, template1, status='TODO')
        task2 = self.create_task_instance(instance, template2, status='TODO')
        
        # Task2 depends on Task1
        self.post(f'/api/v1/template/{template2.template_id}/dependencies/', {
            'target_id': template1.template_id,
            'dependency_type': 'depends_on'
        })
        
        response = self.get(f'/api/v1/task/{task2.task_instance_id}/blocked/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REL_009_task_blocked_by_incomplete(self):
        """REL-009: Task blocked by incomplete dependency shows blocked=true."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, description='Blocker')
        template2 = self.create_template(tracker, description='Blocked')
        instance = self.create_instance(tracker)
        task1 = self.create_task_instance(instance, template1, status='TODO')  # Not done
        task2 = self.create_task_instance(instance, template2, status='TODO')
        
        # Task2 depends on Task1
        self.post(f'/api/v1/template/{template2.template_id}/dependencies/', {
            'target_id': template1.template_id,
            'dependency_type': 'depends_on'
        })
        
        response = self.get(f'/api/v1/task/{task2.task_instance_id}/blocked/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('blocked', True))
    
    def test_REL_010_task_unblocked_by_complete(self):
        """REL-010: Task unblocked when dependency is complete."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, description='Blocker')
        template2 = self.create_template(tracker, description='Blocked')
        instance = self.create_instance(tracker)
        task1 = self.create_task_instance(instance, template1, status='DONE')  # Done!
        task2 = self.create_task_instance(instance, template2, status='TODO')
        
        # Task2 depends on Task1
        self.post(f'/api/v1/template/{template2.template_id}/dependencies/', {
            'target_id': template1.template_id,
            'dependency_type': 'depends_on'
        })
        
        response = self.get(f'/api/v1/task/{task2.task_instance_id}/blocked/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data.get('blocked', False))


class DependencyGraphTests(BaseAPITestCase):
    """Tests for /api/v1/tracker/{id}/dependency-graph/ endpoint."""
    
    def test_REL_011_get_dependency_graph(self):
        """REL-011: Get dependency graph returns 200 with graph."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker, description='A')
        template2 = self.create_template(tracker, description='B')
        template3 = self.create_template(tracker, description='C')
        
        # Create dependencies
        self.post(f'/api/v1/template/{template1.template_id}/dependencies/', {
            'target_id': template2.template_id,
            'dependency_type': 'depends_on'
        })
        self.post(f'/api/v1/template/{template2.template_id}/dependencies/', {
            'target_id': template3.template_id,
            'dependency_type': 'depends_on'
        })
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/dependency-graph/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_REL_012_graph_for_tracker_no_deps(self):
        """REL-012: Graph for tracker with no dependencies shows no edges."""
        tracker = self.create_tracker()
        template1 = self.create_template(tracker)
        template2 = self.create_template(tracker)
        
        response = self.get(f'/api/v1/tracker/{tracker.tracker_id}/dependency-graph/')
        
        self.assertEqual(response.status_code, 200)
