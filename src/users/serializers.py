"""
Serializers for user management and authentication.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, ApiToken, FavoriteRepository, RecentRepository, RepositoryViewMode, RepositorySettings


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile with user details.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'email', 'role', 'sso_provider', 
            'last_sso_login', 'settings', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'username', 'email', 'sso_provider', 'last_sso_login', 'created_at', 'updated_at']


class ApiTokenSerializer(serializers.ModelSerializer):
    """
    Serializer for API tokens.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ApiToken
        fields = ['id', 'username', 'name', 'token', 'last_used_at', 'created_at']
        read_only_fields = ['id', 'username', 'token', 'last_used_at', 'created_at']
    
    def create(self, validated_data):
        """Generate token on creation."""
        validated_data['token'] = ApiToken.generate_token()
        return super().create(validated_data)


class ApiTokenCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating API tokens."""
    
    class Meta:
        model = ApiToken
        fields = ['name']


class FavoriteRepositorySerializer(serializers.ModelSerializer):
    """Serializer for favorite repositories."""
    
    class Meta:
        model = FavoriteRepository
        fields = ['id', 'repository_id', 'created_at']
        read_only_fields = ['id', 'created_at']


class RecentRepositorySerializer(serializers.ModelSerializer):
    """Serializer for recent repositories."""
    
    class Meta:
        model = RecentRepository
        fields = ['id', 'repository_id', 'last_viewed_at', 'created_at']
        read_only_fields = ['id', 'last_viewed_at', 'created_at']


class RepositoryViewModeSerializer(serializers.ModelSerializer):
    """Serializer for repository view mode preferences."""
    
    class Meta:
        model = RepositoryViewMode
        fields = ['id', 'repository_id', 'view_mode', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class LoginSerializer(serializers.Serializer):
    """Serializer for login requests."""
    username = serializers.CharField(help_text='Username')
    password = serializers.CharField(help_text='Password', write_only=True)


class UserInfoSerializer(serializers.ModelSerializer):
    """Serializer for current user information."""
    role = serializers.CharField(source='userprofile.role', read_only=True)
    settings = serializers.JSONField(source='userprofile.settings', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'settings']
        read_only_fields = ['id', 'username']


class RepositorySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for repository-specific settings.
    
    @cpt-cyberwiki-fr-document-index
    """
    
    class Meta:
        model = RepositorySettings
        fields = ['id', 'repository_id', 'provider', 'base_url', 'branch', 'settings', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSettingsUpdateSerializer(serializers.Serializer):
    """Serializer for updating user settings (generic key-value pairs)."""
    settings = serializers.JSONField(help_text='User settings as JSON object')
