"""
Views for service token management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import ServiceToken
from .serializers import ServiceTokenSerializer, ServiceTokenCreateSerializer


class ServiceTokenViewSet(viewsets.ViewSet):
    """
    ViewSet for service token operations (JIRA, ZTA, etc.).
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        operation_id='service_tokens',
        summary='Manage service tokens',
        description='Get, save, or delete service tokens (JIRA, ZTA, etc.).',
        request=ServiceTokenCreateSerializer,
        responses={
            200: ServiceTokenSerializer(many=True),
            201: ServiceTokenSerializer,
            204: None,
        },
        tags=['service-tokens'],
    )
    @action(detail=False, methods=['get', 'post', 'delete'], url_path='tokens')
    def tokens(self, request):
        """Manage service tokens (GET/POST/DELETE)."""
        
        if request.method == 'GET':
            # Get user's service tokens
            tokens = ServiceToken.objects.filter(user=request.user)
            serializer = ServiceTokenSerializer(tokens, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Save service token
            serializer = ServiceTokenCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            service_type = serializer.validated_data['service_type']
            base_url = serializer.validated_data.get('base_url') or ''
            token = serializer.validated_data.get('token')  # Optional - may be None
            username = serializer.validated_data.get('username')
            header_name = serializer.validated_data.get('header_name')
            name = serializer.validated_data.get('name')
            
            # Get or create ServiceToken
            service_token, created = ServiceToken.objects.get_or_create(
                user=request.user,
                service_type=service_type,
                base_url=base_url,
                defaults={
                    'header_name': header_name,
                    'name': name,
                }
            )
            
            # Update credentials
            # Only update token if provided (allows editing other fields without changing token)
            if token:
                service_token.set_token(token)
            if username:
                service_token.set_username(username)
            if header_name:
                service_token.header_name = header_name
            if name:
                service_token.name = name
            service_token.save()
            
            response_serializer = ServiceTokenSerializer(service_token)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        elif request.method == 'DELETE':
            # Delete service token
            service_type = request.query_params.get('service_type')
            base_url = request.query_params.get('base_url', '')
            
            if not service_type:
                return Response(
                    {'error': 'service_type is required', 'code': 'MISSING_PARAMETERS'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                service_token = ServiceToken.objects.get(
                    user=request.user, 
                    service_type=service_type, 
                    base_url=base_url
                )
                service_token.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except ServiceToken.DoesNotExist:
                return Response(
                    {'error': 'Token not found', 'code': 'NOT_FOUND'},
                    status=status.HTTP_404_NOT_FOUND
                )
