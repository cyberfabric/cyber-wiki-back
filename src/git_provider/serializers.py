"""
Serializers for Git provider API responses.
"""
from rest_framework import serializers


class RepositorySerializer(serializers.Serializer):
    """Serializer for repository data."""
    id = serializers.CharField()
    name = serializers.CharField()
    full_name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, allow_null=True)
    private = serializers.BooleanField()
    html_url = serializers.URLField()
    clone_url = serializers.URLField()
    default_branch = serializers.CharField()
    updated_at = serializers.DateTimeField()


class FileContentSerializer(serializers.Serializer):
    """Serializer for file content."""
    path = serializers.CharField()
    content = serializers.CharField()
    encoding = serializers.CharField()
    size = serializers.IntegerField()
    sha = serializers.CharField()


class TreeEntrySerializer(serializers.Serializer):
    """Serializer for tree entry."""
    path = serializers.CharField()
    type = serializers.ChoiceField(choices=['file', 'dir'])
    size = serializers.IntegerField(required=False, allow_null=True)
    sha = serializers.CharField(required=False, allow_null=True)


class ReviewerSerializer(serializers.Serializer):
    """Serializer for PR reviewer."""
    username = serializers.CharField()
    display_name = serializers.CharField()
    avatar_url = serializers.CharField(allow_blank=True)
    role = serializers.CharField()
    status = serializers.CharField()


class PullRequestSerializer(serializers.Serializer):
    """Serializer for pull request."""
    number = serializers.IntegerField()
    title = serializers.CharField()
    state = serializers.CharField()
    author = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    html_url = serializers.URLField()
    reviewers = ReviewerSerializer(many=True, required=False, default=[])


class CommitSerializer(serializers.Serializer):
    """Serializer for commit."""
    sha = serializers.CharField()
    message = serializers.CharField()
    author = serializers.CharField()
    date = serializers.DateTimeField()
    html_url = serializers.URLField()
