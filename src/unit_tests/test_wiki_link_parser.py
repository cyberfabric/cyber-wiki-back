"""
Unit tests for wiki link parser.

Tested Scenarios:
- Extract markdown links from content
- Extract links with various text formats
- Extract multiple links from content
- Classify internal links (.md, .markdown)
- Classify external links (http://, https://)
- Classify reference links (anchors, relative paths)
- Extract and classify all links together
- Handle empty content
- Handle content with no links

Untested Scenarios / Gaps:
- Image links ![alt](url)
- Reference-style links [text][ref]
- Autolinks <url>
- HTML links <a href="">
- Malformed markdown links
- Links with special characters in URL
- Very long URLs

Test Strategy:
- Pure unit tests (no database)
- Test regex pattern matching
- Test link classification logic
- Test edge cases and empty inputs
"""
import pytest
from wiki.link_parser import LinkParser


class TestLinkParserExtraction:
    """Tests for markdown link extraction."""
    
    def test_extract_single_link(self):
        """Test extracting a single markdown link."""
        content = "Check out [this page](https://example.com)"
        links = LinkParser.extract_markdown_links(content)
        
        assert len(links) == 1
        assert links[0]['text'] == 'this page'
        assert links[0]['url'] == 'https://example.com'
    
    def test_extract_multiple_links(self):
        """Test extracting multiple markdown links."""
        content = """
        Here are some links:
        - [Link 1](https://example.com)
        - [Link 2](https://another.com)
        - [Link 3](/docs/page.md)
        """
        links = LinkParser.extract_markdown_links(content)
        
        assert len(links) == 3
        assert links[0]['text'] == 'Link 1'
        assert links[0]['url'] == 'https://example.com'
        assert links[1]['text'] == 'Link 2'
        assert links[1]['url'] == 'https://another.com'
        assert links[2]['text'] == 'Link 3'
        assert links[2]['url'] == '/docs/page.md'
    
    def test_extract_link_with_spaces(self):
        """Test extracting link with spaces in text and URL."""
        content = "[  Link Text  ](  https://example.com  )"
        links = LinkParser.extract_markdown_links(content)
        
        assert len(links) == 1
        assert links[0]['text'] == 'Link Text'  # Stripped
        assert links[0]['url'] == 'https://example.com'  # Stripped
    
    def test_extract_empty_content(self):
        """Test extracting links from empty content."""
        content = ""
        links = LinkParser.extract_markdown_links(content)
        
        assert links == []
    
    def test_extract_no_links(self):
        """Test extracting from content with no links."""
        content = "This is just plain text with no links."
        links = LinkParser.extract_markdown_links(content)
        
        assert links == []
    
    def test_extract_link_with_special_characters(self):
        """Test extracting link with special characters in text."""
        content = "[Link with **bold** and _italic_](https://example.com)"
        links = LinkParser.extract_markdown_links(content)
        
        assert len(links) == 1
        assert links[0]['text'] == 'Link with **bold** and _italic_'
        assert links[0]['url'] == 'https://example.com'
    
    def test_extract_link_with_query_params(self):
        """Test extracting link with query parameters."""
        content = "[Search](https://example.com/search?q=test&page=1)"
        links = LinkParser.extract_markdown_links(content)
        
        assert len(links) == 1
        assert links[0]['url'] == 'https://example.com/search?q=test&page=1'
    
    def test_extract_link_with_anchor(self):
        """Test extracting link with anchor."""
        content = "[Section](#section-name)"
        links = LinkParser.extract_markdown_links(content)
        
        assert len(links) == 1
        assert links[0]['text'] == 'Section'
        assert links[0]['url'] == '#section-name'


