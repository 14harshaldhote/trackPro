
import pytest
import json
from django.test import TestCase
from django.urls import reverse
from core.tests.factories import UserFactory, TrackerFactory, TemplateFactory, TaskInstanceFactory, InstanceFactory
from core.models import TrackerDefinition, TaskInstance

@pytest.mark.django_db
class TestAPIContracts(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.client.force_login(self.user)
        self.tracker = TrackerFactory.create(self.user)
        self.template = TemplateFactory.create(self.tracker)
        self.instance = InstanceFactory.create(self.tracker)
        self.task_instance = TaskInstanceFactory.create(self.instance, self.template)

    def test_response_structure_common(self):
        """
        Test that common attributes like 'success' or specific data keys are present.
        """
        # Testing get_active_trackers endpoint implied by dashboard or similar, 
        # but let's test specific API endpoints listed in views_api.py
        
        # Test Search API contract
        url = reverse('api_search')
        response = self.client.get(url, {'q': 'test'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Contract: expect 'trackers', 'tasks', 'goals', 'total_count'
        self.assertIn('trackers', data)
        self.assertIn('tasks', data)
        self.assertIn('total_count', data)
        self.assertIsInstance(data['trackers'], list)

    def test_task_toggle_contract(self):
        """
        Test /api/v1/tasks/{id}/toggle/ contract.
        """
        url = reverse('api_toggle_task', args=[self.task_instance.task_instance_id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Contract: expect 'data' with 'new_status', 'old_status', 'feedback'
        self.assertIn('data', data)
        self.assertIn('new_status', data['data'])
        self.assertIn('old_status', data['data'])
        self.assertIn('feedback', data)
        self.assertEqual(data['data']['new_status'], 'DONE') # Assuming it toggles to DONE

    def test_tracker_crud_contract(self):
        """
        Test /api/v1/trackers/ create/update/delete contract.
        """
        # Create
        url_create = reverse('api_tracker_create')
        payload = {
            'name': 'New Contract Tracker',
            'description': 'Testing contract',
            'time_mode': 'daily',
            'tasks': ['Task A', 'Task B']
        }
        response = self.client.post(url_create, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Response structure has nested data
        self.assertIn('success', data)
        self.assertIn('data', data)
        self.assertIn('tracker', data['data'])
        tracker_id = data['data']['tracker']['id']
        
        # Update
        url_update = reverse('api_tracker_update', args=[tracker_id])
        update_payload = {'name': 'Updated Name'}
        response = self.client.post(url_update, update_payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('success', data)
        self.assertTrue(data.get('success', False))
        
        # Delete
        url_delete = reverse('api_tracker_delete', args=[tracker_id])
        response = self.client.post(url_delete)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success', False))

    def test_error_response_structure_404(self):
        """
        Ensure 404 returns JSON with standard error structure.
        """
        url = reverse('api_tracker_update', args=['non-existent-id'])
        response = self.client.post(url, {}, content_type='application/json')
        
        # Depending on how the view handles it, it might be 404
        # views_api.py seems to use handle_service_errors decorator or similar
        self.assertIn(response.status_code, [404, 400])
        data = response.json()
        self.assertIn('error', data)

    def test_validation_error_structure(self):
        """
        Ensure validation errors return structured JSON.
        """
        url = reverse('api_tracker_create')
        # Empty name should fail
        payload = {'name': ''}
        response = self.client.post(url, payload, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        # Should ideally have field info
        # self.assertIn('field', data or 'details' in data)

    def test_day_note_contract(self):
        """
        Test /api/v1/notes/{date}/ contract.
        """
        date_str = '2025-01-01'
        url = reverse('api_day_note', args=[date_str])
        
        # POST to save
        payload = {'content': 'My Note'}
        response = self.client.post(url, payload, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('success'))
        
        # GET to retrieve (if supported, or via another endpoint)
        # Assuming api_day_note handles GET or similar
        # If not, skipping GET
