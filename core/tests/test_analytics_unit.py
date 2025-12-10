
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta
from core import analytics

class TestAnalyticsUnit:

    @pytest.fixture
    def mock_crud(self):
        with patch('core.analytics.crud') as mock:
            yield mock

    @pytest.fixture
    def mock_nlp(self):
        with patch('core.analytics.nlp_utils') as mock:
            yield mock
    
    @pytest.fixture
    def mock_metric_helpers(self):
        with patch('core.analytics.metric_helpers') as mock:
            yield mock

    def test_compute_completion_rate_no_data(self, mock_crud):
        mock_crud.get_tracker_instances_with_tasks.return_value = []
        result = analytics.compute_completion_rate('tracker-no-data')
        assert result['value'] == 0.0
        assert result['daily_rates'] == []

    def test_compute_completion_rate_with_data(self, mock_crud):
        inst1 = Mock()
        inst1.period_start = date(2023, 1, 1)
        # Mock tasks
        t1 = Mock(status='DONE')
        t2 = Mock(status='TODO')
        inst1.tasks.all.return_value = [t1, t2]

        inst2 = Mock()
        inst2.period_start = "2023-01-02"
        t3 = Mock(status='DONE')
        inst2.tasks.all.return_value = [t3]

        mock_crud.get_tracker_instances_with_tasks.return_value = [inst1, inst2]

        result = analytics.compute_completion_rate('tracker-with-data')
        
        assert result['value'] == (2/3) * 100
        assert len(result['daily_rates']) == 2
        assert result['daily_rates'][0]['rate'] == 50.0
        assert result['daily_rates'][1]['rate'] == 100.0

    def test_detect_streaks_no_data(self, mock_crud):
        mock_crud.get_tracker_instances_with_tasks.return_value = []
        result = analytics.detect_streaks('tracker-streaks-no-data')
        assert result['value']['current_streak'] == 0
        assert result['value']['longest_streak'] == 0

    def test_detect_streaks_with_data(self, mock_crud, mock_metric_helpers):
        inst1 = Mock(period_start=date(2023, 1, 1))
        inst1.tasks.all.return_value = [Mock(status='DONE')] # True
        
        inst2 = Mock(period_start=date(2023, 1, 2))
        inst2.tasks.all.return_value = [Mock(status='TODO')] # False
        
        inst3 = Mock(period_start=date(2023, 1, 3))
        inst3.tasks.all.return_value = [Mock(status='DONE')] # True

        mock_crud.get_tracker_instances_with_tasks.return_value = [inst1, inst2, inst3]
        
        mock_metric_helpers.detect_streaks.return_value = {'current': 1, 'best': 1}

        result = analytics.detect_streaks('tracker-streaks-data')
        
        # Should verify that metric_helpers.detect_streaks was called with boolean list
        # sorted day 1: T, day 2: F, day 3: T -> [True, False, True] (if dict sort works)
        # However, dict order is not guaranteed until python 3.7+ (and we rely on sorted() on items)
        
        assert result['value']['current_streak'] == 1
        assert result['value']['longest_streak'] == 1

    def test_detect_streaks_with_template_filter(self, mock_crud):
        inst1 = Mock(period_start=date(2023, 1, 1))
        t1 = Mock(status='DONE')
        t1.template_id = 't1'
        inst1.tasks.all.return_value = [t1]

        mock_crud.get_tracker_instances_with_tasks.return_value = [inst1]
        
        with patch('core.analytics.metric_helpers.detect_streaks') as mock_ds:
            mock_ds.return_value = {'current': 1, 'best': 1}
            analytics.detect_streaks('tracker-streaks-filter', task_template_id='t1')
            mock_ds.assert_called()

    def test_compute_consistency_score_no_data(self, mock_crud):
        mock_crud.get_tracker_instances_with_tasks.return_value = []
        result = analytics.compute_consistency_score('tracker-consistency-no-data')
        assert result['value'] == 0.0

    def test_compute_consistency_score(self, mock_crud):
        insts = []
        for i in range(10):
            inst = Mock(period_start=date(2023, 1, 1) + timedelta(days=i))
            inst.tasks.all.return_value = [Mock(status='DONE')]
            insts.append(inst)
        
        mock_crud.get_tracker_instances_with_tasks.return_value = insts
        
        result = analytics.compute_consistency_score('tracker-consistency', window_days=5)
        assert result['value'] == 100.0
        assert len(result['rolling_scores']) == 10

    def test_compute_balance_score(self, mock_crud):
        t1 = Mock(template_id=1, category='Health')
        t2 = Mock(template_id=2, category='Work')
        mock_crud.get_task_templates_for_tracker.return_value = [t1, t2]

        inst = Mock()
        task1 = Mock(template_id=1)
        task2 = Mock(template_id=2)
        inst.tasks.all.return_value = [task1, task2]
        mock_crud.get_tracker_instances_with_tasks.return_value = [inst]

        result = analytics.compute_balance_score('tracker-balance')
        # 1 Health, 1 Work. Perfectly balanced.
        assert result['value'] == 100.0
        assert result['raw_inputs']['entropy'] == 1.0 # - (0.5log0.5 + 0.5log0.5) = - (-0.5 -0.5) = 1

    def test_compute_balance_score_empty(self, mock_crud):
        mock_crud.get_task_templates_for_tracker.return_value = []
        mock_crud.get_tracker_instances_with_tasks.return_value = []
        result = analytics.compute_balance_score('tracker-balance-empty')
        assert result['value'] == 0.0

    def test_compute_effort_index(self, mock_crud):
        t1 = Mock(template_id=1, weight=5)
        mock_crud.get_task_templates_for_tracker.return_value = [t1]
        
        inst = Mock()
        task = Mock(template_id=1, status='DONE')
        inst.tasks.all.return_value = [task]
        mock_crud.get_tracker_instances_with_tasks.return_value = [inst]
        
        result = analytics.compute_effort_index('tracker-effort')
        assert result['value'] == 5.0

    def test_analyze_notes_sentiment(self, mock_crud, mock_nlp):
        mock_crud.db.fetch_filter.return_value = [
            {'date': '2023-01-01', 'content': 'Good day'},
            {'date': date(2023, 1, 2), 'content': 'Bad day'}
        ]
        mock_nlp.compute_sentiment.side_effect = [
            {'compound': 0.5, 'pos': 0.5, 'neu': 0.5, 'neg': 0},
            {'compound': -0.5, 'pos': 0, 'neu': 0.5, 'neg': 0.5},
        ]
        
        result = analytics.analyze_notes_sentiment('tracker-123')
        assert result['raw_inputs']['note_count'] == 2
        assert result['average_mood'] == 0.0 # (0.5 - 0.5) / 2

    def test_analyze_notes_sentiment_empty(self, mock_crud):
        mock_crud.db.fetch_filter.return_value = []
        result = analytics.analyze_notes_sentiment('tracker-123')
        assert result['average_mood'] == 0.0

    def test_extract_keywords_from_notes(self, mock_crud, mock_nlp):
        mock_crud.db.fetch_filter.return_value = [{'content': 'Test note'}]
        mock_nlp.extract_keywords.return_value = [('test', 1)]
        
        result = analytics.extract_keywords_from_notes('tracker-123')
        assert result['keywords'] == [('test', 1)]

    def test_compute_mood_trends(self, mock_crud):
        with patch('core.analytics.analyze_notes_sentiment') as mock_ans:
            mock_ans.return_value = {
                'daily_mood': [
                    {'date': '2023-01-01', 'compound': 0.1},
                    {'date': '2023-01-02', 'compound': 0.2},
                    {'date': '2023-01-03', 'compound': 0.3}
                ]
            }
            result = analytics.compute_mood_trends('tracker-123', window_days=2)
            assert len(result['rolling_mood']) == 3
            # Last point: (0.2 + 0.3) / 2 = 0.25
            assert result['rolling_mood'][-1]['mood'] == 0.25

    def test_compute_mood_trends_empty(self, mock_crud):
        with patch('core.analytics.analyze_notes_sentiment') as mock_ans:
            mock_ans.return_value = {'daily_mood': []}
            result = analytics.compute_mood_trends('tracker-123')
            assert result['rolling_mood'] == []

    def test_visualizations(self):
        assert analytics.generate_completion_chart('t') is None
        assert analytics.generate_category_pie_chart('t') is None
        assert analytics.generate_completion_heatmap('t') is None
        assert analytics.generate_streak_timeline('t') is None

    def test_compute_tracker_stats(self):
        with patch('core.analytics.compute_completion_rate') as mock_cr, \
             patch('core.analytics.detect_streaks') as mock_ds:
            
            mock_cr.return_value = {'value': 50.0, 'raw_inputs': {'total_tasks': 10, 'completed_tasks': 5}}
            mock_ds.return_value = {'value': {'current_streak': 3}}
            
            result = analytics.compute_tracker_stats('t')
            assert result['completion_rate'] == 50.0
            assert result['current_streak'] == 3

    def test_compute_correlations(self, mock_crud, mock_metric_helpers):
        # Mock compute_completion_rate and analyze_notes_sentiment
        with patch('core.analytics.compute_completion_rate') as mock_cr, \
             patch('core.analytics.analyze_notes_sentiment') as mock_ans:
            
            mock_cr.return_value = {
                'daily_rates': [
                    {'date': '2023-01-01', 'rate': 100},
                    {'date': '2023-01-02', 'rate': 50}
                ]
            }
            mock_ans.return_value = {
                'daily_mood': [
                    {'date': '2023-01-01', 'compound': 0.8},
                    {'date': '2023-01-02', 'compound': 0.4}
                ]
            }
            
            # For effort, we mock crud
            mock_crud.get_tracker_instances.return_value = [] # skip effort for simplicity or minimal test
            
            mock_metric_helpers.calculate_correlation.return_value = 0.9
            
            result = analytics.compute_correlations('t', metrics=['completion_rate', 'mood'])
            
            assert 'correlation_matrix' in result
            assert result['correlation_matrix']['completion_rate']['mood'] == 0.9

    def test_analyze_time_series(self, mock_metric_helpers):
        with patch('core.analytics.compute_completion_rate') as mock_cr:
            mock_cr.return_value = {
                'daily_rates': [{'rate': 10}, {'rate': 20}]
            }
            mock_metric_helpers.compute_trend_line_pure_python.return_value = {'slope': 1, 'direction': 1}
            mock_metric_helpers.exponential_moving_average.return_value = [10, 20]
            
            result = analytics.analyze_time_series('t')
            
            assert result['trend']['direction'] == 'improving'
            assert len(result['forecast']['forecast']) == 7

    def test_analyze_time_series_empty(self, mock_metric_helpers):
        with patch('core.analytics.compute_completion_rate') as mock_cr:
            mock_cr.return_value = {'daily_rates': []}
            result = analytics.analyze_time_series('t')
            assert result['trend']['direction'] == 'stable'

    def test_analyze_trends(self, mock_metric_helpers):
        with patch('core.analytics.compute_completion_rate') as mock_cr:
            mock_cr.return_value = {
                'daily_rates': [
                    {'date': '2023-01-01', 'rate': 10}, 
                    {'date': '2023-01-02', 'rate': 20}
                ]
            }
            mock_metric_helpers.exponential_moving_average.return_value = [10.0, 20.0]
            
            result = analytics.analyze_trends('t')
            
            assert result['trend_direction'] == 'improving'
            assert result['improving_periods'] == 1

    def test_analyze_trends_empty(self):
        with patch('core.analytics.compute_completion_rate') as mock_cr:
            mock_cr.return_value = {'daily_rates': []}
            result = analytics.analyze_trends('t')
            assert result['smoothed_data'] == []
