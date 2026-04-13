"""
URL routing for user management endpoints.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Profile
    path('profile', views.UserProfileViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='user-profile'),
    
    # API Tokens
    path('tokens', views.ApiTokenViewSet.as_view({'get': 'list', 'post': 'create'}), name='api-tokens'),
    path('tokens/<uuid:pk>', views.ApiTokenViewSet.as_view({'delete': 'destroy'}), name='api-token-detail'),
    
    # Favorites
    path('favorites', views.FavoriteRepositoryViewSet.as_view({'get': 'list', 'post': 'create'}), name='favorites'),
    path('favorites/<uuid:pk>', views.FavoriteRepositoryViewSet.as_view({'delete': 'destroy'}), name='favorite-detail'),
    
    # Recent repositories
    path('recent', views.RecentRepositoryViewSet.as_view({'get': 'list'}), name='recent-repositories'),
    
    # View modes
    path('view-modes/<str:repo_id>', views.RepositoryViewModeViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='view-mode'),
    
    # Generic user settings
    path('settings', views.UserSettingsViewSet.as_view({
        'get': 'get_settings',
        'patch': 'update_settings',
        'put': 'replace_settings'
    }), name='user-settings'),
    
    # Repository-specific settings
    path('repository-settings', views.RepositorySettingsViewSet.as_view({'get': 'list'}), name='repository-settings-list'),
    path('repository-settings/<str:pk>', views.RepositorySettingsViewSet.as_view({
        'get': 'retrieve',
        'put': 'update'
    }), name='repository-settings-detail'),
]
