"""
Integration tests for Enrichment Provider API.

Tests the enrichment system including:
- Enrichment retrieval (all types and filtered)
- Comment enrichments
- Diff enrichments
- Local changes enrichments
- PR enrichments
- Enrichment type listing
"""
import pytest
import requests
from .test_helpers import create_space, delete_space, get_unique_id


# ============================================================================
# Helper Functions for Enrichment Tests
# ============================================================================

def create_test_comment(api_session, source_uri: str, line_start: int = 1, line_end: int = 1, text: str = "Test comment"):
    """
    Create a test file comment.
    
    Args:
        api_session: Authenticated API session
        source_uri: Source URI for the comment
        line_start: Starting line number
        line_end: Ending line number
        text: Comment text
    
    Returns:
        Dict with created comment data or None
    """
    comment_data = {
        "source_uri": source_uri,
        "line_start": line_start,
        "line_end": line_end,
        "text": text,
    }
    
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
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  Error creating comment: {e}")
        return None


def delete_test_comment(api_session, comment_id: int) -> bool:
    """
    Delete a test comment.
    
    Args:
        api_session: Authenticated API session
        comment_id: ID of the comment to delete
    
    Returns:
        True if deletion was successful
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


def create_test_user_change(api_session, space_id: int, file_path: str, content: str = "Test content", description: str = "Test change"):
    """
    Create a test user change (pending change).
    
    Args:
        api_session: Authenticated API session
        space_id: ID of the space
        file_path: Path to the file
        content: Modified content
        description: Change description
    
    Returns:
        Dict with created change data or None
    """
    change_data = {
        "space_id": space_id,
        "file_path": file_path,
        "content": content,
        "description": description,
        "status": "pending",
    }
    
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/user-changes/",
            json=change_data,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            print(f"⚠️  Failed to create user change: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  Error creating user change: {e}")
        return None


def delete_test_user_change(api_session, change_id: int) -> bool:
    """
    Delete a test user change.
    
    Args:
        api_session: Authenticated API session
        change_id: ID of the change to delete
    
    Returns:
        True if deletion was successful
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/wiki/v1/user-changes/{change_id}/",
            headers=api_session.headers,
            timeout=5
        )
        return response.status_code in [200, 204]
    except Exception as e:
        print(f"⚠️  Error deleting user change {change_id}: {e}")
        return False


# ============================================================================
# Test Classes
# ============================================================================

