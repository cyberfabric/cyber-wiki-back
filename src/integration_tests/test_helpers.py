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
# Comment Helper Functions
# ============================================================================

def create_comment(api_session, source_uri: str, text: str = "Test comment", 
                   line_start: Optional[int] = None, line_end: Optional[int] = None,
                   parent_id: Optional[str] = None, **kwargs) -> Optional[Dict]:
    """
    Create a test comment.
    
    Args:
        api_session: Authenticated API session
        source_uri: URI of the source file (e.g., "space://slug/path/file.md")
        text: Comment text
        line_start: Optional starting line number for line-specific comments
        line_end: Optional ending line number for line-specific comments
        parent_id: Optional parent comment ID for threaded replies
        **kwargs: Additional comment attributes
    
    Returns:
        Dict with created comment data or None if creation failed
    """
    comment_data = {
        "source_uri": source_uri,
        "text": text,
        **kwargs
    }
    
    if line_start is not None:
        comment_data["line_start"] = line_start
    if line_end is not None:
        comment_data["line_end"] = line_end
    if parent_id is not None:
        comment_data["parent_comment"] = parent_id
    
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            json=comment_data,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"⚠️  Failed to create comment: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error creating comment: {e}")
        return None


def delete_comment(api_session, comment_id: str) -> bool:
    """
    Delete a comment by ID.
    
    Args:
        api_session: Authenticated API session
        comment_id: ID of the comment to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/wiki/v1/comments/{comment_id}/",
            headers=api_session.headers,
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️  Error deleting comment {comment_id}: {e}")
        return False


def cleanup_test_comments(api_session, source_uri: str):
    """
    Clean up all comments for a given source URI.
    
    Args:
        api_session: Authenticated API session
        source_uri: URI of the source file
    """
    try:
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            params={"source_uri": source_uri},
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code != 200:
            return
        
        data = response.json()
        comments = data if isinstance(data, list) else data.get("results", [])
        
        for comment in comments:
            delete_comment(api_session, comment['id'])
    except Exception as e:
        print(f"⚠️  Comments cleanup error: {e}")


# ============================================================================
# User Changes Helper Functions
# ============================================================================

def create_user_change(api_session, repository_full_name: str, file_path: str,
                      original_content: str = "Original content",
                      modified_content: str = "Modified content",
                      commit_message: str = "Test change", **kwargs) -> Optional[Dict]:
    """
    Create a test user change (pending edit).
    
    Args:
        api_session: Authenticated API session
        repository_full_name: Full repository name (e.g., "owner/repo")
        file_path: Path to the file being changed
        original_content: Original file content
        modified_content: Modified file content
        commit_message: Commit message for the change
        **kwargs: Additional change attributes
    
    Returns:
        Dict with created change data or None if creation failed
    """
    change_data = {
        "repository_full_name": repository_full_name,
        "file_path": file_path,
        "original_content": original_content,
        "modified_content": modified_content,
        "commit_message": commit_message,
        **kwargs
    }
    
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/changes/",
            json=change_data,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"⚠️  Failed to create user change: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error creating user change: {e}")
        return None


def approve_user_change(api_session, change_id: str) -> Optional[Dict]:
    """
    Approve a user change.
    
    Args:
        api_session: Authenticated API session
        change_id: ID of the change to approve
    
    Returns:
        Dict with approved change data or None if approval failed
    """
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/changes/{change_id}/approve/",
            headers=api_session.headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Failed to approve change: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error approving change {change_id}: {e}")
        return None


def delete_user_change(api_session, change_id: str) -> bool:
    """
    Delete a user change.
    
    Args:
        api_session: Authenticated API session
        change_id: ID of the change to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/wiki/v1/changes/{change_id}/",
            headers=api_session.headers,
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️  Error deleting change {change_id}: {e}")
        return False


def reject_user_change(api_session, change_id: str) -> Optional[Dict]:
    """
    Reject a user change.
    
    Args:
        api_session: Authenticated API session
        change_id: ID of the change to reject
    
    Returns:
        Dict with rejected change data or None if failed
    """
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/changes/{change_id}/reject/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Failed to reject change {change_id}: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error rejecting change {change_id}: {e}")
        return None


def cleanup_test_user_changes(api_session):
    """
    Clean up all test user changes.
    
    Args:
        api_session: Authenticated API session
    """
    try:
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/changes/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code != 200:
            return
        
        data = response.json()
        changes = data if isinstance(data, list) else data.get("results", [])
        
        for change in changes:
            if TEST_PREFIX in change.get("description", ""):
                delete_user_change(api_session, change['id'])
    except Exception as e:
        print(f"⚠️  User changes cleanup error: {e}")


