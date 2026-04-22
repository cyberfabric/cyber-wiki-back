"""
URL routing for wiki endpoints.
"""
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import space_views
from .views_comments import FileCommentViewSet
from .views_user_changes import UserChangeViewSet
from .views_tags import TagViewSet, DocumentTagViewSet
from .views_links import DocumentLinkViewSet
from .views_file_mapping import FileMappingViewSet
from .views_draft_changes import DraftChangeViewSet
from .views_user_branch import UserBranchViewSet

router = DefaultRouter()

# Space-centric API endpoints
router.register(r'spaces', space_views.SpaceViewSet, basename='space')
router.register(r'preferences', space_views.UserSpacePreferenceViewSet, basename='preferences')

# Supporting endpoints
router.register(r'comments', FileCommentViewSet, basename='comment')
router.register(r'changes', UserChangeViewSet, basename='change')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'document-tags', DocumentTagViewSet, basename='document-tag')
router.register(r'links', DocumentLinkViewSet, basename='link')

# Draft changes (new simplified edit workflow)
router.register(r'draft-changes', DraftChangeViewSet, basename='draft-change')

# User branch management (commit, PR, discard, unstage, rebase)
router.register(r'user-branch', UserBranchViewSet, basename='user-branch')

# Nested routes for file mappings under spaces
file_mapping_router = DefaultRouter()
file_mapping_router.register(r'file-mappings', FileMappingViewSet, basename='file-mapping')

urlpatterns = router.urls + [
    path('spaces/<slug:space_slug>/', include(file_mapping_router.urls)),
]
