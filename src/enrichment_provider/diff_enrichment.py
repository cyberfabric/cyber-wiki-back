"""
Diff enrichment provider for showing changes.
"""
from typing import List, Dict, Any
import difflib
from .base import BaseEnrichmentProvider, EnrichmentCategory
from wiki.models import UserChange


class DiffEnrichmentProvider(BaseEnrichmentProvider):
    """
    Provides diff enrichments for pending user changes.
    Shows inline diffs for modified files.
    """
    
    def get_enrichments(self, source_uri: str, user) -> List[Dict[str, Any]]:
        """
        Get diff enrichments for a source URI.
        
        Args:
            source_uri: Universal source address
            user: Django User instance
        
        Returns:
            List of diff enrichments with line-by-line changes
        """
        try:
            # Extract file path from source_uri
            # Format: git://provider/base_url/project/repo/branch/path
            parts = source_uri.split('/')
            if len(parts) < 7:
                return []
            
            file_path = '/'.join(parts[6:])
            
            # Get pending changes for this file
            changes = UserChange.objects.filter(
                user=user,
                file_path=file_path,
                status='pending'
            ).order_by('-created_at')
            
            enrichments = []
            
            for change in changes:
                # Generate unified diff
                diff_lines = self._generate_diff(
                    change.original_content,
                    change.modified_content,
                    file_path
                )
                
                # Parse diff into structured format
                diff_hunks = self._parse_diff(diff_lines)
                
                enrichments.append({
                    'type': 'diff',
                    'id': str(change.id),
                    'file_path': change.file_path,
                    'description': getattr(change, 'description', ''),
                    'status': change.status,
                    'diff_hunks': diff_hunks,
                    'diff_text': '\n'.join(diff_lines),
                    'created_at': change.created_at.isoformat(),
                    'updated_at': change.updated_at.isoformat(),
                    'stats': {
                        'additions': sum(1 for line in diff_lines if line.startswith('+')),
                        'deletions': sum(1 for line in diff_lines if line.startswith('-')),
                        'total_changes': len([line for line in diff_lines if line.startswith(('+', '-'))]),
                    }
                })
            
            return enrichments
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting diff enrichments: {e}", exc_info=True)
            return []
    
    def _generate_diff(self, original: str, modified: str, filename: str) -> List[str]:
        """
        Generate unified diff between original and modified content.
        
        Args:
            original: Original file content
            modified: Modified file content
            filename: File name for diff header
            
        Returns:
            List of diff lines
        """
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f'a/{filename}',
            tofile=f'b/{filename}',
            lineterm=''
        )
        
        return list(diff)
    
    def _parse_diff(self, diff_lines: List[str]) -> List[Dict[str, Any]]:
        """
        Parse unified diff into structured hunks.
        
        Args:
            diff_lines: Lines from unified diff
            
        Returns:
            List of diff hunks with line numbers and changes
        """
        hunks = []
        current_hunk = None
        
        for line in diff_lines:
            if line.startswith('@@'):
                # New hunk header
                if current_hunk:
                    hunks.append(current_hunk)
                
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                parts = line.split('@@')
                if len(parts) >= 2:
                    ranges = parts[1].strip().split()
                    old_range = ranges[0].lstrip('-').split(',')
                    new_range = ranges[1].lstrip('+').split(',')
                    
                    current_hunk = {
                        'old_start': int(old_range[0]),
                        'old_count': int(old_range[1]) if len(old_range) > 1 else 1,
                        'new_start': int(new_range[0]),
                        'new_count': int(new_range[1]) if len(new_range) > 1 else 1,
                        'lines': []
                    }
            elif current_hunk is not None:
                # Add line to current hunk
                if line.startswith('+'):
                    current_hunk['lines'].append({'type': 'add', 'content': line[1:]})
                elif line.startswith('-'):
                    current_hunk['lines'].append({'type': 'delete', 'content': line[1:]})
                elif line.startswith(' '):
                    current_hunk['lines'].append({'type': 'context', 'content': line[1:]})
        
        if current_hunk:
            hunks.append(current_hunk)
        
        return hunks
    
    def get_enrichment_type(self) -> str:
        return 'diff'
    
    def get_enrichment_category(self) -> str:
        return EnrichmentCategory.DIFF
