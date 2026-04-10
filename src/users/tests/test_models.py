"""
Tests for users models.
"""
import pytest
from django.contrib.auth.models import User
from users.models import UserProfile, ApiToken, FavoriteRepository, RecentRepository, RepositoryViewMode, UserRole


@pytest.mark.django_db
class TestUserProfile:
    """Tests for UserProfile model."""
    
    def test_create_user_profile(self):
        """Test creating a user profile."""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        profile = UserProfile.objects.create(
            user=user,
            role='editor'
        )
        
        assert profile.user == user
        assert profile.role == 'editor'
        assert str(profile) == 'testuser - editor'
    
    def test_user_profile_default_role(self):
        """Test default role is viewer."""
        user = User.objects.create_user(username='testuser2')
        profile = UserProfile.objects.create(user=user)
        
        assert profile.role == 'viewer'
    
    def test_user_profile_role_choices(self):
        """Test all role choices are valid."""
        user = User.objects.create_user(username='testuser3')
        
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
    
    def test_create_api_token(self):
        """Test creating an API token."""
        user = User.objects.create_user(username='testuser')
        api_token = ApiToken.objects.create(
            user=user,
            name='Test Token'
        )
        
        assert api_token.user == user
        assert api_token.name == 'Test Token'
        assert len(api_token.token) == 64
        assert api_token.last_used_at is None
    
    def test_api_token_string_representation(self):
        """Test string representation."""
        user = User.objects.create_user(username='testuser')
        api_token = ApiToken.objects.create(
            user=user,
            name='My Token'
        )
        
        assert str(api_token) == 'testuser - My Token'


@pytest.mark.django_db
class TestFavoriteRepository:
    """Tests for FavoriteRepository model."""
    
    def test_create_favorite(self):
        """Test creating a favorite repository."""
        user = User.objects.create_user(username='testuser')
        favorite = FavoriteRepository.objects.create(
            user=user,
            repository_id='facebook/react'
        )
        
        assert favorite.user == user
        assert favorite.repository_id == 'facebook/react'
        assert str(favorite) == 'testuser - facebook/react'
    
    def test_unique_favorite(self):
        """Test that user can't favorite same repo twice."""
        user = User.objects.create_user(username='testuser')
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
    
    def test_create_recent(self):
        """Test creating a recent repository."""
        user = User.objects.create_user(username='testuser')
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
    
    def test_create_view_mode(self):
        """Test creating a repository view mode."""
        user = User.objects.create_user(username='testuser')
        view_mode = RepositoryViewMode.objects.create(
            user=user,
            repository_id='facebook/react',
            view_mode='developer'
        )
        
        assert view_mode.user == user
        assert view_mode.repository_id == 'facebook/react'
        assert view_mode.view_mode == 'developer'
    
    def test_default_view_mode(self):
        """Test default view mode is document."""
        user = User.objects.create_user(username='testuser')
        view_mode = RepositoryViewMode.objects.create(
            user=user,
            repository_id='facebook/react'
        )
        
        assert view_mode.view_mode == 'document'
