
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta
from core.services.grid_builder_service import GridBuilderService

class TestGridBuilderService:

    @pytest.fixture
    def service(self):
        return GridBuilderService(tracker_id="test-tracker-id")

    @pytest.fixture
    def mock_crud(self):
        with patch('core.services.grid_builder_service.crud') as mock:
            yield mock

    @pytest.fixture
    def sample_templates(self):
        return [
            {'template_id': 't1', 'name': 'Task 1', 'time_of_day': 'morning'},
            {'template_id': 't2', 'name': 'Task 2', 'time_of_day': 'evening'}
        ]

    @pytest.fixture
    def sample_tasks(self):
        return [
            {'template_id': 't1', 'status': 'DONE', 'notes': 'Did it'},
            {'template_id': 't2', 'status': 'TODO', 'notes': ''}
        ]

    def test_init(self, service):
        assert service.tracker_id == "test-tracker-id"

    def test_build_grid_no_tracker(self, service, mock_crud):
        dates = [date(2023, 1, 1)]
        mock_crud.get_day_grid_data.return_value = {
            'tracker': None,
            'templates': [],
            'instances_map': {}
        }
        
        result = service.build_grid(dates)
        
        assert result['tracker'] is None
        assert result['templates'] == []
        assert result['grid'] == []
        assert result['stats'] == {}
        assert result['dates'] == dates

    def test_build_grid_date_layout(self, service, mock_crud, sample_templates):
        dates = [date(2023, 1, 1)]
        instances_map = {
            '2023-01-01': {'tasks': [{'template_id': 't1', 'status': 'DONE'}]}
        }
        
        mock_crud.get_day_grid_data.return_value = {
            'tracker': {'id': 'test'},
            'templates': sample_templates,
            'instances_map': instances_map
        }
        
        result = service.build_grid(dates, layout='date')
        
        assert result['tracker'] == {'id': 'test'}
        assert len(result['grid']) == 2  # 2 templates
        assert len(result['grid'][0]['days']) == 1  # 1 date
        assert result['stats']['total_tasks'] == 1
        assert result['stats']['done_tasks'] == 1

    def test_build_grid_task_layout(self, service, mock_crud, sample_templates):
        dates = [date(2023, 1, 1)]
        instances_map = {
            '2023-01-01': {'tasks': [{'template_id': 't1', 'status': 'DONE'}]}
        }
        
        mock_crud.get_day_grid_data.return_value = {
            'tracker': {'id': 'test'},
            'templates': sample_templates,
            'instances_map': instances_map
        }
        
        result = service.build_grid(dates, layout='task')
        
        assert len(result['grid']) == 1  # 1 date
        assert len(result['grid'][0]['tasks']) == 2  # 2 templates
        assert result['stats']['total_tasks'] == 1

    def test_build_monthly_grid(self, service):
        # We can mock build_grid or tested thoroughly. 
        # Here we'll mock build_grid to verify metadata construction
        with patch.object(service, 'build_grid') as mock_build:
            mock_build.return_value = {}
            result = service.build_monthly_grid(2023, 1)
            
            assert result['year'] == 2023
            assert result['month'] == 1
            assert result['month_name'] == 'January 2023'
            assert result['num_days'] == 31
            assert result['prev_month'] == 12
            assert result['prev_year'] == 2022
            assert result['next_month'] == 2
            assert result['next_year'] == 2023
            mock_build.assert_called_once()

    def test_build_week_grid(self, service):
        with patch.object(service, 'build_grid') as mock_build:
            mock_build.return_value = {}
            with patch('core.services.grid_builder_service.date') as mock_date:
                mock_date.today.return_value = date(2023, 1, 2) # Monday
                mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
                
                result = service.build_week_grid(week_offset=0)
                
                assert result['week_start'] == date(2023, 1, 2)
                assert result['week_end'] == date(2023, 1, 8)
                assert result['week_offset'] == 0
                mock_build.assert_called_once()

    def test_build_custom_range_grid(self, service):
        with patch.object(service, 'build_grid') as mock_build:
            mock_build.return_value = {}
            start = date(2023, 1, 1)
            end = date(2023, 1, 3)
            
            result = service.build_custom_range_grid(start, end)
            
            assert result['start_date'] == start
            assert result['end_date'] == end
            assert result['num_days'] == 3
            mock_build.assert_called_once()

    def test_calculate_grid_stats_various_statuses(self, service):
        # Create a grid manually to test stats calc logic
        grid_date_layout = [
            {'days': [
                {'task': {'status': 'DONE'}},
                {'task': {'status': 'IN_PROGRESS'}},
                {'task': {'status': 'MISSED'}},
                {'task': {'status': 'TODO'}},
                {'task': None} # Should receive no count
            ]}
        ]
        
        stats = service._calculate_grid_stats(grid_date_layout, layout='date')
        assert stats['total_tasks'] == 4
        assert stats['done_tasks'] == 1
        assert stats['in_progress_tasks'] == 1
        assert stats['missed_tasks'] == 1
        assert stats['todo_tasks'] == 1
        assert stats['completion_rate'] == 25.0

    def test_calculate_grid_stats_task_layout(self, service):
        grid_task_layout = [
            {'tasks': [
                {'task': {'status': 'DONE'}},
                {'task': None}
            ]}
        ]
        stats = service._calculate_grid_stats(grid_task_layout, layout='task')
        assert stats['total_tasks'] == 1
        assert stats['done_tasks'] == 1
        assert stats['completion_rate'] == 100.0

    @patch('core.models.TaskInstance')
    def test_get_time_of_day_breakdown(self, mock_task_model, service):
        # Setup mock tasks
        mock_t1 = Mock()
        mock_t1.template.time_of_day = 'morning'
        mock_t1.status = 'DONE'
        
        mock_t2 = Mock()
        mock_t2.template.time_of_day = 'evening'
        mock_t2.status = 'TODO'
        
        mock_t3 = Mock()
        mock_t3.template.time_of_day = None # Should be unspecified
        mock_t3.status = 'DONE'
        
        mock_task_model.objects.filter.return_value.select_related.return_value = [mock_t1, mock_t2, mock_t3]
        
        result = service.get_time_of_day_breakdown()
        
        assert result['morning']['total'] == 1
        assert result['morning']['completed'] == 1
        assert result['evening']['total'] == 1
        assert result['evening']['completed'] == 0
        assert result['unspecified']['total'] == 1
        assert result['unspecified']['completed'] == 1

    @patch('core.models.TaskInstance')
    def test_get_daily_time_pattern(self, mock_task_model, service):
        mock_t1 = Mock()
        mock_t1.template.time_of_day = 'morning'
        
        mock_t2 = Mock()
        mock_t2.template.time_of_day = 'morning'
        
        mock_t3 = Mock()
        mock_t3.template.time_of_day = 'afternoon'
        
        mock_task_model.objects.filter.return_value.select_related.return_value = [mock_t1, mock_t2, mock_t3]
        
        result = service.get_daily_time_pattern()
        
        assert result['time_counts']['morning'] == 2
        assert result['time_counts']['afternoon'] == 1
        assert result['best_time'] == 'morning'
        assert "morning" in result['recommendation']

    @patch('core.models.TaskInstance')
    def test_get_daily_time_pattern_empty(self, mock_task_model, service):
        mock_task_model.objects.filter.return_value.select_related.return_value = []
        
        result = service.get_daily_time_pattern()
        
        assert result['best_time'] == 'morning' # Default
        assert result['time_counts']['morning'] == 0
