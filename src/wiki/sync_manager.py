"""
Background sync manager for Git synchronization.
"""
from django.utils import timezone
from .models import GitSyncConfig, Space, Document
from git_provider.factory import GitProviderFactory
from service_tokens.models import ServiceToken
from source_provider.base import SourceAddress
import logging

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manages background Git synchronization for spaces.
    """
    
    @staticmethod
    def sync_space(space: Space, user=None):
        """
        Sync a space with its Git repository.
        
        Args:
            space: Space instance to sync
            user: User for Git credentials (optional, uses space creator if not provided)
        
        Returns:
            Dict with sync results
        """
        sync_config = GitSyncConfig.objects.filter(space=space, status='active').first()
        
        if not sync_config:
            return {'error': 'No active sync configuration'}
        
        # Use space creator if no user provided
        if not user:
            user = space.created_by
        
        if not user:
            return {'error': 'No user available for sync'}
        
        try:
            # Get Git credentials
            # Parse repository URL to determine provider
            # This is simplified - in production, you'd parse the URL properly
            provider_type = 'github'  # Default
            
            service_token = ServiceToken.objects.filter(user=user, service_type=provider_type).first()
            
            if not service_token:
                sync_config.status = 'error'
                sync_config.last_sync_error = 'No Git credentials found'
                sync_config.save()
                return {'error': 'No Git credentials found'}
            
            provider = GitProviderFactory.create_from_service_token(service_token)
            
            # Get repository ID from URL
            # This is simplified - in production, you'd parse the URL properly
            repo_id = sync_config.repository_url.split('/')[-1].replace('.git', '')
            
            # Get file tree
            tree = provider.get_directory_tree(
                repo_id=repo_id,
                path='',
                branch=sync_config.branch,
                recursive=True
            )
            
            # Filter for markdown files
            md_files = [f for f in tree if f['type'] == 'file' and f['path'].endswith(('.md', '.markdown'))]
            
            synced_count = 0
            
            # Sync each file
            for file_entry in md_files:
                try:
                    # Get file content
                    content_data = provider.get_file_content(
                        repo_id=repo_id,
                        file_path=file_entry['path'],
                        branch=sync_config.branch
                    )
                    
                    # Create or update document
                    document, created = Document.objects.update_or_create(
                        space=space,
                        repository_id=repo_id,
                        path=file_entry['path'],
                        defaults={
                            'title': file_entry['path'].split('/')[-1].replace('.md', '').replace('-', ' ').title(),
                            'content': content_data.get('content', ''),
                            'branch': sync_config.branch,
                            'doc_type': 'markdown',
                            'created_by': user
                        }
                    )
                    
                    synced_count += 1
                
                except Exception as e:
                    logger.error(f"Error syncing file {file_entry['path']}: {e}")
                    continue
            
            # Update sync config
            sync_config.last_sync_at = timezone.now()
            sync_config.last_sync_error = ''
            sync_config.save()
            
            return {
                'success': True,
                'synced_count': synced_count,
                'total_files': len(md_files)
            }
        
        except Exception as e:
            logger.error(f"Error syncing space {space.slug}: {e}")
            sync_config.status = 'error'
            sync_config.last_sync_error = str(e)
            sync_config.save()
            
            return {'error': str(e)}
    
    @staticmethod
    def sync_all_active():
        """
        Sync all spaces with active sync configurations.
        
        Returns:
            Dict with sync results
        """
        active_configs = GitSyncConfig.objects.filter(status='active').select_related('space')
        
        results = []
        
        for config in active_configs:
            result = SyncManager.sync_space(config.space)
            results.append({
                'space': config.space.slug,
                'result': result
            })
        
        return {
            'total_synced': len(results),
            'results': results
        }
