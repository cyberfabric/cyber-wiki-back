"""
Universal source addressing and base provider interface.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re


@dataclass
class SourceAddress:
    """
    Universal source address for files and content.
    
    Format: git://{provider}/{repo}/{branch}/{path}#{line_start}-{line_end}
    
    Examples:
        - git://github/facebook_react/main/README.md
        - git://github/facebook_react/main/src/index.js#10-20
        - git://bitbucket_server/PROJECT_repo/main/docs/api.md#5
    """
    provider: str  # 'github' or 'bitbucket_server'
    repository: str  # Repository identifier (e.g., 'owner_repo' or 'projectkey_reposlug')
    branch: str  # Branch name
    path: str  # File path within repository
    line_start: Optional[int] = None  # Starting line number (1-indexed)
    line_end: Optional[int] = None  # Ending line number (1-indexed, inclusive)
    
    @classmethod
    def parse(cls, uri: str) -> 'SourceAddress':
        """
        Parse a source URI into a SourceAddress.
        
        Args:
            uri: Source URI string
        
        Returns:
            SourceAddress instance
        
        Raises:
            ValueError: If URI format is invalid
        """
        # Pattern: git://{provider}/{repo}/{branch}/{path}#{lines}
        pattern = r'^git://([^/]+)/([^/]+)/([^/]+)/(.+?)(?:#(\d+)(?:-(\d+))?)?$'
        match = re.match(pattern, uri)
        
        if not match:
            raise ValueError(f"Invalid source URI format: {uri}")
        
        provider, repository, branch, path, line_start, line_end = match.groups()
        
        return cls(
            provider=provider,
            repository=repository,
            branch=branch,
            path=path,
            line_start=int(line_start) if line_start else None,
            line_end=int(line_end) if line_end else None
        )
    
    def to_uri(self) -> str:
        """
        Convert SourceAddress to URI string.
        
        Returns:
            URI string
        """
        uri = f"git://{self.provider}/{self.repository}/{self.branch}/{self.path}"
        
        if self.line_start is not None:
            if self.line_end is not None and self.line_end != self.line_start:
                uri += f"#{self.line_start}-{self.line_end}"
            else:
                uri += f"#{self.line_start}"
        
        return uri
    
    def __str__(self) -> str:
        return self.to_uri()


class BaseSourceProvider:
    """
    Base interface for source content providers.
    """
    
    def get_content(self, address: SourceAddress) -> Dict[str, Any]:
        """
        Get content from a source address.
        
        Args:
            address: SourceAddress instance
        
        Returns:
            Dict with content, encoding, metadata
        """
        raise NotImplementedError
    
    def get_tree(self, address: SourceAddress, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Get directory tree from a source address.
        
        Args:
            address: SourceAddress instance (path should be directory)
            recursive: Whether to recursively list all files
        
        Returns:
            List of tree entries
        """
        raise NotImplementedError
