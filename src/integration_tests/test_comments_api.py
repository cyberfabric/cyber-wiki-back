"""
Integration tests for File Comments API.

Tested Scenarios:
- Creating comments on files (document-level and line-specific)
- Listing comments by source URI
- Filtering comments by resolved status
- Updating comment text
- Resolving and unresolving comments
- Deleting comments
- Comment threading (parent-child relationships)
- Line anchoring (start line, end line, line ranges)
- Document-level comments with threaded replies
- Line-specific comments with threaded replies
- Mixed document and line comments with replies
- Reply inheritance of parent context
- Nested reply chains (multi-level threading)
- Thread retrieval and structure verification

Untested Scenarios / Gaps:
- Comment permissions (who can edit/delete others' comments)
- Comment notifications
- Comment mentions (@username)
- Comment attachments
- Bulk comment operations
- Comment search/filtering by author or date
- Comment versioning/edit history
- Maximum thread depth limits
- Comment ordering within threads
- Thread collapsing/expanding
- Thread locking/archiving
- Cross-document thread references
- Thread search and filtering
- Thread export
- Thread permissions (who can reply)
- Thread moderation and spam detection

Test Strategy:
- Each test is completely independent
- Tests use real backend with actual database
- Proper cleanup in finally blocks
- Comprehensive logging for debugging
- Uses centralized helpers from test_helpers.py
"""
import pytest
import requests
from .test_helpers import (
    create_space,
    delete_space,
    get_unique_id,
    create_comment,
    delete_comment,
    cleanup_test_comments
)


