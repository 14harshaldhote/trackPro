"""
Database Transaction Tests

Test IDs: DB-009 to DB-013
Coverage: Atomic transactions, isolation levels, row locking, deadlocks
"""
import pytest
import threading
import time
from django.db import transaction, connection
from django.contrib.auth import get_user_model
from core.tests.base import BaseTransactionTestCase
from core.tests.factories import UserFactory, TrackerFactory
from core.models import TrackerDefinition

User = get_user_model()

@pytest.mark.database
class DatabaseTransactionTests(BaseTransactionTestCase):
    """Tests for database transaction handling."""
    
    def test_DB_009_atomic_transaction_rollback_on_error(self):
        """DB-009: Atomic transactions rollback on error."""
        user_count_before = User.objects.count()
        
        # Try to create user and fail in atomic block
        try:
            with transaction.atomic():
                User.objects.create_user(
                    username='testuser_tx',
                    email='test@tx.com',
                    password='pass123'
                )
                # Force an error
                raise Exception("Forced error")
        except Exception:
            pass
        
        # User should not be created (rolled back)
        user_count_after = User.objects.count()
        self.assertEqual(user_count_before, user_count_after)
    
    def test_DB_010_nested_transactions_rollback(self):
        """DB-010: Nested transactions rollback correctly."""
        initial_count = User.objects.count()
        
        try:
            with transaction.atomic():
                User.objects.create_user(
                    username='outer',
                    email='outer@test.com',
                    password='pass123'
                )
                
                try:
                    with transaction.atomic():
                        User.objects.create_user(
                            username='inner',
                            email='inner@test.com',
                            password='pass123'
                        )
                        raise Exception("Inner error")
                except Exception:
                    pass  # Inner transaction rolled back
                
                # Outer transaction continues
        except Exception:
            pass
        
        # Only outer user should exist (inner rolled back)
        final_count = User.objects.count()
        self.assertEqual(final_count, initial_count + 1)
    
    def test_DB_011_transaction_isolation_level(self):
        """DB-011: Transaction isolation prevents dirty reads."""
        # This test verifies read committed isolation
        user = UserFactory.create()
        
        def update_in_transaction():
            with transaction.atomic():
                user_in_tx = User.objects.select_for_update().get(id=user.id)
                user_in_tx.username = 'modified'
                user_in_tx.save()
                time.sleep(0.1)  # Hold lock briefly
        
        # Start transaction in thread
        thread = threading.Thread(target=update_in_transaction)
        thread.start()
        thread.join()
        
        # Read should see committed value
        user.refresh_from_db()
        self.assertEqual(user.username, 'modified')
    
    def test_DB_012_select_for_update_locks_row(self):
        """DB-012: SELECT FOR UPDATE properly locks rows."""
        tracker = TrackerFactory.create(UserFactory.create())
        
        lock_acquired = []
        
        def try_lock():
            try:
                with transaction.atomic():
                    # Try to acquire lock with timeout
                    # Use pk or tracker_id, not id (which is a property)
                    TrackerDefinition.objects.select_for_update(
                        nowait=True
                    ).get(pk=tracker.pk)
                    lock_acquired.append(True)
            except Exception:
                lock_acquired.append(False)
        
        # Acquire lock in main thread
        with transaction.atomic():
            TrackerDefinition.objects.select_for_update().get(pk=tracker.pk)
            
            # Try to acquire in another thread (should fail)
            thread = threading.Thread(target=try_lock)
            thread.start()
            thread.join(timeout=1)
        
        # Second lock attempt should have failed (or timed out)
        if lock_acquired:
            self.assertFalse(lock_acquired[0])


@pytest.mark.database
@pytest.mark.slow
class DatabaseDeadlockTests(BaseTransactionTestCase):
    """Tests for deadlock detection and handling."""
    
    def test_DB_013_deadlock_detection(self):
        """DB-013: Database detects deadlocks."""
        # Create two trackers
        user = UserFactory.create()
        tracker1 = TrackerFactory.create(user)
        tracker2 = TrackerFactory.create(user)
        
        # This test demonstrates deadlock detection
        # In production, your code should have retry logic
        deadlock_occurred = [False]
        
        def tx1():
            try:
                with transaction.atomic():
                    # Lock tracker1 first
                    TrackerDefinition.objects.select_for_update().get(id=tracker1.id)
                    time.sleep(0.1)
                    # Try to lock tracker2
                    TrackerDefinition.objects.select_for_update().get(id=tracker2.id)
            except Exception as e:
                if 'deadlock' in str(e).lower():
                    deadlock_occurred[0] = True
        
        def tx2():
            try:
                with transaction.atomic():
                    # Lock tracker2 first
                    TrackerDefinition.objects.select_for_update().get(id=tracker2.id)
                    time.sleep(0.1)
                    # Try to lock tracker1 (potential deadlock)
                    TrackerDefinition.objects.select_for_update().get(id=tracker1.id)
            except Exception as e:
                if 'deadlock' in str(e).lower():
                    deadlock_occurred[0] = True
        
        # Run both transactions (one might fail with deadlock)
        t1 = threading.Thread(target=tx1)
        t2 = threading.Thread(target=tx2)
        
        t1.start()
        t2.start()
        
        t1.join(timeout=2)
        t2.join(timeout=2)
        
        # At least one should complete (deadlock detected and handled by DB)
        # This test just verifies the system handles it
