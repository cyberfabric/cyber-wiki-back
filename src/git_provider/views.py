"""
Views for Git provider management and operations.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from service_tokens.models import ServiceToken
from .factory import GitProviderFactory
from .serializers import (
    RepositorySerializer,
    FileContentSerializer, TreeEntrySerializer, PullRequestSerializer,
    CommitSerializer
)
from users.decorators import cached_api_response
import base64
import logging

logger = logging.getLogger(__name__)


class GitProviderViewSet(viewsets.ViewSet):
    """
    ViewSet for Git provider operations.
    """
    permission_classes = [IsAuthenticated]
    
    # Note: Git credentials are now managed via /api/service-tokens/v1/tokens/
    # This ViewSet only handles repository operations using those credentials
    
    def _get_provider(self, request):
        """Get Git provider instance for the user."""
        provider_type = request.query_params.get('provider')
        base_url = request.query_params.get('base_url')
        
        if not provider_type or not base_url:
            raise ValueError('provider and base_url are required')
        
        try:
            service_token = ServiceToken.objects.get(user=request.user, service_type=provider_type, base_url=base_url)
            return GitProviderFactory.create_from_service_token(service_token)
        except ServiceToken.DoesNotExist:
            raise ValueError('Git credentials not found')
    
    @extend_schema(
        operation_id='git_provider_repositories_list',
        summary='List repositories',
        description='List repositories accessible to the authenticated user.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='page', type=int, required=False),
            OpenApiParameter(name='per_page', type=int, required=False),
        ],
        responses={200: RepositorySerializer(many=True)},
        tags=['git-provider'],
    )
    @action(detail=False, methods=['get'], url_path='projects')
    def list_projects(self, request):
        """List projects."""
        try:
            provider = self._get_provider(request)
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 100))
            
            # Check if provider supports list_projects
            if not hasattr(provider, 'list_projects'):
                return Response(
                    {'error': 'Provider does not support project listing', 'code': 'NOT_SUPPORTED'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = provider.list_projects(page=page, per_page=per_page)
            return Response(result)
        except Exception as e:
            logger.exception(f"Error listing projects: {str(e)}")
            return Response(
                {'error': 'Internal server error', 'code': 'INTERNAL_ERROR', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='repositories')
    def list_repositories(self, request):
        """List repositories. Optionally filter by project_key."""
        try:
            provider = self._get_provider(request)
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 30))
            project_key = request.query_params.get('project_key')
            
            result = provider.list_repositories(page=page, per_page=per_page, project_key=project_key)
            return Response(result)
        except ValueError as e:
            logger.error(f"Invalid request for list_repositories: {str(e)}")
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import requests
            logger.exception(f"Error listing repositories: {str(e)}")
            
            # Check if it's an authentication error
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code == 401:
                    return Response(
                        {
                            'error': 'Authentication failed',
                            'code': 'AUTHENTICATION_FAILED',
                            'detail': 'Invalid credentials. Please check your tokens in the Configuration page and ensure they are valid and not expired.',
                            'help': 'Verify: 1) Bitbucket token is valid, 2) Username is correct, 3) Custom header token (if required) is valid and not expired'
                        },
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                elif e.response.status_code == 403:
                    return Response(
                        {
                            'error': 'Access forbidden',
                            'code': 'FORBIDDEN',
                            'detail': 'You do not have permission to access this resource. Check your token permissions.',
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            return Response(
                {'error': 'Internal server error', 'code': 'INTERNAL_ERROR', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        operation_id='git_provider_repository_get',
        summary='Get repository details',
        description='Get details of a specific repository.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='repo_id', type=str, required=True, location=OpenApiParameter.PATH),
        ],
        responses={200: RepositorySerializer},
        tags=['git-provider'],
    )
    @action(detail=True, methods=['get'], url_path='')
    def get_repository(self, request, pk=None):
        """Get repository details."""
        try:
            provider = self._get_provider(request)
            repo = provider.get_repository(pk)
            return Response(repo)
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        operation_id='git_provider_file_get',
        summary='Get file content',
        description='Get content of a specific file.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='project_key', type=str, required=True, description='Project key (for Bitbucket Server) or owner (for GitHub)'),
            OpenApiParameter(name='repo_slug', type=str, required=True, description='Repository slug/name'),
            OpenApiParameter(name='file_path', type=str, required=True, description='Path to the file'),
            OpenApiParameter(name='branch', type=str, required=False),
        ],
        responses={200: FileContentSerializer},
        tags=['git-provider'],
    )
    @cached_api_response(
        provider_type_param='provider',
        endpoint_func=lambda view, **kwargs: '/file'
    )
    @action(detail=False, methods=['get'], url_path='file')
    def get_file(self, request):
        """Get file content."""
        try:
            provider = self._get_provider(request)
            project_key = request.query_params.get('project_key')
            repo_slug = request.query_params.get('repo_slug')
            file_path = request.query_params.get('file_path')
            branch = request.query_params.get('branch', 'main')
            
            if not project_key or not repo_slug or not file_path:
                return Response(
                    {'error': 'project_key, repo_slug, and file_path are required', 'code': 'MISSING_PARAMETERS'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            file_data = provider.get_file_content(project_key, repo_slug, file_path, branch)
            
            # Decode base64 content if needed
            if file_data.get('encoding') == 'base64':
                try:
                    file_data['content'] = base64.b64decode(file_data['content']).decode('utf-8')
                    file_data['encoding'] = 'utf-8'
                except Exception:
                    pass  # Keep as base64 if decode fails
            
            return Response(file_data)
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import requests
            logger.exception(f"Error getting file content: {str(e)}")
            
            # Check if it's an authentication error
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code == 401:
                    return Response(
                        {
                            'error': 'Authentication failed',
                            'code': 'AUTHENTICATION_FAILED',
                            'detail': 'Invalid credentials. Please check your tokens in the Configuration page and ensure they are valid and not expired.',
                            'help': 'Verify: 1) Git provider token is valid, 2) Username is correct, 3) Custom header token (if required) is valid and not expired'
                        },
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                elif e.response.status_code == 403:
                    return Response(
                        {
                            'error': 'Access forbidden',
                            'code': 'FORBIDDEN',
                            'detail': 'You do not have permission to access this resource. Check your token permissions.',
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            return Response(
                {'error': 'Internal server error', 'code': 'INTERNAL_ERROR', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        operation_id='git_provider_tree_get',
        summary='Get directory tree',
        description='Get directory tree for a repository.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='project_key', type=str, required=True, description='Project key (for Bitbucket Server) or owner (for GitHub)'),
            OpenApiParameter(name='repo_slug', type=str, required=True, description='Repository slug/name'),
            OpenApiParameter(name='path', type=str, required=False),
            OpenApiParameter(name='branch', type=str, required=False),
            OpenApiParameter(name='recursive', type=bool, required=False),
        ],
        responses={200: TreeEntrySerializer(many=True)},
        tags=['git-provider'],
    )
    @cached_api_response(
        provider_type_param='provider',
        endpoint_func=lambda view, **kwargs: '/tree'
    )
    @action(detail=False, methods=['get'], url_path='tree')
    def get_tree(self, request):
        """Get directory tree."""
        try:
            provider = self._get_provider(request)
            project_key = request.query_params.get('project_key')
            repo_slug = request.query_params.get('repo_slug')
            path = request.query_params.get('path', '')
            branch = request.query_params.get('branch', 'main')
            recursive = request.query_params.get('recursive', 'false').lower() == 'true'
            
            if not project_key or not repo_slug:
                return Response(
                    {'error': 'project_key and repo_slug are required', 'code': 'MISSING_PARAMETERS'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            tree = provider.get_directory_tree(project_key, repo_slug, path, branch, recursive)
            return Response(tree)
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import requests
            logger.exception(f"Error getting directory tree: {str(e)}")
            
            # Check if it's an authentication error
            if isinstance(e, requests.exceptions.HTTPError):
                if e.response.status_code == 401:
                    return Response(
                        {
                            'error': 'Authentication failed',
                            'code': 'AUTHENTICATION_FAILED',
                            'detail': 'Invalid credentials. Please check your tokens in the Configuration page and ensure they are valid and not expired.',
                            'help': 'Verify: 1) Git provider token is valid, 2) Username is correct, 3) Custom header token (if required) is valid and not expired'
                        },
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                elif e.response.status_code == 403:
                    return Response(
                        {
                            'error': 'Access forbidden',
                            'code': 'FORBIDDEN',
                            'detail': 'You do not have permission to access this resource. Check your token permissions.',
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            return Response(
                {'error': 'Internal server error', 'code': 'INTERNAL_ERROR', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema(
    operation_id='git_provider_repository_get',
    summary='Get repository details',
    description='Get details of a specific repository.',
    parameters=[
        OpenApiParameter(name='provider', type=str, required=True),
        OpenApiParameter(name='base_url', type=str, required=True),
        OpenApiParameter(name='repo_id', type=str, required=True, location=OpenApiParameter.PATH),
    ],
    responses={200: RepositorySerializer},
    tags=['git-provider'],
)
@action(detail=True, methods=['get'], url_path='')
def get_repository(self, request, pk=None):
    """Get repository details."""
    try:
        provider = self._get_provider(request)
        repo = provider.get_repository(pk)
        return Response(repo)
    except ValueError as e:
        return Response(
            {'error': str(e), 'code': 'INVALID_REQUEST'},
            status=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    operation_id='git_provider_file_get',
    summary='Get file content',
    description='Get content of a specific file.',
    parameters=[
        OpenApiParameter(name='provider', type=str, required=True),
        OpenApiParameter(name='base_url', type=str, required=True),
        OpenApiParameter(name='project_key', type=str, required=True, description='Project key (for Bitbucket Server) or owner (for GitHub)'),
        OpenApiParameter(name='repo_slug', type=str, required=True, description='Repository slug/name'),
        OpenApiParameter(name='file_path', type=str, required=True, description='Path to the file'),
        OpenApiParameter(name='branch', type=str, required=False),
    ],
    responses={200: FileContentSerializer},
    tags=['git-provider'],
)
@action(detail=False, methods=['get'], url_path='file')
def get_file(self, request):
    """Get file content."""
    try:
        provider = self._get_provider(request)
        project_key = request.query_params.get('project_key')
        repo_slug = request.query_params.get('repo_slug')
        file_path = request.query_params.get('file_path')
        branch = request.query_params.get('branch', 'main')
        
        if not project_key or not repo_slug or not file_path:
            return Response(
                {'error': 'project_key, repo_slug, and file_path are required', 'code': 'MISSING_PARAMETERS'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_data = provider.get_file_content(project_key, repo_slug, file_path, branch)
        
        # Decode base64 content if needed
        if file_data.get('encoding') == 'base64':
            try:
                file_data['content'] = base64.b64decode(file_data['content']).decode('utf-8')
                file_data['encoding'] = 'utf-8'
            except Exception:
                pass  # Keep as base64 if decode fails
        
        return Response(file_data)
    except ValueError as e:
        return Response(
            {'error': str(e), 'code': 'INVALID_REQUEST'},
            status=status.HTTP_400_BAD_REQUEST
        )

    
    @extend_schema(
        operation_id='git_provider_pull_requests_list',
        summary='List pull requests',
        description='List pull requests for a repository.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='repo_id', type=str, required=True, location=OpenApiParameter.PATH),
            OpenApiParameter(name='state', type=str, required=False, description='PR state (open, closed, merged)'),
            OpenApiParameter(name='page', type=int, required=False),
            OpenApiParameter(name='per_page', type=int, required=False),
        ],
        responses={200: PullRequestSerializer(many=True)},
        tags=['git-provider'],
    )
    @action(detail=True, methods=['get'], url_path='pull-requests')
    def list_pull_requests(self, request, pk=None):
        """List pull requests."""
        try:
            provider = self._get_provider(request)
            state = request.query_params.get('state', 'open')
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 30))
            
            result = provider.list_pull_requests(pk, state, page, per_page)
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        operation_id='git_provider_pull_request_get',
        summary='Get pull request details',
        description='Get details of a specific pull request.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='repo_id', type=str, required=True, location=OpenApiParameter.PATH),
            OpenApiParameter(name='number', type=int, required=True, location=OpenApiParameter.PATH),
        ],
        responses={200: PullRequestSerializer},
        tags=['git-provider'],
    )
    @action(detail=True, methods=['get'], url_path='pull-requests/(?P<number>[0-9]+)')
    def get_pull_request(self, request, pk=None, number=None):
        """Get pull request details."""
        try:
            provider = self._get_provider(request)
            pr = provider.get_pull_request(pk, int(number))
            return Response(pr)
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        operation_id='git_provider_pull_request_diff_get',
        summary='Get pull request diff',
        description='Get diff for a pull request.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='repo_id', type=str, required=True, location=OpenApiParameter.PATH),
            OpenApiParameter(name='number', type=int, required=True, location=OpenApiParameter.PATH),
        ],
        responses={200: str},
        tags=['git-provider'],
    )
    @action(detail=True, methods=['get'], url_path='pull-requests/(?P<number>[0-9]+)/diff')
    def get_pull_request_diff(self, request, pk=None, number=None):
        """Get pull request diff."""
        try:
            provider = self._get_provider(request)
            diff = provider.get_pull_request_diff(pk, int(number))
            return Response({'diff': diff})
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        operation_id='git_provider_commits_list',
        summary='List commits',
        description='List commits for a repository.',
        parameters=[
            OpenApiParameter(name='provider', type=str, required=True),
            OpenApiParameter(name='base_url', type=str, required=True),
            OpenApiParameter(name='repo_id', type=str, required=True, location=OpenApiParameter.PATH),
            OpenApiParameter(name='branch', type=str, required=False),
            OpenApiParameter(name='page', type=int, required=False),
            OpenApiParameter(name='per_page', type=int, required=False),
        ],
        responses={200: CommitSerializer(many=True)},
        tags=['git-provider'],
    )
    @action(detail=True, methods=['get'], url_path='commits')
    def list_commits(self, request, pk=None):
        """List commits."""
        try:
            provider = self._get_provider(request)
            branch = request.query_params.get('branch', 'main')
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 30))
            
            result = provider.list_commits(pk, branch, page, per_page)
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e), 'code': 'INVALID_REQUEST'},
                status=status.HTTP_400_BAD_REQUEST
            )
