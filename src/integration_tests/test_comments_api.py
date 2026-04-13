"""
Integration tests for File Comments API.

Tests cover:
- Creating comments on files
- Listing comments by source URI
- Filtering by resolved status
- Updating comment text
- Resolving/unresolving comments
- Deleting comments
- Comment threading (parent-child relationships)
- Line anchoring

Following TEST_STRUCTURE.md principles:
- Independent tests with proper setup/teardown
- Comprehensive logging
- Idempotent operations
- Reusable helper functions
"""
import pytest
import requests
from .test_helpers import create_space, delete_space, get_unique_id


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_comment(api_session, source_uri: str, line_start: int, line_end: int, text: str, parent_id=None):
    """
    Create a test comment.
    
    Args:
        api_session: API session fixture
        source_uri: Source URI for the comment
        line_start: Starting line number
        line_end: Ending line number
        text: Comment text
        parent_id: Optional parent comment ID for threading
    
    Returns:
        dict: Created comment data or None if failed
    """
    try:
        payload = {
            "source_uri": source_uri,
            "line_start": line_start,
            "line_end": line_end,
            "text": text
        }
        if parent_id:
            payload["parent_comment"] = parent_id
        
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/comments/",
            json=payload,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            comment = response.json()
            print(f"✅ Created test comment: {comment['id']}")
            return comment
        else:
            print(f"⚠️  Failed to create comment: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error creating comment: {e}")
        return None


