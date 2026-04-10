"""
Link extraction and parsing from markdown content.
"""
import re
from typing import List, Dict
from urllib.parse import urlparse


class LinkParser:
    """
    Extract and parse links from markdown content.
    """
    
    @staticmethod
    def extract_markdown_links(content: str) -> List[Dict[str, str]]:
        """
        Extract markdown links from content.
        
        Args:
            content: Markdown content
        
        Returns:
            List of dicts with 'text' and 'url' keys
        """
        # Pattern: [text](url)
        pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        matches = re.findall(pattern, content)
        
        links = []
        for text, url in matches:
            links.append({
                'text': text.strip(),
                'url': url.strip()
            })
        
        return links
    
    @staticmethod
    def classify_link(url: str) -> str:
        """
        Classify link as internal, external, or reference.
        
        Args:
            url: Link URL
        
        Returns:
            Link type: 'internal', 'external', or 'reference'
        """
        # Reference links (anchors, relative paths without extension)
        if url.startswith('#'):
            return 'reference'
        
        # Check if it's a relative path
        if not url.startswith(('http://', 'https://', '//')):
            # Relative path - could be internal document
            if url.endswith(('.md', '.markdown')):
                return 'internal'
            return 'reference'
        
        # Absolute URL - external
        return 'external'
    
    @staticmethod
    def extract_all_links(content: str) -> List[Dict[str, str]]:
        """
        Extract all links and classify them.
        
        Args:
            content: Markdown content
        
        Returns:
            List of dicts with 'text', 'url', and 'type' keys
        """
        markdown_links = LinkParser.extract_markdown_links(content)
        
        classified_links = []
        for link in markdown_links:
            link_type = LinkParser.classify_link(link['url'])
            classified_links.append({
                'text': link['text'],
                'url': link['url'],
                'type': link_type
            })
        
        return classified_links
