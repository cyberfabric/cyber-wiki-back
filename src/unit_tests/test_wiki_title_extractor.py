"""
Unit tests for wiki title extractor.

Tested Scenarios:
- Extract title from ATX-style heading (# Title)
- Extract title from Setext-style heading (Title\n====)
- Extract title from YAML frontmatter
- Extract title from filename (various formats)
- Fallback behavior when title not found
- Strategy selection (first_heading, frontmatter, filename)
- Special filename handling (README)
- Title case conversion from kebab-case and snake_case

Untested Scenarios / Gaps:
- Multiple H1 headings (only first is extracted)
- Malformed frontmatter
- Unicode in titles
- Very long titles
- Titles with markdown formatting

Test Strategy:
- Pure unit tests (no database)
- Test each extraction method independently
- Test fallback logic
- Test edge cases and empty inputs
"""
import pytest
from wiki.title_extractor import TitleExtractor


class TestTitleExtractorFirstHeading:
    """Tests for extracting title from first heading."""
    
    def test_extract_atx_heading(self):
        """Test extracting ATX-style heading (# Title)."""
        content = "# My Document Title\n\nSome content here."
        title = TitleExtractor.extract_first_heading(content)
        
        assert title == "My Document Title"
    
    def test_extract_atx_heading_with_extra_spaces(self):
        """Test extracting ATX heading with extra spaces."""
        content = "#   Title With Spaces   \n\nContent."
        title = TitleExtractor.extract_first_heading(content)
        
        assert title == "Title With Spaces"
    
    def test_extract_setext_heading(self):
        """Test extracting Setext-style heading (Title\n====)."""
        content = "My Document Title\n=================\n\nContent here."
        title = TitleExtractor.extract_first_heading(content)
        
        assert title == "My Document Title"
    
    def test_extract_setext_heading_short_underline(self):
        """Test extracting Setext heading with short underline."""
        content = "Title\n===\n\nContent."
        title = TitleExtractor.extract_first_heading(content)
        
        assert title == "Title"
    
    def test_no_heading_returns_none(self):
        """Test that content without heading returns None."""
        content = "This is just regular content without any headings."
        title = TitleExtractor.extract_first_heading(content)
        
        assert title is None
    
    def test_empty_content_returns_none(self):
        """Test that empty content returns None."""
        content = ""
        title = TitleExtractor.extract_first_heading(content)
        
        assert title is None
    
    def test_h2_heading_not_extracted(self):
        """Test that H2 heading is not extracted."""
        content = "## This is H2\n\nContent."
        title = TitleExtractor.extract_first_heading(content)
        
        assert title is None
    
    def test_first_h1_is_extracted(self):
        """Test that only first H1 is extracted."""
        content = "# First Title\n\nSome content.\n\n# Second Title"
        title = TitleExtractor.extract_first_heading(content)
        
        assert title == "First Title"


class TestTitleExtractorFrontmatter:
    """Tests for extracting title from frontmatter."""
    
    def test_extract_from_frontmatter(self):
        """Test extracting title from YAML frontmatter."""
        content = """---
title: My Document Title
author: John Doe
---

Content here."""
        title = TitleExtractor.extract_from_frontmatter(content)
        
        assert title == "My Document Title"
    
    def test_extract_frontmatter_with_quotes(self):
        """Test extracting title with quotes in frontmatter."""
        content = """---
title: "My Document Title"
---

Content."""
        title = TitleExtractor.extract_from_frontmatter(content)
        
        assert title == "My Document Title"
    
    def test_extract_frontmatter_with_single_quotes(self):
        """Test extracting title with single quotes."""
        content = """---
title: 'My Document Title'
---

Content."""
        title = TitleExtractor.extract_from_frontmatter(content)
        
        assert title == "My Document Title"
    
    def test_no_frontmatter_returns_none(self):
        """Test that content without frontmatter returns None."""
        content = "# Regular Heading\n\nContent."
        title = TitleExtractor.extract_from_frontmatter(content)
        
        assert title is None
    
    def test_frontmatter_without_title_returns_none(self):
        """Test that frontmatter without title field returns None."""
        content = """---
author: John Doe
date: 2024-01-01
---

Content."""
        title = TitleExtractor.extract_from_frontmatter(content)
        
        assert title is None
    
    def test_empty_content_returns_none(self):
        """Test that empty content returns None."""
        content = ""
        title = TitleExtractor.extract_from_frontmatter(content)
        
        assert title is None


