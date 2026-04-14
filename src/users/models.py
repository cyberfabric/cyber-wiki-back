import uuid
from django.db import models
from django.contrib.auth.models import User
import secrets


class UserRole(models.TextChoices):
    """User role choices for permission management."""
    ADMIN = 'admin', 'Admin'
    EDITOR = 'editor', 'Editor'
    COMMENTER = 'commenter', 'Commenter'
    VIEWER = 'viewer', 'Viewer'
    GUEST = 'guest', 'Guest'


class UserProfile(models.Model):
    """
    Extended user profile with role and settings.
    
    Stores user preferences, SSO information, and role-based permissions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.VIEWER,
        help_text='User role for permission management'
    )
    sso_provider = models.CharField(max_length=50, null=True, blank=True)
    last_sso_login = models.DateTimeField(null=True, blank=True)
    settings = models.JSONField(
        default=dict,
        help_text='User preferences and settings (JSON)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class ApiToken(models.Model):
    """
    API tokens for Bearer authentication.
    
    Allows users to create named tokens for programmatic API access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_tokens')
    name = models.CharField(
        max_length=255,
        help_text='Descriptive name for the token (e.g., "CLI Access", "CI/CD")'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Generate token on creation if not provided."""
        if not self.token:
            self.token = self.generate_token()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_token():
        """Generate a secure random token."""
        return secrets.token_urlsafe(48)
    
    class Meta:
        verbose_name = 'API Token'
        verbose_name_plural = 'API Tokens'
        ordering = ['-created_at']


class FavoriteRepository(models.Model):
    """
    User's favorite repositories for quick access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_repositories')
    repository_id = models.CharField(
        max_length=255,
        help_text='Repository identifier (e.g., "projectkey_reposlug")'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['user', 'repository_id']]
        verbose_name = 'Favorite Repository'
        verbose_name_plural = 'Favorite Repositories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.repository_id}"


class RecentRepository(models.Model):
    """
    Recently viewed repositories for each user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recent_repositories')
    repository_id = models.CharField(max_length=255)
    last_viewed_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['user', 'repository_id']]
        verbose_name = 'Recent Repository'
        verbose_name_plural = 'Recent Repositories'
        ordering = ['-last_viewed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.repository_id}"


class RepositoryViewMode(models.Model):
    """
    Per-repository view mode preference (Developer vs Document mode).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class ViewMode(models.TextChoices):
        DEVELOPER = 'developer', 'Developer Mode'  # Raw file tree
        DOCUMENT = 'document', 'Document Mode'     # Filtered doc tree
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repository_view_modes')
    repository_id = models.CharField(max_length=255)
    view_mode = models.CharField(
        max_length=20,
        choices=ViewMode.choices,
        default=ViewMode.DOCUMENT
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'repository_id']]
        verbose_name = 'Repository View Mode'
        verbose_name_plural = 'Repository View Modes'
    
    def __str__(self):
        return f"{self.user.username} - {self.repository_id} - {self.view_mode}"


class RepositorySettings(models.Model):
    """
    Per-repository configuration and preferences.
    Stores document index settings, branch preferences, etc.
    
    @cpt-cyberwiki-fr-document-index
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repository_settings')
    repository_id = models.CharField(max_length=255, help_text='Repository identifier')
    provider = models.CharField(max_length=50, help_text='Git provider (github, bitbucket_server, etc.)')
    base_url = models.URLField(blank=True, help_text='Provider base URL')
    branch = models.CharField(max_length=255, default='main', help_text='Default branch')
    settings = models.JSONField(
        default=dict,
        help_text='Repository-specific settings (document index, view mode, etc.)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'repository_id', 'provider']]
        verbose_name = 'Repository Settings'
        verbose_name_plural = 'Repository Settings'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.repository_id}"


class APIResponseCache(models.Model):
    """
    Cached API response with time-based invalidation.
    
    Stores responses keyed by provider, endpoint, and parameters.
    Used for development caching to work offline or reduce API calls.
    """
    import hashlib
    import json
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_cache',
        help_text='User who made the request'
    )
    
    # Request identification
    provider_type = models.CharField(
        max_length=50,
        help_text='Provider type (github, bitbucket_server, etc.)'
    )
    
    provider_id = models.CharField(
        max_length=255,
        help_text='Provider identifier (e.g., github.com, bitbucket.example.com)'
    )
    
    endpoint = models.CharField(
        max_length=500,
        help_text='API endpoint path'
    )
    
    method = models.CharField(
        max_length=10,
        default='GET',
        help_text='HTTP method'
    )
    
    # Parameters for cache key
    params_hash = models.CharField(
        max_length=64,
        help_text='SHA256 hash of request parameters'
    )
    
    params_json = models.JSONField(
        default=dict,
        help_text='Request parameters (repo, branch, file path, etc.)'
    )
    
    # Cached response
    response_data = models.JSONField(
        help_text='Cached response data'
    )
    
    status_code = models.IntegerField(
        default=200,
        help_text='HTTP status code'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    hit_count = models.IntegerField(
        default=0,
        help_text='Number of times this cache entry was used'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'provider_type', 'provider_id', 'endpoint', 'params_hash']),
            models.Index(fields=['user', 'created_at']),
        ]
        unique_together = ['user', 'provider_type', 'provider_id', 'endpoint', 'method', 'params_hash']
        verbose_name = 'API Response Cache'
        verbose_name_plural = 'API Response Caches'
    
    def __str__(self):
        return f"{self.provider_type}:{self.endpoint} ({self.params_hash[:8]})"
    
    @staticmethod
    def compute_params_hash(params: dict) -> str:
        """Compute SHA256 hash of parameters for cache key."""
        import hashlib
        import json
        # Sort keys for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        return hashlib.sha256(sorted_params.encode()).hexdigest()
