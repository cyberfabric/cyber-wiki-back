"""
Views for source provider operations.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .base import SourceAddress
from .git_source import GitSourceProvider
from .serializers import SourceContentSerializer, SourceTreeEntrySerializer


@extend_schema(
    operation_id='source_content_get',
    summary='Get source content by URI',
    description='Retrieve file content using a universal source URI.',
    parameters=[
        OpenApiParameter(
            name='uri',
            type=str,
            required=True,
            location=OpenApiParameter.QUERY,
            description='Source URI (e.g., git://github/owner_repo/main/README.md#10-20)',
        )
    ],
    responses={
        200: SourceContentSerializer,
        400: 'Invalid URI format',
        404: 'Content not found',
    },
    tags=['source'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_content(request):
    """
    Get source content by URI.
    """
    uri = request.query_params.get('uri')
    
    if not uri:
        return Response(
            {'error': 'uri parameter is required', 'code': 'MISSING_PARAMETER'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Parse source address
        address = SourceAddress.parse(uri)
        
        # Get content using Git source provider
        provider = GitSourceProvider(request.user)
        content = provider.get_content(address)
        
        return Response(content)
    
    except ValueError as e:
        return Response(
            {'error': str(e), 'code': 'INVALID_URI'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e), 'code': 'RETRIEVAL_ERROR'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    operation_id='source_tree_get',
    summary='Get directory tree by URI',
    description='Retrieve directory tree using a universal source URI.',
    parameters=[
        OpenApiParameter(
            name='uri',
            type=str,
            required=True,
            location=OpenApiParameter.QUERY,
            description='Source URI (e.g., git://github/owner_repo/main/src)',
        ),
        OpenApiParameter(
            name='recursive',
            type=bool,
            required=False,
            location=OpenApiParameter.QUERY,
            description='Whether to recursively list all files',
        )
    ],
    responses={
        200: SourceTreeEntrySerializer(many=True),
        400: 'Invalid URI format',
        404: 'Directory not found',
    },
    tags=['source'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tree(request):
    """
    Get directory tree by URI.
    """
    uri = request.query_params.get('uri')
    
    if not uri:
        return Response(
            {'error': 'uri parameter is required', 'code': 'MISSING_PARAMETER'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Parse source address
        address = SourceAddress.parse(uri)
        
        # Get recursive flag
        recursive = request.query_params.get('recursive', 'false').lower() == 'true'
        
        # Get tree using Git source provider
        provider = GitSourceProvider(request.user)
        tree = provider.get_tree(address, recursive=recursive)
        
        return Response(tree)
    
    except ValueError as e:
        return Response(
            {'error': str(e), 'code': 'INVALID_URI'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e), 'code': 'RETRIEVAL_ERROR'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
