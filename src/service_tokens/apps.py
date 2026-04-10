"""
App configuration for service tokens.
"""
from django.apps import AppConfig


class ServiceTokensConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'service_tokens'
    verbose_name = 'Service Tokens'
