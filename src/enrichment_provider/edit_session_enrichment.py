"""
Edit enrichment providers.

Provides user edit changes as enrichments:
- edit: User's edits stored in DocLab (not in git yet)
  Actions: commit, discard
  
- commit: Commits in user's fork branch that are not in main repo
  Actions: unstage, create_pr
  
Once a PR is created, changes appear as pr_diff enrichments instead.
"""
import logging
from typing import List, Dict, Any
from .base import BaseEnrichmentProvider, EnrichmentCategory
from source_provider.base import SourceAddress

logger = logging.getLogger(__name__)


class EditEnrichmentProvider(BaseEnrichmentProvider):
    """
    Provides edit enrichments for user's changes.
    
    These are user's edits stored in DocLab (UserDraftChange model).
    Not yet committed to git.
    
    Actions: commit (commit to fork), discard
    """
    
    def get_enrichments(self, source_uri: str, user) -> List[Dict[str, Any]]:
        """Get draft edit changes for a source URI."""
        from wiki.models import UserDraftChange
        
        try:
            address = SourceAddress.parse(source_uri)
            file_path = address.path
            
            logger.debug(f"[Edit] Looking for edit changes to {file_path} by user {user.username}")
            
            enrichments = []
            
            # Get draft changes from UserDraftChange model
            draft_changes = UserDraftChange.objects.filter(
                user=user,
                file_path=file_path
            ).select_related('space')
            
            for change in draft_changes:
                diff_hunks = change.generate_diff_hunks()
                
                enrichments.append({
                    'type': 'edit',
                    'id': str(change.id),
                    'space_id': str(change.space.id),
                    'space_slug': change.space.slug,
                    'file_path': change.file_path,
                    'change_type': change.change_type,
                    'description': change.description or '',
                    'user': user.username,
                    'user_full_name': user.get_full_name() or user.username,
                    'created_at': change.created_at.isoformat(),
                    'updated_at': change.updated_at.isoformat(),
                    'diff_hunks': diff_hunks,
                    'actions': ['commit', 'discard'],
                })
            
            logger.info(f"[Edit] Found {len(enrichments)} edit changes for {file_path}")
            return enrichments
        
        except Exception as e:
            logger.error(f"[Edit] Error getting enrichments: {e}", exc_info=True)
            return []
    
    def get_enrichment_type(self) -> str:
        return 'edit'
    
    def get_enrichment_category(self) -> str:
        return EnrichmentCategory.DIFF


class CommitEnrichmentProvider(BaseEnrichmentProvider):
    """
    Provides commit enrichments for changes in user's fork branch.
    
    Any commit in the user's local/fork branch that is not in the main repo
    is shown as a 'commit' enrichment.
    
    Actions: unstage (reset branch), create_pr
    """
    
    def get_enrichments(self, source_uri: str, user) -> List[Dict[str, Any]]:
        """Get commit enrichments for a source URI."""
        from wiki.models import UserBranch
        from git_provider.worktree_manager import get_worktree_manager
        
        try:
            address = SourceAddress.parse(source_uri)
            file_path = address.path
            
            logger.debug(f"[Commit] Looking for commit changes to {file_path} by user {user.username}")
            
            enrichments = []
            
            # Get active branches for this user (branches with commits not yet in PR)
            branches = UserBranch.objects.filter(
                user=user,
                status__in=[UserBranch.Status.ACTIVE, UserBranch.Status.PR_OPEN]
            ).select_related('space')
            
            manager = get_worktree_manager()
            
            for branch in branches:
                try:
                    space = branch.space
                    
                    # Determine repo path - local path takes precedence
                    if space.edit_fork_local_path:
                        repo_path = space.edit_fork_local_path
                    else:
                        repo_path = manager.get_bare_repo_path(str(space.id))
                    
                    # Skip if repo doesn't exist
                    import os
                    if not os.path.exists(repo_path):
                        logger.debug(f"[Commit] Repo not found at {repo_path}")
                        continue
                    
                    # Get diff from git for this file
                    # This compares branch to base (main) - shows what's not in main yet
                    file_diff = manager.get_file_diff_sync(
                        repo_path=repo_path,
                        branch_name=branch.branch_name,
                        base_branch=branch.base_branch,
                        file_path=file_path
                    )
                    
                    if file_diff:
                        # Determine actions based on branch status
                        if branch.status == UserBranch.Status.PR_OPEN:
                            actions = ['view_pr']
                        else:
                            actions = ['unstage', 'create_pr']
                        
                        enrichments.append({
                            'type': 'commit',
                            'id': str(branch.id),
                            'space_id': str(space.id),
                            'space_slug': space.slug,
                            'file_path': file_path,
                            'branch_name': branch.branch_name,
                            'base_branch': branch.base_branch,
                            'commit_sha': branch.last_commit_sha,
                            'user': user.username,
                            'user_full_name': user.get_full_name() or user.username,
                            'created_at': branch.created_at.isoformat(),
                            'updated_at': branch.updated_at.isoformat(),
                            'diff_hunks': file_diff.get('hunks', []),
                            'additions': file_diff.get('additions', 0),
                            'deletions': file_diff.get('deletions', 0),
                            'pr_id': branch.pr_id,
                            'pr_url': branch.pr_url,
                            'actions': actions,
                        })
                except Exception as e:
                    logger.warning(f"[Commit] Error getting diff for branch {branch.branch_name}: {e}")
                    continue
            
            logger.info(f"[Commit] Found {len(enrichments)} commit changes for {file_path}")
            return enrichments
        
        except Exception as e:
            logger.error(f"[Commit] Error getting enrichments: {e}", exc_info=True)
            return []
    
    def get_enrichment_type(self) -> str:
        return 'commit'
    
    def get_enrichment_category(self) -> str:
        return EnrichmentCategory.DIFF
