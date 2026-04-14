import logging
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .registry import get_registry

logger = logging.getLogger(__name__)


def _get_recursive_enrichments(request, source_uri, enrichment_type, start_time):
    """
    Get enrichments for all files in a directory.
    """
    from source_provider.base import SourceAddress
    from git_provider.factory import GitProviderFactory
    from service_tokens.models import ServiceToken
    
    try:
        # Strip trailing slash for root directory
        original_uri = source_uri
        source_uri = source_uri.rstrip('/')
        logger.debug(f"[Enrichments] Original URI: {original_uri}")
        logger.debug(f"[Enrichments] After rstrip: {source_uri}")
        logger.debug(f"[Enrichments] Slash count: {source_uri.count('/')}")
        
        # For root directory, add a placeholder path for parser
        # git://provider/repo/branch has 4 slashes (git:// = 2, then 2 more)
        # git://provider/repo/branch/path has 5+ slashes
        if source_uri.count('/') == 4:  # No path component (root directory)
            source_uri += '/.'
            logger.debug(f"[Enrichments] Added placeholder: {source_uri}")
        
        # Parse source address to get provider and repository info
        address = SourceAddress.parse(source_uri)
        
        # Get Git provider
        service_token = ServiceToken.objects.filter(
            user=request.user,
            service_type=address.provider
        ).first()
        
        if not service_token:
            return Response(
                {'error': 'No service token found for provider'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        provider = GitProviderFactory.create_from_service_token(service_token)
        
        # Get directory tree
        tree_start = time.time()
        # Convert '.' placeholder to empty string for root directory
        tree_path = '' if address.path == '.' else (address.path or '')
        # Split repository into project_key and repo_slug
        project_key, repo_slug = address.repository.split('_', 1)
        tree_entries = provider.get_directory_tree(project_key, repo_slug, tree_path, address.branch, recursive=False)
        tree_duration = time.time() - tree_start
        logger.info(f"[Enrichments] Tree fetch took {tree_duration:.3f}s, found {len(tree_entries)} entries")
        
        # Filter only files (not directories)
        files = [entry for entry in tree_entries if entry.get('type') == 'file']
        logger.info(f"[Enrichments] Processing {len(files)} files")
        
        # Get enrichments for each file
        registry = get_registry()
        results = {}
        
        for file_entry in files:
            file_path = file_entry.get('path', '')
            # Build source URI for this file
            file_source_uri = f"git://{address.provider}/{address.repository}/{address.branch}/{file_path}"
            
            try:
                if enrichment_type:
                    enrichments = registry.get_enrichments_by_type(file_source_uri, request.user, enrichment_type)
                    results[file_source_uri] = {enrichment_type: enrichments}
                else:
                    enrichments = registry.get_all_enrichments(file_source_uri, request.user)
                    results[file_source_uri] = enrichments
            except Exception as e:
                logger.error(f"[Enrichments] Failed to get enrichments for {file_source_uri}: {e}")
                results[file_source_uri] = {}
        
        total_duration = time.time() - start_time
        logger.info(f"[Enrichments] Recursive request completed in {total_duration:.3f}s for {len(files)} files")
        
        return Response(results)
        
    except Exception as e:
        logger.error(f"[Enrichments] Recursive enrichment failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_enrichments(request):
    """
    Get all enrichments for a source URI.
    
    Query Parameters:
        source_uri: Universal source address (required)
        type: Filter by enrichment type (optional)
        recursive: If true, get enrichments for all files in directory (optional)
    
    Returns:
        - If recursive=false: Dictionary mapping enrichment types to lists of enrichments
        - If recursive=true: Dictionary mapping source URIs to their enrichments
    """
    start_time = time.time()
    source_uri = request.query_params.get('source_uri')
    enrichment_type = request.query_params.get('type')
    recursive = request.query_params.get('recursive', 'false').lower() == 'true'
    
    logger.info(f"[Enrichments] Request for: {source_uri} (type: {enrichment_type or 'all'}, recursive: {recursive})")
    
    if not source_uri:
        return Response(
            {'error': 'source_uri parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle recursive directory enrichments
    if recursive:
        return _get_recursive_enrichments(request, source_uri, enrichment_type, start_time)
    
    registry = get_registry()
    
    if enrichment_type:
        # Get enrichments of specific type
        type_start = time.time()
        enrichments = registry.get_enrichments_by_type(source_uri, request.user, enrichment_type)
        type_duration = time.time() - type_start
        logger.info(f"[Enrichments] Type '{enrichment_type}' took {type_duration:.3f}s")
        result = {enrichment_type: enrichments}
    else:
        # Get all enrichments
        all_start = time.time()
        enrichments = registry.get_all_enrichments(source_uri, request.user)
        all_duration = time.time() - all_start
        
        # Log individual provider times
        for enrich_type, enrich_list in enrichments.items():
            count = len(enrich_list) if enrich_list else 0
            logger.info(f"[Enrichments]   - {enrich_type}: {count} items")
        
        logger.info(f"[Enrichments] All enrichments took {all_duration:.3f}s")
        result = enrichments
    
    total_duration = time.time() - start_time
    logger.info(f"[Enrichments] Total request time: {total_duration:.3f}s for {source_uri}")
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_enrichment_types(request):
    """
    Get list of available enrichment types.
    
    Returns:
        List of enrichment type strings
    """
    registry = get_registry()
    types = registry.get_enrichment_types()
    return Response({'types': types})
