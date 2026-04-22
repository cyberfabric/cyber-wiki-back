"""
Views for UserBranch management.

Endpoints for the SpaceWorkspaceBar:
  GET  /user-branch/status/         – current branch + draft state for a space
  POST /user-branch/create-pr/      – create PR from branch on the git provider
  POST /user-branch/discard/        – hard-reset branch (lose all commits)
  POST /user-branch/unstage/        – soft-reset → recreate commits as draft edits
  POST /user-branch/rebase/         – explicit rebase (e.g. after resolving conflict)
"""
import logging
import os

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from git_provider.factory import GitProviderFactory
from git_provider.worktree_manager import GitWorktreeManager, GitError, RebaseConflictError
from service_tokens.models import ServiceToken
from users.permissions import IsEditorOrAbove
from .models import Space, UserBranch, UserDraftChange

logger = logging.getLogger(__name__)


def _serialize_branch(branch: UserBranch, files: list | None = None) -> dict:
    files = files or []
    return {
        'id': str(branch.id),
        'branch_name': branch.branch_name,
        'base_branch': branch.base_branch,
        'status': branch.status,
        'last_commit_sha': branch.last_commit_sha,
        'pr_id': branch.pr_id,
        'pr_url': branch.pr_url,
        'conflict_files': branch.conflict_files or [],
        'files_count': len(files),
        'files': files,
        'created_at': branch.created_at.isoformat(),
        'updated_at': branch.updated_at.isoformat(),
    }


def _get_branch_files(branch: UserBranch, space: Space) -> list:
    """Return list of file paths changed in the branch vs base ([] on any error)."""
    try:
        manager = GitWorktreeManager()
        if space.edit_fork_local_path:
            repo_path = space.edit_fork_local_path
        else:
            repo_path = manager.get_bare_repo_path(str(space.id))

        if not os.path.exists(repo_path):
            return []

        return manager.list_changed_files_sync(
            repo_path, branch.branch_name, f'origin/{branch.base_branch}'
        )
    except Exception:
        return []


def _repo_path(manager: GitWorktreeManager, space: Space) -> str:
    """Return the correct git repo path for a space (local clone or bare cache)."""
    if space.edit_fork_local_path and os.path.exists(space.edit_fork_local_path):
        return space.edit_fork_local_path
    return manager.get_bare_repo_path(str(space.id))


def _open_worktree(manager: GitWorktreeManager, space: Space, branch: UserBranch) -> str:
    """Create (or reopen) a worktree for the branch. Fetches latest from remote."""
    return manager.create_worktree_sync(
        space_id=str(space.id),
        session_id=str(branch.id),
        branch_name=branch.branch_name,
        base_branch=branch.base_branch,
        ssh_url=space.edit_fork_ssh_url,
        local_repo_path=space.edit_fork_local_path,
    )


class UserBranchViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsEditorOrAbove]

    # ── Status ────────────────────────────────────────────────────────────────

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Return workspace state for a space:
          - draft edits (UserDraftChange)
          - staged branch (UserBranch)
          - conflict files
        """
        space_id = request.query_params.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        draft_count = UserDraftChange.objects.filter(
            user=request.user, space=space
        ).count()

        branch = UserBranch.objects.filter(
            user=request.user,
            space=space,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        ).first()

        branch_data = None
        if branch:
            branch_files = _get_branch_files(branch, space)
            branch_data = _serialize_branch(branch, branch_files)

        return Response({
            'draft_count': draft_count,
            'branch': branch_data,
            'edit_enabled': space.edit_enabled,
        })

    # ── Create PR ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='create-pr')
    def create_pr(self, request):
        """
        Create a pull request from the user's branch.

        Body: { space_id, title?, description? }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        if not space.edit_enabled:
            return Response({'error': 'Edit fork not configured'}, status=status.HTTP_400_BAD_REQUEST)

        branch = UserBranch.objects.filter(
            user=request.user, space=space, status=UserBranch.Status.ACTIVE
        ).first()

        if not branch or not branch.last_commit_sha:
            return Response(
                {'error': 'No committed changes found. Commit changes first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service_token = ServiceToken.objects.filter(
            user=request.user, service_type=space.git_provider
        ).first()

        if not service_token:
            return Response(
                {'error': f'No {space.git_provider} token found'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = GitProviderFactory.create_from_service_token(service_token)

        title = request.data.get('title') or f"Changes by {request.user.get_full_name() or request.user.username}"
        description = request.data.get('description', '')

        try:
            result = provider.create_pull_request(
                from_project=space.edit_fork_project_key,
                from_repo=space.edit_fork_repo_slug,
                from_branch=branch.branch_name,
                to_project=space.git_project_key,
                to_repo=space.git_repository_id,
                to_branch=branch.base_branch,
                title=title,
                description=description,
            )
        except Exception as e:
            logger.error(f"[UserBranch] create_pr failed: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        branch.pr_id = result.get('id')
        branch.pr_url = result.get('url')
        branch.status = UserBranch.Status.PR_OPEN
        branch.save(update_fields=['pr_id', 'pr_url', 'status'])

        logger.info(f"[UserBranch] Created PR #{branch.pr_id} for {request.user.username}")

        return Response({
            'pr_id': branch.pr_id,
            'pr_url': branch.pr_url,
            'branch_name': branch.branch_name,
        })

    # ── Discard (hard reset) ───────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def discard(self, request):
        """
        Discard all commits on the branch (hard reset to base).
        The branch record is deleted; any draft edits are untouched.

        Body: { space_id }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        branch = UserBranch.objects.filter(
            user=request.user, space=space,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        ).first()

        if not branch:
            return Response({'error': 'No active branch found'}, status=status.HTTP_404_NOT_FOUND)

        manager = GitWorktreeManager()
        rp = _repo_path(manager, space)
        try:
            worktree_path = _open_worktree(manager, space, branch)
            manager.hard_reset_to_base_sync(worktree_path, branch.base_branch)
            # Push the reset so remote branch is also cleaned
            manager.push_branch_sync(worktree_path, branch.branch_name, force=True)
        except GitError as e:
            logger.warning(f"[UserBranch] discard git error (continuing): {e.message}")
        finally:
            try:
                manager.cleanup_worktree_sync(str(space.id), str(branch.id), repo_path=rp)
            except Exception:
                pass

        branch.status = UserBranch.Status.ABANDONED
        branch.last_commit_sha = None
        branch.conflict_files = []
        branch.save(update_fields=['status', 'last_commit_sha', 'conflict_files'])

        logger.info(f"[UserBranch] Discarded branch {branch.branch_name} for {request.user.username}")

        return Response({'discarded': True, 'branch_name': branch.branch_name})

    # ── Unstage (soft reset → drafts) ─────────────────────────────────────

    @action(detail=False, methods=['post'])
    def unstage(self, request):
        """
        Soft-reset the branch to base, converting all committed changes back
        into UserDraftChange records so they appear as editable draft enrichments.

        Body: { space_id }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        branch = UserBranch.objects.filter(
            user=request.user, space=space,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        ).first()

        if not branch:
            return Response({'error': 'No active branch found'}, status=status.HTTP_404_NOT_FOUND)

        manager = GitWorktreeManager()
        rp = _repo_path(manager, space)
        unstaged_files = []
        try:
            worktree_path = _open_worktree(manager, space, branch)

            # Soft-reset: undo commits, keep changes in working tree
            changed_files = manager.soft_reset_to_base_sync(worktree_path, branch.base_branch)

            # Recreate a UserDraftChange for each changed file
            for file_path in changed_files:
                modified_content = manager.read_file_sync(worktree_path, file_path)
                if modified_content is None:
                    # File was deleted in the commit
                    change_type = 'delete'
                    modified_content = ''
                else:
                    change_type = 'modify'

                # Read original content from base branch so the diff is correct
                original_content = manager.read_file_at_base_sync(
                    worktree_path, file_path, branch.base_branch
                ) or ''

                # Normalize trailing newlines so split('\n') doesn't produce a
                # spurious trailing empty element, which renders as an extra diff line.
                original_content = original_content.rstrip('\n')
                if modified_content:
                    modified_content = modified_content.rstrip('\n')

                UserDraftChange.objects.update_or_create(
                    user=request.user,
                    space=space,
                    file_path=file_path,
                    defaults={
                        'original_content': original_content,
                        'modified_content': modified_content,
                        'change_type': change_type,
                        'description': f'Unstaged from {branch.branch_name}',
                    },
                )
                unstaged_files.append(file_path)

            # Force-push the reset branch so remote matches
            manager.push_branch_sync(worktree_path, branch.branch_name, force=True)

        except GitError as e:
            logger.error(f"[UserBranch] unstage git error: {e.message}", exc_info=True)
            return Response({'error': e.message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            try:
                manager.cleanup_worktree_sync(str(space.id), str(branch.id), repo_path=rp)
            except Exception:
                pass

        branch.status = UserBranch.Status.ABANDONED
        branch.last_commit_sha = None
        branch.conflict_files = []
        branch.save(update_fields=['status', 'last_commit_sha', 'conflict_files'])

        logger.info(
            f"[UserBranch] Unstaged {len(unstaged_files)} files from "
            f"{branch.branch_name} for {request.user.username}"
        )

        return Response({'unstaged_files': unstaged_files, 'branch_name': branch.branch_name})

    # ── Rebase ────────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def rebase(self, request):
        """
        Explicitly rebase the branch onto the latest base branch.
        Returns 409 with conflict_files if conflicts are detected.

        Body: { space_id }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        branch = UserBranch.objects.filter(
            user=request.user, space=space, status=UserBranch.Status.ACTIVE
        ).first()

        if not branch:
            return Response({'error': 'No active branch found'}, status=status.HTTP_404_NOT_FOUND)

        manager = GitWorktreeManager()
        rp = _repo_path(manager, space)
        try:
            worktree_path = _open_worktree(manager, space, branch)
            manager.rebase_onto_base_sync(worktree_path, branch.base_branch)
            manager.push_branch_sync(worktree_path, branch.branch_name, force=True)
            branch.conflict_files = []
            branch.save(update_fields=['conflict_files'])
            manager.cleanup_worktree_sync(str(space.id), str(branch.id), repo_path=rp)
            return Response({'rebased': True, 'branch_name': branch.branch_name})

        except RebaseConflictError as exc:
            branch.conflict_files = exc.conflicting_files
            branch.save(update_fields=['conflict_files'])
            try:
                manager.cleanup_worktree_sync(str(space.id), str(branch.id), repo_path=rp)
            except Exception:
                pass
            return Response(
                {'error': 'rebase_conflict', 'conflict_files': exc.conflicting_files},
                status=status.HTTP_409_CONFLICT,
            )
        except GitError as e:
            logger.error(f"[UserBranch] rebase error: {e.message}", exc_info=True)
            try:
                manager.cleanup_worktree_sync(str(space.id), str(branch.id), repo_path=rp)
            except Exception:
                pass
            return Response({'error': e.message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
