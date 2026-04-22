"""
Git Worktree Manager for Edit Workflow.

This module manages bare repositories and git worktrees for the edit workflow.
It provides efficient, isolated workspaces for each edit session without
requiring full repository clones for each operation.

Architecture:
- One bare repo per space (cached in DOCLAB_GIT_CACHE_DIR)
- Temporary worktrees created per edit session
- Worktrees are cleaned up after PR creation
"""
import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any

from django.conf import settings

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Exception raised for git operation failures."""

    def __init__(self, message: str, returncode: int = 1, stderr: str = ''):
        self.message = message
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(message)


class RebaseConflictError(Exception):
    """Raised when a rebase produces merge conflicts."""

    def __init__(self, conflicting_files: List[str]):
        self.conflicting_files = conflicting_files
        super().__init__(f"Rebase conflict in {len(conflicting_files)} file(s)")


class GitWorktreeManager:
    """
    Manages bare repositories and worktrees for edit sessions.
    
    This class handles:
    - Caching bare repos for each space's edit fork
    - Creating/removing worktrees for edit sessions
    - Executing git commands with proper SSH configuration
    """
    
    def __init__(
        self,
        cache_dir: Optional[str] = None,
        worktree_dir: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
    ):
        """
        Initialize the worktree manager.
        
        Args:
            cache_dir: Directory for bare repo cache (default: from settings)
            worktree_dir: Directory for temporary worktrees (default: from settings)
            ssh_key_path: Path to SSH private key (default: from settings)
        """
        self.cache_dir = cache_dir or getattr(
            settings, 'DOCLAB_GIT_CACHE_DIR', '/data/doclab/git-cache'
        )
        self.worktree_dir = worktree_dir or getattr(
            settings, 'DOCLAB_GIT_WORKTREE_DIR', '/tmp/doclab-worktrees'
        )
        self.ssh_key_path = ssh_key_path or getattr(
            settings, 'DOCLAB_GIT_SSH_KEY', None
        )
        
        # Ensure directories exist
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.worktree_dir, exist_ok=True)
    
    def _get_git_env(self) -> Dict[str, str]:
        """Get environment variables for git commands."""
        env = os.environ.copy()
        
        if self.ssh_key_path and os.path.exists(self.ssh_key_path):
            env['GIT_SSH_COMMAND'] = (
                f'ssh -i {self.ssh_key_path} '
                f'-o StrictHostKeyChecking=no '
                f'-o UserKnownHostsFile=/dev/null'
            )
        
        return env
    
    async def _run_git(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        timeout: int = 300,
    ) -> str:
        """
        Run a git command asynchronously.
        
        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory
            timeout: Command timeout in seconds
            
        Returns:
            Command stdout
            
        Raises:
            GitError: If command fails
        """
        cmd = ['git'] + args
        logger.debug(f"Running git command: {' '.join(cmd)} in {cwd}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                env=self._get_git_env(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()
            
            if process.returncode != 0:
                logger.error(f"Git command failed: {stderr_str}")
                raise GitError(
                    f"Git command failed: {' '.join(args)}",
                    returncode=process.returncode,
                    stderr=stderr_str
                )
            
            if stderr_str:
                logger.debug(f"Git stderr: {stderr_str}")
            
            return stdout_str
            
        except asyncio.TimeoutError:
            raise GitError(f"Git command timed out after {timeout}s: {' '.join(args)}")
    
    def _run_git_sync(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        timeout: int = 300,
    ) -> str:
        """
        Run a git command synchronously.
        
        Args:
            args: Git command arguments (without 'git' prefix)
            cwd: Working directory
            timeout: Command timeout in seconds
            
        Returns:
            Command stdout
            
        Raises:
            GitError: If command fails
        """
        import subprocess
        
        cmd = ['git'] + args
        logger.debug(f"Running git command (sync): {' '.join(cmd)} in {cwd}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                env=self._get_git_env(),
                capture_output=True,
                timeout=timeout,
            )
            
            stdout_str = result.stdout.decode('utf-8', errors='replace').strip()
            stderr_str = result.stderr.decode('utf-8', errors='replace').strip()
            
            if result.returncode != 0:
                logger.error(f"Git command failed: {stderr_str}")
                raise GitError(
                    f"Git command failed: {' '.join(args)}",
                    returncode=result.returncode,
                    stderr=stderr_str
                )
            
            if stderr_str:
                logger.debug(f"Git stderr: {stderr_str}")
            
            return stdout_str
            
        except subprocess.TimeoutExpired:
            raise GitError(f"Git command timed out after {timeout}s: {' '.join(args)}")
    
    def get_bare_repo_path(self, space_id: str) -> str:
        """Get path to cached bare repo for a space."""
        return os.path.join(self.cache_dir, 'spaces', space_id, 'edit-fork.git')
    
    def get_worktree_path(self, session_id: str) -> str:
        """Get path to worktree for an edit session."""
        return os.path.join(self.worktree_dir, session_id)
    
    async def ensure_bare_repo(self, space_id: str, ssh_url: str) -> str:
        """
        Ensure bare repo exists and is up-to-date.
        
        Args:
            space_id: Space UUID
            ssh_url: SSH clone URL for the edit fork
            
        Returns:
            Path to the bare repo
        """
        bare_path = self.get_bare_repo_path(space_id)
        
        if not os.path.exists(bare_path):
            # First time: clone as bare mirror
            logger.info(f"Cloning bare repo for space {space_id}")
            os.makedirs(os.path.dirname(bare_path), exist_ok=True)
            
            await self._run_git([
                'clone', '--bare', '--mirror',
                ssh_url,
                bare_path
            ])
            logger.info(f"Bare repo cloned to {bare_path}")
        else:
            # Update existing bare repo
            logger.info(f"Fetching updates for space {space_id}")
            await self._run_git(
                ['fetch', '--all', '--prune'],
                cwd=bare_path
            )
        
        return bare_path
    
    def ensure_bare_repo_sync(self, space_id: str, ssh_url: str) -> str:
        """Synchronous version of ensure_bare_repo."""
        bare_path = self.get_bare_repo_path(space_id)
        
        if not os.path.exists(bare_path):
            logger.info(f"Cloning bare repo for space {space_id}")
            os.makedirs(os.path.dirname(bare_path), exist_ok=True)
            
            self._run_git_sync([
                'clone', '--bare', '--mirror',
                ssh_url,
                bare_path
            ])
            logger.info(f"Bare repo cloned to {bare_path}")
        else:
            logger.info(f"Fetching updates for space {space_id}")
            self._run_git_sync(
                ['fetch', '--all', '--prune'],
                cwd=bare_path
            )
        
        return bare_path
    
    async def create_worktree(
        self,
        space_id: str,
        session_id: str,
        branch_name: str,
        base_branch: str = 'master',
        ssh_url: Optional[str] = None,
    ) -> str:
        """
        Create a worktree for an edit session.
        
        Args:
            space_id: Space UUID
            session_id: Edit session UUID
            branch_name: Name for the new branch
            base_branch: Branch to base changes on
            ssh_url: SSH URL (required if bare repo doesn't exist)
            
        Returns:
            Path to the worktree
        """
        bare_path = self.get_bare_repo_path(space_id)
        worktree_path = self.get_worktree_path(session_id)
        
        # Ensure bare repo exists
        if not os.path.exists(bare_path):
            if not ssh_url:
                raise GitError(f"Bare repo not found and no SSH URL provided")
            await self.ensure_bare_repo(space_id, ssh_url)
        else:
            # Fetch latest changes
            await self._run_git(['fetch', '--all'], cwd=bare_path)
        
        # Remove existing worktree if it exists (cleanup from failed attempt)
        if os.path.exists(worktree_path):
            logger.warning(f"Removing existing worktree at {worktree_path}")
            await self._run_git(
                ['worktree', 'remove', '--force', worktree_path],
                cwd=bare_path
            )
        
        # Create worktree with new branch
        logger.info(f"Creating worktree for session {session_id}")
        await self._run_git([
            'worktree', 'add',
            '-b', branch_name,
            worktree_path,
            f'origin/{base_branch}'
        ], cwd=bare_path)
        
        logger.info(f"Worktree created at {worktree_path}")
        return worktree_path
    
    def create_worktree_sync(
        self,
        space_id: str,
        session_id: str,
        branch_name: str,
        base_branch: str = 'master',
        ssh_url: Optional[str] = None,
        local_repo_path: Optional[str] = None,
    ) -> str:
        """
        Synchronous version of create_worktree.
        
        Args:
            space_id: Space UUID
            session_id: Session/branch UUID for worktree
            branch_name: Name for the branch
            base_branch: Base branch to create from
            ssh_url: SSH URL to clone from (if no local path)
            local_repo_path: Local path to existing repo (takes precedence over ssh_url)
        """
        worktree_path = self.get_worktree_path(session_id)
        
        # Determine the repo path to use
        if local_repo_path and os.path.exists(local_repo_path):
            # Use local repo directly (for development)
            repo_path = local_repo_path
            logger.info(f"Using local repo at {repo_path}")
            
            # Fetch latest (local repos may have remotes configured)
            try:
                self._run_git_sync(['fetch', '--all'], cwd=repo_path)
            except GitError:
                logger.debug("Fetch failed (may not have remotes), continuing...")
        else:
            # Use bare repo cache with SSH clone
            repo_path = self.get_bare_repo_path(space_id)
            
            if not os.path.exists(repo_path):
                if not ssh_url:
                    raise GitError(f"Bare repo not found and no SSH URL provided")
                self.ensure_bare_repo_sync(space_id, ssh_url)
            else:
                self._run_git_sync(['fetch', '--all'], cwd=repo_path)
        
        # Remove existing worktree if it exists
        if os.path.exists(worktree_path):
            logger.warning(f"Removing existing worktree at {worktree_path}")
            try:
                self._run_git_sync(
                    ['worktree', 'remove', '--force', worktree_path],
                    cwd=repo_path
                )
            except GitError:
                # Fallback: just delete the directory
                shutil.rmtree(worktree_path, ignore_errors=True)
        
        # Check if branch already exists (locally or on remote)
        branch_exists = False
        try:
            self._run_git_sync(['rev-parse', '--verify', branch_name], cwd=repo_path)
            branch_exists = True
            logger.info(f"Branch {branch_name} exists locally")
        except GitError:
            # Check if it exists on remote
            try:
                self._run_git_sync(['rev-parse', '--verify', f'origin/{branch_name}'], cwd=repo_path)
                branch_exists = True
                logger.info(f"Branch {branch_name} exists on remote")
            except GitError:
                pass
        
        logger.info(f"Creating worktree for session {session_id}")
        
        if branch_exists:
            # Use existing branch
            self._run_git_sync([
                'worktree', 'add',
                worktree_path,
                branch_name
            ], cwd=repo_path)
        else:
            # Create new branch from base
            # For local repos, base_branch might not have origin/ prefix
            base_ref = f'origin/{base_branch}' if not local_repo_path else base_branch
            try:
                self._run_git_sync([
                    'worktree', 'add',
                    '-b', branch_name,
                    worktree_path,
                    base_ref
                ], cwd=repo_path)
            except GitError:
                # Try without origin/ prefix
                self._run_git_sync([
                    'worktree', 'add',
                    '-b', branch_name,
                    worktree_path,
                    base_branch
                ], cwd=repo_path)
        
        logger.info(f"Worktree created at {worktree_path}")
        return worktree_path
    
    def apply_changes(
        self,
        worktree_path: str,
        changes: List[Dict[str, Any]],
    ) -> None:
        """
        Apply file changes to a worktree.
        
        Args:
            worktree_path: Path to the worktree
            changes: List of changes from EditSession.pending_changes
        """
        for change in changes:
            file_path = os.path.join(worktree_path, change['file_path'])
            change_type = change.get('change_type', 'modify')
            
            if change_type == 'delete':
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted: {change['file_path']}")
            else:
                # Create parent directories if needed
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                content = change.get('modified_content', '')
                # Ensure text files end with a newline (POSIX standard).
                # Prevents spurious last-line diffs when the editor strips the
                # trailing newline that was present in the original file.
                if content and not content.endswith('\n'):
                    content += '\n'
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.debug(f"Written: {change['file_path']}")
    
    async def commit_changes(
        self,
        worktree_path: str,
        message: str,
        author_name: str,
        author_email: str,
        description: str = '',
    ) -> str:
        """
        Stage and commit changes in a worktree.
        
        Args:
            worktree_path: Path to the worktree
            message: Commit message (title)
            author_name: Git author name
            author_email: Git author email
            description: Extended commit description
            
        Returns:
            Commit SHA
        """
        # Stage all changes
        await self._run_git(['add', '-A'], cwd=worktree_path)
        
        # Build commit command
        author = f"{author_name} <{author_email}>"
        commit_args = [
            'commit',
            f'--author={author}',
            '-m', message,
        ]
        
        if description:
            commit_args.extend(['-m', description])
        
        await self._run_git(commit_args, cwd=worktree_path)
        
        # Get commit SHA
        sha = await self._run_git(['rev-parse', 'HEAD'], cwd=worktree_path)
        logger.info(f"Created commit {sha[:8]} by {author}")
        
        return sha
    
    def commit_changes_sync(
        self,
        worktree_path: str,
        message: str,
        author_name: str,
        author_email: str,
        description: str = '',
    ) -> str:
        """Synchronous version of commit_changes."""
        self._run_git_sync(['add', '-A'], cwd=worktree_path)
        
        author = f"{author_name} <{author_email}>"
        commit_args = [
            'commit',
            f'--author={author}',
            '-m', message,
        ]
        
        if description:
            commit_args.extend(['-m', description])
        
        self._run_git_sync(commit_args, cwd=worktree_path)
        
        sha = self._run_git_sync(['rev-parse', 'HEAD'], cwd=worktree_path)
        logger.info(f"Created commit {sha[:8]} by {author}")
        
        return sha
    
    async def push_branch(
        self,
        worktree_path: str,
        branch_name: str,
        force: bool = False,
    ) -> None:
        """
        Push branch to remote.
        
        Args:
            worktree_path: Path to the worktree
            branch_name: Branch name to push
            force: Force push (for amending commits)
        """
        push_args = ['push', 'origin', branch_name]
        if force:
            push_args.insert(1, '--force')
        
        await self._run_git(push_args, cwd=worktree_path, timeout=60)
        logger.info(f"Pushed branch {branch_name}")
    
    def push_branch_sync(
        self,
        worktree_path: str,
        branch_name: str,
        force: bool = False,
    ) -> None:
        """Synchronous version of push_branch."""
        push_args = ['push', 'origin', branch_name]
        if force:
            push_args.insert(1, '--force')
        
        self._run_git_sync(push_args, cwd=worktree_path, timeout=60)
        logger.info(f"Pushed branch {branch_name}")
    
    async def cleanup_worktree(
        self,
        space_id: str,
        session_id: str,
    ) -> None:
        """
        Remove a worktree after PR creation.
        
        Args:
            space_id: Space UUID
            session_id: Edit session UUID
        """
        bare_path = self.get_bare_repo_path(space_id)
        worktree_path = self.get_worktree_path(session_id)
        
        if os.path.exists(worktree_path):
            try:
                await self._run_git(
                    ['worktree', 'remove', '--force', worktree_path],
                    cwd=bare_path
                )
                logger.info(f"Removed worktree {worktree_path}")
            except GitError as e:
                # Fallback: just delete the directory
                logger.warning(f"Git worktree remove failed, using rmtree: {e}")
                shutil.rmtree(worktree_path, ignore_errors=True)
    
    def cleanup_worktree_sync(
        self,
        space_id: str,
        session_id: str,
        repo_path: Optional[str] = None,
    ) -> None:
        """Synchronous version of cleanup_worktree."""
        bare_path = repo_path if (repo_path and os.path.exists(repo_path)) else self.get_bare_repo_path(space_id)
        worktree_path = self.get_worktree_path(session_id)

        if os.path.exists(worktree_path):
            try:
                self._run_git_sync(
                    ['worktree', 'remove', '--force', worktree_path],
                    cwd=bare_path
                )
                logger.info(f"Removed worktree {worktree_path}")
            except GitError as e:
                logger.warning(f"Git worktree remove failed, using rmtree: {e}")
                shutil.rmtree(worktree_path, ignore_errors=True)
    
    async def delete_remote_branch(
        self,
        space_id: str,
        branch_name: str,
    ) -> None:
        """
        Delete a branch from the remote (after PR merged/closed).
        
        Args:
            space_id: Space UUID
            branch_name: Branch name to delete
        """
        bare_path = self.get_bare_repo_path(space_id)
        
        if os.path.exists(bare_path):
            try:
                await self._run_git(
                    ['push', 'origin', '--delete', branch_name],
                    cwd=bare_path
                )
                logger.info(f"Deleted remote branch {branch_name}")
            except GitError as e:
                logger.warning(f"Failed to delete remote branch {branch_name}: {e}")
    
    def delete_remote_branch_sync(
        self,
        space_id: str,
        branch_name: str,
    ) -> None:
        """Synchronous version of delete_remote_branch."""
        bare_path = self.get_bare_repo_path(space_id)
        
        if os.path.exists(bare_path):
            try:
                self._run_git_sync(
                    ['push', 'origin', '--delete', branch_name],
                    cwd=bare_path
                )
                logger.info(f"Deleted remote branch {branch_name}")
            except GitError as e:
                logger.warning(f"Failed to delete remote branch {branch_name}: {e}")
    
    def cleanup_stale_worktrees(self, max_age_hours: int = 24) -> int:
        """
        Clean up stale worktrees older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of worktrees cleaned up
        """
        import time
        
        cleaned = 0
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        
        if not os.path.exists(self.worktree_dir):
            return 0
        
        for entry in os.scandir(self.worktree_dir):
            if entry.is_dir():
                try:
                    age = now - entry.stat().st_mtime
                    if age > max_age_seconds:
                        logger.info(f"Cleaning up stale worktree: {entry.path}")
                        shutil.rmtree(entry.path, ignore_errors=True)
                        cleaned += 1
                except OSError as e:
                    logger.warning(f"Error checking worktree {entry.path}: {e}")
        
        return cleaned


    def get_file_diff_sync(
        self,
        repo_path: str,
        branch_name: str,
        base_branch: str,
        file_path: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get diff for a specific file between branch and base.
        
        Args:
            repo_path: Path to the git repo (local or bare)
            branch_name: The branch with changes
            base_branch: The base branch to compare against
            file_path: Path to the file within the repo
            
        Returns:
            Dict with hunks, additions, deletions or None if no diff
        """
        try:
            # Get the diff output
            diff_output = self._run_git_sync([
                'diff',
                f'{base_branch}...{branch_name}',
                '--',
                file_path
            ], cwd=repo_path)
            
            if not diff_output:
                return None
            
            # Parse the diff into hunks
            hunks = self._parse_diff_output(diff_output)
            
            # Count additions and deletions
            additions = 0
            deletions = 0
            for hunk in hunks:
                for line in hunk.get('lines', []):
                    if line.startswith('+'):
                        additions += 1
                    elif line.startswith('-'):
                        deletions += 1
            
            return {
                'hunks': hunks,
                'additions': additions,
                'deletions': deletions,
                'raw_diff': diff_output,
            }
            
        except GitError as e:
            logger.debug(f"No diff for {file_path}: {e.message}")
            return None
    
    def _parse_diff_output(self, diff_output: str) -> List[Dict[str, Any]]:
        """Parse git diff output into structured hunks."""
        import re
        
        hunks = []
        current_hunk = None
        
        for line in diff_output.split('\n'):
            if line.startswith('@@'):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                if current_hunk:
                    hunks.append(current_hunk)
                
                # Extract line numbers from hunk header
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2) or 1)
                    new_start = int(match.group(3))
                    new_count = int(match.group(4) or 1)
                    
                    current_hunk = {
                        'old_start': old_start,
                        'old_count': old_count,
                        'new_start': new_start,
                        'new_count': new_count,
                        'lines': [],  # Array of lines, not dict
                    }
            elif current_hunk is not None:
                if line.startswith('+++') or line.startswith('---'):
                    # Skip file headers
                    continue
                elif line.startswith('\\'):
                    # Skip "\ No newline at end of file"
                    continue
                else:
                    # Add context, addition, or deletion lines
                    current_hunk['lines'].append(line)
        
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
    
    def list_changed_files_sync(
        self,
        repo_path: str,
        branch_name: str,
        base_branch: str,
    ) -> List[str]:
        """List files changed between branch and base."""
        try:
            output = self._run_git_sync([
                'diff', '--name-only', f'{base_branch}...{branch_name}'
            ], cwd=repo_path)
            return [f.strip() for f in output.split('\n') if f.strip()] if output else []
        except GitError as e:
            logger.debug(f"Error listing changed files: {e.message}")
            return []

    def rebase_onto_base_sync(self, worktree_path: str, base_branch: str) -> None:
        """
        Rebase the current branch onto origin/{base_branch}.

        Raises:
            RebaseConflictError: if conflicts are detected — worktree is left in
                                 mid-rebase state; caller must abort or resolve.
        """
        try:
            self._run_git_sync(
                ['rebase', f'origin/{base_branch}'],
                cwd=worktree_path,
            )
        except GitError as e:
            # Rebase failed — collect conflicting files then abort
            conflict_files = self._get_conflicting_files_sync(worktree_path)
            try:
                self._run_git_sync(['rebase', '--abort'], cwd=worktree_path)
            except GitError:
                pass
            raise RebaseConflictError(conflict_files) from e

    def _get_conflicting_files_sync(self, worktree_path: str) -> List[str]:
        """Return list of files with unresolved merge conflicts."""
        try:
            output = self._run_git_sync(
                ['diff', '--name-only', '--diff-filter=U'],
                cwd=worktree_path,
            )
            return [f.strip() for f in output.split('\n') if f.strip()]
        except GitError:
            return []

    def soft_reset_to_base_sync(self, worktree_path: str, base_branch: str) -> List[str]:
        """
        Soft-reset the branch to origin/{base_branch}, keeping all file changes
        in the working tree.

        Returns:
            List of file paths that were changed (and are now unstaged).
        """
        # Collect changed files before reset so caller can recreate drafts
        changed = self.list_changed_files_sync(
            worktree_path,
            branch_name='HEAD',
            base_branch=f'origin/{base_branch}',
        )
        self._run_git_sync(
            ['reset', '--soft', f'origin/{base_branch}'],
            cwd=worktree_path,
        )
        logger.info(f"[Worktree] Soft-reset to origin/{base_branch}, {len(changed)} files kept")
        return changed

    def hard_reset_to_base_sync(self, worktree_path: str, base_branch: str) -> None:
        """Hard-reset the branch to origin/{base_branch}, discarding all commits."""
        self._run_git_sync(
            ['reset', '--hard', f'origin/{base_branch}'],
            cwd=worktree_path,
        )
        logger.info(f"[Worktree] Hard-reset to origin/{base_branch}")

    def read_file_sync(self, worktree_path: str, file_path: str) -> Optional[str]:
        """Read a file from the worktree. Returns None if not found."""
        full_path = os.path.join(worktree_path, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as fh:
                return fh.read()
        except (FileNotFoundError, OSError):
            return None

    def read_file_at_base_sync(self, worktree_path: str, file_path: str, base_branch: str) -> Optional[str]:
        """Read a file as it exists at origin/{base_branch}. Returns None if not found."""
        try:
            return self._run_git_sync(
                ['show', f'origin/{base_branch}:{file_path}'],
                cwd=worktree_path,
            )
        except GitError:
            return None

    def count_commits_ahead_sync(self, worktree_path: str, base_branch: str) -> int:
        """Return number of commits on the branch that are not in base_branch."""
        try:
            output = self._run_git_sync(
                ['rev-list', '--count', f'origin/{base_branch}..HEAD'],
                cwd=worktree_path,
            )
            return int(output.strip()) if output.strip() else 0
        except (GitError, ValueError):
            return 0


# Singleton instance
_worktree_manager: Optional[GitWorktreeManager] = None


def get_worktree_manager() -> GitWorktreeManager:
    """Get or create the singleton worktree manager instance."""
    global _worktree_manager
    if _worktree_manager is None:
        _worktree_manager = GitWorktreeManager()
    return _worktree_manager
