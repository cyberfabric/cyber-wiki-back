"""
Integration tests for User Preferences API.

Tested Scenarios:
- Adding spaces to favorites
- Listing favorite spaces
- Removing spaces from favorites
- Tracking recently visited spaces
- Listing recent spaces
- Automatic recent space tracking on visit

Untested Scenarios / Gaps:
- Favorite ordering/sorting
- Favorite limits (max number of favorites)
- Recent spaces limit (max number tracked)
- Recent spaces ordering by visit time
- Favorite folders/collections
- Sharing favorites between users
- Exporting/importing favorites
- Favorite notifications
- User preferences for UI settings
- Theme preferences
- Language preferences
- Notification preferences
- Display preferences (view modes, layouts)
- Keyboard shortcuts preferences

Test Strategy:
- Each test is completely independent
- Tests use real backend with actual database
- Proper cleanup in finally blocks
- Comprehensive logging for debugging
"""
import pytest
import requests

from .test_helpers import (
    create_space,
    delete_space,
    cleanup_all_test_spaces,
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
# Test Class: Favorites
# ============================================================================

class TestFavorites:
    """Test favorites functionality. Each test is independent."""

    def test_add_space_to_favorites(self, api_session):
        """Test adding a space to favorites."""
        print("\n" + "="*80)
        print("TEST: Add Space to Favorites")
        print("="*80)
        print("Purpose: Verify that a space can be added to favorites")
        print("Expected: HTTP 200/201")
        
        # Setup: Create a space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_favorite")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Test: Add to favorites
            print(f"\n📤 Adding space to favorites...")
            response = requests.post(
                f"{api_session.base_url}/api/user_management/v1/favorites",
                json={"repository_id": f"space_{space_slug}"},
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            
            assert response.status_code in [200, 201], f"Failed to add favorite: {response.text}"
            print(f"\n✅ PASS: Space added to favorites")
                
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)

    def test_list_favorites(self, api_session):
        """Test listing user favorites."""
        print("\n" + "="*80)
        print("TEST: List Favorites")
        print("="*80)
        print("Purpose: Verify that favorites can be listed")
        print("Expected: HTTP 200, list of favorites")
        
        # Setup: Create a space and add to favorites
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_fav_list")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Add to favorites first
            print(f"\n🔧 Adding space to favorites...")
            add_response = requests.post(
                f"{api_session.base_url}/api/user_management/v1/favorites",
                json={"repository_id": f"space_{space_slug}"},
                headers=api_session.headers
            )
            assert add_response.status_code in [200, 201], f"Failed to add favorite: {add_response.text}"
            
            # Test: List favorites
            print(f"\n📤 Listing favorites...")
            response = requests.get(
                f"{api_session.base_url}/api/user_management/v1/favorites",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed to list favorites: {response.text}"
            
            data = response.json()
            favorites = data if isinstance(data, list) else data.get("results", [])
            print(f"\n🔍 Found {len(favorites)} favorite(s)")
            print(f"\n✅ PASS: Favorites listed successfully")
                
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)

    def test_remove_space_from_favorites(self, api_session):
        """Test removing a space from favorites."""
        print("\n" + "="*80)
        print("TEST: Remove Space from Favorites")
        print("="*80)
        print("Purpose: Verify that a space can be removed from favorites")
        print("Expected: HTTP 200/204")
        
        # Setup: Create a space and add to favorites
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_fav_remove")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Add to favorites first
            print(f"\n🔧 Adding space to favorites...")
            add_response = requests.post(
                f"{api_session.base_url}/api/user_management/v1/favorites",
                json={"repository_id": f"space_{space_slug}"},
                headers=api_session.headers
            )
            assert add_response.status_code in [200, 201], f"Failed to add favorite: {add_response.text}"
            favorite_id = add_response.json()["id"]
            
            # Test: Remove from favorites
            print(f"\n📤 Removing space from favorites...")
            response = requests.delete(
                f"{api_session.base_url}/api/user_management/v1/favorites/{favorite_id}",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code in [200, 204], f"Failed to remove favorite: {response.text}"
            print(f"\n✅ PASS: Space removed from favorites")
                
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)


# ============================================================================
# Test Class: Recent Spaces
# ============================================================================

class TestRecentSpaces:
    """Test recent spaces functionality. Each test is independent."""

    def test_visit_space_adds_to_recent(self, api_session):
        """Test that visiting a space adds it to recent list."""
        print("\n" + "="*80)
        print("TEST: Visit Space Adds to Recent")
        print("="*80)
        print("Purpose: Verify that visiting a space tracks it as recent")
        print("Expected: Space appears in recent list")
        
        # Setup: Create a space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_recent")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Test: Mark space as visited
            print(f"\n📤 Marking space as visited...")
            response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/preferences/visited/{space_slug}/",
                headers=api_session.headers
            )
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed to mark visited: {response.text}"
            print(f"   ✓ Space marked as visited")
            
            # Check recent list
            print(f"\n📤 Checking recent spaces...")
            recent_response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/preferences/recent/",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {recent_response.status_code}")
            assert recent_response.status_code == 200, f"Failed to get recent: {recent_response.text}"
            
            data = recent_response.json()
            recent = data if isinstance(data, list) else data.get("results", [])
            print(f"\n🔍 Found {len(recent)} recent space(s)")
            
            # Verify our space is in the recent list
            space_slugs = [r.get('space_slug') for r in recent]
            assert space_slug in space_slugs, f"Space {space_slug} not found in recent list. Found: {space_slugs}"
            print(f"   ✓ Space {space_slug} found in recent list")
            print(f"✅ PASS: Recent tracking working correctly")
                
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)

    def test_list_recent_spaces(self, api_session):
        """Test listing recently visited spaces."""
        print("\n" + "="*80)
        print("TEST: List Recent Spaces")
        print("="*80)
        print("Purpose: Verify that recent spaces can be listed")
        print("Expected: HTTP 200, list of recent spaces")
        
        # Setup: Create and visit a space
        print(f"\n🔧 Setup: Creating test space...")
        space = create_space(api_session, name_suffix="_recent_list")
        assert space is not None, "Failed to create test space"
        space_slug = space["slug"]
        print(f"   ✓ Created space {space_slug}")
        
        try:
            # Mark space as visited to add to recent
            print(f"\n🔧 Marking space as visited...")
            visit_response = requests.post(
                f"{api_session.base_url}/api/wiki/v1/preferences/visited/{space_slug}/",
                headers=api_session.headers
            )
            assert visit_response.status_code == 200, f"Failed to mark visited: {visit_response.text}"
            print(f"   ✓ Space marked as visited")
            
            # Test: List recent spaces
            print(f"\n📤 Listing recent spaces...")
            response = requests.get(
                f"{api_session.base_url}/api/wiki/v1/preferences/recent/",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed to list recent: {response.text}"
            
            data = response.json()
            recent = data if isinstance(data, list) else data.get("results", [])
            print(f"\n🔍 Found {len(recent)} recent space(s)")
            
            # Verify our space is in the list
            space_slugs = [r.get('space_slug') for r in recent]
            assert space_slug in space_slugs, f"Space {space_slug} not found in recent list. Found: {space_slugs}"
            print(f"   ✓ Space {space_slug} found in recent list")
            print(f"\n✅ PASS: Recent spaces listed successfully")
                
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_space(api_session, space_slug):
                print(f"   ✓ Deleted space {space_slug}")
                
        print("="*80)
