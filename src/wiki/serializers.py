"""
Serializers for wiki models.
"""
from rest_framework import serializers
from .models import (
    Space, Document, FileComment, UserChange, Tag, DocumentTag, DocumentLink, GitSyncConfig,
    SpacePermission, SpaceConfiguration, SpaceShortcut, UserSpacePreference, SpaceAttribute
)


class SpaceDetailSerializer(serializers.ModelSerializer):
    """Serializer for Space model with full Git integration details."""
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    git_repository_url = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Space
        fields = [
            'id', 'slug', 'name', 'description',
            'owner', 'owner_username',
            'visibility', 'is_public',
            'git_provider', 'git_base_url', 'git_project_key',
            'git_repository_id', 'git_repository_name', 'git_default_branch',
            'git_repository_url',
            'page_count',
            'created_by', 'created_by_username',
            'created_at', 'updated_at', 'last_synced_at'
        ]
        read_only_fields = ['id', 'created_by', 'page_count', 'created_at', 'updated_at', 'last_synced_at']
        extra_kwargs = {
            'git_default_branch': {'allow_blank': True, 'required': False},
        }
    
    def create(self, validated_data):
        git_repository_url = validated_data.pop('git_repository_url', None)
        git_provider = validated_data.get('git_provider')
        
        if git_repository_url and git_provider:
            # Parse URL and extract repository details
            parsed = self._parse_and_verify_git_url(git_repository_url, git_provider)
            validated_data.update(parsed)
            
            # Auto-detect default branch if not specified
            if not validated_data.get('git_default_branch'):
                default_branch = self._detect_default_branch(
                    git_provider,
                    parsed.get('git_base_url'),
                    parsed.get('git_project_key'),
                    parsed.get('git_repository_id')
                )
                if default_branch:
                    validated_data['git_default_branch'] = default_branch
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Remove slug from validated_data to prevent updates (slug is immutable)
        validated_data.pop('slug', None)
        
        git_repository_url = validated_data.pop('git_repository_url', None)
        git_provider = validated_data.get('git_provider', instance.git_provider)
        
        if git_repository_url and git_provider:
            # Parse URL and extract repository details
            parsed = self._parse_and_verify_git_url(git_repository_url, git_provider)
            validated_data.update(parsed)
            
            # Auto-detect default branch if not specified
            if not validated_data.get('git_default_branch'):
                default_branch = self._detect_default_branch(
                    git_provider,
                    parsed.get('git_base_url'),
                    parsed.get('git_project_key'),
                    parsed.get('git_repository_id')
                )
                if default_branch:
                    validated_data['git_default_branch'] = default_branch
        
        return super().update(instance, validated_data)
    
    def _parse_and_verify_git_url(self, url, provider):
        """Parse Git repository URL and extract details based on provider."""
        from urllib.parse import urlparse
        
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname or ''
        path = parsed_url.path.strip('/')
        
        if provider == 'github':
            base_url = f"{parsed_url.scheme}://{hostname}"
            parts = path.split('/')
            if len(parts) >= 2:
                repo_id = f"{parts[0]}/{parts[1]}"
                repo_name = parts[1]
            else:
                repo_id = path
                repo_name = path
            project_key = None
        elif provider == 'bitbucket_server':
            base_url = f"{parsed_url.scheme}://{hostname}"
            # Bitbucket Server URL format: /projects/PROJECT/repos/REPO
            if 'projects' in path and 'repos' in path:
                parts = path.split('/')
                try:
                    project_idx = parts.index('projects')
                    repos_idx = parts.index('repos')
                    project_key = parts[project_idx + 1] if project_idx + 1 < len(parts) else None
                    repo_id = parts[repos_idx + 1] if repos_idx + 1 < len(parts) else None
                    repo_name = repo_id
                except (ValueError, IndexError):
                    project_key = None
                    repo_id = path.split('/')[-1]
                    repo_name = repo_id
            else:
                project_key = None
                repo_id = path.split('/')[-1]
                repo_name = repo_id
        else:  # local_git
            base_url = str(parsed_url.scheme + '://' + hostname) if parsed_url.scheme else url.rsplit('/', 1)[0]
            repo_id = path.split('/')[-1] if path else url.split('/')[-1]
            repo_name = repo_id
            project_key = None
        
        return {
            'git_base_url': base_url,
            'git_project_key': project_key,
            'git_repository_id': repo_id,
            'git_repository_name': repo_name,
        }
    
    def _detect_default_branch(self, provider, base_url, project_key, repo_id):
        """Detect the default branch by fetching branches from the Git provider."""
        try:
            from git_provider.factory import GitProviderFactory
            
            # Get provider instance
            git_provider = GitProviderFactory.get_provider(provider, base_url)
            
            # Construct full repo ID for Bitbucket
            if provider == 'bitbucket_server' and project_key:
                full_repo_id = f"{project_key}_{repo_id}"
            else:
                full_repo_id = repo_id
            
            # Fetch branches
            branches = git_provider.list_branches(full_repo_id)
            
            # Return first branch (usually the default)
            if branches:
                return branches[0]
            
            # Fallback to common defaults
            return 'master'
        except Exception:
            # If detection fails, use common default
            return 'master'


