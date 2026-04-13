"""
Integration tests for Authentication and User Management API endpoints.

Test Strategy:
- Each test is completely independent
- Each test creates its own artifacts before testing
- Each test cleans up its artifacts after testing
- Comprehensive logging for each test step

Test Coverage:
1. Authentication (login, logout, me endpoint, token auth)
2. User profile management
3. API token management
"""
import pytest
import requests


# ============================================================================
# Test Class: Authentication
# ============================================================================

class TestAuthentication:
    """Test authentication endpoints. Each test is independent."""

    def test_login_success(self, base_url):
        """Test successful login with valid credentials."""
        print("\n" + "="*80)
        print("TEST: Login with Valid Credentials")
        print("="*80)
        print("Purpose: Verify successful login returns user data")
        print("Expected: HTTP 200, user object with username")
        
        print(f"\n📤 Sending POST to /api/auth/v1/login")
        response = requests.post(
            f"{base_url}/api/auth/v1/login",
            json={
                "username": "admin",
                "password": "admin"
            }
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"\n🔍 Verifying response...")
        assert "user" in data
        print(f"   ✓ Contains 'user' field")
        
        assert data["user"]["username"] == "admin"
        print(f"   ✓ Username: {data['user']['username']}")
        
        print(f"\n✅ PASS: Login successful")
        print("="*80)

    def test_login_invalid_credentials(self, base_url):
        """Test login with invalid credentials."""
        print("\n" + "="*80)
        print("TEST: Login with Invalid Credentials")
        print("="*80)
        print("Purpose: Verify login fails with wrong password")
        print("Expected: HTTP 400/401")
        
        print(f"\n📤 Sending POST with wrong password")
        response = requests.post(
            f"{base_url}/api/auth/v1/login",
            json={
                "username": "admin",
                "password": "wrongpassword"
            }
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code in [400, 401], f"Unexpected status: {response.status_code}"
        
        print(f"\n✅ PASS: Invalid credentials rejected")
        print("="*80)

    def test_bearer_token_authentication(self, api_session):
        """Test Bearer token authentication works."""
        print("\n" + "="*80)
        print("TEST: Bearer Token Authentication")
        print("="*80)
        print("Purpose: Verify API token from .env works for authentication")
        print("Expected: HTTP 200, authenticated user data")
        
        print(f"\n📤 Sending GET to /api/user_management/v1/profile")
        print(f"   Using Bearer token from .env")
        response = requests.get(
            f"{api_session.base_url}/api/user_management/v1/profile",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"\n🔍 Verifying response...")
        assert "username" in data
        print(f"   ✓ Authenticated as: {data['username']}")
        
        print(f"\n✅ PASS: Bearer token authentication successful")
        print("="*80)

    def test_invalid_bearer_token(self, base_url):
        """Test authentication with invalid token."""
        print("\n" + "="*80)
        print("TEST: Invalid Bearer Token")
        print("="*80)
        print("Purpose: Verify invalid tokens are rejected")
        print("Expected: HTTP 401")
        
        print(f"\n📤 Sending GET with invalid token")
        response = requests.get(
            f"{base_url}/api/user_management/v1/profile",
            headers={"Authorization": "Bearer invalid-token-12345"}
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 401, f"Should reject invalid token"
        
        print(f"\n✅ PASS: Invalid token rejected")
        print("="*80)

    def test_missing_authorization_header(self, base_url):
        """Test request without authorization header."""
        print("\n" + "="*80)
        print("TEST: Missing Authorization Header")
        print("="*80)
        print("Purpose: Verify protected endpoints require authentication")
        print("Expected: HTTP 401")
        
        print(f"\n📤 Sending GET without Authorization header")
        response = requests.get(f"{base_url}/api/user_management/v1/profile")
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 401, f"Should require authentication"
        
        print(f"\n✅ PASS: Missing auth header rejected")
        print("="*80)

    def test_me_endpoint(self, api_session):
        """Test /me endpoint returns current user."""
        print("\n" + "="*80)
        print("TEST: Get Current User (/me endpoint)")
        print("="*80)
        print("Purpose: Verify /me endpoint returns authenticated user")
        print("Expected: HTTP 200, user data")
        
        print(f"\n📤 Sending GET to /api/auth/v1/me")
        response = requests.get(
            f"{api_session.base_url}/api/auth/v1/me",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"\n🔍 Verifying response...")
        assert "username" in data
        print(f"   ✓ Username: {data['username']}")
        
        print(f"\n✅ PASS: /me endpoint successful")
        print("="*80)


# ============================================================================
# Test Class: User Profile
# ============================================================================

class TestUserProfile:
    """Test user profile endpoints. Each test is independent."""

    def test_get_profile(self, api_session):
        """Test getting user profile."""
        print("\n" + "="*80)
        print("TEST: Get User Profile")
        print("="*80)
        print("Purpose: Verify profile endpoint returns user data")
        print("Expected: HTTP 200, profile with username and email")
        
        print(f"\n📤 Sending GET to /api/user_management/v1/profile")
        response = requests.get(
            f"{api_session.base_url}/api/user_management/v1/profile",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"\n🔍 Verifying response...")
        assert "username" in data
        print(f"   ✓ Username: {data['username']}")
        
        assert "email" in data
        print(f"   ✓ Email: {data.get('email', 'N/A')}")
        
        print(f"\n✅ PASS: Profile retrieved successfully")
        print("="*80)

    def test_update_profile(self, api_session):
        """Test updating user profile settings."""
        print("\n" + "="*80)
        print("TEST: Update User Profile Settings")
        print("="*80)
        print("Purpose: Verify profile settings can be updated")
        print("Expected: HTTP 200, settings updated")
        print("Note: email, username are read-only; only 'settings' and 'role' are editable")
        
        # Get current profile
        print(f"\n🔧 Setup: Getting current profile...")
        response = requests.get(
            f"{api_session.base_url}/api/user_management/v1/profile",
            headers=api_session.headers
        )
        original_settings = response.json().get("settings", {})
        print(f"   ✓ Current settings: {original_settings}")
        
        try:
            # Update settings
            new_settings = {"theme": "dark", "test_key": "test_value"}
            print(f"\n📤 Updating settings...")
            print(f"   New settings: {new_settings}")
            response = requests.put(
                f"{api_session.base_url}/api/user_management/v1/profile",
                json={"settings": new_settings},
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            print(f"\n🔍 Verifying update...")
            assert data.get("settings") == new_settings
            print(f"   ✓ Settings updated: {data['settings']}")
            
            print(f"\n✅ PASS: Profile settings updated successfully")
            
        finally:
            # Restore original settings
            print(f"\n🧹 Restoring original settings...")
            requests.put(
                f"{api_session.base_url}/api/user_management/v1/profile",
                json={"settings": original_settings},
                headers=api_session.headers
            )
            print(f"   ✓ Settings restored")
                
        print("="*80)


# ============================================================================
# Test Class: API Token Management
# ============================================================================

class TestApiTokenManagement:
    """Test API token management endpoints. Each test is independent."""

    def test_create_api_token(self, api_session):
        """Test creating a new API token."""
        print("\n" + "="*80)
        print("TEST: Create API Token")
        print("="*80)
        print("Purpose: Verify new API tokens can be created")
        print("Expected: HTTP 201, token data with 64-char token")
        
        print(f"\n📤 Creating token: 'Integration Test Token'")
        response = requests.post(
            f"{api_session.base_url}/api/user_management/v1/tokens",
            json={"name": "Integration Test Token"},
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 201, f"Failed: {response.text}"
        
        data = response.json()
        token_id = data.get("id")
        
        try:
            print(f"\n🔍 Verifying response...")
            assert "token" in data
            print(f"   ✓ Token generated")
            
            assert data["name"] == "Integration Test Token"
            print(f"   ✓ Name: {data['name']}")
            
            assert len(data["token"]) == 64
            print(f"   ✓ Token length: {len(data['token'])} chars")
            
            print(f"\n✅ PASS: API token created successfully")
            
        finally:
            # Cleanup
            if token_id:
                print(f"\n🧹 Cleaning up...")
                delete_response = requests.delete(
                    f"{api_session.base_url}/api/user_management/v1/tokens/{token_id}",
                    headers=api_session.headers
                )
                if delete_response.status_code in [200, 204]:
                    print(f"   ✓ Deleted token {token_id}")
                    
        print("="*80)

    def test_list_api_tokens(self, api_session):
        """Test listing user's API tokens."""
        print("\n" + "="*80)
        print("TEST: List API Tokens")
        print("="*80)
        print("Purpose: Verify API tokens can be listed")
        print("Expected: HTTP 200, list of tokens")
        
        print(f"\n📤 Sending GET to /api/user_management/v1/tokens")
        response = requests.get(
            f"{api_session.base_url}/api/user_management/v1/tokens",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        print(f"\n🔍 Analyzing response...")
        
        # Handle both paginated and non-paginated responses
        if isinstance(data, list):
            tokens = data
        else:
            tokens = data.get("results", [])
        
        print(f"   ✓ Found {len(tokens)} API token(s)")
        
        print(f"\n✅ PASS: Tokens listed successfully")
        print("="*80)

    def test_delete_api_token(self, api_session):
        """Test deleting an API token."""
        print("\n" + "="*80)
        print("TEST: Delete API Token")
        print("="*80)
        print("Purpose: Verify API tokens can be deleted")
        print("Expected: HTTP 200/204")
        
        # Setup: Create a token to delete
        print(f"\n🔧 Setup: Creating token to delete...")
        create_response = requests.post(
            f"{api_session.base_url}/api/user_management/v1/tokens",
            json={"name": "Token to Delete"},
            headers=api_session.headers
        )
        assert create_response.status_code == 201, f"Setup failed: {create_response.text}"
        token_id = create_response.json()["id"]
        print(f"   ✓ Created token {token_id}")
        
        # Test: Delete it
        print(f"\n📤 Deleting token {token_id}...")
        response = requests.delete(
            f"{api_session.base_url}/api/user_management/v1/tokens/{token_id}",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code in [204, 200], f"Failed: {response.text}"
        
        print(f"\n✅ PASS: Token deleted successfully")
        print("="*80)

    def test_configured_token_works(self, api_session):
        """Test that the configured API token from .env works."""
        print("\n" + "="*80)
        print("TEST: Configured API Token Works")
        print("="*80)
        print("Purpose: Verify the API token from .env is valid")
        print("Expected: HTTP 200, successful authentication")
        
        print(f"\n📤 Testing token from .env...")
        response = requests.get(
            f"{api_session.base_url}/api/user_management/v1/profile",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {response.status_code}")
        assert response.status_code == 200, f"Token invalid: {response.text}"
        
        print(f"   ✓ Token is valid")
        
        print(f"\n✅ PASS: Configured API token works")
        print("="*80)
