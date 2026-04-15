"""
Integration tests for Wiki/Space API.

Tested Scenarios:
- Creating spaces with all fields
- Creating spaces with missing required fields (error handling)
- Reading/retrieving space details
- Listing all spaces
- Updating space editable fields
- Attempting to update immutable fields (slug)
- Deleting spaces
- Bulk operations (creating and listing multiple spaces)

Untested Scenarios / Gaps:
- Space permissions (viewer/editor/admin roles)
- Space visibility settings (public/private)
- Space templates
- Space cloning/duplication
- Space archiving/restoration
- Space search and filtering (by owner, tags, etc.)
- Space statistics (page count, contributors, etc.)
- Space configuration (git provider settings)
- Space webhooks
- Space export/import
- Space collaboration features
- Space audit logs
- Space quotas and limits

Test Strategy:
- Each test is completely independent
- Tests use real backend with actual database
- All test artifacts prefixed with 'test_' for easy identification
- Global cleanup removes leftover artifacts from failed tests
- Proper cleanup in finally blocks
- Comprehensive logging for debugging
"""
import pytest
import requests

from .test_helpers import (
    get_unique_id,
    create_space,
    delete_space,
    cleanup_all_test_spaces,
    TEST_PREFIX,
    TEST_SPACE_BASE_NAME,
    TEST_SPACE_DESCRIPTION
)


@pytest.fixture(scope="module", autouse=True)
def cleanup_before_and_after(api_session):
    """Clean up test artifacts before and after all tests in this module."""
    print("\n🧹 Cleaning up any leftover test artifacts...")
    cleanup_all_test_spaces(api_session)
    yield
    print("\n🧹 Final cleanup of test artifacts...")
    cleanup_all_test_spaces(api_session)


# ============================================================================
# Test Class: Space CRUD Operations
# ============================================================================

