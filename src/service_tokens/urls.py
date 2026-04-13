"""
URL configuration for service tokens.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tokens', views.ServiceTokenViewSet, basename='service-tokens')

urlpatterns = router.urls
