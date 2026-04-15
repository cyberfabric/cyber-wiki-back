"""
Unit tests for user models.

Tested Scenarios:
- UserProfile creation and default role
- UserProfile role choices validation
- ApiToken generation and uniqueness
- ApiToken creation and string representation
- FavoriteRepository creation and uniqueness constraint
- FavoriteRepository string representation
- RecentRepository creation with timestamp
- RecentRepository string representation
- RepositoryViewMode creation and default value
- RepositoryViewMode string representation
- RepositorySettings string representation
- APIResponseCache string representation

Untested Scenarios / Gaps:
- UserProfile update operations
- ApiToken expiration and renewal
- ApiToken last_used_at updates
- FavoriteRepository ordering and limits
- RecentRepository cleanup of old entries
- RepositoryViewMode updates and history
- Cascade deletion behavior
- Model validation edge cases
- Concurrent creation conflicts

Test Strategy:
- Model tests with database using @pytest.mark.django_db
- Test model creation, defaults, and constraints
- Use shared fixtures from conftest.py
- Verify string representations and relationships
"""
import pytest
from users.models import (
    UserProfile, ApiToken, FavoriteRepository, RecentRepository, 
    RepositoryViewMode, RepositorySettings, APIResponseCache, UserRole
)


@pytest.mark.django_db
class TestUserProfile:
    """Tests for UserProfile model."""
    
    def test_create_user_profile(self, user):
        """Test user profile exists and can be updated."""
        # Profile already exists from signal
        profile = user.userprofile
        profile.role = 'editor'
        profile.save()
        
        assert profile.user == user
        assert profile.role == 'editor'
        assert str(profile) == 'testuser - editor'
    
    def test_user_profile_default_role(self, user):
        """Test default role is viewer."""
        # Profile already exists from signal, just get it
        profile = user.userprofile
        
        assert profile.role == 'viewer'
    
    def test_user_profile_role_choices(self):
        """Test all role choices are valid."""
        from django.contrib.auth.models import User
        
        for role, _ in UserRole.choices:
            # Create a unique user for each role test
            test_user = User.objects.create_user(
                username=f'test_{role}',
                password='testpass',
                email=f'test_{role}@test.com'
            )
            # Delete auto-created profile if exists
            UserProfile.objects.filter(user=test_user).delete()
            # Create profile with specific role
            profile = UserProfile.objects.create(user=test_user, role=role)
            assert profile.role == role
            # Cleanup
            test_user.delete()


@pytest.mark.django_db
class TestApiToken:
    """Tests for ApiToken model."""
    
    def test_generate_token(self):
        """Test token generation."""
        token = ApiToken.generate_token()
        
        assert len(token) == 64
        assert isinstance(token, str)
        
        # Test uniqueness
        token2 = ApiToken.generate_token()
        assert token != token2
    
    def test_create_api_token(self, user):
        """Test creating an API token."""
        api_token = ApiToken.objects.create(
            user=user,
            name='Test Token'
        )
        
        assert api_token.user == user
        assert api_token.name == 'Test Token'
        assert len(api_token.token) == 64
        assert api_token.last_used_at is None
    
    def test_api_token_string_representation(self, user):
        """Test string representation."""
        api_token = ApiToken.objects.create(
            user=user,
            name='My Token'
        )
        
        assert str(api_token) == 'testuser - My Token'


@pytest.mark.django_db
class TestFavoriteRepository:
    """Tests for FavoriteRepository model."""
    
    def test_create_favorite(self, user):
        """Test creating a favorite repository."""
        favorite = FavoriteRepository.objects.create(
            user=user,
            repository_id='facebook/react'
        )
        
        assert favorite.user == user
        assert favorite.repository_id == 'facebook/react'
        assert str(favorite) == 'testuser - facebook/react'
    
    def test_unique_favorite(self, user):
        """Test that user can't favorite same repo twice."""
        FavoriteRepository.objects.create(
            user=user,
            repository_id='facebook/react'
        )
        
        # Attempting to create duplicate should raise error
        with pytest.raises(Exception):
            FavoriteRepository.objects.create(
                user=user,
                repository_id='facebook/react'
            )


@pytest.mark.django_db
class TestRecentRepository:
    """Tests for RecentRepository model."""
    
    def test_create_recent(self, user):
        """Test creating a recent repository."""
        recent = RecentRepository.objects.create(
            user=user,
            repository_id='facebook/react'
        )
        
        assert recent.user == user
        assert recent.repository_id == 'facebook/react'
        assert recent.last_viewed_at is not None
        assert str(recent) == 'testuser - facebook/react'


@pytest.mark.django_db
class TestRepositoryViewMode:
    """Tests for RepositoryViewMode model."""
    
    def test_create_view_mode(self, user):
        """Test creating a repository view mode."""
        view_mode = RepositoryViewMode.objects.create(
            user=user,
            repository_id='facebook/react',
            view_mode='developer'
        )
        
        assert view_mode.user == user
        assert view_mode.repository_id == 'facebook/react'
        assert view_mode.view_mode == 'developer'
        assert str(view_mode) == 'testuser - facebook/react - developer'
    
    def test_default_view_mode(self, user):
        """Test default view mode is document."""
        view_mode = RepositoryViewMode.objects.create(
            user=user,
            repository_id='facebook/react'
        )
        
        assert view_mode.view_mode == 'document'


@pytest.mark.django_db
class TestRepositorySettings:
    """Tests for RepositorySettings model."""
    
    def test_repository_settings_string_representation(self, user):
        """Test string representation of repository settings."""
        repo_settings = RepositorySettings.objects.create(
            user=user,
            repository_id='facebook/react',
            provider='github',
            base_url='https://github.com',
            settings={'document_index_enabled': True}
        )
        
        assert str(repo_settings) == 'testuser - facebook/react'


@pytest.mark.django_db
class TestAPIResponseCache:
    """Tests for APIResponseCache model."""
    
    def test_api_response_cache_string_representation(self, user):
        """Test string representation of API response cache."""
        cache_entry = APIResponseCache.objects.create(
            user=user,
            provider_type='github',
            provider_id='github.com',
            endpoint='/repos',
            method='GET',
            params_hash='1234567890abcdef',
            params_json={},
            response_data={'repos': []},
            status_code=200
        )
        
        assert str(cache_entry) == 'github:/repos (12345678)'
