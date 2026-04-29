"""
Views for User Draft Changes.

Simple CRUD for draft changes (user edits not yet committed to git).
Actions: commit (create git commit from selected edits), discard
"""
import logging
import os
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Space, UserDraftChange, UserBranch
from . import git_ops_log
from .views_user_branch import (
    _derive_upstream_ssh_url,
    _create_or_update_pr,
    PRCreationError,
)
from users.permissions import IsEditorOrAbove
from git_provider.worktree_manager import (
    GitWorktreeManager, GitError, RebaseConflictError, EmptyCommitError,
)

logger = logging.getLogger(__name__)


class DraftChangeViewSet(viewsets.ViewSet):
    """
    ViewSet for managing user draft changes.
    """
    permission_classes = [IsAuthenticated, IsEditorOrAbove]
    
    @extend_schema(
        operation_id='draft_changes_list',
        summary='List draft changes',
        description='List all draft changes for the current user.',
        responses={200: dict},
        tags=['draft-changes'],
    )
    def list(self, request):
        """List draft changes for current user."""
        space_id = request.query_params.get('space_id')
        
        queryset = UserDraftChange.objects.filter(user=request.user)
        if space_id:
            queryset = queryset.filter(space_id=space_id)
        
        changes = []
        for change in queryset.select_related('space'):
            changes.append({
                'id': str(change.id),
                'space_id': str(change.space.id),
                'space_slug': change.space.slug,
                'file_path': change.file_path,
                'change_type': change.change_type,
                'description': change.description,
                'branch_id': str(change.user_branch_id) if change.user_branch_id else None,
                'created_at': change.created_at.isoformat(),
                'updated_at': change.updated_at.isoformat(),
            })
        
        return Response(changes)
    
    @extend_schema(
        operation_id='draft_changes_create',
        summary='Save draft change',
        description='Save a file change as draft.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'space_id': {'type': 'string'},
                    'file_path': {'type': 'string'},
                    'original_content': {'type': 'string'},
                    'modified_content': {'type': 'string'},
                    'change_type': {'type': 'string', 'enum': ['modify', 'create', 'delete']},
                    'description': {'type': 'string'},
                },
                'required': ['space_id', 'file_path', 'modified_content'],
            }
        },
        responses={200: dict},
        tags=['draft-changes'],
    )
    def create(self, request):
        """Save a draft change."""
        space_id = request.data.get('space_id')
        file_path = request.data.get('file_path')
        original_content = request.data.get('original_content', '')
        modified_content = request.data.get('modified_content', '')
        change_type = request.data.get('change_type', 'modify')
        description = request.data.get('description', '')
        
        if not space_id or not file_path:
            return Response(
                {'error': 'space_id and file_path are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        space = get_object_or_404(Space, id=space_id)

        # Associate draft with the currently selected task (branch) if one is active.
        selected_branch = UserBranch.get_selected_for_user(request.user, space)

        # Lookup key: scoped to branch when one is selected, otherwise fallback to
        # (user, space, file_path) for unassigned drafts.
        if selected_branch:
            lookup = {'user': request.user, 'user_branch': selected_branch, 'file_path': file_path}
        else:
            # No task selected — find any unassigned draft for this file
            lookup = {'user': request.user, 'space': space, 'file_path': file_path, 'user_branch': None}

        # Create or update draft change
        change, created = UserDraftChange.objects.update_or_create(
            **lookup,
            defaults={
                'space': space,
                'original_content': original_content,
                'modified_content': modified_content,
                'change_type': change_type,
                'description': description,
            }
        )
        
        logger.info(f"[DraftChange] {'Created' if created else 'Updated'} draft for {file_path} by {request.user.username}")
        
        return Response({
            'id': str(change.id),
            'space_id': str(space.id),
            'file_path': change.file_path,
            'change_type': change.change_type,
            'created': created,
            'updated_at': change.updated_at.isoformat(),
        })
    
    @extend_schema(
        operation_id='draft_changes_retrieve',
        summary='Get draft change',
        description='Get a specific draft change.',
        responses={200: dict},
        tags=['draft-changes'],
    )
    def retrieve(self, request, pk=None):
        """Get a draft change."""
        change = get_object_or_404(
            UserDraftChange,
            id=pk,
            user=request.user
        )
        
        return Response({
            'id': str(change.id),
            'space_id': str(change.space.id),
            'space_slug': change.space.slug,
            'file_path': change.file_path,
            'change_type': change.change_type,
            'original_content': change.original_content,
            'modified_content': change.modified_content,
            'description': change.description,
            'created_at': change.created_at.isoformat(),
            'updated_at': change.updated_at.isoformat(),
        })
    
    @extend_schema(
        operation_id='draft_changes_destroy',
        summary='Discard draft change',
        description='Discard a draft change.',
        responses={204: None},
        tags=['draft-changes'],
    )
    def destroy(self, request, pk=None):
        """Discard a draft change."""
        change = get_object_or_404(
            UserDraftChange,
            id=pk,
            user=request.user
        )
        file_path = change.file_path
        change.delete()
        
        logger.info(f"[DraftChange] Discarded draft for {file_path} by {request.user.username}")
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @extend_schema(
        operation_id='draft_changes_commit',
        summary='Commit draft changes',
        description='''
        Commit selected draft changes to git.
        
        Creates a git commit in the user's fork branch with the selected changes.
        The commit will be attributed to the user (as author) but pushed by the service account.
        
        After successful commit:
        - Selected draft changes are deleted
        - Changes appear as 'commit' enrichments instead of 'edit' enrichments
        ''',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'change_ids': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': 'List of draft change IDs to commit'
                    },
                    'commit_message': {
                        'type': 'string',
                        'description': 'Commit message (optional, will be auto-generated if not provided)'
                    },
                },
                'required': ['change_ids'],
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'commit_sha': {'type': 'string'},
                    'branch_name': {'type': 'string'},
                    'files_committed': {'type': 'integer'},
                }
            },
            400: {'description': 'Invalid request'},
            404: {'description': 'Draft change not found'},
        },
        tags=['draft-changes'],
    )
    @action(detail=False, methods=['post'])
    def commit(self, request):
        """
        Commit selected draft changes to git.

        Body:
          change_ids     – list of draft change UUIDs to commit
          commit_message – optional commit message
          branch_id      – optional task (UserBranch) UUID; defaults to selected task

        Flow:
        1. Resolve target branch (branch_id or selected task)
        2. Open/create worktree for that branch
        3. Apply changes and push
        4. Delete the draft changes
        """
        change_ids = request.data.get('change_ids', [])
        commit_message = request.data.get('commit_message', '')
        branch_id = request.data.get('branch_id')
        
        if not change_ids:
            return Response(
                {'error': 'change_ids is required and must not be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the draft changes
        changes = UserDraftChange.objects.filter(
            id__in=change_ids,
            user=request.user
        ).select_related('space')
        
        if not changes.exists():
            return Response(
                {'error': 'No valid draft changes found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verify all changes are from the same space
        space_ids = set(str(c.space.id) for c in changes)
        if len(space_ids) > 1:
            return Response(
                {'error': 'All changes must be from the same space'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        space = changes.first().space
        
        # Check if space has edit fork configured
        if not space.edit_enabled:
            return Response(
                {'error': 'Edit fork not configured for this space'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate commit message if not provided
        if not commit_message:
            file_count = changes.count()
            if file_count == 1:
                change = changes.first()
                commit_message = change.description or f"Update {change.file_path}"
            else:
                commit_message = f"Update {file_count} files"
        
        try:
            # 1. Resolve target branch
            branch_created = False
            if branch_id:
                user_branch = UserBranch.objects.filter(
                    id=branch_id, user=request.user, space=space,
                    status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN],
                ).first()
                if not user_branch:
                    return Response(
                        {'error': 'Branch not found or not active'},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                # Use selected task, or create a new one
                user_branch = UserBranch.get_selected_for_user(request.user, space)
                if not user_branch:
                    # Auto-create a nameless task so backward-compat flow still works
                    user_branch = UserBranch.objects.create(
                        user=request.user,
                        space=space,
                        name='',
                        branch_name=UserBranch.generate_branch_name(request.user),
                        base_branch=space.git_default_branch or 'master',
                    )
                    UserBranch.set_selected(user_branch)
                    branch_created = True

            logger.info(
                f"[DraftChange] {'Created' if branch_created else 'Using'} branch "
                f"{user_branch.branch_name} for {request.user.username}"
            )

            # 2. Create worktree (also fetches latest from remote)
            manager = GitWorktreeManager()
            effective_repo_path = (
                space.edit_fork_local_path
                if space.edit_fork_local_path and os.path.exists(space.edit_fork_local_path)
                else manager.get_bare_repo_path(str(space.id))
            )
            worktree_path = manager.create_worktree_sync(
                space_id=str(space.id),
                session_id=str(user_branch.id),
                branch_name=user_branch.branch_name,
                base_branch=user_branch.base_branch,
                ssh_url=space.edit_fork_ssh_url,
                local_repo_path=space.edit_fork_local_path,
                upstream_ssh_url=_derive_upstream_ssh_url(space),
            )
            logger.info(f"[DraftChange] Worktree at {worktree_path}")

            # 3. Rebase onto latest base (remote repos only — local repos are managed
            #    by the user and are assumed current; their remotes may not be the fork).
            if not space.edit_fork_local_path:
                try:
                    manager.rebase_onto_base_sync(worktree_path, user_branch.base_branch, prefer_upstream=True)
                except RebaseConflictError as exc:
                    user_branch.conflict_files = exc.conflicting_files
                    user_branch.save(update_fields=['conflict_files'])
                    manager.cleanup_worktree_sync(str(space.id), str(user_branch.id), repo_path=effective_repo_path)
                    return Response(
                        {
                            'error': 'rebase_conflict',
                            'message': 'Your branch conflicts with the latest base branch.',
                            'conflict_files': exc.conflicting_files,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

            # Clear any previous conflict state
            if user_branch.conflict_files:
                user_branch.conflict_files = []
                user_branch.save(update_fields=['conflict_files'])

            # 4. Apply draft changes (pass original_content so apply_changes can
            #    3-way merge when a previous commit already touched the same file)
            changes_list = [
                {'file_path': c.file_path, 'change_type': c.change_type,
                 'original_content': c.original_content,
                 'modified_content': c.modified_content}
                for c in changes
            ]
            manager.apply_changes(worktree_path, changes_list)
            logger.info(f"[DraftChange] Applied {len(changes_list)} changes")

            # 5. Commit with user as author
            author_name = request.user.get_full_name() or request.user.username
            author_email = request.user.email or f"{request.user.username}@doclab.local"
            try:
                commit_sha = manager.commit_changes_sync(
                    worktree_path=worktree_path,
                    message=commit_message,
                    author_name=author_name,
                    author_email=author_email,
                )
                logger.info(f"[DraftChange] Created commit {commit_sha[:8]}")
            except EmptyCommitError:
                # Drafts whose content already matches HEAD (e.g. a prior commit
                # succeeded but the response was lost) leave nothing to stage.
                # Treat as no-op success: clear the stale drafts, keep the
                # branch pointed at HEAD, skip the empty push.
                deleted_count = changes.count()
                head_sha = manager.head_sha_sync(worktree_path)
                user_branch.last_commit_sha = head_sha
                user_branch.save(update_fields=['last_commit_sha'])
                changes.delete()
                manager.cleanup_worktree_sync(
                    str(space.id), str(user_branch.id), repo_path=effective_repo_path
                )
                logger.info(
                    f"[DraftChange] No-op commit for {request.user.username} "
                    f"in {space.slug}: drafts already match HEAD ({head_sha[:8]})"
                )
                pr_payload_noop = (
                    {'pr_id': user_branch.pr_id, 'pr_url': user_branch.pr_url}
                    if user_branch.pr_id and user_branch.pr_url
                    else None
                )
                return Response({
                    'success': True,
                    'commit_sha': head_sha,
                    'branch_name': user_branch.branch_name,
                    'files_committed': 0,
                    'drafts_cleared': deleted_count,
                    'space_id': str(space.id),
                    'space_slug': space.slug,
                    'noop': True,
                    'pr': pr_payload_noop,
                    'pr_error': None,
                    'pr_status': 'existing' if pr_payload_noop else 'not_attempted',
                })

            # 6. Push to fork
            manager.push_branch_sync(worktree_path, user_branch.branch_name)
            logger.info(f"[DraftChange] Pushed branch {user_branch.branch_name}")

            # 7. Update branch record and remove drafts
            # Preserve PR_OPEN status — a new push updates the existing PR in-place.
            deleted_count = changes.count()
            user_branch.last_commit_sha = commit_sha
            if user_branch.status != UserBranch.Status.PR_OPEN:
                user_branch.status = UserBranch.Status.ACTIVE
            user_branch.save(update_fields=['last_commit_sha', 'status', 'conflict_files'])
            changes.delete()

            # 8. Cleanup worktree
            manager.cleanup_worktree_sync(str(space.id), str(user_branch.id), repo_path=effective_repo_path)

            logger.info(
                f"[DraftChange] Committed {deleted_count} changes for "
                f"{request.user.username} in {space.slug}: {commit_sha[:8]}"
            )
            git_ops_log.record(
                request.user.id,
                kind='commit',
                status='ok',
                message=f"{deleted_count} file(s) committed: {commit_message[:80]}",
                space_slug=space.slug,
                branch_name=user_branch.branch_name,
                payload={
                    'commit_sha': commit_sha,
                    'files_committed': deleted_count,
                    'base_branch': user_branch.base_branch,
                },
            )

            # 9. Auto-create PR for branches that don't have one yet. The push
            #    in step 6 already produced a remote head. We always return a
            #    `pr_status` enum so the frontend can show a clear banner:
            #    `created`     — PR newly opened on this commit,
            #    `existing`    — branch already had a PR (push updates it),
            #    `failed`      — attempt failed mid-flight,
            #    `not_attempted` — prerequisites missing (no edit fork / token).
            had_pr_before = bool(user_branch.pr_id)
            pr_payload = None
            pr_error = None
            pr_status = 'existing' if had_pr_before else 'not_attempted'
            if not had_pr_before:
                try:
                    _create_or_update_pr(request.user, space, user_branch)
                    pr_status = 'created'
                except PRCreationError as e:
                    pr_error = str(e)
                    pr_status = 'failed'
                    logger.warning(
                        f"[DraftChange] auto-PR creation skipped for "
                        f"{user_branch.branch_name}: {e}"
                    )
                    git_ops_log.record(
                        request.user.id,
                        kind='pr.create.auto',
                        status='error',
                        message=str(e),
                        space_slug=space.slug,
                        branch_name=user_branch.branch_name,
                        payload={'http_status': e.status_code},
                    )
            if user_branch.pr_id and user_branch.pr_url:
                pr_payload = {'pr_id': user_branch.pr_id, 'pr_url': user_branch.pr_url}
                if pr_status == 'created':
                    git_ops_log.record(
                        request.user.id,
                        kind='pr.create.auto',
                        status='ok',
                        message=f"PR #{user_branch.pr_id} opened for {user_branch.branch_name}",
                        space_slug=space.slug,
                        branch_name=user_branch.branch_name,
                        payload={
                            'pr_id': user_branch.pr_id,
                            'pr_url': user_branch.pr_url,
                        },
                    )
                elif pr_status == 'existing':
                    git_ops_log.record(
                        request.user.id,
                        kind='pr.update.push',
                        status='ok',
                        message=(
                            f"Pushed new commit to existing PR #{user_branch.pr_id}"
                        ),
                        space_slug=space.slug,
                        branch_name=user_branch.branch_name,
                        payload={
                            'pr_id': user_branch.pr_id,
                            'pr_url': user_branch.pr_url,
                            'commit_sha': commit_sha,
                        },
                    )

            return Response({
                'success': True,
                'commit_sha': commit_sha,
                'branch_name': user_branch.branch_name,
                'files_committed': deleted_count,
                'space_id': str(space.id),
                'space_slug': space.slug,
                'pr': pr_payload,
                'pr_error': pr_error,
                'pr_status': pr_status,
            })

        except RebaseConflictError as exc:
            git_ops_log.record(
                request.user.id,
                kind='commit',
                status='error',
                message=f"Rebase conflict: {len(exc.conflicting_files)} file(s)",
                space_slug=space.slug,
                payload={'conflict_files': exc.conflicting_files},
            )
            return Response(
                {'error': 'rebase_conflict', 'conflict_files': exc.conflicting_files},
                status=status.HTTP_409_CONFLICT,
            )
        except GitError as e:
            logger.error(f"[DraftChange] Git error: {e.message}", exc_info=True)
            git_ops_log.record(
                request.user.id,
                kind='commit',
                status='error',
                message=f"Git error: {e.message}",
                space_slug=space.slug,
            )
            return Response(
                {'error': f'Git operation failed: {e.message}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"[DraftChange] Unexpected error: {e}", exc_info=True)
            git_ops_log.record(
                request.user.id,
                kind='commit',
                status='error',
                message=f"Unexpected error: {str(e)[:200]}",
                space_slug=space.slug,
            )
            return Response(
                {'error': f'Commit failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
