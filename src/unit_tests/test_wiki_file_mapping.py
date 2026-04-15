"""
Unit tests for file mapping inheritance and effective value computation.

Tested Scenarios:
- File inherits from space default when no parent folder
- File inherits from parent folder's children_display_name_source
- File overrides parent folder with explicit setting
- Nested folder inheritance (nearest parent wins)
- Folders always use filename or custom (never inherit)
- Visibility inheritance from parent folder
- Effective values recompute after parent changes
- Effective values recompute after space default changes

Untested Scenarios / Gaps:
- Multi-level nested inheritance (> 3 levels)
- Circular inheritance detection
- Inheritance with deleted parent folders
- Concurrent updates to parent and child
- Bulk recomputation performance
- Cache invalidation on inheritance changes
- Cross-space inheritance (should not happen)

Test Strategy:
- Model tests with database fixtures
- Use shared fixtures from conftest.py
- Test inheritance chain logic
- Test effective value computation
"""
import pytest
from wiki.models import Space, FileMapping


@pytest.mark.django_db
class TestFileMappingInheritance:
    """Test inheritance chain: space → folder → file"""
    
    def test_file_inherits_from_space_default(self, space):
        """File with no mapping should inherit from space default."""
        mapping = FileMapping.objects.create(
            space=space,
            file_path='docs/readme.md',
            is_folder=False,
        )
        
        # Should inherit from space default (first_h1)
        assert mapping.effective_display_name_source == 'first_h1'
        assert mapping.effective_is_visible == True
    
    def test_file_inherits_from_parent_folder(self, space):
        """File should inherit from parent folder's children_display_name_source."""
        # Create parent folder with children rule
        folder = FileMapping.objects.create(
            space=space,
            file_path='api',
            is_folder=True,
            display_name_source='filename',
            children_display_name_source='first_h2',
        )
        
        # Create file in folder
        file_mapping = FileMapping.objects.create(
            space=space,
            file_path='api/endpoints.md',
            is_folder=False,
        )
        
        # Should inherit H2 from parent folder
        assert file_mapping.effective_display_name_source == 'first_h2'
    
    def test_file_overrides_parent_folder(self, space):
        """File with explicit setting should override parent folder."""
        # Create parent folder
        FileMapping.objects.create(
            space=space,
            file_path='api',
            is_folder=True,
            children_display_name_source='first_h2',
        )
        
        # Create file with explicit setting
        file_mapping = FileMapping.objects.create(
            space=space,
            file_path='api/auth.md',
            is_folder=False,
            display_name_source='custom',
            display_name='Authentication',
        )
        
        # Should use own setting, not parent
        assert file_mapping.effective_display_name_source == 'custom'
    
    def test_nested_folder_inheritance(self, space):
        """File should inherit from nearest parent with children_display_name_source."""
        # Create grandparent folder
        FileMapping.objects.create(
            space=space,
            file_path='docs',
            is_folder=True,
            children_display_name_source='first_h1',
        )
        
        # Create parent folder with different rule
        FileMapping.objects.create(
            space=space,
            file_path='docs/api',
            is_folder=True,
            children_display_name_source='first_h2',
        )
        
        # Create file
        file_mapping = FileMapping.objects.create(
            space=space,
            file_path='docs/api/endpoints.md',
            is_folder=False,
        )
        
        # Should inherit from nearest parent (api/ → H2)
        assert file_mapping.effective_display_name_source == 'first_h2'
    
    def test_folder_always_uses_filename_or_custom(self, space):
        """Folders should always use filename or custom, never inherit."""
        # Create parent folder
        FileMapping.objects.create(
            space=space,
            file_path='docs',
            is_folder=True,
            children_display_name_source='first_h1',
        )
        
        # Create child folder without explicit setting
        child_folder = FileMapping.objects.create(
            space=space,
            file_path='docs/api',
            is_folder=True,
        )
        
        # Should use filename, not inherit from parent
        assert child_folder.effective_display_name_source == 'filename'
    
    def test_visibility_inheritance(self, space):
        """Test visibility inheritance from parent folder."""
        # Create hidden parent folder
        FileMapping.objects.create(
            space=space,
            file_path='internal',
            is_folder=True,
            is_visible=False,
            children_display_name_source='first_h1',
        )
        
        # Create file in hidden folder
        file_mapping = FileMapping.objects.create(
            space=space,
            file_path='internal/secret.md',
            is_folder=False,
        )
        
        # Should inherit hidden status from parent
        assert file_mapping.effective_is_visible == False


@pytest.mark.django_db
class TestFileMappingSync:
    """Test sync functionality - removing outdated mappings."""
    
    def test_recompute_effective_values_after_parent_change(self, space):
        """When parent folder changes, child effective values should update."""
        # Create parent folder
        folder = FileMapping.objects.create(
            space=space,
            file_path='api',
            is_folder=True,
            children_display_name_source='first_h1',
        )
        
        # Create file
        file_mapping = FileMapping.objects.create(
            space=space,
            file_path='api/endpoints.md',
            is_folder=False,
        )
        
        assert file_mapping.effective_display_name_source == 'first_h1'
        
        # Change parent folder's children rule
        folder.children_display_name_source = 'first_h2'
        folder.save()
        
        # Recompute file's effective values
        file_mapping.refresh_from_db()
        effective_source, _ = file_mapping.compute_effective_values()
        file_mapping.effective_display_name_source = effective_source
        file_mapping.save()
        
        # Should now use H2
        file_mapping.refresh_from_db()
        assert file_mapping.effective_display_name_source == 'first_h2'
    
    def test_recompute_after_space_default_change(self, space):
        """When space default changes, files without parent should update."""
        # Create file with no parent folder
        file_mapping = FileMapping.objects.create(
            space=space,
            file_path='readme.md',
            is_folder=False,
        )
        
        assert file_mapping.effective_display_name_source == 'first_h1'
        
        # Change space default
        space.default_display_name_source = 'first_h2'
        space.save()
        
        # Recompute
        effective_source, _ = file_mapping.compute_effective_values()
        file_mapping.effective_display_name_source = effective_source
        file_mapping.save()
        
        file_mapping.refresh_from_db()
        assert file_mapping.effective_display_name_source == 'first_h2'
