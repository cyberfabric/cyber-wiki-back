
"""
Shared helper functions for unit tests.

This module provides common utilities and helper functions used across unit tests.
"""
from unittest.mock import Mock
from typing import Dict, Any, Optional


def create_mock_response(status_code: int = 200, json_data: Optional[Dict[str, Any]] = None, text: str = ""):
    """
    Create a mock HTTP response.
    
    Args:
        status_code: HTTP status code (default: 200)
        json_data: Optional JSON data to return
        text: Optional response text
    
    Returns:
        Mock: A mock response object
    
    Example:
        >>> response = create_mock_response(200, {'key': 'value'})
        >>> response.status_code
        200
        >>> response.json()
        {'key': 'value'}
    """
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.text = text
    
    if json_data is not None:
        mock_response.json.return_value = json_data
    
    return mock_response


def create_test_user(username: str = 'testuser', **kwargs):
    """
    Create a test user with defaults.
    
    Args:
        username: Username for the user
        **kwargs: Additional user fields (password, email, etc.)
    
    Returns:
        User: A Django user instance
    
    Example:
        >>> user = create_test_user('john', email='john@test.com')
        >>> user.username
        'john'
    """
    from django.contrib.auth.models import User
    
    password = kwargs.pop('password', 'testpass123')
    email = kwargs.pop('email', f'{username}@test.com')
    
    return User.objects.create_user(
        username=username,
        password=password,
        email=email,
        **kwargs
    )


def create_test_space(owner, slug: str = 'test-space', **kwargs):
    """
    Create a test space with defaults.
    
    Args:
        owner: User who owns the space
        slug: Space slug
        **kwargs: Additional space fields
    
    Returns:
        Space: A Space instance
    
    Example:
        >>> space = create_test_space(user, slug='my-space')
        >>> space.slug
        'my-space'
    """
    from wiki.models import Space
    
    defaults = {
        'name': kwargs.pop('name', 'Test Space'),
        'default_display_name_source': 'first_h1',
        'git_provider': 'local_git',
        'git_base_url': '/tmp/test-repo',
        'git_repository_id': 'test-repo',
    }
    defaults.update(kwargs)
    
    return Space.objects.create(
        slug=slug,
        owner=owner,
        **defaults
    )


def create_mock_user(username: str = 'testuser', **kwargs):
    """
    Create a mock user object for testing without database.
    
    Args:
        username: Username for the mock user
        **kwargs: Additional attributes to set on the mock user
    
    Returns:
        Mock: A mock user object with common user attributes
    
    Example:
        >>> mock_user = create_mock_user('john', email='john@test.com')
        >>> mock_user.username
        'john'
        >>> mock_user.email
        'john@test.com'
    """
    mock_user = Mock()
    mock_user.username = username
    mock_user.email = kwargs.get('email', f'{username}@test.com')
    mock_user.id = kwargs.get('id', 1)
    mock_user.is_active = kwargs.get('is_active', True)
    mock_user.is_staff = kwargs.get('is_staff', False)
    mock_user.is_superuser = kwargs.get('is_superuser', False)
    
    # Set any additional attributes
    for key, value in kwargs.items():
        if key not in ['email', 'id', 'is_active', 'is_staff', 'is_superuser']:
            setattr(mock_user, key, value)
    
    return mock_user


def assert_mock_called_with_params(mock_obj, **expected_params):
    """
    Assert that a mock was called with specific parameters.
    
    Args:
        mock_obj: The mock object to check
        **expected_params: Expected parameter values
    
    Raises:
        AssertionError: If mock wasn't called with expected params
    
    Example:
        >>> mock_func = Mock()
        >>> mock_func(user='john', age=30)
        >>> assert_mock_called_with_params(mock_func, user='john', age=30)
    """
    assert mock_obj.called, "Mock was not called"
    
    call_args = mock_obj.call_args
    if call_args is None:
        raise AssertionError("Mock was not called")
    
    actual_kwargs = call_args.kwargs if hasattr(call_args, 'kwargs') else call_args[1]
    
    for key, expected_value in expected_params.items():
        assert key in actual_kwargs, f"Parameter '{key}' not found in call"
        actual_value = actual_kwargs[key]
        assert actual_value == expected_value, \
            f"Parameter '{key}': expected {expected_value}, got {actual_value}"
