"""
URL routing for wiki endpoints.
"""
from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from .views_comments import FileCommentViewSet
from .views_user_changes import UserChangeViewSet
from .views_tags import TagViewSet, DocumentTagViewSet
from .views_links import DocumentLinkViewSet

router = DefaultRouter()
router.register(r'spaces', views.SpaceViewSet, basename='space')
router.register(r'documents', views.DocumentViewSet, basename='document')
router.register(r'comments', FileCommentViewSet, basename='comment')
router.register(r'changes', UserChangeViewSet, basename='change')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'document-tags', DocumentTagViewSet, basename='document-tag')
router.register(r'links', DocumentLinkViewSet, basename='link')

urlpatterns = router.urls
