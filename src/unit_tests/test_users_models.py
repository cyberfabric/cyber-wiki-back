"""
Unit tests for user models.

Tested Scenarios:
- UserProfile creation and default role
- UserProfile role choices validation
- ApiToken generation and uniqueness
- ApiToken creation and string representation
- FavoriteRepository creation and uniqueness constraint
- RecentRepository creation with timestamp
- RepositoryViewMode creation and default value

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
from users.models import UserProfile, ApiToken, FavoriteRepository, RecentRepository, RepositoryViewMode, UserRole


@pytest.mark.django_db
class TestUserProfile:
    """Tests for UserProfile model."""
    
    def test_create_user_profile(self, user):
        """Test creating a user profile."""
        profile = UserProfile.objects.create(
            user=user,
            role='editor'
        )
        
        assert profile.user == user
        assert profile.role == 'editor'
        assert str(profile) == 'testuser - editor'
    
    def test_user_profile_default_role(self, user):
        """Test default role is viewer."""
        profile = UserProfile.objects.create(user=user)
        
        assert profile.role == 'viewer'
    
    def test_user_profile_role_choices(self, user):
        """Test all role choices are valid."""
        
        for role, _ in UserRole.choices:
            profile = UserProfile.objects.create(user=user, role=role)
            assert profile.role == role
            profile.delete()


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
    
    def test_default_view_mode(self, user):
        """Test default view mode is document."""
        view_mode = RepositoryViewMode.objects.create(
            user=user,
            repository_id='facebook/react'
        )
        
        assert view_mode.view_mode == 'document'
