"""
Local changes enrichment provider.
"""
from typing import List, Dict, Any
from .base import BaseEnrichmentProvider, EnrichmentCategory
from source_provider.base import SourceAddress
from wiki.models import UserChange


class LocalChangesEnrichmentProvider(BaseEnrichmentProvider):
    """
    Provides pending local changes as enrichments.
    """
    
    def get_enrichments(self, source_uri: str, user) -> List[Dict[str, Any]]:
        """
        Get local changes for a source URI.
        
        Args:
            source_uri: Universal source address
            user: Django User instance
        
        Returns:
            List of local change enrichments
        """
        try:
            # Parse source address
            address = SourceAddress.parse(source_uri)
            
            # Get pending changes for this file
            changes = UserChange.objects.filter(
                user=user,
                repository_full_name=address.repository,
                file_path=address.path,
                status='pending'
            ).order_by('-created_at')
            
            enrichments = []
            for change in changes:
                enrichments.append({
                    'type': 'local_change',
                    'id': change.id,
                    'file_path': change.file_path,
                    'commit_message': change.commit_message,
                    'status': change.status,
                    'created_at': change.created_at.isoformat(),
                    'updated_at': change.updated_at.isoformat(),
                })
            
            return enrichments
        
        except Exception:
            return []
    
    def get_enrichment_type(self) -> str:
        return 'local_changes'
    
    def get_enrichment_category(self) -> str:
        return EnrichmentCategory.REFERENCE
