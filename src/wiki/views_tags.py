"""
Views for tags and document tagging.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Tag, DocumentTag, Document
from .serializers import TagSerializer, DocumentTagSerializer
from .tag_generator import TagGenerator


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tags.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    
    @extend_schema(
        operation_id='wiki_tags_list',
        summary='List all tags',
        description='List all tags with usage counts.',
        parameters=[
            OpenApiParameter(name='type', type=str, required=False, description='Filter by tag type (auto/custom)'),
        ],
        responses={200: TagSerializer(many=True)},
        tags=['tags'],
    )
    def list(self, request):
        queryset = self.queryset
        
        tag_type = request.query_params.get('type')
        if tag_type:
            queryset = queryset.filter(tag_type=tag_type)
        
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_tags_autocomplete',
        summary='Tag autocomplete',
        description='Get tag suggestions for autocomplete.',
        parameters=[
            OpenApiParameter(name='q', type=str, required=True, description='Search query'),
        ],
        responses={200: TagSerializer(many=True)},
        tags=['tags'],
    )
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        tags = Tag.objects.filter(name__icontains=query)[:10]
        serializer = self.serializer_class(tags, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_tags_generate',
        summary='Generate auto-tags for document',
        description='Generate tags for a document using TF-IDF.',
        responses={200: {'type': 'array', 'items': {'type': 'object'}}},
        tags=['tags'],
    )
    @action(detail=False, methods=['post'])
    def generate(self, request):
        document_id = request.data.get('document_id')
        
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get all documents in the same space for corpus
        all_docs = Document.objects.filter(space=document.space)
        all_texts = [doc.content for doc in all_docs if doc.content]
        
        # Generate tags
        generated_tags = TagGenerator.generate_tags(
            document.content,
            all_texts,
            max_tags=10
        )
        
        # Create Tag objects and DocumentTag associations
        for tag_data in generated_tags:
            tag, created = Tag.objects.get_or_create(
                name=tag_data['tag'],
                defaults={'tag_type': 'auto'}
            )
            
            DocumentTag.objects.get_or_create(
                document=document,
                tag=tag,
                defaults={'relevance_score': tag_data['score']}
            )
            
            # Update usage count
            tag.usage_count = tag.document_tags.count()
            tag.save()
        
        return Response(generated_tags)


class DocumentTagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for document-tag associations.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentTagSerializer
    
    def get_queryset(self):
        document_id = self.request.query_params.get('document_id')
        if document_id:
            return DocumentTag.objects.filter(document_id=document_id).select_related('tag', 'document')
        return DocumentTag.objects.all().select_related('tag', 'document')
    
    @extend_schema(
        operation_id='wiki_document_tags_list',
        summary='List document tags',
        description='List tags for a specific document.',
        parameters=[
            OpenApiParameter(name='document_id', type=int, required=False, description='Filter by document ID'),
        ],
        responses={200: DocumentTagSerializer(many=True)},
        tags=['tags'],
    )
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        doc_tag = serializer.save(created_by=request.user)
        
        # Update tag usage count
        tag = doc_tag.tag
        tag.usage_count = tag.document_tags.count()
        tag.save()
        
        response_serializer = self.serializer_class(doc_tag)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
