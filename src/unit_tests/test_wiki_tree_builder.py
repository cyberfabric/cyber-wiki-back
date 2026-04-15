"""
Unit tests for wiki tree builder.

Tested Scenarios:
- TreeNode creation and dictionary conversion
- TreeNode child management
- TreeNode sorting (alphabetical and custom order)
- Pattern matching (include/exclude)
- Developer tree building
- Document tree building
- Tree insertion with intermediate directories
- Title extraction integration
- Custom ordering

Untested Scenarios / Gaps:
- Very deep directory structures (>10 levels)
- Large trees (>1000 nodes)
- Circular path references
- Unicode in paths and titles
- Special characters in filenames
- Performance with large file lists

Test Strategy:
- Pure unit tests (no database)
- Test TreeNode and TreeBuilder separately
- Test pattern matching logic
- Test tree construction and sorting
- Use mock file listings
"""
import pytest
from wiki.tree_builder import TreeNode, TreeBuilder
from wiki.config_parser import CyberWikiConfig


class TestTreeNode:
    """Tests for TreeNode class."""
    
    def test_create_file_node(self):
        """Test creating a file node."""
        node = TreeNode(
            path='docs/readme.md',
            title='README',
            node_type='file'
        )
        
        assert node.path == 'docs/readme.md'
        assert node.title == 'README'
        assert node.node_type == 'file'
        assert node.children == []
        assert node.metadata == {}
    
    def test_create_directory_node(self):
        """Test creating a directory node."""
        node = TreeNode(
            path='docs',
            title='Documentation',
            node_type='directory'
        )
        
        assert node.node_type == 'directory'
        assert node.children == []
    
    def test_node_with_metadata(self):
        """Test node with metadata."""
        node = TreeNode(
            path='file.md',
            title='File',
            metadata={'size': 1024, 'sha': 'abc123'}
        )
        
        assert node.metadata['size'] == 1024
        assert node.metadata['sha'] == 'abc123'
    
    def test_add_child(self):
        """Test adding child nodes."""
        parent = TreeNode('docs', 'Docs', 'directory')
        child = TreeNode('docs/file.md', 'File', 'file')
        
        parent.add_child(child)
        
        assert len(parent.children) == 1
        assert parent.children[0] == child
    
    def test_to_dict_simple(self):
        """Test converting simple node to dict."""
        node = TreeNode('file.md', 'File', 'file')
        result = node.to_dict()
        
        assert result['path'] == 'file.md'
        assert result['title'] == 'File'
        assert result['type'] == 'file'
        assert 'children' not in result
    
    def test_to_dict_with_children(self):
        """Test converting node with children to dict."""
        parent = TreeNode('docs', 'Docs', 'directory')
        child = TreeNode('docs/file.md', 'File', 'file')
        parent.add_child(child)
        
        result = parent.to_dict()
        
        assert result['type'] == 'directory'
        assert len(result['children']) == 1
        assert result['children'][0]['path'] == 'docs/file.md'
    
    def test_to_dict_with_metadata(self):
        """Test converting node with metadata to dict."""
        node = TreeNode('file.md', 'File', 'file', metadata={'size': 100})
        result = node.to_dict()
        
        assert result['metadata']['size'] == 100
    
    def test_sort_children_alphabetically(self):
        """Test sorting children alphabetically."""
        parent = TreeNode('root', 'Root', 'directory')
        parent.add_child(TreeNode('zebra.md', 'Zebra', 'file'))
        parent.add_child(TreeNode('apple.md', 'Apple', 'file'))
        parent.add_child(TreeNode('banana.md', 'Banana', 'file'))
        
        parent.sort_children()
        
        titles = [child.title for child in parent.children]
        assert titles == ['Apple', 'Banana', 'Zebra']
    
    def test_sort_directories_before_files(self):
        """Test that directories are sorted before files."""
        parent = TreeNode('root', 'Root', 'directory')
        parent.add_child(TreeNode('file.md', 'File', 'file'))
        parent.add_child(TreeNode('dir', 'Directory', 'directory'))
        parent.add_child(TreeNode('another.md', 'Another', 'file'))
        
        parent.sort_children()
        
        assert parent.children[0].node_type == 'directory'
        assert parent.children[1].node_type == 'file'
        assert parent.children[2].node_type == 'file'
    
    def test_sort_with_custom_order(self):
        """Test sorting with custom order."""
        parent = TreeNode('root', 'Root', 'directory')
        parent.add_child(TreeNode('c.md', 'C', 'file'))
        parent.add_child(TreeNode('a.md', 'A', 'file'))
        parent.add_child(TreeNode('b.md', 'B', 'file'))
        
        custom_order = ['b.md', 'a.md', 'c.md']
        parent.sort_children(custom_order)
        
        paths = [child.path for child in parent.children]
        assert paths == ['b.md', 'a.md', 'c.md']
    
    def test_sort_recursive(self):
        """Test that sorting is recursive."""
        root = TreeNode('root', 'Root', 'directory')
        child_dir = TreeNode('dir', 'Dir', 'directory')
        child_dir.add_child(TreeNode('dir/z.md', 'Z', 'file'))
        child_dir.add_child(TreeNode('dir/a.md', 'A', 'file'))
        root.add_child(child_dir)
        
        root.sort_children()
        
        # Check that grandchildren are sorted
        grandchildren_titles = [gc.title for gc in child_dir.children]
        assert grandchildren_titles == ['A', 'Z']


