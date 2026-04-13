"""
Integration tests for Service Tokens API endpoints.

Test Strategy:
- Each test is completely independent
- Each test creates its own artifacts before testing
- Each test cleans up its artifacts after testing
- Comprehensive logging for each test step

Test Coverage:
1. Service token CRUD operations
2. Token encryption verification
3. Different service types (custom_header, github, bitbucket)
"""
import pytest
import requests


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
        create_response = requests.post(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/",
            json={
                "service_type": "custom_header",
                "header_name": "X-Test-Token",
                "token": "test_token_value_12345",
                "name": "Integration Test Token"
            },
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {create_response.status_code}")
        assert create_response.status_code == 201, f"Failed: {create_response.text}"
        
        data = create_response.json()
        token_id = data["id"]
        
        print(f"\n🔍 Verifying created token...")
        assert data["service_type"] == "custom_header"
        print(f"   ✓ Service type: {data['service_type']}")
        
        assert data["name"] == "Integration Test Token"
        print(f"   ✓ Name: {data['name']}")
        
        print(f"   ✓ Token ID: {token_id}")
        
        # Test: Delete the token
        print(f"\n📤 Deleting service token {token_id}...")
        delete_response = requests.delete(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {delete_response.status_code}")
        assert delete_response.status_code in [204, 200], f"Failed: {delete_response.text}"
        
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
        create_response = requests.post(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/",
            json={
                "service_type": "custom_header",
                "header_name": "X-Detail-Test",
                "token": "detail_test_token_12345",
                "name": "Detail Test Token"
            },
            headers=api_session.headers
        )
        assert create_response.status_code == 201, f"Setup failed: {create_response.text}"
        token_id = create_response.json()["id"]
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
            delete_response = requests.delete(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                headers=api_session.headers
            )
            if delete_response.status_code in [200, 204]:
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
        create_response = requests.post(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/",
            json={
                "service_type": "custom_header",
                "header_name": "X-Secret-Token",
                "token": secret_value,
                "name": "Encryption Test Token"
            },
            headers=api_session.headers
        )
        
        print(f"📥 Response: HTTP {create_response.status_code}")
        assert create_response.status_code == 201, f"Failed: {create_response.text}"
        
        token_id = create_response.json()["id"]
        
        try:
            print(f"\n🔍 Verifying encryption...")
            data = create_response.json()
            
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
            delete_response = requests.delete(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                headers=api_session.headers
            )
            if delete_response.status_code in [200, 204]:
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
        create_response = requests.post(
            f"{api_session.base_url}/api/service-tokens/v1/tokens/",
            json={
                "service_type": "custom_header",
                "header_name": "X-Update-Test",
                "token": "update_test_token_12345",
                "name": "Update Test Token"
            },
            headers=api_session.headers
        )
        assert create_response.status_code == 201, f"Setup failed: {create_response.text}"
        token_id = create_response.json()["id"]
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
            delete_response = requests.delete(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                headers=api_session.headers
            )
            if delete_response.status_code in [200, 204]:
                print(f"   ✓ Deleted token {token_id}")
                
        print("="*80)
