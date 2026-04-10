"""
Factory for creating Git provider instances.
"""
from typing import Optional
from .base import BaseGitProvider
from .providers.github import GitHubProvider
from .providers.bitbucket_server import BitbucketServerProvider
from service_tokens.models import ServiceType


class GitProviderFactory:
    """
    Factory class for creating Git provider instances.
    """
    
    @staticmethod
    def create(provider: str, base_url: str, token: str, username: Optional[str] = None, custom_header: Optional[str] = None, custom_header_token: Optional[str] = None) -> BaseGitProvider:
        """
        Create a Git provider instance.
        
        Args:
            provider: Provider type ('github' or 'bitbucket_server')
            base_url: Base URL for the provider API
            token: Access token
            username: Username (required for Bitbucket Server)
            custom_header: Custom header name for authentication (e.g., 'X-Custom-Token')
            custom_header_token: Token value for custom header
        
        Returns:
            BaseGitProvider instance
        
        Raises:
            ValueError: If provider type is not supported
        """
        if provider == ServiceType.GITHUB:
            return GitHubProvider(base_url=base_url, token=token, username=username)
        elif provider == ServiceType.BITBUCKET_SERVER:
            if not username:
                raise ValueError("Username is required for Bitbucket Server")
            return BitbucketServerProvider(base_url=base_url, token=token, username=username, custom_header=custom_header, custom_header_token=custom_header_token)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @staticmethod
    def create_from_service_token(service_token):
        """
        Create a Git provider instance from a ServiceToken model.
        
        Args:
            service_token: ServiceToken model instance
        
        Returns:
            BaseGitProvider instance
        """
        from service_tokens.models import ServiceToken
        
        custom_header = None
        custom_header_name = None
        
        # For Bitbucket Server, also fetch custom header token if available
        if service_token.service_type == ServiceType.BITBUCKET_SERVER:
            try:
                custom_token = ServiceToken.objects.get(
                    user=service_token.user,
                    service_type=ServiceType.CUSTOM_HEADER
                )
                custom_header = custom_token.get_token()
                custom_header_name = custom_token.header_name
            except ServiceToken.DoesNotExist:
                pass  # Custom header token not configured, continue without it
        
        return GitProviderFactory.create(
            provider=service_token.service_type,
            base_url=service_token.base_url,
            token=service_token.get_token(),
            username=service_token.get_username(),
            custom_header=custom_header_name,
            custom_header_token=custom_header
        )