class TestLinkParserClassification:
    """Tests for link classification."""
    
    def test_classify_external_http(self):
        """Test classifying HTTP external link."""
        assert LinkParser.classify_link('http://example.com') == 'external'
    
    def test_classify_external_https(self):
        """Test classifying HTTPS external link."""
        assert LinkParser.classify_link('https://example.com') == 'external'
    
    def test_classify_external_protocol_relative(self):
        """Test classifying protocol-relative external link."""
        assert LinkParser.classify_link('//example.com') == 'external'
    
    def test_classify_internal_md(self):
        """Test classifying internal .md link."""
        assert LinkParser.classify_link('docs/page.md') == 'internal'
        assert LinkParser.classify_link('./docs/page.md') == 'internal'
        assert LinkParser.classify_link('../docs/page.md') == 'internal'
    
    def test_classify_internal_markdown(self):
        """Test classifying internal .markdown link."""
        assert LinkParser.classify_link('docs/page.markdown') == 'internal'
    
    def test_classify_reference_anchor(self):
        """Test classifying anchor reference."""
        assert LinkParser.classify_link('#section') == 'reference'
        assert LinkParser.classify_link('#section-name') == 'reference'
    
    def test_classify_reference_relative_path(self):
        """Test classifying relative path without extension."""
        assert LinkParser.classify_link('docs/page') == 'reference'
        assert LinkParser.classify_link('./file') == 'reference'
        assert LinkParser.classify_link('../other') == 'reference'
    
    def test_classify_reference_file_with_extension(self):
        """Test classifying file with non-markdown extension."""
        assert LinkParser.classify_link('image.png') == 'reference'
        assert LinkParser.classify_link('docs/file.pdf') == 'reference'
        assert LinkParser.classify_link('script.js') == 'reference'


class TestLinkParserExtractAll:
    """Tests for extracting and classifying all links."""
    
    def test_extract_all_mixed_links(self):
        """Test extracting and classifying mixed link types."""
        content = """
        - [External](https://example.com)
        - [Internal](docs/page.md)
        - [Anchor](#section)
        - [Reference](./file)
        """
        links = LinkParser.extract_all_links(content)
        
        assert len(links) == 4
        
        assert links[0]['text'] == 'External'
        assert links[0]['url'] == 'https://example.com'
        assert links[0]['type'] == 'external'
        
        assert links[1]['text'] == 'Internal'
        assert links[1]['url'] == 'docs/page.md'
        assert links[1]['type'] == 'internal'
        
        assert links[2]['text'] == 'Anchor'
        assert links[2]['url'] == '#section'
        assert links[2]['type'] == 'reference'
        
        assert links[3]['text'] == 'Reference'
        assert links[3]['url'] == './file'
        assert links[3]['type'] == 'reference'
    
    def test_extract_all_empty_content(self):
        """Test extracting all links from empty content."""
        content = ""
        links = LinkParser.extract_all_links(content)
        
        assert links == []
    
    def test_extract_all_only_external(self):
        """Test extracting all links when only external links present."""
        content = """
        [Link 1](https://example.com)
        [Link 2](http://another.com)
        """
        links = LinkParser.extract_all_links(content)
        
        assert len(links) == 2
        assert all(link['type'] == 'external' for link in links)
    
    def test_extract_all_only_internal(self):
        """Test extracting all links when only internal links present."""
        content = """
        [Page 1](docs/page1.md)
        [Page 2](docs/page2.markdown)
        """
        links = LinkParser.extract_all_links(content)
        
        assert len(links) == 2
        assert all(link['type'] == 'internal' for link in links)
    
    def test_extract_all_preserves_order(self):
        """Test that link extraction preserves order."""
        content = "[First](url1) [Second](url2) [Third](url3)"
        links = LinkParser.extract_all_links(content)
        
        assert len(links) == 3
        assert links[0]['text'] == 'First'
        assert links[1]['text'] == 'Second'
        assert links[2]['text'] == 'Third'
    
    def test_extract_all_with_duplicate_urls(self):
        """Test extracting links with duplicate URLs."""
        content = """
        [Link 1](https://example.com)
        [Link 2](https://example.com)
        """
        links = LinkParser.extract_all_links(content)
        
        # Should extract both, even if URLs are the same
        assert len(links) == 2
        assert links[0]['url'] == links[1]['url']
        assert links[0]['text'] != links[1]['text']
