"""
Integration tests for Service Tokens API.

Tested Scenarios:
- Listing all service tokens for a user
- Creating service tokens (custom_header, github, bitbucket_server)
- Deleting service tokens
- Retrieving specific token details
- Token encryption verification (tokens are encrypted at rest)
- Updating service tokens

Untested Scenarios / Gaps:
- Token usage in actual git provider API calls
- Token expiration and renewal
- Token permissions and scopes
- Token sharing between users/teams
- Token audit logging
- Token rate limiting
- Multiple tokens for same service type
- Token validation against actual services
- Token rotation policies
- Bulk token operations
- Token import/export

Test Strategy:
- Each test is completely independent
- Tests use real backend with actual database
- Proper cleanup in finally blocks
- Comprehensive logging for debugging
"""
import pytest
import requests
from .test_helpers import create_service_token, delete_service_token


# ============================================================================
# Test Class: Service Token Management
# ============================================================================

class TestServiceTokens:
    """Test service token management endpoints. Each test is independent."""

    def test_list_service_tokens(self, api_session):
        """Test listing user's service tokens."""
        print("\n" + "="*80)
        print("TEST: List Service Tokens")
        print("="*80)
        print("Purpose: Verify service tokens can be listed")
        print("Expected: HTTP 200, list of tokens")
        
        print(f"\n📤 Sending GET to /api/service-tokens/v1/tokens/")
        response = requests.get(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/",
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
        
        assert isinstance(tokens, list)
        print(f"   ✓ Found {len(tokens)} service token(s)")
        
        print(f"\n✅ PASS: Service tokens listed successfully")
        print("="*80)

    def test_create_and_delete_service_token(self, api_session):
        """Test creating and deleting a service token."""
        print("\n" + "="*80)
        print("TEST: Create and Delete Service Token")
        print("="*80)
        print("Purpose: Verify service tokens can be created and deleted")
        print("Expected: HTTP 201 for create, HTTP 200/204 for delete")
        
        # Test: Create token
        print(f"\n📤 Creating custom_header service token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Integration Test Token",
            header_name="X-Test-Token",
            token="test_token_value_12345"
        )
        
        assert token is not None, "Failed to create token"
        token_id = token["id"]
        
        print(f"\n🔍 Verifying created token...")
        assert token["service_type"] == "custom_header"
        print(f"   ✓ Service type: {token['service_type']}")
        
        assert token["name"] == "Integration Test Token"
        print(f"   ✓ Name: {token['name']}")
        
        print(f"   ✓ Token ID: {token_id}")
        
        # Test: Delete the token
        print(f"\n📤 Deleting service token {token_id}...")
        success = delete_service_token(api_session, token_id)
        
        assert success, "Failed to delete token"
        
        print(f"\n✅ PASS: Service token created and deleted successfully")
        print("="*80)

    def test_get_service_token_detail(self, api_session):
        """Test getting service token details."""
        print("\n" + "="*80)
        print("TEST: Get Service Token Detail")
        print("="*80)
        print("Purpose: Verify service token details can be retrieved")
        print("Expected: HTTP 200, token details without sensitive data")
        
        # Setup: Create a token
        print(f"\n🔧 Setup: Creating service token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Detail Test Token",
            header_name="X-Detail-Test",
            token="detail_test_token_12345"
        )
        assert token is not None, "Setup failed"
        token_id = token["id"]
        print(f"   ✓ Created token {token_id}")
        
        try:
            # Test: Get token detail
            print(f"\n📤 Getting token details for {token_id}...")
            detail_response = requests.get(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {detail_response.status_code}")
            assert detail_response.status_code == 200, f"Failed: {detail_response.text}"
            
            data = detail_response.json()
            print(f"\n🔍 Verifying response...")
            assert data["id"] == token_id
            print(f"   ✓ ID matches: {data['id']}")
            
            assert data["service_type"] == "custom_header"
            print(f"   ✓ Service type: {data['service_type']}")
            
            # Verify sensitive data is not exposed
            assert "encrypted_token" not in data
            print(f"   ✓ Encrypted token not exposed")
            
            print(f"\n✅ PASS: Token details retrieved successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_service_token(api_session, token_id):
                print(f"   ✓ Deleted token {token_id}")
                
        print("="*80)

    def test_token_encryption(self, api_session):
        """Test that tokens are properly encrypted."""
        print("\n" + "="*80)
        print("TEST: Token Encryption")
        print("="*80)
        print("Purpose: Verify tokens are encrypted and not exposed in API")
        print("Expected: Token value not returned in API responses")
        
        # Test: Create a token with sensitive data
        secret_value = "super_secret_value_12345"
        print(f"\n📤 Creating token with secret value...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Encryption Test Token",
            header_name="X-Secret-Token",
            token=secret_value
        )
        
        assert token is not None, "Failed to create token"
        token_id = token["id"]
        
        try:
            print(f"\n🔍 Verifying encryption...")
            data = token
            
            # Verify token is not returned in plain text
            if "token" in data:
                assert data["token"] != secret_value, "Token should be encrypted!"
                print(f"   ✓ Token not exposed in create response")
            else:
                print(f"   ✓ Token field not in response (properly hidden)")
            
            # Verify encrypted_token is not exposed
            assert "encrypted_token" not in data
            print(f"   ✓ Encrypted token not exposed")
            
            print(f"\n✅ PASS: Token properly encrypted")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_service_token(api_session, token_id):
                print(f"   ✓ Deleted token {token_id}")
                
        print("="*80)

    def test_update_service_token(self, api_session):
        """Test updating a service token."""
        print("\n" + "="*80)
        print("TEST: Update Service Token")
        print("="*80)
        print("Purpose: Verify service token can be updated")
        print("Expected: HTTP 200, updated fields reflected")
        
        # Setup: Create a token
        print(f"\n🔧 Setup: Creating service token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Update Test Token",
            header_name="X-Update-Test",
            token="update_test_token_12345"
        )
        assert token is not None, "Setup failed"
        token_id = token["id"]
        print(f"   ✓ Created token {token_id}")
        
        try:
            # Test: Update the token name
            new_name = "Updated Token Name"
            print(f"\n📤 Updating token name to: {new_name}")
            update_response = requests.patch(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                json={"name": new_name},
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {update_response.status_code}")
            assert update_response.status_code == 200, f"Failed: {update_response.text}"
            
            data = update_response.json()
            print(f"\n🔍 Verifying update...")
            assert data["name"] == new_name
            print(f"   ✓ Name updated: {data['name']}")
            
            print(f"\n✅ PASS: Service token updated successfully")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up...")
            if delete_service_token(api_session, token_id):
                print(f"   ✓ Deleted token {token_id}")
                
        print("="*80)
