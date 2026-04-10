"""
Wiki models for spaces, documents, comments, tags, and change management.
"""
from django.db import models
from django.contrib.auth.models import User
import uuid


class Space(models.Model):
    """
    Organizational container for documents.
    """
    slug = models.SlugField(max_length=100, unique=True, help_text='URL-friendly identifier')
    name = models.CharField(max_length=255, help_text='Display name')
    description = models.TextField(blank=True, help_text='Space description')
    is_public = models.BooleanField(default=False, help_text='Whether space is publicly accessible')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_spaces')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Space'
        verbose_name_plural = 'Spaces'
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(models.Model):
    """
    Document within a space, linked to Git repository content.
    """
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=500, help_text='Document title')
    path = models.CharField(max_length=1000, help_text='File path in repository')
    content = models.TextField(blank=True, help_text='Cached document content')
    repository_id = models.CharField(max_length=255, default='', help_text='Repository identifier')
    branch = models.CharField(max_length=255, default='main', help_text='Git branch')
    doc_type = models.CharField(max_length=20, default='markdown', help_text='Document type')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-updated_at']
        unique_together = [['space', 'repository_id', 'path']]

    def __str__(self):
        return self.title


class GitSyncConfig(models.Model):
    """
    Configuration for Git synchronization.
    """
    
    class SyncDirection(models.TextChoices):
        PULL_ONLY = 'pull_only', 'Pull Only'
        PUSH_ONLY = 'push_only', 'Push Only'
        BIDIRECTIONAL = 'bidirectional', 'Bidirectional'
    
    class SyncStatus(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        ERROR = 'error', 'Error'
    
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name='sync_configs')
    repository_url = models.URLField(max_length=500, help_text='Git repository URL')
    branch = models.CharField(max_length=255, default='main', help_text='Branch to sync')
    direction = models.CharField(
        max_length=20,
        choices=SyncDirection.choices,
        default=SyncDirection.PULL_ONLY
    )
    status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.ACTIVE
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Git Sync Config'
        verbose_name_plural = 'Git Sync Configs'

    def __str__(self):
        return f"{self.space.name} - {self.repository_url}"


class Tag(models.Model):
    """
    Tag for categorizing documents.
    """
    
    class TagType(models.TextChoices):
        AUTO = 'auto', 'Auto-generated'
        CUSTOM = 'custom', 'Custom'
    
    name = models.CharField(max_length=100, unique=True, db_index=True)
    tag_type = models.CharField(
        max_length=10,
        choices=TagType.choices,
        default=TagType.CUSTOM
    )
    usage_count = models.IntegerField(default=0, help_text='Number of documents using this tag')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['-usage_count', 'name']

    def __str__(self):
        return self.name


class DocumentTag(models.Model):
    """
    Association between documents and tags with relevance scoring.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='document_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='document_tags')
    relevance_score = models.FloatField(default=1.0, help_text='TF-IDF or manual relevance score')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['document', 'tag']]
        verbose_name = 'Document Tag'
        verbose_name_plural = 'Document Tags'
        ordering = ['-relevance_score']

    def __str__(self):
        return f"{self.document.title} - {self.tag.name}"


class DocumentLink(models.Model):
    """
    Links between documents for navigation and discovery.
    """
    
    class LinkType(models.TextChoices):
        INTERNAL = 'internal', 'Internal Link'
        EXTERNAL = 'external', 'External Link'
        REFERENCE = 'reference', 'Reference'
    
    source_document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='outgoing_links')
    target_document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True, related_name='incoming_links')
    target_url = models.URLField(max_length=1000, blank=True, help_text='External URL if not internal link')
    link_type = models.CharField(max_length=20, choices=LinkType.choices, default=LinkType.INTERNAL)
    is_valid = models.BooleanField(default=True, help_text='Whether link target exists')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Document Link'
        verbose_name_plural = 'Document Links'

    def __str__(self):
        if self.target_document:
            return f"{self.source_document.title} → {self.target_document.title}"
        return f"{self.source_document.title} → {self.target_url}"


class FileComment(models.Model):
    """
    Inline comment on source files with line anchoring.
    """
    
    class AnchoringStatus(models.TextChoices):
        ANCHORED = 'anchored', 'Anchored'
        MOVED = 'moved', 'Moved'
        OUTDATED = 'outdated', 'Outdated'
    
    source_uri = models.CharField(max_length=1000, db_index=True, help_text='Universal source address')
    line_start = models.IntegerField(null=True, blank=True, help_text='Starting line number (1-indexed)')
    line_end = models.IntegerField(null=True, blank=True, help_text='Ending line number (1-indexed)')
    text = models.TextField(help_text='Comment text (supports Markdown)')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_comments')
    thread_id = models.UUIDField(default=uuid.uuid4, db_index=True, help_text='Thread identifier for grouping')
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    is_resolved = models.BooleanField(default=False, help_text='Whether comment is resolved')
    anchoring_status = models.CharField(
        max_length=20,
        choices=AnchoringStatus.choices,
        default=AnchoringStatus.ANCHORED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'File Comment'
        verbose_name_plural = 'File Comments'
        ordering = ['source_uri', 'line_start', 'created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.source_uri}"


class UserChange(models.Model):
    """
    Pending user changes for approval workflow.
    """
    
    class ChangeStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        COMMITTED = 'committed', 'Committed'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='changes')
    repository_full_name = models.CharField(max_length=255, help_text='Repository identifier')
    file_path = models.CharField(max_length=1000, help_text='File path in repository')
    original_content = models.TextField(help_text='Original file content')
    modified_content = models.TextField(help_text='Modified file content')
    commit_message = models.TextField(blank=True, help_text='Commit message')
    status = models.CharField(
        max_length=20,
        choices=ChangeStatus.choices,
        default=ChangeStatus.PENDING
    )
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_changes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Change'
        verbose_name_plural = 'User Changes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.file_path} ({self.status})"
