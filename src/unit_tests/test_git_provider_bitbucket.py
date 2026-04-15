"""
Unit tests for Bitbucket Server nested path handling.

Tested Scenarios:
- Root level nested paths are collapsed to top-level directories
- Multiple nested paths sharing same top-level directory are deduplicated
- Subdirectory nested paths are collapsed correctly
- Normal (non-nested) paths remain unchanged
- Mixed nested and normal paths are handled correctly

Untested Scenarios / Gaps:
- Very deep nesting (> 5 levels)
- Special characters in path names
- Unicode characters in paths
- Empty path handling
- Path normalization edge cases
- Performance with large directory trees

Test Strategy:
- Pure unit tests with mocks (no database)
- Mock Bitbucket API responses
- Test path collapsing logic in isolation
- Fast execution (< 1 second per test)
"""
import pytest
from unittest.mock import patch
from git_provider.providers.bitbucket_server import BitbucketServerProvider
from unit_tests.test_helpers import create_mock_response


class TestBitbucketNestedPaths:
    """Test Bitbucket Server provider handles nested paths correctly."""
    
    @pytest.fixture
    def provider(self):
        """Create a Bitbucket provider instance."""
        return BitbucketServerProvider(
            base_url='https://git.example.com',
            token='test-token',
            username='test-user'
        )
    
    def test_root_level_nested_paths_are_collapsed(self, provider):
        """
        Test that when Bitbucket returns nested paths at root level,
        we extract only the top-level directory.
        
        Example: ".agents/skills" should become ".agents"
        """
        # Mock Bitbucket API response with nested paths
        mock_response = create_mock_response(200, {
            'children': {
                'values': [
                    {
                        'path': {'toString': '.agents/skills'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': '.github/workflows'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': 'README.md'},
                        'type': 'FILE',
                        'size': 1234
                    },
                    {
                        'path': {'toString': 'docs'},
                        'type': 'DIRECTORY',
                        'size': 0
                    }
                ]
            }
        })
        
        with patch.object(provider, '_request', return_value=mock_response):
            result = provider.get_directory_tree('PROJECT', 'repo', path='', branch='main')
        
        # Extract paths from result
        paths = [item['path'] for item in result]
        
        # Should have collapsed nested paths to top-level only
        assert '.agents' in paths, "Should have .agents directory"
        assert '.agents/skills' not in paths, "Should NOT have nested .agents/skills"
        assert '.github' in paths, "Should have .github directory"
        assert '.github/workflows' not in paths, "Should NOT have nested .github/workflows"
        assert 'README.md' in paths, "Should have README.md file"
        assert 'docs' in paths, "Should have docs directory"
        
        # Should have exactly 4 items (2 collapsed dirs + 1 file + 1 normal dir)
        assert len(result) == 4, f"Expected 4 items, got {len(result)}: {paths}"
    
    def test_root_level_no_duplicates(self, provider):
        """
        Test that when multiple nested paths share the same top-level directory,
        we only return one entry for that directory.
        
        Example: ".agents/skills" and ".agents/workflows" should both become ".agents"
        """
        mock_response = create_mock_response(200, {
            'children': {
                'values': [
                    {
                        'path': {'toString': '.agents/skills'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': '.agents/workflows'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': '.agents/templates'},
                        'type': 'DIRECTORY',
                        'size': 0
                    }
                ]
            }
        })
        
        with patch.object(provider, '_request', return_value=mock_response):
            result = provider.get_directory_tree('PROJECT', 'repo', path='', branch='main')
        
        paths = [item['path'] for item in result]
        
        # Should have only ONE .agents entry
        assert paths.count('.agents') == 1, f"Should have exactly 1 .agents entry, got {paths.count('.agents')}"
        assert len(result) == 1, f"Expected 1 item, got {len(result)}: {paths}"
    
    def test_subdirectory_nested_paths_are_collapsed(self, provider):
        """
        Test that nested paths in subdirectories are also handled correctly.
        
        Example: When in "src/", path "components/ui/Button" should become "components"
        """
        mock_response = create_mock_response(200, {
            'children': {
                'values': [
                    {
                        'path': {'toString': 'components/ui/Button'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': 'utils/helpers'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': 'index.ts'},
                        'type': 'FILE',
                        'size': 500
                    }
                ]
            }
        })
        
        with patch.object(provider, '_request', return_value=mock_response):
            result = provider.get_directory_tree('PROJECT', 'repo', path='src', branch='main')
        
        paths = [item['path'] for item in result]
        
        # Should have collapsed to immediate children only
        assert 'src/components' in paths, "Should have src/components"
        assert 'src/components/ui/Button' not in paths, "Should NOT have deeply nested path"
        assert 'src/utils' in paths, "Should have src/utils"
        assert 'src/index.ts' in paths, "Should have src/index.ts"
        
        assert len(result) == 3, f"Expected 3 items, got {len(result)}: {paths}"
    
    def test_normal_paths_unchanged(self, provider):
        """
        Test that normal (non-nested) paths are returned as-is.
        """
        mock_response = create_mock_response(200, {
            'children': {
                'values': [
                    {
                        'path': {'toString': 'README.md'},
                        'type': 'FILE',
                        'size': 1234
                    },
                    {
                        'path': {'toString': 'docs'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': 'src'},
                        'type': 'DIRECTORY',
                        'size': 0
                    }
                ]
            }
        })
        
        with patch.object(provider, '_request', return_value=mock_response):
            result = provider.get_directory_tree('PROJECT', 'repo', path='', branch='main')
        
        paths = [item['path'] for item in result]
        
        # All paths should be returned unchanged
        assert 'README.md' in paths
        assert 'docs' in paths
        assert 'src' in paths
        assert len(result) == 3
    
    def test_mixed_nested_and_normal_paths(self, provider):
        """
        Test handling of a mix of nested and normal paths.
        """
        mock_response = create_mock_response(200, {
            'children': {
                'values': [
                    {
                        'path': {'toString': '.agents/skills'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': 'README.md'},
                        'type': 'FILE',
                        'size': 1234
                    },
                    {
                        'path': {'toString': 'docs'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': '.github/workflows'},
                        'type': 'DIRECTORY',
                        'size': 0
                    },
                    {
                        'path': {'toString': 'src'},
                        'type': 'DIRECTORY',
                        'size': 0
                    }
                ]
            }
        })
        
        with patch.object(provider, '_request', return_value=mock_response):
            result = provider.get_directory_tree('PROJECT', 'repo', path='', branch='main')
        
        paths = [item['path'] for item in result]
        
        # Nested paths should be collapsed
        assert '.agents' in paths
        assert '.github' in paths
        # Normal paths should remain
        assert 'README.md' in paths
        assert 'docs' in paths
        assert 'src' in paths
        # Nested paths should NOT appear
        assert '.agents/skills' not in paths
        assert '.github/workflows' not in paths
        
        assert len(result) == 5, f"Expected 5 items, got {len(result)}: {paths}"
