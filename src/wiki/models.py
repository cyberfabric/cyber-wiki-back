"""
Wiki models for spaces, documents, comments, tags, and change management.
"""
from django.db import models
from django.contrib.auth.models import User
import uuid


class Space(models.Model):
    """
    A Space is a container for Pages, similar to Confluence spaces.
    Each space is linked to a Git repository and has its own configuration.
    """
    # Primary Key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    slug = models.SlugField(max_length=100, unique=True, db_index=True, help_text='URL-friendly identifier')
    name = models.CharField(max_length=200, help_text='Display name')
    description = models.TextField(blank=True, help_text='Space description')
    
    # Ownership
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_spaces',
        null=True,  # Nullable for migration, will be populated from created_by
        help_text='Space owner with full control'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_spaces',
        help_text='User who created the space (legacy field)'
    )
    
    # Visibility
    VISIBILITY_CHOICES = [
        ('private', 'Private - Only owner and explicitly shared users'),
        ('team', 'Team - All authenticated users'),
        ('public', 'Public - Anyone with link'),
    ]
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private',
        help_text='Space visibility level'
    )
    is_public = models.BooleanField(
        default=False,
        help_text='Legacy field - use visibility instead'
    )
    
    # Git Integration
    git_provider = models.CharField(
        max_length=50,
        choices=[
            ('bitbucket_server', 'Bitbucket Server'),
            ('github', 'GitHub'),
            ('local_git', 'Local Git Repository'),
        ],
        null=True,
        blank=True,
        help_text='Git provider type'
    )
    git_base_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text='Git provider base URL or filesystem path for local Git'
    )
    git_project_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Git project key (for Bitbucket)'
    )
    git_repository_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text='Git repository identifier'
    )
    git_repository_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text='Git repository name'
    )
    git_default_branch = models.CharField(
        max_length=100,
        default='',
        blank=True,
        help_text='Default Git branch (auto-detected if empty)'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last Git sync timestamp'
    )
    
    # Counters (denormalized for performance)
    page_count = models.IntegerField(
        default=0,
        help_text='Number of pages in this space'
    )

    class Meta:
        verbose_name = 'Space'
        verbose_name_plural = 'Spaces'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['visibility']),
        ]

    def __str__(self):
        return self.name


class Document(models.Model):
    """
    Document within a space, linked to Git repository content.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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


class SpacePermission(models.Model):
    """
    Defines user-specific permissions for a space.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='space_permissions'
    )
    
    ROLE_CHOICES = [
        ('viewer', 'Viewer - Read only'),
        ('editor', 'Editor - Can edit pages'),
        ('admin', 'Admin - Full control'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    
    created_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_permissions'
    )
    
    class Meta:
        db_table = 'space_permissions'
        unique_together = [['space', 'user']]
        indexes = [
            models.Index(fields=['user', 'role']),
        ]
        verbose_name = 'Space Permission'
        verbose_name_plural = 'Space Permissions'
    
    def __str__(self):
        return f"{self.user.username} - {self.space.name} ({self.role})"


class SpaceConfiguration(models.Model):
    """
    Stores configuration settings for a space.
    Uses JSON field for flexible schema.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space = models.OneToOneField(
        Space,
        on_delete=models.CASCADE,
        related_name='configuration'
    )
    
    # File tree to page mapping configuration
    file_tree_config = models.JSONField(
        default=dict,
        help_text="""
        Configuration for mapping Git file tree to pages.
        Example: {
            "root_path": "/docs",
            "file_extensions": [".md", ".mdx"],
            "ignore_patterns": ["node_modules", ".git"],
            "title_from_frontmatter": true,
            "title_field": "title"
        }
        """
    )
    
    # Page display configuration
    page_display_config = models.JSONField(
        default=dict,
        help_text="""
        Configuration for page display.
        Example: {
            "show_breadcrumbs": true,
            "show_toc": true,
            "show_last_updated": true,
            "default_view_mode": "document"
        }
        """
    )
    
    # Sync configuration
    sync_config = models.JSONField(
        default=dict,
        help_text="""
        Configuration for Git sync.
        Example: {
            "auto_sync": true,
            "sync_interval_minutes": 15,
            "sync_on_webhook": true,
            "conflict_resolution": "git_wins"
        }
        """
    )
    
    # Custom settings (extensible)
    custom_settings = models.JSONField(
        default=dict,
        help_text="Additional custom settings"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'space_configurations'
        verbose_name = 'Space Configuration'
        verbose_name_plural = 'Space Configurations'
    
    def __str__(self):
        return f"Configuration for {self.space.name}"


class SpaceShortcut(models.Model):
    """
    User-defined shortcuts to pages within a space.
    Similar to Confluence space shortcuts.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name='shortcuts'
    )
    # Note: Will reference Page model once it's created
    page_id = models.IntegerField(
        help_text='ID of the target page'
    )
    
    label = models.CharField(max_length=200)
    order = models.IntegerField(default=0)
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_shortcuts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'space_shortcuts'
        ordering = ['order', 'label']
        verbose_name = 'Space Shortcut'
        verbose_name_plural = 'Space Shortcuts'
    
    def __str__(self):
        return f"{self.space.name} - {self.label}"


