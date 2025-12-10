
import pytest
from django.test import TestCase
from django.urls import reverse
from core.tests.factories import UserFactory
from django.test.utils import override_settings

@pytest.mark.django_db
class TestAPIVersioning(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.client.force_login(self.user)

    def test_api_v1_prefix(self):
        """
        Ensure all key APIs are under /api/v1/.
        """
        # Check only v1 versioned endpoints (using namespace)
        # Note: Some legacy endpoints like /api/search/ may not be versioned yet
        url_create = reverse('api_v1:tracker_create')
        self.assertTrue(url_create.startswith('/api/v1/'), f"URL {url_create} does not start with /api/v1/")

    def test_accept_header_versioning(self):
        """
        If we implement header-based versioning in future, this test handles it.
        For now, we ensure that standard requests work.
        """
        url = reverse('api_search')
        response = self.client.get(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 200)

    def test_deprecated_versions(self):
        """
        Ensure legacy endpoints (if any) are either redirected or 404.
        Starting fresh with v1, so probing v0 should 404.
        """
        response = self.client.get('/api/v0/search/')
        self.assertEqual(response.status_code, 404)
