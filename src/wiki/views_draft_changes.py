"""
Views for User Draft Changes.

Simple CRUD for draft changes (user edits not yet committed to git).
Actions: commit (create git commit from selected edits), discard
"""
import logging
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import Space, UserDraftChange, UserBranch
from users.permissions import IsEditorOrAbove
from git_provider.worktree_manager import GitWorktreeManager, GitError

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
        
        # Create or update draft change
        change, created = UserDraftChange.objects.update_or_create(
            user=request.user,
            space=space,
            file_path=file_path,
            defaults={
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
        
        This action:
        1. Takes a list of draft change IDs
        2. Creates/gets the user's branch in the fork
        3. Applies the changes and creates a commit
        4. Deletes the draft changes (they're now in git)
        
        The changes will then appear as 'commit' enrichments.
        """
        change_ids = request.data.get('change_ids', [])
        commit_message = request.data.get('commit_message', '')
        
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
            # 1. Get or create user's branch
            user_branch, branch_created = UserBranch.get_or_create_for_user(
                user=request.user,
                space=space
            )
            
            logger.info(
                f"[DraftChange] {'Created' if branch_created else 'Using'} branch "
                f"{user_branch.branch_name} for {request.user.username}"
            )
            
            # 2. Initialize GitWorktreeManager
            manager = GitWorktreeManager()
            
            # 3. Create worktree (use branch ID as session ID)
            worktree_path = manager.create_worktree_sync(
                space_id=str(space.id),
                session_id=str(user_branch.id),
                branch_name=user_branch.branch_name,
                base_branch=user_branch.base_branch,
                ssh_url=space.edit_fork_ssh_url,
                local_repo_path=space.edit_fork_local_path,
            )
            
            logger.info(f"[DraftChange] Created worktree at {worktree_path}")
            
            # 4. Apply changes to worktree
            changes_list = [
                {
                    'file_path': c.file_path,
                    'change_type': c.change_type,
                    'modified_content': c.modified_content,
                }
                for c in changes
            ]
            manager.apply_changes(worktree_path, changes_list)
            
            logger.info(f"[DraftChange] Applied {len(changes_list)} changes")
            
            # 5. Commit with user as author
            author_name = request.user.get_full_name() or request.user.username
            author_email = request.user.email or f"{request.user.username}@doclab.local"
            
            commit_sha = manager.commit_changes_sync(
                worktree_path=worktree_path,
                message=commit_message,
                author_name=author_name,
                author_email=author_email,
            )
            
            logger.info(f"[DraftChange] Created commit {commit_sha[:8]}")
            
            # 6. Push to fork - disabled for now, will implement later
            # TODO: Re-enable push when git flow is finalized
            logger.info(f"[DraftChange] Push skipped (not yet implemented)")
            
            # 7. Update UserBranch record
            user_branch.last_commit_sha = commit_sha
            user_branch.save()
            
            # 8. Delete draft changes (they're now in git)
            deleted_count = changes.count()
            changes.delete()
            
            logger.info(
                f"[DraftChange] Committed {deleted_count} changes for "
                f"{request.user.username} in space {space.slug}: {commit_sha[:8]}"
            )
            
            # 9. Cleanup worktree (optional - keep for potential amendments)
            # manager.cleanup_worktree_sync(str(space.id), str(user_branch.id))
            
            return Response({
                'success': True,
                'commit_sha': commit_sha,
                'branch_name': user_branch.branch_name,
                'files_committed': deleted_count,
                'space_id': str(space.id),
                'space_slug': space.slug,
            })
            
        except GitError as e:
            logger.error(f"[DraftChange] Git error: {e.message}", exc_info=True)
            return Response(
                {'error': f'Git operation failed: {e.message}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"[DraftChange] Unexpected error: {e}", exc_info=True)
            return Response(
                {'error': f'Commit failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