class TestEnrichmentTypes:
    """Tests for enrichment type listing."""
    
    def test_get_enrichment_types(self, api_session):
        """
        Test: Get list of available enrichment types
        Expected: Returns list of all registered enrichment types
        """
        print("\n" + "="*80)
        print("TEST: Get Enrichment Types")
        print("="*80)
        
        print("\n📋 Step 1: Request enrichment types list")
        response = requests.get(
            f"{api_session.base_url}/api/enrichments/v1/enrichments/types/",
            headers=api_session.headers,
            timeout=5
        )
        
        print(f"✓ Response status: {response.status_code}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"✓ Response data: {data}")
        
        print("\n📋 Step 2: Verify enrichment types")
        assert 'types' in data, "Response should contain 'types' key"
        types = data['types']
        
        print(f"✓ Enrichment types: {types}")
        
        # Verify expected types are present
        expected_types = ['comments', 'local_changes', 'pr_diff', 'diff']
        for expected_type in expected_types:
            assert expected_type in types, f"Expected type '{expected_type}' not found in {types}"
            print(f"✓ Found expected type: {expected_type}")
        
        print("\n✅ TEST PASSED: Enrichment types retrieved successfully")


class TestCommentEnrichments:
    """Tests for comment enrichments."""
    
    def test_get_comment_enrichments(self, api_session):
        """
        Test: Get comment enrichments for a source URI
        Expected: Returns comments as enrichments
        """
        print("\n" + "="*80)
        print("TEST: Get Comment Enrichments")
        print("="*80)
        
        # Setup: Create test space and comment
        print("\n📋 Setup: Creating test space and comment")
        space = create_space(api_session, name_suffix="_comment_enrichment")
        assert space is not None, "Failed to create test space"
        print(f"✓ Created space: {space['slug']}")
        
        source_uri = f"git://test/test/{space['slug']}/test-repo/main/test.py"
        comment = None
        
        try:
            comment = create_test_comment(
                api_session,
                source_uri=source_uri,
                line_start=10,
                line_end=15,
                text="This is a test comment for enrichment"
            )
            assert comment is not None, "Failed to create test comment"
            print(f"✓ Created comment: ID {comment['id']}")
            
            print("\n📋 Step 1: Request enrichments for source URI")
            response = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/",
                params={"source_uri": source_uri},
                headers=api_session.headers,
                timeout=5
            )
            
            print(f"✓ Response status: {response.status_code}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            print(f"✓ Response keys: {list(data.keys())}")
            
            print("\n📋 Step 2: Verify comment enrichments")
            assert 'comments' in data, "Response should contain 'comments' key"
            comments = data['comments']
            
            print(f"✓ Found {len(comments)} comment enrichment(s)")
            assert len(comments) > 0, "Should have at least one comment enrichment"
            
            # Verify comment data
            comment_enrichment = comments[0]
            assert comment_enrichment['type'] == 'comment', "Enrichment type should be 'comment'"
            assert comment_enrichment['id'] == comment['id'], "Comment ID should match"
            assert comment_enrichment['line_start'] == 10, "Line start should be 10"
            assert comment_enrichment['line_end'] == 15, "Line end should be 15"
            assert 'test comment' in comment_enrichment['text'].lower(), "Comment text should match"
            
            print(f"✓ Comment enrichment verified: {comment_enrichment}")
            
            print("\n✅ TEST PASSED: Comment enrichments retrieved successfully")
            
        finally:
            # Cleanup
            print("\n🧹 Cleanup: Removing test artifacts")
            if comment:
                delete_test_comment(api_session, comment['id'])
                print(f"✓ Deleted comment: {comment['id']}")
            delete_space(api_session, space['slug'])
            print(f"✓ Deleted space: {space['slug']}")
    
    def test_filter_comment_enrichments_by_type(self, api_session):
        """
        Test: Filter enrichments by type (comments only)
        Expected: Returns only comment enrichments
        """
        print("\n" + "="*80)
        print("TEST: Filter Comment Enrichments by Type")
        print("="*80)
        
        # Setup
        print("\n📋 Setup: Creating test space and comment")
        space = create_space(api_session, name_suffix="_filter_comments")
        assert space is not None
        print(f"✓ Created space: {space['slug']}")
        
        source_uri = f"git://test/test/{space['slug']}/test-repo/main/filter.py"
        comment = None
        
        try:
            comment = create_test_comment(
                api_session,
                source_uri=source_uri,
                text="Filtered comment test"
            )
            assert comment is not None
            print(f"✓ Created comment: ID {comment['id']}")
            
            print("\n📋 Step 1: Request enrichments filtered by type=comments")
            response = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/",
                params={"source_uri": source_uri, "type": "comments"},
                headers=api_session.headers,
                timeout=5
            )
            
            print(f"✓ Response status: {response.status_code}")
            assert response.status_code == 200
            
            data = response.json()
            print(f"✓ Response keys: {list(data.keys())}")
            
            print("\n📋 Step 2: Verify only comments are returned")
            assert 'comments' in data, "Should have comments key"
            assert len(data) == 1, "Should only have one enrichment type"
            assert len(data['comments']) > 0, "Should have comment enrichments"
            
            print(f"✓ Filtered response contains only comments: {len(data['comments'])} item(s)")
            
            print("\n✅ TEST PASSED: Comment filtering works correctly")
            
        finally:
            # Cleanup
            print("\n🧹 Cleanup")
            if comment:
                delete_test_comment(api_session, comment['id'])
            delete_space(api_session, space['slug'])


