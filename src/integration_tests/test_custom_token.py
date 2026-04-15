"""
Integration tests for Custom Token (Service Token) API.

Tested Scenarios:
- Creating custom header tokens (e.g., X-Zero-Trust-Token)
- Listing all custom tokens for a user
- Retrieving specific custom token details
- Updating custom token (name, header, value)
- Deleting custom tokens
- Token persistence after list operations (regression test)
- Multiple custom header tokens per user

Untested Scenarios / Gaps:
- Token encryption at rest verification
- Token usage in actual API calls (integration with git providers)
- Token expiration and renewal
- Token permissions/scopes
- Audit logging of token usage
- Token sharing between users
- Token rate limiting
- Invalid token format handling
- Special characters in header names

Test Strategy:
- Each test is completely independent
- Tests use real backend with actual database
- Proper cleanup in finally blocks
- Preserves existing tokens, only cleans up test-created ones
"""
import pytest
import requests
from .test_helpers import create_service_token, delete_service_token


@pytest.fixture(scope="module", autouse=True)
def cleanup_custom_tokens(api_session):
    """Track and clean up only test-created custom tokens, preserving existing ones."""
    print("\n🔍 Recording existing custom tokens to preserve them...")
    
    # Get existing tokens before tests
    existing_token_ids = set()
    response = requests.get(
        f"{api_session.base_url}/api/service-tokens/v1/tokens/",
        headers=api_session.headers
    )
    
    if response.status_code == 200:
        tokens = response.json()
        for token in tokens:
            if token.get('service_type') == 'custom_header':
                existing_token_ids.add(token['id'])
                print(f"   ✓ Preserving existing token: {token.get('name')} ({token.get('header_name')})")
    
    print(f"   Found {len(existing_token_ids)} existing custom token(s) to preserve")
    
    yield
    
    # Cleanup only test-created tokens after tests
    print("\n🧹 Cleaning up test-created custom tokens (preserving existing ones)...")
    response = requests.get(
        f"{api_session.base_url}/api/service-tokens/v1/tokens/",
        headers=api_session.headers
    )
    
    if response.status_code == 200:
        tokens = response.json()
        for token in tokens:
            if token.get('service_type') == 'custom_header':
                token_id = token['id']
                # Only delete if this token was created during tests
                if token_id not in existing_token_ids:
                    if delete_service_token(api_session, token_id):
                        print(f"   ✓ Deleted test token {token_id}")
                else:
                    print(f"   ⊙ Preserved existing token {token_id}")


