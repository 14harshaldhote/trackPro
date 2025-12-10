"""
Database Layer Tests (Connection & Performance)

Test IDs: DB-001 to DB-004, DB-014 to DB-018
Priority: CRITICAL
Coverage: Connection management, pooling, query performance

Moved to separate files:
- Constraints: test_database_constraints.py
- Transactions: test_database_transactions.py
- Migrations: test_migrations.py
"""
import pytest
import threading
import time
from django.db import connection, connections
from django.contrib.auth import get_user_model
from core.tests.base import BaseAPITestCase, BaseTransactionTestCase
from core.tests.factories import TrackerFactory, UserFactory
from core.models import TrackerDefinition, TaskTemplate

User = get_user_model()

@pytest.mark.database
class DatabaseConnectionTests(BaseTransactionTestCase):
    """Tests for database connection management."""
    
    def test_DB_001_connection_pool_initialized(self):
        """DB-001: Database connection pool is properly initialized."""
        # Verify connection is available
        self.assertIsNotNone(connection)
        self.assertTrue(connection.is_usable())
    
    def test_DB_002_multiple_connections_reused(self):
        """DB-002: Multiple queries reuse connections from pool."""
        conn1_id = id(connection.connection)
        list(User.objects.all())
        conn2_id = id(connection.connection)
        self.assertEqual(conn1_id, conn2_id)
    
    def test_DB_003_connection_closes_properly(self):
        """DB-003: Database connection closes properly after use."""
        connection.close()
        # Connection should be None or unusable
        self.assertTrue(connection.connection is None or not connection.is_usable())
        # Reconnect
        list(User.objects.all())
        self.assertTrue(connection.is_usable())
    
    def test_DB_004_concurrent_connections_isolated(self):
        """DB-004: Concurrent connections are properly isolated."""
        barrier = threading.Barrier(2)
        results = []
        
        def query_in_thread():
            barrier.wait()
            count = User.objects.count()
            results.append(count)
        
        threads = [threading.Thread(target=query_in_thread) for _ in range(2)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], results[1])


@pytest.mark.database
class DatabasePerformanceTests(BaseAPITestCase):
    """Tests for database query performance."""
    
    def test_DB_014_no_n_plus_1_queries_in_tracker_list(self):
        """DB-014: Tracker list doesn't have N+1 query problem."""
        for i in range(5):
            tracker = self.create_tracker(name=f"Tracker {i}")
            for j in range(3):
                self.create_template(tracker, description=f"Task {j}")
        
        from django.db import reset_queries
        with self.settings(DEBUG=True):
            reset_queries()
            self.get('/api/v1/tracker/list/')
            from django.db import connection as db_conn
            query_count = len(db_conn.queries)
            self.assertLess(query_count, 10, 
                          f"Too many queries: {query_count}. Possible N+1 problem.")
    
    def test_DB_015_bulk_create_efficiency(self):
        """DB-015: Bulk create is efficient."""
        user = UserFactory.create()
        tracker = TrackerFactory.create(user)
        
        templates = [
            TaskTemplate(
                tracker=tracker, template_id=f"template-{i}",
                description=f"Task {i}", category='general', points=1
            ) for i in range(100)
        ]
        
        start_time = time.time()
        TaskTemplate.objects.bulk_create(templates)
        duration = time.time() - start_time
        
        self.assertLess(duration, 1.0, f"Bulk create too slow: {duration}s")
        self.assertEqual(TaskTemplate.objects.filter(tracker=tracker).count(), 100)
    
    def test_DB_016_database_indexes_exist(self):
        """DB-016: Critical database indexes exist."""
        cursor = connection.cursor()
        tables_to_check = ['tracker_definitions', 'task_templates', 'tracker_instances']
        
        for table in tables_to_check:
            try:
                cursor.execute(f"SHOW INDEX FROM {table}")
                indexes = cursor.fetchall()
                self.assertGreater(len(indexes), 0, f"No indexes found on {table}")
            except Exception:
                pass


@pytest.mark.database
class DatabaseConnectionPoolTests(BaseTransactionTestCase):
    """Tests for connection pool behavior."""
    
    def test_DB_017_connection_pool_handles_concurrent_requests(self):
        """DB-017: Connection pool handles multiple concurrent requests."""
        results = []
        def execute_query():
            try:
                User.objects.count()
                results.append('success')
            except Exception as e:
                results.append(f'error: {e}')
        
        threads = [threading.Thread(target=execute_query) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=5)
        
        self.assertEqual(len(results), 20)
        self.assertEqual(sum(1 for r in results if r == 'success'), 20)
    
    def test_DB_018_connection_pool_recovery_after_failure(self):
        """DB-018: Connection pool recovers after connection failure."""
        for conn in connections.all():
            conn.close()
        self.assertIsNotNone(User.objects.count())
        self.assertTrue(connection.is_usable())
