"""
Views for file comments API.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import FileComment
from .serializers import FileCommentSerializer, FileCommentCreateSerializer
from users.permissions import IsCommenterOrAbove


class FileCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for file comments with line anchoring.
    """
    permission_classes = [IsAuthenticated, IsCommenterOrAbove]
    serializer_class = FileCommentSerializer
    
    def get_queryset(self):
        source_uri = self.request.query_params.get('source_uri')
        if source_uri:
            return FileComment.objects.filter(source_uri=source_uri, parent_comment=None).select_related('author').prefetch_related('replies')
        return FileComment.objects.filter(parent_comment=None).select_related('author').prefetch_related('replies')
    
    @extend_schema(
        operation_id='wiki_comments_list',
        summary='List comments for a source URI',
        description='Retrieve all comments for a specific source file or line range.',
        parameters=[
            OpenApiParameter(name='source_uri', type=str, required=False, description='Filter by source URI'),
            OpenApiParameter(name='is_resolved', type=bool, required=False, description='Filter by resolution status'),
        ],
        responses={200: FileCommentSerializer(many=True)},
        tags=['comments'],
    )
    def list(self, request):
        queryset = self.get_queryset()
        
        # Filter by resolution status
        is_resolved = request.query_params.get('is_resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_comments_create',
        summary='Create a new comment',
        description='Add an inline comment to a source file at a specific line or block.',
        request=FileCommentCreateSerializer,
        responses={201: FileCommentSerializer},
        tags=['comments'],
    )
    def create(self, request):
        serializer = FileCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comment = serializer.save(author=request.user)
        response_serializer = FileCommentSerializer(comment)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        operation_id='wiki_comments_resolve',
        summary='Resolve a comment thread',
        description='Mark a comment thread as resolved.',
        responses={200: FileCommentSerializer},
        tags=['comments'],
    )
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        comment = self.get_object()
        comment.is_resolved = True
        comment.save()
        serializer = self.serializer_class(comment)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_comments_unresolve',
        summary='Unresolve a comment thread',
        description='Mark a comment thread as unresolved.',
        responses={200: FileCommentSerializer},
        tags=['comments'],
    )
    @action(detail=True, methods=['post'])
    def unresolve(self, request, pk=None):
        comment = self.get_object()
        comment.is_resolved = False
        comment.save()
        serializer = self.serializer_class(comment)
        return Response(serializer.data)