class FileCommentSerializer(serializers.ModelSerializer):
    """Serializer for FileComment model."""
    author_username = serializers.CharField(source='author.username', read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = FileComment
        fields = ['id', 'source_uri', 'line_start', 'line_end', 'text', 'author', 'author_username', 'thread_id', 'parent_comment', 'is_resolved', 'anchoring_status', 'replies', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'thread_id', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        if obj.replies.exists():
            return FileCommentSerializer(obj.replies.all(), many=True).data
        return []


class FileCommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating file comments."""
    
    class Meta:
        model = FileComment
        fields = ['source_uri', 'line_start', 'line_end', 'text', 'parent_comment']


class UserChangeSerializer(serializers.ModelSerializer):
    """Serializer for UserChange model."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    approved_by_username = serializers.CharField(source='approved_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = UserChange
        fields = ['id', 'user', 'user_username', 'repository_full_name', 'file_path', 'original_content', 'modified_content', 'commit_message', 'status', 'approved_by', 'approved_by_username', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'approved_by', 'created_at', 'updated_at']


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model."""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'tag_type', 'usage_count', 'created_at']
        read_only_fields = ['id', 'usage_count', 'created_at']


class DocumentTagSerializer(serializers.ModelSerializer):
    """Serializer for DocumentTag model."""
    tag_name = serializers.CharField(source='tag.name', read_only=True)
    
    class Meta:
        model = DocumentTag
        fields = ['id', 'document', 'tag', 'tag_name', 'relevance_score', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']


class DocumentLinkSerializer(serializers.ModelSerializer):
    """Serializer for DocumentLink model."""
    source_title = serializers.CharField(source='source_document.title', read_only=True)
    target_title = serializers.CharField(source='target_document.title', read_only=True, allow_null=True)
    
    class Meta:
        model = DocumentLink
        fields = ['id', 'source_document', 'source_title', 'target_document', 'target_title', 'target_url', 'link_type', 'is_valid', 'created_at']
        read_only_fields = ['id', 'is_valid', 'created_at']


class GitSyncConfigSerializer(serializers.ModelSerializer):
    """Serializer for GitSyncConfig model."""
    space_name = serializers.CharField(source='space.name', read_only=True)
    
    class Meta:
        model = GitSyncConfig
        fields = ['id', 'space', 'space_name', 'repository_url', 'branch', 'direction', 'status', 'last_sync_at', 'last_sync_error', 'created_at', 'updated_at']
        read_only_fields = ['id', 'last_sync_at', 'last_sync_error', 'created_at', 'updated_at']


# ============================================================================
# New Space-related Serializers
# ============================================================================

class SpacePermissionSerializer(serializers.ModelSerializer):
    """Serializer for SpacePermission model."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.username', read_only=True, allow_null=True)
    space_name = serializers.CharField(source='space.name', read_only=True)
    
    class Meta:
        model = SpacePermission
        fields = [
            'id', 'space', 'space_name',
            'user', 'user_username', 'user_email',
            'role',
            'granted_by', 'granted_by_username',
            'created_at'
        ]
        read_only_fields = ['id', 'granted_by', 'created_at']


class SpaceConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for SpaceConfiguration model."""
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    space_name = serializers.CharField(source='space.name', read_only=True)
    
    class Meta:
        model = SpaceConfiguration
        fields = [
            'id', 'space', 'space_slug', 'space_name',
            'file_tree_config',
            'page_display_config',
            'sync_config',
            'custom_settings',
            'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class SpaceShortcutSerializer(serializers.ModelSerializer):
    """Serializer for SpaceShortcut model."""
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = SpaceShortcut
        fields = [
            'id', 'space', 'space_slug',
            'page_id', 'label', 'order',
            'created_by', 'created_by_username',
            'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']


class UserSpacePreferenceSerializer(serializers.ModelSerializer):
    """Serializer for UserSpacePreference model."""
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    space_name = serializers.CharField(source='space.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserSpacePreference
        fields = [
            'id', 'user', 'user_username',
            'space', 'space_slug', 'space_name',
            'is_favorite',
            'last_visited_at',
            'visit_count',
            'last_viewed_page_id'
        ]
        read_only_fields = ['id', 'last_visited_at', 'visit_count']


class SpaceAttributeSerializer(serializers.ModelSerializer):
    """Serializer for SpaceAttribute model."""
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    value = serializers.SerializerMethodField()
    
    class Meta:
        model = SpaceAttribute
        fields = [
            'id', 'space', 'space_slug',
            'field_id', 'field_name',
            'field_value_str', 'field_value_int', 'field_value_float',
            'value',  # Computed field
            'collected_at', 'data_source', 'version'
        ]
        read_only_fields = ['id', 'collected_at']
    
    def get_value(self, obj):
        """Get the actual value based on which field is populated."""
        return obj.get_value()
    
    def validate(self, data):
        """Ensure at least one value field is populated."""
        if not any([
            data.get('field_value_str'),
            data.get('field_value_int') is not None,
            data.get('field_value_float') is not None
        ]):
            raise serializers.ValidationError(
                "At least one value field (field_value_str, field_value_int, or field_value_float) must be provided"
            )
        return data
