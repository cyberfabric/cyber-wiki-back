"""
Unit tests for CyberWiki configuration parser.

Tested Scenarios:
- Default configuration values
- Parsing YAML with all fields
- Parsing YAML with partial fields
- Parsing empty YAML
- Invalid YAML handling
- Parsing from dictionary
- Custom title extraction modes
- Include/exclude patterns
- Custom file ordering

Untested Scenarios / Gaps:
- Pattern matching logic (tested elsewhere)
- File system integration
- Configuration validation rules
- Merging configurations
- Configuration inheritance

Test Strategy:
- Pure unit tests (no database)
- Test YAML parsing and defaults
- Test error handling
- Test all configuration options
"""
import pytest
from wiki.config_parser import CyberWikiConfig, CyberWikiConfigParser


class TestCyberWikiConfig:
    """Tests for CyberWikiConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CyberWikiConfig()
        
        assert config.title_extraction == 'first_heading'
        assert config.include_patterns == ['**/*.md', '**/*.markdown']
        assert '**/node_modules/**' in config.exclude_patterns
        assert '**/.git/**' in config.exclude_patterns
        assert '**/venv/**' in config.exclude_patterns
        assert config.custom_order == []
    
    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = CyberWikiConfig(
            title_extraction='frontmatter',
            include_patterns=['docs/**/*.md'],
            exclude_patterns=['**/test/**'],
            custom_order=['README.md', 'CHANGELOG.md']
        )
        
        assert config.title_extraction == 'frontmatter'
        assert config.include_patterns == ['docs/**/*.md']
        assert config.exclude_patterns == ['**/test/**']
        assert config.custom_order == ['README.md', 'CHANGELOG.md']


class TestCyberWikiConfigParser:
    """Tests for CyberWikiConfigParser."""
    
    def test_parse_empty_yaml(self):
        """Test parsing empty YAML uses defaults."""
        content = ""
        config = CyberWikiConfigParser.parse(content)
        
        assert config.title_extraction == 'first_heading'
        assert config.include_patterns == ['**/*.md', '**/*.markdown']
        assert len(config.exclude_patterns) > 0
        assert config.custom_order == []
    
    def test_parse_yaml_with_all_fields(self):
        """Test parsing YAML with all configuration fields."""
        content = """
title_extraction: frontmatter
include_patterns:
  - "docs/**/*.md"
  - "*.md"
exclude_patterns:
  - "**/node_modules/**"
  - "**/test/**"
custom_order:
  - README.md
  - docs/getting-started.md
  - docs/api.md
"""
        config = CyberWikiConfigParser.parse(content)
        
        assert config.title_extraction == 'frontmatter'
        assert config.include_patterns == ['docs/**/*.md', '*.md']
        assert config.exclude_patterns == ['**/node_modules/**', '**/test/**']
        assert config.custom_order == ['README.md', 'docs/getting-started.md', 'docs/api.md']
    
    def test_parse_yaml_with_partial_fields(self):
        """Test parsing YAML with only some fields specified."""
        content = """
title_extraction: filename
include_patterns:
  - "**/*.md"
"""
        config = CyberWikiConfigParser.parse(content)
        
        assert config.title_extraction == 'filename'
        assert config.include_patterns == ['**/*.md']
        # Should use defaults for unspecified fields
        assert len(config.exclude_patterns) > 0
        assert config.custom_order == []
    
    def test_parse_yaml_title_extraction_modes(self):
        """Test different title extraction modes."""
        modes = ['first_heading', 'frontmatter', 'filename']
        
        for mode in modes:
            content = f"title_extraction: {mode}"
            config = CyberWikiConfigParser.parse(content)
            assert config.title_extraction == mode
    
    def test_parse_invalid_yaml(self):
        """Test that invalid YAML raises ValueError."""
        invalid_yaml = """
title_extraction: frontmatter
  invalid indentation:
    - item
"""
        with pytest.raises(ValueError, match="Invalid YAML"):
            CyberWikiConfigParser.parse(invalid_yaml)
    
    def test_parse_yaml_with_comments(self):
        """Test parsing YAML with comments."""
        content = """
# This is a comment
title_extraction: first_heading  # inline comment
include_patterns:
  - "docs/**/*.md"  # documentation files
  - "*.md"  # root markdown files
"""
        config = CyberWikiConfigParser.parse(content)
        
        assert config.title_extraction == 'first_heading'
        assert config.include_patterns == ['docs/**/*.md', '*.md']
    
    def test_parse_from_dict_with_all_fields(self):
        """Test parsing from dictionary with all fields."""
        data = {
            'title_extraction': 'frontmatter',
            'include_patterns': ['docs/**/*.md'],
            'exclude_patterns': ['**/test/**'],
            'custom_order': ['README.md']
        }
        
        config = CyberWikiConfigParser.parse_from_dict(data)
        
        assert config.title_extraction == 'frontmatter'
        assert config.include_patterns == ['docs/**/*.md']
        assert config.exclude_patterns == ['**/test/**']
        assert config.custom_order == ['README.md']
    
    def test_parse_from_dict_with_partial_fields(self):
        """Test parsing from dictionary with partial fields."""
        data = {
            'title_extraction': 'filename'
        }
        
        config = CyberWikiConfigParser.parse_from_dict(data)
        
        assert config.title_extraction == 'filename'
        # Should use defaults for missing fields
        assert config.include_patterns == ['**/*.md', '**/*.markdown']
        assert len(config.exclude_patterns) > 0
    
    def test_parse_from_empty_dict(self):
        """Test parsing from empty dictionary uses defaults."""
        data = {}
        config = CyberWikiConfigParser.parse_from_dict(data)
        
        assert config.title_extraction == 'first_heading'
        assert config.include_patterns == ['**/*.md', '**/*.markdown']
        assert len(config.exclude_patterns) > 0
    
    def test_get_default(self):
        """Test getting default configuration."""
        config = CyberWikiConfigParser.get_default()
        
        assert config.title_extraction == 'first_heading'
        assert config.include_patterns == ['**/*.md', '**/*.markdown']
        assert '**/node_modules/**' in config.exclude_patterns
        assert config.custom_order == []
    
    def test_parse_yaml_with_empty_lists(self):
        """Test parsing YAML with explicitly empty lists."""
        content = """
title_extraction: first_heading
include_patterns: []
exclude_patterns: []
custom_order: []
"""
        config = CyberWikiConfigParser.parse(content)
        
        # Empty lists should be preserved, not replaced with defaults
        assert config.include_patterns == []
        assert config.exclude_patterns == []
        assert config.custom_order == []
    
    def test_default_exclude_patterns_comprehensive(self):
        """Test that default exclude patterns cover common directories."""
        config = CyberWikiConfig()
        
        expected_patterns = [
            '**/node_modules/**',
            '**/.git/**',
            '**/venv/**',
            '**/__pycache__/**',
            '**/dist/**',
            '**/build/**',
        ]
        
        for pattern in expected_patterns:
            assert pattern in config.exclude_patterns
