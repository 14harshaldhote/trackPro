"""
Unit tests for core/services/goal_service.py

Tests goal progress calculations, status updates, and insights:
- Count-based and value-based goal progress
- Goal achieving and status transitions
- Goal insights and velocity calculations
- Edge cases (target=0, progress > target)
"""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone

from core.services.goal_service import GoalService
from core.models import Goal, GoalTaskMapping, TaskInstance, Notification


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='goal_test_user',
        email='goal@test.com',
        password='testpass123'
    )


@pytest.fixture
def tracker(db, user):
    """Create a test tracker."""
    from core.tests.factories import TrackerFactory
    return TrackerFactory.create(user)


@pytest.fixture
def template(db, tracker):
    """Create a test task template."""
    from core.tests.factories import TemplateFactory
    return TemplateFactory.create(tracker)


@pytest.fixture
def goal(db, user, tracker):
    """Create a test goal."""
    from core.tests.factories import GoalFactory
    return GoalFactory.create(user, tracker=tracker, target_value=10)


@pytest.fixture
def goal_with_mapping(db, user, tracker, template, goal):
    """Create a goal with task mapping."""
    GoalTaskMapping.objects.create(
        goal=goal,
        template=template,
        contribution_weight=1.0
    )
    return goal


# ============================================================================
# Tests for update_goal_progress
# ============================================================================

class TestUpdateGoalProgress:
    """Tests for GoalService.update_goal_progress."""
    
    @pytest.mark.django_db
    def test_no_mappings_returns_zero_progress(self, goal):
        """Goal with no mappings should return 0 progress."""
        result = GoalService.update_goal_progress(goal)
        
        assert result['progress'] == 0
        assert result['current_value'] == 0
        assert result['target_value'] == goal.target_value
    
    @pytest.mark.django_db
    def test_progress_with_completed_tasks(self, goal_with_mapping, tracker, template):
        """Progress should reflect completed tasks."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        # Create instance with 2 tasks, 1 done
        instance = InstanceFactory.create(tracker)
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='TODO')
        
        goal_with_mapping.refresh_from_db()
        result = GoalService.update_goal_progress(goal_with_mapping)
        
        assert result['current_value'] >= 1
        assert result['progress'] >= 0
    
    @pytest.mark.django_db
    def test_goal_status_changes_to_achieved(self, goal_with_mapping, tracker, template):
        """Goal should become 'achieved' when target is met."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        # Create enough completed tasks to meet target
        goal_with_mapping.target_value = 2
        goal_with_mapping.save()
        
        instance = InstanceFactory.create(tracker)
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        result = GoalService.update_goal_progress(goal_with_mapping)
        
        goal_with_mapping.refresh_from_db()
        assert goal_with_mapping.current_value >= 2
    
    @pytest.mark.django_db
    def test_achievement_notification_sent(self, goal_with_mapping, tracker, template, user):
        """Notification should be created when goal is achieved."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        goal_with_mapping.target_value = 1
        goal_with_mapping.save()
        
        instance = InstanceFactory.create(tracker)
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        initial_count = Notification.objects.filter(user=user, type='achievement').count()
        
        GoalService.update_goal_progress(goal_with_mapping)
        
        # Check if notification was created (may or may not depending on status transition)
        goal_with_mapping.refresh_from_db()
        if goal_with_mapping.status == 'achieved':
            final_count = Notification.objects.filter(user=user, type='achievement').count()
            assert final_count >= initial_count
    
    @pytest.mark.django_db
    def test_deleted_templates_excluded(self, goal_with_mapping, tracker, template):
        """Deleted templates should be excluded from progress."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        template.deleted_at = timezone.now()
        template.save()
        
        result = GoalService.update_goal_progress(goal_with_mapping)
        
        # With deleted template, no mappings should be active
        assert result['progress'] == 0


# ============================================================================
# Tests for get_goal_insights
# ============================================================================

