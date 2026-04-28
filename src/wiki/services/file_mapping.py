"""
Service for file mapping business logic.
"""
from typing import Optional, Dict, List
from wiki.models import Space, FileMapping
from django.db.models import Q


class FileMappingService:
    """Business logic for file mappings."""
    
    @staticmethod
    def get_effective_mapping(space: Space, file_path: str) -> Optional[FileMapping]:
        """
        Get effective mapping for a file, considering inheritance.
        
        Args:
            space: Space instance
            file_path: File path
        
        Returns:
            FileMapping instance or None
        """
        # 1. Check for direct mapping
        try:
            mapping = FileMapping.objects.get(space=space, file_path=file_path)
            if mapping.is_override or not mapping.parent_rule:
                return mapping
        except FileMapping.DoesNotExist:
            pass
        
        # 2. Check parent folder rules
        path_parts = file_path.split('/')
        for i in range(len(path_parts) - 1, 0, -1):
            parent_path = '/'.join(path_parts[:i]) + '/'
            try:
                parent_rule = FileMapping.objects.get(
                    space=space,
                    file_path=parent_path,
                    apply_to_children=True
                )
                return parent_rule
            except FileMapping.DoesNotExist:
                continue
        
        # 3. Return None (use space defaults)
        return None
    
    @staticmethod
    def apply_folder_rule(
        space: Space,
        folder_path: str,
        rule: Dict,
        apply_to_children: bool = True,
        user=None
    ) -> FileMapping:
        """
        Apply a rule to a folder and optionally its children.
        
        Args:
            space: Space instance
            folder_path: Folder path
            rule: Rule configuration dict
            apply_to_children: Apply to children
            user: User creating the rule
        
        Returns:
            Created/updated FileMapping
        """
        # Ensure folder_path ends with /
        if not folder_path.endswith('/'):
            folder_path += '/'
        
        # Create or update folder mapping
        folder_mapping, created = FileMapping.objects.update_or_create(
            space=space,
            file_path=folder_path,
            defaults={
                'is_folder': True,
                'apply_to_children': apply_to_children,
                'created_by': user if created else None,
                **rule
            }
        )
        
        if apply_to_children:
            # Update all children that don't have overrides
            children = FileMapping.objects.filter(
                space=space,
                file_path__startswith=folder_path,
                is_override=False
            ).exclude(file_path=folder_path)
            
            children.update(parent_rule=folder_mapping)
        
        return folder_mapping
    
    @staticmethod
    def bulk_update_mappings(
        space: Space,
        mappings: List[Dict],
        user=None
    ) -> List[FileMapping]:
        """
        Bulk update or create file mappings.
        
        Args:
            space: Space instance
            mappings: List of mapping dicts with file_path and config
            user: User creating mappings
        
        Returns:
            List of created/updated FileMappings
        """
        results = []
        
        for mapping_data in mappings:
            file_path = mapping_data.pop('file_path')
            is_folder = mapping_data.get('is_folder', False)
            
            # Ensure folder paths end with /
            if is_folder and not file_path.endswith('/'):
                file_path += '/'
            
            mapping, created = FileMapping.objects.update_or_create(
                space=space,
                file_path=file_path,
                defaults={
                    'created_by': user if created else None,
                    **mapping_data
                }
            )
            results.append(mapping)
        
        return results
    
    @staticmethod
    def get_visible_files(
        space: Space,
        file_tree: List[Dict],
        mode: str = 'dev'
    ) -> List[Dict]:
        """
        Filter file tree based on visibility settings.
        
        Args:
            space: Space instance
            file_tree: List of file/folder dicts from git provider
            mode: 'dev' or 'documents'
        
        Returns:
            Filtered file tree
        """
        if mode == 'dev':
            # In dev mode, show everything
            return file_tree
        
        # In documents mode, filter by visibility
        mappings = {
            m.file_path: m
            for m in FileMapping.objects.filter(space=space)
        }
        
        visible_files = []
        for item in file_tree:
            path = item['path']
            
            # Get effective mapping
            mapping = FileMappingService.get_effective_mapping(space, path)
            
            # Check visibility
            if mapping and not mapping.is_visible:
                continue
            
            # Add display name if available
            if mapping:
                item['display_name'] = mapping.get_display_name()
                item['icon'] = mapping.icon
                item['sort_order'] = mapping.sort_order
            
            visible_files.append(item)
        
        return visible_files
    
    @staticmethod
    def build_tree_with_mappings(
        space: Space,
        git_provider,
        path: str = '',
        mode: str = 'dev',
        filters: List[str] = None
    ) -> List[Dict]:
        """
        Build file tree with mappings applied.
        
        Args:
            space: Space instance
            git_provider: Git provider instance
            path: Root path to start from
            mode: 'dev' or 'documents'
            filters: List of file extensions to filter
        
        Returns:
            File tree with mappings
        """
        # Get raw file tree from git provider
        # For Bitbucket: project_key and repo_slug
        # For GitHub: project_key is owner, repo_slug is repo name
        
        # Handle repository identification
        if space.git_project_key:
            # Explicit project key (Bitbucket Server)
            project_key = space.git_project_key
            repo_slug = space.git_repository_id or space.git_repository_name or ''
        elif space.git_repository_id and '/' in space.git_repository_id:
            # GitHub format "owner/repo" in repository_id
            parts = space.git_repository_id.split('/', 1)
            project_key = parts[0]
            repo_slug = parts[1]
        elif space.git_repository_id and '_' in space.git_repository_id:
            # Repository ID in format "project_repo" (legacy)
            parts = space.git_repository_id.split('_', 1)
            project_key = parts[0]
            repo_slug = parts[1]
        elif space.git_repository_name and '/' in space.git_repository_name:
            # GitHub format "owner/repo"
            parts = space.git_repository_name.split('/', 1)
            project_key = parts[0]
            repo_slug = parts[1]
        else:
            # Fallback
            project_key = space.git_project_key or ''
            repo_slug = space.git_repository_id or space.git_repository_name or ''
        
        branch = space.git_default_branch or 'main'
        
        raw_tree = git_provider.get_directory_tree(
            project_key=project_key,
            repo_slug=repo_slug,
            path=path,
            branch=branch,
            recursive=False  # Load only current level, not recursively
        )
        
        # Get all mappings for this space
        mappings = {
            m.file_path: m
            for m in FileMapping.objects.filter(space=space)
        }
        
        # Build tree with mappings
        result = []
        for item in raw_tree:
            file_path = item.get('path', '')
            if not file_path:
                continue
            
            # Extract name from path
            name = file_path.split('/')[-1] if file_path else ''
            item['name'] = name
            
            # Apply filters - but always show folders (they may contain matching files)
            is_folder = item.get('type') == 'dir'
            if filters and not is_folder:
                matches_filter = any(file_path.endswith(f) for f in filters)
                if not matches_filter:
                    if mode == 'documents':
                        # Skip in documents mode
                        continue
                    else:
                        # Mark as filtered in dev mode
                        item['filtered'] = True
            
            # Get effective mapping
            mapping = FileMappingService.get_effective_mapping(space, file_path)
            
            # Apply visibility
            if mode == 'documents' and mapping and not mapping.is_visible:
                continue
            
            # Apply mapping data
            if mapping:
                item['is_visible'] = mapping.is_visible
                item['display_name'] = mapping.get_display_name()
                item['display_name_source'] = mapping.display_name_source
                item['extracted_name'] = mapping.extracted_name
                item['icon'] = mapping.icon
                item['sort_order'] = mapping.sort_order
                item['has_mapping'] = True
            else:
                item['is_visible'] = True
                item['display_name'] = name
                item['display_name_source'] = 'filename'
                item['has_mapping'] = False
            
            result.append(item)
        
        # Sort: directories first, then by sort_order/name
        result.sort(key=lambda x: (
            0 if x.get('type') == 'dir' else 1,  # Directories first
            x.get('sort_order') if x.get('sort_order') is not None else 999999,
            x['name']
        ))
        
        return result
