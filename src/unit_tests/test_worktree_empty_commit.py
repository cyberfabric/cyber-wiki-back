"""
Unit tests for EmptyCommitError raised by GitWorktreeManager.commit_changes_sync
when `git add -A --force` produces nothing to stage.

Covers the noop-success branch in views_draft_changes that catches this error
and clears stale drafts whose content already matches HEAD (typical when a
prior commit succeeded but the response was lost).
"""
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from git_provider.worktree_manager import (
    GitWorktreeManager, GitError, EmptyCommitError,
)


@pytest.fixture
def empty_repo(tmp_path: Path) -> str:
    """Initialise a git repo with one committed file, return repo path."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@x',
           'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@x'}
    subprocess.run(['git', 'init', '-b', 'main'], cwd=repo, check=True, env=env, capture_output=True)
    (repo / 'a.txt').write_text('hello\n')
    subprocess.run(['git', 'add', 'a.txt'], cwd=repo, check=True, env=env)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=repo, check=True, env=env, capture_output=True)
    return str(repo)


class TestEmptyCommitError:
    def test_inherits_from_git_error(self):
        # Catchers that handle GitError must also handle EmptyCommitError so
        # legacy except blocks are not silently bypassed.
        exc = EmptyCommitError()
        assert isinstance(exc, GitError)
        assert exc.returncode == 1

    def test_default_message(self):
        exc = EmptyCommitError()
        assert 'No changes to commit' in exc.message

    def test_commit_changes_sync_raises_empty_commit_error(self, empty_repo: str):
        manager = GitWorktreeManager()
        # No file changes — `git add -A --force` stages nothing, the diff
        # check trips, and we surface EmptyCommitError instead of a confusing
        # generic GitError on `git commit`.
        with pytest.raises(EmptyCommitError):
            manager.commit_changes_sync(
                worktree_path=empty_repo,
                message='noop',
                author_name='Author',
                author_email='author@example.com',
            )

    def test_head_sha_sync_returns_full_sha(self, empty_repo: str):
        manager = GitWorktreeManager()
        sha = manager.head_sha_sync(empty_repo)
        assert len(sha) == 40
        assert all(c in '0123456789abcdef' for c in sha)

    def test_real_change_succeeds(self, empty_repo: str):
        # Sanity check: when there *is* a change, commit_changes_sync produces
        # a sha (and does not raise EmptyCommitError).
        Path(empty_repo, 'a.txt').write_text('updated\n')
        manager = GitWorktreeManager()
        sha = manager.commit_changes_sync(
            worktree_path=empty_repo,
            message='update',
            author_name='Author',
            author_email='author@example.com',
        )
        assert len(sha) == 40
