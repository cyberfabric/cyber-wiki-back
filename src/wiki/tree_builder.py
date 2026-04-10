"""
Tree builder for constructing document navigation trees.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import fnmatch
from .config_parser import CyberWikiConfig
from .title_extractor import TitleExtractor


class TreeNode:
    """
    Node in the document tree.
    """
    
    def __init__(
        self,
        path: str,
        title: str,
        node_type: str = 'file',  # 'file' or 'directory'
        children: Optional[List['TreeNode']] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.path = path
        self.title = title
        self.node_type = node_type
        self.children = children or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            'path': self.path,
            'title': self.title,
            'type': self.node_type,
        }
        
        if self.children:
            result['children'] = [child.to_dict() for child in self.children]
        
        if self.metadata:
            result['metadata'] = self.metadata
        
        return result
    
    def add_child(self, child: 'TreeNode'):
        """Add a child node."""
        self.children.append(child)
    
    def sort_children(self, custom_order: List[str] = None):
        """
        Sort children alphabetically or by custom order.
        
        Args:
            custom_order: List of paths in desired order
        """
        if custom_order:
            # Create order map
            order_map = {path: i for i, path in enumerate(custom_order)}
            
            # Sort with custom order first, then alphabetically
            self.children.sort(
                key=lambda node: (
                    order_map.get(node.path, float('inf')),
                    node.title.lower()
                )
            )
        else:
            # Directories first, then files, both alphabetically
            self.children.sort(
                key=lambda node: (
                    0 if node.node_type == 'directory' else 1,
                    node.title.lower()
                )
            )
        
        # Recursively sort children
        for child in self.children:
            if child.children:
                child.sort_children(custom_order)


class TreeBuilder:
    """
    Build document navigation trees from file listings.
    """
    
    def __init__(self, config: CyberWikiConfig):
        """
        Initialize tree builder.
        
        Args:
            config: CyberWiki configuration
        """
        self.config = config
    
    def should_include(self, path: str) -> bool:
        """
        Check if file should be included based on patterns.
        
        Args:
            path: File path
        
        Returns:
            True if file should be included
        """
        # Check exclude patterns first
        for pattern in self.config.exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return False
        
        # Check include patterns
        for pattern in self.config.include_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
        
        return False
    
    def build_developer_tree(
        self,
        files: List[Dict[str, Any]],
        file_contents: Optional[Dict[str, str]] = None
    ) -> TreeNode:
        """
        Build developer mode tree (raw file structure).
        
        Args:
            files: List of file entries from Git provider
            file_contents: Optional dict of path -> content for title extraction
        
        Returns:
            Root TreeNode
        """
        root = TreeNode(path='', title='Root', node_type='directory')
        
        # Filter files
        filtered_files = [f for f in files if self.should_include(f['path'])]
        
        # Build tree structure
        for file_entry in filtered_files:
            path = file_entry['path']
            is_dir = file_entry.get('type') == 'dir'
            
            # Extract title
            if is_dir:
                title = Path(path).name
            else:
                if file_contents and path in file_contents:
                    title = TitleExtractor.extract(
                        file_contents[path],
                        path,
                        self.config.title_extraction
                    )
                else:
                    title = TitleExtractor.extract_from_filename(path)
            
            # Create node
            node = TreeNode(
                path=path,
                title=title,
                node_type='directory' if is_dir else 'file',
                metadata={
                    'size': file_entry.get('size', 0),
                    'sha': file_entry.get('sha', ''),
                }
            )
            
            # Insert into tree
            self._insert_node(root, node, path)
        
        # Sort tree
        root.sort_children(self.config.custom_order)
        
        return root
    
    def build_document_tree(
        self,
        files: List[Dict[str, Any]],
        file_contents: Optional[Dict[str, str]] = None
    ) -> TreeNode:
        """
        Build document mode tree (filtered for documentation files).
        
        Args:
            files: List of file entries from Git provider
            file_contents: Optional dict of path -> content for title extraction
        
        Returns:
            Root TreeNode
        """
        # Document mode only includes markdown files
        doc_files = [
            f for f in files
            if f.get('type') != 'dir' and self.should_include(f['path'])
        ]
        
        root = TreeNode(path='', title='Documentation', node_type='directory')
        
        for file_entry in doc_files:
            path = file_entry['path']
            
            # Extract title
            if file_contents and path in file_contents:
                title = TitleExtractor.extract(
                    file_contents[path],
                    path,
                    self.config.title_extraction
                )
            else:
                title = TitleExtractor.extract_from_filename(path)
            
            # Create node
            node = TreeNode(
                path=path,
                title=title,
                node_type='file',
                metadata={
                    'size': file_entry.get('size', 0),
                    'sha': file_entry.get('sha', ''),
                }
            )
            
            # Insert into tree (create directory structure)
            self._insert_node(root, node, path)
        
        # Sort tree
        root.sort_children(self.config.custom_order)
        
        return root
    
    def _insert_node(self, root: TreeNode, node: TreeNode, path: str):
        """
        Insert node into tree, creating intermediate directories as needed.
        
        Args:
            root: Root node
            node: Node to insert
            path: Full path of node
        """
        parts = path.split('/')
        current = root
        
        # Navigate/create directory structure
        for i, part in enumerate(parts[:-1]):
            # Find or create directory node
            dir_path = '/'.join(parts[:i+1])
            dir_node = None
            
            for child in current.children:
                if child.path == dir_path:
                    dir_node = child
                    break
            
            if not dir_node:
                dir_node = TreeNode(
                    path=dir_path,
                    title=part,
                    node_type='directory'
                )
                current.add_child(dir_node)
            
            current = dir_node
        
        # Add the file/directory node
        current.add_child(node)
