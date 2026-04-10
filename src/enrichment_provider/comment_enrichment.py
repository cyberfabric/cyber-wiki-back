"""
Comment enrichment provider.
"""
from typing import List, Dict, Any
from .base import BaseEnrichmentProvider
from wiki.models import FileComment


class CommentEnrichmentProvider(BaseEnrichmentProvider):
    """
    Provides file comments as enrichments.
    """
    
    def get_enrichments(self, source_uri: str, user) -> List[Dict[str, Any]]:
        """
        Get comments for a source URI.
        
        Args:
            source_uri: Universal source address
            user: Django User instance
        
        Returns:
            List of comment enrichments
        """
        # Get comments for this source URI
        comments = FileComment.objects.filter(
            source_uri=source_uri
        ).select_related('author').order_by('line_start', 'created_at')
        
        enrichments = []
        for comment in comments:
            enrichments.append({
                'type': 'comment',
                'id': comment.id,
                'source_uri': comment.source_uri,
                'line_start': comment.line_start,
                'line_end': comment.line_end,
                'text': comment.text,
                'author': comment.author.username,
                'thread_id': str(comment.thread_id),
                'is_resolved': comment.is_resolved,
                'anchoring_status': comment.anchoring_status,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat(),
            })
        
        return enrichments
    
    def get_enrichment_type(self) -> str:
        return 'comments'
