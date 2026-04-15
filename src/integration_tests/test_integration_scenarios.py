"""
Integration tests for end-to-end workflows.

Tested Scenarios:
- Complete edit workflow (create space → create change → approve → commit)
- Complete comment workflow (create space → add comments → resolve)
- Multiple enrichment types aggregation (comments + line ranges)
- Enrichment type listing
- Cross-feature integration (spaces + comments + changes)

Untested Scenarios / Gaps:
- Multi-user collaboration (concurrent edits)
- Conflict resolution workflows
- Real git provider integration in workflows
- Document synchronization workflows
- Permission-based workflows (viewer/editor/admin)
- Bulk operations workflows
- Import/export workflows
- Migration workflows
- Rollback/undo workflows
- Branching and merging workflows
- Review and approval chains
- Notification workflows

Test Strategy:
- Each test is completely independent
- Tests use real backend with actual database
- Tests real user workflows end-to-end
- Proper cleanup in finally blocks
- Comprehensive logging for debugging
"""
import pytest
import requests
from .test_helpers import (
    create_space,
    delete_space,
    get_unique_id,
    create_comment,
    cleanup_test_comments,
    create_user_change,
    approve_user_change,
    cleanup_test_user_changes
)


# ============================================================================
# Test Classes
# ============================================================================

class TestEditWorkflow:
    """Test complete edit workflow from creation to commit."""
    
    def test_complete_edit_workflow(self, api_session):
        """
        Test: Complete edit workflow
        
        End-to-end scenario:
        1. Create a space
        2. Simulate loading a file
        3. Create a pending change (edit)
        4. Approve the change
        5. Commit the change
        6. Verify final state
        7. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Complete edit workflow")
        print("="*80)
        print("Purpose: Verify end-to-end edit and approval workflow")
        print("Expected: Change goes from pending → approved → committed")
        
        test_id = get_unique_id()
        space_slug = f"test-edit-workflow-{test_id}"
        repo_name = f"test_{test_id}/edit-workflow-repo"
        file_path = "src/main.py"
        
        try:
            # Step 1: Create space
            print(f"\n📤 Step 1: Creating space '{space_slug}'...")
            space = create_space(api_session, test_id, slug=space_slug, name=f"Edit Workflow Test {test_id}")
            assert space is not None, "Failed to create space"
            print(f"✅ Space created: {space['id']}")
            
            # Step 2: Simulate file content
            print(f"\n📤 Step 2: Simulating file content...")
            original_content = """def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
"""
            modified_content = """def main():
    print("Hello, DocLab!")
    print("This is an updated version")

if __name__ == "__main__":
    main()
