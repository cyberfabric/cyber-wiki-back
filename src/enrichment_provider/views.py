import logging
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .registry import get_registry
from wiki.models import Space

logger = logging.getLogger(__name__)


def _get_space_enrichments(request, space_slug, start_time):
    """
    Get all enrichments for a space.
    Fetches all PRs once and maps them to files.
    Returns: {file_path: {pr_diff: [...], comments: [...]}}
    """
    from git_provider.factory import GitProviderFactory
    from service_tokens.models import ServiceToken
    
    try:
        # Get space
        space = Space.objects.get(slug=space_slug)
        
        # Build repository ID
        repo_id = f"{space.git_project_key}_{space.git_repository_id}"
        
        logger.info(f"[SpaceEnrichments] Space: {space.name}, Provider: {space.git_provider}, Repo: {repo_id}")
        
        # Get Git provider
        service_token = ServiceToken.objects.filter(
            user=request.user,
            service_type=space.git_provider
        ).first()
        
        if not service_token:
            logger.warning(f"[SpaceEnrichments] No service token for {space.git_provider}")
            return Response({'error': 'No service token found'}, status=status.HTTP_400_BAD_REQUEST)
        
        provider = GitProviderFactory.create_from_service_token(service_token)
        
        # Get all open PRs for this repository
        logger.info(f"[SpaceEnrichments] Fetching PRs for space: {space.name}")
        prs_start = time.time()
        prs_response = provider.list_pull_requests(
            repo_id=repo_id,
            state='open',
            page=1,
            per_page=1000
        )
        prs_duration = time.time() - prs_start
        pr_count = len(prs_response.get('pull_requests', []))
        logger.info(f"[SpaceEnrichments] Fetched {pr_count} PRs in {prs_duration:.3f}s")
        
        # Build file_path -> enrichments mapping
        file_enrichments = {}
        
        # Process each PR
        for pr in prs_response.get('pull_requests', []):
            try:
                # Fetch PR diff
                diff_text = provider.get_pull_request_diff(
                    repo_id=repo_id,
                    pr_number=pr['number']
                )
                
                if not diff_text:
                    continue
                
                # Parse diff to find all files touched by this PR
                touched_files = _extract_files_from_diff(diff_text)
                
                # For each file, parse hunks and add enrichment
                for file_path in touched_files:
                    hunks = _parse_diff_hunks_for_file(diff_text, file_path)
                    
                    if hunks:
                        # Initialize file enrichments if not exists
                        if file_path not in file_enrichments:
                            file_enrichments[file_path] = {'pr_diff': [], 'comments': [], 'diff': [], 'local_changes': []}
                        
                        # Add PR enrichment
                        file_enrichments[file_path]['pr_diff'].append({
                            'type': 'pr_diff',
                            'pr_number': pr['number'],
                            'pr_title': pr['title'],
                            'pr_author': pr['author'],
                            'pr_state': pr['state'],
                            'pr_url': pr['url'],
                            'created_at': pr['created_at'],
                            'diff_hunks': hunks,
                        })
            
            except Exception as e:
                logger.warning(f"[SpaceEnrichments] Failed to process PR #{pr.get('number')}: {e}")
                continue
        
        # TODO: Add comments enrichments (query all comments for space)
        
        total_duration = time.time() - start_time
        logger.info(f"[SpaceEnrichments] Total time: {total_duration:.3f}s, files with enrichments: {len(file_enrichments)}")
        
        return Response(file_enrichments)
    
    except Space.DoesNotExist:
        return Response({'error': 'Space not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"[SpaceEnrichments] Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _extract_files_from_diff(diff_text):
    """Extract all file paths from a diff."""
    files = set()
    for line in diff_text.split('\n'):
        if line.startswith('---') or line.startswith('+++'):
            # Extract filename from diff marker
            marker_file = line[4:].strip()
            if marker_file.startswith('a/') or marker_file.startswith('b/'):
                marker_file = marker_file[2:]
            if marker_file and marker_file != '/dev/null':
                files.add(marker_file)
    return files


def _parse_diff_hunks_for_file(diff_text, file_path):
    """Parse diff hunks for a specific file."""
    import re
    hunks = []
    in_file = False
    current_hunk = None
    
    for line in diff_text.split('\n'):
        # Check if we're entering the section for our file
        if line.startswith('---') or line.startswith('+++'):
            marker_file = line[4:].strip()
            if marker_file.startswith('a/') or marker_file.startswith('b/'):
                marker_file = marker_file[2:]
            
            is_match = (marker_file == file_path)
            
            if is_match:
                in_file = True
            elif marker_file:
                in_file = False
            continue
        
        # Parse hunk header
        if in_file and line.startswith('@@'):
            if current_hunk:
                hunks.append(current_hunk)
            
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                current_hunk = {
                    'old_start': int(match.group(1)),
                    'old_count': int(match.group(2)) if match.group(2) else 1,
                    'new_start': int(match.group(3)),
                    'new_count': int(match.group(4)) if match.group(4) else 1,
                    'lines': []
                }
        
        # Collect hunk lines
        elif in_file and current_hunk is not None:
            if line.startswith('+') or line.startswith('-') or line.startswith(' '):
                current_hunk['lines'].append(line)
    
    if current_hunk:
        hunks.append(current_hunk)
    
    return hunks


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
        
        # Get directory tree recursively to get all files in subdirectories
        tree_start = time.time()
        # Convert '.' placeholder to empty string for root directory
        tree_path = '' if address.path == '.' else (address.path or '')
        # Split repository into project_key and repo_slug
        project_key, repo_slug = address.repository.split('_', 1)
        tree_entries = provider.get_directory_tree(project_key, repo_slug, tree_path, address.branch, recursive=True)
        tree_duration = time.time() - tree_start
        logger.info(f"[Enrichments] Recursive tree fetch took {tree_duration:.3f}s, found {len(tree_entries)} entries")
        
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
    Get enrichments for a source URI or entire space.
    
    Query Parameters:
        source_uri: Universal source address for specific file (optional)
        space_slug: Space slug for all enrichments in space (optional)
        type: Filter by enrichment type (optional)
        recursive: If true, get enrichments for all files in directory (optional, only with source_uri)
    
    Returns:
        - If source_uri: Dictionary mapping enrichment types to lists of enrichments
        - If space_slug: Dictionary mapping file paths to their enrichments
    """
    start_time = time.time()
    source_uri = request.query_params.get('source_uri')
    space_slug = request.query_params.get('space_slug')
    enrichment_type = request.query_params.get('type')
    recursive = request.query_params.get('recursive', 'false').lower() == 'true'
    
    # Handle space-level enrichments
    if space_slug:
        logger.info(f"[Enrichments] Space request for: {space_slug}")
        return _get_space_enrichments(request, space_slug, start_time)
    
    # Handle file-level enrichments
    if not source_uri:
        return Response(
            {'error': 'Either source_uri or space_slug parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    logger.info(f"[Enrichments] File request for: {source_uri} (type: {enrichment_type or 'all'}, recursive: {recursive})")
    
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
