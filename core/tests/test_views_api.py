
import pytest
import json
from unittest.mock import Mock, patch
from django.test import RequestFactory
from django.http import JsonResponse
from core.views_api import (
    require_auth, api_task_toggle, api_task_delete, api_task_status, 
    api_tasks_bulk, api_task_add, api_task_edit, api_tracker_reorder,
    api_tracker_create, api_tracker_delete, api_tracker_update,
    api_template_activate, api_search, api_day_note, api_undo, api_export
)
from core.models import UserPreferences

@pytest.fixture
def factory():
    return RequestFactory()

@pytest.fixture
def user():
    u = Mock()
    u.is_authenticated = True
    u.id = 1
    return u

@pytest.fixture
def mock_tracker_service():
    with patch('core.views_api.tracker_service') as mock:
        yield mock

@pytest.fixture
def mock_task_service():
    with patch('core.views_api.task_service') as mock:
        yield mock

class TestViewsApi:

    def test_require_auth_decorator_session(self, factory, user):
        """Test authentication decorator with session auth."""
        request = factory.get('/')
        request.user = user
        
        @require_auth
        def view(req):
            return JsonResponse({'status': 'ok'})
            
        response = view(request)
        assert response.status_code == 200

    def test_require_auth_decorator_unauth(self, factory):
        """Test authentication decorator failure."""
        request = factory.get('/')
        request.user = Mock()
        request.user.is_authenticated = False
        request.headers = {}
        
        @require_auth
        def view(req):
            return JsonResponse({'status': 'ok'})
            
        response = view(request)
        assert response.status_code == 401

    def test_api_task_toggle(self, factory, user, mock_task_service):
        """Test task toggle endpoint."""
        request = factory.post('/api/task/1/toggle/')
        request.user = user
        
        # Mock service return
        mock_task_service.toggle_task_status.return_value = {
            'task_instance_id': '1', 'status': 'DONE'
        }
        
        # Mock TaskInstance query
        with patch('core.views_api.TaskInstance') as MockTaskModel:
            mock_task = Mock()
            mock_task.tracker_instance.tracker.tracker_id = 't1'
            MockTaskModel.objects.select_related.return_value.get.return_value = mock_task
            MockTaskModel.objects.filter.return_value.count.return_value = 0
            
            response = api_task_toggle(request, '1')
            
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['success'] is True
            assert "All tasks complete" in data['feedback']['message']

    def test_api_task_delete(self, factory, user, mock_task_service):
        """Test task delete endpoint."""
        request = factory.delete('/api/task/1/')
        request.user = user
        
        mock_task_service.delete_task_instance.return_value = {}
        
        response = api_task_delete(request, '1')
        assert response.status_code == 200

    def test_api_task_status(self, factory, user, mock_task_service):
        """Test setting task status explicitly."""
        request = factory.post(
            '/api/task/1/status/', 
            data=json.dumps({'status': 'SKIPPED', 'notes': 'Skip'}),
            content_type='application/json'
        )
        request.user = user
        
        mock_task_service.update_task_status.return_value = {'status': 'SKIPPED'}
        
        response = api_task_status(request, '1')
        assert response.status_code == 200

    def test_api_tasks_bulk(self, factory, user, mock_task_service):
        """Test bulk task update."""
        request = factory.post(
            '/api/tasks/bulk/',
            data=json.dumps({'action': 'complete', 'task_ids': ['1', '2']}),
            content_type='application/json'
        )
        request.user = user
        
        mock_task_service.bulk_update_tasks.return_value = {'updated': 2}
        
        response = api_tasks_bulk(request)
        assert response.status_code == 200

    def test_api_task_add(self, factory, user, mock_task_service):
        """Test adding a task."""
        request = factory.post(
            '/api/tracker/t1/task/add/',
            data=json.dumps({'description': 'New Task', 'points': 3}),
            content_type='application/json'
        )
        request.user = user
        
        mock_task_service.quick_add_task.return_value = {'id': 'new'}
        
        response = api_task_add(request, 't1')
        assert response.status_code == 200

    def test_api_tracker_create(self, factory, user, mock_tracker_service):
        """Test creating a tracker."""
        request = factory.post(
            '/api/tracker/create/',
            data=json.dumps({'name': 'New Tracker'}),
            content_type='application/json'
        )
        request.user = user
        
        mock_tracker_service.create_tracker.return_value = {'id': 't1', 'name': 'New Tracker'}
        
        response = api_tracker_create(request)
        assert response.status_code == 200

    def test_api_template_activate(self, factory, user):
        """Test activating a template."""
        request = factory.post(
            '/api/template/activate/',
            data=json.dumps({'template_key': 'morning'}),
            content_type='application/json'
        )
        request.user = user
        
        with patch('core.models.TrackerDefinition') as MockTrackerDef, \
             patch('core.models.TaskTemplate'), \
             patch('core.services.instance_service.ensure_tracker_instance'), \
             patch('django.db.transaction.atomic'):
            
            MockTrackerDef.objects.create.return_value.tracker_id = 't1'
            MockTrackerDef.objects.create.return_value.name = 'Morning Routine'
            
            response = api_template_activate(request)
            if response.status_code != 200:
                print(f"Template Activate Error: {response.content.decode()}")
                
            assert response.status_code == 200
            data = json.loads(response.content)
            assert data['data']['tracker_name'] == 'Morning Routine'

    def test_api_search(self, factory, user):
        """Test search endpoint."""
        request = factory.get('/api/search/?q=test')
        request.user = user
        
        with patch('core.views_api.search_service') as mock_search:
            mock_search.search.return_value = {'results': []}
            
            response = api_search(request)
            assert response.status_code == 200
            data = json.loads(response.content)
            assert 'commands' in data

    def test_api_day_note(self, factory, user):
        """Test saving a day note."""
        request = factory.post(
            '/api/note/2023-01-01/',
            data=json.dumps({'note': 'My note', 'tracker_id': 't1'}),
            content_type='application/json'
        )
        request.user = user
        
        with patch('core.views_api.get_object_or_404') as mock_get_404, \
             patch('core.views_api.DayNote') as MockDayNote:
            
            mock_note = Mock()
            mock_note.note_id = 'n1'
            MockDayNote.objects.update_or_create.return_value = (mock_note, True)
            
            response = api_day_note(request, '2023-01-01')
            assert response.status_code == 200

    def test_api_undo_task_toggle(self, factory, user):
        """Test undo task toggle."""
        request = factory.post(
            '/api/undo/',
            data=json.dumps({
                'type': 'task_toggle',
                'data': {'task_id': 't1', 'old_status': 'TODO'}
            }),
            content_type='application/json'
        )
        request.user = user
        
        with patch('core.views_api.TaskInstance') as MockTaskInstance:
            mock_task = Mock()
            mock_task.deleted_at = None
            MockTaskInstance.objects.get.return_value = mock_task
            
            response = api_undo(request)
            if response.status_code != 200:
                pytest.fail(f"Undo Error Content: {response.content.decode()}")
                
            assert response.status_code == 200
            assert mock_task.status == 'TODO'
            mock_task.save.assert_called()

    def test_api_export(self, factory, user):
        """Test export endpoint."""
        request = factory.get('/api/export/t1/?format=csv')
        request.user = user
        
        with patch('core.views_api.get_object_or_404') as mock_get_404, \
             patch('core.views_api.TaskInstance') as MockTaskInstance:
             
             mock_get_404.return_value = Mock(name="Test Tracker")
             
             mock_task = Mock()
             mock_task.tracker_instance.tracking_date = "2023-01-01"
             mock_task.snapshot_description = "Task A"
             mock_task.status = "DONE"
             mock_task.snapshot_points = 1
             mock_task.template.category = "Cat"
             
             MockTaskInstance.objects.filter.return_value.select_related.return_value.order_by.return_value = [mock_task]
             
             response = api_export(request, 't1')
             assert response.status_code == 200
             assert response['Content-Type'] == 'text/csv'
             assert b"Date,Description" in response.content
             assert b"Task A" in response.content 
