"""
Shared pytest fixtures for unit tests.

This module provides common fixtures used across all unit tests.
"""
import pytest
from django.contrib.auth.models import User
from wiki.models import Space


@pytest.fixture
def user(db):
    """
    Create a test user with UserProfile.
    
    Returns:
        User: A Django user instance with username 'testuser' and viewer role
    """
    from users.models import UserProfile
    
    # Clean up any existing user/profile from previous tests
    # Delete in correct order (profile first due to foreign key)
    UserProfile.objects.filter(user__username='testuser').delete()
    User.objects.filter(username='testuser').delete()
    
    user = User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='testuser@test.com'
    )
    # Ensure UserProfile exists with viewer role (may be created by signal)
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'viewer'})
    return user


@pytest.fixture
def admin_user(db):
    """
    Create an admin user with UserProfile.
    
    Returns:
        User: A Django superuser instance with admin role
    """
    from users.models import UserProfile
    
    # Clean up any existing user/profile from previous tests
    UserProfile.objects.filter(user__username='admin').delete()
    User.objects.filter(username='admin').delete()
    
    user = User.objects.create_superuser(
        username='admin',
        password='admin123',
        email='admin@test.com'
    )
    # Ensure UserProfile exists with admin role (may be created by signal)
    profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': 'admin'})
    if not created:
        profile.role = 'admin'
        profile.save()
    return user


@pytest.fixture
def another_user(db):
    """
    Create another test user for multi-user scenarios.
    
    Returns:
        User: A Django user instance with username 'anotheruser' and viewer role
    """
    from users.models import UserProfile
    
    # Clean up any existing user/profile from previous tests
    UserProfile.objects.filter(user__username='anotheruser').delete()
    User.objects.filter(username='anotheruser').delete()
    
    user = User.objects.create_user(
        username='anotheruser',
        password='testpass123',
        email='anotheruser@test.com'
    )
    # Ensure UserProfile exists with viewer role (may be created by signal)
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'viewer'})
    return user


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