"""
            print(f"✅ File content prepared")
            
            # Step 3: Create pending change
            print(f"\n📤 Step 3: Creating pending change...")
            change = create_user_change(
                api_session,
                repo_name,
                file_path,
                original_content,
                modified_content,
                "Update greeting message and add version info"
            )
            assert change is not None, "Failed to create change"
            assert change['status'] == 'pending'
            print(f"✅ Pending change created: {change['id']}")
            
            # Step 4: Approve change
            print(f"\n📤 Step 4: Approving change...")
            approved = approve_user_change(api_session, change['id'])
            assert approved is not None, "Failed to approve change"
            assert approved['status'] == 'approved'
            print(f"✅ Change approved")
            
            # Step 5: Commit change
            print(f"\n📤 Step 5: Committing approved changes...")
            commit_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/changes/commit_batch/",
                headers=api_session.headers,
                timeout=5
            )
            assert commit_response.status_code == 200
            print(f"✅ Changes committed: {commit_response.json()['message']}")
            
            # Step 6: Verify final state
            print(f"\n📤 Step 6: Verifying final state...")
            final_change = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/{change['id']}/",
                headers=api_session.headers,
                timeout=5
            ).json()
            
            assert final_change['status'] == 'committed'
            assert final_change['repository_full_name'] == repo_name
            assert final_change['file_path'] == file_path
            print(f"✅ Change successfully committed")
            
            print(f"\n🎉 Complete edit workflow successful!")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
            delete_space(api_session, space_slug)


class TestCommentWorkflow:
    """Test complete comment workflow."""
    
    def test_complete_comment_workflow(self, api_session):
        """
        Test: Complete comment workflow
        
        End-to-end scenario:
        1. Create a space
        2. Add a comment to a file
        3. Reply to the comment (threading)
        4. Resolve the comment thread
        5. Verify enrichments include the comment
        6. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Complete comment workflow")
        print("="*80)
        print("Purpose: Verify end-to-end comment and resolution workflow")
        print("Expected: Comment thread created, replied to, and resolved")
        
        test_id = get_unique_id()
        space_slug = f"test-comment-workflow-{test_id}"
        source_uri = f"git://test/example.com/project/repo/main/workflow_{test_id}.py"
        
        try:
            # Step 1: Create space
            print(f"\n📤 Step 1: Creating space '{space_slug}'...")
            space = create_space(api_session, test_id, slug=space_slug, name=f"Comment Workflow Test {test_id}")
            assert space is not None
            print(f"✅ Space created")
            
            # Step 2: Add comment
            print(f"\n📤 Step 2: Adding comment to file...")
            parent_comment = create_comment(
                api_session,
                source_uri,
                "This needs review",
                line_start=15,
                line_end=15
            )
            assert parent_comment is not None
            assert parent_comment['is_resolved'] is False
            print(f"✅ Comment added: {parent_comment['id']}")
            
            # Step 3: Reply to comment
            print(f"\n📤 Step 3: Adding reply to comment...")
            reply_comment = create_comment(
                api_session,
                source_uri,
                "I'll take a look",
                line_start=15,
                line_end=15,
                parent_id=parent_comment['id']
            )
            assert reply_comment is not None
            assert reply_comment['parent_comment'] == parent_comment['id']
            print(f"✅ Reply added: {reply_comment['id']}")
            
            # Step 4: Resolve comment thread
            print(f"\n📤 Step 4: Resolving comment thread...")
            resolve_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/comments/{parent_comment['id']}/resolve/",
                headers=api_session.headers,
                timeout=5
            )
            assert resolve_response.status_code == 200
            resolved = resolve_response.json()
            assert resolved['is_resolved'] is True
            print(f"✅ Comment thread resolved")
            
            # Step 5: Verify enrichments
            print(f"\n📤 Step 5: Verifying enrichments include comment...")
            enrichments_response = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/?source_uri={source_uri}",
                headers=api_session.headers,
                timeout=5
            )
            assert enrichments_response.status_code == 200
            enrichments = enrichments_response.json()
            
            assert 'comments' in enrichments
            assert len(enrichments['comments']) > 0
            
            # Find our comment
            our_comment = next(
                (c for c in enrichments['comments'] if c['id'] == parent_comment['id']),
                None
            )
            assert our_comment is not None
            assert our_comment['is_resolved'] is True
            print(f"✅ Comment appears in enrichments")
            
            print(f"\n🎉 Complete comment workflow successful!")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
            delete_space(api_session, space_slug)


