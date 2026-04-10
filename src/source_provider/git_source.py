"""
Git-based source provider implementation.
"""
from typing import Dict, Any, List
from .base import BaseSourceProvider, SourceAddress
from git_provider.factory import GitProviderFactory
from service_tokens.models import ServiceToken


class GitSourceProvider(BaseSourceProvider):
    """
    Source provider that retrieves content from Git providers.
    """
    
    def __init__(self, user):
        """
        Initialize Git source provider.
        
        Args:
            user: Django User instance
        """
        self.user = user
    
    def _get_git_provider(self, address: SourceAddress):
        """Get Git provider instance for the source address."""
        try:
            # Find matching ServiceToken for this provider and repository
            service_token = ServiceToken.objects.filter(
                user=self.user,
                service_type=address.provider
            ).first()
            
            if not service_token:
                raise ValueError(f"No credentials found for provider: {address.provider}")
            
            return GitProviderFactory.create_from_service_token(service_token)
        except ServiceToken.DoesNotExist:
            raise ValueError(f"No credentials found for provider: {address.provider}")
    
    def get_content(self, address: SourceAddress) -> Dict[str, Any]:
        """
        Get file content from Git provider.
        
        Args:
            address: SourceAddress instance
        
        Returns:
            Dict with content, encoding, metadata, and optionally filtered lines
        """
        provider = self._get_git_provider(address)
        
        # Get file content from Git provider
        file_data = provider.get_file_content(
            repo_id=address.repository,
            file_path=address.path,
            branch=address.branch
        )
        
        # If line range is specified, filter content
        if address.line_start is not None:
            content = file_data.get('content', '')
            lines = content.split('\n')
            
            start = address.line_start - 1  # Convert to 0-indexed
            end = address.line_end if address.line_end else address.line_start
            
            # Extract specified lines
            filtered_lines = lines[start:end]
            file_data['content'] = '\n'.join(filtered_lines)
            file_data['line_start'] = address.line_start
            file_data['line_end'] = end
            file_data['total_lines'] = len(lines)
        
        # Add source address to response
        file_data['source_uri'] = address.to_uri()
        
        return file_data
    
    def get_tree(self, address: SourceAddress, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Get directory tree from Git provider.
        
        Args:
            address: SourceAddress instance
            recursive: Whether to recursively list all files
        
        Returns:
            List of tree entries with source URIs
        """
        provider = self._get_git_provider(address)
        
        # Get directory tree from Git provider
        tree = provider.get_directory_tree(
            repo_id=address.repository,
            path=address.path,
            branch=address.branch,
            recursive=recursive
        )
        
        # Add source URIs to each entry
        for entry in tree:
            entry_address = SourceAddress(
                provider=address.provider,
                repository=address.repository,
                branch=address.branch,
                path=entry['path']
            )
            entry['source_uri'] = entry_address.to_uri()
        
        return tree