class TestDiffEnrichments:
    """Tests for diff enrichments."""
    
    def test_get_diff_enrichments_no_changes(self, api_session):
        """
        Test: Get diff enrichments when no pending changes exist
        Expected: Returns empty diff enrichments
        """
        print("\n" + "="*80)
        print("TEST: Get Diff Enrichments (No Changes)")
        print("="*80)
        
        source_uri = f"git://test/test/project/repo/main/no_changes.py"
        
        print("\n📋 Step 1: Request enrichments for file with no changes")
        response = requests.get(
            f"{api_session.base_url}/api/enrichments/v1/enrichments/",
            params={"source_uri": source_uri, "type": "diff"},
            headers=api_session.headers,
            timeout=5
        )
        
        print(f"✓ Response status: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        print(f"✓ Response: {data}")
        
        print("\n📋 Step 2: Verify empty diff enrichments")
        assert 'diff' in data, "Should have diff key"
        assert len(data['diff']) == 0, "Should have no diff enrichments"
        
        print("✓ No diff enrichments found (as expected)")
        print("\n✅ TEST PASSED: Empty diff enrichments handled correctly")


class TestEnrichmentAggregation:
    """Tests for enrichment aggregation from multiple providers."""
    
    def test_get_all_enrichments(self, api_session):
        """
        Test: Get all enrichments from all providers
        Expected: Returns aggregated enrichments from all types
        """
        print("\n" + "="*80)
        print("TEST: Get All Enrichments (Aggregated)")
        print("="*80)
        
        # Setup
        print("\n📋 Setup: Creating test space and comment")
        space = create_space(api_session, name_suffix="_all_enrichments")
        assert space is not None
        print(f"✓ Created space: {space['slug']}")
        
        source_uri = f"git://test/test/{space['slug']}/test-repo/main/aggregate.py"
        comment = None
        
        try:
            comment = create_test_comment(
                api_session,
                source_uri=source_uri,
                text="Aggregation test comment"
            )
            assert comment is not None
            print(f"✓ Created comment: ID {comment['id']}")
            
            print("\n📋 Step 1: Request all enrichments (no type filter)")
            response = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/",
                params={"source_uri": source_uri},
                headers=api_session.headers,
                timeout=5
            )
            
            print(f"✓ Response status: {response.status_code}")
            assert response.status_code == 200
            
            data = response.json()
            print(f"✓ Response keys: {list(data.keys())}")
            
            print("\n📋 Step 2: Verify aggregated enrichments")
            # Should have multiple enrichment types
            assert isinstance(data, dict), "Response should be a dictionary"
            assert len(data) > 0, "Should have at least one enrichment type"
            
            # Verify comments are included
            assert 'comments' in data, "Should include comments"
            assert len(data['comments']) > 0, "Should have comment enrichments"
            
            print(f"✓ Aggregated enrichments from {len(data)} provider(s)")
            for enrichment_type, enrichments in data.items():
                print(f"  - {enrichment_type}: {len(enrichments)} item(s)")
            
            print("\n✅ TEST PASSED: Enrichment aggregation works correctly")
            
        finally:
            # Cleanup
            print("\n🧹 Cleanup")
            if comment:
                delete_test_comment(api_session, comment['id'])
            delete_space(api_session, space['slug'])


class TestEnrichmentErrorHandling:
    """Tests for enrichment API error handling."""
    
    def test_missing_source_uri_parameter(self, api_session):
        """
        Test: Request enrichments without source_uri parameter
        Expected: Returns 400 Bad Request with error message
        """
        print("\n" + "="*80)
        print("TEST: Missing source_uri Parameter")
        print("="*80)
        
        print("\n📋 Step 1: Request enrichments without source_uri")
        response = requests.get(
            f"{api_session.base_url}/api/enrichments/v1/enrichments/",
            headers=api_session.headers,
            timeout=5
        )
        
        print(f"✓ Response status: {response.status_code}")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        data = response.json()
        print(f"✓ Response: {data}")
        
        print("\n📋 Step 2: Verify error message")
        assert 'error' in data, "Response should contain error message"
        assert 'source_uri' in data['error'].lower(), "Error should mention source_uri"
        
        print(f"✓ Error message: {data['error']}")
        print("\n✅ TEST PASSED: Missing parameter handled correctly")
    
    def test_unauthenticated_request(self, session):
        """
        Test: Request enrichments without authentication
        Expected: Returns 401 Unauthorized, 403 Forbidden, or 404 Not Found
        """
        print("\n" + "="*80)
        print("TEST: Unauthenticated Enrichment Request")
        print("="*80)
        
        print("\n📋 Step 1: Request enrichments without authentication")
        response = requests.get(
            f"{session.base_url}/api/enrichments/v1/enrichments/",
            params={"source_uri": "git://test/test/test/test/main/test.py"},
            timeout=5
        )
        
        print(f"✓ Response status: {response.status_code}")
        # 401/403 = auth required, 404 = endpoint not accessible without auth
        assert response.status_code in [401, 403, 404], f"Expected 401, 403, or 404, got {response.status_code}"
        
        print("✓ Unauthenticated request rejected")
        print("\n✅ TEST PASSED: Authentication required for enrichments")
