"""
Enrichment provider registry and aggregator.
"""
from typing import List, Dict, Any
from .base import BaseEnrichmentProvider
from .comment_enrichment import CommentEnrichmentProvider
from .local_changes_enrichment import LocalChangesEnrichmentProvider
from .pr_enrichment import PREnrichmentProvider
from .diff_enrichment import DiffEnrichmentProvider


class EnrichmentRegistry:
    """
    Registry for enrichment providers.
    Manages all available enrichment providers and aggregates their results.
    """
    
    def __init__(self):
        self._providers: List[BaseEnrichmentProvider] = []
        self._register_default_providers()
    
    def _register_default_providers(self):
        """Register default enrichment providers."""
        self.register(CommentEnrichmentProvider())
        self.register(LocalChangesEnrichmentProvider())
        self.register(PREnrichmentProvider())
        self.register(DiffEnrichmentProvider())
    
    def register(self, provider: BaseEnrichmentProvider):
        """
        Register an enrichment provider.
        
        Args:
            provider: Enrichment provider instance
        """
        self._providers.append(provider)
    
    def get_providers(self) -> List[BaseEnrichmentProvider]:
        """Get all registered providers."""
        return self._providers
    
    def get_provider_by_type(self, enrichment_type: str) -> BaseEnrichmentProvider:
        """
        Get provider by enrichment type.
        
        Args:
            enrichment_type: Type of enrichment
            
        Returns:
            Provider instance or None
        """
        for provider in self._providers:
            if provider.get_enrichment_type() == enrichment_type:
                return provider
        return None
    
    def get_enrichment_types(self) -> List[str]:
        """
        Get list of all available enrichment types.
        
        Returns:
            List of enrichment type strings
        """
        return [provider.get_enrichment_type() for provider in self._providers]
    
    def get_all_enrichments(self, source_uri: str, user) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get enrichments from all providers for a source URI.
        
        Args:
            source_uri: Universal source address
            user: Django User instance
            
        Returns:
            Dictionary mapping enrichment types to lists of enrichments
        """
        result = {}
        
        for provider in self._providers:
            enrichment_type = provider.get_enrichment_type()
            try:
                enrichments = provider.get_enrichments(source_uri, user)
                if enrichments:
                    result[enrichment_type] = enrichments
            except Exception as e:
                # Log error but continue with other providers
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting enrichments from {enrichment_type} provider: {e}", exc_info=True)
                result[enrichment_type] = []
        
        return result
    
    def get_enrichments_by_type(self, source_uri: str, user, enrichment_type: str) -> List[Dict[str, Any]]:
        """
        Get enrichments of a specific type for a source URI.
        
        Args:
            source_uri: Universal source address
            user: Django User instance
            enrichment_type: Type of enrichment to retrieve
            
        Returns:
            List of enrichments
        """
        provider = self.get_provider_by_type(enrichment_type)
        if provider:
            try:
                return provider.get_enrichments(source_uri, user)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting {enrichment_type} enrichments: {e}", exc_info=True)
        return []


# Global registry instance
_registry = None


def get_registry() -> EnrichmentRegistry:
    """Get the global enrichment registry instance."""
    global _registry
    if _registry is None:
        _registry = EnrichmentRegistry()
    return _registry