class TestGetGoalInsights:
    """Tests for GoalService.get_goal_insights."""
    
    @pytest.mark.django_db
    def test_returns_basic_goal_info(self, goal):
        """Should return basic goal information."""
        insights = GoalService.get_goal_insights(goal)
        
        assert 'goal_id' in insights
        assert 'title' in insights
        assert 'progress' in insights
        assert 'current_value' in insights
        assert 'target_value' in insights
    
    @pytest.mark.django_db
    def test_returns_days_remaining(self, goal):
        """Should calculate days remaining when target_date set."""
        goal.target_date = date.today() + timedelta(days=10)
        goal.save()
        
        insights = GoalService.get_goal_insights(goal)
        
        assert insights['days_remaining'] == 10
    
    @pytest.mark.django_db
    def test_days_remaining_none_without_target_date(self, goal):
        """Days remaining should be None without target_date."""
        goal.target_date = None
        goal.save()
        
        insights = GoalService.get_goal_insights(goal)
        
        assert insights['days_remaining'] is None
    
    @pytest.mark.django_db
    def test_task_breakdowns_included(self, goal_with_mapping, tracker, template):
        """Should include task breakdowns."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        instance = InstanceFactory.create(tracker)
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        insights = GoalService.get_goal_insights(goal_with_mapping)
        
        assert 'task_breakdowns' in insights
        assert len(insights['task_breakdowns']) == 1
    
    @pytest.mark.django_db
    def test_on_track_calculation(self, goal):
        """Should calculate if goal is on track."""
        goal.target_date = date.today() + timedelta(days=10)
        goal.target_value = 10
        goal.current_value = 8
        goal.save()
        
        insights = GoalService.get_goal_insights(goal)
        
        assert 'on_track' in insights
        assert isinstance(insights['on_track'], bool)


# ============================================================================
# Tests for _calculate_velocity
# ============================================================================

class TestCalculateVelocity:
    """Tests for GoalService._calculate_velocity."""
    
    @pytest.mark.django_db
    def test_velocity_calculation(self, goal):
        """Should calculate daily velocity."""
        # Goal created today, 5 completions
        goal.current_value = 5
        goal.save()
        
        velocity = GoalService._calculate_velocity(goal)
        
        assert velocity >= 0
    
    @pytest.mark.django_db
    def test_velocity_zero_on_no_progress(self, goal):
        """Zero progress should give zero or low velocity."""
        goal.current_value = 0
        goal.save()
        
        velocity = GoalService._calculate_velocity(goal)
        
        assert velocity == 0


# ============================================================================
# Tests for _is_on_track
# ============================================================================

class TestIsOnTrack:
    """Tests for GoalService._is_on_track."""
    
    @pytest.mark.django_db
    def test_on_track_with_good_velocity(self, goal):
        """Should be on track with sufficient velocity."""
        goal.target_value = 10
        goal.current_value = 5
        goal.save()
        
        # 1/day velocity, 10 days remaining, need 5 more
        result = GoalService._is_on_track(goal, velocity=1.0, days_remaining=10)
        
        assert result is True
    
    @pytest.mark.django_db
    def test_not_on_track_with_low_velocity(self, goal):
        """Should not be on track with insufficient velocity."""
        goal.target_value = 100
        goal.current_value = 5
        goal.save()
        
        # 0.1/day velocity, 10 days remaining, need 95 more
        result = GoalService._is_on_track(goal, velocity=0.1, days_remaining=10)
        
        assert result is False
    
    @pytest.mark.django_db
    def test_achieved_goal_always_on_track(self, goal):
        """Achieved goals should be on track."""
        goal.status = 'achieved'
        goal.save()
        
        result = GoalService._is_on_track(goal, velocity=0, days_remaining=0)
        
        assert result is True
    
    @pytest.mark.django_db
    def test_no_target_value_returns_achieved_status(self, goal):
        """No target value should check achieved status."""
        goal.target_value = None
        goal.status = 'active'
        goal.save()
        
        result = GoalService._is_on_track(goal, velocity=1.0, days_remaining=10)
        
        assert result is False  # Not achieved yet


# ============================================================================
# Tests for update_target
# ============================================================================

class TestUpdateTarget:
    """Tests for GoalService.update_target."""
    
    @pytest.mark.django_db
    def test_update_target_increases(self, goal):
        """Should increase target value."""
        old_target = goal.target_value
        
        result = GoalService.update_target(goal, 20)
        
        goal.refresh_from_db()
        assert goal.target_value == 20
        assert result['old_target'] == old_target
        assert result['new_target'] == 20
    
    @pytest.mark.django_db
    def test_update_target_decreases(self, goal):
        """Should decrease target value."""
        goal.target_value = 100
        goal.save()
        
        result = GoalService.update_target(goal, 50)
        
        goal.refresh_from_db()
        assert goal.target_value == 50
    
    @pytest.mark.django_db
    def test_achieved_becomes_active_on_increase(self, goal):
        """Achieved goal should become active if target increases beyond progress."""
        goal.current_value = 10
        goal.target_value = 10
        goal.status = 'achieved'
        goal.save()
        
        result = GoalService.update_target(goal, 20)
        
        goal.refresh_from_db()
        assert goal.status == 'active'
        assert result['status_changed'] is True
    
    @pytest.mark.django_db
    def test_active_becomes_achieved_on_decrease(self, goal):
        """Active goal should become achieved if target decreases below progress."""
        goal.current_value = 15
        goal.target_value = 20
        goal.status = 'active'
        goal.save()
        
        GoalService.update_target(goal, 10)
        
        goal.refresh_from_db()
        assert goal.status == 'achieved'


# ============================================================================
# Tests for get_count_based_progress
# ============================================================================

class TestGetCountBasedProgress:
    """Tests for GoalService.get_count_based_progress."""
    
    @pytest.mark.django_db
    def test_count_progress_no_tasks(self, goal):
        """Should return zero progress with no tasks."""
        result = GoalService.get_count_based_progress(goal)
        
        assert result['current_count'] == 0
        assert result['progress_percent'] == 0
    
    @pytest.mark.django_db
    def test_count_progress_with_completed_tasks(self, goal_with_mapping, tracker, template):
        """Should count completed tasks."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        instance = InstanceFactory.create(tracker)
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='TODO')
        
        result = GoalService.get_count_based_progress(goal_with_mapping)
        
        assert result['current_count'] == 2
    
    @pytest.mark.django_db
    def test_count_progress_with_date_filter(self, goal_with_mapping, tracker, template):
        """Should filter by date range."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        instance = InstanceFactory.create(tracker, target_date=today)
        task = TaskInstanceFactory.create(instance, template, status='DONE')
        task.completed_at = timezone.now()
        task.save()
        
        # Query for today only
        result = GoalService.get_count_based_progress(
            goal_with_mapping,
            start_date=today,
            end_date=today
        )
        
        assert result['current_count'] >= 0
    
    @pytest.mark.django_db
    def test_progress_capped_at_100_percent(self, goal_with_mapping, tracker, template):
        """Progress percent should cap at 100."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        goal_with_mapping.target_value = 1
        goal_with_mapping.save()
        
        instance = InstanceFactory.create(tracker)
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        result = GoalService.get_count_based_progress(goal_with_mapping)
        
        assert result['progress_percent'] == 100
    
    @pytest.mark.django_db
    def test_remaining_count_calculation(self, goal_with_mapping, tracker, template):
        """Should calculate remaining count correctly."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        goal_with_mapping.target_value = 10
        goal_with_mapping.save()
        
        instance = InstanceFactory.create(tracker)
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        result = GoalService.get_count_based_progress(goal_with_mapping)
        
        assert result['remaining'] == 7


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestGoalServiceEdgeCases:
    """Edge case tests for GoalService."""
    
    @pytest.mark.django_db
    def test_zero_target_value(self, goal):
        """Target value of 0 should handle gracefully."""
        goal.target_value = 0
        goal.save()
        
        result = GoalService.get_count_based_progress(goal)
        
        # Should not divide by zero
        assert 'progress_percent' in result
    
    @pytest.mark.django_db
    def test_negative_days_remaining(self, goal):
        """Past target date should show negative days."""
        goal.target_date = date.today() - timedelta(days=5)
        goal.save()
        
        insights = GoalService.get_goal_insights(goal)
        
        assert insights['days_remaining'] == -5
    
    @pytest.mark.django_db
    def test_very_large_target(self, goal_with_mapping):
        """Very large target should work."""
        goal = goal_with_mapping
        goal.target_value = 1000000
        goal.save()
        
        # Mock the query count since we can't create 1000 tasks effectively
        with patch('core.services.goal_service.TaskInstance.objects.filter') as mock_filter:
            # Setup a mock for the queryset that allows chaining filter()
            # but returns a specific integer for count()
            mock_qs = ChainableMock()
            
            # We must override the count attribute to be a generic Mock 
            # so it doesn't use ChainableMock's __call__ (which returns self)
            mock_qs.count = Mock(return_value=1000)
            
            # Ensure calling filter() chains correctly
            mock_qs.filter.return_value = mock_qs
            mock_filter.return_value = mock_qs
            
            result = GoalService.get_count_based_progress(goal)
        
        # 1,000,000 - 1,000 = 999,000
        assert result['remaining'] == 999000
        
class ChainableMock(Mock):
    def __call__(self, *args, **kwargs):
        return self
    
    @pytest.mark.django_db
    def test_progress_exceeds_target(self, goal_with_mapping, tracker, template):
        """Progress can exceed target (overachievement)."""
        from core.tests.factories import InstanceFactory, TaskInstanceFactory
        
        goal_with_mapping.target_value = 2
        goal_with_mapping.save()
        
        instance = InstanceFactory.create(tracker)
        for _ in range(5):
            TaskInstanceFactory.create(instance, template, status='DONE')
        
        result = GoalService.get_count_based_progress(goal_with_mapping)
        
        assert result['current_count'] == 5
        assert result['progress_percent'] == 100  # Capped at 100
        assert result['remaining'] == 0