class TestTitleExtractorFilename:
    """Tests for extracting title from filename."""
    
    def test_extract_from_simple_filename(self):
        """Test extracting title from simple filename."""
        title = TitleExtractor.extract_from_filename("document.md")
        
        assert title == "Document"
    
    def test_extract_from_kebab_case(self):
        """Test extracting title from kebab-case filename."""
        title = TitleExtractor.extract_from_filename("my-document-title.md")
        
        assert title == "My Document Title"
    
    def test_extract_from_snake_case(self):
        """Test extracting title from snake_case filename."""
        title = TitleExtractor.extract_from_filename("my_document_title.md")
        
        assert title == "My Document Title"
    
    def test_extract_from_mixed_case(self):
        """Test extracting title from mixed separators."""
        title = TitleExtractor.extract_from_filename("my-document_title.md")
        
        assert title == "My Document Title"
    
    def test_readme_special_case(self):
        """Test that README is handled specially."""
        title = TitleExtractor.extract_from_filename("readme.md")
        
        assert title == "README"
    
    def test_readme_uppercase(self):
        """Test README in uppercase."""
        title = TitleExtractor.extract_from_filename("README.md")
        
        assert title == "README"
    
    def test_extract_from_path(self):
        """Test extracting title from full path."""
        title = TitleExtractor.extract_from_filename("docs/guides/getting-started.md")
        
        assert title == "Getting Started"
    
    def test_extract_without_extension(self):
        """Test extracting from filename without extension."""
        title = TitleExtractor.extract_from_filename("my-document")
        
        assert title == "My Document"


class TestTitleExtractorStrategy:
    """Tests for title extraction with different strategies."""
    
    def test_first_heading_strategy(self):
        """Test first_heading strategy."""
        content = """---
title: Frontmatter Title
---

# Heading Title

Content."""
        title = TitleExtractor.extract(content, "document.md", strategy="first_heading")
        
        # Should prefer heading over frontmatter
        assert title == "Heading Title"
    
    def test_frontmatter_strategy(self):
        """Test frontmatter strategy."""
        content = """---
title: Frontmatter Title
---

# Heading Title

Content."""
        title = TitleExtractor.extract(content, "document.md", strategy="frontmatter")
        
        # Should prefer frontmatter over heading
        assert title == "Frontmatter Title"
    
    def test_filename_strategy(self):
        """Test filename strategy."""
        content = """---
title: Frontmatter Title
---

# Heading Title

Content."""
        title = TitleExtractor.extract(content, "my-document.md", strategy="filename")
        
        # Should use filename regardless of content
        assert title == "My Document"
    
    def test_first_heading_fallback_to_frontmatter(self):
        """Test first_heading strategy falls back to frontmatter."""
        content = """---
title: Frontmatter Title
---

No heading here."""
        title = TitleExtractor.extract(content, "document.md", strategy="first_heading")
        
        assert title == "Frontmatter Title"
    
    def test_frontmatter_fallback_to_heading(self):
        """Test frontmatter strategy falls back to heading."""
        content = "# Heading Title\n\nNo frontmatter."
        title = TitleExtractor.extract(content, "document.md", strategy="frontmatter")
        
        assert title == "Heading Title"
    
    def test_fallback_to_filename(self):
        """Test final fallback to filename."""
        content = "Just plain content with no title."
        title = TitleExtractor.extract(content, "my-document.md", strategy="first_heading")
        
        # Should fall back to filename
        assert title == "My Document"
    
    def test_unknown_strategy_uses_default(self):
        """Test that unknown strategy uses default (first_heading)."""
        content = "# Heading Title\n\nContent."
        title = TitleExtractor.extract(content, "document.md", strategy="unknown")
        
        assert title == "Heading Title"
    
    def test_empty_content_uses_filename(self):
        """Test that empty content falls back to filename."""
        content = ""
        title = TitleExtractor.extract(content, "my-document.md", strategy="first_heading")
        
        assert title == "My Document"
    
    def test_always_returns_value(self):
        """Test that extract() always returns a value."""
        # Even with empty content and no strategy
        title = TitleExtractor.extract("", "file.md")
        
        assert title is not None
        assert title == "File"
