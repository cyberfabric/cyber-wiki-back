"""
Service for extracting display names from file content.
"""
import re
import os
from typing import Optional
import yaml


class NameExtractionService:
    """Extract display names from various file types."""
    
    @staticmethod
    def extract_from_markdown(content: str, source: str) -> Optional[str]:
        """
        Extract name from markdown file.
        
        Args:
            content: File content
            source: Extraction method ('first_h1', 'first_h2', 'title_frontmatter')
        
        Returns:
            Extracted name or None
        """
        if source == 'first_h1':
            # Find first # Header
            match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            return match.group(1).strip() if match else None
            
        elif source == 'first_h2':
            # Find first ## Header
            match = re.search(r'^##\s+(.+)$', content, re.MULTILINE)
            return match.group(1).strip() if match else None
            
        elif source == 'title_frontmatter':
            # Extract from YAML frontmatter
            match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if match:
                try:
                    frontmatter = yaml.safe_load(match.group(1))
                    if isinstance(frontmatter, dict):
                        return frontmatter.get('title')
                except yaml.YAMLError:
                    pass
        
        return None
    
    @staticmethod
    def extract_from_xml(content: str, source: str) -> Optional[str]:
        """
        Extract name from XML file (e.g., drawio).
        
        Args:
            content: File content
            source: Extraction method
        
        Returns:
            Extracted name or None
        """
        # For now, try to find a title or name attribute
        # This can be enhanced based on specific XML formats
        title_match = re.search(r'<title>(.+?)</title>', content, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        name_match = re.search(r'name="([^"]+)"', content)
        if name_match:
            return name_match.group(1).strip()
        
        return None
    
    @staticmethod
    def extract_name(file_path: str, content: str, source: str) -> Optional[str]:
        """
        Extract display name based on file type and source.
        
        Args:
            file_path: Path to the file
            content: File content
            source: Extraction method
        
        Returns:
            Extracted name or None
        """
        if source == 'filename':
            # Just return the filename without extension
            basename = os.path.basename(file_path)
            name, _ = os.path.splitext(basename)
            return name
        
        # Get file extension
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.md', '.markdown', '.mdx']:
            return NameExtractionService.extract_from_markdown(content, source)
        elif ext in ['.xml', '.drawio']:
            return NameExtractionService.extract_from_xml(content, source)
        
        # Fallback to filename
        basename = os.path.basename(file_path)
        name, _ = os.path.splitext(basename)
        return name
    
    @staticmethod
    def extract_names_bulk(files: list, git_provider, source: str) -> dict:
        """
        Extract names for multiple files in bulk.
        
        Args:
            files: List of file paths
            git_provider: Git provider instance to fetch content
            source: Extraction method
        
        Returns:
            Dict mapping file_path to extracted name
        """
        results = {}
        
        for file_path in files:
            try:
                # Fetch file content
                content = git_provider.get_file_content(file_path)
                
                # Extract name
                extracted = NameExtractionService.extract_name(file_path, content, source)
                if extracted:
                    results[file_path] = extracted
                else:
                    # Fallback to filename
                    basename = os.path.basename(file_path)
                    name, _ = os.path.splitext(basename)
                    results[file_path] = name
            except Exception as e:
                # On error, use filename
                basename = os.path.basename(file_path)
                name, _ = os.path.splitext(basename)
                results[file_path] = name
        
        return results
