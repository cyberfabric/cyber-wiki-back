"""
Serializers for source provider.
"""
from rest_framework import serializers


class SourceContentSerializer(serializers.Serializer):
    """Serializer for source content response."""
    content = serializers.CharField(help_text='File content')
    encoding = serializers.CharField(help_text='Content encoding')
    sha = serializers.CharField(help_text='File SHA/hash')
    size = serializers.IntegerField(help_text='File size in bytes')
    path = serializers.CharField(help_text='File path')
    source_uri = serializers.CharField(help_text='Source URI')
    line_start = serializers.IntegerField(required=False, help_text='Starting line (if filtered)')
    line_end = serializers.IntegerField(required=False, help_text='Ending line (if filtered)')
    total_lines = serializers.IntegerField(required=False, help_text='Total lines in file')


class SourceTreeEntrySerializer(serializers.Serializer):
    """Serializer for source tree entry."""
    path = serializers.CharField(help_text='File/directory path')
    type = serializers.CharField(help_text='Entry type (file or dir)')
    size = serializers.IntegerField(help_text='Size in bytes')
    sha = serializers.CharField(help_text='SHA/hash')
    source_uri = serializers.CharField(help_text='Source URI')
