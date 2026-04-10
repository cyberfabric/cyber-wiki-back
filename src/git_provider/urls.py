"""
URL routing for Git provider endpoints.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'repositories', views.GitProviderViewSet, basename='git-provider')

urlpatterns = router.urls
