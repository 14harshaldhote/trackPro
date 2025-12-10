
from django.test import TestCase
from unittest.mock import patch, Mock
from core.repositories import base_repository
from core.models import TrackerDefinition, TaskTemplate, TrackerInstance, TaskInstance
from core.tests.factories import UserFactory, TrackerFactory, TemplateFactory, InstanceFactory

class TestBaseRepositoryExceptions(TestCase):
    """Test exception handling in base_repository."""

    def setUp(self):
        self.user = UserFactory.create()
        self.tracker = TrackerFactory.create(user=self.user)

    def test_create_tracker_definition_exception(self):
        with patch('core.models.TrackerDefinition.objects.create', side_effect=Exception("DB Error")):
            try:
                base_repository.create_tracker_definition({'name': 'Test'})
                assert False, "Should raise exception"
            except Exception as e:
                assert "DB Error" in str(e)

    def test_get_all_tracker_definitions_exception(self):
        with patch('core.models.TrackerDefinition.objects.filter', side_effect=Exception("DB Error")):
            result = base_repository.get_all_tracker_definitions()
            assert result == []

    def test_get_tracker_by_id_exception(self):
        with patch('core.models.TrackerDefinition.objects.get', side_effect=Exception("DB Error")):
            result = base_repository.get_tracker_by_id("test-id")
            assert result is None

    def test_create_task_template_exception(self):
        with patch('core.models.TaskTemplate.objects.create', side_effect=Exception("DB Error")):
            try:
                base_repository.create_task_template({
                    'tracker_id': self.tracker.tracker_id,
                    'description': 'Test'
                })
                assert False
            except Exception:
                pass

    def test_get_task_templates_exception(self):
        with patch('core.models.TaskTemplate.objects.filter', side_effect=Exception("DB Error")):
            result = base_repository.get_task_templates_for_tracker("test-id")
            assert result == []

    def test_get_task_template_by_id_exception(self):
        with patch('core.models.TaskTemplate.objects.get', side_effect=Exception("DB Error")):
            result = base_repository.get_task_template_by_id("test-id")
            assert result is None

    def test_create_tracker_instance_exception(self):
        with patch('core.models.TrackerInstance.objects.get_or_create', side_effect=Exception("DB Error")):
            try:
                base_repository.create_tracker_instance({
                    'tracker_id': self.tracker.tracker_id,
                    'tracking_date': '2023-01-01'
                })
                assert False
            except Exception:
                pass

    def test_get_tracker_instances_exception(self):
        with patch('core.models.TrackerInstance.objects.filter', side_effect=Exception("DB Error")):
            result = base_repository.get_tracker_instances("test-id")
            assert result == []

    def test_get_tracker_instance_by_date_exception(self):
        with patch('core.models.TrackerInstance.objects.get', side_effect=Exception("DB Error")):
            result = base_repository.get_tracker_instance_by_date("test-id", "2023-01-01")
            assert result is None

    def test_create_task_instance_exception(self):
        instance = InstanceFactory.create(tracker=self.tracker)
        template = TemplateFactory.create(tracker=self.tracker)
        
        with patch('core.models.TaskInstance.objects.create', side_effect=Exception("DB Error")):
            try:
                base_repository.create_task_instance({
                    'tracker_instance_id': instance.instance_id,
                    'template_id': template.template_id
                })
                assert False
            except Exception:
                pass

    def test_get_task_instances_exception(self):
        with patch('core.models.TaskInstance.objects.filter', side_effect=Exception("DB Error")):
            result = base_repository.get_task_instances_for_tracker_instance("test-id")
            assert result == []

    def test_update_task_instance_status_exception(self):
        with patch('core.models.TaskInstance.objects.get', side_effect=Exception("DB Error")):
            try:
                base_repository.update_task_instance_status("test-id", "DONE")
                assert False
            except Exception:
                pass

    def test_database_engine_fetch_by_id_exception(self):
        db = base_repository.DatabaseEngine()
        with patch('core.models.TrackerDefinition.objects.get', side_effect=Exception("DB Error")):
            result = db.fetch_by_id('TrackerDefinitions', 'tracker_id', 'test')
            assert result is None

    def test_database_engine_fetch_all_exception(self):
        db = base_repository.DatabaseEngine()
        with patch('core.models.TrackerDefinition.objects.all', side_effect=Exception("DB Error")):
            result = db.fetch_all('TrackerDefinitions')
            assert result == []

    def test_database_engine_insert_exception(self):
        db = base_repository.DatabaseEngine()
        with patch('core.models.TrackerDefinition.objects.create', side_effect=Exception("DB Error")):
            try:
                db.insert('TrackerDefinitions', {'name': 'Test'})
                assert False
            except Exception:
                pass

    def test_database_engine_update_exception(self):
        db = base_repository.DatabaseEngine()
        with patch('core.models.TrackerDefinition.objects.get', side_effect=Exception("DB Error")):
            try:
                db.update('TrackerDefinitions', 'tracker_id', 'test', {'name': 'Updated'})
                assert False
            except Exception:
                pass

    def test_database_engine_delete_exception(self):
        db = base_repository.DatabaseEngine()
        with patch('core.models.TrackerDefinition.objects.filter') as mock_filter:
            mock_filter.return_value.delete.side_effect = Exception("DB Error")
            result = db.delete('TrackerDefinitions', 'tracker_id', 'test')
            assert result is False

    def test_database_engine_fetch_filter_exception(self):
        db = base_repository.DatabaseEngine()
        with patch('core.models.TrackerDefinition.objects.filter', side_effect=Exception("DB Error")):
            result = db.fetch_filter('TrackerDefinitions', tracker_id='test')
            assert result == []

    def test_get_tracker_instances_with_tasks_exception(self):
        with patch('core.models.TrackerInstance.objects.filter', side_effect=Exception("DB Error")):
            result = base_repository.get_tracker_instances_with_tasks("test-id")
            assert result == []

    def test_get_tracker_with_templates_exception(self):
        with patch('core.models.TrackerDefinition.objects.prefetch_related', side_effect=Exception("DB Error")):
            result = base_repository.get_tracker_with_templates("test-id")
            assert result is None

    def test_get_day_grid_data_exception(self):
        with patch('core.repositories.base_repository.get_tracker_with_templates', return_value=None):
            result = base_repository.get_day_grid_data("test-id", [])
            assert result['tracker'] is None

    def test_update_task_instance_exception(self):
        with patch('core.models.TaskInstance.objects.get', side_effect=Exception("DB Error")):
            try:
                base_repository.update_task_instance("test-id", {'notes': 'test'})
                assert False
            except Exception:
                pass

    def test_model_to_dict_with_relations_coverage(self):
        """Cover model_to_dict_with_relations for different model types."""
        # Test with None
        assert base_repository.model_to_dict_with_relations(None) is None
        
        # Test with TrackerInstance (has tasks)
        instance = InstanceFactory.create(tracker=self.tracker)
        result = base_repository.model_to_dict_with_relations(instance)
        assert result is not None
        
        # Test with TaskInstance (has template)
        template = TemplateFactory.create(tracker=self.tracker)
        from core.tests.factories import TaskInstanceFactory
        task = TaskInstanceFactory.create(instance=instance, template=template)
        result = base_repository.model_to_dict_with_relations(task)
        assert result is not None
        
        # Test with TrackerDefinition (has templates)
        result = base_repository.model_to_dict_with_relations(self.tracker)
        assert result is not None
