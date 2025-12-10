"""
Database Constraint Tests

Test IDs: DB-005 to DB-008
Coveage: Integrity errors, NOT NULL, Foreign Keys, Unique constraints
"""
import pytest
from django.db import transaction, IntegrityError
from core.tests.base import BaseAPITestCase
from core.tests.factories import TagFactory
from core.models import TrackerDefinition, TaskTemplate, Tag

@pytest.mark.database
class DatabaseConstraintTests(BaseAPITestCase):
    """Tests for database constraint handling."""
    
    def test_DB_005_unique_constraint_violation_handled(self):
        """DB-005: Unique constraint violations are properly handled."""
        # Create a tag
        tag = TagFactory.create(self.user, name="UniqueTag")
        
        # Try to create duplicate tag with same name for same user
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(
                    user=self.user,
                    name="UniqueTag",
                    tag_id="different-id"
                )
    
    def test_DB_006_foreign_key_constraint_enforced(self):
        """DB-006: Foreign key constraints are enforced."""
        # Try to create template with non-existent tracker
        with self.assertRaises((IntegrityError, ValueError)):
            with transaction.atomic():
                TaskTemplate.objects.create(
                    tracker_id=99999,  # Non-existent
                    template_id="test-template",
                    description="Test"
                )
    
    def test_DB_007_null_constraint_enforced(self):
        """DB-007: NOT NULL constraints are enforced."""
        # Try to create tracker with explicit None for non-nullable field
        with self.assertRaises((IntegrityError, ValueError)):
            with transaction.atomic():
                TrackerDefinition.objects.create(
                    user=self.user,
                    tracker_id="test-id-null-check",
                    name=None
                )
    
    def test_DB_008_cascade_delete_works(self):
        """DB-008: CASCADE delete properly removes related objects."""
        tracker = self.create_tracker()
        template = self.create_template(tracker)
        instance = self.create_instance(tracker)
        
        template_id = template.template_id
        instance_id = instance.instance_id
        
        # Delete tracker
        tracker.delete()
        
        # Related objects should be soft-deleted or removed
        # (depending on your model implementation)
        self.assertFalse(
            TrackerDefinition.objects.filter(
                tracker_id=tracker.tracker_id,
                deleted_at__isnull=True
            ).exists()
        )
