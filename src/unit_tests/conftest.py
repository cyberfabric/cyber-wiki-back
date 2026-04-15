"""
Shared pytest fixtures for unit tests.

This module provides common fixtures used across all unit tests.
"""
import pytest
from django.contrib.auth.models import User
from wiki.models import Space


@pytest.fixture
def user():
    """
    Create a test user.
    
    Returns:
        User: A Django user instance with username 'testuser'
    """
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='testuser@test.com'
    )


@pytest.fixture
def admin_user():
    """
    Create an admin user.
    
    Returns:
        User: A Django superuser instance
    """
    return User.objects.create_superuser(
        username='admin',
        password='admin123',
        email='admin@test.com'
    )


@pytest.fixture
def another_user():
    """
    Create another test user for multi-user scenarios.
    
    Returns:
        User: A Django user instance with username 'anotheruser'
    """
    return User.objects.create_user(
        username='anotheruser',
        password='testpass123',
        email='anotheruser@test.com'
    )


@pytest.fixture
def space(user):
    """
    Create a test space.
    
    Args:
        user: The user fixture (space owner)
    
    Returns:
        Space: A Space instance configured for testing
    """
    return Space.objects.create(
        slug='test-space',
        name='Test Space',
        owner=user,
        default_display_name_source='first_h1',
        git_provider='local_git',
        git_base_url='/tmp/test-repo',
        git_repository_id='test-repo',
    )


@pytest.fixture
def request_factory():
    """
    Provide Django RequestFactory for testing views.
    
    Returns:
        RequestFactory: Django test request factory
    """
    from django.test import RequestFactory
    return RequestFactory()
