"""
Pytest configuration and fixtures for TrackPro API tests.

This module provides reusable fixtures for testing.
"""
import pytest
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from datetime import date, timedelta


@pytest.fixture
def api_client():
    """Returns an API client instance."""
    return APIClient()


@pytest.fixture
def user(db):
    """Creates and returns a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def other_user(db):
    """Creates and returns another test user for access control tests."""
    User = get_user_model()
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Returns an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def tracker(user):
    """Creates and returns a test tracker."""
    from core.tests.factories import TrackerFactory
    return TrackerFactory.create(user)


@pytest.fixture
def tracker_with_tasks(user):
    """Creates a tracker with multiple task templates."""
    from core.tests.factories import create_tracker_with_tasks
    tracker, templates = create_tracker_with_tasks(user, task_count=3)
    return tracker, templates


@pytest.fixture
def today():
    """Returns today's date."""
    return date.today()


@pytest.fixture
def yesterday():
    """Returns yesterday's date."""
    return date.today() - timedelta(days=1)


@pytest.fixture
def last_week():
    """Returns the date one week ago."""
    return date.today() - timedelta(days=7)
