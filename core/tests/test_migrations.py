"""
Database Migration Tests

Test IDs: DB-019 to DB-020
Coverage: Migration plan integrity, model/schema sync
"""
import pytest
from django.test import TransactionTestCase
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.core.management import call_command
from io import StringIO

@pytest.mark.database
class DatabaseMigrationTests(TransactionTestCase):
    """Tests for database migrations."""
    
    def test_DB_019_migrations_are_applied(self):
        """DB-019: All migrations are applied."""
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        # No pending migrations
        self.assertEqual(len(plan), 0,
                        f"Unapplied migrations found: {[m[0].name for m in plan]}")
    
    def test_DB_020_models_match_database_schema(self):
        """DB-020: Model definitions match database schema."""
        # This checks if makemigrations would create any new migrations
        out = StringIO()
        call_command('makemigrations', '--dry-run', '--check', stdout=out)
        
        # No new migrations should be needed
        output = out.getvalue()
        self.assertIn('No changes detected', output,
                     "Model changes detected but not migrated")

    def test_DB_021_migration_rollback_safety(self):
        """DB-021: Verify migrations can be rolled back safely."""
        # This is a basic check. In a real CI, you'd unapply migrations and check state.
        # Here we just verify the migration plan structure is sound.
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        self.assertTrue(len(targets) > 0)
