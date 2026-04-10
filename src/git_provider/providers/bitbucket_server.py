"""
Bitbucket Server provider implementation.
"""
import requests
from typing import List, Dict, Any, Optional
from ..base import BaseGitProvider


class BitbucketServerProvider(BaseGitProvider):
    """
    Bitbucket Server REST API implementation.
    
    Documentation: https://docs.atlassian.com/bitbucket-server/rest/
    """
    
    def __init__(self, base_url: str, token: str, username: Optional[str] = None, custom_header: Optional[str] = None, custom_header_token: Optional[str] = None):
        super().__init__(base_url, token, username)
        
        # Set up headers
        self.headers = {
            'Content-Type': 'application/json',
        }
        
        # Add custom header if provided (for additional authentication)
        if custom_header and custom_header_token:
            self.headers[custom_header] = custom_header_token
        
        # Cache for all repositories (to avoid re-fetching on pagination)
        self._all_repos_cache = None
    
    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Bitbucket Server API."""
        url = f"{self.base_url}/rest/api/1.0{endpoint}"
        
        # Use HTTP Basic Auth for Bitbucket Server (username:token)
        if self.username:
            kwargs['auth'] = (self.username, self.token)
        
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response
    
    def list_projects(self, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        """List all projects accessible to the user."""
        start = (page - 1) * per_page
        response = self._request('GET', '/projects', params={
            'start': start,
            'limit': per_page,
        })
        
        data = response.json()
        projects = data.get('values', [])
        
        return {
            'projects': [self._normalize_project(project) for project in projects],
            'page': page,
            'per_page': per_page,
            'total': data.get('size', len(projects)),
            'is_last_page': data.get('isLastPage', True),
        }
    
    def list_repositories(self, page: int = 1, per_page: int = 30, project_key: Optional[str] = None) -> Dict[str, Any]:
        """
        List repositories. If project_key is provided, list repos for that project only.
        Otherwise, list all repos (legacy behavior, may have duplicates).
        """
        if project_key:
            # List repos for specific project
            start = (page - 1) * per_page
            response = self._request('GET', f'/projects/{project_key}/repos', params={
                'start': start,
                'limit': per_page,
            })
            
            data = response.json()
            repos = data.get('values', [])
            
            return {
                'repositories': [self._normalize_repo(repo) for repo in repos],
                'page': page,
                'per_page': per_page,
                'total': data.get('size', len(repos)),
                'is_last_page': data.get('isLastPage', True),
            }
        else:
            # Legacy: list all repos (may have duplicates)
            start = (page - 1) * per_page
            response = self._request('GET', '/repos', params={
                'start': start,
                'limit': per_page,
            })
            
            data = response.json()
            repos = data.get('values', [])
            
            return {
                'repositories': [self._normalize_repo(repo) for repo in repos],
                'page': page,
                'per_page': per_page,
                'total': data.get('size', len(repos)),
                'is_last_page': data.get('isLastPage', True),
            }
    
    def _normalize_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize project data to common format."""
        return {
            'id': project.get('key'),
            'key': project.get('key'),
            'name': project.get('name'),
            'description': project.get('description', ''),
            'public': project.get('public', False),
            'type': project.get('type', 'NORMAL'),
        }
    
    def get_repository(self, repo_id: str) -> Dict[str, Any]:
        """Get repository details. repo_id format: 'projectkey_reposlug'"""
        project_key, repo_slug = repo_id.split('_', 1)
        response = self._request('GET', f'/projects/{project_key}/repos/{repo_slug}')
        return self._normalize_repo(response.json())
    
    def get_file_content(self, repo_id: str, file_path: str, branch: str = 'main') -> Dict[str, Any]:
        """Get file content from repository."""
        project_key, repo_slug = repo_id.split('_', 1)
        
        # Get file content
        response = self._request('GET', f'/projects/{project_key}/repos/{repo_slug}/browse/{file_path}', params={
            'at': branch,
        })
        
        data = response.json()
        lines = data.get('lines', [])
        content = '\n'.join([line.get('text', '') for line in lines])
        
        return {
            'content': content,
            'encoding': 'utf-8',
            'sha': '',  # Bitbucket doesn't provide SHA in browse endpoint
            'size': len(content),
            'path': file_path,
        }
    
    def get_directory_tree(self, repo_id: str, path: str = '', branch: str = 'main', recursive: bool = False) -> List[Dict[str, Any]]:
        """Get directory tree."""
        project_key, repo_slug = repo_id.split('_', 1)
        
        endpoint = f'/projects/{project_key}/repos/{repo_slug}/browse'
        if path:
            endpoint += f'/{path}'
        
        response = self._request('GET', endpoint, params={
            'at': branch,
            'limit': 1000,
        })
        
        data = response.json()
        children = data.get('children', {}).get('values', [])
        
        results = []
        for child in children:
            results.append(self._normalize_tree_entry(child))
            
            # Recursively get subdirectories if requested
            if recursive and child.get('type') == 'DIRECTORY':
                subpath = f"{path}/{child.get('path', {}).get('name', '')}" if path else child.get('path', {}).get('name', '')
                results.extend(self.get_directory_tree(repo_id, subpath, branch, recursive))
        
        return results
    
    def list_pull_requests(self, repo_id: str, state: str = 'open', page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """List pull requests."""
        project_key, repo_slug = repo_id.split('_', 1)
        start = (page - 1) * per_page
        
        # Map state to Bitbucket state
        bb_state = {
            'open': 'OPEN',
            'closed': 'DECLINED',
            'merged': 'MERGED',
            'all': 'ALL',
        }.get(state.lower(), 'OPEN')
        
        response = self._request('GET', f'/projects/{project_key}/repos/{repo_slug}/pull-requests', params={
            'state': bb_state,
            'start': start,
            'limit': per_page,
        })
        
        data = response.json()
        prs = data.get('values', [])
        
        return {
            'pull_requests': [self._normalize_pr(pr) for pr in prs],
            'page': page,
            'per_page': per_page,
            'is_last_page': data.get('isLastPage', True),
        }
    
    def get_pull_request(self, repo_id: str, pr_number: int) -> Dict[str, Any]:
        """Get pull request details."""
        project_key, repo_slug = repo_id.split('_', 1)
        response = self._request('GET', f'/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_number}')
        return self._normalize_pr(response.json())
    
    def get_pull_request_diff(self, repo_id: str, pr_number: int) -> str:
        """Get pull request diff."""
        project_key, repo_slug = repo_id.split('_', 1)
        response = self._request('GET', f'/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_number}/diff')
        
        # Bitbucket returns diff in a structured format
        data = response.json()
        diffs = data.get('diffs', [])
        
        # Convert to unified diff format
        diff_text = []
        for diff in diffs:
            source = diff.get('source', {})
            destination = diff.get('destination', {})
            diff_text.append(f"--- {source.get('toString', '')}")
            diff_text.append(f"+++ {destination.get('toString', '')}")
            
            for hunk in diff.get('hunks', []):
                for segment in hunk.get('segments', []):
                    for line in segment.get('lines', []):
                        diff_text.append(line.get('line', ''))
        
        return '\n'.join(diff_text)
    
    def list_commits(self, repo_id: str, branch: str = 'main', page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """List commits."""
        project_key, repo_slug = repo_id.split('_', 1)
        start = (page - 1) * per_page
        
        response = self._request('GET', f'/projects/{project_key}/repos/{repo_slug}/commits', params={
            'until': branch,
            'start': start,
            'limit': per_page,
        })
        
        data = response.json()
        commits = data.get('values', [])
        
        return {
            'commits': [self._normalize_commit(commit) for commit in commits],
            'page': page,
            'per_page': per_page,
            'is_last_page': data.get('isLastPage', True),
        }
    
    def create_commit(self, repo_id: str, branch: str, message: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create a commit with file changes."""
        raise NotImplementedError("Commit creation not yet implemented for Bitbucket Server")
    
    def _normalize_repo(self, repo: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize repository data."""
        project = repo.get('project', {})
        links = repo.get('links', {})
        clone_links = links.get('clone', [])
        
        clone_url = ''
        for link in clone_links:
            if link.get('name') == 'http':
                clone_url = link.get('href', '')
                break
        
        return {
            'id': f"{project.get('key', '')}_{repo.get('slug', '')}",
            'name': repo.get('name', ''),
            'full_name': f"{project.get('key', '')}/{repo.get('slug', '')}",
            'description': repo.get('description', ''),
            'private': not repo.get('public', False),
            'default_branch': repo.get('defaultBranch', 'main'),
            'url': links.get('self', [{}])[0].get('href', ''),
            'clone_url': clone_url,
            'updated_at': '',
        }
    
    def _normalize_tree_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize tree entry."""
        path_info = entry.get('path', {})
        return {
            'path': path_info.get('toString', ''),
            'type': 'dir' if entry.get('type') == 'DIRECTORY' else 'file',
            'size': entry.get('size', 0),
            'sha': '',
        }
    
    def _normalize_pr(self, pr: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize pull request data."""
        author = pr.get('author', {}).get('user', {})
        links = pr.get('links', {})
        
        return {
            'number': pr.get('id', 0),
            'title': pr.get('title', ''),
            'state': pr.get('state', '').lower(),
            'author': author.get('displayName', ''),
            'created_at': str(pr.get('createdDate', '')),
            'updated_at': str(pr.get('updatedDate', '')),
            'merged': pr.get('state') == 'MERGED',
            'url': links.get('self', [{}])[0].get('href', ''),
        }
    
    def _normalize_commit(self, commit: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize commit data."""
        author = commit.get('author', {})
        
        return {
            'sha': commit.get('id', ''),
            'message': commit.get('message', ''),
            'author': author.get('displayName', ''),
            'date': str(commit.get('authorTimestamp', '')),
            'url': '',
        }
    
    def normalize_repository_id(self, repo_data: Dict[str, Any]) -> str:
        """Normalize repository ID to 'projectkey_reposlug' format."""
        project = repo_data.get('project', {})
        return f"{project.get('key', '')}_{repo_data.get('slug', '')}"
