"""
CyberWiki configuration parser for .cyberwiki.yml files.
"""
import yaml
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class CyberWikiConfig:
    """
    Parsed CyberWiki configuration from .cyberwiki.yml
    
    Example .cyberwiki.yml:
    ```yaml
    title_extraction: first_heading  # or frontmatter, filename
    include_patterns:
      - "docs/**/*.md"
      - "*.md"
    exclude_patterns:
      - "**/node_modules/**"
      - "**/.git/**"
    custom_order:
      - README.md
      - docs/getting-started.md
      - docs/api.md
    ```
    """
    title_extraction: str = 'first_heading'  # first_heading, frontmatter, filename
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    custom_order: List[str] = None
    
    def __post_init__(self):
        if self.include_patterns is None:
            self.include_patterns = ['**/*.md', '**/*.markdown']
        if self.exclude_patterns is None:
            self.exclude_patterns = [
                '**/node_modules/**',
                '**/.git/**',
                '**/venv/**',
                '**/__pycache__/**',
                '**/dist/**',
                '**/build/**',
            ]
        if self.custom_order is None:
            self.custom_order = []


class CyberWikiConfigParser:
    """
    Parser for .cyberwiki.yml configuration files.
    """
    
    @staticmethod
    def parse(content: str) -> CyberWikiConfig:
        """
        Parse YAML content into CyberWikiConfig.
        
        Args:
            content: YAML file content
        
        Returns:
            CyberWikiConfig instance
        """
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        return CyberWikiConfig(
            title_extraction=data.get('title_extraction', 'first_heading'),
            include_patterns=data.get('include_patterns'),
            exclude_patterns=data.get('exclude_patterns'),
            custom_order=data.get('custom_order'),
        )
    
    @staticmethod
    def parse_from_dict(data: Dict[str, Any]) -> CyberWikiConfig:
        """
        Parse dictionary into CyberWikiConfig.
        
        Args:
            data: Configuration dictionary
        
        Returns:
            CyberWikiConfig instance
        """
        return CyberWikiConfig(
            title_extraction=data.get('title_extraction', 'first_heading'),
            include_patterns=data.get('include_patterns'),
            exclude_patterns=data.get('exclude_patterns'),
            custom_order=data.get('custom_order'),
        )
    
    @staticmethod
    def get_default() -> CyberWikiConfig:
        """
        Get default configuration.
        
        Returns:
            Default CyberWikiConfig instance
        """
        return CyberWikiConfig()
