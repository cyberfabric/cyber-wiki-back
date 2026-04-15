"""
Integration tests for Enrichment Provider API.

Tested Scenarios:
- Listing all enrichment types
- Retrieving comment enrichments for a file
- Filtering comment enrichments by type
- Threaded comment enrichments (parent-child relationships)
- Diff enrichments (no changes scenario)
- Aggregating all enrichments for a source URI
- Missing source_uri parameter error handling
- Unauthenticated request error handling

Untested Scenarios / Gaps:
- PR (Pull Request) enrichments with real git provider
- Local changes enrichments
- Diff enrichments with actual changes
- Enrichment caching behavior
- Enrichment performance with large files
- Enrichment ordering and sorting
- Enrichment pagination
- Real-time enrichment updates
- Enrichment conflicts resolution
- Cross-file enrichments
- Enrichment export/import

Test Strategy:
- Each test is completely independent
- Tests use real backend with actual database
- Proper cleanup in finally blocks
- Comprehensive logging for debugging
"""
import pytest
import requests
from .test_helpers import (
    create_space, delete_space, get_unique_id,
    create_comment, delete_comment,
    create_user_change, delete_user_change
)


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
            comment = create_comment(
                api_session,
                source_uri=source_uri,
                text="This is a test comment for enrichment",
                line_start=10,
                line_end=15
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
                delete_comment(api_session, comment['id'])
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
            comment = create_comment(
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
                delete_comment(api_session, comment['id'])
            delete_space(api_session, space['slug'])
    
    def test_threaded_comment_enrichments(self, api_session):
        """
        Test: Get comment enrichments with nested replies
        Expected: Returns root comments with replies field containing nested comments
        """
        print("\n" + "="*80)
        print("TEST: Threaded Comment Enrichments")
        print("="*80)
        
        import uuid
        source_uri = f"git://test/test/project/repo/main/threaded-{uuid.uuid4()}.py"
        parent_id = None
        reply1_id = None
        reply2_id = None
        
        try:
            # Create parent comment
            print("\n📋 Step 1: Create parent comment")
            parent = create_comment(
                api_session,
                source_uri=source_uri,
                text="Parent comment",
                line_start=10,
                line_end=10
            )
            assert parent is not None, "Failed to create parent comment"
            parent_id = parent['id']
            print(f"✓ Created parent comment: {parent_id}")
            
            # Create first reply
            print("\n📋 Step 2: Create first reply")
            reply1 = create_comment(
                api_session,
                source_uri=source_uri,
                text="First reply",
                parent_id=parent_id
            )
            assert reply1 is not None, "Failed to create first reply"
            reply1_id = reply1['id']
            print(f"✓ Created first reply: {reply1_id}")
            
            # Create second reply
            print("\n📋 Step 3: Create second reply")
            reply2 = create_comment(
                api_session,
                source_uri=source_uri,
                text="Second reply",
                parent_id=parent_id
            )
            assert reply2 is not None, "Failed to create second reply"
            reply2_id = reply2['id']
            print(f"✓ Created second reply: {reply2_id}")
            
            # Get enrichments
            print("\n📋 Step 4: Get comment enrichments")
            response = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/",
                params={"source_uri": source_uri, "type": "comments"},
                headers=api_session.headers
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify structure
            print("\n📋 Step 5: Verify nested structure")
            assert 'comments' in data
            comments = data['comments']
            assert len(comments) == 1, f"Should have 1 root comment, got {len(comments)}"
            
            root_comment = comments[0]
            assert root_comment['id'] == parent_id, "Root comment ID mismatch"
            assert 'replies' in root_comment, "Root comment should have replies field"
            assert len(root_comment['replies']) == 2, f"Should have 2 replies, got {len(root_comment['replies'])}"
            
            # Verify replies
            reply_ids = {r['id'] for r in root_comment['replies']}
            assert reply1_id in reply_ids, "Reply1 should be in replies"
            assert reply2_id in reply_ids, "Reply2 should be in replies"
            
            # Verify parent_id in replies
            for reply in root_comment['replies']:
                assert reply['parent_id'] == parent_id, f"Reply parent_id should be {parent_id}"
                assert 'replies' in reply, "Reply should have replies field (even if empty)"
            
            print(f"✓ Nested structure verified:")
            print(f"  - Root comment: {parent_id}")
            print(f"  - Replies: {[r['id'] for r in root_comment['replies']]}")
            
            print("\n✅ TEST PASSED: Threaded comment enrichments work correctly")
            
        finally:
            # Cleanup
            print("\n🧹 Cleanup")
            for comment_id in [reply2_id, reply1_id, parent_id]:
                if comment_id:
                    delete_comment(api_session, comment_id)


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
            comment = create_comment(
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
                delete_comment(api_session, comment['id'])
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