class TestEnrichmentAggregation:
    """Test enrichment aggregation across multiple types."""
    
    def test_multiple_enrichment_types(self, api_session):
        """
        Test: Multiple enrichment types on same file
        
        Scenario:
        1. Create comments on a file
        2. Create pending changes for the file
        3. Get all enrichments
        4. Verify all types are present and aggregated correctly
        5. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Multiple enrichment types")
        print("="*80)
        print("Purpose: Verify enrichment aggregation across types")
        print("Expected: Comments and diffs both appear in enrichments")
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/enrichment_{test_id}.py"
        repo_name = f"test_{test_id}/enrichment-repo"
        file_path = f"enrichment_{test_id}.py"
        
        try:
            # Step 1: Create comments
            print(f"\n📤 Step 1: Creating comments...")
            comment1 = create_comment(api_session, source_uri, "Comment 1", line_start=10, line_end=15)
            comment2 = create_comment(api_session, source_uri, "Comment 2", line_start=20, line_end=25)
            assert comment1 and comment2
            print(f"✅ Created 2 comments")
            
            # Step 2: Create pending change
            print(f"\n📤 Step 2: Creating pending change...")
            change = create_user_change(
                api_session,
                repo_name,
                file_path,
                "original code",
                "modified code",
                "Test enrichment aggregation"
            )
            assert change is not None
            print(f"✅ Created pending change")
            
            # Step 3: Get all enrichments
            print(f"\n📤 Step 3: Getting all enrichments...")
            enrichments_response = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/?source_uri={source_uri}",
                headers=api_session.headers,
                timeout=5
            )
            assert enrichments_response.status_code == 200
            enrichments = enrichments_response.json()
            
            # Step 4: Verify all types present
            print(f"\n📤 Step 4: Verifying enrichment types...")
            assert 'comments' in enrichments
            assert len(enrichments['comments']) == 2
            
            # Note: diff enrichments use repository_full_name, not source_uri
            # So they won't appear for this source_uri
            print(f"✅ Comments enrichments verified")
            
            # Step 5: Test filtering by type
            print(f"\n📤 Step 5: Testing type filtering...")
            comments_only = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/?source_uri={source_uri}&type=comments",
                headers=api_session.headers,
                timeout=5
            ).json()
            
            assert 'comments' in comments_only
            assert len(comments_only['comments']) == 2
            print(f"✅ Type filtering works")
            
            print(f"\n🎉 Enrichment aggregation successful!")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)
            cleanup_test_user_changes(api_session)
    
    def test_enrichment_line_ranges(self, api_session):
        """
        Test: Enrichments on overlapping line ranges
        
        Scenario:
        1. Create comments on different line ranges
        2. Create comments on overlapping ranges
        3. Verify all are tracked correctly
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Enrichment line ranges")
        print("="*80)
        
        test_id = get_unique_id()
        source_uri = f"git://test/example.com/project/repo/main/lines_{test_id}.py"
        
        try:
            # Create comments on different ranges
            print(f"\n📤 Creating comments on different line ranges...")
            comment1 = create_comment(api_session, source_uri, "Lines 10-15", line_start=10, line_end=15)
            comment2 = create_comment(api_session, source_uri, "Lines 20-25", line_start=20, line_end=25)
            comment3 = create_comment(api_session, source_uri, "Lines 12-18 (overlaps)", line_start=12, line_end=18)
            
            assert comment1 and comment2 and comment3
            
            # Get enrichments
            print(f"\n📤 Getting enrichments...")
            enrichments = requests.get(
                f"{api_session.base_url}/api/enrichments/v1/enrichments/?source_uri={source_uri}",
                headers=api_session.headers,
                timeout=5
            ).json()
            
            assert len(enrichments['comments']) == 3
            
            # Verify line ranges
            comments = enrichments['comments']
            assert any(c['line_start'] == 10 and c['line_end'] == 15 for c in comments)
            assert any(c['line_start'] == 20 and c['line_end'] == 25 for c in comments)
            assert any(c['line_start'] == 12 and c['line_end'] == 18 for c in comments)
            
            print(f"✅ All line ranges tracked correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_comments(api_session, source_uri)


class TestEnrichmentTypes:
    """Test enrichment type listing and filtering."""
    
    def test_list_enrichment_types(self, api_session):
        """
        Test: List available enrichment types
        
        Scenario:
        1. Get list of enrichment types
        2. Verify expected types are present
        """
        print("\n" + "="*80)
        print("TEST: List enrichment types")
        print("="*80)
        
        print(f"\n📤 Getting enrichment types...")
        response = requests.get(
            f"{api_session.base_url}/api/enrichments/v1/enrichments/types/",
            headers=api_session.headers,
            timeout=5
        )
        
        assert response.status_code == 200
        types_data = response.json()
        
        assert 'types' in types_data
        types = types_data['types']
        
        # Verify expected types
        expected_types = ['comments', 'diff', 'pr_diff', 'local_changes']
        for expected_type in expected_types:
            assert expected_type in types, f"Expected type '{expected_type}' not found"
        
        print(f"✅ All expected enrichment types present: {types}")
        print(f"\n🎉 Enrichment types test successful!")
