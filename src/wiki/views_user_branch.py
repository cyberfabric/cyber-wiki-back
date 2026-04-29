"""
Views for UserBranch (task) management.

Each "task" is a named UserBranch that maps 1:1 to a git branch.
Users can have multiple tasks per space, switch between them, and
commit/PR independently for each task.

Endpoints:
  GET  /user-branch/workspace/    – all tasks + draft summary for SpaceWorkspaceBar
  POST /user-branch/create-task/  – create a new named task (branch)
  POST /user-branch/select-task/  – switch the selected task
  POST /user-branch/create-pr/    – create/update PR for a task
  POST /user-branch/discard/      – hard-reset a task branch
  POST /user-branch/unstage/      – soft-reset → recreate commits as draft edits
  POST /user-branch/rebase/       – explicit rebase onto upstream
"""
import logging
import os
import re
from typing import Optional

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from git_provider.factory import GitProviderFactory
from git_provider.worktree_manager import GitWorktreeManager, GitError, RebaseConflictError
from service_tokens.models import ServiceToken
from users.models import APIResponseCache
from users.permissions import IsEditorOrAbove
from .models import Space, UserBranch, UserDraftChange
from . import git_ops_log

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _derive_upstream_ssh_url(space: Space) -> Optional[str]:
    fork_url = space.edit_fork_ssh_url
    if not fork_url or not space.git_project_key or not space.git_repository_id:
        return None
    match = re.match(r'^(ssh://[^/]+)/[^/]+/[^/]+?(?:\.git)?$', fork_url)
    if match:
        return f"{match.group(1)}/{space.git_project_key}/{space.git_repository_id}.git"
    return None


def _repo_path(manager: GitWorktreeManager, space: Space) -> str:
    if space.edit_fork_local_path and os.path.exists(space.edit_fork_local_path):
        return space.edit_fork_local_path
    return manager.get_bare_repo_path(str(space.id))


def _get_branch_files(branch: UserBranch, space: Space) -> list:
    """Return list of file paths changed in the branch vs base ([] on any error)."""
    try:
        manager = GitWorktreeManager()
        rp = _repo_path(manager, space)
        if not os.path.exists(rp):
            return []
        base_ref = manager._resolve_base_ref(rp, branch.base_branch)
        return manager.list_changed_files_sync(rp, branch.branch_name, base_ref)
    except Exception:
        return []


