"""
Views for service token management.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import ServiceToken
from .serializers import ServiceTokenSerializer, ServiceTokenCreateSerializer


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
        """Create a new service token."""
        serializer = ServiceTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract validated data
        service_type = serializer.validated_data['service_type']
        base_url = serializer.validated_data.get('base_url', '')
        token = serializer.validated_data.get('token')
        username = serializer.validated_data.get('username')
        header_name = serializer.validated_data.get('header_name')
        name = serializer.validated_data.get('name')
        
        # Create the service token instance (not saved yet)
        service_token = ServiceToken(
            user=request.user,
            service_type=service_type,
            base_url=base_url,
            header_name=header_name,
            name=name,
        )
        
        # Set encrypted fields BEFORE saving
        if token:
            service_token.set_token(token)
        else:
            # Set empty token if not provided (required field)
            service_token.set_token('')
            
        if username:
            service_token.set_username(username)
        
        # Now save with all fields set
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
