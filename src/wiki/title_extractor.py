"""
Title extraction from markdown files using various strategies.
"""
import re
from typing import Optional
from pathlib import Path


class TitleExtractor:
    """
    Extract document titles from markdown content using different strategies.
    """
    
    @staticmethod
    def extract_first_heading(content: str) -> Optional[str]:
        """
        Extract title from first H1 heading in markdown.
        
        Args:
            content: Markdown content
        
        Returns:
            Title string or None
        """
        # Match # Heading or === underline style
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # ATX-style heading: # Title
            match = re.match(r'^#\s+(.+)$', line.strip())
            if match:
                return match.group(1).strip()
            
            # Setext-style heading: Title\n====
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'^=+$', next_line) and line.strip():
                    return line.strip()
        
        return None
    
    @staticmethod
    def extract_from_frontmatter(content: str) -> Optional[str]:
        """
        Extract title from YAML frontmatter.
        
        Args:
            content: Markdown content with frontmatter
        
        Returns:
            Title string or None
        """
        # Match YAML frontmatter: ---\ntitle: ...\n---
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(frontmatter_pattern, content, re.DOTALL)
        
        if not match:
            return None
        
        frontmatter = match.group(1)
        
        # Extract title field
        title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        
        return None
    
    @staticmethod
    def extract_from_filename(file_path: str) -> str:
        """
        Extract title from filename.
        
        Args:
            file_path: File path
        
        Returns:
            Title derived from filename
        """
        # Get filename without extension
        filename = Path(file_path).stem
        
        # Convert kebab-case and snake_case to Title Case
        # my-document.md -> My Document
        # my_document.md -> My Document
        title = filename.replace('-', ' ').replace('_', ' ')
        
        # Title case
        title = title.title()
        
        # Special handling for common patterns
        if title.lower() == 'readme':
            return 'README'
        
        return title
    
    @staticmethod
    def extract(content: str, file_path: str, strategy: str = 'first_heading') -> str:
        """
        Extract title using specified strategy with fallback.
        
        Args:
            content: Markdown content
            file_path: File path
            strategy: Extraction strategy ('first_heading', 'frontmatter', 'filename')
        
        Returns:
            Extracted title (always returns a value)
        """
        title = None
        
        if strategy == 'frontmatter':
            title = TitleExtractor.extract_from_frontmatter(content)
            if not title:
                title = TitleExtractor.extract_first_heading(content)
        elif strategy == 'first_heading':
            title = TitleExtractor.extract_first_heading(content)
            if not title:
                title = TitleExtractor.extract_from_frontmatter(content)
        elif strategy == 'filename':
            title = TitleExtractor.extract_from_filename(file_path)
        else:
            # Default to first_heading
            title = TitleExtractor.extract_first_heading(content)
        
        # Final fallback to filename
        if not title:
            title = TitleExtractor.extract_from_filename(file_path)
        
        return title
