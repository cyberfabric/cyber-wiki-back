"""
Views for document links.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import DocumentLink, Document
from .serializers import DocumentLinkSerializer
from .link_parser import LinkParser


class DocumentLinkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing document links.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentLinkSerializer
    
    def get_queryset(self):
        document_id = self.request.query_params.get('document_id')
        if document_id:
            return DocumentLink.objects.filter(source_document_id=document_id).select_related('source_document', 'target_document')
        return DocumentLink.objects.all().select_related('source_document', 'target_document')
    
    @extend_schema(
        operation_id='wiki_links_list',
        summary='List document links',
        description='List outgoing links for a document.',
        parameters=[
            OpenApiParameter(name='document_id', type=int, required=False, description='Filter by source document ID'),
        ],
        responses={200: DocumentLinkSerializer(many=True)},
        tags=['links'],
    )
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_links_backlinks',
        summary='Get document backlinks',
        description='Get incoming links (backlinks) for a document.',
        parameters=[
            OpenApiParameter(name='document_id', type=int, required=True, location=OpenApiParameter.PATH),
        ],
        responses={200: DocumentLinkSerializer(many=True)},
        tags=['links'],
    )
    @action(detail=True, methods=['get'])
    def backlinks(self, request, pk=None):
        backlinks = DocumentLink.objects.filter(target_document_id=pk).select_related('source_document', 'target_document')
        serializer = self.serializer_class(backlinks, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='wiki_links_extract',
        summary='Extract links from document',
        description='Extract and parse all links from a document.',
        responses={200: {'type': 'array', 'items': {'type': 'object'}}},
        tags=['links'],
    )
    @action(detail=False, methods=['post'])
    def extract(self, request):
        document_id = request.data.get('document_id')
        
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Extract links from content
        links = LinkParser.extract_all_links(document.content)
        
        # Create DocumentLink objects
        for link in links:
            if link['type'] == 'internal':
                # Try to find target document
                # This is simplified - in production, you'd resolve the path properly
                target_doc = None
            else:
                target_doc = None
            
            DocumentLink.objects.get_or_create(
                source_document=document,
                target_url=link['url'],
                defaults={
                    'target_document': target_doc,
                    'link_type': link['type'],
                    'is_valid': target_doc is not None if link['type'] == 'internal' else True
                }
            )
        
        return Response(links)
    
    @extend_schema(
        operation_id='wiki_links_validate',
        summary='Validate document links',
        description='Validate all links in a document.',
        responses={200: {'type': 'object'}},
        tags=['links'],
    )
    @action(detail=False, methods=['post'])
    def validate(self, request):
        document_id = request.data.get('document_id')
        
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
        
        links = DocumentLink.objects.filter(source_document=document)
        
        valid_count = links.filter(is_valid=True).count()
        invalid_count = links.filter(is_valid=False).count()
        
        return Response({
            'total': links.count(),
            'valid': valid_count,
            'invalid': invalid_count
        })
