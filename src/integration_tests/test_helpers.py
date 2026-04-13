"""
Common helper functions for integration tests.

This module contains reusable utilities for:
- Creating and deleting test artifacts
- Cleanup operations
- Common test data generation
"""
import requests
import time
from typing import Dict, Optional


# ============================================================================
# Constants
# ============================================================================

TEST_PREFIX = "test_"
TEST_SPACE_BASE_NAME = f"{TEST_PREFIX}integration_space"
TEST_SPACE_DESCRIPTION = "Integration test space - safe to delete"


# ============================================================================
# Utility Functions
# ============================================================================

def get_unique_id() -> str:
    """Generate unique ID for test artifacts using microsecond timestamp."""
    return str(int(time.time() * 1000000))


# ============================================================================
# Space Helper Functions
# ============================================================================

def create_space(api_session, name_suffix: str = "", **kwargs) -> Optional[Dict]:
    """
    Create a test space.
    
    Args:
        api_session: Authenticated API session with base_url and headers
        name_suffix: Optional suffix for the space name
        **kwargs: Additional space attributes to override defaults
    
    Returns:
        Dict with created space data or None if creation failed
    """
    unique_id = get_unique_id()
    space_data = {
        "name": f"{TEST_SPACE_BASE_NAME}{name_suffix}_{unique_id}",
        "slug": f"{TEST_PREFIX}space{name_suffix.replace('_', '')}_{unique_id}",
        "description": TEST_SPACE_DESCRIPTION,
        "visibility": "private",
        "git_provider": "local_git",
        "git_base_url": "/tmp/test-repo",
        **kwargs
    }
    
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/spaces/",
            json=space_data,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"⚠️  Failed to create space: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error creating space: {e}")
        return None


def delete_space(api_session, space_slug: str) -> bool:
    """
    Delete a space by slug.
    
    Args:
        api_session: Authenticated API session
        space_slug: Slug of the space to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/wiki/v1/spaces/{space_slug}/",
            headers=api_session.headers,
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️  Error deleting space {space_slug}: {e}")
        return False


def cleanup_all_test_spaces(api_session):
    """
    Clean up all test spaces (prefixed with 'test_').
    
    This function is idempotent and safe to call multiple times.
    It removes any leftover test artifacts from previous test runs.
    
    Args:
        api_session: Authenticated API session
    """
    try:
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/spaces/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code != 200:
            return
        
        data = response.json()
        spaces = data if isinstance(data, list) else data.get("results", [])
        
        deleted_count = 0
        for space in spaces:
            if (space.get("name", "").startswith(TEST_PREFIX) or 
                space.get("slug", "").startswith(TEST_PREFIX)):
                if delete_space(api_session, space['slug']):
                    deleted_count += 1
        
        if deleted_count > 0:
            print(f"\n🧹 Cleaned up {deleted_count} leftover test space(s)")
    except Exception as e:
        print(f"⚠️  Cleanup error: {e}")


# ============================================================================
# Favorites Helper Functions (for future use)
# ============================================================================

def cleanup_test_favorites(api_session):
    """
    Clean up test favorites.
    
    Args:
        api_session: Authenticated API session
    """
    try:
        response = requests.get(
            f"{api_session.base_url}/api/user_management/v1/favorites/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code != 200:
            return
        
        data = response.json()
        favorites = data if isinstance(data, list) else data.get("results", [])
        
        for favorite in favorites:
            repo_id = favorite.get("repository_id", "")
            if TEST_PREFIX in repo_id:
                requests.delete(
                    f"{api_session.base_url}/api/user_management/v1/favorites/{favorite['id']}/",
                    headers=api_session.headers,
                    timeout=5
                )
    except Exception as e:
        print(f"⚠️  Favorites cleanup error: {e}")
