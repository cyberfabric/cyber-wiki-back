"""
User management views for profile, tokens, favorites, and preferences.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import UserProfile, ApiToken, FavoriteRepository, RecentRepository, RepositoryViewMode, RepositorySettings
from .serializers import (
    UserProfileSerializer, ApiTokenSerializer, ApiTokenCreateSerializer,
    FavoriteRepositorySerializer, RecentRepositorySerializer, RepositoryViewModeSerializer,
    RepositorySettingsSerializer, UserSettingsUpdateSerializer
)


class UserProfileViewSet(viewsets.ViewSet):
    """
    ViewSet for user profile management.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        operation_id='user_management_profile_get',
        summary='Get user profile',
        description='Retrieve the current user\'s profile information.',
        responses={200: UserProfileSerializer},
        tags=['user_management'],
    )
    def retrieve(self, request):
        """Get current user's profile."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='user_management_profile_update',
        summary='Update user profile',
        description='Update the current user\'s profile settings.',
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        tags=['user_management'],
    )
    def update(self, request):
        """Update current user's profile."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ApiTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for API token management.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ApiTokenSerializer
    
    def get_queryset(self):
        return ApiToken.objects.filter(user=self.request.user)
    
    @extend_schema(
        operation_id='user_management_tokens_list',
        summary='List API tokens',
        description='List all API tokens for the current user.',
        responses={200: ApiTokenSerializer(many=True)},
        tags=['user_management'],
    )
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='user_management_tokens_create',
        summary='Create API token',
        description='Create a new API token for programmatic access.',
        request=ApiTokenCreateSerializer,
        responses={201: ApiTokenSerializer},
        tags=['user_management'],
    )
    def create(self, request):
        serializer = ApiTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = ApiToken.objects.create(
            user=request.user,
            name=serializer.validated_data['name'],
            token=ApiToken.generate_token()
        )
        response_serializer = ApiTokenSerializer(token)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        operation_id='user_management_tokens_delete',
        summary='Delete API token',
        description='Delete an API token by ID.',
        responses={204: None},
        tags=['user_management'],
    )
    def destroy(self, request, pk=None):
        try:
            token = self.get_queryset().get(pk=pk)
            token.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ApiToken.DoesNotExist:
            return Response(
                {'error': 'Token not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )


class FavoriteRepositoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing favorite repositories.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteRepositorySerializer
    
    def get_queryset(self):
        return FavoriteRepository.objects.filter(user=self.request.user)
    
    @extend_schema(
        operation_id='user_management_favorites_list',
        summary='List favorite repositories',
        description='List all favorite repositories for the current user.',
        responses={200: FavoriteRepositorySerializer(many=True)},
        tags=['user_management'],
    )
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='user_management_favorites_create',
        summary='Add favorite repository',
        description='Add a repository to favorites.',
        request=FavoriteRepositorySerializer,
        responses={201: FavoriteRepositorySerializer},
        tags=['user_management'],
    )
    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite, created = FavoriteRepository.objects.get_or_create(
            user=request.user,
            repository_id=serializer.validated_data['repository_id']
        )
        response_serializer = self.serializer_class(favorite)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        operation_id='user_management_favorites_delete',
        summary='Remove favorite repository',
        description='Remove a repository from favorites.',
        responses={204: None},
        tags=['user_management'],
    )
    def destroy(self, request, pk=None):
        try:
            favorite = self.get_queryset().get(pk=pk)
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FavoriteRepository.DoesNotExist:
            return Response(
                {'error': 'Favorite not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )


class RecentRepositoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing recent repositories.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RecentRepositorySerializer
    
    def get_queryset(self):
        return RecentRepository.objects.filter(user=self.request.user)
    
    @extend_schema(
        operation_id='user_management_recent_list',
        summary='List recent repositories',
        description='List recently viewed repositories for the current user.',
        responses={200: RecentRepositorySerializer(many=True)},
        tags=['user_management'],
    )
    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data)


class RepositoryViewModeViewSet(viewsets.ViewSet):
    """
    ViewSet for managing repository view mode preferences.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        operation_id='user_management_view_mode_get',
        summary='Get repository view mode',
        description='Get the view mode preference for a specific repository.',
        parameters=[
            OpenApiParameter(
                name='repo_id',
                type=str,
                location=OpenApiParameter.PATH,
                description='Repository identifier'
            )
        ],
        responses={200: RepositoryViewModeSerializer},
        tags=['user_management'],
    )
    def retrieve(self, request, repo_id=None):
        """Get view mode for a repository."""
        view_mode, created = RepositoryViewMode.objects.get_or_create(
            user=request.user,
            repository_id=repo_id
        )
        serializer = RepositoryViewModeSerializer(view_mode)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='user_management_view_mode_update',
        summary='Update repository view mode',
        description='Update the view mode preference for a specific repository.',
        parameters=[
            OpenApiParameter(
                name='repo_id',
                type=str,
                location=OpenApiParameter.PATH,
                description='Repository identifier'
            )
        ],
        request=RepositoryViewModeSerializer,
        responses={200: RepositoryViewModeSerializer},
        tags=['user_management'],
    )
    def update(self, request, repo_id=None):
        """Update view mode for a repository."""
        view_mode, created = RepositoryViewMode.objects.get_or_create(
            user=request.user,
            repository_id=repo_id
        )
        serializer = RepositoryViewModeSerializer(view_mode, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserSettingsViewSet(viewsets.ViewSet):
    """
    Generic user settings management.
    Provides endpoints for storing and retrieving arbitrary user settings.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        operation_id='user_settings_get',
        summary='Get user settings',
        description='Get all user settings as a JSON object.',
        responses={200: UserSettingsUpdateSerializer},
        tags=['user_settings'],
    )
    @action(detail=False, methods=['get'], url_path='')
    def get_settings(self, request):
        """Get user settings."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        return Response({'settings': profile.settings})
    
    @extend_schema(
        operation_id='user_settings_update',
        summary='Update user settings',
        description='Update user settings (merges with existing settings).',
        request=UserSettingsUpdateSerializer,
        responses={200: UserSettingsUpdateSerializer},
        tags=['user_settings'],
    )
    @action(detail=False, methods=['patch'], url_path='')
    def update_settings(self, request):
        """Update user settings (merge)."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Merge new settings with existing
        new_settings = serializer.validated_data['settings']
        profile.settings.update(new_settings)
        profile.save()
        
        return Response({'settings': profile.settings})
    
    @extend_schema(
        operation_id='user_settings_replace',
        summary='Replace user settings',
        description='Replace all user settings with new settings.',
        request=UserSettingsUpdateSerializer,
        responses={200: UserSettingsUpdateSerializer},
        tags=['user_settings'],
    )
    @action(detail=False, methods=['put'], url_path='')
    def replace_settings(self, request):
        """Replace user settings (full replace)."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserSettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Replace all settings
        profile.settings = serializer.validated_data['settings']
        profile.save()
        
        return Response({'settings': profile.settings})


class RepositorySettingsViewSet(viewsets.ViewSet):
    """
    Per-repository settings management.
    Stores repository-specific configuration like document index, branch, etc.
    
    @cpt-cyberwiki-fr-document-index
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        operation_id='repository_settings_list',
        summary='List repository settings',
        description='List all repository settings for the current user.',
        responses={200: RepositorySettingsSerializer(many=True)},
        tags=['repository_settings'],
    )
    def list(self, request):
        """List all repository settings."""
        settings = RepositorySettings.objects.filter(user=request.user)
        serializer = RepositorySettingsSerializer(settings, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        operation_id='repository_settings_get',
        summary='Get repository settings',
        description='Get settings for a specific repository.',
        parameters=[
            OpenApiParameter(name='repository_id', type=str, location=OpenApiParameter.PATH),
        ],
        responses={200: RepositorySettingsSerializer},
        tags=['repository_settings'],
    )
    def retrieve(self, request, pk=None):
        """Get settings for a specific repository."""
        try:
            settings = RepositorySettings.objects.get(
                user=request.user,
                repository_id=pk
            )
            serializer = RepositorySettingsSerializer(settings)
            return Response(serializer.data)
        except RepositorySettings.DoesNotExist:
            # Return default settings
            return Response({
                'repository_id': pk,
                'provider': '',
                'base_url': '',
                'branch': 'main',
                'settings': {
                    'documentIndex': {
                        'includedExtensions': ['.md', '.mdx'],
                        'excludedPaths': ['**/node_modules/**', '**/.github/**'],
                        'titleExtraction': 'first-heading',
                        'defaultViewMode': 'document'
                    },
                    'viewMode': 'document'
                }
            })
    
    @extend_schema(
        operation_id='repository_settings_create_or_update',
        summary='Create or update repository settings',
        description='Create or update settings for a specific repository.',
        parameters=[
            OpenApiParameter(name='repository_id', type=str, location=OpenApiParameter.PATH),
        ],
        request=RepositorySettingsSerializer,
        responses={200: RepositorySettingsSerializer},
        tags=['repository_settings'],
    )
    def update(self, request, pk=None):
        """Create or update repository settings."""
        settings, created = RepositorySettings.objects.get_or_create(
            user=request.user,
            repository_id=pk,
            defaults={
                'provider': request.data.get('provider', ''),
                'base_url': request.data.get('base_url', ''),
                'branch': request.data.get('branch', 'main'),
                'settings': request.data.get('settings', {})
            }
        )
        
        if not created:
            serializer = RepositorySettingsSerializer(settings, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        
        response_serializer = RepositorySettingsSerializer(settings)
        return Response(response_serializer.data)
