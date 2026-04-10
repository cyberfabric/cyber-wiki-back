"""
Serializers for wiki models.
"""
from rest_framework import serializers
from .models import Space, Document, FileComment, UserChange, Tag, DocumentTag, DocumentLink, GitSyncConfig


class SpaceSerializer(serializers.ModelSerializer):
    """Serializer for Space model."""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = Space
        fields = ['id', 'slug', 'name', 'description', 'is_public', 'created_by', 'created_by_username', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model."""
    space_slug = serializers.CharField(source='space.slug', read_only=True)
    
    class Meta:
        model = Document
        fields = ['id', 'unique_id', 'space', 'space_slug', 'title', 'path', 'content', 'repository_id', 'branch', 'doc_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'unique_id', 'created_at', 'updated_at']


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