def cleanup_user_changes(api_session):
    """
    Clean up all test user changes (alias for cleanup_test_user_changes).
    
    Args:
        api_session: Authenticated API session
    """
    try:
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/changes/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code != 200:
            return
        
        data = response.json()
        changes = data if isinstance(data, list) else data.get("results", [])
        
        for change in changes:
            # Only delete test changes (those with test_ in repository name)
            if 'test_' in change.get('repository_full_name', ''):
                delete_user_change(api_session, change['id'])
    except Exception as e:
        print(f"⚠️  User changes cleanup error: {e}")


# ============================================================================
# Service Token Helper Functions
# ============================================================================

def create_service_token(api_session, service_type: str = "custom_header",
                        name: str = None, base_url: str = "",
                        token: str = "test_token_value",
                        header_name: str = "X-Test-Token", **kwargs) -> Optional[Dict]:
    """
    Create a test service token.
    
    Args:
        api_session: Authenticated API session
        service_type: Type of service (custom_header, github, bitbucket_server)
        name: Token name (auto-generated if not provided)
        base_url: Base URL for the service
        token: Token value
        header_name: Header name for custom_header type
        **kwargs: Additional token attributes
    
    Returns:
        Dict with created token data or None if creation failed
    """
    if name is None:
        name = f"{TEST_PREFIX}token_{get_unique_id()}"
    
    token_data = {
        "service_type": service_type,
        "name": name,
        "base_url": base_url,
        "token": token,
        **kwargs
    }
    
    if service_type == "custom_header":
        token_data["header_name"] = header_name
    
    try:
        response = requests.post(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/",
            json=token_data,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"⚠️  Failed to create service token: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error creating service token: {e}")
        return None


def delete_service_token(api_session, token_id: str) -> bool:
    """
    Delete a service token.
    
    Args:
        api_session: Authenticated API session
        token_id: ID of the token to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
            headers=api_session.headers,
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️  Error deleting service token {token_id}: {e}")
        return False


# ============================================================================
# API Token Helper Functions
# ============================================================================

def create_api_token(api_session, name: str = None, expires_in_days: int = 30) -> Optional[Dict]:
    """
    Create a test API token.
    
    Args:
        api_session: Authenticated API session
        name: Token name (auto-generated if not provided)
        expires_in_days: Number of days until expiration
    
    Returns:
        Dict with created token data or None if creation failed
    """
    if name is None:
        name = f"{TEST_PREFIX}api_token_{get_unique_id()}"
    
    token_data = {
        "name": name,
        "expires_in_days": expires_in_days
    }
    
    try:
        response = requests.post(
            f"{api_session.base_url}/api/user_management/v1/tokens/",
            json=token_data,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"⚠️  Failed to create API token: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error creating API token: {e}")
        return None


def delete_api_token(api_session, token_id: str) -> bool:
    """
    Delete an API token.
    
    Args:
        api_session: Authenticated API session
        token_id: ID of the token to delete
    
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/user_management/v1/tokens/{token_id}/",
            headers=api_session.headers,
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️  Error deleting API token {token_id}: {e}")
        return False


# ============================================================================
# Favorites Helper Functions
# ============================================================================

def add_favorite(api_session, repository_id: str) -> Optional[Dict]:
    """
    Add a repository to favorites.
    
    Args:
        api_session: Authenticated API session
        repository_id: ID of the repository to favorite
    
    Returns:
        Dict with favorite data or None if operation failed
    """
    try:
        response = requests.post(
            f"{api_session.base_url}/api/user_management/v1/favorites/",
            json={"repository_id": repository_id},
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"⚠️  Failed to add favorite: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️  Error adding favorite: {e}")
        return None


def remove_favorite(api_session, favorite_id: str) -> bool:
    """
    Remove a repository from favorites.
    
    Args:
        api_session: Authenticated API session
        favorite_id: ID of the favorite to remove
    
    Returns:
        True if removal was successful, False otherwise
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/user_management/v1/favorites/{favorite_id}/",
            headers=api_session.headers,
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️  Error removing favorite {favorite_id}: {e}")
        return False


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
                remove_favorite(api_session, favorite['id'])
    except Exception as e:
        print(f"⚠️  Favorites cleanup error: {e}")
