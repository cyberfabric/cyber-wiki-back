"""
Views for service token management.
"""
import json
import base64
import logging
from datetime import datetime, timezone

from django.utils import timezone as dj_tz

import requests as http_requests
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import ServiceToken, ServiceType
from .serializers import ServiceTokenSerializer, ServiceTokenCreateSerializer

logger = logging.getLogger(__name__)


class ServiceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for service token CRUD operations.
    Provides standard REST endpoints for managing service tokens.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ServiceTokenSerializer
    
    def get_queryset(self):
        """Return only the current user's service tokens."""
        return ServiceToken.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use ServiceTokenCreateSerializer for create/update operations."""
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceTokenCreateSerializer
        return ServiceTokenSerializer
    
    @extend_schema(
        operation_id='service_tokens_list',
        summary='List service tokens',
        description='Get all service tokens for the current user.',
        responses={200: ServiceTokenSerializer(many=True)},
        tags=['service-tokens'],
    )
    def list(self, request):
        """List all service tokens for the current user."""
        queryset = self.get_queryset()
        serializer = ServiceTokenSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='service_tokens_create',
        summary='Create service token',
        description='Create a new service token.',
        request=ServiceTokenCreateSerializer,
        responses={201: ServiceTokenSerializer},
        tags=['service-tokens'],
    )
    def create(self, request):
        """Create or update a service token."""
        serializer = ServiceTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        service_type = serializer.validated_data['service_type']
        base_url = serializer.validated_data.get('base_url', '')
        token = serializer.validated_data.get('token')
        username = serializer.validated_data.get('username')
        header_name = serializer.validated_data.get('header_name')
        name = serializer.validated_data.get('name')
        
        # Try to get existing token or create new one
        # For custom_header tokens, include header_name in the lookup
        lookup_fields = {
            'user': request.user,
            'service_type': service_type,
            'base_url': base_url,
        }
        if service_type == 'custom_header':
            lookup_fields['header_name'] = header_name
        
        service_token, created = ServiceToken.objects.get_or_create(
            **lookup_fields,
            defaults={
                'header_name': header_name,
                'name': name,
            }
        )
        
        # Update fields if token already existed
        if not created:
            service_token.header_name = header_name
            service_token.name = name
        
        # Set encrypted fields
        if token:
            service_token.set_token(token)
        elif created:
            # Set empty token if not provided for new tokens
            service_token.set_token('')
            
        if username:
            service_token.set_username(username)
        
        # Save with all fields set
        service_token.save()
        
        response_serializer = ServiceTokenSerializer(service_token)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        operation_id='service_tokens_retrieve',
        summary='Get service token',
        description='Get details of a specific service token.',
        responses={200: ServiceTokenSerializer},
        tags=['service-tokens'],
    )
    def retrieve(self, request, pk=None):
        """Get a specific service token by ID."""
        try:
            service_token = self.get_queryset().get(pk=pk)
            serializer = ServiceTokenSerializer(service_token)
            return Response(serializer.data)
        except ServiceToken.DoesNotExist:
            return Response(
                {'error': 'Token not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        operation_id='service_tokens_update',
        summary='Update service token',
        description='Update a service token.',
        request=ServiceTokenCreateSerializer,
        responses={200: ServiceTokenSerializer},
        tags=['service-tokens'],
    )
    def partial_update(self, request, pk=None):
        """Partially update a service token."""
        try:
            service_token = self.get_queryset().get(pk=pk)
        except ServiceToken.DoesNotExist:
            return Response(
                {'error': 'Token not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ServiceTokenCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Update fields
        if 'name' in serializer.validated_data:
            service_token.name = serializer.validated_data['name']
        if 'header_name' in serializer.validated_data:
            service_token.header_name = serializer.validated_data['header_name']
        if 'base_url' in serializer.validated_data:
            service_token.base_url = serializer.validated_data['base_url']
        
        # Update encrypted fields if provided
        if 'token' in serializer.validated_data:
            service_token.set_token(serializer.validated_data['token'])
        if 'username' in serializer.validated_data:
            service_token.set_username(serializer.validated_data['username'])
        
        service_token.save()
        
        response_serializer = ServiceTokenSerializer(service_token)
        return Response(response_serializer.data)
    
    @extend_schema(
        operation_id='service_tokens_delete',
        summary='Delete service token',
        description='Delete a service token by ID.',
        responses={204: None},
        tags=['service-tokens'],
    )
    def destroy(self, request, pk=None):
        """Delete a service token."""
        try:
            service_token = self.get_queryset().get(pk=pk)
            service_token.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ServiceToken.DoesNotExist:
            return Response(
                {'error': 'Token not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        operation_id='service_tokens_validate',
        summary='Validate service token',
        description='Test whether a service token is still valid by making a lightweight API call to the target service.',
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'valid': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'details': {'type': 'object'},
                },
            },
        },
        tags=['service-tokens'],
    )
    @action(detail=True, methods=['post'], url_path='validate')
    def validate_token(self, request, pk=None):
        """Validate a service token against its target service."""
        try:
            service_token = self.get_queryset().get(pk=pk)
        except ServiceToken.DoesNotExist:
            return Response(
                {'error': 'Token not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            token_value = service_token.get_token()
        except Exception:
            result = {'valid': False, 'message': 'Failed to decrypt token', 'details': {}}
            self._save_validation(service_token, result)
            return Response(result)

        if not token_value:
            result = {'valid': False, 'message': 'Token is empty', 'details': {}}
            self._save_validation(service_token, result)
            return Response(result)

        st = service_token.service_type

        if st == ServiceType.CUSTOM_HEADER:
            result = self._check_custom_header(token_value)
        elif st == ServiceType.GITHUB:
            result = self._check_github(token_value, service_token)
        elif st == ServiceType.BITBUCKET_SERVER:
            result = self._check_bitbucket(token_value, service_token, request.user)
        elif st == ServiceType.JIRA:
            result = self._check_jira(token_value, service_token)
        else:
            result = {'valid': False, 'message': f'Unsupported service type: {st}', 'details': {}}

        self._save_validation(service_token, result)
        return Response(result)

    # ── private helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _save_validation(service_token, result):
        """Persist validation result to the database."""
        service_token.last_validated_at = dj_tz.now()
        service_token.last_validation_valid = result['valid']
        service_token.last_validation_message = result['message'][:500]
        service_token.save(update_fields=[
            'last_validated_at', 'last_validation_valid', 'last_validation_message',
        ])

    def _check_custom_header(self, token_value):
        """Validate a custom header token (JWT exp check). Returns dict."""
        parts = token_value.split('.')
        if len(parts) != 3:
            return {'valid': True, 'message': 'Token is set (not a JWT, cannot check expiry)', 'details': {'format': 'opaque'}}

        try:
            payload_b64 = parts[1]
            payload_b64 += '=' * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        except Exception:
            return {'valid': True, 'message': 'Token is set (JWT payload unreadable)', 'details': {'format': 'jwt'}}

        exp = payload.get('exp')
        if exp is None:
            return {'valid': True, 'message': 'JWT has no expiry claim', 'details': {'format': 'jwt'}}

        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        if exp_dt < now:
            delta = now - exp_dt
            return {
                'valid': False,
                'message': f'JWT expired {self._humanize_delta(delta)} ago',
                'details': {'format': 'jwt', 'expired_at': exp_dt.isoformat()},
            }

        delta = exp_dt - now
        return {
            'valid': True,
            'message': f'JWT valid, expires in {self._humanize_delta(delta)}',
            'details': {'format': 'jwt', 'expires_at': exp_dt.isoformat()},
        }

    @staticmethod
    def _check_github(token_value, service_token):
        """Validate GitHub token via GET /user. Returns dict."""
        base_url = service_token.base_url or 'https://api.github.com'
        try:
            resp = http_requests.get(
                f'{base_url}/user',
                headers={
                    'Authorization': f'Bearer {token_value}',
                    'Accept': 'application/vnd.github.v3+json',
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'valid': True,
                    'message': f'Authenticated as {data.get("login", "?")}',
                    'details': {'login': data.get('login')},
                }
            return {'valid': False, 'message': f'GitHub returned HTTP {resp.status_code}', 'details': {}}
        except http_requests.RequestException as e:
            return {'valid': False, 'message': f'Connection error: {str(e)}', 'details': {}}

    @staticmethod
    def _check_bitbucket(token_value, service_token, user):
        """Validate Bitbucket Server token via lightweight API call. Returns dict."""
        base_url = service_token.base_url
        if not base_url:
            return {'valid': False, 'message': 'No base URL configured', 'details': {}}

        username = service_token.get_username()
        headers = {'Content-Type': 'application/json'}

        # Add custom header (ZTA) if available for this user
        try:
            custom_token = ServiceToken.objects.filter(
                user=user,
                service_type=ServiceType.CUSTOM_HEADER,
            ).order_by('base_url').first()
            if custom_token:
                h_name = custom_token.header_name
                h_value = custom_token.get_token()
                if h_name and h_value:
                    headers[h_name] = h_value
        except Exception:
            pass

        auth = None
        if username:
            auth = (username, token_value)
        else:
            headers['Authorization'] = f'Bearer {token_value}'

        try:
            resp = http_requests.get(
                f'{base_url}/rest/api/1.0/users',
                headers=headers,
                auth=auth,
                params={'limit': 1},
                timeout=10,
            )
            if resp.status_code == 200:
                return {'valid': True, 'message': 'Bitbucket Server authentication successful', 'details': {}}
            return {'valid': False, 'message': f'Bitbucket returned HTTP {resp.status_code}', 'details': {}}
        except http_requests.RequestException as e:
            return {'valid': False, 'message': f'Connection error: {str(e)}', 'details': {}}

    @staticmethod
    def _check_jira(token_value, service_token):
        """Validate JIRA token via GET /rest/api/2/myself. Returns dict."""
        base_url = service_token.base_url
        if not base_url:
            return {'valid': False, 'message': 'No base URL configured', 'details': {}}

        username = service_token.get_username()
        try:
            resp = http_requests.get(
                f'{base_url}/rest/api/2/myself',
                auth=(username or '', token_value) if username else None,
                headers={'Content-Type': 'application/json'},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'valid': True,
                    'message': f'Authenticated as {data.get("displayName", "?")}',
                    'details': {'displayName': data.get('displayName')},
                }
            return {'valid': False, 'message': f'JIRA returned HTTP {resp.status_code}', 'details': {}}
        except http_requests.RequestException as e:
            return {'valid': False, 'message': f'Connection error: {str(e)}', 'details': {}}

    @staticmethod
    def _humanize_delta(delta):
        """Convert timedelta to a human-readable string."""
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            return f'{total_seconds}s'
        minutes = total_seconds // 60
        if minutes < 60:
            return f'{minutes}m'
        hours = minutes // 60
        if hours < 24:
            return f'{hours}h {minutes % 60}m'
        days = hours // 24
        return f'{days}d {hours % 24}h'
