"""
GitHub provider implementation.
"""
import requests
from typing import List, Dict, Any, Optional
from ..base import BaseGitProvider


class GitHubProvider(BaseGitProvider):
    """
    GitHub REST API v3 implementation.
    
    Documentation: https://docs.github.com/en/rest
    """
    
    def __init__(self, base_url: str = 'https://api.github.com', token: str = '', username: Optional[str] = None, user=None):
        super().__init__(base_url, token, username, user)
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3+json',
        }
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Report which features this provider supports.
        GitHub has full API support.
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
            'supports_webhooks': True,
            'supports_projects': False,  # GitHub uses orgs, not projects
            'supports_organizations': True,  # Unique to GitHub
            'supports_actions': True,  # Unique to GitHub
        }
    
    @property
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        return 'github'
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to GitHub API."""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response
    
    def list_repositories(self, page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """List repositories accessible to the authenticated user."""
        response = self._request('GET', '/user/repos', params={
            'page': page,
            'per_page': per_page,
            'sort': 'updated',
            'affiliation': 'owner,collaborator,organization_member'
        })
        
        repos = response.json()
        return {
            'repositories': [self._normalize_repo(repo) for repo in repos],
            'page': page,
            'per_page': per_page,
            'total': len(repos),  # GitHub doesn't provide total count easily
        }
    
    def get_repository(self, repo_id: str) -> Dict[str, Any]:
        """Get repository details. repo_id format: 'owner/repo'"""
        response = self._request('GET', f'/repos/{repo_id}')
        return self._normalize_repo(response.json())
    
    def get_file_content(self, project_key: str, repo_slug: str, file_path: str, branch: str = 'main') -> Dict[str, Any]:
        """Get file content from repository."""
        repo_id = f"{project_key}/{repo_slug}"
        response = self._request('GET', f'/repos/{repo_id}/contents/{file_path}', params={'ref': branch})
        data = response.json()
        
        return {
            'content': data.get('content', ''),
            'encoding': data.get('encoding', 'base64'),
            'sha': data.get('sha', ''),
            'size': data.get('size', 0),
            'path': data.get('path', file_path),
        }
    
    def get_directory_tree(self, project_key: str, repo_slug: str, path: str = '', branch: str = 'main', recursive: bool = False) -> List[Dict[str, Any]]:
        """Get directory tree."""
        repo_id = f"{project_key}/{repo_slug}"
        if recursive:
            # Use Git Trees API for recursive listing
            response = self._request('GET', f'/repos/{repo_id}/git/trees/{branch}', params={'recursive': '1'})
            tree = response.json().get('tree', [])
            return [self._normalize_tree_entry(entry) for entry in tree]
        else:
            # Use Contents API for single directory
            endpoint = f'/repos/{repo_id}/contents/{path}' if path else f'/repos/{repo_id}/contents'
            response = self._request('GET', endpoint, params={'ref': branch})
            contents = response.json()
            
            if isinstance(contents, list):
                return [self._normalize_tree_entry(entry) for entry in contents]
            else:
                return [self._normalize_tree_entry(contents)]
    
    def list_pull_requests(self, repo_id: str, state: str = 'open', page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """List pull requests."""
        response = self._request('GET', f'/repos/{repo_id}/pulls', params={
            'state': state if state != 'merged' else 'closed',
            'page': page,
            'per_page': per_page,
        })
        
        prs = response.json()
        return {
            'pull_requests': [self._normalize_pr(pr) for pr in prs],
            'page': page,
            'per_page': per_page,
        }
    
    def get_pull_request(self, repo_id: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request details."""
        response = self._request('GET', f'/repos/{repo_id}/pulls/{pr_number}')
        return self._normalize_pr(response.json())
    
    def get_pull_request_diff(self, repo_id: str, pr_number: int) -> str:
        """Get pull request diff."""
        headers = {**self.headers, 'Accept': 'application/vnd.github.v3.diff'}
        response = self._request('GET', f'/repos/{repo_id}/pulls/{pr_number}')
        
        # Get diff via separate request
        diff_response = requests.get(
            f"{self.base_url}/repos/{repo_id}/pulls/{pr_number}",
            headers=headers
        )
        diff_response.raise_for_status()
        return diff_response.text
    
    def list_commits(self, repo_id: str, branch: str = 'main', page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """List commits."""
        response = self._request('GET', f'/repos/{repo_id}/commits', params={
            'sha': branch,
            'page': page,
            'per_page': per_page,
        })
        
        commits = response.json()
        return {
            'commits': [self._normalize_commit(commit) for commit in commits],
            'page': page,
            'per_page': per_page,
        }
    
    def create_commit(self, repo_id: str, branch: str, message: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create a commit with file changes."""
        # This is a simplified implementation
        # Full implementation would use GitHub's Git Data API
        raise NotImplementedError("Commit creation not yet implemented for GitHub")
    
    def _normalize_repo(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize repository data."""
        return {
            'id': repo.get('full_name', ''),
            'name': repo.get('name', ''),
            'full_name': repo.get('full_name', ''),
            'description': repo.get('description', ''),
            'private': repo.get('private', False),
            'default_branch': repo.get('default_branch', 'main'),
            'url': repo.get('html_url', ''),
            'clone_url': repo.get('clone_url', ''),
            'updated_at': repo.get('updated_at', ''),
        }
    
    def _normalize_tree_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize tree entry."""
        return {
            'path': entry.get('path', ''),
            'type': entry.get('type', 'file'),
            'size': entry.get('size', 0),
            'sha': entry.get('sha', ''),
        }
    
    def _normalize_pr(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize pull request data."""
        return {
            'number': pr.get('number', 0),
            'title': pr.get('title', ''),
            'state': pr.get('state', ''),
            'author': pr.get('user', {}).get('login', ''),
            'created_at': pr.get('created_at', ''),
            'updated_at': pr.get('updated_at', ''),
            'merged': pr.get('merged', False),
            'url': pr.get('html_url', ''),
        }
    
    def _normalize_commit(self, commit: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize commit data."""
        return {
            'sha': commit.get('sha', ''),
            'message': commit.get('commit', {}).get('message', ''),
            'author': commit.get('commit', {}).get('author', {}).get('name', ''),
            'date': commit.get('commit', {}).get('author', {}).get('date', ''),
            'url': commit.get('html_url', ''),
        }
    
    def normalize_repository_id(self, repo_data: Dict[str, Any]) -> str:
        """Normalize repository ID to 'owner_repo' format."""
        full_name = repo_data.get('full_name', '')
        return full_name.replace('/', '_')
