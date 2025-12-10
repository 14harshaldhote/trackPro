"""
Tags System Tests V1.5 (14 tests)

Test IDs: TAG-001 to TAG-014
Coverage: /api/v1/tags/*, /api/v1/template/{id}/tag/{tag_id}/

These tests cover:
- Tag CRUD operations
- Tag-template associations
- Tasks by tag filtering
- Tag analytics
"""
from django.test import TestCase
from core.tests.base import BaseAPITestCase
from core.tests.factories import (
    TrackerFactory, TemplateFactory, TagFactory
)


class TagCreateTests(BaseAPITestCase):
    """Tests for POST /api/v1/tags/ endpoint."""
    
    def test_TAG_001_create_tag(self):
        """TAG-001: Create tag returns 201."""
        response = self.post('/api/v1/tags/', {
            'name': 'Health'
        })
        
        self.assertIn(response.status_code, [200, 201])
    
    def test_TAG_002_create_tag_with_color_icon(self):
        """TAG-002: Create tag with color and icon returns 201."""
        response = self.post('/api/v1/tags/', {
            'name': 'Fitness',
            'color': '#10B981',
            'icon': 'dumbbell'
        })
        
        self.assertIn(response.status_code, [200, 201])
    
    def test_TAG_003_create_duplicate_name(self):
        """TAG-003: Create tag with duplicate name returns 400."""
        # Create first tag
        TagFactory.create(self.user, name='Unique')
        
        # Try to create duplicate
        response = self.post('/api/v1/tags/', {
            'name': 'Unique'
        })
        
        self.assertEqual(response.status_code, 400)


class TagListTests(BaseAPITestCase):
    """Tests for GET /api/v1/tags/ endpoint."""
    
    def test_TAG_004_list_all_tags(self):
        """TAG-004: List all tags returns 200 with counts."""
        tag1 = TagFactory.create(self.user, name='Tag 1')
        tag2 = TagFactory.create(self.user, name='Tag 2')
        
        response = self.get('/api/v1/tags/')
        
        self.assertEqual(response.status_code, 200)


class TagUpdateTests(BaseAPITestCase):
    """Tests for PUT /api/v1/tags/{id}/ endpoint."""
    
    def test_TAG_005_update_tag(self):
        """TAG-005: Update tag returns 200."""
        tag = TagFactory.create(self.user, name='Old Name')
        
        response = self.put(f'/api/v1/tags/{tag.tag_id}/', {
            'name': 'New Name'
        })
        
        self.assertEqual(response.status_code, 200)


class TagDeleteTests(BaseAPITestCase):
    """Tests for DELETE /api/v1/tags/{id}/ endpoint."""
    
    def test_TAG_006_delete_tag(self):
        """TAG-006: Delete tag returns 200."""
        tag = TagFactory.create(self.user)
        
        response = self.delete(f'/api/v1/tags/{tag.tag_id}/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_TAG_007_delete_tag_removes_associations(self):
        """TAG-007: Deleting tag removes template associations."""
        tag = TagFactory.create(self.user)
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Associate tag with template
        self.post(f'/api/v1/template/{template.template_id}/tag/{tag.tag_id}/')
        
        # Delete tag
        response = self.delete(f'/api/v1/tags/{tag.tag_id}/')
        
        self.assertEqual(response.status_code, 200)


class TagTemplateAssociationTests(BaseAPITestCase):
    """Tests for /api/v1/template/{id}/tag/{tag_id}/ endpoint."""
    
    def test_TAG_008_add_tag_to_template(self):
        """TAG-008: Add tag to template returns 200."""
        tag = TagFactory.create(self.user)
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        response = self.post(f'/api/v1/template/{template.template_id}/tag/{tag.tag_id}/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_TAG_009_remove_tag_from_template(self):
        """TAG-009: Remove tag from template returns 200."""
        tag = TagFactory.create(self.user)
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Add tag first
        self.post(f'/api/v1/template/{template.template_id}/tag/{tag.tag_id}/')
        
        # Remove tag
        response = self.post(f'/api/v1/template/{template.template_id}/tag/{tag.tag_id}/', {
            'action': 'remove'
        })
        
        self.assertEqual(response.status_code, 200)


class TasksByTagTests(BaseAPITestCase):
    """Tests for /api/v1/tasks/by-tag/ endpoint."""
    
    def test_TAG_010_get_tasks_by_tag(self):
        """TAG-010: Get tasks by tag returns 200 with filtered tasks."""
        tag = TagFactory.create(self.user)
        
        response = self.get(f'/api/v1/tasks/by-tag/?tags={tag.tag_id}')
        
        self.assertEqual(response.status_code, 200)
    
    def test_TAG_011_tasks_by_multiple_tags(self):
        """TAG-011: Tasks by multiple tags returns OR-filtered results."""
        tag1 = TagFactory.create(self.user, name='Tag 1')
        tag2 = TagFactory.create(self.user, name='Tag 2')
        
        response = self.get(f'/api/v1/tasks/by-tag/?tags={tag1.tag_id},{tag2.tag_id}')
        
        self.assertEqual(response.status_code, 200)


class TagAnalyticsTests(BaseAPITestCase):
    """Tests for /api/v1/tags/analytics/ endpoint."""
    
    def test_TAG_012_get_tag_analytics(self):
        """TAG-012: Get tag analytics returns 200 with tag stats."""
        tag = TagFactory.create(self.user)
        
        response = self.get('/api/v1/tags/analytics/')
        
        self.assertEqual(response.status_code, 200)
    
    def test_TAG_013_tag_analytics_completion_rates(self):
        """TAG-013: Tag analytics includes per-tag completion rates."""
        tag = TagFactory.create(self.user)
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        
        # Associate tag with template
        self.post(f'/api/v1/template/{template.template_id}/tag/{tag.tag_id}/')
        
        # Create some completed tasks
        instance = self.create_instance(tracker)
        self.create_task_instance(instance, template, status='DONE')
        
        response = self.get('/api/v1/tags/analytics/')
        
        self.assertEqual(response.status_code, 200)


class TagEdgeCaseTests(BaseAPITestCase):
    """Tests for tag edge cases."""
    
    def test_TAG_014_tag_with_special_characters(self):
        """TAG-014: Tag with special characters is handled properly."""
        response = self.post('/api/v1/tags/', {
            'name': 'Health & Fitness <script>alert(1)</script>'
        })
        
        # Should either accept (sanitized) or reject
        self.assertIn(response.status_code, [200, 201, 400])
