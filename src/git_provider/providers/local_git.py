"""
Local Git repository provider implementation.
Provides access to Git repositories on the local filesystem.
"""
import os
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
import base64
from datetime import datetime

from ..base import BaseGitProvider


class LocalGitProvider(BaseGitProvider):
    """
    Git provider for local filesystem repositories.
    
    This provider allows accessing Git repositories that are cloned locally
    on the server's filesystem, without requiring remote API access.
    """
    
    def __init__(self, base_path: str, token: str = '', username: Optional[str] = None, user=None):
        """
        Initialize the local Git provider.
        
        Args:
            base_path: Base directory path where Git repositories are located
            token: Not used for local repos (kept for interface compatibility)
            username: Not used for local repos (kept for interface compatibility)
            user: Django user instance for caching (optional)
        """
        super().__init__(base_url=base_path, token=token, username=username, user=user)
        self.base_path = Path(base_path)
        
        if not self.base_path.exists():
            raise ValueError(f"Base path does not exist: {base_path}")
        
        if not self.base_path.is_dir():
            raise ValueError(f"Base path is not a directory: {base_path}")
    
    @property
    def capabilities(self) -> Dict[str, bool]:
        """
        Report which features this provider supports.
        Local Git has different capabilities than remote providers.
        """
        return {
            'list_repositories': True,
            'get_repository': True,
            'get_file_content': True,
            'get_directory_tree': True,
            'list_pull_requests': False,  # Not supported for local repos
            'get_pull_request': False,  # Not supported for local repos
            'get_pull_request_diff': False,  # Not supported for local repos
            'list_commits': True,
            'create_commit': True,
            'requires_authentication': False,  # No auth needed for local
            'supports_webhooks': False,
            'supports_projects': False,
            'direct_filesystem_access': True,  # Unique to local
            'fast_access': True,  # Unique to local
            'air_gapped_compatible': True,  # Unique to local
        }
    
    @property
    def provider_type(self) -> str:
        """Return the provider type identifier."""
        return 'local_git'
    
    def _run_git_command(self, repo_path: Path, command: List[str]) -> str:
        """
        Run a Git command in a repository.
        
        Args:
            repo_path: Path to the repository
            command: Git command arguments (without 'git' prefix)
        
        Returns:
            Command output
        
        Raises:
            subprocess.CalledProcessError: If command fails
        """
        full_command = ['git', '-C', str(repo_path)] + command
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    
    def _get_repo_path(self, repo_id: str) -> Path:
        """
        Get full path to a repository.
        
        Args:
            repo_id: Repository identifier (relative path from base_path)
        
        Returns:
            Full path to repository
        """
        repo_path = self.base_path / repo_id
        
        if not repo_path.exists():
            raise ValueError(f"Repository not found: {repo_id}")
        
        if not (repo_path / '.git').exists():
            raise ValueError(f"Not a Git repository: {repo_id}")
        
        return repo_path
    
    def _is_git_repo(self, path: Path) -> bool:
        """Check if a directory is a Git repository."""
        return (path / '.git').exists() and path.is_dir()
    
    def list_repositories(self, page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """
        List all Git repositories in the base path.
        
        Scans the base directory for Git repositories (directories containing .git).
        Supports nested repositories up to 3 levels deep.
        """
        repositories = []
        
        # Scan for Git repositories
        for root, dirs, files in os.walk(self.base_path):
            root_path = Path(root)
            
            # Limit depth to avoid scanning too deep
            depth = len(root_path.relative_to(self.base_path).parts)
            if depth > 3:
                continue
            
            if self._is_git_repo(root_path):
                try:
                    # Get repository info
                    repo_id = str(root_path.relative_to(self.base_path))
                    
                    # Get remote URL if available
                    try:
                        remote_url = self._run_git_command(
                            root_path,
                            ['config', '--get', 'remote.origin.url']
                        )
                    except subprocess.CalledProcessError:
                        remote_url = ''
                    
                    # Get current branch
                    try:
                        current_branch = self._run_git_command(
                            root_path,
                            ['rev-parse', '--abbrev-ref', 'HEAD']
                        )
                    except subprocess.CalledProcessError:
                        current_branch = 'main'
                    
                    # Get last commit info
                    try:
                        last_commit_date = self._run_git_command(
                            root_path,
                            ['log', '-1', '--format=%ci']
                        )
                        last_commit_message = self._run_git_command(
                            root_path,
                            ['log', '-1', '--format=%s']
                        )
                    except subprocess.CalledProcessError:
                        last_commit_date = ''
                        last_commit_message = ''
                    
                    repositories.append({
                        'id': repo_id,
                        'name': root_path.name,
                        'full_name': repo_id,
                        'description': last_commit_message,
                        'clone_url': remote_url or f'file://{root_path}',
                        'default_branch': current_branch,
                        'updated_at': last_commit_date,
                        'is_private': True,  # Local repos are always private
                        'provider': 'local_git',
                        'path': str(root_path),
                    })
                    
                    # Don't descend into Git repositories
                    dirs[:] = []
                except Exception as e:
                    # Skip repositories that cause errors
                    print(f"Error processing repository {root_path}: {e}")
                    continue
        
        # Sort by name
        repositories.sort(key=lambda x: x['name'])
        
        # Pagination
        total = len(repositories)
        start = (page - 1) * per_page
        end = start + per_page
        page_repos = repositories[start:end]
        
        return {
            'repositories': page_repos,
            'page': page,
            'per_page': per_page,
            'total': total,
            'is_last_page': end >= total,
        }
    
    def get_repository(self, repo_id: str) -> Dict[str, Any]:
        """
        Get details of a specific repository.
        """
        repo_path = self._get_repo_path(repo_id)
        
        # Get remote URL
        try:
            remote_url = self._run_git_command(
                repo_path,
                ['config', '--get', 'remote.origin.url']
            )
        except subprocess.CalledProcessError:
            remote_url = ''
        
        # Get current branch
        try:
            current_branch = self._run_git_command(
                repo_path,
                ['rev-parse', '--abbrev-ref', 'HEAD']
            )
        except subprocess.CalledProcessError:
            current_branch = 'main'
        
        # Get last commit
        try:
            last_commit_sha = self._run_git_command(
                repo_path,
                ['rev-parse', 'HEAD']
            )
            last_commit_date = self._run_git_command(
                repo_path,
                ['log', '-1', '--format=%ci']
            )
            last_commit_message = self._run_git_command(
                repo_path,
                ['log', '-1', '--format=%s']
            )
            last_commit_author = self._run_git_command(
                repo_path,
                ['log', '-1', '--format=%an']
            )
        except subprocess.CalledProcessError:
            last_commit_sha = ''
            last_commit_date = ''
            last_commit_message = ''
            last_commit_author = ''
        
        return {
            'id': repo_id,
            'name': repo_path.name,
            'full_name': repo_id,
            'description': last_commit_message,
            'clone_url': remote_url or f'file://{repo_path}',
            'default_branch': current_branch,
            'updated_at': last_commit_date,
            'is_private': True,
            'provider': 'local_git',
            'path': str(repo_path),
            'last_commit': {
                'sha': last_commit_sha,
                'message': last_commit_message,
                'author': last_commit_author,
                'date': last_commit_date,
            }
        }
    
    def get_file_blame(
        self,
        project_key: str,
        repo_slug: str,
        file_path: str,
        branch: str = 'main',
    ) -> List[Dict[str, Any]]:
        """Run `git blame --line-porcelain` and parse it into per-line dicts.

        Each line in the file becomes one dict. We use --line-porcelain (not
        --porcelain) because it repeats author headers on every line, which
        makes the parser straightforward — wiki files are small enough that
        the size penalty is negligible.
        """
        repo_id = f"{project_key}_{repo_slug}"
        repo_path = self._get_repo_path(repo_id)

        try:
            output = self._run_git_command(
                repo_path,
                ['blame', '--line-porcelain', branch, '--', file_path],
            )
        except subprocess.CalledProcessError as e:
            raise ValueError(
                f"Could not blame {file_path} in branch {branch}: {e.stderr}"
            ) from e

        return self._parse_blame_porcelain(output)

    @staticmethod
    def _parse_blame_porcelain(output: str) -> List[Dict[str, Any]]:
        """Parse `git blame --line-porcelain` text into per-line dicts.

        Exposed as a static helper so the wiki space view can reuse it on the
        worktree-manager bare repo without instantiating LocalGitProvider
        (which expects a `base_path` directory layout we don't have there).
        """
        from datetime import datetime, timezone

        result: List[Dict[str, Any]] = []
        # Parser state for the current "block" — git blame --line-porcelain
        # emits one block per line: a header line "<sha> <orig> <final> <n>",
        # then key/value lines, then a tab-prefixed content line.
        current: Dict[str, Any] = {}
        line_no = 0
        for raw in output.split('\n'):
            if not raw:
                continue
            if raw.startswith('\t'):
                # Content of the line — closes the current block.
                line_no += 1
                content = raw[1:]
                author_iso = ''
                ts = current.get('author-time')
                if ts:
                    try:
                        author_iso = datetime.fromtimestamp(
                            int(ts), tz=timezone.utc
                        ).isoformat()
                    except (TypeError, ValueError):
                        author_iso = ''
                email = current.get('author-mail', '').strip('<>')
                if email.lower().startswith('mailto:'):
                    email = email[len('mailto:'):]
                result.append({
                    'line_no': line_no,
                    'content': content,
                    'commit_sha': current.get('sha', ''),
                    'author_name': current.get('author', ''),
                    'author_email': email,
                    'author_date': author_iso,
                    'summary': current.get('summary', ''),
                })
                current = {}
                continue

            parts = raw.split(' ', 3)
            if len(parts) >= 3 and len(parts[0]) == 40 and all(
                c in '0123456789abcdef' for c in parts[0]
            ):
                current = {'sha': parts[0]}
                continue

            key, _, value = raw.partition(' ')
            if key:
                current[key] = value

        return result

    def get_file_content(self, project_key: str, repo_slug: str, file_path: str, branch: str = 'main') -> Dict[str, Any]:
        """
        Get content of a specific file.
        """
        repo_id = f"{project_key}_{repo_slug}"
        repo_path = self._get_repo_path(repo_id)
        
        # Use git show to get file content at specific branch
        try:
            content = self._run_git_command(
                repo_path,
                ['show', f'{branch}:{file_path}']
            )
            
            # Get file SHA
            sha = self._run_git_command(
                repo_path,
                ['rev-parse', f'{branch}:{file_path}']
            )
            
            # Encode content as base64 for consistency with remote providers
            content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            return {
                'content': content_base64,
                'encoding': 'base64',
                'sha': sha,
                'path': file_path,
                'name': Path(file_path).name,
                'size': len(content),
            }
        except subprocess.CalledProcessError as e:
            raise ValueError(f"File not found: {file_path} in branch {branch}") from e
    
    def get_directory_tree(self, project_key: str, repo_slug: str, path: str = '', branch: str = 'main', recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Get directory tree/listing.
        """
        repo_id = f"{project_key}_{repo_slug}"
        repo_path = self._get_repo_path(repo_id)
        
        # Use git ls-tree to list files
        try:
            if recursive:
                output = self._run_git_command(
                    repo_path,
                    ['ls-tree', '-r', '--long', branch, path]
                )
            else:
                output = self._run_git_command(
                    repo_path,
                    ['ls-tree', '--long', branch, path]
                )
            
            entries = []
            for line in output.split('\n'):
                if not line.strip():
                    continue
                
                # Parse ls-tree output: <mode> <type> <sha> <size> <path>
                parts = line.split(maxsplit=4)
                if len(parts) < 5:
                    continue
                
                mode, obj_type, sha, size, file_path = parts
                
                entries.append({
                    'path': file_path,
                    'name': Path(file_path).name,
                    'type': 'file' if obj_type == 'blob' else 'directory',
                    'sha': sha,
                    'size': int(size) if size != '-' else 0,
                    'mode': mode,
                })
            
            return entries
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Path not found: {path} in branch {branch}") from e
    
    def list_pull_requests(self, repo_id: str, state: str = 'open', page: int = 1, per_page: int = 30, reviewer: Optional[str] = None) -> Dict[str, Any]:
        """
        List pull requests - not supported for local repositories.
        """
        return {
            'pull_requests': [],
            'page': page,
            'per_page': per_page,
            'total': 0,
            'is_last_page': True,
            'message': 'Pull requests are not supported for local Git repositories'
        }
    
    def get_pull_request(self, repo_id: str, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request - not supported for local repositories.
        """
        raise NotImplementedError("Pull requests are not supported for local Git repositories")
    
    def get_pull_request_diff(self, repo_id: str, pr_number: int) -> str:
        """
        Get pull request diff - not supported for local repositories.
        """
        raise NotImplementedError("Pull requests are not supported for local Git repositories")
    
    def list_commits(self, repo_id: str, branch: str = 'main', page: int = 1, per_page: int = 30) -> Dict[str, Any]:
        """
        List commits for a repository.
        """
        repo_path = self._get_repo_path(repo_id)
        
        try:
            # Get total commit count
            total_commits_str = self._run_git_command(
                repo_path,
                ['rev-list', '--count', branch]
            )
            total_commits = int(total_commits_str)
            
            # Get commits for this page
            skip = (page - 1) * per_page
            output = self._run_git_command(
                repo_path,
                ['log', branch, f'--skip={skip}', f'--max-count={per_page}',
                 '--format=%H|%an|%ae|%ci|%s']
            )
            
            commits = []
            for line in output.split('\n'):
                if not line.strip():
                    continue
                
                sha, author_name, author_email, date, message = line.split('|', 4)
                
                commits.append({
                    'sha': sha,
                    'message': message,
                    'author': {
                        'name': author_name,
                        'email': author_email,
                    },
                    'date': date,
                    'url': f'file://{repo_path}/commit/{sha}',
                })
            
            return {
                'commits': commits,
                'page': page,
                'per_page': per_page,
                'total': total_commits,
                'is_last_page': (skip + per_page) >= total_commits,
            }
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to list commits for branch {branch}") from e
    
    def create_commit(self, repo_id: str, branch: str, message: str, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Create a new commit with file changes.
        
        Note: This creates commits directly in the local repository.
        Use with caution in production environments.
        """
        repo_path = self._get_repo_path(repo_id)
        
        try:
            # Checkout branch
            self._run_git_command(repo_path, ['checkout', branch])
            
            # Apply file changes
            for file_change in files:
                file_path = file_change['path']
                action = file_change['action']
                full_path = repo_path / file_path
                
                if action == 'delete':
                    if full_path.exists():
                        full_path.unlink()
                        self._run_git_command(repo_path, ['rm', file_path])
                else:  # create or update
                    # Ensure parent directory exists
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write content
                    content = file_change.get('content', '')
                    full_path.write_text(content)
                    
                    # Stage file
                    self._run_git_command(repo_path, ['add', file_path])
            
            # Create commit
            self._run_git_command(repo_path, ['commit', '-m', message])
            
            # Get commit SHA
            sha = self._run_git_command(repo_path, ['rev-parse', 'HEAD'])
            
            return {
                'sha': sha,
                'message': message,
                'branch': branch,
                'files_changed': len(files),
            }
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Failed to create commit: {e}") from e
    
    def normalize_repository_id(self, repo_data: Dict[str, Any]) -> str:
        """
        Normalize repository identifier.
        For local repos, use the relative path.
        """
        return repo_data.get('id', repo_data.get('full_name', ''))
