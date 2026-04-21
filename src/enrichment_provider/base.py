"""
Base interface for enrichment providers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class EnrichmentCategory:
    """
    Enrichment categories define how enrichments interact with content.
    """
    REFERENCE = 'reference'  # Points to a line without modifying it (comments)
    DIFF = 'diff'  # Modifies content by adding/removing lines (PR diffs, commits, edits)


class BaseEnrichmentProvider(ABC):
    """
    Abstract base class for enrichment providers.
    
    Enrichment providers add metadata to source files (comments, PR diffs, local changes, etc.)
    """
    
    @abstractmethod
    def get_enrichments(self, source_uri: str, user) -> List[Dict[str, Any]]:
        """
        Get enrichments for a source URI.
        
        Args:
            source_uri: Universal source address
            user: Django User instance
        
        Returns:
            List of enrichment dictionaries
        """
        pass
    
    @abstractmethod
    def get_enrichment_type(self) -> str:
        """
        Get the type of enrichment this provider handles.
        
        Returns:
            Enrichment type string (e.g., 'comments', 'pr_diff', 'local_changes')
        """
        pass
    
    @abstractmethod
    def get_enrichment_category(self) -> str:
        """
        Get the category of enrichment this provider handles.
        
        Returns:
            Enrichment category (EnrichmentCategory.REFERENCE or EnrichmentCategory.DIFF)
        """
        pass