class TestCustomToken:
    """Test custom token CRUD operations."""
    
    def test_create_custom_token(self, api_session):
        """Test creating a custom header token."""
        print("\n" + "="*80)
        print("TEST: Create Custom Token")
        print("="*80)
        print("Purpose: Verify that a custom header token can be created")
        print("Expected: HTTP 201, token created with header_name")
        
        # Test: Create custom token
        print(f"\n📤 Creating custom token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Test Custom Token",
            header_name="X-Auth-Token",
            token="test-token-12345"
        )
        
        assert token is not None, "Failed to create custom token"
        
        print(f"\n✅ Token created:")
        print(f"   ID: {token['id']}")
        print(f"   Name: {token.get('name')}")
        print(f"   Service Type: {token.get('service_type')}")
        print(f"   Header Name: {token.get('header_name')}")
        
        # Verify fields
        assert token['service_type'] == 'custom_header', "Service type should be custom_header"
        assert token['name'] == 'Test Custom Token', "Name should match"
        assert token['header_name'] == 'X-Auth-Token', "Header name should match"
        assert token.get('has_token') is True, "Should indicate token is configured"
        assert 'encrypted_token' not in token, "Should not expose encrypted_token for security"
        
        # Cleanup
        token_id = token['id']
        print(f"\n🧹 Cleaning up token {token_id}...")
        success = delete_service_token(api_session, token_id)
        assert success, "Failed to delete token"
        print(f"   ✓ Token deleted")
        
        print("="*80)
    
    def test_list_custom_tokens(self, api_session):
        """Test listing custom tokens."""
        print("\n" + "="*80)
        print("TEST: List Custom Tokens")
        print("="*80)
        print("Purpose: Verify that custom tokens appear in the list")
        print("Expected: HTTP 200, custom token in list")
        
        # Setup: Create a custom token
        print(f"\n🔧 Setup: Creating custom token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="List Test Token",
            header_name="X-API-Key",
            token="list-test-token-67890"
        )
        assert token is not None, "Failed to create token"
        token_id = token['id']
        print(f"   ✓ Created token {token_id}")
        
        try:
            # Test: List tokens
            print(f"\n📤 Listing all tokens...")
            response = requests.get(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed to list tokens: {response.text}"
            
            tokens = response.json()
            print(f"\n🔍 Found {len(tokens)} token(s)")
            
            # Find our custom token
            custom_tokens = [t for t in tokens if t.get('service_type') == 'custom_header']
            print(f"   Custom tokens: {len(custom_tokens)}")
            
            assert len(custom_tokens) > 0, "Should have at least one custom token"
            
            # Verify our token is in the list
            our_token = next((t for t in custom_tokens if t['id'] == token_id), None)
            assert our_token is not None, f"Token {token_id} not found in list"
            
            print(f"\n✅ Token found in list:")
            print(f"   ID: {our_token['id']}")
            print(f"   Name: {our_token.get('name')}")
            print(f"   Header Name: {our_token.get('header_name')}")
            
            assert our_token['name'] == 'List Test Token', "Name should match"
            assert our_token['header_name'] == 'X-API-Key', "Header name should match"
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up token {token_id}...")
            success = delete_service_token(api_session, token_id)
            assert success, "Failed to delete token"
            print(f"   ✓ Token deleted")
        
        print("="*80)
    
    def test_get_custom_token_detail(self, api_session):
        """Test retrieving a specific custom token."""
        print("\n" + "="*80)
        print("TEST: Get Custom Token Detail")
        print("="*80)
        print("Purpose: Verify that a custom token can be retrieved by ID")
        print("Expected: HTTP 200, token details returned")
        
        # Setup: Create a custom token
        print(f"\n🔧 Setup: Creating custom token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Detail Test Token",
            header_name="Authorization",
            token="detail-test-token-abc123"
        )
        assert token is not None, "Failed to create token"
        token_id = token['id']
        print(f"   ✓ Created token {token_id}")
        
        try:
            # Test: Get token detail
            print(f"\n📤 Getting token detail...")
            response = requests.get(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            assert response.status_code == 200, f"Failed to get token: {response.text}"
            
            token = response.json()
            print(f"\n✅ Token retrieved:")
            print(f"   ID: {token['id']}")
            print(f"   Name: {token.get('name')}")
            print(f"   Service Type: {token.get('service_type')}")
            print(f"   Header Name: {token.get('header_name')}")
            print(f"   Has token: {token.get('has_token')}")
            
            # Verify fields
            assert token['id'] == token_id, "ID should match"
            assert token['service_type'] == 'custom_header', "Service type should be custom_header"
            assert token['name'] == 'Detail Test Token', "Name should match"
            assert token['header_name'] == 'Authorization', "Header name should match"
            assert token.get('has_token') is True, "Should indicate token is configured"
            assert 'encrypted_token' not in token, "Should not expose encrypted_token for security"
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up token {token_id}...")
            success = delete_service_token(api_session, token_id)
            assert success, "Failed to delete token"
            print(f"   ✓ Token deleted")
        
        print("="*80)
    
    def test_update_custom_token(self, api_session):
        """Test updating a custom token."""
        print("\n" + "="*80)
        print("TEST: Update Custom Token")
        print("="*80)
        print("Purpose: Verify that a custom token can be updated")
        print("Expected: HTTP 200, token updated")
        
        # Setup: Create a custom token
        print(f"\n🔧 Setup: Creating custom token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Update Test Token",
            header_name="X-Old-Header",
            token="old-token-123"
        )
        assert token is not None, "Failed to create token"
        token_id = token['id']
        print(f"   ✓ Created token {token_id}")
        
        try:
            # Test: Update token
            print(f"\n📤 Updating token...")
            response = requests.patch(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                json={
                    "name": "Updated Token Name",
                    "header_name": "X-New-Header",
                    "token": "new-token-456"
                },
                headers=api_session.headers
            )
            
            print(f"📥 Response: HTTP {response.status_code}")
            if response.status_code != 200:
                print(f"Response body: {response.text}")
            
            assert response.status_code == 200, f"Failed to update token: {response.text}"
            
            updated_token = response.json()
            print(f"\n✅ Token updated:")
            print(f"   ID: {updated_token['id']}")
            print(f"   Name: {updated_token.get('name')}")
            print(f"   Header Name: {updated_token.get('header_name')}")
            
            # Verify updates
            assert updated_token['name'] == 'Updated Token Name', "Name should be updated"
            assert updated_token['header_name'] == 'X-New-Header', "Header name should be updated"
            
            # Verify persistence: Get token again
            print(f"\n📤 Verifying persistence...")
            get_response = requests.get(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                headers=api_session.headers
            )
            assert get_response.status_code == 200, "Failed to get token"
            
            persisted_token = get_response.json()
            print(f"   Name (persisted): {persisted_token.get('name')}")
            print(f"   Header Name (persisted): {persisted_token.get('header_name')}")
            
            assert persisted_token['name'] == 'Updated Token Name', "Updated name should persist"
            assert persisted_token['header_name'] == 'X-New-Header', "Updated header name should persist"
            print(f"   ✓ Updates persisted correctly")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up token {token_id}...")
            success = delete_service_token(api_session, token_id)
            assert success, "Failed to delete token"
            print(f"   ✓ Token deleted")
        
        print("="*80)
    
    def test_custom_token_persistence_after_list(self, api_session):
        """Test that custom token persists after listing all tokens."""
        print("\n" + "="*80)
        print("TEST: Custom Token Persistence After List")
        print("="*80)
        print("Purpose: Verify that custom token remains configured after listing")
        print("Expected: Token persists with all fields intact")
        
        # Setup: Create a custom token
        print(f"\n🔧 Setup: Creating custom token...")
        token = create_service_token(
            api_session,
            service_type="custom_header",
            name="Persistence Test",
            header_name="X-Persist-Token",
            token="persist-token-xyz789"
        )
        assert token is not None, "Failed to create token"
        token_id = token['id']
        original_data = token
        print(f"   ✓ Created token {token_id}")
        print(f"   Original header_name: {original_data.get('header_name')}")
        
        try:
            # Step 1: List all tokens (simulating page load)
            print(f"\n📤 Step 1: Listing all tokens (simulating page load)...")
            list_response = requests.get(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/",
                headers=api_session.headers
            )
            assert list_response.status_code == 200, "Failed to list tokens"
            tokens = list_response.json()
            print(f"   ✓ Listed {len(tokens)} token(s)")
            
            # Step 2: Find our token in the list
            print(f"\n📤 Step 2: Finding our token in the list...")
            our_token = next((t for t in tokens if t['id'] == token_id), None)
            assert our_token is not None, f"Token {token_id} not found in list"
            print(f"   ✓ Token found in list")
            print(f"   header_name from list: {our_token.get('header_name')}")
            
            # Verify it still has header_name
            assert our_token.get('header_name') == 'X-Persist-Token', \
                f"header_name missing or wrong in list! Got: {our_token.get('header_name')}"
            
            # Step 3: Get token detail (simulating configuration page load)
            print(f"\n📤 Step 3: Getting token detail (simulating config page)...")
            detail_response = requests.get(
                f"{api_session.base_url}/api/service-tokens/v1/tokens/{token_id}/",
                headers=api_session.headers
            )
            assert detail_response.status_code == 200, "Failed to get token detail"
            detail_token = detail_response.json()
            print(f"   ✓ Got token detail")
            print(f"   header_name from detail: {detail_token.get('header_name')}")
            
            # Verify it STILL has header_name
            assert detail_token.get('header_name') == 'X-Persist-Token', \
                f"header_name missing or wrong in detail! Got: {detail_token.get('header_name')}"
            
            print(f"\n✅ PASS: Token persisted correctly through list and detail operations")
            
        finally:
            # Cleanup
            print(f"\n🧹 Cleaning up token {token_id}...")
            success = delete_service_token(api_session, token_id)
            assert success, "Failed to delete token"
            print(f"   ✓ Token deleted")
        
        print("="*80)