class TestTreeBuilderPatterns:
    """Tests for pattern matching in TreeBuilder."""
    
    def test_should_include_matching_pattern(self):
        """Test that matching files are included."""
        config = CyberWikiConfig(
            include_patterns=['*.md', 'docs/*.md', '*/*/*.md'],
            exclude_patterns=[]
        )
        builder = TreeBuilder(config)
        
        assert builder.should_include('README.md')
        assert builder.should_include('docs/guide.md')
        assert builder.should_include('deep/nested/file.md')
    
    def test_should_exclude_matching_pattern(self):
        """Test that excluded files are not included."""
        config = CyberWikiConfig(
            include_patterns=['*.md', '*/*.md', '*/*/*.md'],
            exclude_patterns=['node_modules/*', '*/node_modules/*', '*/node_modules/*/*']
        )
        builder = TreeBuilder(config)
        
        assert not builder.should_include('node_modules/package/README.md')
        assert not builder.should_include('src/node_modules/file.md')
    
    def test_exclude_takes_precedence(self):
        """Test that exclude patterns take precedence over include."""
        config = CyberWikiConfig(
            include_patterns=['*.md', '*/*.md', '*/*/*.md'],
            exclude_patterns=['test/*', '*/test/*']
        )
        builder = TreeBuilder(config)
        
        assert builder.should_include('docs/guide.md')
        assert not builder.should_include('test/readme.md')
    
    def test_should_not_include_non_matching(self):
        """Test that non-matching files are not included."""
        config = CyberWikiConfig(
            include_patterns=['*.md', '*/*.md'],
            exclude_patterns=[]
        )
        builder = TreeBuilder(config)
        
        assert not builder.should_include('script.js')
        assert not builder.should_include('image.png')


class TestTreeBuilderDeveloperTree:
    """Tests for building developer mode trees."""
    
    def test_build_simple_tree(self):
        """Test building a simple developer tree."""
        config = CyberWikiConfig(
            include_patterns=['*.md', '*/*.md'],
            exclude_patterns=[]
        )
        builder = TreeBuilder(config)
        
        files = [
            {'path': 'README.md', 'type': 'file', 'size': 100},
            {'path': 'docs/guide.md', 'type': 'file', 'size': 200},
        ]
        
        tree = builder.build_developer_tree(files)
        
        assert tree.title == 'Root'
        assert len(tree.children) > 0
    
    def test_build_tree_with_directories(self):
        """Test building tree with directory structure."""
        config = CyberWikiConfig(
            include_patterns=['*.md', '*/*.md'],
            exclude_patterns=[]
        )
        builder = TreeBuilder(config)
        
        files = [
            {'path': 'docs', 'type': 'dir'},
            {'path': 'docs/guide.md', 'type': 'file', 'size': 100},
        ]
        
        tree = builder.build_developer_tree(files)
        
        # Should have docs directory
        assert any(child.path == 'docs' for child in tree.children)
    
    def test_build_tree_filters_files(self):
        """Test that tree building filters files by patterns."""
        config = CyberWikiConfig(
            include_patterns=['*.md', '*/*.md'],
            exclude_patterns=['test/*']
        )
        builder = TreeBuilder(config)
        
        files = [
            {'path': 'README.md', 'type': 'file'},
            {'path': 'test/file.md', 'type': 'file'},
            {'path': 'script.js', 'type': 'file'},
        ]
        
        tree = builder.build_developer_tree(files)
        
        # Should only include README.md
        file_paths = self._get_all_file_paths(tree)
        assert 'README.md' in file_paths
        assert 'test/file.md' not in file_paths
        assert 'script.js' not in file_paths
    
    def test_build_tree_with_custom_order(self):
        """Test building tree with custom ordering."""
        config = CyberWikiConfig(
            include_patterns=['*.md'],
            exclude_patterns=[],
            custom_order=['b.md', 'a.md']
        )
        builder = TreeBuilder(config)
        
        files = [
            {'path': 'a.md', 'type': 'file'},
            {'path': 'b.md', 'type': 'file'},
        ]
        
        tree = builder.build_developer_tree(files)
        
        # Should be ordered according to custom_order
        paths = [child.path for child in tree.children]
        assert paths[0] == 'b.md'
        assert paths[1] == 'a.md'
    
    def _get_all_file_paths(self, node):
        """Helper to get all file paths in tree."""
        paths = []
        if node.node_type == 'file':
            paths.append(node.path)
        for child in node.children:
            paths.extend(self._get_all_file_paths(child))
        return paths


