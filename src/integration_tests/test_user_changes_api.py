"""
Integration tests for User Changes API.

Tests cover:
- Creating pending changes
- Listing changes (own and all for editors/admins)
- Filtering by status
- Getting change details
- Approving changes (editor/admin)
- Rejecting changes (editor/admin)
- Deleting changes
- Committing approved changes (admin)
- Change descriptions and metadata

Following TEST_STRUCTURE.md principles:
- Independent tests with proper setup/teardown
- Comprehensive logging
- Idempotent operations
- Reusable helper functions
"""
import pytest
import requests
from .test_helpers import get_unique_id


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_user_change(api_session, repository_full_name: str, file_path: str, 
                           original_content: str, modified_content: str, commit_message: str = ""):
    """
    Create a test user change.
    
    Args:
        api_session: API session fixture
        repository_full_name: Repository identifier
        file_path: File path in repository
        original_content: Original file content
        modified_content: Modified file content
        commit_message: Optional commit message
    
    Returns:
        dict: Created change data or None if failed
    """
    try:
        payload = {
            "repository_full_name": repository_full_name,
            "file_path": file_path,
            "original_content": original_content,
            "modified_content": modified_content,
            "commit_message": commit_message
        }
        
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/changes/",
            json=payload,
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 201:
            change = response.json()
            print(f"✅ Created test user change: {change['id']}")
            return change
        else:
            print(f"⚠️  Failed to create user change: {response.status_code}")
            print(f"    Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating user change: {e}")
        return None


def delete_test_user_change(api_session, change_id: str):
    """
    Delete a test user change.
    
    Args:
        api_session: API session fixture
        change_id: Change ID to delete
    
    Returns:
        bool: True if deleted successfully
    """
    try:
        response = requests.delete(
            f"{api_session.base_url}/api/wiki/v1/changes/{change_id}/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code in [200, 204]:
            print(f"✅ Deleted test user change: {change_id}")
            return True
        else:
            print(f"⚠️  Failed to delete user change {change_id}: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error deleting user change {change_id}: {e}")
        return False


def approve_user_change(api_session, change_id: str):
    """
    Approve a user change.
    
    Args:
        api_session: API session fixture
        change_id: Change ID to approve
    
    Returns:
        dict: Approved change data or None if failed
    """
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/changes/{change_id}/approve/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 200:
            change = response.json()
            print(f"✅ Approved user change: {change_id}")
            return change
        else:
            print(f"⚠️  Failed to approve user change: {response.status_code}")
            print(f"    Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error approving user change: {e}")
        return None


def reject_user_change(api_session, change_id: str):
    """
    Reject a user change.
    
    Args:
        api_session: API session fixture
        change_id: Change ID to reject
    
    Returns:
        dict: Rejected change data or None if failed
    """
    try:
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/changes/{change_id}/reject/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 200:
            change = response.json()
            print(f"✅ Rejected user change: {change_id}")
            return change
        else:
            print(f"⚠️  Failed to reject user change: {response.status_code}")
            print(f"    Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error rejecting user change: {e}")
        return None


def cleanup_test_user_changes(api_session):
    """
    Clean up all test user changes.
    
    Args:
        api_session: API session fixture
    """
    try:
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/changes/",
            headers=api_session.headers,
            timeout=5
        )
        
        if response.status_code == 200:
            changes = response.json()
            for change in changes:
                # Only delete test changes (those with test_ in repository name)
                if 'test_' in change.get('repository_full_name', ''):
                    delete_test_user_change(api_session, change['id'])
    except Exception as e:
        print(f"⚠️  Error during user changes cleanup: {e}")


# ============================================================================
# Test Classes
# ============================================================================

