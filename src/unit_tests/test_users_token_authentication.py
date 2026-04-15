"""
Unit tests for Bearer token authentication.

Tested Scenarios:
- Successful authentication with valid token
- Authentication updates last_used_at timestamp
- Invalid token raises AuthenticationFailed
- Missing Authorization header returns None
- Non-Bearer authorization returns None
- Malformed Bearer token handling
- authenticate_header returns 'Bearer'

Untested Scenarios / Gaps:
- Token expiration handling
- Concurrent token usage
- Token revocation
- Rate limiting
- Token refresh
- Multiple tokens per user

Test Strategy:
- Database tests with @pytest.mark.django_db
- Test authentication flow
- Test error handling
- Test timestamp updates
- Use mock requests
"""
import pytest
from unittest.mock import Mock
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from users.token_authentication import BearerTokenAuthentication
from users.models import ApiToken


@pytest.mark.django_db
class TestBearerTokenAuthentication:
    """Tests for BearerTokenAuthentication class."""
    
    def test_successful_authentication(self, user):
        """Test successful authentication with valid token."""
        # Create API token
        api_token = ApiToken.objects.create(user=user, name='Test Token')
        
        # Create mock request
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {api_token.token}'}
        
        # Authenticate
        auth = BearerTokenAuthentication()
        result = auth.authenticate(request)
        
        assert result is not None
        authenticated_user, auth_data = result
        assert authenticated_user == user
        assert auth_data is None
    
    def test_authentication_updates_last_used(self, user):
        """Test that authentication updates last_used_at timestamp."""
        # Create API token
        api_token = ApiToken.objects.create(user=user, name='Test Token')
        initial_last_used = api_token.last_used_at
        
        # Create mock request
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {api_token.token}'}
        
        # Authenticate
        auth = BearerTokenAuthentication()
        auth.authenticate(request)
        
        # Refresh from database
        api_token.refresh_from_db()
        
        # last_used_at should be updated
        assert api_token.last_used_at is not None
        if initial_last_used:
            assert api_token.last_used_at > initial_last_used
    
    def test_invalid_token_raises_error(self):
        """Test that invalid token raises AuthenticationFailed."""
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': 'Bearer invalid_token_12345'}
        
        auth = BearerTokenAuthentication()
        
        with pytest.raises(AuthenticationFailed, match='Invalid token'):
            auth.authenticate(request)
    
    def test_missing_authorization_header_returns_none(self):
        """Test that missing Authorization header returns None."""
        request = Mock()
        request.META = {}
        
        auth = BearerTokenAuthentication()
        result = auth.authenticate(request)
        
        assert result is None
    
    def test_non_bearer_authorization_returns_none(self):
        """Test that non-Bearer authorization returns None."""
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': 'Basic dXNlcjpwYXNz'}
        
        auth = BearerTokenAuthentication()
        result = auth.authenticate(request)
        
        assert result is None
    
    def test_bearer_without_space_returns_none(self):
        """Test that 'Bearer' without space returns None (not recognized)."""
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': 'Bearer'}
        
        auth = BearerTokenAuthentication()
        
        # 'Bearer' without space doesn't match 'Bearer ' pattern, returns None
        result = auth.authenticate(request)
        assert result is None
    
    def test_bearer_with_empty_token(self):
        """Test that Bearer with empty token raises error."""
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': 'Bearer '}
        
        auth = BearerTokenAuthentication()
        
        with pytest.raises(AuthenticationFailed):
            auth.authenticate(request)
    
    def test_authenticate_header(self):
        """Test that authenticate_header returns 'Bearer'."""
        request = Mock()
        auth = BearerTokenAuthentication()
        
        header = auth.authenticate_header(request)
        
        assert header == 'Bearer'
    
    def test_case_sensitive_bearer(self):
        """Test that 'bearer' (lowercase) is not recognized."""
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': 'bearer token123'}
        
        auth = BearerTokenAuthentication()
        result = auth.authenticate(request)
        
        # Should return None (not recognized as Bearer)
        assert result is None
    
    def test_multiple_authentications_same_token(self, user):
        """Test multiple authentications with same token."""
        api_token = ApiToken.objects.create(user=user, name='Test Token')
        
        request = Mock()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {api_token.token}'}
        
        auth = BearerTokenAuthentication()
        
        # First authentication
        result1 = auth.authenticate(request)
        assert result1[0] == user
        
        # Second authentication should also work
        result2 = auth.authenticate(request)
        assert result2[0] == user
    
    def test_authentication_with_different_users(self, user, another_user):
        """Test authentication with tokens from different users."""
        token1 = ApiToken.objects.create(user=user, name='User 1 Token')
        token2 = ApiToken.objects.create(user=another_user, name='User 2 Token')
        
        auth = BearerTokenAuthentication()
        
        # Authenticate with first token
        request1 = Mock()
        request1.META = {'HTTP_AUTHORIZATION': f'Bearer {token1.token}'}
        result1 = auth.authenticate(request1)
        assert result1[0] == user
        
        # Authenticate with second token
        request2 = Mock()
        request2.META = {'HTTP_AUTHORIZATION': f'Bearer {token2.token}'}
        result2 = auth.authenticate(request2)
        assert result2[0] == another_user