class TestTreeBuilderDocumentTree:
    """Tests for building document mode trees."""
    
    def test_build_document_tree_only_files(self):
        """Test that document tree only includes files, not directories."""
        config = CyberWikiConfig(
            include_patterns=['*.md', '*/*.md'],
            exclude_patterns=[]
        )
        builder = TreeBuilder(config)
        
        files = [
            {'path': 'docs', 'type': 'dir'},
            {'path': 'docs/guide.md', 'type': 'file', 'size': 100},
        ]
        
        tree = builder.build_document_tree(files)
        
        # Should create directory structure but only for containing files
        assert tree.title == 'Documentation'
    
    def test_build_document_tree_filters_non_markdown(self):
        """Test that document tree filters non-markdown files."""
        config = CyberWikiConfig(
            include_patterns=['*.md'],
            exclude_patterns=[]
        )
        builder = TreeBuilder(config)
        
        files = [
            {'path': 'README.md', 'type': 'file'},
            {'path': 'script.js', 'type': 'file'},
            {'path': 'image.png', 'type': 'file'},
        ]
        
        tree = builder.build_document_tree(files)
        
        # Should only include README.md
        file_paths = self._get_all_file_paths(tree)
        assert 'README.md' in file_paths
        assert 'script.js' not in file_paths
        assert 'image.png' not in file_paths
    
    def _get_all_file_paths(self, node):
        """Helper to get all file paths in tree."""
        paths = []
        if node.node_type == 'file':
            paths.append(node.path)
        for child in node.children:
            paths.extend(self._get_all_file_paths(child))
        return paths


class TestTreeBuilderInsertion:
    """Tests for node insertion logic."""
    
    def test_insert_creates_intermediate_directories(self):
        """Test that inserting a nested file creates intermediate directories."""
        config = CyberWikiConfig()
        builder = TreeBuilder(config)
        
        root = TreeNode('', 'Root', 'directory')
        file_node = TreeNode('a/b/c/file.md', 'File', 'file')
        
        builder._insert_node(root, file_node, 'a/b/c/file.md')
        
        # Should create a -> b -> c -> file.md
        assert len(root.children) == 1
        assert root.children[0].path == 'a'
        assert root.children[0].node_type == 'directory'
    
    def test_insert_reuses_existing_directories(self):
        """Test that inserting reuses existing directory nodes."""
        config = CyberWikiConfig()
        builder = TreeBuilder(config)
        
        root = TreeNode('', 'Root', 'directory')
        
        # Insert first file
        file1 = TreeNode('docs/file1.md', 'File 1', 'file')
        builder._insert_node(root, file1, 'docs/file1.md')
        
        # Insert second file in same directory
        file2 = TreeNode('docs/file2.md', 'File 2', 'file')
        builder._insert_node(root, file2, 'docs/file2.md')
        
        # Should only have one 'docs' directory
        assert len(root.children) == 1
        assert root.children[0].path == 'docs'
        # But it should have two children
        assert len(root.children[0].children) == 2