class TestUserChangesBasicOperations:
    """Test basic CRUD operations for user changes."""
    
    def test_create_pending_change(self, api_session):
        """
        Test: Create a pending change
        
        Scenario:
        1. Create a pending change with file modifications
        2. Verify response contains all expected fields
        3. Verify status is 'pending'
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Create pending change")
        print("="*80)
        print("Purpose: Verify pending changes can be created")
        print("Expected: HTTP 201, change with pending status")
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        file_path = f"src/test_{test_id}.py"
        
        try:
            # Test: Create change
            print(f"\n📤 Creating pending change for {repo_name}/{file_path}...")
            original = "def hello():\n    print('Hello')"
            modified = "def hello():\n    print('Hello, World!')"
            commit_msg = f"Test change {test_id}"
            
            change = create_test_user_change(
                api_session, repo_name, file_path, original, modified, commit_msg
            )
            
            assert change is not None, "Change creation failed"
            assert change['repository_full_name'] == repo_name
            assert change['file_path'] == file_path
            assert change['original_content'] == original
            assert change['modified_content'] == modified
            assert change['commit_message'] == commit_msg
            assert change['status'] == 'pending'
            assert 'id' in change
            assert 'user' in change
            assert 'created_at' in change
            
            print(f"✅ Pending change created successfully: {change['id']}")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
    
    def test_list_user_changes(self, api_session):
        """
        Test: List user changes
        
        Scenario:
        1. Create multiple changes
        2. List all changes
        3. Verify all changes are returned
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: List user changes")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        try:
            # Setup: Create multiple changes
            print(f"\n🔧 Setup: Creating 3 changes...")
            change1 = create_test_user_change(
                api_session, repo_name, "file1.py", "old1", "new1", "Change 1"
            )
            change2 = create_test_user_change(
                api_session, repo_name, "file2.py", "old2", "new2", "Change 2"
            )
            change3 = create_test_user_change(
                api_session, repo_name, "file3.py", "old3", "new3", "Change 3"
            )
            
            assert change1 and change2 and change3, "Failed to create test changes"
            
            # Test: List changes
            print(f"\n📤 Listing user changes...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            changes = response.json()
            
            # Filter to only our test changes
            test_changes = [c for c in changes if 'test_' in c['repository_full_name']]
            assert len(test_changes) >= 3, f"Expected at least 3 test changes, got {len(test_changes)}"
            
            change_ids = {c['id'] for c in test_changes}
            assert change1['id'] in change_ids
            assert change2['id'] in change_ids
            assert change3['id'] in change_ids
            
            print(f"✅ All changes retrieved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
    
    def test_get_change_detail(self, api_session):
        """
        Test: Get detailed change information
        
        Scenario:
        1. Create a change
        2. Get its details
        3. Verify all fields are present
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Get change detail")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        try:
            # Setup: Create change
            print(f"\n🔧 Setup: Creating change...")
            change = create_test_user_change(
                api_session, repo_name, "detail_test.py", "original", "modified", "Detail test"
            )
            assert change is not None
            
            # Test: Get detail
            print(f"\n📤 Getting change detail...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/{change['id']}/",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            detail = response.json()
            assert detail['id'] == change['id']
            assert detail['repository_full_name'] == repo_name
            assert detail['file_path'] == "detail_test.py"
            assert detail['status'] == 'pending'
            
            print(f"✅ Change detail retrieved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
    
    def test_delete_change(self, api_session):
        """
        Test: Delete a pending change
        
        Scenario:
        1. Create a change
        2. Delete it
        3. Verify it no longer exists
        """
        print("\n" + "="*80)
        print("TEST: Delete change")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        # Setup: Create change
        print(f"\n🔧 Setup: Creating change...")
        change = create_test_user_change(
            api_session, repo_name, "to_delete.py", "old", "new", "To be deleted"
        )
        assert change is not None
        
        # Test: Delete change
        print(f"\n📤 Deleting change...")
        success = delete_test_user_change(api_session, change['id'])
        assert success, "Failed to delete change"
        
        # Verify: Change no longer exists
        print(f"\n📤 Verifying change is gone...")
        response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/changes/{change['id']}/",
            headers=api_session.headers,
            timeout=5
        )
        assert response.status_code == 404, "Change still exists after deletion"
        
        print(f"✅ Change deleted successfully")


class TestUserChangesApprovalWorkflow:
    """Test approval/rejection workflow for user changes."""
    
    def test_approve_change(self, api_session):
        """
        Test: Approve a pending change
        
        Scenario:
        1. Create a pending change
        2. Approve it
        3. Verify status is 'approved'
        4. Verify approved_by is set
        5. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Approve change")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        try:
            # Setup: Create pending change
            print(f"\n🔧 Setup: Creating pending change...")
            change = create_test_user_change(
                api_session, repo_name, "approve_test.py", "old", "new", "To be approved"
            )
            assert change is not None
            assert change['status'] == 'pending'
            
            # Test: Approve change
            print(f"\n📤 Approving change...")
            approved = approve_user_change(api_session, change['id'])
            
            assert approved is not None, "Approval failed"
            assert approved['status'] == 'approved'
            assert approved['id'] == change['id']
            assert 'approved_by' in approved
            
            print(f"✅ Change approved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
    
    def test_reject_change(self, api_session):
        """
        Test: Reject a pending change
        
        Scenario:
        1. Create a pending change
        2. Reject it
        3. Verify status is 'rejected'
        4. Verify approved_by is set (reviewer)
        5. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Reject change")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        try:
            # Setup: Create pending change
            print(f"\n🔧 Setup: Creating pending change...")
            change = create_test_user_change(
                api_session, repo_name, "reject_test.py", "old", "new", "To be rejected"
            )
            assert change is not None
            assert change['status'] == 'pending'
            
            # Test: Reject change
            print(f"\n📤 Rejecting change...")
            rejected = reject_user_change(api_session, change['id'])
            
            assert rejected is not None, "Rejection failed"
            assert rejected['status'] == 'rejected'
            assert rejected['id'] == change['id']
            assert 'approved_by' in rejected
            
            print(f"✅ Change rejected successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
    
    def test_filter_changes_by_status(self, api_session):
        """
        Test: Filter changes by status
        
        Scenario:
        1. Create changes with different statuses
        2. Filter by status=pending
        3. Filter by status=approved
        4. Filter by status=rejected
        5. Verify correct filtering
        6. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Filter changes by status")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        try:
            # Setup: Create changes with different statuses
            print(f"\n🔧 Setup: Creating changes with different statuses...")
            pending1 = create_test_user_change(
                api_session, repo_name, "pending1.py", "old", "new", "Pending 1"
            )
            pending2 = create_test_user_change(
                api_session, repo_name, "pending2.py", "old", "new", "Pending 2"
            )
            to_approve = create_test_user_change(
                api_session, repo_name, "approved.py", "old", "new", "To approve"
            )
            to_reject = create_test_user_change(
                api_session, repo_name, "rejected.py", "old", "new", "To reject"
            )
            
            assert pending1 and pending2 and to_approve and to_reject
            
            # Approve and reject
            approve_user_change(api_session, to_approve['id'])
            reject_user_change(api_session, to_reject['id'])
            
            # Test: Filter for pending
            print(f"\n📤 Filtering for pending changes...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/?status=pending",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            pending_changes = response.json()
            test_pending = [c for c in pending_changes if 'test_' in c['repository_full_name']]
            assert len(test_pending) >= 2
            
            print(f"✅ Pending filter works correctly")
            
            # Test: Filter for approved
            print(f"\n📤 Filtering for approved changes...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/?status=approved",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            approved_changes = response.json()
            test_approved = [c for c in approved_changes if c['id'] == to_approve['id']]
            assert len(test_approved) == 1
            
            print(f"✅ Approved filter works correctly")
            
            # Test: Filter for rejected
            print(f"\n📤 Filtering for rejected changes...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/?status=rejected",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            rejected_changes = response.json()
            test_rejected = [c for c in rejected_changes if c['id'] == to_reject['id']]
            assert len(test_rejected) == 1
            
            print(f"✅ Rejected filter works correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)


class TestUserChangesAdvanced:
    """Test advanced user changes scenarios."""
    
    def test_change_with_description(self, api_session):
        """
        Test: Create change with detailed commit message
        
        Scenario:
        1. Create change with multi-line commit message
        2. Verify message is preserved
        3. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Change with description")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        try:
            # Test: Create with detailed message
            print(f"\n📤 Creating change with detailed commit message...")
            commit_msg = """Fix critical bug in authentication

This change addresses the security vulnerability in the login flow.
- Added input validation
- Improved error handling
- Updated tests"""
            
            change = create_test_user_change(
                api_session, repo_name, "auth.py", "old code", "new code", commit_msg
            )
            
            assert change is not None
            assert change['commit_message'] == commit_msg
            
            print(f"✅ Commit message preserved correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
    
    def test_concurrent_changes_same_file(self, api_session):
        """
        Test: Multiple pending changes on same file
        
        Scenario:
        1. Create multiple pending changes for same file
        2. Verify all are tracked separately
        3. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Concurrent changes on same file")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        file_path = "concurrent.py"
        
        try:
            # Test: Create multiple changes for same file
            print(f"\n📤 Creating multiple changes for {file_path}...")
            change1 = create_test_user_change(
                api_session, repo_name, file_path, "version 0", "version 1", "Change 1"
            )
            change2 = create_test_user_change(
                api_session, repo_name, file_path, "version 0", "version 2", "Change 2"
            )
            
            assert change1 and change2
            assert change1['id'] != change2['id']
            assert change1['file_path'] == change2['file_path']
            
            print(f"✅ Multiple changes tracked separately")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
    
    def test_commit_approved_changes(self, api_session):
        """
        Test: Commit batch of approved changes
        
        Scenario:
        1. Create and approve multiple changes
        2. Call commit_batch endpoint
        3. Verify changes are marked as committed
        4. Clean up
        """
        print("\n" + "="*80)
        print("TEST: Commit approved changes")
        print("="*80)
        
        test_id = get_unique_id()
        repo_name = f"test_{test_id}/example-repo"
        
        try:
            # Setup: Create and approve changes
            print(f"\n🔧 Setup: Creating and approving changes...")
            change1 = create_test_user_change(
                api_session, repo_name, "file1.py", "old1", "new1", "Commit test 1"
            )
            change2 = create_test_user_change(
                api_session, repo_name, "file2.py", "old2", "new2", "Commit test 2"
            )
            
            assert change1 and change2
            
            approve_user_change(api_session, change1['id'])
            approve_user_change(api_session, change2['id'])
            
            # Test: Commit batch
            print(f"\n📤 Committing approved changes...")
            response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/changes/commit_batch/",
                headers=api_session.headers,
                timeout=5
            )
            
            assert response.status_code == 200
            result = response.json()
            assert 'message' in result
            
            print(f"✅ Batch commit completed: {result['message']}")
            
            # Verify: Changes are marked as committed
            print(f"\n📤 Verifying changes are committed...")
            detail1 = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/{change1['id']}/",
                headers=api_session.headers,
                timeout=5
            ).json()
            
            detail2 = requests.get(
                f"{api_session.base_url}/api/wiki/v1/changes/{change2['id']}/",
                headers=api_session.headers,
                timeout=5
            ).json()
            
            assert detail1['status'] == 'committed'
            assert detail2['status'] == 'committed'
            
            print(f"✅ Changes marked as committed")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            cleanup_test_user_changes(api_session)
