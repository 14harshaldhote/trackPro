
from django.test import TestCase
from datetime import date, timedelta
from unittest.mock import patch, Mock
from core.services.habit_intelligence_service import HabitIntelligenceService
from core.models import DayNote
from core.tests.factories import UserFactory, TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory

class TestHabitIntelligenceServiceUnit(TestCase):

    def setUp(self):
        self.user = UserFactory.create(username="habit_user")
        self.tracker = TrackerFactory.create(user=self.user)
        self.template = TemplateFactory.create(tracker=self.tracker, description="Gym")

    def test_analyze_day_of_week_patterns(self):
        # Create tasks for Monday (0) - DONE
        # Create tasks for Sunday (6) - MISSED
        today = date.today()
        # Find a Monday and Sunday within last 90 days
        monday = today - timedelta(days=today.weekday()) # This Monday
        if monday == today: monday -= timedelta(days=7) # Ensure it is in past if needed, though today works
        
        # Ensure Monday is Monday
        monday = today - timedelta(days=today.weekday())
        
        # Sunday: monday - 1 day
        sunday = monday - timedelta(days=1)
        
        # Check if they are in range (Start date is today - 90).
        # monday is close to today. Sunday is close to today. Safe.
        
        inst_mon = InstanceFactory.create(tracker=self.tracker, target_date=monday)
        TaskInstanceFactory.create(instance=inst_mon, template=self.template, status='DONE')
        
        inst_sun = InstanceFactory.create(tracker=self.tracker, target_date=sunday)
        TaskInstanceFactory.create(instance=inst_sun, template=self.template, status='MISSED')
        
        # Test
        res = HabitIntelligenceService.analyze_day_of_week_patterns(self.user.pk)
        
        # Verify results
        # Monday is 0. Sunday is 6.
        # Note: Sunday date calculated as Monday - 1 is previous Sunday.
        # Is Sunday 6? Yes. .weekday() returns 6.
        
        by_day = {d['day']: d for d in res['by_day']}
        assert by_day[0]['completion_rate'] == 100.0
        assert by_day[6]['miss_rate'] == 100.0
        
        # Best day should be Monday
        assert res['best_day']['day'] == 0
        assert res['worst_day']['day'] == 6

    def test_analyze_task_difficulty(self):
        # Create 5 instances (min required)
        # 3 DONE, 1 MISSED, 1 IN_PROGRESS
        for i in range(5):
            day = date.today() - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            
            if i < 3: status = 'DONE'
            elif i == 3: status = 'MISSED'
            else: status = 'IN_PROGRESS'
            
            TaskInstanceFactory.create(instance=inst, template=self.template, status=status)
            
        res = HabitIntelligenceService.analyze_task_difficulty(self.user.pk)
        assert len(res) == 1
        item = res[0]
        assert item['total_instances'] == 5
        assert item['completion_rate'] == 60.0
        assert item['miss_rate'] == 20.0

    @patch('core.services.streak_service.StreakService')
    def test_find_streak_correlations(self, mock_streak_service):
        # Mock StreakService to return streak >= 7
        mock_streak_data = Mock()
        mock_streak_data.current_streak = 10
        mock_streak_service.calculate_streak.return_value = mock_streak_data
        
        # Create 10 days of data with Gym tasks DONE
        today = date.today()
        for i in range(10):
            day = today - timedelta(days=i)
            inst = InstanceFactory.create(tracker=self.tracker, target_date=day)
            TaskInstanceFactory.create(instance=inst, template=self.template, status='DONE')
            
        res = HabitIntelligenceService.find_streak_correlations(self.user.pk)
        
        # Should find correlation
        # "Your {tracker.name} streak relies on consistently doing: gym"
        assert len(res['correlations']) == 1
        # Use lower case comparison because description might be normalized or not
        assert "Gym" in res['correlations'][0]['anchor_tasks'][0]['description']

    def test_analyze_mood_task_correlation(self):
        # Create DayNote with high mood + DONE task
        day1 = date.today() - timedelta(days=1)
        DayNote.objects.create(tracker=self.tracker, date=day1, sentiment_score=0.9, content="Happy")
        inst1 = InstanceFactory.create(tracker=self.tracker, target_date=day1)
        TaskInstanceFactory.create(instance=inst1, template=self.template, status='DONE')
        
        # Create DayNote with low mood + MISSED task
        day2 = date.today() - timedelta(days=2)
        DayNote.objects.create(tracker=self.tracker, date=day2, sentiment_score=0.2, content="Sad")
        inst2 = InstanceFactory.create(tracker=self.tracker, target_date=day2)
        TaskInstanceFactory.create(instance=inst2, template=self.template, status='MISSED')
        
        res = HabitIntelligenceService.analyze_mood_task_correlation(self.user.pk)
        
        # High mood completion should be 100% (1/1)
        # Low mood completion should be 0% (0/1)
        assert res['high_mood_completion_rate'] == 100.0
        assert res['low_mood_completion_rate'] == 0.0
        assert len(res['insights']) > 0

    def test_get_optimal_schedule_suggestions(self):
        # We need to mock analyze_day_of_week and analyze_task_difficulty
        # Or just populate data carefully.
        # Let's mock the static methods to simplify
        with patch.object(HabitIntelligenceService, 'analyze_day_of_week_patterns') as mock_dow, \
             patch.object(HabitIntelligenceService, 'analyze_task_difficulty') as mock_diff:
             
            mock_dow.return_value = {
                'best_day': {'day_name': 'Monday', 'day': 0},
                'worst_day': {'day_name': 'Sunday', 'miss_rate': 60}
            }
            mock_diff.return_value = [
                {'description': 'Gym', 'miss_rate': 55}
            ]
            
            res = HabitIntelligenceService.get_optimal_schedule_suggestions(self.user.pk)
            
            # Suggest moving Gym to Monday
            assert len(res) >= 1
            assert "Consider moving 'Gym' to Monday" in res[0]['suggestion']
            # Suggest reducing load on Sunday
            assert any("reducing your task load on Sunday" in r['suggestion'] for r in res)

    def test_generate_all_insights(self):
        # Just ensure it calls all methods and aggregates
         with patch.object(HabitIntelligenceService, 'analyze_day_of_week_patterns') as mock_dow, \
             patch.object(HabitIntelligenceService, 'analyze_task_difficulty') as mock_diff, \
             patch.object(HabitIntelligenceService, 'find_streak_correlations') as mock_streak, \
             patch.object(HabitIntelligenceService, 'analyze_mood_task_correlation') as mock_mood, \
             patch.object(HabitIntelligenceService, 'get_optimal_schedule_suggestions') as mock_sug:
            
            mock_dow.return_value = {'best_day': None, 'worst_day': None, 'insights': []}
            mock_diff.return_value = []
            mock_streak.return_value = {}
            mock_mood.return_value = {}
            mock_sug.return_value = []
            
            res = HabitIntelligenceService.generate_all_insights(self.user.pk)
            assert 'insights' in res
            assert 'analysis' in res