def delete_test_comment(api_session, comment_id: str):
    """
    Delete a test comment.
    
    Args:
        api_session: API session fixture
        comment_id: Comment ID to delete
    
    Returns:
        bool: True if deleted successfully
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/wiki/v1/comments/{comment_id}/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code in [200, 204]:
            print(f"✅ Deleted test comment: {comment_id}")
            return True
        else:
            print(f"⚠️  Failed to delete comment {comment_id}: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error deleting comment {comment_id}: {e}")
        return False


def get_comments_for_source(api_session, source_uri: str):
    """
    Get all comments for a source URI.
    
    Args:
        api_session: API session fixture
        source_uri: Source URI to query
    
    Returns:
        list: List of comments or empty list if failed
    """
    try:
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Failed to get comments: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error getting comments: {e}")
        return []


def cleanup_test_comments(api_session, source_uri: str):
    """
    Clean up all test comments for a source URI.
    
    Args:
        api_session: API session fixture
        source_uri: Source URI to clean up
    """
    try:
        comments = get_comments_for_source(api_session, source_uri)
        for comment in comments:
            delete_test_comment(api_session, comment['id'])
    except Exception as e:
        print(f"⚠️  Error during comment cleanup: {e}")


# ============================================================================
# Test Classes
# ============================================================================

class TestCommentsBasicOperations:
    """Test basic CRUD operations for comments."""
    
    def test_create_comment_on_file(self, api_session):
        """
        Test: Create a comment on a specific file line range
        
        Scenario:
        1. Create a comment with line range
        2. Verify response contains all expected fields
        3. Verify comment is returned in list
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Create comment on file")
        print("="*80)
        print("Purpose: Verify comments can be created with line anchoring")
        print("Expected: HTTP 201, comment with all fields")
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Test: Create comment
            print(f"\n📤 Creating comment on {source_uri} lines 10-15...")
            comment_text = f"Test comment {test_id}"
            comment = create_test_comment(api_session, source_uri, 10, 15, comment_text)
            
            assert comment is not None, "Comment creation failed"
            assert comment['source_uri'] == source_uri
            assert comment['line_start'] == 10
            assert comment['line_end'] == 15
            assert comment['text'] == comment_text
            assert comment['is_resolved'] is False
            assert 'id' in comment
            assert 'author' in comment
            assert 'created_at' in comment
            
            print(f"✅ Comment created successfully: {comment['id']}")
            
            # Verify: Comment appears in list
            print(f"\n📤 Verifying comment appears in list...")
            comments = get_comments_for_source(api_session, source_uri)
            assert len(comments) == 1
            assert comments[0]['id'] == comment['id']
            
            print(f"✅ Comment verified in list")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
    
    def test_list_comments_by_source_uri(self, api_session):
        """
        Test: List all comments for a specific source URI
        
        Scenario:
        1. Create multiple comments on same file
        2. List comments for that source URI
        3. Verify all comments are returned
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: List comments by source URI")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Setup: Create multiple comments
            print(f"\n🔧 Setup: Creating 3 comments...")
            comment1 = create_test_comment(api_session, source_uri, 10, 12, "Comment 1")
            comment2 = create_test_comment(api_session, source_uri, 20, 25, "Comment 2")
            comment3 = create_test_comment(api_session, source_uri, 30, 30, "Comment 3")
            
            assert comment1 and comment2 and comment3, "Failed to create test comments"
            
            # Test: List comments
            print(f"\n📤 Listing comments for {source_uri}...")
            comments = get_comments_for_source(api_session, source_uri)
            
            assert len(comments) == 3, f"Expected 3 comments, got {len(comments)}"
            comment_ids = {c['id'] for c in comments}
            assert comment1['id'] in comment_ids
            assert comment2['id'] in comment_ids
            assert comment3['id'] in comment_ids
            
            print(f"✅ All 3 comments retrieved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
    
    def test_update_comment_text(self, api_session):
        """
        Test: Update comment text
        
        Scenario:
        1. Create a comment
        2. Update its text
        3. Verify text was updated
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Update comment text")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Setup: Create comment
            print(f"\n🔧 Setup: Creating comment...")
            comment = create_test_comment(api_session, source_uri, 10, 15, "Original text")
            assert comment is not None
            
            # Test: Update comment
            print(f"\n📤 Updating comment text...")
            updated_text = "Updated text"
            response = requests.patch(
                f"{api_session.base_url}/api/wiki/v1/comments/{comment['id']}/",
                json={"text": updated_text},
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            updated_comment = response.json()
            assert updated_comment['text'] == updated_text
            assert updated_comment['id'] == comment['id']
            
            print(f"✅ Comment text updated successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
    
    def test_delete_comment(self, api_session):
        """
        Test: Delete a comment
        
        Scenario:
        1. Create a comment
        2. Delete it
        3. Verify it no longer appears in list
        """
        print("\n" + "="*80)
        print("TEST: Delete comment")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        # Setup: Create comment
        print(f"\n🔧 Setup: Creating comment...")
        comment = create_test_comment(api_session, source_uri, 10, 15, "To be deleted")
        assert comment is not None
        
        # Test: Delete comment
        print(f"\n📤 Deleting comment...")
        success = delete_test_comment(api_session, comment['id'])
        assert success, "Failed to delete comment"
        
        # Verify: Comment no longer in list
        print(f"\n📤 Verifying comment is gone...")
        comments = get_comments_for_source(api_session, source_uri)
        assert len(comments) == 0, "Comment still exists after deletion"
        
        print(f"✅ Comment deleted successfully")


class TestCommentsResolution:
    """Test comment resolution functionality."""
    
    def test_resolve_comment(self, api_session):
        """
        Test: Mark comment as resolved
        
        Scenario:
        1. Create an unresolved comment
        2. Resolve it
        3. Verify is_resolved is True
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Resolve comment")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Setup: Create comment
            print(f"\n🔧 Setup: Creating unresolved comment...")
            comment = create_test_comment(api_session, source_uri, 10, 15, "Needs resolution")
            assert comment is not None
            assert comment['is_resolved'] is False
            
            # Test: Resolve comment
            print(f"\n📤 Resolving comment...")
            response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/{comment['id']}/resolve/",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            resolved_comment = response.json()
            assert resolved_comment['is_resolved'] is True
            assert resolved_comment['id'] == comment['id']
            
            print(f"✅ Comment resolved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
    
    def test_unresolve_comment(self, api_session):
        """
        Test: Mark resolved comment as unresolved
        
        Scenario:
        1. Create and resolve a comment
        2. Unresolve it
        3. Verify is_resolved is False
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Unresolve comment")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Setup: Create and resolve comment
            print(f"\n🔧 Setup: Creating and resolving comment...")
            comment = create_test_comment(api_session, source_uri, 10, 15, "Will be unresolved")
            assert comment is not None
            
            # Resolve it first
            resolve_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/{comment['id']}/resolve/",
                headers=api_session.headers,
                timeout=5
            )
            assert resolve_response.status_code == 200
            
            # Test: Unresolve comment
            print(f"\n📤 Unresolving comment...")
            response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/{comment['id']}/unresolve/",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            unresolved_comment = response.json()
            assert unresolved_comment['is_resolved'] is False
            assert unresolved_comment['id'] == comment['id']
            
            print(f"✅ Comment unresolved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
    
    def test_filter_comments_by_resolved_status(self, api_session):
        """
        Test: Filter comments by resolved/unresolved status
        
        Scenario:
        1. Create resolved and unresolved comments
        2. Filter by is_resolved=true
        3. Filter by is_resolved=false
        4. Verify correct filtering
        5. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Filter comments by resolved status")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Setup: Create comments with different statuses
            print(f"\n🔧 Setup: Creating resolved and unresolved comments...")
            comment1 = create_test_comment(api_session, source_uri, 10, 12, "Unresolved 1")
            comment2 = create_test_comment(api_session, source_uri, 20, 22, "Unresolved 2")
            comment3 = create_test_comment(api_session, source_uri, 30, 32, "To be resolved")
            
            assert comment1 and comment2 and comment3
            
            # Resolve comment3
            requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/{comment3['id']}/resolve/",
                headers=api_session.headers,
                timeout=5
            )
            
            # Test: Filter for resolved comments
            print(f"\n📤 Filtering for resolved comments...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}&is_resolved=true",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            resolved_comments = response.json()
            assert len(resolved_comments) == 1
            assert resolved_comments[0]['id'] == comment3['id']
            
            print(f"✅ Resolved filter works correctly")
            
            # Test: Filter for unresolved comments
            print(f"\n📤 Filtering for unresolved comments...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}&is_resolved=false",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            unresolved_comments = response.json()
            assert len(unresolved_comments) == 2
            unresolved_ids = {c['id'] for c in unresolved_comments}
            assert comment1['id'] in unresolved_ids
            assert comment2['id'] in unresolved_ids
            
            print(f"✅ Unresolved filter works correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)


class TestCommentsThreading:
    """Test comment threading (parent-child relationships)."""
    
    def test_comment_threading(self, api_session):
        """
        Test: Create threaded comments (replies)
        
        Scenario:
        1. Create parent comment
        2. Create reply to parent
        3. Verify parent-child relationship
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Comment threading")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Setup: Create parent comment
            print(f"\n🔧 Setup: Creating parent comment...")
            parent = create_test_comment(api_session, source_uri, 10, 15, "Parent comment")
            assert parent is not None
            
            # Test: Create reply
            print(f"\n📤 Creating reply to parent...")
            reply = create_test_comment(api_session, source_uri, 10, 15, "Reply comment", parent_id=parent['id'])
            assert reply is not None
            assert reply['parent_comment'] == parent['id']
            
            print(f"✅ Reply created successfully")
            
            # Verify: Parent has replies
            print(f"\n📤 Verifying parent has replies...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/{parent['id']}/",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            parent_data = response.json()
            assert 'replies' in parent_data
            assert len(parent_data['replies']) == 1
            assert parent_data['replies'][0]['id'] == reply['id']
            
            print(f"✅ Threading verified successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
    
    def test_comment_line_anchoring(self, api_session):
        """
        Test: Verify line range anchoring
        
        Scenario:
        1. Create comments with different line ranges
        2. Verify line_start and line_end are preserved
        3. Test single-line comment (line_start == line_end)
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Comment line anchoring")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/test_{test_id}.py"
        
        try:
            # Test: Multi-line comment
            print(f"\n📤 Creating multi-line comment (lines 10-20)...")
            multi_line = create_test_comment(api_session, source_uri, 10, 20, "Multi-line comment")
            assert multi_line is not None
            assert multi_line['line_start'] == 10
            assert multi_line['line_end'] == 20
            
            # Test: Single-line comment
            print(f"\n📤 Creating single-line comment (line 50)...")
            single_line = create_test_comment(api_session, source_uri, 50, 50, "Single-line comment")
            assert single_line is not None
            assert single_line['line_start'] == 50
            assert single_line['line_end'] == 50
            
            print(f"✅ Line anchoring works correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
