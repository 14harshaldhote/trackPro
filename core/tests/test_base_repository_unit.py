
from django.test import TestCase
from datetime import date, datetime
from core.repositories import base_repository
from core.models import TrackerDefinition, TaskTemplate, TrackerInstance, TaskInstance, DayNote
from core.tests.factories import TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory

class TestBaseRepository(TestCase):

    def setUp(self):
        from core.tests.factories import UserFactory
        self.user = UserFactory.create()
        self.tracker = TrackerFactory.create(user=self.user, tracker_id="test-id", name="Test Tracker")
        self.template = TemplateFactory.create(tracker=self.tracker, template_id="temp-1", description="Task 1")
        self.instance = InstanceFactory.create(tracker=self.tracker, target_date=date(2023, 1, 1), instance_id="inst-1")

    def test_create_tracker_definition(self):
        data = {'tracker_id': 'new-tracker', 'name': 'New Tracker', 'description': 'desc'}
        t = base_repository.create_tracker_definition(data)
        assert t.tracker_id == 'new-tracker'
        assert t.name == 'New Tracker'
        
        # Test default ID
        data2 = {'name': 'Auto ID'}
        t2 = base_repository.create_tracker_definition(data2)
        assert t2.tracker_id is not None

    def test_get_tracker_by_id(self):
        # Found
        t = base_repository.get_tracker_by_id("test-id")
        assert t is not None
        assert t.name == "Test Tracker"
        
        # Not found
        assert base_repository.get_tracker_by_id("non-existent") is None

    def test_get_all_tracker_definitions(self):
        trackers = base_repository.get_all_tracker_definitions()
        assert len(trackers) >= 1

    def test_create_task_template(self):
        data = {
            'template_id': 'new-temp',
            'tracker_id': 'test-id',
            'description': 'New Task',
            'is_recurring': True
        }
        t = base_repository.create_task_template(data)
        assert t.template_id == 'new-temp'
        assert t.description == 'New Task'

    def test_get_task_templates_for_tracker(self):
        templates = base_repository.get_task_templates_for_tracker('test-id')
        assert templates.count() == 1
        assert templates[0].description == "Task 1"

    def test_get_task_template_by_id(self):
        t = base_repository.get_task_template_by_id('temp-1')
        assert t is not None
        assert base_repository.get_task_template_by_id('missing') is None

    def test_create_tracker_instance(self):
        data = {
            'tracker_id': 'test-id',
            'tracking_date': date(2023, 1, 2)
        }
        inst = base_repository.create_tracker_instance(data)
        assert inst.tracking_date == date(2023, 1, 2)
        
        # Test with datetime
        data2 = {
            'tracker_id': 'test-id',
            'tracking_date': datetime(2023, 1, 3)
        }
        inst2 = base_repository.create_tracker_instance(data2)
        assert inst2.tracking_date == date(2023, 1, 3)

    def test_get_tracker_instances(self):
        insts = base_repository.get_tracker_instances('test-id')
        assert insts.count() >= 1
        
        # Date filter
        base_repository.create_tracker_instance({'tracker_id': 'test-id', 'tracking_date': date(2023, 1, 2)})
        f_insts = base_repository.get_tracker_instances('test-id', start_date=date(2023, 1, 2))
        assert f_insts.count() == 1
        assert f_insts.first().tracking_date == date(2023, 1, 2)

    def test_get_tracker_instance_by_date(self):
        inst = base_repository.get_tracker_instance_by_date('test-id', date(2023, 1, 1))
        assert inst is not None
        assert base_repository.get_tracker_instance_by_date('test-id', date(2099, 1, 1)) is None

    def test_create_task_instance(self):
        data = {
            'tracker_instance_id': 'inst-1',
            'template_id': 'temp-1',
            'status': 'DONE'
        }
        task = base_repository.create_task_instance(data)
        assert task.status == 'DONE'
        assert task.completed_at is not None

    def test_update_task_instance_status(self):
        task = TaskInstanceFactory.create(instance=self.instance, template=self.template)
        updated = base_repository.update_task_instance_status(task.task_instance_id, 'DONE')
        assert updated.status == 'DONE'
        assert updated.completed_at is not None
        
        # Revert
        updated = base_repository.update_task_instance_status(task.task_instance_id, 'TODO')
        assert updated.status == 'TODO'
        assert updated.completed_at is None
        
        # Missing
        assert base_repository.update_task_instance_status('missing', 'DONE') is None

    def test_update_task_instance(self):
        task = TaskInstanceFactory.create(instance=self.instance, template=self.template, status='TODO')
        # Update notes
        updated = base_repository.update_task_instance(task.task_instance_id, {'notes': 'updated'})
        assert updated.notes == 'updated'
        
        # Update status
        updated = base_repository.update_task_instance(task.task_instance_id, {'status': 'DONE'})
        assert updated.status == 'DONE'
        assert updated.completed_at is not None
        
        assert base_repository.update_task_instance('missing', {}) is None

    def test_database_engine_shim(self):
        db = base_repository.db
        
        # fetch_by_id
        res = db.fetch_by_id('TrackerDefinitions', 'tracker_id', 'test-id')
        assert res['tracker_id'] == 'test-id'
        
        # fetch_all
        res = db.fetch_all('TrackerDefinitions')
        assert len(res) >= 1
        
        # insert
        new_data = {'tracker_id': 'shim-test', 'name': 'Shim'}
        res = db.insert('TrackerDefinitions', new_data)
        assert res['tracker_id'] == 'shim-test'
        
        # update
        res = db.update('TrackerDefinitions', 'tracker_id', 'shim-test', {'name': 'Shim Updated'})
        assert res['name'] == 'Shim Updated'
        
        # delete
        assert db.delete('TrackerDefinitions', 'tracker_id', 'shim-test')
        assert db.fetch_by_id('TrackerDefinitions', 'tracker_id', 'shim-test') is None
        
        # fetch_filter
        res = db.fetch_filter('TrackerDefinitions', tracker_id='test-id')
        assert len(res) == 1
        
        # Unknown sheet
        assert db.fetch_by_id('Unknown', 'id', 'val') is None

    def test_optimized_queries(self):
        # get_tracker_with_templates
        t = base_repository.get_tracker_with_templates('test-id')
        assert t.templates.count() == 1
        
        # get_tracker_instances_with_tasks
        inst = base_repository.get_tracker_instances_with_tasks('test-id')
        assert inst.count() == 1
        
        # get_day_grid_data
        dates = [date(2023, 1, 1)]
        grid = base_repository.get_day_grid_data('test-id', dates)
        assert grid['tracker'] is not None
        assert '2023-01-01' in grid['instances_map']

    def test_model_to_dict_utils(self):
        # Already tested implicitly via Shim tests, but specifically:
        d = base_repository.model_to_dict(self.tracker)
        assert d['tracker_id'] == 'test-id'
        assert d['created_at'] is not None # datetime serialization
        
        d2 = base_repository.model_to_dict(None)
        assert d2 is None

    def test_exception_handling(self):
        # Trigger exceptions by passing invalid types where they might break or mocking methods
        # For now, simplistic checks were done with 'missing' IDs.
        pass
