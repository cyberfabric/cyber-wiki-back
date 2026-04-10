"""
Serializers for service token management.
"""
from rest_framework import serializers
from .models import ServiceToken, ServiceType


class ServiceTokenSerializer(serializers.ModelSerializer):
    """Serializer for service tokens (read)."""
    
    class Meta:
        model = ServiceToken
        fields = [
            'id', 'service_type', 'base_url', 'username', 'header_name', 
            'name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    username = serializers.SerializerMethodField()
    
    def get_username(self, obj):
        """Return decrypted username."""
        return obj.get_username()


class ServiceTokenCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating service tokens."""
    service_type = serializers.ChoiceField(choices=ServiceType.choices)
    base_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    header_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate(self, data):
        """Validate based on service type."""
        service_type = data.get('service_type')
        
        if service_type in [ServiceType.GITHUB, ServiceType.BITBUCKET_SERVER]:
            # Git providers require base_url and token
            if not data.get('base_url'):
                raise serializers.ValidationError({
                    'base_url': 'Base URL is required for Git providers'
                })
            # Bitbucket Server requires username
            if service_type == ServiceType.BITBUCKET_SERVER and not data.get('username'):
                raise serializers.ValidationError({
                    'username': 'Username is required for Bitbucket Server'
                })
        
        elif service_type == ServiceType.JIRA:
            # JIRA requires base_url and username
            if not data.get('base_url'):
                raise serializers.ValidationError({
                    'base_url': 'Base URL is required for JIRA'
                })
            if not data.get('username'):
                raise serializers.ValidationError({
                    'username': 'Username/email is required for JIRA'
                })
        
        elif service_type == ServiceType.CUSTOM_HEADER:
            # Custom header tokens require header_name
            if not data.get('header_name'):
                raise serializers.ValidationError({
                    'header_name': 'Header name is required for custom header tokens'
                })
        
        return data
