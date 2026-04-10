"""
Admin configuration for service tokens.
"""
from django.contrib import admin
from .models import ServiceToken


@admin.register(ServiceToken)
class ServiceTokenAdmin(admin.ModelAdmin):
    """Admin interface for service tokens."""
    list_display = ['user', 'service_type', 'base_url', 'name', 'created_at']
    list_filter = ['service_type', 'created_at']
    search_fields = ['user__username', 'base_url', 'name']
    readonly_fields = ['created_at', 'updated_at', 'encrypted_token', 'encrypted_username']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'service_type', 'name')
        }),
        ('Service Configuration', {
            'fields': ('base_url', 'header_name')
        }),
        ('Encrypted Data (Read-Only)', {
            'fields': ('encrypted_token', 'encrypted_username'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