# ============================================================================
# Local Helper Functions (specific to comments tests)
# ============================================================================

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
            f"{api_session.base_url}/api/wiki/v1/comments/",
            params={"source_uri": source_uri},
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️  Failed to get comments: {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️  Error getting comments: {e}")
        return []


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
            comment = create_comment(api_session, source_uri, comment_text, line_start=10, line_end=15)
            
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
            comment1 = create_comment(api_session, source_uri, "Comment 1", line_start=10, line_end=12)
            comment2 = create_comment(api_session, source_uri, "Comment 2", line_start=20, line_end=25)
            comment3 = create_comment(api_session, source_uri, "Comment 3", line_start=30, line_end=30)
            
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
            comment = create_comment(api_session, source_uri, "Original text", line_start=10, line_end=15)
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
        comment = create_comment(api_session, source_uri, "To be deleted", line_start=10, line_end=15)
        assert comment is not None
        
        # Test: Delete comment
        print(f"\n📤 Deleting comment...")
        success = delete_comment(api_session, comment['id'])
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
            comment = create_comment(api_session, source_uri, "Needs resolution", line_start=10, line_end=15)
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
            comment = create_comment(api_session, source_uri, "Will be unresolved", line_start=10, line_end=15)
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
            comment1 = create_comment(api_session, source_uri, "Unresolved 1", line_start=10, line_end=12)
            comment2 = create_comment(api_session, source_uri, "Unresolved 2", line_start=20, line_end=22)
            comment3 = create_comment(api_session, source_uri, "To be resolved", line_start=30, line_end=32)
            
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
            parent = create_comment(api_session, source_uri, "Parent comment", line_start=10, line_end=15)
            assert parent is not None
            
            # Test: Create reply
            print(f"\n📤 Creating reply to parent...")
            reply = create_comment(api_session, source_uri, "Reply comment", line_start=10, line_end=15, parent_id=parent['id'])
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
            multi_line = create_comment(api_session, source_uri, "Multi-line comment", line_start=10, line_end=20)
            assert multi_line is not None
            assert multi_line['line_start'] == 10
            assert multi_line['line_end'] == 20
            
            # Test: Single-line comment
            print(f"\n📤 Creating single-line comment (line 50)...")
            single_line = create_comment(api_session, source_uri, "Single-line comment", line_start=50, line_end=50)
            assert single_line is not None
            assert single_line['line_start'] == 50
            assert single_line['line_end'] == 50
            
            print(f"✅ Line anchoring works correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
    
    def test_document_level_comment_with_replies(self, api_session):
        """Test creating document-level comment with nested replies."""
        print("\n" + "="*80)
        print("TEST: Document-Level Comment with Nested Replies")
        print("="*80)
        print("Purpose: Verify document comments support multi-level threaded replies")
        print("Expected: Parent comment has no line anchoring, replies form nested structure")
        
        import uuid
        source_uri = f"git://test-repo/main/test-doc-comments-{uuid.uuid4()}.py"
        parent_id = None
        reply1_id = None
        reply2_id = None
        nested_reply_id = None
        
        try:
            # Step 1: Create document-level comment (no line_start/line_end)
            print(f"\n📤 Step 1: Creating document-level comment...")
            parent = create_comment(
                api_session,
                source_uri=source_uri,
                text="This is a document-level comment about the entire file"
            )
            assert parent is not None, "Failed to create parent comment"
            parent_id = parent['id']
            
            print(f"\n✅ Document comment created:")
            print(f"   ID: {parent_id}")
            print(f"   Line Start: {parent.get('line_start')}")
            print(f"   Line End: {parent.get('line_end')}")
            
            # Verify it's a document-level comment
            assert parent.get('line_start') is None, "Document comment should have no line_start"
            assert parent.get('line_end') is None, "Document comment should have no line_end"
            
            # Step 2: Add first reply to document comment
            print(f"\n📤 Step 2: Adding first reply to document comment...")
            reply1 = create_comment(
                api_session,
                source_uri=source_uri,
                text="I agree with this document-level observation",
                parent_id=parent_id
            )
            assert reply1 is not None, "Failed to create reply1"
            reply1_id = reply1['id']
            print(f"   ✓ Reply 1 created (ID: {reply1_id})")
            assert reply1.get('parent_id') == parent_id, f"Reply should have parent_id={parent_id}"
            
            # Step 3: Add second reply to document comment
            print(f"\n📤 Step 3: Adding second reply to document comment...")
            reply2 = create_comment(
                api_session,
                source_uri=source_uri,
                text="Another perspective on the document",
                parent_id=parent_id
            )
            assert reply2 is not None, "Failed to create reply2"
            reply2_id = reply2['id']
            print(f"   ✓ Reply 2 created (ID: {reply2_id})")
            
            # Step 4: Add nested reply (reply to reply)
            print(f"\n📤 Step 4: Adding nested reply (reply to reply1)...")
            nested_reply = create_comment(
                api_session,
                source_uri=source_uri,
                text="Responding to the first reply",
                parent_id=reply1_id
            )
            assert nested_reply is not None, "Failed to create nested reply"
            nested_reply_id = nested_reply['id']
            print(f"   ✓ Nested reply created (ID: {nested_reply_id})")
            assert nested_reply.get('parent_id') == reply1_id, f"Nested reply should have parent_id={reply1_id}"
            
            # Step 5: Retrieve all comments and verify structure
            print(f"\n📤 Step 5: Retrieving all comments for source_uri...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}",
                headers=api_session.headers
            )
            
            assert response.status_code == 200, f"Failed to list comments: {response.text}"
            root_comments = response.json()
            print(f"   ✓ Retrieved {len(root_comments)} root comment(s)")
            
            # Verify nested structure
            assert len(root_comments) == 1, f"Should have 1 root comment, got {len(root_comments)}"
            
            parent_from_list = root_comments[0]
            assert parent_from_list['id'] == parent_id, "Root comment ID mismatch"
            assert parent_from_list.get('line_start') is None, "Parent should have no line_start"
            
            replies = parent_from_list.get('replies', [])
            assert len(replies) == 2, f"Parent should have 2 direct replies, got {len(replies)}"
            
            reply1_from_list = next((r for r in replies if r['id'] == reply1_id), None)
            assert reply1_from_list is not None, "Reply1 not found in parent's replies"
            
            nested_replies = reply1_from_list.get('replies', [])
            assert len(nested_replies) == 1, f"Reply1 should have 1 nested reply, got {len(nested_replies)}"
            assert nested_replies[0]['id'] == nested_reply_id, "Nested reply ID mismatch"
            
            print(f"\n✅ PASS: Document-level threading works correctly")
            print(f"   Structure:")
            print(f"   - Document comment (ID: {parent_id})")
            print(f"     ├─ Reply 1 (ID: {reply1_id})")
            print(f"     │  └─ Nested reply (ID: {nested_reply_id})")
            print(f"     └─ Reply 2 (ID: {reply2_id})")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up comments...")
            for comment_id in [nested_reply_id, reply2_id, reply1_id, parent_id]:
                if comment_id:
                    delete_comment(api_session, comment_id)
            print(f"   ✓ All comments deleted")
        
        print("="*80)
    
    def test_line_specific_comment_with_replies(self, api_session):
        """Test creating line-specific comment with replies."""
        print("\n" + "="*80)
        print("TEST: Line-Specific Comment with Replies")
        print("="*80)
        print("Purpose: Verify line comments support threaded replies")
        print("Expected: Parent comment has line anchoring, replies inherit context")
        
        import uuid
        source_uri = f"git://test-repo/main/test-line-comments-{uuid.uuid4()}.py"
        parent_id = None
        reply_id = None
        
        try:
            # Step 1: Create line-specific comment
            print(f"\n📤 Step 1: Creating line-specific comment (line 42)...")
            parent = create_comment(
                api_session,
                source_uri=source_uri,
                text="This line has a bug",
                line_start=42,
                line_end=42
            )
            assert parent is not None, "Failed to create parent comment"
            parent_id = parent['id']
            
            print(f"\n✅ Line comment created:")
            print(f"   ID: {parent_id}")
            print(f"   Line: {parent.get('line_start')}")
            
            # Verify it's a line-specific comment
            assert parent.get('line_start') == 42, "Should have line_start=42"
            assert parent.get('line_end') == 42, "Should have line_end=42"
            
            # Step 2: Add reply to line comment
            print(f"\n📤 Step 2: Adding reply to line comment...")
            reply = create_comment(
                api_session,
                source_uri=source_uri,
                text="Good catch! Here's how to fix it...",
                parent_id=parent_id
            )
            assert reply is not None, "Failed to create reply"
            reply_id = reply['id']
            print(f"   ✓ Reply created (ID: {reply_id})")
            assert reply.get('parent_id') == parent_id, f"Reply should have parent_id={parent_id}"
            
            # Step 3: Retrieve comments and verify
            print(f"\n📤 Step 3: Retrieving comments...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}",
                headers=api_session.headers
            )
            
            assert response.status_code == 200, f"Failed to list comments: {response.text}"
            root_comments = response.json()
            print(f"   ✓ Retrieved {len(root_comments)} root comment(s)")
            
            assert len(root_comments) == 1, f"Should have 1 root comment, got {len(root_comments)}"
            
            parent_from_list = root_comments[0]
            assert parent_from_list['id'] == parent_id, "Root comment ID mismatch"
            assert parent_from_list.get('line_start') == 42, "Parent should have line_start=42"
            
            replies = parent_from_list.get('replies', [])
            assert len(replies) == 1, f"Parent should have 1 reply, got {len(replies)}"
            assert replies[0]['id'] == reply_id, "Reply ID mismatch"
            
            print(f"\n✅ PASS: Line-specific threading works correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up comments...")
            for comment_id in [reply_id, parent_id]:
                if comment_id:
                    delete_comment(api_session, comment_id)
            print(f"   ✓ All comments deleted")
        
        print("="*80)
    
    def test_mixed_document_and_line_comments(self, api_session):
        """Test mixing document-level and line-specific comments with replies."""
        print("\n" + "="*80)
        print("TEST: Mixed Document and Line Comments")
        print("="*80)
        print("Purpose: Verify document and line comments don't interfere")
        print("Expected: Each type maintains its own threading structure")
        
        import uuid
        source_uri = f"git://test-repo/main/test-mixed-comments-{uuid.uuid4()}.py"
        doc_id = None
        line_id = None
        doc_reply_id = None
        line_reply_id = None
        
        try:
            # Create document comment
            print(f"\n📤 Creating document comment...")
            doc_comment = create_comment(
                api_session,
                source_uri=source_uri,
                text="Overall file structure looks good"
            )
            assert doc_comment is not None, "Failed to create document comment"
            doc_id = doc_comment['id']
            print(f"   ✓ Document comment (ID: {doc_id})")
            
            # Create line comment
            print(f"\n📤 Creating line comment...")
            line_comment = create_comment(
                api_session,
                source_uri=source_uri,
                text="This line needs attention",
                line_start=10,
                line_end=10
            )
            assert line_comment is not None, "Failed to create line comment"
            line_id = line_comment['id']
            print(f"   ✓ Line comment (ID: {line_id})")
            
            # Add reply to document comment
            print(f"\n📤 Adding reply to document comment...")
            doc_reply = create_comment(
                api_session,
                source_uri=source_uri,
                text="I agree about the structure",
                parent_id=doc_id
            )
            assert doc_reply is not None, "Failed to create doc reply"
            doc_reply_id = doc_reply['id']
            print(f"   ✓ Reply to document (ID: {doc_reply_id})")
            
            # Add reply to line comment
            print(f"\n📤 Adding reply to line comment...")
            line_reply = create_comment(
                api_session,
                source_uri=source_uri,
                text="Fixed in latest commit",
                parent_id=line_id
            )
            assert line_reply is not None, "Failed to create line reply"
            line_reply_id = line_reply['id']
            print(f"   ✓ Reply to line (ID: {line_reply_id})")
            
            # Retrieve and verify
            print(f"\n📤 Retrieving all comments...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/comments/?source_uri={source_uri}",
                headers=api_session.headers
            )
            assert response.status_code == 200
            root_comments = response.json()
            
            assert len(root_comments) == 2, f"Should have 2 root comments, got {len(root_comments)}"
            
            # Find document and line comments
            doc_from_list = next((c for c in root_comments if c['id'] == doc_id), None)
            line_from_list = next((c for c in root_comments if c['id'] == line_id), None)
            
            assert doc_from_list is not None, "Document comment not found"
            assert line_from_list is not None, "Line comment not found"
            
            # Verify document comment thread
            assert doc_from_list.get('line_start') is None, "Doc comment should have no line"
            doc_replies = doc_from_list.get('replies', [])
            assert len(doc_replies) == 1, f"Doc comment should have 1 reply, got {len(doc_replies)}"
            assert doc_replies[0]['id'] == doc_reply_id, "Doc reply ID mismatch"
            
            # Verify line comment thread
            assert line_from_list.get('line_start') == 10, "Line comment should have line=10"
            line_replies = line_from_list.get('replies', [])
            assert len(line_replies) == 1, f"Line comment should have 1 reply, got {len(line_replies)}"
            assert line_replies[0]['id'] == line_reply_id, "Line reply ID mismatch"
            
            print(f"\n✅ PASS: Mixed comments maintain separate threading")
            print(f"   Document thread: {doc_id} → {doc_reply_id}")
            print(f"   Line thread: {line_id} → {line_reply_id}")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up comments...")
            for comment_id in [line_reply_id, doc_reply_id, line_id, doc_id]:
                if comment_id:
                    delete_comment(api_session, comment_id)
            print(f"   ✓ All comments deleted")
        
        print("="*80)
    
    def test_reply_without_line_anchoring_inherits_parent_context(self, api_session):
        """Test that replies don't need line anchoring - they inherit from parent."""
        print("\n" + "="*80)
        print("TEST: Reply Inherits Parent Context")
        print("="*80)
        print("Purpose: Verify replies don't need explicit line_start/line_end")
        print("Expected: Replies work with just parent_id field")
        
        import uuid
        source_uri = f"git://test-repo/main/test-reply-inherit-{uuid.uuid4()}.py"
        parent_id = None
        reply_id = None
        
        try:
            # Create line comment
            print(f"\n📤 Creating line comment...")
            parent = create_comment(
                api_session,
                source_uri=source_uri,
                text="This block of code is complex",
                line_start=25,
                line_end=30
            )
            assert parent is not None, "Failed to create parent comment"
            parent_id = parent['id']
            
            # Create reply WITHOUT line_start/line_end
            print(f"\n📤 Creating reply without line anchoring...")
            reply = create_comment(
                api_session,
                source_uri=source_uri,
                text="We should refactor this",
                parent_id=parent_id
                # Note: NO line_start or line_end
            )
            
            assert reply is not None, "Reply should work without line anchoring"
            reply_id = reply['id']
            
            print(f"   ✓ Reply created (ID: {reply_id})")
            print(f"   Parent ID: {reply.get('parent_id')}")
            print(f"   Line Start: {reply.get('line_start')}")
            print(f"   Line End: {reply.get('line_end')}")
            
            # Verify reply has parent
            assert reply.get('parent_id') == parent_id, "Should have parent_id"
            
            print(f"\n✅ PASS: Replies work without explicit line anchoring")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up comments...")
            for comment_id in [reply_id, parent_id]:
                if comment_id:
                    delete_comment(api_session, comment_id)
            print(f"   ✓ All comments deleted")
        
        print("="*80)
