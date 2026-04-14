"""
Pull request enrichment provider.
"""
import logging
import time
from typing import List, Dict, Any
from .base import BaseEnrichmentProvider
from source_provider.base import SourceAddress
from git_provider.factory import GitProviderFactory
from service_tokens.models import ServiceToken

logger = logging.getLogger(__name__)


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
        start_time = time.time()
        try:
            # Parse source address
            parse_start = time.time()
            address = SourceAddress.parse(source_uri)
            logger.debug(f"[PR] Parse URI took {time.time() - parse_start:.3f}s")
            
            # Get Git provider
            token_start = time.time()
            service_token = ServiceToken.objects.filter(
                user=user,
                service_type=address.provider
            ).first()
            
            if not service_token:
                logger.debug(f"[PR] No service token for {address.provider}")
                return []
            
            provider = GitProviderFactory.create_from_service_token(service_token)
            logger.debug(f"[PR] Get provider took {time.time() - token_start:.3f}s")
            
            # Get ALL open PRs for this repository
            list_start = time.time()
            prs_response = provider.list_pull_requests(
                repo_id=address.repository,
                state='open',
                page=1,
                per_page=1000  # Fetch all open PRs (most repos have < 1000 open PRs)
            )
            list_duration = time.time() - list_start
            pr_count = len(prs_response.get('pull_requests', []))
            logger.info(f"[PR] List {pr_count} open PRs took {list_duration:.3f}s")
            
            enrichments = []
            
            # Check if this file is modified in any PR
            check_start = time.time()
            for pr in prs_response.get('pull_requests', []):
                try:
                    pr_file_start = time.time()
                    
                    # Fetch diff once and use for both checking and parsing
                    diff_text = provider.get_pull_request_diff(
                        repo_id=address.repository,
                        pr_number=pr['number']
                    )
                    
                    if not diff_text:
                        logger.debug(f"[PR] No diff available for PR #{pr['number']}")
                        continue
                    
                    # Check if file is modified in this PR
                    file_is_modified = address.path in diff_text
                    
                    pr_file_duration = time.time() - pr_file_start
                    logger.debug(f"[PR] Check PR #{pr['number']} took {pr_file_duration:.3f}s (match: {file_is_modified})")
                    
                    if file_is_modified:
                        # Parse diff to extract hunks for this file
                        logger.debug(f"[PR] Parsing diff for file: {address.path}, diff length: {len(diff_text)} chars")
                        hunks = self._parse_diff_hunks(diff_text, address.path)
                        logger.debug(f"[PR] Found {len(hunks)} hunks for PR #{pr['number']}")
                        
                        enrichments.append({
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
                    # If we can't get the diff for a PR, skip it
                    import traceback
                    logger.warning(f"Failed to get files for PR {pr['number']}: {e}")
                    logger.debug(f"Traceback: {traceback.format_exc()}")
                    continue
            
            check_duration = time.time() - check_start
            logger.info(f"[PR] Check all PRs took {check_duration:.3f}s, found {len(enrichments)} matches")
            
            total_duration = time.time() - start_time
            logger.info(f"[PR] Total PR enrichment time: {total_duration:.3f}s for {address.path}")
            
            return enrichments
        
        except Exception as e:
            logger.error(f"Failed to get PR enrichments: {e}")
            return []
    
    def _parse_diff_hunks(self, diff_text: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse unified diff format to extract hunks for a specific file.
        
        Returns list of hunks with line ranges:
        [
            {
                'old_start': 10,
                'old_count': 5,
                'new_start': 10,
                'new_count': 7,
                'lines': [...]
            }
        ]
        """
        logger.debug(f"[PR] Parsing diff for file: {file_path}")
        logger.debug(f"[PR] Diff text length: {len(diff_text)} chars")
        
        hunks = []
        in_file = False
        current_hunk = None
        
        for line in diff_text.split('\n'):
            # Check if we're entering the section for our file
            if line.startswith('---') or line.startswith('+++'):
                if file_path in line:
                    in_file = True
                    logger.debug(f"[PR] Matched our file: {line}")
                else:
                    in_file = False
                continue
            
            # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
            if in_file and line.startswith('@@'):
                if current_hunk:
                    hunks.append(current_hunk)
                
                # Extract line numbers from hunk header
                import re
                match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    old_start = int(match.group(1))
                    old_count = int(match.group(2)) if match.group(2) else 1
                    new_start = int(match.group(3))
                    new_count = int(match.group(4)) if match.group(4) else 1
                    
                    current_hunk = {
                        'old_start': old_start,
                        'old_count': old_count,
                        'new_start': new_start,
                        'new_count': new_count,
                        'lines': []
                    }
            
            # Collect hunk lines
            elif in_file and current_hunk is not None:
                if line.startswith('+') or line.startswith('-') or line.startswith(' '):
                    current_hunk['lines'].append(line)
        
        # Don't forget the last hunk
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
    
    def get_enrichment_type(self) -> str:
        return 'pr_diff'
