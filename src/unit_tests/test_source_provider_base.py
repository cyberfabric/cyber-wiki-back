"""
Unit tests for source provider base module.

Tested Scenarios:
- SourceAddress parsing from URI (various formats)
- SourceAddress with line numbers (single and range)
- SourceAddress without line numbers
- SourceAddress to_uri() conversion
- SourceAddress string representation
- Invalid URI format handling
- Edge cases (empty paths, special characters)

Untested Scenarios / Gaps:
- BaseSourceProvider implementations (abstract class)
- URI encoding/decoding for special characters
- Very long paths or repository names
- Unicode in paths
- Case sensitivity in provider names

Test Strategy:
- Pure unit tests (no database)
- Test parsing and serialization
- Test error handling
- Test round-trip conversion (parse → to_uri)
"""
import pytest
from source_provider.base import SourceAddress, BaseSourceProvider


class TestSourceAddress:
    """Tests for SourceAddress dataclass."""
    
    def test_parse_simple_uri(self):
        """Test parsing a simple URI without line numbers."""
        uri = "git://github/facebook_react/main/README.md"
        addr = SourceAddress.parse(uri)
        
        assert addr.provider == "github"
        assert addr.repository == "facebook_react"
        assert addr.branch == "main"
        assert addr.path == "README.md"
        assert addr.line_start is None
        assert addr.line_end is None
    
    def test_parse_uri_with_single_line(self):
        """Test parsing URI with single line number."""
        uri = "git://github/facebook_react/main/src/index.js#42"
        addr = SourceAddress.parse(uri)
        
        assert addr.provider == "github"
        assert addr.repository == "facebook_react"
        assert addr.branch == "main"
        assert addr.path == "src/index.js"
        assert addr.line_start == 42
        assert addr.line_end is None
    
    def test_parse_uri_with_line_range(self):
        """Test parsing URI with line range."""
        uri = "git://github/facebook_react/main/src/index.js#10-20"
        addr = SourceAddress.parse(uri)
        
        assert addr.provider == "github"
        assert addr.repository == "facebook_react"
        assert addr.branch == "main"
        assert addr.path == "src/index.js"
        assert addr.line_start == 10
        assert addr.line_end == 20
    
    def test_parse_uri_with_nested_path(self):
        """Test parsing URI with deeply nested path."""
        uri = "git://bitbucket_server/PROJECT_repo/develop/src/components/Button/index.tsx#5-15"
        addr = SourceAddress.parse(uri)
        
        assert addr.provider == "bitbucket_server"
        assert addr.repository == "PROJECT_repo"
        assert addr.branch == "develop"
        assert addr.path == "src/components/Button/index.tsx"
        assert addr.line_start == 5
        assert addr.line_end == 15
    
    def test_parse_invalid_uri_format(self):
        """Test that invalid URI format raises ValueError."""
        invalid_uris = [
            "not-a-git-uri",
            "git://",
            "git://github",
            "git://github/repo",
            "git://github/repo/branch",  # Missing path
            "http://github.com/repo",
            "git:/github/repo/branch/path",  # Missing //
        ]
        
        for uri in invalid_uris:
            with pytest.raises(ValueError, match="Invalid source URI format"):
                SourceAddress.parse(uri)
    
    def test_to_uri_without_lines(self):
        """Test converting SourceAddress to URI without line numbers."""
        addr = SourceAddress(
            provider="github",
            repository="facebook_react",
            branch="main",
            path="README.md"
        )
        
        assert addr.to_uri() == "git://github/facebook_react/main/README.md"
    
    def test_to_uri_with_single_line(self):
        """Test converting SourceAddress to URI with single line."""
        addr = SourceAddress(
            provider="github",
            repository="facebook_react",
            branch="main",
            path="src/index.js",
            line_start=42
        )
        
        assert addr.to_uri() == "git://github/facebook_react/main/src/index.js#42"
    
    def test_to_uri_with_line_range(self):
        """Test converting SourceAddress to URI with line range."""
        addr = SourceAddress(
            provider="github",
            repository="facebook_react",
            branch="main",
            path="src/index.js",
            line_start=10,
            line_end=20
        )
        
        assert addr.to_uri() == "git://github/facebook_react/main/src/index.js#10-20"
    
    def test_to_uri_with_same_start_end_line(self):
        """Test that same start and end line shows as single line."""
        addr = SourceAddress(
            provider="github",
            repository="facebook_react",
            branch="main",
            path="src/index.js",
            line_start=42,
            line_end=42
        )
        
        # Should show as single line, not range
        assert addr.to_uri() == "git://github/facebook_react/main/src/index.js#42"
    
    def test_string_representation(self):
        """Test __str__ returns URI."""
        addr = SourceAddress(
            provider="github",
            repository="facebook_react",
            branch="main",
            path="README.md",
            line_start=10,
            line_end=20
        )
        
        assert str(addr) == "git://github/facebook_react/main/README.md#10-20"
    
    def test_round_trip_conversion(self):
        """Test that parse → to_uri is idempotent."""
        original_uri = "git://bitbucket_server/PROJECT_repo/feature-branch/docs/api.md#100-200"
        
        addr = SourceAddress.parse(original_uri)
        converted_uri = addr.to_uri()
        
        assert converted_uri == original_uri
    
    def test_parse_path_with_dots(self):
        """Test parsing path with multiple dots."""
        uri = "git://github/repo/main/config.test.js"
        addr = SourceAddress.parse(uri)
        
        assert addr.path == "config.test.js"
    
    def test_parse_branch_with_slashes(self):
        """Test parsing branch name with slashes (feature branches)."""
        uri = "git://github/repo/feature/new-feature/README.md"
        addr = SourceAddress.parse(uri)
        
        # Note: This will parse 'feature' as branch and 'new-feature/README.md' as path
        # This is expected behavior based on the current regex
        assert addr.branch == "feature"
        assert addr.path == "new-feature/README.md"


class TestBaseSourceProvider:
    """Tests for BaseSourceProvider abstract class."""
    
    def test_get_content_not_implemented(self):
        """Test that get_content raises NotImplementedError."""
        provider = BaseSourceProvider()
        addr = SourceAddress(
            provider="github",
            repository="repo",
            branch="main",
            path="file.txt"
        )
        
        with pytest.raises(NotImplementedError):
            provider.get_content(addr)
    
    def test_get_tree_not_implemented(self):
        """Test that get_tree raises NotImplementedError."""
        provider = BaseSourceProvider()
        addr = SourceAddress(
            provider="github",
            repository="repo",
            branch="main",
            path="src"
        )
        
        with pytest.raises(NotImplementedError):
            provider.get_tree(addr)