class UserSpacePreference(models.Model):
    """
    User-specific preferences for spaces (favorites, recent, etc.)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='space_preferences'
    )
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name='user_preferences'
    )
    
    is_favorite = models.BooleanField(default=False)
    last_visited_at = models.DateTimeField(auto_now=True)
    visit_count = models.IntegerField(default=0)
    
    # Last viewed page in this space (will be FK to Page once created)
    last_viewed_page_id = models.IntegerField(
        null=True,
        blank=True,
        help_text='ID of last viewed page'
    )
    
    class Meta:
        db_table = 'user_space_preferences'
        unique_together = [['user', 'space']]
        indexes = [
            models.Index(fields=['user', '-last_visited_at']),
            models.Index(fields=['user', 'is_favorite']),
        ]
        verbose_name = 'User Space Preference'
        verbose_name_plural = 'User Space Preferences'
    
    def __str__(self):
        return f"{self.user.username} - {self.space.name}"


class SpaceAttribute(models.Model):
    """
    Extended attributes for spaces using EAV pattern.
    Allows flexible addition of custom properties without schema changes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name='attributes'
    )
    
    # Attribute identification
    field_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text='Machine identifier (e.g., total_pages, health_score)'
    )
    field_name = models.CharField(
        max_length=200,
        help_text='Human-readable label (e.g., "Total Pages", "Health Score")'
    )
    
    # Multi-type value storage
    field_value_str = models.TextField(
        null=True,
        blank=True,
        help_text='String/JSON/enum value'
    )
    field_value_int = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Integer or boolean (0/1) value'
    )
    field_value_float = models.FloatField(
        null=True,
        blank=True,
        help_text='Fractional numeric value'
    )
    
    # Metadata
    collected_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When this attribute was collected/computed'
    )
    data_source = models.CharField(
        max_length=100,
        default='',
        blank=True,
        help_text='Source discriminator (e.g., git_sync, manual, computed)'
    )
    
    # Versioning for deduplication
    version = models.BigIntegerField(
        default=0,
        help_text='Version number for deduplication'
    )
    
    class Meta:
        db_table = 'space_attributes'
        unique_together = [['space', 'field_id', 'version']]
        indexes = [
            models.Index(fields=['space', 'field_id']),
            models.Index(fields=['field_id', 'collected_at']),
            models.Index(fields=['data_source']),
        ]
        verbose_name = 'Space Attribute'
        verbose_name_plural = 'Space Attributes'
    
    def __str__(self):
        return f"{self.space.name} - {self.field_name}"
    
    def get_value(self):
        """Get the actual value based on which field is populated."""
        if self.field_value_str is not None:
            return self.field_value_str
        elif self.field_value_int is not None:
            return self.field_value_int
        elif self.field_value_float is not None:
            return self.field_value_float
        return None
