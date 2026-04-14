"""
Factory for creating Git provider instances.
"""
from typing import Optional
from .base import BaseGitProvider
from .providers.github import GitHubProvider
from .providers.bitbucket_server import BitbucketServerProvider
from .providers.local_git import LocalGitProvider
from service_tokens.models import ServiceType


class GitProviderFactory:
    """
    Factory class for creating Git provider instances.
    """
    
    @staticmethod
    def create(provider: str, base_url: str, token: str, username: Optional[str] = None, custom_header: Optional[str] = None, custom_header_token: Optional[str] = None, user=None) -> BaseGitProvider:
        """
        Create a Git provider instance.
        
        Args:
            provider: Provider type ('github' or 'bitbucket_server')
            base_url: Base URL for the provider API
            token: Access token
            username: Username (required for Bitbucket Server)
            custom_header: Custom header name for authentication (e.g., 'X-Custom-Token')
            custom_header_token: Token value for custom header
            user: Django user instance for caching (optional)
        
        Returns:
            BaseGitProvider instance
        
        Raises:
            ValueError: If provider type is not supported
        """
        if provider == ServiceType.GITHUB:
            return GitHubProvider(base_url=base_url, token=token, username=username, user=user)
        elif provider == ServiceType.BITBUCKET_SERVER:
            if not username:
                raise ValueError("Username is required for Bitbucket Server")
            return BitbucketServerProvider(base_url=base_url, token=token, username=username, custom_header=custom_header, custom_header_token=custom_header_token, user=user)
        elif provider == 'local_git':
            # For local Git, base_url is the filesystem path
            return LocalGitProvider(base_path=base_url, token=token, username=username, user=user)
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
        import logging
        logger = logging.getLogger(__name__)
        
        custom_header = None
        custom_header_name = None
        
        # For Bitbucket Server, also fetch custom header token if available
        if service_token.service_type == ServiceType.BITBUCKET_SERVER:
            logger.info(f"Looking for custom header token for user {service_token.user.username}")
            try:
                # Custom header tokens are typically global (empty base_url)
                # But user might have multiple, so prefer empty base_url first
                all_custom_tokens = ServiceToken.objects.filter(
                    user=service_token.user,
                    service_type=ServiceType.CUSTOM_HEADER
                )
                logger.info(f"Found {all_custom_tokens.count()} custom header token(s)")
                for ct in all_custom_tokens:
                    logger.info(f"  Custom token: base_url='{ct.base_url}', header_name={ct.header_name}, name={ct.name}")
                
                custom_token = all_custom_tokens.order_by('base_url').first()  # Empty string sorts first
                
                if custom_token:
                    custom_header = custom_token.get_token()
                    custom_header_name = custom_token.header_name
                    logger.info(f"Using custom header token: {custom_header_name} (base_url: '{custom_token.base_url}', token length: {len(custom_header) if custom_header else 0})")
                else:
                    logger.warning(f"No custom header token found for user {service_token.user.username}")
            except Exception as e:
                logger.error(f"Error fetching custom header token: {e}", exc_info=True)
                pass  # Custom header token not configured, continue without it
        
        return GitProviderFactory.create(
            provider=service_token.service_type,
            base_url=service_token.base_url,
            token=service_token.get_token(),
            username=service_token.get_username(),
            custom_header=custom_header_name,
            custom_header_token=custom_header,
            user=service_token.user  # Pass user for caching
        )
