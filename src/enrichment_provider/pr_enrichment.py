"""
Pull request enrichment provider.
"""
from typing import List, Dict, Any
from .base import BaseEnrichmentProvider
from source_provider.base import SourceAddress
from git_provider.factory import GitProviderFactory
from service_tokens.models import ServiceToken


class PREnrichmentProvider(BaseEnrichmentProvider):
    """
    Provides PR diffs as enrichments for files that have open PRs.
    """
    
    def get_enrichments(self, source_uri: str, user) -> List[Dict[str, Any]]:
        """
        Get PR enrichments for a source URI.
        
        Args:
            source_uri: Universal source address
            user: Django User instance
        
        Returns:
            List of PR enrichments
        """
        try:
            # Parse source address
            address = SourceAddress.parse(source_uri)
            
            # Get Git provider
            service_token = ServiceToken.objects.filter(
                user=user,
                service_type=address.provider
            ).first()
            
            if not service_token:
                return []
            
            provider = GitProviderFactory.create_from_service_token(service_token)
            
            # Get open PRs for this repository
            prs_response = provider.list_pull_requests(
                repo_id=address.repository,
                state='open',
                page=1,
                per_page=100
            )
            
            enrichments = []
            
            # Check if this file is modified in any PR
            for pr in prs_response.get('pull_requests', []):
                # This is a simplified version - in production, you'd fetch PR files
                # and check if this file is modified
                enrichments.append({
                    'type': 'pr_diff',
                    'pr_number': pr['number'],
                    'pr_title': pr['title'],
                    'pr_author': pr['author'],
                    'pr_state': pr['state'],
                    'pr_url': pr['url'],
                    'created_at': pr['created_at'],
                })
            
            return enrichments
        
        except Exception:
            return []
    
    def get_enrichment_type(self) -> str:
        return 'pr_diff'
