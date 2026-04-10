"""
Service token models for storing encrypted credentials for various services.
"""
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from cryptography.fernet import Fernet
import base64


class ServiceType(models.TextChoices):
    """Service types for tokens."""
    # Git providers
    GITHUB = 'github', 'GitHub'
    BITBUCKET_SERVER = 'bitbucket_server', 'Bitbucket Server'
    # Other services
    JIRA = 'jira', 'JIRA'
    CUSTOM_HEADER = 'custom_header', 'Custom Header Token'


class ServiceToken(models.Model):
    """
    Encrypted service credentials.
    
    Stores access tokens and credentials for various services with encryption.
    Supports Git providers (GitHub, Bitbucket), JIRA, and custom header tokens.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_tokens')
    service_type = models.CharField(
        max_length=50,
        choices=ServiceType.choices,
        help_text='Service type (Git providers, JIRA, Custom Header, etc.)'
    )
    base_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Base URL for the service (e.g., https://jira.acme.com) - not required for custom header tokens'
    )
    encrypted_token = models.TextField(
        help_text='Encrypted access token'
    )
    encrypted_username = models.TextField(
        null=True,
        blank=True,
        help_text='Encrypted username/email (for JIRA and Git providers)'
    )
    # Custom header token fields
    header_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Custom header name for token (e.g., X-Auth-Token, X-API-Key, Authorization)'
    )
    name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text='Descriptive name for this token'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['user', 'service_type', 'base_url']]
        verbose_name = 'Service Token'
        verbose_name_plural = 'Service Tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.service_type == ServiceType.CUSTOM_HEADER:
            return f"{self.user.username} - {self.service_type} - {self.name or 'Unnamed'}"
        return f"{self.user.username} - {self.service_type} - {self.base_url}"
    
    @staticmethod
    def _get_cipher():
        """Get Fernet cipher for encryption/decryption."""
        key = settings.ENCRYPTION_KEY.encode()
        # Ensure key is properly formatted for Fernet (32 bytes base64-encoded)
        # Pad or truncate to 32 bytes, then base64 encode
        key = base64.urlsafe_b64encode(key.ljust(32)[:32])
        return Fernet(key)
    
    def set_token(self, token):
        """Encrypt and store access token."""
        cipher = self._get_cipher()
        self.encrypted_token = cipher.encrypt(token.encode()).decode()
    
    def get_token(self):
        """Decrypt and return access token."""
        cipher = self._get_cipher()
        return cipher.decrypt(self.encrypted_token.encode()).decode()
    
    def set_username(self, username):
        """Encrypt and store username."""
        if username:
            cipher = self._get_cipher()
            self.encrypted_username = cipher.encrypt(username.encode()).decode()
    
    def get_username(self):
        """Decrypt and return username."""
        if self.encrypted_username:
            cipher = self._get_cipher()
            return cipher.decrypt(self.encrypted_username.encode()).decode()
        return None
    
    @classmethod
    def get_default_zta_header(cls):
        """Get default ZTA header name."""
        return 'X-Zero-Trust-Token'
