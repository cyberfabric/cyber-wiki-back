"""
URL configuration for CyberWiki backend.
"""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v1 endpoints (each module manages its own v1 prefix)
    path('api/auth/v1/', include('users.auth_urls')),
    path('api/user_management/v1/', include('users.urls')),
    path('api/wiki/v1/', include('wiki.urls')),
    path('api/git-provider/v1/', include('git_provider.urls')),
    path('api/source/v1/', include('source_provider.urls')),
    path('api/enrichments/v1/', include('enrichment_provider.urls')),
    path('api/service-tokens/v1/', include('service_tokens.urls')),
    
    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
