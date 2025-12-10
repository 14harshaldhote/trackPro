
import pytest
from unittest.mock import Mock, patch
from datetime import date, datetime
from core.repositories import base_repository as repo
from core.models import TrackerDefinition, TaskTemplate, TrackerInstance, TaskInstance

class TestBaseRepository:
    
    def test_create_tracker_definition(self):
        with patch('core.repositories.base_repository.TrackerDefinition.objects.create') as mock_create:
            data = {'name': 'New Tracker', 'description': 'Desc'}
            repo.create_tracker_definition(data)
            mock_create.assert_called_once()
            assert mock_create.call_args[1]['name'] == 'New Tracker'

    def test_get_all_tracker_definitions(self):
        with patch('core.repositories.base_repository.TrackerDefinition.objects.filter') as mock_filter:
            repo.get_all_tracker_definitions()
            mock_filter.assert_called()

    def test_get_tracker_by_id(self):
        with patch('core.repositories.base_repository.TrackerDefinition.objects.get') as mock_get:
            repo.get_tracker_by_id('t1')
            mock_get.assert_called_with(tracker_id='t1', deleted_at__isnull=True)

    def test_create_task_template(self):
        with patch('core.repositories.base_repository.TrackerDefinition.objects.get') as mock_get_tracker, \
             patch('core.repositories.base_repository.TaskTemplate.objects.create') as mock_create:
            
            mock_get_tracker.return_value = Mock()
            data = {'tracker_id': 't1', 'description': 'Task'}
            repo.create_task_template(data)
            mock_create.assert_called()

    def test_create_tracker_instance(self):
         with patch('core.repositories.base_repository.TrackerDefinition.objects.get') as mock_get_tracker, \
              patch('core.repositories.base_repository.TrackerInstance.objects.get_or_create') as mock_create:
            
            mock_get_tracker.return_value = Mock()
            mock_create.return_value = (Mock(), True)
            data = {'tracker_id': 't1', 'tracking_date': date(2023, 1, 1)}
            repo.create_tracker_instance(data)
            mock_create.assert_called()

    def test_get_tracker_instances(self):
        with patch('core.repositories.base_repository.TrackerInstance.objects.filter') as mock_filter:
            repo.get_tracker_instances('t1')
            mock_filter.assert_called()

    def test_create_task_instance(self):
        with patch('core.repositories.base_repository.TrackerInstance.objects.get'), \
             patch('core.repositories.base_repository.TaskTemplate.objects.get'), \
             patch('core.repositories.base_repository.TaskInstance.objects.create') as mock_create:
            
            data = {'tracker_instance_id': 'i1', 'template_id': 'tm1'}
            repo.create_task_instance(data)
            mock_create.assert_called()

    def test_update_task_instance_status(self):
        with patch('core.repositories.base_repository.TaskInstance.objects.get') as mock_get:
            task = Mock()
            task.completed_at = None
            mock_get.return_value = task
            
            repo.update_task_instance_status('ti1', 'DONE')
            
            assert task.status == 'DONE'
            assert task.completed_at is not None
            task.save.assert_called()

    def test_database_engine_fetch_by_id(self):
        db = repo.DatabaseEngine()
        mock_model = Mock()
        # Setup mock manager and object
        mock_obj = Mock()
        mock_obj.id = 1
        mock_obj.name = 'Test'
        # Mock _meta.fields for model_to_dict
        field1 = Mock(); field1.name = 'id'; field1.is_relation = False
        field2 = Mock(); field2.name = 'name'; field2.is_relation = False
        mock_obj._meta.fields = [field1, field2]
        
        mock_model.objects.get.return_value = mock_obj
        
        with patch.dict(repo.DatabaseEngine.MODEL_MAP, {'TrackerDefinitions': mock_model}):
            result = db.fetch_by_id('TrackerDefinitions', 'id', 1)
            assert result['name'] == 'Test'

    def test_get_tracker_instances_with_tasks(self):
        with patch('core.repositories.base_repository.TrackerInstance.objects.filter') as mock_filter:
            mock_qs = mock_filter.return_value
            mock_qs.filter.return_value = mock_qs # Chainable
            
            repo.get_tracker_instances_with_tasks('t1', start_date='2023-01-01')
            
            mock_qs.prefetch_related.assert_called()

    def test_get_day_grid_data(self):
        with patch('core.repositories.base_repository.get_tracker_with_templates') as mock_get_tracker, \
             patch('core.repositories.base_repository.get_tracker_instances_with_tasks') as mock_get_instances:
            
            mock_get_tracker.return_value = Mock()
            mock_get_instances.return_value = []
            
            result = repo.get_day_grid_data('t1', [date(2023, 1, 1)])
            assert result['tracker'] is not None

    def test_update_task_instance(self):
        with patch('core.repositories.base_repository.TaskInstance.objects.get') as mock_get:
            task = Mock()
            mock_get.return_value = task
            
            repo.update_task_instance('ti1', {'notes': 'New Note'})
            
            assert task.notes == 'New Note'
            task.save.assert_called()