class PRCreationError(Exception):
    """Raised by `_create_or_update_pr` when PR creation cannot proceed.

    `status_code` lets the calling view translate the failure into an HTTP
    status without re-deriving it from the message.
    """

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def _create_or_update_pr(
    user,
    space: Space,
    branch: UserBranch,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a PR for `branch` and persist the resulting id/url on it.

    Shared between the explicit `/user-branch/create-pr/` endpoint and the
    auto-PR step inside `/draft-changes/commit/`. Idempotent: if the branch
    already has a PR open, returns the cached id/url instead of creating a
    second one.
    """
    if branch.pr_id and branch.pr_url:
        return {'id': branch.pr_id, 'url': branch.pr_url}

    if not space.edit_enabled:
        raise PRCreationError('Edit fork not configured', status_code=400)
    if not branch.last_commit_sha:
        raise PRCreationError(
            'No committed changes found. Commit changes first.',
            status_code=400,
        )

    service_token = ServiceToken.objects.filter(
        user=user, service_type=space.git_provider
    ).first()
    if not service_token:
        raise PRCreationError(
            f'No {space.git_provider} token found',
            status_code=400,
        )

    provider = GitProviderFactory.create_from_service_token(service_token)
    default_title = branch.name or f"Changes by {user.get_full_name() or user.username}"
    pr_title = title or default_title
    pr_description = description if description is not None else ''

    try:
        result = provider.create_pull_request(
            from_project=space.edit_fork_project_key,
            from_repo=space.edit_fork_repo_slug,
            from_branch=branch.branch_name,
            to_project=space.git_project_key,
            to_repo=space.git_repository_id,
            to_branch=branch.base_branch,
            title=pr_title,
            description=pr_description,
        )
    except Exception as e:
        logger.error(f"[UserBranch] PR creation failed: {e}", exc_info=True)
        raise PRCreationError(str(e), status_code=500) from e

    branch.pr_id = result.get('id')
    branch.pr_url = result.get('url')
    branch.status = UserBranch.Status.PR_OPEN
    branch.save(update_fields=['pr_id', 'pr_url', 'status'])
    logger.info(f"[UserBranch] Created PR #{branch.pr_id} for task '{branch.name}'")

    try:
        deleted = APIResponseCache.objects.filter(
            user=user, endpoint__contains='/pull-requests',
        ).delete()[0]
        if deleted:
            logger.info(f"[UserBranch] Invalidated {deleted} PR cache entries")
    except Exception as e:
        logger.warning(f"[UserBranch] Failed to clear PR cache: {e}")

    return result


def _serialize_task(branch: UserBranch, files: list | None = None, draft_count: int = 0) -> dict:
    files = files or []
    return {
        'id': str(branch.id),
        'name': branch.name,
        'branch_name': branch.branch_name,
        'base_branch': branch.base_branch,
        'status': branch.status,
        'is_selected': branch.is_selected,
        'last_commit_sha': branch.last_commit_sha,
        'pr_id': branch.pr_id,
        'pr_url': branch.pr_url,
        'conflict_files': branch.conflict_files or [],
        'files_count': len(files),
        'files': files,
        'draft_count': draft_count,
        'created_at': branch.created_at.isoformat(),
        'updated_at': branch.updated_at.isoformat(),
    }


def _sync_pr_status(branch: UserBranch, space: Space, user) -> None:
    pr_id = branch.pr_id
    logger.info(f"[UserBranch] Syncing PR status for branch '{branch.name}' PR #{pr_id}")
    try:
        service_token = ServiceToken.objects.filter(
            user=user, service_type=space.git_provider
        ).first()
        if not service_token:
            logger.warning(f"[UserBranch] No service token for {space.git_provider} — skipping PR sync")
            return

        APIResponseCache.objects.filter(
            user=user, endpoint__contains=f'/pull-requests/{pr_id}',
        ).delete()

        provider = GitProviderFactory.create_from_service_token(service_token)
        pr_state = provider.get_pull_request_status(
            project_key=space.git_project_key,
            repo_slug=space.git_repository_id,
            pr_id=int(pr_id),
        )
        logger.info(f"[UserBranch] PR #{pr_id} state from provider: {pr_state}")

        if pr_state == 'OPEN':
            # PR is still live — ensure status reflects that
            if branch.status != UserBranch.Status.PR_OPEN:
                branch.status = UserBranch.Status.PR_OPEN
                branch.save(update_fields=['status', 'updated_at'])
                logger.info(f"[UserBranch] PR #{pr_id} open — restored PR_OPEN status")
        elif pr_state == 'MERGED':
            branch.status = UserBranch.Status.ABANDONED
            branch.pr_id = None
            branch.pr_url = None
            branch.save(update_fields=['status', 'pr_id', 'pr_url', 'updated_at'])
            logger.info(f"[UserBranch] PR #{pr_id} merged — marked branch abandoned")
        else:
            # DECLINED, DELETED, or unknown — clear PR data, keep branch active
            branch.status = UserBranch.Status.ACTIVE
            branch.pr_id = None
            branch.pr_url = None
            branch.save(update_fields=['status', 'pr_id', 'pr_url', 'updated_at'])
            logger.info(f"[UserBranch] PR #{pr_id} {pr_state.lower()} — cleared stale pr_url")
    except Exception as e:
        logger.warning(f"[UserBranch] PR status sync failed for PR #{pr_id}: {e}")


def _open_worktree(manager: GitWorktreeManager, space: Space, branch: UserBranch) -> str:
    return manager.create_worktree_sync(
        space_id=str(space.id),
        session_id=str(branch.id),
        branch_name=branch.branch_name,
        base_branch=branch.base_branch,
        ssh_url=space.edit_fork_ssh_url,
        local_repo_path=space.edit_fork_local_path,
        upstream_ssh_url=_derive_upstream_ssh_url(space),
    )


def _get_branch_for_action(request, space: Space) -> UserBranch | None:
    """
    Resolve which branch an action targets.
    Priority: branch_id in body > selected branch for space.
    """
    branch_id = request.data.get('branch_id')
    if branch_id:
        return UserBranch.objects.filter(
            id=branch_id, user=request.user, space=space,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        ).first()
    return UserBranch.get_selected_for_user(request.user, space)


# ── ViewSet ───────────────────────────────────────────────────────────────────

class UserBranchViewSet(ViewSet):
    permission_classes = [IsAuthenticated, IsEditorOrAbove]

    # ── Workspace (all tasks + global state) ─────────────────────────────────

    @action(detail=False, methods=['get'])
    def workspace(self, request):
        """
        Return full workspace state for SpaceWorkspaceBar:
          - all tasks (branches) for this user+space
          - selected task id
          - total draft count
          - edit_enabled flag
        """
        space_id = request.query_params.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        branches = UserBranch.objects.filter(
            user=request.user,
            space=space,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        ).order_by('-is_selected', '-updated_at')

        # Sync PR status for any branch that still has a pr_url set
        # (not just PR_OPEN — a prior bug could have reset status to ACTIVE
        # while leaving pr_url in place, orphaning the stale link)
        for b in branches:
            if b.pr_url and b.pr_id:
                _sync_pr_status(b, space, request.user)

        # Reload after potential status updates
        branches = list(UserBranch.objects.filter(
            user=request.user,
            space=space,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        ).order_by('-is_selected', '-updated_at'))

        # Always ensure a Default workspace exists
        has_default = any(b.name == 'Default' for b in branches)
        if not has_default and space.edit_enabled:
            is_only = not branches
            default_branch = UserBranch.objects.create(
                user=request.user,
                space=space,
                name='Default',
                branch_name=UserBranch.generate_branch_name(request.user, 'default'),
                base_branch=space.git_default_branch or 'master',
                is_selected=is_only,
            )
            branches.append(default_branch)
            logger.info(f"[UserBranch] Auto-created Default workspace for {request.user.username}")

        # Count drafts per task
        draft_counts = {}
        for dc in UserDraftChange.objects.filter(user=request.user, space=space).values('user_branch_id'):
            bid = str(dc['user_branch_id']) if dc['user_branch_id'] else None
            draft_counts[bid] = draft_counts.get(bid, 0) + 1

        tasks = []
        for b in branches:
            files = _get_branch_files(b, space) if b.last_commit_sha else []
            dc = draft_counts.get(str(b.id), 0)
            tasks.append(_serialize_task(b, files, dc))

        # Unassigned drafts (no branch)
        unassigned_drafts = draft_counts.get(None, 0)

        selected_id = next((str(b.id) for b in branches if b.is_selected), None)

        return Response({
            'tasks': tasks,
            'selected_task_id': selected_id,
            'unassigned_draft_count': unassigned_drafts,
            'edit_enabled': space.edit_enabled,
        })

    # ── Create task ───────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='create-task')
    def create_task(self, request):
        """
        Create a new named task (branch) and auto-select it.

        Body: { space_id, name }
        """
        space_id = request.data.get('space_id')
        name = (request.data.get('name') or '').strip()

        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        if not space.edit_enabled:
            return Response({'error': 'Edit fork not configured'}, status=status.HTTP_400_BAD_REQUEST)

        branch_name = UserBranch.generate_branch_name(request.user, name)
        branch = UserBranch.objects.create(
            user=request.user,
            space=space,
            name=name,
            branch_name=branch_name,
            base_branch=space.git_default_branch or 'master',
            is_selected=False,
        )
        UserBranch.set_selected(branch)

        logger.info(f"[UserBranch] Created task '{name}' → {branch_name} for {request.user.username}")
        return Response(_serialize_task(branch), status=status.HTTP_201_CREATED)

    # ── Select task ───────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='select-task')
    def select_task(self, request):
        """
        Switch the active task for this user+space.

        Body: { branch_id }
        """
        branch_id = request.data.get('branch_id')
        if not branch_id:
            return Response({'error': 'branch_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        branch = get_object_or_404(
            UserBranch, id=branch_id, user=request.user,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        )
        UserBranch.set_selected(branch)
        logger.info(f"[UserBranch] Selected task '{branch.name}' ({branch.branch_name})")
        return Response({'selected_task_id': str(branch.id)})

    # ── Delete task ───────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='delete-task')
    def delete_task(self, request):
        """
        Delete a workspace (task) and its associated drafts.
        The Default workspace cannot be deleted.

        Body: { branch_id }
        """
        branch_id = request.data.get('branch_id')
        if not branch_id:
            return Response({'error': 'branch_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        branch = get_object_or_404(
            UserBranch, id=branch_id, user=request.user,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        )

        if branch.name == 'Default':
            return Response(
                {'error': 'The Default workspace cannot be deleted'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        space = branch.space

        # Delete associated draft changes
        deleted_drafts = UserDraftChange.objects.filter(user_branch=branch).delete()[0]

        # If selected, auto-select Default or next available
        if branch.is_selected:
            other = (
                UserBranch.objects.filter(
                    user=request.user, space=space,
                    status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
                ).exclude(pk=branch.pk).order_by('-name')  # 'Default' sorts after others alphabetically desc
                .first()
            )
            if other:
                UserBranch.set_selected(other)

        # Best-effort: discard git branch so it doesn't litter the remote
        if branch.last_commit_sha:
            manager = GitWorktreeManager()
            rp = _repo_path(manager, space)
            try:
                worktree_path = _open_worktree(manager, space, branch)
                manager.hard_reset_to_base_sync(worktree_path, branch.base_branch)
                manager.push_branch_sync(worktree_path, branch.branch_name, force=True)
                manager.cleanup_worktree_sync(str(space.id), str(branch.id), repo_path=rp)
            except Exception as e:
                logger.warning(f"[UserBranch] delete_task: git cleanup failed (continuing): {e}")

        branch_name = branch.branch_name
        branch.delete()
        logger.info(
            f"[UserBranch] Deleted workspace '{branch_name}' for {request.user.username}"
            f" (drafts removed: {deleted_drafts})"
        )
        return Response({'deleted': True, 'branch_name': branch_name})

    # ── Create / update PR ────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='create-pr')
    def create_pr(self, request):
        """
        Create a pull request from a task branch.

        Body: { space_id, branch_id?, title?, description? }
        branch_id defaults to the selected task.
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)

        branch = _get_branch_for_action(request, space)
        if not branch:
            return Response(
                {'error': 'No active task branch found'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            _create_or_update_pr(
                request.user,
                space,
                branch,
                title=request.data.get('title'),
                description=request.data.get('description'),
            )
        except PRCreationError as e:
            git_ops_log.record(
                request.user.id,
                kind='pr.create.manual',
                status='error',
                message=str(e),
                space_slug=space.slug,
                branch_name=branch.branch_name,
                payload={'http_status': e.status_code},
            )
            return Response({'error': str(e)}, status=e.status_code)

        git_ops_log.record(
            request.user.id,
            kind='pr.create.manual',
            status='ok',
            message=f"PR #{branch.pr_id} opened for {branch.branch_name}",
            space_slug=space.slug,
            branch_name=branch.branch_name,
            payload={'pr_id': branch.pr_id, 'pr_url': branch.pr_url},
        )
        return Response({'pr_id': branch.pr_id, 'pr_url': branch.pr_url, 'branch_name': branch.branch_name})

    # ── Discard ────────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def discard(self, request):
        """
        Hard-reset a task branch back to base (loses all commits).

        Body: { space_id, branch_id? }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)
        branch = _get_branch_for_action(request, space)
        if not branch:
            return Response({'error': 'No active branch found'}, status=status.HTTP_404_NOT_FOUND)

        manager = GitWorktreeManager()
        rp = _repo_path(manager, space)
        try:
            worktree_path = _open_worktree(manager, space, branch)
            manager.hard_reset_to_base_sync(worktree_path, branch.base_branch)
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
        logger.info(f"[UserBranch] Discarded branch {branch.branch_name}")
        return Response({'discarded': True, 'branch_name': branch.branch_name})

    # ── Unstage ────────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def unstage(self, request):
        """
        Soft-reset the branch to base, converting committed changes back to drafts.

        Body: { space_id, branch_id? }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)
        branch = _get_branch_for_action(request, space)
        if not branch:
            return Response({'error': 'No active branch found'}, status=status.HTTP_404_NOT_FOUND)

        manager = GitWorktreeManager()
        rp = _repo_path(manager, space)
        unstaged_files = []
        try:
            worktree_path = _open_worktree(manager, space, branch)
            changed_files = manager.soft_reset_to_base_sync(worktree_path, branch.base_branch)

            for file_path in changed_files:
                modified_content = manager.read_file_sync(worktree_path, file_path)
                if modified_content is None:
                    change_type = 'delete'
                    modified_content = ''
                else:
                    change_type = 'modify'

                original_content = manager.read_file_at_base_sync(
                    worktree_path, file_path, branch.base_branch
                ) or ''
                original_content = original_content.rstrip('\n')
                if modified_content:
                    modified_content = modified_content.rstrip('\n')

                # Skip files where content is identical after normalization — no real change
                if change_type == 'modify' and original_content == modified_content:
                    logger.debug(f"[UserBranch] unstage: skipping {file_path} (content identical to base)")
                    continue

                # Keep draft associated with this branch so it re-commits here
                UserDraftChange.objects.update_or_create(
                    user=request.user,
                    user_branch=branch,
                    file_path=file_path,
                    defaults={
                        'space': space,
                        'original_content': original_content,
                        'modified_content': modified_content,
                        'change_type': change_type,
                        'description': f'Unstaged from {branch.branch_name}',
                    },
                )
                unstaged_files.append(file_path)

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
        logger.info(f"[UserBranch] Unstaged {len(unstaged_files)} files from {branch.branch_name}")
        return Response({'unstaged_files': unstaged_files, 'branch_name': branch.branch_name})

    # ── Rebase ─────────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'])
    def rebase(self, request):
        """
        Explicitly rebase a task branch onto the latest upstream.

        Body: { space_id, branch_id? }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)
        branch = _get_branch_for_action(request, space)
        if not branch or branch.status != UserBranch.Status.ACTIVE:
            return Response({'error': 'No active branch found'}, status=status.HTTP_404_NOT_FOUND)

        manager = GitWorktreeManager()
        rp = _repo_path(manager, space)
        try:
            worktree_path = _open_worktree(manager, space, branch)
            manager.rebase_onto_base_sync(worktree_path, branch.base_branch, prefer_upstream=True)
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

    # ── Rename task ───────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='rename-task')
    def rename_task(self, request):
        """
        Rename a task (human-readable name only; branch_name is unchanged).

        Body: { branch_id, name }
        """
        branch_id = request.data.get('branch_id')
        name = (request.data.get('name') or '').strip()

        if not branch_id:
            return Response({'error': 'branch_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

        branch = get_object_or_404(
            UserBranch, id=branch_id, user=request.user,
            status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
        )
        branch.name = name
        branch.save(update_fields=['name', 'updated_at'])
        logger.info(f"[UserBranch] Renamed task {branch.branch_name} → '{name}'")
        return Response(_serialize_task(branch))

    # ── Delete PR ─────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='delete-pr')
    def delete_pr(self, request):
        """
        Decline/delete the open PR and clear pr_id/pr_url from the task.
        The branch and its commits are preserved.

        Body: { space_id, branch_id? }
        """
        space_id = request.data.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)
        branch = _get_branch_for_action(request, space)
        if not branch:
            return Response({'error': 'No active branch found'}, status=status.HTTP_404_NOT_FOUND)

        if not branch.pr_id:
            return Response({'error': 'No PR found for this task'}, status=status.HTTP_400_BAD_REQUEST)

        pr_id = branch.pr_id

        # Best-effort: decline the PR via the git provider
        try:
            service_token = ServiceToken.objects.filter(
                user=request.user, service_type=space.git_provider
            ).first()
            if service_token:
                provider = GitProviderFactory.create_from_service_token(service_token)
                provider.decline_pull_request(
                    project_key=space.git_project_key,
                    repo_slug=space.git_repository_id,
                    pr_id=int(pr_id),
                )
                logger.info(f"[UserBranch] Declined PR #{pr_id} via provider")
            else:
                logger.warning(f"[UserBranch] No service token — skipping provider PR decline")
        except Exception as e:
            logger.warning(f"[UserBranch] Failed to decline PR #{pr_id} via provider: {e}")

        branch.pr_id = None
        branch.pr_url = None
        branch.status = UserBranch.Status.ACTIVE
        branch.save(update_fields=['pr_id', 'pr_url', 'status', 'updated_at'])

        try:
            APIResponseCache.objects.filter(
                user=request.user, endpoint__contains='/pull-requests',
            ).delete()
        except Exception as e:
            logger.warning(f"[UserBranch] Failed to clear PR cache after delete: {e}")

        logger.info(f"[UserBranch] Deleted PR #{pr_id} for task '{branch.name}'")
        return Response({'deleted': True, 'branch_name': branch.branch_name})

    # ── Legacy status (kept for backward compat) ──────────────────────────────

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Legacy single-branch status — use /workspace/ for multi-task support."""
        space_id = request.query_params.get('space_id')
        if not space_id:
            return Response({'error': 'space_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        space = get_object_or_404(Space, id=space_id)
        draft_count = UserDraftChange.objects.filter(user=request.user, space=space).count()
        branch = UserBranch.get_selected_for_user(request.user, space)

        branch_data = None
        if branch:
            if branch.status == UserBranch.Status.PR_OPEN and branch.pr_id:
                _sync_pr_status(branch, space, request.user)
                branch.refresh_from_db()
            if branch.status in (UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN):
                files = _get_branch_files(branch, space)
                branch_data = _serialize_task(branch, files)

        return Response({
            'draft_count': draft_count,
            'branch': branch_data,
            'edit_enabled': space.edit_enabled,
        })