class TestSpaceCRUD:
    """Test CRUD operations for spaces. Each test is independent."""

    def test_create_space_with_all_fields(self, api_session):
        """Test creating a space with all required and optional fields."""
        print("\n" + "="*80)
        print("TEST: Create Space with All Fields")
        print("="*80)
        print("Purpose: Verify that a space can be created with all fields")
        print("Expected: HTTP 201, space created with all specified fields")
        
        unique_id = get_unique_id()
        space_data = {
            "name": f"{TEST_SPACE_BASE_NAME}_all_fields_{unique_id}",
            "slug": f"{TEST_PREFIX}allfields_{unique_id}",
            "description": TEST_SPACE_DESCRIPTION,
            "visibility": "private",
            "git_provider": "local_git",
            "git_base_url": "/tmp/test-repo",
            "git_repository_name": "test-repo",
            "git_default_branch": "main"
        }
        
        print(f"\n📤 Creating space: {space_data['name']}")
        
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/spaces/",
            json=space_data,
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        
        try:
            assert response.status_code == 201, f"Failed: {response.text}"
            data = response.json()
            space_slug = data["slug"]
            
            print(f"\n🔍 Verifying response fields...")
            assert data["name"] == space_data["name"]
            print(f"   ✓ name: {data['name']}")
            
            assert data["slug"] == space_data["slug"]
            print(f"   ✓ slug: {data['slug']}")
            
            assert data["description"] == space_data["description"]
            print(f"   ✓ description: {data['description'][:50]}...")
            
            assert data["visibility"] == space_data["visibility"]
            print(f"   ✓ visibility: {data['visibility']}")
            
            assert "id" in data
            print(f"   ✓ id: {data['id']}")
            
            assert "created_at" in data
            print(f"   ✓ created_at present")
            
            print(f"\n✅ PASS: Space created successfully")
            
        finally:
            # Cleanup
            if response.status_code == 201:
                print(f"\n🧹 Cleaning up test space...")
                if delete_space(api_session, space_slug):
                    print(f"   ✓ Deleted space {space_slug}")
                    
        print("="*80)

    def test_create_space_missing_required_fields(self, api_session):
        """Test that space creation fails without mandatory fields."""
        print("\n" + "="*80)
        print("TEST: Create Space Without Required Fields")
        print("="*80)
        print("Purpose: Verify validation of required fields")
        print("Expected: HTTP 400 for missing required fields")
        
        # Test missing 'name'
        print(f"\n📤 Test 1: Creating space without 'name' field")
        response = requests.post(
            f"{api_session.base_url}/api/wiki/v1/spaces/",
            json={"description": "Missing name"},
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 400, "Should fail without 'name'"
        print(f"✅ Correctly rejected: Missing 'name' returns HTTP 400")
        
        print("="*80)

    def test_read_space(self, api_session):
        """Test reading a space by ID."""
        print("\n" + "="*80)
        print("TEST: Read/Retrieve Space by ID")
        print("="*80)
        print("Purpose: Verify that a space can be retrieved by its ID")
        print("Expected: HTTP 200, space data returned")
        
        # Setup: Create a space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_read")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Test: Read the space
            print(f"\n📤 Reading space {space_slug}...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/spaces/{space_slug}/",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            print(f"\n🔍 Verifying response...")
            assert data["slug"] == space_slug
            print(f"   ✓ Slug matches: {data['slug']}")
            
            assert data["name"] == space["name"]
            print(f"   ✓ Name matches: {data['name']}")
            
            print(f"\n✅ PASS: Space retrieved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)

    def test_list_spaces(self, api_session):
        """Test listing all spaces."""
        print("\n" + "="*80)
        print("TEST: List All Spaces")
        print("="*80)
        print("Purpose: Verify that spaces can be listed")
        print("Expected: HTTP 200, list contains created test space")
        
        # Setup: Create a test space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_list")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Test: List spaces
            print(f"\n📤 Listing all spaces...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/spaces/",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            spaces = data if isinstance(data, list) else data.get("results", [])
            
            print(f"\n🔍 Analyzing response...")
            print(f"   Total spaces: {len(spaces)}")
            
            # Verify our test space is in the list
            found = any(s["slug"] == space_slug for s in spaces)
            assert found, "Created space not found in list"
            print(f"   ✓ Test space found in list")
            
            print(f"\n✅ PASS: Spaces listed successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)

    def test_update_space_editable_fields(self, api_session):
        """Test updating editable fields of a space."""
        print("\n" + "="*80)
        print("TEST: Update Space Editable Fields")
        print("="*80)
        print("Purpose: Verify that editable fields can be updated")
        print("Expected: HTTP 200, fields updated successfully")
        
        # Setup: Create a space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_update")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Test: Update editable fields
            updates = {
                "name": f"{space['name']}_updated",
                "description": "Updated description",
                "visibility": "team",
                "git_default_branch": "develop"
            }
            
            print(f"\n📤 Updating space {space_slug}...")
            print(f"   Updates: {list(updates.keys())}")
            
            response = requests.patch(
                f"{api_session.base_url}/api/wiki/v1/spaces/{space_slug}/",
                json=updates,
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            
            print(f"\n🔍 Verifying updates...")
            assert data["name"] == updates["name"]
            print(f"   ✓ name: {data['name']}")
            
            assert data["description"] == updates["description"]
            print(f"   ✓ description: {data['description']}")
            
            assert data["visibility"] == updates["visibility"]
            print(f"   ✓ visibility: {data['visibility']}")
            
            print(f"\n✅ PASS: Fields updated successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)

    def test_update_immutable_slug(self, api_session):
        """Test that immutable field 'slug' cannot be updated."""
        print("\n" + "="*80)
        print("TEST: Update Immutable Field (slug)")
        print("="*80)
        print("Purpose: Verify that 'slug' field is immutable")
        print("Expected: HTTP 400 or slug unchanged")
        
        # Setup: Create a space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_immutable")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Test: Try to update slug
            print(f"\n📤 Attempting to update slug...")
            response = requests.patch(
                f"{api_session.base_url}/api/wiki/v1/spaces/{space_slug}/",
                json={"slug": f"{TEST_PREFIX}new_slug_{get_unique_id()}"},
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n🔍 Verifying slug unchanged...")
                assert data["slug"] == space_slug, "Slug should not change"
                print(f"   ✓ Slug unchanged: {data['slug']}")
                print(f"\n✅ PASS: Slug update ignored (immutable)")
            elif response.status_code == 400:
                print(f"\n✅ PASS: Slug update rejected (immutable)")
            else:
                pytest.fail(f"Unexpected status: {response.status_code}")
                
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)

    def test_delete_space(self, api_session):
        """Test deleting a space."""
        print("\n" + "="*80)
        print("TEST: Delete Space")
        print("="*80)
        print("Purpose: Verify that a space can be deleted")
        print("Expected: HTTP 200/204, space no longer exists")
        
        # Setup: Create a space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_delete")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        # Test: Delete the space
        print(f"\n📤 Deleting space {space_slug}...")
        response = requests.delete(
            f"{api_session.base_url}/api/wiki/v1/spaces/{space_slug}/",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code in [200, 204], f"Failed: {response.text}"
        print(f"   ✓ Space deleted")
        
        # Verify deletion
        print(f"\n🔍 Verifying space no longer exists...")
        get_response = requests.get(
            f"{api_session.base_url}/api/wiki/v1/spaces/{space_slug}/",
            headers=api_session.headers
        )
        
        print(f"📥 GET Response: HTTP {get_response.status_code}")
        assert get_response.status_code == 404, "Space should not exist"
        print(f"   ✓ Space returns HTTP 404")
        
        print(f"\n✅ PASS: Space deleted and verified")
        print("="*80)


# ============================================================================
# Test Class: Bulk Operations
# ============================================================================

class TestBulkOperations:
    """Test bulk operations. Each test is independent."""

    def test_create_and_list_multiple_spaces(self, api_session):
        """Test creating multiple spaces and listing them."""
        print("\n" + "="*80)
        print("TEST: Create and List Multiple Spaces")
        print("="*80)
        print("Purpose: Verify bulk space creation and listing")
        print("Expected: All created spaces appear in list")
        
        # Setup: Create multiple spaces
        print(f"\n🔧 Setup: Creating 3 test spaces...")
        spaces = []
        for i in range(3):
            space = create_space(api_session, name_suffix=f"_bulk_{i}")
            if space:
                spaces.append(space)
                print(f"   ✓ Created space {i+1}: {space['id']}")
        
        assert len(spaces) == 3, f"Only created {len(spaces)}/3 spaces"
        
        try:
            # Test: List and verify
            print(f"\n📤 Listing all spaces...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/spaces/",
                headers=api_session.headers
            )
            
            assert response.status_code == 200
            data = response.json()
            all_spaces = data if isinstance(data, list) else data.get("results", [])
            
            print(f"\n🔍 Verifying all test spaces in list...")
            created_slugs = {s["slug"] for s in spaces}
            listed_slugs = {s["slug"] for s in all_spaces}
            
            assert created_slugs.issubset(listed_slugs), "Not all spaces found"
            print(f"   ✓ All {len(spaces)} test spaces found")
            
            print(f"\n✅ PASS: Bulk operations successful")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up {len(spaces)} spaces...")
            for space in spaces:
                if delete_space(api_session, space["slug"]):
                    print(f"   ✓ Deleted space {space['slug']}")
                    
        print("="*80)
