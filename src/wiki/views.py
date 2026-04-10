"""
Main wiki views for spaces and documents.
"""
from django.db import models
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Space, Document
from .serializers import SpaceSerializer, DocumentSerializer
from .tree_builder import TreeBuilder
from .config_parser import CyberWikiConfigParser
from source_provider.git_source import GitSourceProvider
from source_provider.base import SourceAddress


class SpaceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing spaces.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SpaceSerializer
    queryset = Space.objects.all()
    lookup_field = 'slug'
    
    @extend_schema(
        operation_id='wiki_spaces_list',
        summary='List spaces',
        description='List all spaces accessible to the user.',
        responses={200: SpaceSerializer(many=True)},
        tags=['wiki'],
    )
    def list(self, request):
        # Filter by public or created_by
        queryset = self.queryset.filter(
            models.Q(is_public=True) | models.Q(created_by=request.user)
        )
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        space = serializer.save(created_by=request.user)
        response_serializer = self.serializer_class(space)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing documents.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer
    queryset = Document.objects.all()
    
    @extend_schema(
        operation_id='wiki_documents_list',
        summary='List documents',
        description='List documents in a space.',
        parameters=[
            OpenApiParameter(name='space', type=str, required=False, description='Filter by space slug'),
        ],
        responses={200: DocumentSerializer(many=True)},
        tags=['wiki'],
    )
    def list(self, request):
        queryset = self.queryset
        
        space_slug = request.query_params.get('space')
        if space_slug:
            queryset = queryset.filter(space__slug=space_slug)
        
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_documents_tree',
        summary='Get document tree',
        description='Get navigation tree for documents.',
        parameters=[
            OpenApiParameter(name='space', type=str, required=True, description='Space slug'),
            OpenApiParameter(name='mode', type=str, required=False, description='Tree mode (developer/document)'),
        ],
        responses={200: {'type': 'object'}},
        tags=['wiki'],
    )
    @action(detail=False, methods=['get'])
    def tree(self, request):
        space_slug = request.query_params.get('space')
        mode = request.query_params.get('mode', 'document')
        
        if not space_slug:
            return Response({'error': 'space parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            space = Space.objects.get(slug=space_slug)
        except Space.DoesNotExist:
            return Response({'error': 'Space not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get documents for this space
        documents = Document.objects.filter(space=space)
        
        # Build file list from documents
        files = [
            {'path': doc.path, 'type': 'file', 'size': len(doc.content)}
            for doc in documents
        ]
        
        # Get config (default for now)
        config = CyberWikiConfigParser.get_default()
        
        # Build tree
        builder = TreeBuilder(config)
        
        if mode == 'developer':
            tree = builder.build_developer_tree(files)
        else:
            tree = builder.build_document_tree(files)
        
        return Response(tree.to_dict())
    
    @extend_schema(
        operation_id='wiki_documents_search',
        summary='Search documents',
        description='Search documents by text and tags.',
        parameters=[
            OpenApiParameter(name='q', type=str, required=False, description='Search query'),
            OpenApiParameter(name='tags', type=str, required=False, description='Comma-separated tag names'),
            OpenApiParameter(name='space', type=str, required=False, description='Filter by space slug'),
        ],
        responses={200: DocumentSerializer(many=True)},
        tags=['wiki'],
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        queryset = self.queryset
        
        # Filter by space
        space_slug = request.query_params.get('space')
        if space_slug:
            queryset = queryset.filter(space__slug=space_slug)
        
        # Search by text
        query = request.query_params.get('q')
        if query:
            queryset = queryset.filter(
                models.Q(title__icontains=query) | models.Q(content__icontains=query)
            )
        
        # Filter by tags
        tags = request.query_params.get('tags')
        if tags:
            tag_names = [t.strip() for t in tags.split(',')]
            queryset = queryset.filter(document_tags__tag__name__in=tag_names).distinct()
        
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
