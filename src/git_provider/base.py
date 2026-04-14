"""
Abstract base class for Git provider implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseGitProvider(ABC):
    """
    Abstract interface for Git provider implementations.
    
    All Git providers (GitHub, Bitbucket Server, etc.) must implement this interface.
    """
    
    def __init__(self, base_url: str, token: str, username: Optional[str] = None, user=None):
        """
        Initialize the Git provider.
        
        Args:
            base_url: Base URL for the Git provider API
            token: Access token for authentication
            username: Username (required for some providers like Bitbucket Server)
            user: Django user instance for caching (optional)
        """
        self.base_url = base_url
        self.token = token
        self.username = username
        self.user = user  # Store user for caching
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Report which features this provider supports.
        
        Returns:
            Dict mapping feature names to support status (True/False)
        """
        return {
            'list_repositories': True,
            'get_repository': True,
            'get_file_content': True,
            'get_directory_tree': True,
            'list_pull_requests': True,
            'get_pull_request': True,
            'get_pull_request_diff': True,
            'list_commits': True,
            'create_commit': True,
            'requires_authentication': True,
            'supports_webhooks': False,
            'supports_projects': False,
        }
    
    @property
    def provider_type(self) -> str:
        """
        Return the provider type identifier.
        
        Returns:
            Provider type string (e.g., 'github', 'bitbucket_server', 'local_git')
        """
        return 'unknown'
    
    @abstractmethod
    def list_repositories(self, page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """
        List repositories accessible to the authenticated user.
        
        Args:
            page: Page number (1-indexed)
            per_page: Number of repositories per page
        
        Returns:
            Dict with 'repositories' list and pagination metadata
        """
        pass
    
    @abstractmethod
    def get_repository(self, repo_id: str) -> Dict[str, Any]:
        """
        Get details of a specific repository.
        
        Args:
            repo_id: Repository identifier (format varies by provider)
        
        Returns:
            Repository details
        """
        pass
    
    @abstractmethod
    def get_file_content(self, project_key: str, repo_slug: str, file_path: str, branch: str = 'main') -> Dict[str, Any]:
        """
        Get content of a specific file.
        
        Args:
            project_key: Project key (for Bitbucket) or owner (for GitHub)
            repo_slug: Repository slug/name
            file_path: Path to the file within the repository
            branch: Branch name (default: 'main')
        
        Returns:
            Dict with 'content', 'encoding', 'sha', etc.
        """
        pass
    
    @abstractmethod
    def get_directory_tree(self, project_key: str, repo_slug: str, path: str = '', branch: str = 'main', recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Get directory tree/listing.
        
        Args:
            project_key: Project key (for Bitbucket) or owner (for GitHub)
            repo_slug: Repository slug/name
            path: Directory path (empty for root)
            branch: Branch name
            recursive: Whether to recursively list all files
        
        Returns:
            List of file/directory entries
        """
        pass
    
    @abstractmethod
    def list_pull_requests(self, repo_id: str, state: str = 'open', page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """
        List pull requests for a repository.
        
        Args:
            repo_id: Repository identifier
            state: PR state ('open', 'closed', 'merged', 'all')
            page: Page number
            per_page: Number of PRs per page
        
        Returns:
            Dict with 'pull_requests' list and pagination metadata
        """
        pass
    
    @abstractmethod
    def get_pull_request(self, repo_id: str, pr_number: int) -> Dict[str, Any]:
        """
        Get details of a specific pull request.
        
        Args:
            repo_id: Repository identifier
            pr_number: Pull request number
        
        Returns:
            Pull request details
        """
        pass
    
    @abstractmethod
    def get_pull_request_diff(self, repo_id: str, pr_number: int) -> str:
        """
        Get diff for a pull request.
        
        Args:
            repo_id: Repository identifier
            pr_number: Pull request number
        
        Returns:
            Diff content as string
        """
        pass
    
    @abstractmethod
    def list_commits(self, repo_id: str, branch: str = 'main', page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """
        List commits for a repository.
        
        Args:
            repo_id: Repository identifier
            branch: Branch name
            page: Page number
            per_page: Number of commits per page
        
        Returns:
            Dict with 'commits' list and pagination metadata
        """
        pass
    
    @abstractmethod
    def create_commit(self, repo_id: str, branch: str, message: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Create a new commit with file changes.
        
        Args:
            repo_id: Repository identifier
            branch: Branch name
            message: Commit message
            files: List of file changes [{'path': '...', 'content': '...', 'action': 'create|update|delete'}]
        
        Returns:
            Commit details
        """
        pass
    
    def normalize_repository_id(self, repo_data: Dict[str, Any]) -> str:
        """
        Normalize repository identifier across providers.
        
        Args:
            repo_data: Repository data from provider
        
        Returns:
            Normalized repository ID (e.g., "owner_repo" or "projectkey_reposlug")
        """
        # Default implementation - can be overridden
        return repo_data.get('id', '')
